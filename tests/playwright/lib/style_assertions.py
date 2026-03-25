"""Style Guide Color & Token Assertion Library (Epic 58, Story 58.1).

Reusable assertion helpers that extract computed CSS colors from Playwright
page elements via ``page.evaluate()`` / ``getComputedStyle()`` and validate
them against the TheStudio style guide token definitions (Sections 4–5 of
``docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md``).

Covers:
- Status colors: success / warning / error / info / neutral (§5.1)
- Trust tier colors: EXECUTE / SUGGEST / OBSERVE (§5.2)
- Role colors: ADMIN / OPERATOR (§5.3)
- Interactive / button colors: primary / secondary / destructive / ghost (§5.4)
- Focus ring color (§4.2)
- Dark-theme variants (set ``data-theme="dark"`` on the root element)

Usage example::

    from tests.playwright.lib.style_assertions import (
        assert_status_colors,
        assert_trust_tier_colors,
        assert_focus_ring_color,
    )

    def test_badge_colors(page):
        page.goto("/admin/ui/dashboard")
        assert_status_colors(page, "[data-status='success']", status="success")
        assert_focus_ring_color(page, "button.primary")
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Primitive token palette (hex values from §4.1 of the style guide)
# ---------------------------------------------------------------------------

_PRIMITIVES: dict[str, str] = {
    # Grays
    "gray-50": "#f9fafb",
    "gray-100": "#f3f4f6",
    "gray-200": "#e5e7eb",
    "gray-300": "#d1d5db",
    "gray-400": "#9ca3af",
    "gray-500": "#6b7280",
    "gray-600": "#4b5563",
    "gray-700": "#374151",
    "gray-800": "#1f2937",
    "gray-900": "#111827",
    "gray-950": "#030712",
    # Blues
    "blue-50": "#eff6ff",
    "blue-100": "#dbeafe",
    "blue-500": "#3b82f6",
    "blue-600": "#2563eb",
    "blue-700": "#1d4ed8",
    # Standard Tailwind blue-800 (not a named primitive but used in role tables)
    "blue-800": "#1e40af",
    # Greens
    "green-50": "#f0fdf4",
    "green-100": "#dcfce7",
    "green-500": "#22c55e",
    "green-600": "#16a34a",
    "green-800": "#166534",
    # Reds
    "red-50": "#fef2f2",
    "red-100": "#fee2e2",
    "red-500": "#ef4444",
    "red-600": "#dc2626",
    "red-700": "#b91c1c",
    "red-800": "#991b1b",
    # Yellows
    "yellow-50": "#fefce8",
    "yellow-100": "#fef9c3",
    "yellow-500": "#eab308",
    "yellow-600": "#ca8a04",
    "yellow-800": "#854d0e",
    # Purples
    "purple-50": "#faf5ff",
    "purple-100": "#f3e8ff",
    "purple-500": "#a855f7",
    "purple-600": "#9333ea",
    "purple-800": "#6b21a8",
    # White / misc
    "white": "#ffffff",
}

# ---------------------------------------------------------------------------
# Semantic status token definitions per theme (§5.1)
# ---------------------------------------------------------------------------

# Light-theme status colors: (bg_hex, text_hex)
_STATUS_LIGHT: dict[str, tuple[str, str]] = {
    "success": (_PRIMITIVES["green-100"], _PRIMITIVES["green-800"]),
    "warning": (_PRIMITIVES["yellow-100"], _PRIMITIVES["yellow-800"]),
    "error": (_PRIMITIVES["red-100"], _PRIMITIVES["red-800"]),
    "info": (_PRIMITIVES["blue-100"], _PRIMITIVES["blue-700"]),
    "neutral": (_PRIMITIVES["gray-100"], _PRIMITIVES["gray-700"]),
}

# Dark-theme status colors: (bg_rgba_tuple_or_hex, text_hex)
# bg is an rgba() value; we store as (r, g, b, alpha) for comparison
_STATUS_DARK_BG_RGBA: dict[str, tuple[int, int, int, float]] = {
    "success": (22, 163, 74, 0.2),
    "warning": (234, 179, 8, 0.2),
    "error": (239, 68, 68, 0.2),
    "info": (59, 130, 246, 0.2),
    "neutral": (31, 41, 55, 1.0),  # gray-800 solid
}

_STATUS_DARK_TEXT: dict[str, str] = {
    "success": _PRIMITIVES["green-500"],
    "warning": _PRIMITIVES["yellow-500"],
    "error": _PRIMITIVES["red-500"],
    "info": _PRIMITIVES["blue-500"],
    "neutral": _PRIMITIVES["gray-400"],
}

# ---------------------------------------------------------------------------
# Trust tier token definitions (§5.2)
# ---------------------------------------------------------------------------

_TRUST_TIER_LIGHT: dict[str, tuple[str, str]] = {
    "EXECUTE": (_PRIMITIVES["purple-100"], _PRIMITIVES["purple-800"]),
    "SUGGEST": (_PRIMITIVES["blue-100"], _PRIMITIVES["blue-800"]),
    "OBSERVE": (_PRIMITIVES["gray-100"], _PRIMITIVES["gray-700"]),
}

_TRUST_TIER_DARK_BG_RGBA: dict[str, tuple[int, int, int, float]] = {
    "EXECUTE": (168, 85, 247, 0.2),   # purple-500 / 20%
    "SUGGEST": (59, 130, 246, 0.2),   # blue-500 / 20%
    "OBSERVE": (31, 41, 55, 1.0),     # gray-800 solid
}

_TRUST_TIER_DARK_TEXT: dict[str, str] = {
    "EXECUTE": _PRIMITIVES["purple-500"],
    "SUGGEST": _PRIMITIVES["blue-500"],
    "OBSERVE": _PRIMITIVES["gray-400"],
}

# ---------------------------------------------------------------------------
# Role color definitions (§5.3)
# ---------------------------------------------------------------------------

_ROLE_LIGHT: dict[str, tuple[str, str]] = {
    "ADMIN": (_PRIMITIVES["red-100"], _PRIMITIVES["red-800"]),
    "OPERATOR": (_PRIMITIVES["yellow-100"], _PRIMITIVES["yellow-800"]),
    "OTHER": (_PRIMITIVES["blue-100"], _PRIMITIVES["blue-800"]),
}

_ROLE_DARK_BG_RGBA: dict[str, tuple[int, int, int, float]] = {
    "ADMIN": (239, 68, 68, 0.2),     # red-500/20
    "OPERATOR": (234, 179, 8, 0.2),  # yellow-500/20
    "OTHER": (59, 130, 246, 0.2),    # blue-500/20
}

_ROLE_DARK_TEXT: dict[str, str] = {
    "ADMIN": _PRIMITIVES["red-500"],
    "OPERATOR": _PRIMITIVES["yellow-500"],
    "OTHER": _PRIMITIVES["blue-500"],
}

# ---------------------------------------------------------------------------
# Button / interactive color definitions (§5.4)
# ---------------------------------------------------------------------------

_BUTTON_LIGHT: dict[str, dict[str, str]] = {
    "primary": {
        "bg": _PRIMITIVES["blue-600"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["blue-700"],
    },
    "secondary": {
        "bg": _PRIMITIVES["gray-600"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["gray-700"],
    },
    "destructive": {
        "bg": _PRIMITIVES["red-600"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["red-700"],
    },
    "ghost": {
        "bg": "transparent",
        "text": _PRIMITIVES["gray-600"],
        "hover_bg": _PRIMITIVES["gray-100"],
    },
}

_BUTTON_DARK: dict[str, dict[str, str]] = {
    "primary": {
        "bg": _PRIMITIVES["blue-500"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["blue-600"],
    },
    "secondary": {
        "bg": _PRIMITIVES["gray-500"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["gray-600"],
    },
    "destructive": {
        "bg": _PRIMITIVES["red-500"],
        "text": _PRIMITIVES["white"],
        "hover_bg": _PRIMITIVES["red-600"],
    },
    "ghost": {
        "bg": "transparent",
        "text": _PRIMITIVES["gray-400"],
        "hover_bg": _PRIMITIVES["gray-800"],
    },
}

# Focus ring primitives per theme (§4.2)
_FOCUS_RING_LIGHT = _PRIMITIVES["blue-600"]   # #2563eb
_FOCUS_RING_DARK = _PRIMITIVES["blue-500"]    # #3b82f6

# ---------------------------------------------------------------------------
# Colour parsing / comparison helpers
# ---------------------------------------------------------------------------

# Tolerance per channel for anti-aliasing / rendering differences
_COLOR_TOLERANCE = 5


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a ``#rrggbb`` hex string to an ``(r, g, b)`` tuple.

    Example::

        >>> hex_to_rgb("#dcfce7")
        (220, 252, 231)
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected 6-digit hex color, got: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def parse_css_color(css_value: str) -> tuple[int, int, int, float]:
    """Parse a CSS ``rgb()`` or ``rgba()`` computed-style string.

    Returns ``(r, g, b, alpha)`` where alpha is in ``[0.0, 1.0]``.

    Example::

        >>> parse_css_color("rgb(220, 252, 231)")
        (220, 252, 231, 1.0)
        >>> parse_css_color("rgba(22, 163, 74, 0.2)")
        (22, 163, 74, 0.2)
    """
    css_value = css_value.strip()

    rgba_match = re.match(
        r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)",
        css_value,
    )
    if rgba_match:
        r, g, b = int(rgba_match.group(1)), int(rgba_match.group(2)), int(rgba_match.group(3))
        a = float(rgba_match.group(4))
        return r, g, b, a

    rgb_match = re.match(
        r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        css_value,
    )
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return r, g, b, 1.0

    # Transparent keyword
    if css_value.lower() in ("transparent", "rgba(0, 0, 0, 0)"):
        return 0, 0, 0, 0.0

    raise ValueError(f"Cannot parse CSS color value: {css_value!r}")


def colors_close(
    actual_css: str,
    expected_hex: str,
    tolerance: int = _COLOR_TOLERANCE,
) -> bool:
    """Return True if ``actual_css`` is within ``tolerance`` of ``expected_hex``.

    Parses the computed ``rgb()``/``rgba()`` value from the browser and
    compares each channel against the target hex colour.  Ignores the alpha
    channel difference (solid vs transparent overlays will need separate
    handling via :func:`rgba_close`).

    Example::

        >>> colors_close("rgb(220, 252, 231)", "#dcfce7")
        True
    """
    ar, ag, ab, _ = parse_css_color(actual_css)
    er, eg, eb = hex_to_rgb(expected_hex)
    return (
        abs(ar - er) <= tolerance
        and abs(ag - eg) <= tolerance
        and abs(ab - eb) <= tolerance
    )


def rgba_close(
    actual_css: str,
    expected_rgba: tuple[int, int, int, float],
    tolerance: int = _COLOR_TOLERANCE,
    alpha_tolerance: float = 0.05,
) -> bool:
    """Return True if ``actual_css`` is within tolerance of ``expected_rgba``.

    Example::

        >>> rgba_close("rgba(22, 163, 74, 0.2)", (22, 163, 74, 0.2))
        True
    """
    ar, ag, ab, aa = parse_css_color(actual_css)
    er, eg, eb, ea = expected_rgba
    return (
        abs(ar - er) <= tolerance
        and abs(ag - eg) <= tolerance
        and abs(ab - eb) <= tolerance
        and abs(aa - ea) <= alpha_tolerance
    )


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

_GET_COMPUTED_BG_JS = """\
(selector) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    return window.getComputedStyle(el).backgroundColor;
}
"""

_GET_COMPUTED_COLOR_JS = """\
(selector) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    return window.getComputedStyle(el).color;
}
"""

_GET_COMPUTED_OUTLINE_JS = """\
(selector) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    const s = window.getComputedStyle(el);
    return s.outlineColor || s.getPropertyValue('--color-focus-ring');
}
"""

_GET_CSS_VAR_JS = """\
([selector, prop]) => {
    const el = selector ? document.querySelector(selector) : document.documentElement;
    if (!el) return null;
    return window.getComputedStyle(el).getPropertyValue(prop).trim();
}
"""

_SET_THEME_JS = """\
(theme) => {
    document.documentElement.setAttribute('data-theme', theme);
}
"""

_REMOVE_THEME_JS = """\
() => {
    document.documentElement.removeAttribute('data-theme');
}
"""


def get_background_color(page: Any, selector: str) -> str:
    """Return the computed ``backgroundColor`` for the first matching element.

    Example::

        color = get_background_color(page, ".badge-success")
    """
    result = page.evaluate(_GET_COMPUTED_BG_JS, selector)
    if result is None:
        raise AssertionError(f"No element found for selector: {selector!r}")
    return result


def get_text_color(page: Any, selector: str) -> str:
    """Return the computed ``color`` (text colour) for the first matching element.

    Example::

        color = get_text_color(page, ".badge-success")
    """
    result = page.evaluate(_GET_COMPUTED_COLOR_JS, selector)
    if result is None:
        raise AssertionError(f"No element found for selector: {selector!r}")
    return result


def get_css_variable(page: Any, prop: str, selector: str | None = None) -> str:
    """Return the computed value of a CSS custom property.

    If ``selector`` is given, resolves the variable in that element's context;
    otherwise resolves it on ``:root``.

    Example::

        ring = get_css_variable(page, "--color-focus-ring")
    """
    result = page.evaluate(_GET_CSS_VAR_JS, [selector, prop])
    if result is None:
        raise AssertionError(
            f"CSS variable {prop!r} not found"
            + (f" on {selector!r}" if selector else " on :root")
        )
    return result


def set_dark_theme(page: Any) -> None:
    """Set ``data-theme="dark"`` on ``<html>`` to activate the dark token set."""
    page.evaluate(_SET_THEME_JS, "dark")


def set_light_theme(page: Any) -> None:
    """Set ``data-theme="light"`` on ``<html>`` to activate the light token set."""
    page.evaluate(_SET_THEME_JS, "light")


def remove_theme_attr(page: Any) -> None:
    """Remove the ``data-theme`` attribute from ``<html>`` (restore browser default)."""
    page.evaluate(_REMOVE_THEME_JS)


# ---------------------------------------------------------------------------
# Public assertion functions
# ---------------------------------------------------------------------------


def assert_status_colors(
    page: Any,
    selector: str,
    status: str,
    *,
    dark: bool = False,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert that the element at ``selector`` uses the correct status colours.

    Validates **background** and **text** colours for one of the five status
    semantics — ``success``, ``warning``, ``error``, ``info``, ``neutral`` —
    against the style-guide token values defined in §5.1.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the status badge / element to inspect.
        status: One of ``"success"``, ``"warning"``, ``"error"``, ``"info"``,
            ``"neutral"``.
        dark: When ``True``, compare against dark-theme token values.
            Call :func:`set_dark_theme` on the page before asserting.
        tolerance: Per-channel RGB tolerance for rendering differences (default 5).

    Raises:
        AssertionError: If colours do not match within tolerance.

    Example::

        page.goto("/admin/ui/dashboard")
        assert_status_colors(page, "[data-status='success']", "success")

        set_dark_theme(page)
        assert_status_colors(page, "[data-status='success']", "success", dark=True)
    """
    valid = {"success", "warning", "error", "info", "neutral"}
    if status not in valid:
        raise ValueError(f"status must be one of {valid!r}, got {status!r}")

    actual_bg = get_background_color(page, selector)
    actual_text = get_text_color(page, selector)

    if dark:
        expected_bg_rgba = _STATUS_DARK_BG_RGBA[status]
        expected_text_hex = _STATUS_DARK_TEXT[status]

        if not rgba_close(actual_bg, expected_bg_rgba, tolerance):
            raise AssertionError(
                f"Status '{status}' background mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : rgba{expected_bg_rgba}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Status '{status}' text colour mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )
    else:
        expected_bg_hex, expected_text_hex = _STATUS_LIGHT[status]

        if not colors_close(actual_bg, expected_bg_hex, tolerance):
            raise AssertionError(
                f"Status '{status}' background mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : {expected_bg_hex!r}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Status '{status}' text colour mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )


def assert_all_status_colors(
    page: Any,
    selector_template: str,
    *,
    dark: bool = False,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert all 5 status colours at once using a selector template.

    The template must contain ``{status}`` which is replaced with each status
    name.  For example ``"[data-status='{status}']"``.

    Example::

        assert_all_status_colors(page, "[data-status='{status}']")
    """
    for status in ("success", "warning", "error", "info", "neutral"):
        sel = selector_template.format(status=status)
        assert_status_colors(page, sel, status, dark=dark, tolerance=tolerance)


def assert_trust_tier_colors(
    page: Any,
    selector: str,
    tier: str,
    *,
    dark: bool = False,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert background and text colours for a trust-tier badge (§5.2).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the tier badge / element.
        tier: One of ``"EXECUTE"``, ``"SUGGEST"``, ``"OBSERVE"`` (case-sensitive).
        dark: When ``True``, compare against dark-theme token values.
        tolerance: Per-channel RGB tolerance (default 5).

    Raises:
        AssertionError: If colours do not match within tolerance.

    Example::

        assert_trust_tier_colors(page, ".tier-badge", "EXECUTE")
        set_dark_theme(page)
        assert_trust_tier_colors(page, ".tier-badge", "EXECUTE", dark=True)
    """
    valid = {"EXECUTE", "SUGGEST", "OBSERVE"}
    if tier not in valid:
        raise ValueError(f"tier must be one of {valid!r}, got {tier!r}")

    actual_bg = get_background_color(page, selector)
    actual_text = get_text_color(page, selector)

    if dark:
        expected_bg_rgba = _TRUST_TIER_DARK_BG_RGBA[tier]
        expected_text_hex = _TRUST_TIER_DARK_TEXT[tier]

        if not rgba_close(actual_bg, expected_bg_rgba, tolerance):
            raise AssertionError(
                f"Trust tier '{tier}' background mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : rgba{expected_bg_rgba}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Trust tier '{tier}' text mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )
    else:
        expected_bg_hex, expected_text_hex = _TRUST_TIER_LIGHT[tier]

        if not colors_close(actual_bg, expected_bg_hex, tolerance):
            raise AssertionError(
                f"Trust tier '{tier}' background mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : {expected_bg_hex!r}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Trust tier '{tier}' text mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )


def assert_role_colors(
    page: Any,
    selector: str,
    role: str,
    *,
    dark: bool = False,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert background and text colours for a role badge (§5.3).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the role badge / element.
        role: One of ``"ADMIN"``, ``"OPERATOR"``, ``"OTHER"`` (case-sensitive).
        dark: When ``True``, compare against dark-theme token values.
        tolerance: Per-channel RGB tolerance (default 5).

    Raises:
        AssertionError: If colours do not match within tolerance.

    Example::

        assert_role_colors(page, ".user-role-badge", "ADMIN")
    """
    valid = {"ADMIN", "OPERATOR", "OTHER"}
    if role not in valid:
        raise ValueError(f"role must be one of {valid!r}, got {role!r}")

    actual_bg = get_background_color(page, selector)
    actual_text = get_text_color(page, selector)

    if dark:
        expected_bg_rgba = _ROLE_DARK_BG_RGBA[role]
        expected_text_hex = _ROLE_DARK_TEXT[role]

        if not rgba_close(actual_bg, expected_bg_rgba, tolerance):
            raise AssertionError(
                f"Role '{role}' background mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : rgba{expected_bg_rgba}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Role '{role}' text mismatch (dark theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )
    else:
        expected_bg_hex, expected_text_hex = _ROLE_LIGHT[role]

        if not colors_close(actual_bg, expected_bg_hex, tolerance):
            raise AssertionError(
                f"Role '{role}' background mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : {expected_bg_hex!r}"
            )
        if not colors_close(actual_text, expected_text_hex, tolerance):
            raise AssertionError(
                f"Role '{role}' text mismatch (light theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_text!r}\n"
                f"  expected : {expected_text_hex!r}"
            )


def assert_button_colors(
    page: Any,
    selector: str,
    variant: str,
    *,
    dark: bool = False,
    check_hover: bool = True,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert background, text, and optionally hover colours for a button (§5.4).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the button element.
        variant: One of ``"primary"``, ``"secondary"``, ``"destructive"``,
            ``"ghost"``.
        dark: When ``True``, compare against dark-theme token values.
        check_hover: When ``True`` (default), trigger a hover and check the
            hover background colour.
        tolerance: Per-channel RGB tolerance (default 5).

    Raises:
        AssertionError: If colours do not match within tolerance.

    Example::

        assert_button_colors(page, "button.btn-primary", "primary")
        assert_button_colors(page, "button.btn-destructive", "destructive",
                             dark=True, check_hover=False)
    """
    valid = {"primary", "secondary", "destructive", "ghost"}
    if variant not in valid:
        raise ValueError(f"variant must be one of {valid!r}, got {variant!r}")

    spec = _BUTTON_DARK[variant] if dark else _BUTTON_LIGHT[variant]

    actual_bg = get_background_color(page, selector)
    actual_text = get_text_color(page, selector)

    # Background — ghost buttons are transparent; skip solid comparison
    if spec["bg"] != "transparent":
        if not colors_close(actual_bg, spec["bg"], tolerance):
            theme = "dark" if dark else "light"
            raise AssertionError(
                f"Button '{variant}' background mismatch ({theme} theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {actual_bg!r}\n"
                f"  expected : {spec['bg']!r}"
            )

    # Text colour
    if not colors_close(actual_text, spec["text"], tolerance):
        theme = "dark" if dark else "light"
        raise AssertionError(
            f"Button '{variant}' text colour mismatch ({theme} theme).\n"
            f"  selector : {selector!r}\n"
            f"  actual   : {actual_text!r}\n"
            f"  expected : {spec['text']!r}"
        )

    # Hover state
    if check_hover:
        page.hover(selector)
        hover_bg = get_background_color(page, selector)
        if spec["hover_bg"] != "transparent" and not colors_close(hover_bg, spec["hover_bg"], tolerance):
            theme = "dark" if dark else "light"
            raise AssertionError(
                f"Button '{variant}' hover background mismatch ({theme} theme).\n"
                f"  selector : {selector!r}\n"
                f"  actual   : {hover_bg!r}\n"
                f"  expected : {spec['hover_bg']!r}"
            )


def assert_interactive_hover(
    page: Any,
    selector: str,
    *,
    expected_hover_bg: str | None = None,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert that hovering ``selector`` produces a visible background change.

    If ``expected_hover_bg`` (hex) is provided, validate the exact colour.
    Otherwise, just assert that the colour changed at all.

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the interactive element.
        expected_hover_bg: Optional hex colour expected after hover.
        tolerance: Per-channel RGB tolerance (default 5).

    Raises:
        AssertionError: If the hover colour does not change (or does not match).

    Example::

        assert_interactive_hover(page, "nav a.active", expected_hover_bg="#1f2937")
    """
    before_bg = get_background_color(page, selector)
    page.hover(selector)
    after_bg = get_background_color(page, selector)

    if expected_hover_bg is not None:
        if not colors_close(after_bg, expected_hover_bg, tolerance):
            raise AssertionError(
                f"Hover background mismatch.\n"
                f"  selector         : {selector!r}\n"
                f"  after hover      : {after_bg!r}\n"
                f"  expected         : {expected_hover_bg!r}"
            )
    else:
        # Parse both and check at least one channel changed meaningfully
        try:
            ar, ag, ab, _ = parse_css_color(after_bg)
            br, bg, bb, _ = parse_css_color(before_bg)
        except ValueError:
            return  # Cannot parse; skip check

        if (
            abs(ar - br) <= tolerance
            and abs(ag - bg) <= tolerance
            and abs(ab - bb) <= tolerance
        ):
            raise AssertionError(
                f"No background colour change detected on hover.\n"
                f"  selector  : {selector!r}\n"
                f"  before    : {before_bg!r}\n"
                f"  after     : {after_bg!r}"
            )


def assert_focus_ring_color(
    page: Any,
    selector: str,
    *,
    dark: bool = False,
    tolerance: int = _COLOR_TOLERANCE,
) -> None:
    """Assert that keyboard focus on ``selector`` shows the correct ring colour.

    Tabs to the element (via ``page.focus()``) and then reads the computed
    ``outlineColor`` to verify it matches the ``--color-focus-ring`` token
    (blue-600 in light theme, blue-500 in dark theme).

    Args:
        page: Playwright ``Page`` object.
        selector: CSS selector for the focusable element.
        dark: When ``True``, expect the dark-theme focus ring colour.
        tolerance: Per-channel RGB tolerance (default 5).

    Raises:
        AssertionError: If the focus ring colour does not match.

    Example::

        assert_focus_ring_color(page, "button.primary")
        set_dark_theme(page)
        assert_focus_ring_color(page, "button.primary", dark=True)
    """
    expected_hex = _FOCUS_RING_DARK if dark else _FOCUS_RING_LIGHT
    page.focus(selector)

    actual = page.evaluate(_GET_COMPUTED_OUTLINE_JS, selector)
    if actual is None:
        raise AssertionError(
            f"No element found for selector {selector!r} when checking focus ring."
        )

    if not colors_close(actual, expected_hex, tolerance):
        theme = "dark" if dark else "light"
        raise AssertionError(
            f"Focus ring colour mismatch ({theme} theme).\n"
            f"  selector : {selector!r}\n"
            f"  actual   : {actual!r}\n"
            f"  expected : {expected_hex!r}"
        )


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------------------

__all__ = [
    # Primitive / colour utilities
    "hex_to_rgb",
    "parse_css_color",
    "colors_close",
    "rgba_close",
    # Page interaction helpers
    "get_background_color",
    "get_text_color",
    "get_css_variable",
    "set_dark_theme",
    "set_light_theme",
    "remove_theme_attr",
    # Assertion functions
    "assert_status_colors",
    "assert_all_status_colors",
    "assert_trust_tier_colors",
    "assert_role_colors",
    "assert_button_colors",
    "assert_interactive_hover",
    "assert_focus_ring_color",
    # Token tables (for advanced consumers)
    "_PRIMITIVES",
    "_STATUS_LIGHT",
    "_STATUS_DARK_BG_RGBA",
    "_STATUS_DARK_TEXT",
    "_TRUST_TIER_LIGHT",
    "_TRUST_TIER_DARK_BG_RGBA",
    "_TRUST_TIER_DARK_TEXT",
    "_ROLE_LIGHT",
    "_ROLE_DARK_BG_RGBA",
    "_ROLE_DARK_TEXT",
    "_BUTTON_LIGHT",
    "_BUTTON_DARK",
    "_FOCUS_RING_LIGHT",
    "_FOCUS_RING_DARK",
]
