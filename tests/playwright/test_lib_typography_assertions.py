"""Unit tests for tests/playwright/lib/typography_assertions.py (Epic 58, Story 58.2).

These tests exercise the pure-Python helper functions and assertion logic
without requiring a live Playwright browser.  A ``MagicMock`` page simulates
``page.evaluate()`` responses so each scenario can be exercised in isolation.

Run::

    pytest tests/playwright/test_lib_typography_assertions.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.playwright.lib.typography_assertions import (
    _DENSITY_ROW_HEIGHTS,
    _FONT_FAMILY_MONO,
    _FONT_FAMILY_SANS,
    _KPI_SIZE_RANGE,
    _TYPE_SCALE,
    _em_to_float,
    _normalize_font_family,
    _px_to_float,
    _unitless_to_float,
    assert_density_mode,
    assert_font_family,
    assert_heading_scale,
    assert_spacing,
    assert_typography,
)


# ---------------------------------------------------------------------------
# Pure-Python unit helpers
# ---------------------------------------------------------------------------


class TestPxToFloat:
    def test_basic(self):
        assert _px_to_float("14px") == 14.0

    def test_float_value(self):
        assert _px_to_float("13.5px") == 13.5

    def test_whitespace(self):
        assert _px_to_float("  20px  ") == 20.0

    def test_zero(self):
        assert _px_to_float("0px") == 0.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _px_to_float("1em")


class TestUnitlessToFloat:
    def test_integer_string(self):
        assert _unitless_to_float("400") == 400.0

    def test_decimal_string(self):
        assert _unitless_to_float("1.5") == 1.5

    def test_whitespace(self):
        assert _unitless_to_float("  600  ") == 600.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _unitless_to_float("abc")


class TestEmToFloat:
    def test_normal_returns_none(self):
        assert _em_to_float("normal") is None

    def test_em_value(self):
        assert _em_to_float("0.05em") == pytest.approx(0.05, abs=1e-6)

    def test_negative_em(self):
        assert _em_to_float("-0.01em") == pytest.approx(-0.01, abs=1e-6)

    def test_zero(self):
        assert _em_to_float("0") == 0.0

    def test_normal_caps(self):
        # Case-insensitive
        assert _em_to_float("NORMAL") is None


class TestNormalizeFontFamily:
    def test_single_quoted(self):
        assert _normalize_font_family("'Inter', system-ui") == "Inter"

    def test_double_quoted(self):
        assert _normalize_font_family('"JetBrains Mono", monospace') == "JetBrains Mono"

    def test_no_quotes(self):
        assert _normalize_font_family("Arial, sans-serif") == "Arial"

    def test_single_value(self):
        assert _normalize_font_family("Roboto") == "Roboto"


# ---------------------------------------------------------------------------
# Type scale constants
# ---------------------------------------------------------------------------


class TestTypeScale:
    def test_all_roles_present(self):
        expected_roles = {
            "page_title", "section_title", "subsection", "label",
            "body", "caption", "kpi", "code",
        }
        assert set(_TYPE_SCALE.keys()) == expected_roles

    def test_page_title_spec(self):
        size, weight, lh, tracking = _TYPE_SCALE["page_title"]
        assert size == 20.0
        assert weight == 600
        assert lh == pytest.approx(1.4)
        assert tracking is None

    def test_label_has_tracking(self):
        _size, _weight, _lh, tracking = _TYPE_SCALE["label"]
        assert tracking == pytest.approx(0.05)

    def test_kpi_bold(self):
        _size, weight, lh, tracking = _TYPE_SCALE["kpi"]
        assert weight == 700
        assert lh == pytest.approx(1.2)
        assert tracking == pytest.approx(-0.01)

    def test_kpi_size_range(self):
        lo, hi = _KPI_SIZE_RANGE
        assert lo == 24.0
        assert hi == 30.0

    def test_font_family_constants(self):
        assert _FONT_FAMILY_SANS == "Inter"
        assert _FONT_FAMILY_MONO == "JetBrains Mono"


# ---------------------------------------------------------------------------
# Density mode constants
# ---------------------------------------------------------------------------


class TestDensityConstants:
    def test_compact(self):
        assert _DENSITY_ROW_HEIGHTS["compact"] == 32

    def test_comfortable(self):
        assert _DENSITY_ROW_HEIGHTS["comfortable"] == 40

    def test_spacious(self):
        assert _DENSITY_ROW_HEIGHTS["spacious"] == 48


# ---------------------------------------------------------------------------
# assert_typography
# ---------------------------------------------------------------------------


def _make_page(evaluate_side_effects: list) -> MagicMock:
    """Build a mock page whose ``evaluate`` calls return successive values."""
    page = MagicMock()
    page.evaluate.side_effect = evaluate_side_effects
    return page


class TestAssertTypography:
    """Mock-based tests: simulate page.evaluate() for getComputedStyle calls."""

    def _mock_page(self, font_size, font_weight, line_height, letter_spacing="normal"):
        """Returns a page mock that responds to _get_computed_style calls.

        _get_computed_style is called once per property via page.evaluate().
        """
        page = MagicMock()
        # side_effect list is consumed in order: fontSize, fontWeight,
        # lineHeight, then letterSpacing (if role has tracking)
        page.evaluate.side_effect = [
            font_size,
            font_weight,
            line_height,
            letter_spacing,
        ]
        return page

    def test_body_correct(self):
        page = self._mock_page("14px", "400", "21px")  # 21/14 ≈ 1.5
        assert_typography(page, "p", role="body")  # should not raise

    def test_page_title_correct(self):
        page = self._mock_page("20px", "600", "28px")  # 28/20 = 1.4
        assert_typography(page, "h1", role="page_title")

    def test_label_with_correct_tracking(self):
        page = self._mock_page("12px", "600", "18px", "0.05em")  # 18/12 = 1.5
        assert_typography(page, "label", role="label")

    def test_kpi_within_range(self):
        page = self._mock_page("24px", "700", "28.8px", "-0.01em")  # 28.8/24 = 1.2
        assert_typography(page, ".kpi", role="kpi")

    def test_kpi_upper_bound(self):
        page = self._mock_page("30px", "700", "36px", "-0.01em")  # 36/30 = 1.2
        assert_typography(page, ".kpi-xl", role="kpi")

    def test_wrong_font_size_raises(self):
        page = self._mock_page("12px", "400", "18px")
        with pytest.raises(AssertionError, match="font-size"):
            assert_typography(page, "p", role="body")

    def test_wrong_weight_raises(self):
        # section_title expects 16px/600 — give correct size but wrong weight
        page = self._mock_page("16px", "400", "24px")
        with pytest.raises(AssertionError, match="font-weight"):
            assert_typography(page, "p", role="section_title")

    def test_wrong_role_raises(self):
        page = MagicMock()
        with pytest.raises(AssertionError, match="Unknown type role"):
            assert_typography(page, "p", role="invalid_role")  # type: ignore[arg-type]

    def test_element_not_found_raises(self):
        page = MagicMock()
        page.evaluate.return_value = None
        with pytest.raises(AssertionError, match="No element"):
            assert_typography(page, "#missing", role="body")

    def test_code_role(self):
        page = self._mock_page("13px", "400", "19.5px")  # 19.5/13 = 1.5
        assert_typography(page, "code", role="code")

    def test_caption_role(self):
        page = self._mock_page("12px", "400", "18px")  # 18/12 = 1.5
        assert_typography(page, "small", role="caption")

    def test_subsection_role(self):
        page = self._mock_page("14px", "600", "21px")  # 21/14 = 1.5
        assert_typography(page, "h3", role="subsection")


# ---------------------------------------------------------------------------
# assert_heading_scale
# ---------------------------------------------------------------------------


class TestAssertHeadingScale:
    def _make_heading_page(self, h1_info, h2_info, h3_info) -> MagicMock:
        """Simulate evaluate() calls for assert_heading_scale.

        Call order per heading level:
          1. querySelectorAll(...).length  → int
          2. Array.from(...).map(...)       → list of {fontSize, fontWeight, text}
        """
        page = MagicMock()
        calls = []
        for info_list in (h1_info, h2_info, h3_info):
            calls.append(len(info_list))  # count
            if info_list:
                calls.append(info_list)   # elements info
        page.evaluate.side_effect = calls
        return page

    def test_all_correct(self):
        h1 = [{"fontSize": "20px", "fontWeight": "600", "text": "Dashboard"}]
        h2 = [{"fontSize": "16px", "fontWeight": "600", "text": "Section"}]
        h3 = [{"fontSize": "14px", "fontWeight": "600", "text": "Sub"}]
        page = self._make_heading_page(h1, h2, h3)
        assert_heading_scale(page)  # should not raise

    def test_h1_wrong_size_raises(self):
        h1 = [{"fontSize": "18px", "fontWeight": "600", "text": "Dashboard"}]
        h2 = []
        h3 = []
        page = self._make_heading_page(h1, h2, h3)
        with pytest.raises(AssertionError, match="font-size"):
            assert_heading_scale(page)

    def test_h2_wrong_weight_raises(self):
        h1 = []
        h2 = [{"fontSize": "16px", "fontWeight": "400", "text": "Section"}]
        h3 = []
        page = self._make_heading_page(h1, h2, h3)
        with pytest.raises(AssertionError, match="font-weight"):
            assert_heading_scale(page)

    def test_missing_headings_skipped(self):
        """All heading levels absent — no error should be raised."""
        page = MagicMock()
        page.evaluate.side_effect = [0, 0, 0]  # all counts = 0
        assert_heading_scale(page)  # no assertion


# ---------------------------------------------------------------------------
# assert_font_family
# ---------------------------------------------------------------------------


class TestAssertFontFamily:
    def _make_page(self, font_family_value: str) -> MagicMock:
        page = MagicMock()
        page.evaluate.return_value = font_family_value
        return page

    def test_sans_inter(self):
        page = self._make_page("'Inter', system-ui, sans-serif")
        assert_font_family(page, "p", expected="sans")

    def test_mono_jetbrains(self):
        page = self._make_page("'JetBrains Mono', monospace")
        assert_font_family(page, "code", expected="mono")

    def test_sans_wrong_raises(self):
        page = self._make_page("'Roboto', system-ui")
        with pytest.raises(AssertionError, match="font-family"):
            assert_font_family(page, "p", expected="sans")

    def test_mono_wrong_raises(self):
        page = self._make_page("'Courier New', monospace")
        with pytest.raises(AssertionError, match="font-family"):
            assert_font_family(page, "code", expected="mono")

    def test_invalid_expected_raises(self):
        page = MagicMock()
        with pytest.raises(AssertionError):
            assert_font_family(page, "p", expected="serif")  # type: ignore[arg-type]

    def test_not_found_raises(self):
        page = MagicMock()
        page.evaluate.return_value = None
        with pytest.raises(AssertionError, match="No element"):
            assert_font_family(page, "#missing", expected="sans")


# ---------------------------------------------------------------------------
# assert_spacing
# ---------------------------------------------------------------------------


class TestAssertSpacing:
    def _make_page(self, value: str) -> MagicMock:
        page = MagicMock()
        page.evaluate.return_value = value
        return page

    def test_padding_16(self):
        page = self._make_page("16px")
        assert_spacing(page, ".card", "padding", 16)

    def test_gap_24(self):
        page = self._make_page("24px")
        assert_spacing(page, ".grid", "gap", 24)

    def test_margin_top_8(self):
        page = self._make_page("8px")
        assert_spacing(page, "section", "margin-top", 8)

    def test_non_multiple_of_4_raises(self):
        with pytest.raises(AssertionError, match="not a multiple of 4"):
            assert_spacing(MagicMock(), ".bad", "padding", 10)

    def test_wrong_value_raises(self):
        page = self._make_page("12px")
        with pytest.raises(AssertionError, match="padding"):
            assert_spacing(page, ".card", "padding", 16)

    def test_element_not_found_raises(self):
        page = MagicMock()
        page.evaluate.return_value = None
        with pytest.raises(AssertionError, match="No element"):
            assert_spacing(page, "#missing", "padding", 16)

    def test_valid_4px_grid_values(self):
        """All values in §7.1 are multiples of 4."""
        for val in [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]:
            page = self._make_page(f"{val}px")
            assert_spacing(page, "div", "padding", val)  # must not raise


# ---------------------------------------------------------------------------
# assert_density_mode
# ---------------------------------------------------------------------------


class TestAssertDensityMode:
    def _make_page(self, height: float) -> MagicMock:
        page = MagicMock()
        page.evaluate.return_value = height
        return page

    def test_compact_32(self):
        page = self._make_page(32.0)
        assert_density_mode(page, "tr", mode="compact")

    def test_comfortable_40(self):
        page = self._make_page(40.0)
        assert_density_mode(page, "tr", mode="comfortable")

    def test_spacious_48(self):
        page = self._make_page(48.0)
        assert_density_mode(page, ".wizard-row", mode="spacious")

    def test_spacious_large(self):
        page = self._make_page(60.0)
        assert_density_mode(page, ".wizard-row", mode="spacious")

    def test_spacious_below_min_raises(self):
        page = self._make_page(40.0)
        with pytest.raises(AssertionError, match="spacious"):
            assert_density_mode(page, "div", mode="spacious")

    def test_compact_wrong_height_raises(self):
        page = self._make_page(40.0)
        with pytest.raises(AssertionError, match="compact"):
            assert_density_mode(page, "tr", mode="compact")

    def test_element_not_found_raises(self):
        page = MagicMock()
        page.evaluate.return_value = None
        with pytest.raises(AssertionError, match="No element"):
            assert_density_mode(page, "#missing", mode="compact")

    def test_invalid_mode_raises(self):
        with pytest.raises(AssertionError, match="Unknown density mode"):
            assert_density_mode(MagicMock(), "tr", mode="ultra")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Import and export verification
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_importable_from_lib(self):
        from tests.playwright.lib import typography_assertions as ta
        assert hasattr(ta, "assert_typography")
        assert hasattr(ta, "assert_heading_scale")
        assert hasattr(ta, "assert_font_family")
        assert hasattr(ta, "assert_spacing")
        assert hasattr(ta, "assert_density_mode")

    def test_lib_init_exports(self):
        import tests.playwright.lib as lib
        assert "typography_assertions" in lib.__all__
