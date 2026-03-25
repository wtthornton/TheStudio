"""Unit tests for component_validators.py (Epic 58, Story 58.3).

Tests use ``unittest.mock.MagicMock`` to simulate Playwright ``Page`` objects
so they run without a browser — matching the pattern from the 58.1 and 58.2
test suites.

Each validator is tested with:
- A *passing* scenario (all checks succeed).
- A *failing* scenario (one or more checks fail).
- Edge cases (element not found, missing attributes, etc.).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.playwright.lib.component_validators import (
    AlertVariant,
    ButtonVariant,
    ValidationResult,
    validate_alert,
    validate_badge,
    validate_button,
    validate_card,
    validate_empty_state,
    validate_form_input,
    validate_modal,
    validate_table,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(**kwargs: object) -> MagicMock:
    """Return a MagicMock page where ``evaluate`` returns provided values.

    *kwargs* map ``(js_snippet_substring, args_key)`` → return value, but
    the simpler approach is to supply ``evaluate`` as a side_effect list in
    order of calls.  Each test sets up the list itself.
    """
    page = MagicMock()
    return page


def _seq_evaluate(page: MagicMock, *values: object) -> None:
    """Set page.evaluate to return *values* in sequence."""
    page.evaluate.side_effect = list(values)


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_passed_when_no_fail_details(self) -> None:
        r = ValidationResult(component="test")
        r.details = ["OK: a", "OK: b"]
        assert r.passed is True

    def test_failed_when_any_fail_detail(self) -> None:
        r = ValidationResult(component="test")
        r.details = ["OK: a", "FAIL: something wrong"]
        assert r.passed is False

    def test_summary_pass(self) -> None:
        r = ValidationResult(component="card(#x)")
        r.details = ["OK: border", "OK: radius"]
        assert "[PASS]" in r.summary()
        assert "card(#x)" in r.summary()

    def test_summary_fail_includes_failures(self) -> None:
        r = ValidationResult(component="card(#x)")
        r.details = ["OK: border", "FAIL: radius too small"]
        summary = r.summary()
        assert "[FAIL]" in summary
        assert "radius too small" in summary


# ---------------------------------------------------------------------------
# 1. validate_card
# ---------------------------------------------------------------------------


class TestValidateCard:
    """Tests for validate_card (§9.1)."""

    def _page_for_card(
        self,
        bg: str = "rgb(255, 255, 255)",
        border: str = "rgb(229, 231, 235)",
        radius: str = "8px",
        padding: str = "16px",
    ) -> MagicMock:
        page = _make_page()
        # evaluate() is called by _prop() 4 times: bg, border, radius, padding
        _seq_evaluate(page, bg, border, radius, padding)
        return page

    def test_passes_light_card(self) -> None:
        page = self._page_for_card()
        result = validate_card(page, ".card")
        assert result.passed, result.summary()
        assert all(d.startswith("OK:") for d in result.details)

    def test_fails_wrong_background(self) -> None:
        page = self._page_for_card(bg="rgb(0, 0, 0)")
        result = validate_card(page, ".card")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("background" in d for d in fail_lines)

    def test_fails_insufficient_radius(self) -> None:
        page = self._page_for_card(radius="4px")
        result = validate_card(page, ".card")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("borderRadius" in d for d in fail_lines)

    def test_fails_insufficient_padding(self) -> None:
        page = self._page_for_card(padding="8px")
        result = validate_card(page, ".card")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("padding" in d.lower() for d in fail_lines)

    def test_passes_dark_card(self) -> None:
        page = _make_page()
        _seq_evaluate(
            page,
            "rgb(17, 24, 39)",   # bg-gray-900
            "rgb(55, 65, 81)",   # border-gray-700
            "8px",
            "24px",
        )
        result = validate_card(page, ".card", dark=True)
        assert result.passed, result.summary()

    def test_card_component_name_in_result(self) -> None:
        page = self._page_for_card()
        result = validate_card(page, ".my-card")
        assert ".my-card" in result.component


# ---------------------------------------------------------------------------
# 2. validate_table
# ---------------------------------------------------------------------------


class TestValidateTable:
    def _page_for_table(
        self,
        header_bg: str = "rgb(249, 250, 251)",
        scope_info: dict | None = None,
        mono_count: int = 1,
    ) -> MagicMock:
        page = _make_page()
        if scope_info is None:
            scope_info = {"total": 3, "missing": 0}
        _seq_evaluate(page, header_bg, scope_info, mono_count)
        return page

    def test_passes_well_formed_table(self) -> None:
        page = self._page_for_table()
        result = validate_table(page, "table")
        assert result.passed, result.summary()

    def test_fails_missing_scope_col(self) -> None:
        page = self._page_for_table(scope_info={"total": 3, "missing": 2})
        result = validate_table(page, "table")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("scope" in d for d in fail_lines)

    def test_fails_no_th_elements(self) -> None:
        page = self._page_for_table(scope_info={"total": 0, "missing": 0})
        result = validate_table(page, "table")
        assert not result.passed

    def test_passes_dark_table(self) -> None:
        page = _make_page()
        _seq_evaluate(
            page,
            "rgb(31, 41, 55)",          # bg-gray-800
            {"total": 2, "missing": 0},
            0,
        )
        result = validate_table(page, "table", dark=True)
        assert result.passed, result.summary()

    def test_fails_wrong_header_bg(self) -> None:
        page = self._page_for_table(header_bg="rgb(255, 0, 0)")
        result = validate_table(page, "table")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("background" in d for d in fail_lines)

    def test_no_numeric_columns_is_acceptable(self) -> None:
        page = self._page_for_table(mono_count=0)
        result = validate_table(page, "table")
        # Missing numeric columns is not a failure
        assert not any("FAIL:" in d and "numeric" in d for d in result.details)


# ---------------------------------------------------------------------------
# 3. validate_badge
# ---------------------------------------------------------------------------


class TestValidateBadge:
    def _page_for_badge(
        self,
        padding_left: str = "8px",
        padding_top: str = "2px",
        radius: str = "4px",
        font_size: str = "12px",
        font_weight: str = "600",
    ) -> MagicMock:
        page = _make_page()
        _seq_evaluate(page, padding_left, padding_top, radius, font_size, font_weight)
        return page

    def test_passes_valid_badge(self) -> None:
        page = self._page_for_badge()
        result = validate_badge(page, ".badge")
        assert result.passed, result.summary()

    def test_fails_padding_too_small(self) -> None:
        page = self._page_for_badge(padding_left="4px")
        result = validate_badge(page, ".badge")
        assert not result.passed
        assert any("paddingLeft" in d for d in result.details if d.startswith("FAIL:"))

    def test_fails_no_border_radius(self) -> None:
        page = self._page_for_badge(radius="0px")
        result = validate_badge(page, ".badge")
        assert not result.passed

    def test_fails_font_size_too_large(self) -> None:
        page = self._page_for_badge(font_size="14px")
        result = validate_badge(page, ".badge")
        assert not result.passed
        assert any("fontSize" in d for d in result.details if d.startswith("FAIL:"))

    def test_fails_font_weight_too_light(self) -> None:
        page = self._page_for_badge(font_weight="400")
        result = validate_badge(page, ".badge")
        assert not result.passed
        assert any("fontWeight" in d for d in result.details if d.startswith("FAIL:"))

    def test_passes_large_semibold_badge(self) -> None:
        page = self._page_for_badge(
            padding_left="10px", padding_top="4px", radius="9999px",
            font_size="11px", font_weight="700",
        )
        result = validate_badge(page, ".badge")
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# 4. validate_button
# ---------------------------------------------------------------------------


class TestValidateButton:
    def _page_for_button(
        self,
        radius: str = "6px",
        padding_left: str = "12px",
        padding_top: str = "8px",
        font_size: str = "14px",
        font_weight: str = "500",
        rect: dict | None = None,
    ) -> MagicMock:
        page = _make_page()
        if rect is None:
            rect = {"width": 120.0, "height": 36.0}
        _seq_evaluate(page, radius, padding_left, padding_top, font_size, font_weight, rect)
        return page

    def test_passes_primary_button(self) -> None:
        page = self._page_for_button()
        result = validate_button(page, "button", "primary")
        assert result.passed, result.summary()

    def test_fails_touch_target_too_small(self) -> None:
        page = self._page_for_button(rect={"width": 20.0, "height": 18.0})
        result = validate_button(page, "button")
        assert not result.passed
        assert any("touch target" in d for d in result.details if d.startswith("FAIL:"))

    def test_fails_border_radius_too_small(self) -> None:
        page = self._page_for_button(radius="2px")
        result = validate_button(page, "button")
        assert not result.passed

    def test_fails_font_size_too_large(self) -> None:
        page = self._page_for_button(font_size="16px")
        result = validate_button(page, "button")
        assert not result.passed

    def test_icon_button_uses_p2_padding(self) -> None:
        page = _make_page()
        # icon button: radius, padding_left, font_size, font_weight, rect (no padding_top check)
        _seq_evaluate(page, "6px", "8px", "8px", "14px", "500", {"width": 32.0, "height": 32.0})
        result = validate_button(page, "button", "icon")
        assert result.passed, result.summary()

    def test_element_not_found_returns_fail(self) -> None:
        page = _make_page()
        _seq_evaluate(page, "6px", "12px", "8px", "14px", "500", None)
        result = validate_button(page, "#nonexistent")
        assert not result.passed
        assert any("not found" in d for d in result.details if d.startswith("FAIL:"))

    @pytest.mark.parametrize("variant", ["primary", "secondary", "destructive", "ghost"])
    def test_all_variants_accepted(self, variant: ButtonVariant) -> None:
        page = self._page_for_button()
        result = validate_button(page, "button", variant)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# 5. validate_form_input
# ---------------------------------------------------------------------------


class TestValidateFormInput:
    def _page_for_input(
        self,
        label_assoc: str = "for-id",
        border_style: str = "solid",
        aria_describedby: str | None = "help-text",
    ) -> MagicMock:
        page = _make_page()
        _seq_evaluate(page, label_assoc, border_style, aria_describedby)
        return page

    def test_passes_well_labelled_input(self) -> None:
        page = self._page_for_input()
        result = validate_form_input(page, "input")
        assert result.passed, result.summary()

    def test_passes_wrapped_label(self) -> None:
        page = self._page_for_input(label_assoc="wrapped")
        result = validate_form_input(page, "input")
        assert result.passed, result.summary()

    def test_fails_no_label(self) -> None:
        page = self._page_for_input(label_assoc="none")
        result = validate_form_input(page, "input")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("label" in d for d in fail_lines)

    def test_fails_no_border(self) -> None:
        page = self._page_for_input(border_style="none")
        result = validate_form_input(page, "input")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("border" in d for d in fail_lines)

    def test_no_aria_describedby_is_not_failure(self) -> None:
        page = self._page_for_input(aria_describedby=None)
        result = validate_form_input(page, "input")
        # Not having aria-describedby is a warning, not a hard failure
        assert result.passed, result.summary()

    def test_element_missing_fails(self) -> None:
        page = self._page_for_input(label_assoc="missing")
        result = validate_form_input(page, "#nope")
        assert not result.passed


# ---------------------------------------------------------------------------
# 6. validate_empty_state
# ---------------------------------------------------------------------------


class TestValidateEmptyState:
    def _page_for_empty(
        self,
        heading_count: int = 1,
        desc_count: int = 1,
        cta_count: int = 1,
    ) -> MagicMock:
        page = _make_page()
        _seq_evaluate(page, heading_count, desc_count, cta_count)
        return page

    def test_passes_complete_empty_state(self) -> None:
        page = self._page_for_empty()
        result = validate_empty_state(page, ".empty")
        assert result.passed, result.summary()

    def test_fails_no_heading(self) -> None:
        page = self._page_for_empty(heading_count=0)
        result = validate_empty_state(page, ".empty")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("heading" in d for d in fail_lines)

    def test_fails_no_description(self) -> None:
        page = self._page_for_empty(desc_count=0)
        result = validate_empty_state(page, ".empty")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("description" in d or "<p>" in d for d in fail_lines)

    def test_fails_no_cta(self) -> None:
        page = self._page_for_empty(cta_count=0)
        result = validate_empty_state(page, ".empty")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("CTA" in d for d in fail_lines)

    def test_passes_multiple_elements(self) -> None:
        page = self._page_for_empty(heading_count=2, desc_count=3, cta_count=2)
        result = validate_empty_state(page, ".empty")
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# 7. validate_alert
# ---------------------------------------------------------------------------


class TestValidateAlert:
    def _page_for_alert(
        self,
        role: str = "alert",
        bg: str = "rgb(254, 242, 242)",
    ) -> MagicMock:
        page = _make_page()
        _seq_evaluate(page, role, bg)
        return page

    def test_passes_error_alert(self) -> None:
        page = self._page_for_alert()
        result = validate_alert(page, ".alert", variant="error")
        assert result.passed, result.summary()

    def test_passes_status_role_toast(self) -> None:
        page = self._page_for_alert(role="status", bg="rgb(240, 253, 244)")
        result = validate_alert(page, ".toast", variant="success")
        assert result.passed, result.summary()

    def test_fails_wrong_role(self) -> None:
        page = self._page_for_alert(role="region")
        result = validate_alert(page, ".alert", variant="error")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("role" in d for d in fail_lines)

    def test_fails_wrong_background(self) -> None:
        page = self._page_for_alert(bg="rgb(0, 0, 0)")
        result = validate_alert(page, ".alert", variant="warning")
        assert not result.passed

    @pytest.mark.parametrize(
        "variant,bg",
        [
            ("error",   "rgb(254, 242, 242)"),
            ("warning", "rgb(255, 251, 235)"),
            ("success", "rgb(240, 253, 244)"),
            ("info",    "rgb(239, 246, 255)"),
        ],
    )
    def test_all_variants_pass(self, variant: AlertVariant, bg: str) -> None:
        page = self._page_for_alert(bg=bg)
        result = validate_alert(page, ".alert", variant=variant)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# 8. validate_modal
# ---------------------------------------------------------------------------


class TestValidateModal:
    def _page_for_modal(
        self,
        role: str = "dialog",
        aria_modal: str = "true",
        aria_labelledby: str = "modal-title",
    ) -> MagicMock:
        page = _make_page()
        _seq_evaluate(page, role, aria_modal, aria_labelledby)
        return page

    def test_passes_well_formed_modal(self) -> None:
        page = self._page_for_modal()
        result = validate_modal(page, ".modal")
        assert result.passed, result.summary()

    def test_fails_missing_role(self) -> None:
        page = self._page_for_modal(role=None)
        result = validate_modal(page, ".modal")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("role" in d for d in fail_lines)

    def test_fails_aria_modal_not_true(self) -> None:
        page = self._page_for_modal(aria_modal="false")
        result = validate_modal(page, ".modal")
        assert not result.passed

    def test_fails_no_aria_labelledby(self) -> None:
        page = self._page_for_modal(aria_labelledby=None)
        result = validate_modal(page, ".modal")
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("aria-labelledby" in d for d in fail_lines)

    def test_escape_check_passes_when_hidden(self) -> None:
        page = _make_page()
        # role, aria-modal, aria-labelledby (3 attr calls), then escape eval
        _seq_evaluate(
            page,
            "dialog",
            "true",
            "modal-title",
            {"before": "flex", "after": "none"},
        )
        result = validate_modal(page, ".modal", check_escape=True)
        assert result.passed, result.summary()

    def test_escape_check_fails_when_still_visible(self) -> None:
        page = _make_page()
        _seq_evaluate(
            page,
            "dialog",
            "true",
            "modal-title",
            {"before": "flex", "after": "flex"},
        )
        result = validate_modal(page, ".modal", check_escape=True)
        assert not result.passed
        fail_lines = [d for d in result.details if d.startswith("FAIL:")]
        assert any("Escape" in d for d in fail_lines)

    def test_escape_check_skipped_by_default(self) -> None:
        page = self._page_for_modal()
        result = validate_modal(page, ".modal")
        # 3 checks: role, aria-modal, aria-labelledby — no 4th Escape check
        assert len(result.details) == 3
