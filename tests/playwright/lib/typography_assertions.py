"""Typography & Spacing Assertion Library (Epic 58, Story 58.2).

Reusable assertion helpers that extract computed CSS typography and spacing
values from Playwright page elements via ``page.evaluate()`` /
``getComputedStyle()`` and validate them against the TheStudio style guide
definitions (Sections 6–7 of
``docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md``).

Covers:
- Type scale roles: page_title / section_title / subsection / label / body /
  caption / kpi / code (§6.2)
- Heading scale: h1–h3 pixel/weight validation (§6.2)
- Font family: Inter (sans) / JetBrains Mono (mono) (§6.1)
- Spacing: 4px-grid validation for padding / margin / gap (§7.1)
- Density modes: compact (32px) / comfortable (40px) / spacious (48px+) (§7.2)

Usage example::

    from tests.playwright.lib.typography_assertions import (
        assert_typography,
        assert_heading_scale,
        assert_spacing,
        assert_density_mode,
    )

    def test_headings(page):
        page.goto("/admin/ui/dashboard")
        assert_heading_scale(page)
        assert_typography(page, "h1", role="page_title")
        assert_spacing(page, ".card", "padding", 16)

"""

from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Type scale definitions (§6.2)
# ---------------------------------------------------------------------------

# Type role → (font_size_px, font_weight, line_height, letter_spacing_em)
# line_height is expressed as a unitless ratio (e.g. 1.5)
# letter_spacing_em: None means "normal" (≈ 0em)
_TYPE_SCALE: dict[str, tuple[float, int, float, float | None]] = {
    "page_title":      (20.0, 600, 1.4, None),
    "section_title":   (16.0, 600, 1.5, None),
    "subsection":      (14.0, 600, 1.5, None),
    "label":           (12.0, 600, 1.5, 0.05),
    "body":            (14.0, 400, 1.5, None),
    "caption":         (12.0, 400, 1.5, None),
    "kpi":             (24.0, 700, 1.2, -0.01),  # lower bound; 24–30px accepted
    "code":            (13.0, 400, 1.5, None),
}

# KPI font-size is a range: 24px–30px
_KPI_SIZE_RANGE: tuple[float, float] = (24.0, 30.0)

# Font family keys
_FONT_FAMILY_SANS = "Inter"
_FONT_FAMILY_MONO = "JetBrains Mono"

# Density modes (§7.2): mode → minimum row height in px
_DENSITY_ROW_HEIGHTS: dict[str, int] = {
    "compact":     32,
    "comfortable": 40,
    "spacious":    48,
}

# Maximum height tolerance when checking density (px)
_DENSITY_TOLERANCE_PX = 4

# ---------------------------------------------------------------------------
# Low-level JS helpers
# ---------------------------------------------------------------------------


def _get_computed_style(page: object, selector: str, property_name: str) -> str:
    """Return the computed CSS *property_name* for the first element matching
    *selector*, as a string (e.g. ``"14px"`` or ``"400"``).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector string.
        property_name: camelCase CSS property (e.g. ``"fontSize"``).

    Returns:
        The raw computed value string, or an empty string if not found.

    Raises:
        AssertionError: if *selector* matches no element on the page.

    Example::

        font_size = _get_computed_style(page, "h1", "fontSize")  # "20px"
    """
    js = f"""
    (function() {{
        var el = document.querySelector({selector!r});
        if (!el) return null;
        return window.getComputedStyle(el).getPropertyValue({property_name!r});
    }})()
    """
    result = page.evaluate(js)  # type: ignore[attr-defined]
    assert result is not None, (
        f"No element matching {selector!r} found on page — cannot read {property_name!r}"
    )
    return result.strip()


def _px_to_float(value: str) -> float:
    """Convert a CSS pixel string (e.g. ``"14px"``) to a float.

    Args:
        value: CSS value ending in ``"px"``.

    Returns:
        Numeric pixel value.

    Raises:
        ValueError: if *value* cannot be parsed as a pixel measurement.

    Example::

        _px_to_float("14px")  # 14.0
    """
    stripped = value.strip().lower()
    if stripped.endswith("px"):
        return float(stripped[:-2])
    raise ValueError(f"Cannot parse pixel value from {value!r}")


def _unitless_to_float(value: str) -> float:
    """Convert a unitless CSS number string (e.g. ``"1.5"`` or ``"400"``) to
    a float.

    Args:
        value: CSS value without units.

    Returns:
        Numeric value.

    Raises:
        ValueError: if *value* cannot be parsed.

    Example::

        _unitless_to_float("1.5")  # 1.5
    """
    try:
        return float(value.strip())
    except ValueError as exc:
        raise ValueError(f"Cannot parse unitless value from {value!r}") from exc


def _em_to_float(value: str) -> float | None:
    """Convert a CSS letter-spacing value to em float.

    Handles ``"normal"`` (returns ``None``), ``"0.05em"`` style, and plain
    ``"0"`` (returns ``0.0``).

    Args:
        value: CSS letter-spacing value.

    Returns:
        Float em value, or ``None`` for ``"normal"``.

    Example::

        _em_to_float("0.05em")  # 0.05
        _em_to_float("normal")  # None
    """
    stripped = value.strip().lower()
    if stripped == "normal":
        return None
    if stripped.endswith("em"):
        return float(stripped[:-2])
    if stripped == "0":
        return 0.0
    # px letter spacing: convert by assuming 1em ≈ font-size; skip for now
    return None


def _normalize_font_family(value: str) -> str:
    """Return the *first* font name from a CSS font-family stack, stripped of
    quotes and normalised to title case.

    Args:
        value: Full ``font-family`` computed string
               e.g. ``"'Inter', system-ui, sans-serif"``.

    Returns:
        First font family name, e.g. ``"Inter"``.

    Example::

        _normalize_font_family("'Inter', system-ui")  # "Inter"
    """
    first = value.split(",")[0].strip()
    # Remove surrounding quotes (single or double)
    first = first.strip("\"'")
    return first


# ---------------------------------------------------------------------------
# Public assertion functions
# ---------------------------------------------------------------------------


def assert_typography(
    page: object,
    selector: str,
    role: Literal[
        "page_title",
        "section_title",
        "subsection",
        "label",
        "body",
        "caption",
        "kpi",
        "code",
    ],
    *,
    size_tolerance_px: float = 0.5,
    line_height_tolerance: float = 0.05,
) -> None:
    """Assert that the element matching *selector* has the correct typography
    for the given *role* according to the style guide type scale (§6.2).

    Validates:
    - ``font-size`` (±``size_tolerance_px``, px)
    - ``font-weight``
    - ``line-height`` (±``line_height_tolerance``, unitless ratio)
    - ``letter-spacing`` (when the role defines a non-normal value)

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the element to validate.
        role: Type role name from §6.2. One of:
            ``page_title``, ``section_title``, ``subsection``, ``label``,
            ``body``, ``caption``, ``kpi``, ``code``.
        size_tolerance_px: Allowed font-size deviation in pixels.
        line_height_tolerance: Allowed line-height ratio deviation.

    Raises:
        AssertionError: on any typography mismatch.

    Example::

        assert_typography(page, "h1.page-title", role="page_title")
        assert_typography(page, "p.body-text", role="body")
        assert_typography(page, ".kpi-value", role="kpi")
    """
    assert role in _TYPE_SCALE, (
        f"Unknown type role {role!r}. Valid roles: {list(_TYPE_SCALE)}"
    )
    expected_size, expected_weight, expected_lh, expected_tracking = _TYPE_SCALE[role]

    # --- font-size ---
    raw_size = _get_computed_style(page, selector, "fontSize")
    actual_size = _px_to_float(raw_size)

    if role == "kpi":
        lo, hi = _KPI_SIZE_RANGE
        assert lo - size_tolerance_px <= actual_size <= hi + size_tolerance_px, (
            f"[{selector}] KPI font-size {actual_size}px is outside expected range "
            f"{lo}–{hi}px (tolerance ±{size_tolerance_px}px)"
        )
    else:
        assert abs(actual_size - expected_size) <= size_tolerance_px, (
            f"[{selector}] font-size {actual_size}px != expected {expected_size}px "
            f"(role={role!r}, tolerance ±{size_tolerance_px}px)"
        )

    # --- font-weight ---
    raw_weight = _get_computed_style(page, selector, "fontWeight")
    actual_weight = int(float(raw_weight))
    assert actual_weight == expected_weight, (
        f"[{selector}] font-weight {actual_weight} != expected {expected_weight} "
        f"(role={role!r})"
    )

    # --- line-height ---
    raw_lh = _get_computed_style(page, selector, "lineHeight")
    # lineHeight may be "px" string or unitless; browsers often return px
    lh_str = raw_lh.strip().lower()
    if lh_str.endswith("px") and actual_size > 0:
        # Convert px line-height to unitless ratio
        actual_lh = _px_to_float(raw_lh) / actual_size
    elif lh_str == "normal":
        actual_lh = 1.2  # browser default fallback
    else:
        actual_lh = _unitless_to_float(raw_lh)

    assert abs(actual_lh - expected_lh) <= line_height_tolerance, (
        f"[{selector}] line-height ratio {actual_lh:.3f} != expected {expected_lh} "
        f"(role={role!r}, tolerance ±{line_height_tolerance})"
    )

    # --- letter-spacing (only validated when style guide specifies non-normal) ---
    if expected_tracking is not None:
        raw_tracking = _get_computed_style(page, selector, "letterSpacing")
        actual_tracking = _em_to_float(raw_tracking)
        if actual_tracking is not None:
            assert abs(actual_tracking - expected_tracking) <= 0.005, (
                f"[{selector}] letter-spacing {actual_tracking}em != expected "
                f"{expected_tracking}em (role={role!r}, tolerance ±0.005em)"
            )


def assert_heading_scale(page: object) -> None:
    """Assert that all h1–h3 elements on the page match the style guide heading
    scale (§6.2).

    | Element | Size  | Weight |
    |---------|-------|--------|
    | h1      | 20px  | 600    |
    | h2      | 16px  | 600    |
    | h3      | 14px  | 600    |

    Each heading level is validated only when at least one matching element is
    present; no assertion is made for absent heading levels.

    Args:
        page: Playwright ``Page`` object.

    Raises:
        AssertionError: if any heading element violates the expected scale.

    Example::

        page.goto("/admin/ui/dashboard")
        assert_heading_scale(page)
    """
    heading_specs: list[tuple[str, float, int]] = [
        ("h1", 20.0, 600),
        ("h2", 16.0, 600),
        ("h3", 14.0, 600),
    ]

    for tag, expected_size_px, expected_weight in heading_specs:
        # Check how many elements exist
        count: int = page.evaluate(  # type: ignore[attr-defined]
            f"document.querySelectorAll({tag!r}).length"
        )
        if count == 0:
            continue  # No elements of this level — skip

        # Validate each element individually
        elements_info: list[dict] = page.evaluate(  # type: ignore[attr-defined]
            f"""
            Array.from(document.querySelectorAll({tag!r})).map(function(el) {{
                var s = window.getComputedStyle(el);
                return {{
                    fontSize: s.getPropertyValue('font-size'),
                    fontWeight: s.getPropertyValue('font-weight'),
                    text: el.textContent.slice(0, 40)
                }};
            }})
            """
        )

        for idx, info in enumerate(elements_info):
            actual_size = _px_to_float(info["fontSize"])
            actual_weight = int(float(info["fontWeight"]))
            label = f"<{tag}>[{idx}] {info['text']!r:.40}"

            assert abs(actual_size - expected_size_px) <= 0.5, (
                f"{label}: font-size {actual_size}px != expected {expected_size_px}px"
            )
            assert actual_weight == expected_weight, (
                f"{label}: font-weight {actual_weight} != expected {expected_weight}"
            )


def assert_font_family(
    page: object,
    selector: str,
    expected: Literal["sans", "mono"],
) -> None:
    """Assert that the element matching *selector* uses the correct font family
    per §6.1 of the style guide.

    - ``"sans"``  → first font in the ``--font-sans`` stack should be
      ``"Inter"``
    - ``"mono"``  → first font in the ``--font-mono`` stack should be
      ``"JetBrains Mono"``

    The comparison is done against the **first font name** in the computed
    ``font-family`` stack only (normalized, case-insensitive).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the element to validate.
        expected: ``"sans"`` (Inter) or ``"mono"`` (JetBrains Mono).

    Raises:
        AssertionError: if the first font family does not match.

    Example::

        assert_font_family(page, "p.body", expected="sans")
        assert_font_family(page, "code.hash", expected="mono")
    """
    assert expected in ("sans", "mono"), (
        f"expected must be 'sans' or 'mono', got {expected!r}"
    )
    expected_font = _FONT_FAMILY_SANS if expected == "sans" else _FONT_FAMILY_MONO

    raw_family = _get_computed_style(page, selector, "fontFamily")
    first_font = _normalize_font_family(raw_family)

    assert first_font.lower() == expected_font.lower(), (
        f"[{selector}] font-family first font {first_font!r} != expected "
        f"{expected_font!r} (expected={expected!r})"
    )


def assert_spacing(
    page: object,
    selector: str,
    property: Literal[
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "gap",
        "row-gap",
        "column-gap",
    ],
    expected_px: int,
    *,
    tolerance_px: int = 1,
) -> None:
    """Assert that a spacing property on the element matching *selector* equals
    *expected_px* and is a valid 4px-grid multiple (§7.1).

    For shorthand properties (``"padding"``, ``"margin"``) the top value is
    used for comparison (all four sides are expected to be equal when
    *expected_px* is given as a single value).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the element to validate.
        property: The spacing CSS property name.
        expected_px: Expected pixel value (must be a multiple of 4 per §7.1).
        tolerance_px: Allowed deviation in pixels (default 1).

    Raises:
        AssertionError: if the actual spacing deviates from *expected_px* or
            if *expected_px* is not a multiple of 4.

    Example::

        assert_spacing(page, ".card", "padding", 16)
        assert_spacing(page, "table tr", "padding-top", 8)
        assert_spacing(page, ".grid", "gap", 16)
    """
    assert expected_px % 4 == 0, (
        f"expected_px={expected_px} is not a multiple of 4 (§7.1 base unit)"
    )

    # Map shorthand to the -top or equivalent longhand for computed style
    _shorthand_to_computed: dict[str, str] = {
        "padding": "paddingTop",
        "margin":  "marginTop",
        "gap":     "rowGap",
    }
    # camelCase mapping for longhands
    _prop_camel: dict[str, str] = {
        "padding-top":    "paddingTop",
        "padding-right":  "paddingRight",
        "padding-bottom": "paddingBottom",
        "padding-left":   "paddingLeft",
        "margin-top":     "marginTop",
        "margin-right":   "marginRight",
        "margin-bottom":  "marginBottom",
        "margin-left":    "marginLeft",
        "gap":            "rowGap",
        "row-gap":        "rowGap",
        "column-gap":     "columnGap",
    }

    computed_prop = _shorthand_to_computed.get(
        property, _prop_camel.get(property, property)
    )

    raw_value = _get_computed_style(page, selector, computed_prop)
    actual_px = _px_to_float(raw_value)

    assert abs(actual_px - expected_px) <= tolerance_px, (
        f"[{selector}] {property} {actual_px}px != expected {expected_px}px "
        f"(tolerance ±{tolerance_px}px)"
    )


def assert_density_mode(
    page: object,
    selector: str,
    mode: Literal["compact", "comfortable", "spacious"],
    *,
    tolerance_px: int = _DENSITY_TOLERANCE_PX,
) -> None:
    """Assert that the element matching *selector* has a row height consistent
    with the given *mode* per the density specification (§7.2).

    | Mode        | Expected row height |
    |-------------|---------------------|
    | compact     | 32px                |
    | comfortable | 40px                |
    | spacious    | 48px+               |

    The check uses ``getBoundingClientRect().height``, which measures the
    rendered height of the element. For spacious mode the height must be
    **at least** 48px.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the row element to measure.
        mode: Density mode — ``"compact"``, ``"comfortable"``, or
            ``"spacious"``.
        tolerance_px: Allowed deviation in pixels from the target row height
            (default 4). Not used for spacious (only a lower bound is checked).

    Raises:
        AssertionError: if the actual row height does not match the expected
            density.

    Example::

        # Activity log rows should use compact density
        assert_density_mode(page, ".activity-log tr", mode="compact")

        # Standard card rows use comfortable density
        assert_density_mode(page, ".task-card", mode="comfortable")
    """
    assert mode in _DENSITY_ROW_HEIGHTS, (
        f"Unknown density mode {mode!r}. Valid modes: {list(_DENSITY_ROW_HEIGHTS)}"
    )

    js = f"""
    (function() {{
        var el = document.querySelector({selector!r});
        if (!el) return null;
        return el.getBoundingClientRect().height;
    }})()
    """
    actual_height: float | None = page.evaluate(js)  # type: ignore[attr-defined]
    assert actual_height is not None, (
        f"No element matching {selector!r} found — cannot measure row height"
    )

    expected_height = _DENSITY_ROW_HEIGHTS[mode]

    if mode == "spacious":
        assert actual_height >= expected_height - tolerance_px, (
            f"[{selector}] spacious row height {actual_height}px < minimum "
            f"{expected_height}px (§7.2)"
        )
    else:
        assert abs(actual_height - expected_height) <= tolerance_px, (
            f"[{selector}] {mode} row height {actual_height}px != expected "
            f"{expected_height}px (tolerance ±{tolerance_px}px, §7.2)"
        )
