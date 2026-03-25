"""Unit tests for tests/playwright/lib/style_assertions.py (Epic 58, Story 58.1).

These tests exercise the pure-Python helper functions (colour parsing,
comparison, and assertion logic) without requiring a live Playwright browser.

Run::

    pytest tests/playwright/test_lib_style_assertions.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from tests.playwright.lib.style_assertions import (
    _BUTTON_DARK,
    _BUTTON_LIGHT,
    _FOCUS_RING_DARK,
    _FOCUS_RING_LIGHT,
    _PRIMITIVES,
    _ROLE_DARK_BG_RGBA,
    _ROLE_DARK_TEXT,
    _ROLE_LIGHT,
    _STATUS_DARK_BG_RGBA,
    _STATUS_DARK_TEXT,
    _STATUS_LIGHT,
    _TRUST_TIER_DARK_BG_RGBA,
    _TRUST_TIER_DARK_TEXT,
    _TRUST_TIER_LIGHT,
    assert_button_colors,
    assert_focus_ring_color,
    assert_interactive_hover,
    assert_role_colors,
    assert_status_colors,
    assert_trust_tier_colors,
    colors_close,
    hex_to_rgb,
    parse_css_color,
    rgba_close,
)


# ---------------------------------------------------------------------------
# hex_to_rgb
# ---------------------------------------------------------------------------


class TestHexToRgb:
    def test_green_100(self):
        assert hex_to_rgb("#dcfce7") == (220, 252, 231)

    def test_blue_600(self):
        assert hex_to_rgb("#2563eb") == (37, 99, 235)

    def test_red_800(self):
        assert hex_to_rgb("#991b1b") == (153, 27, 27)

    def test_white(self):
        assert hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_strip_hash(self):
        assert hex_to_rgb("dcfce7") == (220, 252, 231)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            hex_to_rgb("#abc")

    def test_all_primitives_parseable(self):
        """All style-guide primitive tokens should parse without error."""
        for name, hex_val in _PRIMITIVES.items():
            if hex_val.startswith("#"):
                r, g, b = hex_to_rgb(hex_val)
                assert 0 <= r <= 255, f"{name}: r out of range"
                assert 0 <= g <= 255, f"{name}: g out of range"
                assert 0 <= b <= 255, f"{name}: b out of range"


# ---------------------------------------------------------------------------
# parse_css_color
# ---------------------------------------------------------------------------


class TestParseCssColor:
    def test_rgb(self):
        assert parse_css_color("rgb(220, 252, 231)") == (220, 252, 231, 1.0)

    def test_rgba(self):
        assert parse_css_color("rgba(22, 163, 74, 0.2)") == (22, 163, 74, 0.2)

    def test_rgba_full_opacity(self):
        assert parse_css_color("rgba(37, 99, 235, 1)") == (37, 99, 235, 1.0)

    def test_transparent_keyword(self):
        assert parse_css_color("transparent") == (0, 0, 0, 0.0)

    def test_transparent_rgba_zero(self):
        assert parse_css_color("rgba(0, 0, 0, 0)") == (0, 0, 0, 0.0)

    def test_whitespace_tolerant(self):
        assert parse_css_color("rgb( 220 , 252 , 231 )") == (220, 252, 231, 1.0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_css_color("#dcfce7")


# ---------------------------------------------------------------------------
# colors_close
# ---------------------------------------------------------------------------


class TestColorsClose:
    def test_exact_match(self):
        assert colors_close("rgb(220, 252, 231)", "#dcfce7") is True

    def test_within_tolerance(self):
        # actual (221, 252, 231) vs expected (220, 252, 231) — delta 1
        assert colors_close("rgb(221, 252, 231)", "#dcfce7", tolerance=5) is True

    def test_outside_tolerance(self):
        # actual (230, 252, 231) vs expected (220, 252, 231) — delta 10
        assert colors_close("rgb(230, 252, 231)", "#dcfce7", tolerance=5) is False

    def test_rgba_ignores_alpha(self):
        # rgba bg with solid colour comparison — alpha channel ignored
        assert colors_close("rgba(220, 252, 231, 0.5)", "#dcfce7") is True


# ---------------------------------------------------------------------------
# rgba_close
# ---------------------------------------------------------------------------


class TestRgbaClose:
    def test_exact_match(self):
        assert rgba_close("rgba(22, 163, 74, 0.2)", (22, 163, 74, 0.2)) is True

    def test_rgb_treated_as_alpha_1(self):
        assert rgba_close("rgb(22, 163, 74)", (22, 163, 74, 1.0)) is True

    def test_alpha_outside_tolerance(self):
        assert rgba_close("rgba(22, 163, 74, 0.5)", (22, 163, 74, 0.2), alpha_tolerance=0.05) is False

    def test_rgb_channel_mismatch(self):
        assert rgba_close("rgba(50, 163, 74, 0.2)", (22, 163, 74, 0.2), tolerance=5) is False


# ---------------------------------------------------------------------------
# assert_status_colors — light theme
# ---------------------------------------------------------------------------


def _make_page(bg_color: str, text_color: str) -> MagicMock:
    """Build a minimal mock page that returns fixed colors for evaluate()."""
    page = MagicMock()

    def evaluate_side_effect(script, selector):
        if "backgroundColor" in script:
            return bg_color
        if ".color" in script or "color;" in script:
            return text_color
        return None

    page.evaluate.side_effect = evaluate_side_effect
    return page


class TestAssertStatusColorsLight:
    def test_success_passes(self):
        bg, text = _STATUS_LIGHT["success"]
        bg_css = "rgb({},{},{})".format(*hex_to_rgb(bg))
        text_css = "rgb({},{},{})".format(*hex_to_rgb(text))
        page = _make_page(bg_css, text_css)
        # Should not raise
        assert_status_colors(page, ".badge", "success")

    def test_error_passes(self):
        bg, text = _STATUS_LIGHT["error"]
        bg_css = "rgb({},{},{})".format(*hex_to_rgb(bg))
        text_css = "rgb({},{},{})".format(*hex_to_rgb(text))
        page = _make_page(bg_css, text_css)
        assert_status_colors(page, ".badge", "error")

    def test_wrong_background_raises(self):
        # Use error text colour as background (wrong colour)
        bg, text = _STATUS_LIGHT["success"]
        bg_css = "rgb(200, 0, 0)"  # clearly wrong
        text_css = "rgb({},{},{})".format(*hex_to_rgb(text))
        page = _make_page(bg_css, text_css)
        with pytest.raises(AssertionError, match="background mismatch"):
            assert_status_colors(page, ".badge", "success")

    def test_all_statuses_pass(self):
        for status in ("success", "warning", "error", "info", "neutral"):
            bg, text = _STATUS_LIGHT[status]
            bg_css = "rgb({},{},{})".format(*hex_to_rgb(bg))
            text_css = "rgb({},{},{})".format(*hex_to_rgb(text))
            page = _make_page(bg_css, text_css)
            assert_status_colors(page, ".badge", status)  # no raise

    def test_invalid_status_raises_value_error(self):
        page = _make_page("rgb(0,0,0)", "rgb(0,0,0)")
        with pytest.raises(ValueError):
            assert_status_colors(page, ".badge", "unknown")


# ---------------------------------------------------------------------------
# assert_status_colors — dark theme
# ---------------------------------------------------------------------------


class TestAssertStatusColorsDark:
    def test_success_dark_passes(self):
        expected_rgba = _STATUS_DARK_BG_RGBA["success"]  # (22, 163, 74, 0.2)
        expected_text = _STATUS_DARK_TEXT["success"]
        bg_css = "rgba({},{},{},{})".format(*expected_rgba)
        text_css = "rgb({},{},{})".format(*hex_to_rgb(expected_text))
        page = _make_page(bg_css, text_css)
        assert_status_colors(page, ".badge", "success", dark=True)

    def test_neutral_dark_passes(self):
        expected_rgba = _STATUS_DARK_BG_RGBA["neutral"]  # gray-800 solid
        expected_text = _STATUS_DARK_TEXT["neutral"]
        bg_css = "rgba({},{},{},{})".format(*expected_rgba)
        text_css = "rgb({},{},{})".format(*hex_to_rgb(expected_text))
        page = _make_page(bg_css, text_css)
        assert_status_colors(page, ".badge", "neutral", dark=True)


# ---------------------------------------------------------------------------
# assert_trust_tier_colors
# ---------------------------------------------------------------------------


class TestAssertTrustTierColors:
    def test_execute_light(self):
        bg, text = _TRUST_TIER_LIGHT["EXECUTE"]
        page = _make_page(
            "rgb({},{},{})".format(*hex_to_rgb(bg)),
            "rgb({},{},{})".format(*hex_to_rgb(text)),
        )
        assert_trust_tier_colors(page, ".tier-badge", "EXECUTE")

    def test_observe_dark(self):
        expected_rgba = _TRUST_TIER_DARK_BG_RGBA["OBSERVE"]
        expected_text = _TRUST_TIER_DARK_TEXT["OBSERVE"]
        page = _make_page(
            "rgba({},{},{},{})".format(*expected_rgba),
            "rgb({},{},{})".format(*hex_to_rgb(expected_text)),
        )
        assert_trust_tier_colors(page, ".tier-badge", "OBSERVE", dark=True)

    def test_invalid_tier_raises(self):
        page = _make_page("rgb(0,0,0)", "rgb(0,0,0)")
        with pytest.raises(ValueError):
            assert_trust_tier_colors(page, ".tier-badge", "INVALID")


# ---------------------------------------------------------------------------
# assert_role_colors
# ---------------------------------------------------------------------------


class TestAssertRoleColors:
    def test_admin_light(self):
        bg, text = _ROLE_LIGHT["ADMIN"]
        page = _make_page(
            "rgb({},{},{})".format(*hex_to_rgb(bg)),
            "rgb({},{},{})".format(*hex_to_rgb(text)),
        )
        assert_role_colors(page, ".role-badge", "ADMIN")

    def test_operator_dark(self):
        expected_rgba = _ROLE_DARK_BG_RGBA["OPERATOR"]
        expected_text = _ROLE_DARK_TEXT["OPERATOR"]
        page = _make_page(
            "rgba({},{},{},{})".format(*expected_rgba),
            "rgb({},{},{})".format(*hex_to_rgb(expected_text)),
        )
        assert_role_colors(page, ".role-badge", "OPERATOR", dark=True)

    def test_invalid_role_raises(self):
        page = _make_page("rgb(0,0,0)", "rgb(0,0,0)")
        with pytest.raises(ValueError):
            assert_role_colors(page, ".role-badge", "SUPERUSER")


# ---------------------------------------------------------------------------
# assert_button_colors
# ---------------------------------------------------------------------------


class TestAssertButtonColors:
    def _make_button_page(
        self,
        bg: str,
        text: str,
        hover_bg: str | None = None,
    ) -> MagicMock:
        """Mock page that returns a fixed hover bg after page.hover() is called."""
        page = MagicMock()
        call_count = 0

        def evaluate_side_effect(script, selector):
            nonlocal call_count
            if "backgroundColor" in script:
                # 1st evaluate → pre-hover bg; 2nd (if any) → hover bg
                if call_count > 0 and hover_bg is not None:
                    return hover_bg
                call_count += 1
                return bg
            if ".color" in script or "color;" in script:
                return text
            return None

        page.evaluate.side_effect = evaluate_side_effect
        return page

    def test_primary_light_no_hover(self):
        spec = _BUTTON_LIGHT["primary"]
        bg_css = "rgb({},{},{})".format(*hex_to_rgb(spec["bg"]))
        text_css = "rgb({},{},{})".format(*hex_to_rgb(spec["text"]))
        page = self._make_button_page(bg_css, text_css)
        assert_button_colors(page, "button", "primary", check_hover=False)

    def test_destructive_dark_no_hover(self):
        spec = _BUTTON_DARK["destructive"]
        bg_css = "rgb({},{},{})".format(*hex_to_rgb(spec["bg"]))
        text_css = "rgb({},{},{})".format(*hex_to_rgb(spec["text"]))
        page = self._make_button_page(bg_css, text_css)
        assert_button_colors(page, "button", "destructive", dark=True, check_hover=False)

    def test_wrong_background_raises(self):
        spec = _BUTTON_LIGHT["primary"]
        text_css = "rgb({},{},{})".format(*hex_to_rgb(spec["text"]))
        page = self._make_button_page("rgb(0, 0, 0)", text_css)
        with pytest.raises(AssertionError, match="background mismatch"):
            assert_button_colors(page, "button", "primary", check_hover=False)

    def test_invalid_variant_raises(self):
        page = self._make_button_page("rgb(0,0,0)", "rgb(0,0,0)")
        with pytest.raises(ValueError):
            assert_button_colors(page, "button", "link")


# ---------------------------------------------------------------------------
# assert_interactive_hover
# ---------------------------------------------------------------------------


class TestAssertInteractiveHover:
    def _make_hover_page(self, before_bg: str, after_bg: str) -> MagicMock:
        page = MagicMock()
        hover_called = [False]

        def hover_side_effect(selector):
            hover_called[0] = True

        page.hover.side_effect = hover_side_effect

        def evaluate_side_effect(script, selector):
            if "backgroundColor" in script:
                return after_bg if hover_called[0] else before_bg
            return None

        page.evaluate.side_effect = evaluate_side_effect
        return page

    def test_color_changes(self):
        page = self._make_hover_page("rgb(255, 255, 255)", "rgb(31, 41, 55)")
        # Should not raise — colour changed
        assert_interactive_hover(page, "nav a")

    def test_no_change_raises(self):
        page = self._make_hover_page("rgb(255, 255, 255)", "rgb(255, 255, 255)")
        with pytest.raises(AssertionError, match="No background colour change"):
            assert_interactive_hover(page, "nav a")

    def test_expected_hover_bg_match(self):
        page = self._make_hover_page("rgb(255, 255, 255)", "rgb(31, 41, 55)")
        # Should not raise — hover bg is #1f2937 = (31, 41, 55)
        assert_interactive_hover(page, "nav a", expected_hover_bg="#1f2937")

    def test_expected_hover_bg_mismatch_raises(self):
        page = self._make_hover_page("rgb(255, 255, 255)", "rgb(200, 200, 200)")
        with pytest.raises(AssertionError, match="Hover background mismatch"):
            assert_interactive_hover(page, "nav a", expected_hover_bg="#1f2937")


# ---------------------------------------------------------------------------
# assert_focus_ring_color
# ---------------------------------------------------------------------------


class TestAssertFocusRingColor:
    def _make_focus_page(self, outline_color: str) -> MagicMock:
        page = MagicMock()

        def evaluate_side_effect(script, selector):
            if "outlineColor" in script:
                return outline_color
            return None

        page.evaluate.side_effect = evaluate_side_effect
        return page

    def test_light_focus_ring_passes(self):
        # _FOCUS_RING_LIGHT = #2563eb = (37, 99, 235)
        page = self._make_focus_page("rgb(37, 99, 235)")
        assert_focus_ring_color(page, "button")

    def test_dark_focus_ring_passes(self):
        # _FOCUS_RING_DARK = #3b82f6 = (59, 130, 246)
        page = self._make_focus_page("rgb(59, 130, 246)")
        assert_focus_ring_color(page, "button", dark=True)

    def test_wrong_focus_ring_raises(self):
        page = self._make_focus_page("rgb(200, 0, 0)")
        with pytest.raises(AssertionError, match="Focus ring colour mismatch"):
            assert_focus_ring_color(page, "button")

    def test_none_outline_raises(self):
        page = MagicMock()
        page.evaluate.return_value = None
        with pytest.raises(AssertionError, match="No element found"):
            assert_focus_ring_color(page, "button")


# ---------------------------------------------------------------------------
# Token table sanity checks
# ---------------------------------------------------------------------------


class TestTokenTableSanity:
    """Smoke-test the token tables for internal consistency."""

    def test_all_status_light_bg_are_valid_hex(self):
        for status, (bg, _) in _STATUS_LIGHT.items():
            r, g, b = hex_to_rgb(bg)
            assert 0 <= r <= 255, f"status={status}"

    def test_all_status_dark_text_are_valid_hex(self):
        for status, text in _STATUS_DARK_TEXT.items():
            r, g, b = hex_to_rgb(text)
            assert 0 <= r <= 255

    def test_all_trust_tier_keys_present(self):
        for tier in ("EXECUTE", "SUGGEST", "OBSERVE"):
            assert tier in _TRUST_TIER_LIGHT
            assert tier in _TRUST_TIER_DARK_BG_RGBA
            assert tier in _TRUST_TIER_DARK_TEXT

    def test_all_role_keys_present(self):
        for role in ("ADMIN", "OPERATOR", "OTHER"):
            assert role in _ROLE_LIGHT
            assert role in _ROLE_DARK_BG_RGBA
            assert role in _ROLE_DARK_TEXT

    def test_all_button_variants_present(self):
        for variant in ("primary", "secondary", "destructive", "ghost"):
            assert variant in _BUTTON_LIGHT
            assert variant in _BUTTON_DARK

    def test_focus_ring_hex_parseable(self):
        hex_to_rgb(_FOCUS_RING_LIGHT)
        hex_to_rgb(_FOCUS_RING_DARK)

    def test_dark_status_bg_rgba_tuples(self):
        for status, rgba in _STATUS_DARK_BG_RGBA.items():
            assert len(rgba) == 4, f"status={status}: expected 4-tuple"
            r, g, b, a = rgba
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255
            assert 0.0 <= a <= 1.0
