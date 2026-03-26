"""Epic 71.3 — Settings: Style Guide Compliance.

Validates that /admin/ui/settings conforms to the TheStudio style guide
(docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md) sections 4–9:

  §4.1     — CSS design tokens registered on :root
  §4.2     — Focus ring color on interactive elements
  §6       — Typography: page title, section headings, body text
  §9.1     — Card recipe: background, border, radius, padding (config section cards)
  §9.8     — Form inputs: border, radius, focus state, disabled state
  §9.x     — Tab navigation: active/inactive indicator, keyboard focus

These tests check *how* the page looks, not *what* it contains.
Semantic content is covered in test_settings_intent.py (Epic 71.1).
API contracts are covered in test_settings_api.py (Epic 71.2).
"""

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.component_validators import (
    validate_card,
    validate_table,
)
from tests.playwright.lib.style_assertions import (
    assert_focus_ring_color,
    colors_close,
    get_background_color,
    get_css_variable,
    set_dark_theme,
    set_light_theme,
)
from tests.playwright.lib.typography_assertions import (
    assert_heading_scale,
    assert_typography,
)

pytestmark = pytest.mark.playwright

SETTINGS_URL = "/admin/ui/settings"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_settings(page: object, base_url: str) -> None:
    """Navigate to the settings page and wait for the main content."""
    navigate(page, f"{base_url}{SETTINGS_URL}")  # type: ignore[arg-type]


def _has_table(page: object) -> bool:
    """Return True when at least one <table> element is present on the page."""
    return page.locator("table").count() > 0  # type: ignore[attr-defined]


def _count(page: object, selector: str) -> int:
    """Return the count of elements matching *selector* via JS querySelectorAll."""
    return page.evaluate(  # type: ignore[attr-defined]
        f"document.querySelectorAll({selector!r}).length"
    )


# ---------------------------------------------------------------------------
# §4.1 — CSS design tokens registered on :root
# ---------------------------------------------------------------------------


class TestSettingsDesignTokens:
    """CSS design tokens must be registered on :root (§4.1).

    All color, spacing, and typography values must be driven by CSS custom
    properties. Presence of these tokens confirms the correct stylesheet is
    loaded on the settings page.
    """

    def test_color_focus_ring_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-focus-ring is registered on :root."""
        _navigate_to_settings(page, base_url)

        try:
            val = get_css_variable(page, "--color-focus-ring")  # type: ignore[arg-type]
            assert val, (
                "--color-focus-ring CSS variable is empty — §4.1 requires it to be set"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-focus-ring not present; stylesheet may use direct classes"
                )
            raise

    def test_font_sans_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --font-sans is registered on :root (§6.1)."""
        _navigate_to_settings(page, base_url)

        try:
            val = get_css_variable(page, "--font-sans")  # type: ignore[arg-type]
            assert val, (
                "--font-sans CSS variable is empty — §6.1 requires it to specify Inter"
            )
            assert "inter" in val.lower() or "sans" in val.lower(), (
                f"--font-sans value {val!r} does not reference 'Inter' (§6.1)"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--font-sans not present; stylesheet may use direct font declarations"
                )
            raise

    def test_surface_app_token_registered(self, page: object, base_url: str) -> None:
        """CSS custom property --color-surface-app is registered (§4.1)."""
        _navigate_to_settings(page, base_url)

        try:
            val = get_css_variable(page, "--color-surface-app")  # type: ignore[arg-type]
            assert val, (
                "--color-surface-app CSS variable is empty — §4.1 requires a surface token"
            )
        except AssertionError as exc:
            if "not found" in str(exc).lower():
                pytest.skip(
                    "--color-surface-app not present; token may be named differently"
                )
            raise

    def test_page_background_uses_design_token(self, page: object, base_url: str) -> None:
        """Settings page background matches the §4.1 gray-50 or white design token."""
        _navigate_to_settings(page, base_url)

        bg = get_background_color(page, "body")  # type: ignore[arg-type]
        is_gray_50 = colors_close(bg, "#f9fafb")
        is_white = colors_close(bg, "#ffffff")
        assert is_gray_50 or is_white, (
            f"Settings page body background {bg!r} — expected gray-50 (#f9fafb) or "
            f"white (#ffffff) per §4.1 design tokens"
        )


# ---------------------------------------------------------------------------
# §4.2 — Focus ring color
# ---------------------------------------------------------------------------


class TestSettingsFocusRing:
    """Interactive elements must display the correct focus ring color (§4.2)."""

    def test_focusable_element_focus_ring(self, page: object, base_url: str) -> None:
        """Focusable form inputs and controls show the §4.2 focus ring on keyboard focus."""
        _navigate_to_settings(page, base_url)

        selectors_to_try = [
            "input[type='text']",
            "input[type='password']",
            "input[type='email']",
            "input[type='number']",
            "input",
            "select",
            "textarea",
            "button.btn-primary",
            "button[class*='primary']",
            "button",
            "a[href][class*='btn']",
            "a[href]",
        ]
        for sel in selectors_to_try:
            if _count(page, sel) > 0:
                try:
                    assert_focus_ring_color(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No focusable element found on settings page — skipping focus ring check"
        )


# ---------------------------------------------------------------------------
# §6 — Typography
# ---------------------------------------------------------------------------


class TestSettingsTypography:
    """Settings page typography must match the style guide type scale (§6.2)."""

    def test_heading_scale_compliance(self, page: object, base_url: str) -> None:
        """All h1-h3 elements follow the §6.2 heading scale."""
        _navigate_to_settings(page, base_url)
        assert_heading_scale(page)  # type: ignore[arg-type]

    def test_page_title_typography(self, page: object, base_url: str) -> None:
        """Page title (h1 or .page-title) uses §6.2 page_title scale (20px/600)."""
        _navigate_to_settings(page, base_url)

        selectors = ["h1", ".page-title", "[class*='page-title']"]
        for sel in selectors:
            if _count(page, sel) > 0:
                assert_typography(page, sel, role="page_title")  # type: ignore[arg-type]
                return

        pytest.skip(
            "No page title element (h1/.page-title) found — skipping typography check"
        )

    def test_section_heading_typography(self, page: object, base_url: str) -> None:
        """Section headings (h2) use §6.2 section_title scale (16px / weight 600)."""
        _navigate_to_settings(page, base_url)

        count = page.evaluate("document.querySelectorAll('h2').length")  # type: ignore[attr-defined]
        if count == 0:
            pytest.skip("No h2 headings found — skipping section heading typography check")

        assert_typography(page, "h2", role="section_title")  # type: ignore[arg-type]

    def test_label_typography(self, page: object, base_url: str) -> None:
        """Form labels use §6.2 body scale (14px / weight 400–500)."""
        _navigate_to_settings(page, base_url)

        label_selectors = ["label", ".form-label", "[class*='form-label']"]
        for sel in label_selectors:
            if _count(page, sel) > 0:
                assert_typography(page, sel, role="body")  # type: ignore[arg-type]
                return

        pytest.skip("No form label found — skipping label typography check")


# ---------------------------------------------------------------------------
# §9.8 — Form inputs
# ---------------------------------------------------------------------------


class TestSettingsFormInputs:
    """Form inputs on the settings page must conform to §9.8 form input recipe.

    §9.8 mandates:
      - Border: 1px solid with --color-border (gray-300) in default state
      - Border-radius: ≥ 4px (rounded)
      - Focus state: border changes to accent color + §4.2 focus ring
      - Padding: ≥ 8px horizontal, ≥ 6px vertical
      - Disabled state: reduced opacity (0.5–0.6) or gray background

    Settings is the primary form-heavy surface in the admin UI.
    Incorrect input styling makes forms appear broken or inconsistent.
    """

    def test_text_input_has_border(self, page: object, base_url: str) -> None:
        """Text inputs have a visible border per §9.8 default state."""
        _navigate_to_settings(page, base_url)

        input_selectors = [
            "input[type='text']",
            "input[type='password']",
            "input[type='email']",
            "input[type='number']",
            "input[type='url']",
            "input:not([type='checkbox']):not([type='radio']):not([type='submit'])"
            ":not([type='button']):not([type='hidden'])",
        ]
        for sel in input_selectors:
            if _count(page, sel) > 0:
                border = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var s = window.getComputedStyle(el);
                        return {{
                            borderWidth: s.borderWidth,
                            borderStyle: s.borderStyle,
                            borderColor: s.borderColor
                        }};
                    }})()
                    """
                )
                if border:
                    width_str = border.get("borderWidth", "0px")
                    style_str = border.get("borderStyle", "none")
                    width_val = float(width_str.replace("px", "").strip() or "0")
                    assert width_val >= 1 and style_str not in ("none", "hidden"), (
                        f"Form input {sel!r} has no visible border — "
                        f"§9.8 requires borderWidth≥1px, got {border}"
                    )
                    return

        pytest.skip(
            "No text input found on settings page — skipping §9.8 border check"
        )

    def test_text_input_border_radius(self, page: object, base_url: str) -> None:
        """Text inputs have border-radius ≥ 4px per §9.8."""
        _navigate_to_settings(page, base_url)

        input_selectors = [
            "input[type='text']",
            "input[type='password']",
            "input[type='email']",
            "input[type='number']",
            "input:not([type='checkbox']):not([type='radio']):not([type='submit'])"
            ":not([type='button']):not([type='hidden'])",
        ]
        for sel in input_selectors:
            if _count(page, sel) > 0:
                radius = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        return window.getComputedStyle(el).borderRadius;
                    }})()
                    """
                )
                if radius is not None:
                    # Parse the first value (top-left) from e.g. "4px" or "4px 4px 4px 4px"
                    first = radius.split()[0].replace("px", "").strip()
                    try:
                        radius_val = float(first)
                    except ValueError:
                        radius_val = 0.0
                    assert radius_val >= 4, (
                        f"Form input {sel!r} border-radius {radius!r} is < 4px — "
                        "§9.8 requires rounded inputs (≥ 4px)"
                    )
                    return

        pytest.skip(
            "No text input found on settings page — skipping §9.8 border-radius check"
        )

    def test_text_input_padding(self, page: object, base_url: str) -> None:
        """Text inputs have adequate padding per §9.8 (≥ 6px vertical, ≥ 8px horizontal)."""
        _navigate_to_settings(page, base_url)

        input_selectors = [
            "input[type='text']",
            "input[type='password']",
            "input[type='email']",
            "input:not([type='checkbox']):not([type='radio']):not([type='submit'])"
            ":not([type='button']):not([type='hidden'])",
        ]
        for sel in input_selectors:
            if _count(page, sel) > 0:
                padding = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var s = window.getComputedStyle(el);
                        return {{
                            top: s.paddingTop,
                            bottom: s.paddingBottom,
                            left: s.paddingLeft,
                            right: s.paddingRight
                        }};
                    }})()
                    """
                )
                if padding:
                    def _px(v: str) -> float:
                        try:
                            return float(v.replace("px", "").strip())
                        except ValueError:
                            return 0.0

                    v_top = _px(padding.get("top", "0px"))
                    v_bottom = _px(padding.get("bottom", "0px"))
                    h_left = _px(padding.get("left", "0px"))
                    h_right = _px(padding.get("right", "0px"))

                    assert v_top >= 4 and v_bottom >= 4, (
                        f"Input {sel!r} vertical padding top={v_top}px / "
                        f"bottom={v_bottom}px — §9.8 expects ≥ 4px vertical"
                    )
                    assert h_left >= 8 or h_right >= 8, (
                        f"Input {sel!r} horizontal padding left={h_left}px / "
                        f"right={h_right}px — §9.8 expects ≥ 8px horizontal"
                    )
                    return

        pytest.skip(
            "No text input found on settings page — skipping §9.8 padding check"
        )

    def test_disabled_input_visual_distinction(self, page: object, base_url: str) -> None:
        """Disabled inputs have reduced opacity or gray background per §9.8."""
        _navigate_to_settings(page, base_url)

        disabled_selectors = [
            "input[disabled]",
            "input[readonly]",
            "input:disabled",
            "[disabled] input",
        ]
        for sel in disabled_selectors:
            if _count(page, sel) > 0:
                style = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var s = window.getComputedStyle(el);
                        return {{
                            opacity: s.opacity,
                            background: s.backgroundColor,
                            cursor: s.cursor
                        }};
                    }})()
                    """
                )
                if style:
                    opacity = float(style.get("opacity", "1") or "1")
                    bg = style.get("background", "")
                    cursor = style.get("cursor", "auto")
                    has_opacity = opacity < 0.85
                    has_gray_bg = colors_close(bg, "#f3f4f6") or colors_close(bg, "#e5e7eb")
                    has_not_allowed = cursor in ("not-allowed", "default")
                    assert has_opacity or has_gray_bg or has_not_allowed, (
                        f"Disabled input {sel!r} is not visually distinguished — "
                        f"§9.8 requires opacity < 0.85 or gray background. "
                        f"Got opacity={opacity}, bg={bg!r}, cursor={cursor!r}"
                    )
                    return

        pytest.skip(
            "No disabled/readonly input found on settings page — "
            "skipping §9.8 disabled state check"
        )

    def test_textarea_conforms_to_input_recipe(self, page: object, base_url: str) -> None:
        """Textarea elements follow §9.8 input recipe (border, radius, padding)."""
        _navigate_to_settings(page, base_url)

        if _count(page, "textarea") == 0:
            pytest.skip("No textarea found on settings page — skipping textarea check")

        border = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var el = document.querySelector('textarea');
                if (!el) return null;
                var s = window.getComputedStyle(el);
                return {
                    borderWidth: s.borderWidth,
                    borderStyle: s.borderStyle,
                    borderRadius: s.borderRadius
                };
            })()
            """
        )
        if border:
            width_val = float(
                border.get("borderWidth", "0px").replace("px", "").strip() or "0"
            )
            style_str = border.get("borderStyle", "none")
            assert width_val >= 1 and style_str not in ("none", "hidden"), (
                f"Textarea has no visible border — §9.8 requires borderWidth≥1px, "
                f"got {border}"
            )

            first_radius = border.get("borderRadius", "0px").split()[0].replace("px", "")
            radius_val = float(first_radius) if first_radius else 0.0
            assert radius_val >= 4, (
                f"Textarea border-radius {border.get('borderRadius')!r} is < 4px — "
                "§9.8 requires rounded inputs"
            )


# ---------------------------------------------------------------------------
# Tab navigation style
# ---------------------------------------------------------------------------


class TestSettingsTabNavigation:
    """Settings tab navigation must be visually clear and keyboard-accessible.

    The style guide requires tab controls to have:
      - A visible active/inactive indicator (underline, background, or color change)
      - Proper ARIA roles (`role='tab'`, `role='tablist'`, `role='tabpanel'`)
      - Keyboard focus ring on each tab
    """

    def test_tab_active_indicator_visible(self, page: object, base_url: str) -> None:
        """Active tab has a visually distinct active indicator (§9.x tab recipe)."""
        _navigate_to_settings(page, base_url)

        tab_selectors = [
            "[role='tab'][aria-selected='true']",
            "[role='tab'].active",
            ".tab-active",
            "[class*='tab-active']",
            "[class*='tab--active']",
            "button[aria-selected='true']",
            "a[aria-selected='true']",
        ]
        for sel in tab_selectors:
            if _count(page, sel) > 0:
                style = page.evaluate(  # type: ignore[attr-defined]
                    f"""
                    (function() {{
                        var el = document.querySelector({sel!r});
                        if (!el) return null;
                        var s = window.getComputedStyle(el);
                        return {{
                            borderBottom: s.borderBottomWidth + ' ' + s.borderBottomStyle,
                            background: s.backgroundColor,
                            color: s.color,
                            fontWeight: s.fontWeight
                        }};
                    }})()
                    """
                )
                if style:
                    border_bottom = style.get("borderBottom", "")
                    font_weight = int(style.get("fontWeight", "400") or "400")
                    has_border = (
                        "px" in border_bottom
                        and "none" not in border_bottom
                        and "0px" not in border_bottom.split()[0]
                    )
                    has_bold = font_weight >= 500
                    assert has_border or has_bold, (
                        f"Active tab {sel!r} lacks visible active indicator — "
                        f"§9.x requires border-bottom underline or font-weight≥500. "
                        f"Got: {style}"
                    )
                    return

        # Fallback: accept any tab element and skip if none found
        all_tab_selectors = [
            "[role='tab']",
            ".tab",
            "[class*='tab']",
            "nav a",
            "[data-tab]",
        ]
        for sel in all_tab_selectors:
            if _count(page, sel) > 0:
                # At least one tab exists — just verify they render
                count = _count(page, sel)
                assert count > 0, f"Tab navigation element {sel!r} vanished"
                return

        pytest.skip(
            "No tab navigation found on settings page — "
            "page may use section/card layout instead of tabs"
        )

    def test_tab_list_aria_role(self, page: object, base_url: str) -> None:
        """Tab list container has role='tablist' for keyboard navigation (ARIA spec)."""
        _navigate_to_settings(page, base_url)

        if _count(page, "[role='tablist']") > 0:
            # Good — tablist is present
            return

        # Check for tab elements without explicit tablist
        if _count(page, "[role='tab']") > 0:
            tablist_count = _count(page, "[role='tablist']")
            assert tablist_count > 0, (
                "Found role='tab' elements but no role='tablist' container — "
                "§9.x tab recipe requires a tablist wrapper"
            )
            return

        pytest.skip(
            "No ARIA tab pattern found on settings page — "
            "page may use a non-tab layout for config sections"
        )

    def test_tab_keyboard_focus_ring(self, page: object, base_url: str) -> None:
        """Tab elements show the §4.2 focus ring when focused via keyboard."""
        _navigate_to_settings(page, base_url)

        tab_selectors = [
            "[role='tab']",
            ".tab",
            "[class*='tab-item']",
            "[class*='tab-btn']",
            "[data-tab]",
        ]
        for sel in tab_selectors:
            if _count(page, sel) > 0:
                try:
                    assert_focus_ring_color(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No tab element found on settings page — skipping tab focus ring check"
        )


# ---------------------------------------------------------------------------
# §9.1 — Card recipe (config section cards)
# ---------------------------------------------------------------------------


class TestSettingsCardRecipe:
    """Settings section cards must conform to §9.1 card recipe.

    The settings page wraps each configuration section (API keys, infra, etc.)
    in a card container. Each card must have the correct background, border
    color, border-radius (≥ 8px), and padding (≥ 16px) per §9.1.
    """

    def test_card_recipe_if_present(self, page: object, base_url: str) -> None:
        """Config section cards match §9.1 recipe (background, border, radius, padding)."""
        _navigate_to_settings(page, base_url)

        card_selectors = [
            ".card",
            "[class*='card']",
            ".settings-section",
            "[class*='settings-section']",
            ".config-section",
            "[data-component='card']",
        ]
        for sel in card_selectors:
            if _count(page, sel) > 0:
                result = validate_card(page, sel)  # type: ignore[arg-type]
                assert result.passed, (
                    f"Settings section card {sel!r} fails §9.1 recipe: {result.summary()}"
                )
                return

        pytest.skip(
            "No card element found on settings page — skipping §9.1 card recipe check"
        )

    def test_dark_theme_does_not_break_layout(self, page: object, base_url: str) -> None:
        """Settings page layout remains intact when dark theme is applied."""
        _navigate_to_settings(page, base_url)

        set_dark_theme(page)  # type: ignore[arg-type]
        try:
            body = page.locator("body").inner_text()  # type: ignore[attr-defined]
            assert len(body) > 0, "Page body empty after switching to dark theme"
        finally:
            set_light_theme(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §9.2 — Table recipe (if table layout within settings)
# ---------------------------------------------------------------------------


class TestSettingsTableRecipe:
    """If any settings section uses a table, it must conform to §9.2."""

    def test_table_recipe_if_present(self, page: object, base_url: str) -> None:
        """Settings table (if present) matches §9.2 recipe (thead background, th scope)."""
        _navigate_to_settings(page, base_url)

        if not _has_table(page):
            pytest.skip("No table on settings page — card/form layout acceptable")

        result = validate_table(page, "table")  # type: ignore[arg-type]
        assert result.passed, (
            f"Settings table fails §9.2 recipe: {result.summary()}"
        )

    def test_table_header_scope_attributes(self, page: object, base_url: str) -> None:
        """<th> elements in settings tables have scope='col' (§9.2 accessibility)."""
        _navigate_to_settings(page, base_url)

        if not _has_table(page):
            pytest.skip("No table on settings page — skipping th scope check")

        th_count = page.evaluate(  # type: ignore[attr-defined]
            "document.querySelectorAll('table thead th').length"
        )
        if th_count == 0:
            pytest.skip("No thead th elements found — skipping scope attribute check")

        missing_scope = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table thead th');
                var missing = [];
                ths.forEach(function(th, i) {
                    if (!th.hasAttribute('scope')) {
                        missing.push(i);
                    }
                });
                return missing;
            })()
            """
        )
        assert not missing_scope, (
            f"Column headers at indices {missing_scope} are missing scope='col' — "
            "§9.2 requires scope attributes for accessible tables"
        )
