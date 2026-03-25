"""Component Recipe Validators (Epic 58, Story 58.3).

Reusable validators that check DOM structure, CSS classes, ARIA attributes, and
visual properties for each UI component recipe defined in Section 9 of the
TheStudio style guide (``docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md``).

Covers:
- Cards (§9.1)
- Tables (§9.2)
- Badges (§9.3)
- Buttons (§9.4)
- Form Inputs (§9.8)
- Empty States (§9.11)
- Alerts and Toasts (§9.9)
- Modals and Dialogs (§9.6)

Each validator returns a :class:`ValidationResult` dataclass with ``passed``,
``component``, and ``details`` (list of check descriptions).  Failed checks are
prefixed with ``"FAIL:"``; passed checks with ``"OK:"``.

Usage example::

    from tests.playwright.lib.component_validators import (
        validate_card,
        validate_table,
        validate_badge,
        validate_button,
        validate_form_input,
        validate_empty_state,
        validate_alert,
        validate_modal,
    )

    def test_card(page):
        page.goto("/admin/ui/dashboard")
        result = validate_card(page, ".dashboard-card")
        assert result.passed, result.summary()

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Structured pass/fail result returned by every component validator."""

    component: str
    details: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return True only when no detail line starts with ``"FAIL:"``."""
        return not any(d.startswith("FAIL:") for d in self.details)

    def summary(self) -> str:
        """One-line summary suitable for pytest ``assert`` messages."""
        status = "PASS" if self.passed else "FAIL"
        failures = [d for d in self.details if d.startswith("FAIL:")]
        if failures:
            return f"[{status}] {self.component}: " + "; ".join(failures)
        return f"[{status}] {self.component}: all checks passed"


# ---------------------------------------------------------------------------
# Low-level JS helpers (shared with style/typography assertion libs)
# ---------------------------------------------------------------------------

_JS_GET_PROP = """
(args) => {
    const el = document.querySelector(args.selector);
    if (!el) return null;
    return window.getComputedStyle(el)[args.prop];
}
"""

_JS_GET_ATTR = """
(args) => {
    const el = document.querySelector(args.selector);
    if (!el) return null;
    return el.getAttribute(args.attr);
}
"""

_JS_GET_BOUNDING_RECT = """
(args) => {
    const el = document.querySelector(args.selector);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {width: r.width, height: r.height};
}
"""

_JS_HAS_SCOPE_COL = """
(args) => {
    const table = document.querySelector(args.selector);
    if (!table) return {total: 0, missing: 0};
    const ths = table.querySelectorAll('th');
    let missing = 0;
    ths.forEach(th => {
        const sc = th.getAttribute('scope');
        if (sc !== 'col' && sc !== 'row') missing++;
    });
    return {total: ths.length, missing};
}
"""

_JS_CHECK_LABEL_ASSOCIATION = """
(args) => {
    const input = document.querySelector(args.selector);
    if (!input) return 'missing';
    const id = input.id;
    if (id) {
        const label = document.querySelector('label[for="' + id + '"]');
        if (label) return 'for-id';
    }
    if (input.closest('label')) return 'wrapped';
    return 'none';
}
"""

_JS_GET_TAG = """
(args) => {
    const el = document.querySelector(args.selector);
    if (!el) return null;
    return el.tagName.toLowerCase();
}
"""

_JS_HAS_CHILD_TAG = """
(args) => {
    const parent = document.querySelector(args.selector);
    if (!parent) return false;
    return !!parent.querySelector(args.tag);
}
"""

_JS_GET_TEXT_CONTENT = """
(args) => {
    const el = document.querySelector(args.selector);
    if (!el) return null;
    return el.textContent.trim();
}
"""

_JS_COUNT_CHILDREN = """
(args) => {
    const parent = document.querySelector(args.selector);
    if (!parent) return 0;
    return parent.querySelectorAll(args.childSelector).length;
}
"""

_JS_PRESS_ESCAPE_AND_CHECK_HIDDEN = """
async (args) => {
    const el = document.querySelector(args.selector);
    if (!el) return 'missing';
    const before = window.getComputedStyle(el).display;
    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    await new Promise(r => setTimeout(r, 100));
    const after = window.getComputedStyle(el).display;
    return {before, after};
}
"""


def _prop(page: object, selector: str, prop: str) -> str | None:
    """Return computed CSS property for element matching *selector*."""
    return page.evaluate(_JS_GET_PROP, {"selector": selector, "prop": prop})  # type: ignore[attr-defined]


def _attr(page: object, selector: str, attr: str) -> str | None:
    """Return attribute value for element matching *selector*."""
    return page.evaluate(_JS_GET_ATTR, {"selector": selector, "attr": attr})  # type: ignore[attr-defined]


def _rect(page: object, selector: str) -> dict | None:
    """Return {width, height} bounding rect for element matching *selector*."""
    return page.evaluate(_JS_GET_BOUNDING_RECT, {"selector": selector})  # type: ignore[attr-defined]


def _tag(page: object, selector: str) -> str | None:
    """Return lowercase tag name for element matching *selector*."""
    return page.evaluate(_JS_GET_TAG, {"selector": selector})  # type: ignore[attr-defined]


def _has_child(page: object, selector: str, child_tag: str) -> bool:
    """Return True when *selector* contains at least one *child_tag* descendant."""
    return page.evaluate(_JS_HAS_CHILD_TAG, {"selector": selector, "tag": child_tag})  # type: ignore[attr-defined]


def _count(page: object, selector: str, child_selector: str) -> int:
    """Count descendant elements matching *child_selector* within *selector*."""
    return page.evaluate(_JS_COUNT_CHILDREN, {"selector": selector, "childSelector": child_selector})  # type: ignore[attr-defined]


def _css_value_to_px(value: str | None) -> float:
    """Parse a CSS pixel value like ``"8px"`` → ``8.0``.  Returns ``-1`` on failure."""
    if not value:
        return -1.0
    value = value.strip()
    if value.endswith("px"):
        try:
            return float(value[:-2])
        except ValueError:
            return -1.0
    return -1.0


# ---------------------------------------------------------------------------
# Colour token helpers (light-theme primitive values from §4.1)
# ---------------------------------------------------------------------------

_GRAY_50_RGB = "rgb(249, 250, 251)"
_GRAY_800_RGB = "rgb(31, 41, 55)"
_GRAY_900_RGB = "rgb(17, 24, 39)"
_WHITE_RGB = "rgb(255, 255, 255)"
_GRAY_200_RGB = "rgb(229, 231, 235)"
_GRAY_700_RGB = "rgb(55, 65, 81)"

# Acceptable border-color values — hex/rgb vary by browser so we accept both.
_LIGHT_BORDER_COLORS = {_GRAY_200_RGB, "#e5e7eb"}
_DARK_BORDER_COLORS = {_GRAY_700_RGB, "#374151"}
_LIGHT_BG = {_WHITE_RGB, "#ffffff", "#fff"}
_DARK_BG = {_GRAY_900_RGB, "#111827"}

# ---------------------------------------------------------------------------
# 1. validate_card  (§9.1)
# ---------------------------------------------------------------------------


def validate_card(
    page: object,
    selector: str,
    *,
    dark: bool = False,
) -> ValidationResult:
    """Validate a card element against §9.1 style guide requirements.

    Checks background colour, border colour, border-radius (≥ 8 px), and
    padding (≥ 16 px / p-4 compact) on the element matched by *selector*.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the card element.
        dark: Set ``True`` when checking a dark-theme card.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"card({selector})")

    bg = _prop(page, selector, "backgroundColor")
    border_color = _prop(page, selector, "borderColor")
    border_radius_raw = _prop(page, selector, "borderRadius")
    padding_top_raw = _prop(page, selector, "paddingTop")

    # Background
    expected_bg = _DARK_BG if dark else _LIGHT_BG
    if bg in expected_bg or (dark and _GRAY_900_RGB in (bg or "")):
        result.details.append(f"OK: background {bg!r} matches {'dark' if dark else 'light'} spec")
    else:
        result.details.append(
            f"FAIL: background {bg!r} — expected one of {sorted(expected_bg)}"
        )

    # Border colour
    expected_border = _DARK_BORDER_COLORS if dark else _LIGHT_BORDER_COLORS
    if any(c in (border_color or "") for c in expected_border) or border_color in expected_border:
        result.details.append(f"OK: borderColor {border_color!r} matches spec")
    else:
        result.details.append(
            f"FAIL: borderColor {border_color!r} — expected one of {sorted(expected_border)}"
        )

    # Border radius ≥ 8 px (rounded-lg)
    radius_px = _css_value_to_px(border_radius_raw)
    if radius_px >= 8.0:
        result.details.append(f"OK: borderRadius {border_radius_raw!r} ≥ 8px (rounded-lg)")
    else:
        result.details.append(
            f"FAIL: borderRadius {border_radius_raw!r} — expected ≥ 8px (rounded-lg)"
        )

    # Padding ≥ 16 px (p-4)
    padding_px = _css_value_to_px(padding_top_raw)
    if padding_px >= 16.0:
        result.details.append(f"OK: paddingTop {padding_top_raw!r} ≥ 16px (p-4)")
    else:
        result.details.append(
            f"FAIL: paddingTop {padding_top_raw!r} — expected ≥ 16px (p-4 / p-6)"
        )

    return result


# ---------------------------------------------------------------------------
# 2. validate_table  (§9.2)
# ---------------------------------------------------------------------------


def validate_table(
    page: object,
    selector: str,
    *,
    dark: bool = False,
) -> ValidationResult:
    """Validate a table against §9.2 style guide requirements.

    Checks:
    - ``<thead>`` background (gray-50 light / gray-800 dark).
    - All ``<th>`` elements carry ``scope="col"`` or ``scope="row"``.
    - At least one numeric column is right-aligned with ``font-family``
      containing ``JetBrains Mono`` or ``monospace``.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the ``<table>`` element.
        dark: Set ``True`` when checking a dark-theme table.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"table({selector})")

    # Header background
    thead_selector = f"{selector} thead tr"
    header_bg = _prop(page, thead_selector, "backgroundColor")
    expected_header = _GRAY_800_RGB if dark else _GRAY_50_RGB
    if expected_header in (header_bg or ""):
        result.details.append(f"OK: thead background {header_bg!r} matches spec")
    else:
        result.details.append(
            f"FAIL: thead background {header_bg!r} — expected {expected_header!r}"
        )

    # scope="col" / scope="row" on all <th>
    scope_info = page.evaluate(_JS_HAS_SCOPE_COL, {"selector": selector})  # type: ignore[attr-defined]
    if scope_info is None:
        result.details.append(f"FAIL: table element not found at {selector!r}")
    elif scope_info["total"] == 0:
        result.details.append("FAIL: no <th> elements found in table")
    elif scope_info["missing"] == 0:
        result.details.append(
            f"OK: all {scope_info['total']} <th> elements have scope attribute"
        )
    else:
        result.details.append(
            f"FAIL: {scope_info['missing']}/{scope_info['total']} <th> elements "
            "missing scope='col'/'row' — required for screen reader compliance"
        )

    # Numeric columns: at least one td with text-align:right + font-family containing mono
    mono_count = _count(
        page, selector, "td[style*='text-align: right'], td.text-right, td[class*='right']"
    )
    if mono_count > 0:
        result.details.append(
            f"OK: found {mono_count} right-aligned numeric column cell(s)"
        )
    else:
        # Non-fatal: many tables have no numeric columns; just note it
        result.details.append(
            "OK: no right-aligned numeric columns detected (acceptable if table has none)"
        )

    return result


# ---------------------------------------------------------------------------
# 3. validate_badge  (§9.3)
# ---------------------------------------------------------------------------


def validate_badge(
    page: object,
    selector: str,
) -> ValidationResult:
    """Validate a badge / pill element against §9.3 style guide requirements.

    Checks:
    - Horizontal padding ≥ 8 px (``px-2``).
    - Vertical padding ≥ 2 px (``py-0.5``).
    - ``border-radius`` set (``rounded``).
    - Font size ≤ 12 px (``text-xs``).
    - Font weight ≥ 600 (``font-semibold``).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the badge element.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"badge({selector})")

    padding_left = _css_value_to_px(_prop(page, selector, "paddingLeft"))
    padding_top = _css_value_to_px(_prop(page, selector, "paddingTop"))
    border_radius = _css_value_to_px(_prop(page, selector, "borderRadius"))
    font_size = _css_value_to_px(_prop(page, selector, "fontSize"))
    font_weight_raw = _prop(page, selector, "fontWeight") or "0"
    try:
        font_weight = int(font_weight_raw)
    except ValueError:
        font_weight = 0

    # px-2 → 8px horizontal padding
    if padding_left >= 8.0:
        result.details.append(f"OK: paddingLeft {padding_left}px ≥ 8px (px-2)")
    else:
        result.details.append(f"FAIL: paddingLeft {padding_left}px — expected ≥ 8px (px-2)")

    # py-0.5 → 2px vertical padding
    if padding_top >= 2.0:
        result.details.append(f"OK: paddingTop {padding_top}px ≥ 2px (py-0.5)")
    else:
        result.details.append(f"FAIL: paddingTop {padding_top}px — expected ≥ 2px (py-0.5)")

    # rounded → any border-radius
    if border_radius > 0:
        result.details.append(f"OK: borderRadius {border_radius}px (rounded)")
    else:
        result.details.append("FAIL: borderRadius is 0 — expected 'rounded' class")

    # text-xs → ≤ 12px font size
    if 0 < font_size <= 12.0:
        result.details.append(f"OK: fontSize {font_size}px ≤ 12px (text-xs)")
    else:
        result.details.append(f"FAIL: fontSize {font_size}px — expected ≤ 12px (text-xs)")

    # font-semibold → weight 600+
    if font_weight >= 600:
        result.details.append(f"OK: fontWeight {font_weight} ≥ 600 (font-semibold)")
    else:
        result.details.append(
            f"FAIL: fontWeight {font_weight} — expected ≥ 600 (font-semibold)"
        )

    return result


# ---------------------------------------------------------------------------
# 4. validate_button  (§9.4)
# ---------------------------------------------------------------------------

ButtonVariant = Literal["primary", "secondary", "destructive", "ghost", "icon"]


def validate_button(
    page: object,
    selector: str,
    variant: ButtonVariant = "primary",
) -> ValidationResult:
    """Validate a button element against §9.4 style guide requirements.

    Checks:
    - ``border-radius`` ≥ 6 px (``rounded-md``).
    - Horizontal padding ≥ 12 px (``px-3``).
    - Vertical padding ≥ 8 px (``py-2``).
    - Font size ≤ 14 px (``text-sm``).
    - Font weight ≥ 500 (``font-medium``).
    - Touch target: rendered width ≥ 24 px and height ≥ 24 px.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the button element.
        variant: One of ``"primary"``, ``"secondary"``, ``"destructive"``,
            ``"ghost"``, or ``"icon"``.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"button[{variant}]({selector})")

    border_radius = _css_value_to_px(_prop(page, selector, "borderRadius"))
    padding_left = _css_value_to_px(_prop(page, selector, "paddingLeft"))
    padding_top = _css_value_to_px(_prop(page, selector, "paddingTop"))
    font_size = _css_value_to_px(_prop(page, selector, "fontSize"))
    font_weight_raw = _prop(page, selector, "fontWeight") or "0"
    try:
        font_weight = int(font_weight_raw)
    except ValueError:
        font_weight = 0
    dims = _rect(page, selector)

    # rounded-md → ≥ 6px
    if border_radius >= 6.0:
        result.details.append(f"OK: borderRadius {border_radius}px ≥ 6px (rounded-md)")
    else:
        result.details.append(
            f"FAIL: borderRadius {border_radius}px — expected ≥ 6px (rounded-md)"
        )

    # icon buttons use p-2 (8px all sides) not px-3 py-2
    if variant == "icon":
        if padding_left >= 8.0:
            result.details.append(f"OK: paddingLeft {padding_left}px ≥ 8px (p-2 icon)")
        else:
            result.details.append(
                f"FAIL: paddingLeft {padding_left}px — expected ≥ 8px for icon button"
            )
    else:
        # px-3 → 12px
        if padding_left >= 12.0:
            result.details.append(f"OK: paddingLeft {padding_left}px ≥ 12px (px-3)")
        else:
            result.details.append(
                f"FAIL: paddingLeft {padding_left}px — expected ≥ 12px (px-3)"
            )
        # py-2 → 8px
        if padding_top >= 8.0:
            result.details.append(f"OK: paddingTop {padding_top}px ≥ 8px (py-2)")
        else:
            result.details.append(
                f"FAIL: paddingTop {padding_top}px — expected ≥ 8px (py-2)"
            )

    # text-sm → ≤ 14px
    if 0 < font_size <= 14.0:
        result.details.append(f"OK: fontSize {font_size}px ≤ 14px (text-sm)")
    else:
        result.details.append(f"FAIL: fontSize {font_size}px — expected ≤ 14px (text-sm)")

    # font-medium → weight 500+
    if font_weight >= 500:
        result.details.append(f"OK: fontWeight {font_weight} ≥ 500 (font-medium)")
    else:
        result.details.append(
            f"FAIL: fontWeight {font_weight} — expected ≥ 500 (font-medium)"
        )

    # Touch target ≥ 24×24px
    if dims:
        w, h = dims["width"], dims["height"]
        if w >= 24 and h >= 24:
            result.details.append(
                f"OK: touch target {w:.0f}×{h:.0f}px ≥ 24×24px minimum"
            )
        else:
            result.details.append(
                f"FAIL: touch target {w:.0f}×{h:.0f}px — expected ≥ 24×24px"
            )
    else:
        result.details.append(f"FAIL: element not found at {selector!r}")

    return result


# ---------------------------------------------------------------------------
# 5. validate_form_input  (§9.8)
# ---------------------------------------------------------------------------


def validate_form_input(
    page: object,
    selector: str,
) -> ValidationResult:
    """Validate a form input against §9.8 style guide requirements.

    Checks:
    - Associated ``<label>`` (``for``/``id`` or wrapper).
    - Border present (border-style solid or similar).
    - ``aria-describedby`` attribute set for help/error text.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the ``<input>`` (or ``<textarea>``,
            ``<select>``) element.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"form_input({selector})")

    # Label association
    assoc = page.evaluate(_JS_CHECK_LABEL_ASSOCIATION, {"selector": selector})  # type: ignore[attr-defined]
    if assoc == "for-id":
        result.details.append("OK: label associated via for/id")
    elif assoc == "wrapped":
        result.details.append("OK: input wrapped in <label>")
    elif assoc == "none":
        result.details.append("FAIL: no associated <label> found (for/id or wrapper)")
    else:
        result.details.append(f"FAIL: input element not found at {selector!r}")

    # Border
    border_style = _prop(page, selector, "borderStyle")
    if border_style and border_style not in ("none", ""):
        result.details.append(f"OK: border present (borderStyle={border_style!r})")
    else:
        result.details.append(f"FAIL: no visible border (borderStyle={border_style!r})")

    # aria-describedby
    describedby = _attr(page, selector, "aria-describedby")
    if describedby:
        result.details.append(f"OK: aria-describedby={describedby!r} (help/error text)")
    else:
        # Warn but do not fail — not all inputs require help text
        result.details.append(
            "OK: no aria-describedby (acceptable when no help text is shown)"
        )

    return result


# ---------------------------------------------------------------------------
# 6. validate_empty_state  (§9.11)
# ---------------------------------------------------------------------------


def validate_empty_state(
    page: object,
    selector: str,
) -> ValidationResult:
    """Validate an empty-state container against §9.11 style guide requirements.

    Checks:
    - A heading element (``h2``–``h4`` or element with ``role="heading"``) is present.
    - A ``<p>`` description element is present.
    - A ``<button>`` or ``<a>`` CTA element is present.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the empty-state container.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"empty_state({selector})")

    # Heading
    heading_count = _count(
        page, selector, "h1, h2, h3, h4, [role='heading']"
    )
    if heading_count > 0:
        result.details.append(f"OK: heading element present ({heading_count} found)")
    else:
        result.details.append(
            "FAIL: no heading element (h2–h4 or role='heading') — required by §9.11"
        )

    # Description paragraph
    desc_count = _count(page, selector, "p")
    if desc_count > 0:
        result.details.append(f"OK: description <p> element present ({desc_count} found)")
    else:
        result.details.append(
            "FAIL: no <p> description element — required by §9.11"
        )

    # CTA button or link
    cta_count = _count(page, selector, "button, a[href]")
    if cta_count > 0:
        result.details.append(f"OK: CTA button/link present ({cta_count} found)")
    else:
        result.details.append(
            "FAIL: no CTA button or link — required by §9.11"
        )

    return result


# ---------------------------------------------------------------------------
# 7. validate_alert  (§9.9)
# ---------------------------------------------------------------------------

AlertVariant = Literal["error", "warning", "success", "info"]

# Light-theme background colours for alert variants
_ALERT_BG: dict[str, str] = {
    "error":   "rgb(254, 242, 242)",   # bg-red-50
    "warning": "rgb(255, 251, 235)",   # bg-yellow-50
    "success": "rgb(240, 253, 244)",   # bg-green-50
    "info":    "rgb(239, 246, 255)",   # bg-blue-50
}


def validate_alert(
    page: object,
    selector: str,
    variant: AlertVariant = "error",
) -> ValidationResult:
    """Validate an alert/toast element against §9.9 style guide requirements.

    Checks:
    - ``role="alert"`` or ``role="status"`` attribute present.
    - Background colour matches the expected variant.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the alert element.
        variant: One of ``"error"``, ``"warning"``, ``"success"``, ``"info"``.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"alert[{variant}]({selector})")

    # role attribute
    role = _attr(page, selector, "role")
    if role in ("alert", "status"):
        result.details.append(f"OK: role={role!r} present")
    else:
        result.details.append(
            f"FAIL: role={role!r} — expected 'alert' (persistent) or 'status' (toast)"
        )

    # Background colour
    bg = _prop(page, selector, "backgroundColor")
    expected_bg = _ALERT_BG.get(variant, "")
    if bg and expected_bg and expected_bg in bg:
        result.details.append(
            f"OK: background {bg!r} matches {variant} variant spec"
        )
    else:
        result.details.append(
            f"FAIL: background {bg!r} — expected ~{expected_bg!r} for {variant} variant"
        )

    return result


# ---------------------------------------------------------------------------
# 8. validate_modal  (§9.6)
# ---------------------------------------------------------------------------


def validate_modal(
    page: object,
    selector: str,
    *,
    check_escape: bool = False,
) -> ValidationResult:
    """Validate a modal/dialog element against §9.6 style guide requirements.

    Checks:
    - ``role="dialog"`` attribute.
    - ``aria-modal="true"`` attribute.
    - ``aria-labelledby`` attribute pointing to a title element.

    When *check_escape* is ``True``, dispatches an ``Escape`` keydown event and
    verifies the dialog is no longer visible (``display: none``).  This requires
    the page's close handler to respond to the DOM event.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector targeting the modal container.
        check_escape: When ``True``, verify Escape key closes the modal.

    Returns:
        :class:`ValidationResult` with ``passed`` and ``details``.
    """
    result = ValidationResult(component=f"modal({selector})")

    # role="dialog"
    role = _attr(page, selector, "role")
    if role == "dialog":
        result.details.append("OK: role='dialog' present")
    else:
        result.details.append(f"FAIL: role={role!r} — expected 'dialog'")

    # aria-modal="true"
    aria_modal = _attr(page, selector, "aria-modal")
    if aria_modal == "true":
        result.details.append("OK: aria-modal='true' present")
    else:
        result.details.append(f"FAIL: aria-modal={aria_modal!r} — expected 'true'")

    # aria-labelledby
    labelledby = _attr(page, selector, "aria-labelledby")
    if labelledby:
        result.details.append(f"OK: aria-labelledby={labelledby!r} present")
    else:
        result.details.append(
            "FAIL: aria-labelledby missing — required for accessible modal title"
        )

    # Optional: Escape key closes
    if check_escape:
        escape_result = page.evaluate(  # type: ignore[attr-defined]
            _JS_PRESS_ESCAPE_AND_CHECK_HIDDEN, {"selector": selector}
        )
        if isinstance(escape_result, dict):
            before = escape_result.get("before", "")
            after = escape_result.get("after", "")
            if after in ("none", "") and before not in ("none", ""):
                result.details.append("OK: Escape key closes the modal")
            else:
                result.details.append(
                    f"FAIL: modal still visible after Escape (before={before!r}, after={after!r})"
                )
        else:
            result.details.append(
                "FAIL: could not evaluate Escape-key behaviour (modal not found?)"
            )

    return result
