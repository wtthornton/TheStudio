"""Unit tests for interaction_helpers.py (Epic 58, Story 58.5).

All tests use ``unittest.mock.MagicMock`` to simulate a Playwright ``Page``
object — no live browser is required.  Where a function raises a timeout error
the mock is configured to raise ``Exception("timeout")`` to simulate Playwright
``TimeoutError``.

Test matrix:

- InteractionResult dataclass: passed/summary behaviour
- assert_button_clickable: found/not-found, disabled, hidden, small touch target,
  missing label, non-native cursor check
- click_and_assert_state_change: text / attr / class variants, no assertions
  provided error, element not found
- assert_htmx_swap: hx-* attrs present/absent, target changes/does not change
- assert_form_submit: fills + submit, success selector, success text, error
  selector, missing form/field/submit
- assert_keyboard_navigation: min_focusable met/unmet, expected_order match/mismatch,
  container not found
- assert_focus_trap: role present/absent, focusable count, container not found
- assert_dropdown_toggle: aria-expanded lifecycle (open + close), trigger not found,
  open fails, close fails
- assert_copy_button: clickable + feedback selector + feedback text, not clickable
- assert_link_navigation: anchor tag, empty href, expected_href match/mismatch,
  new-tab attrs
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.playwright.lib.interaction_helpers import (
    InteractionResult,
    assert_button_clickable,
    assert_copy_button,
    assert_dropdown_toggle,
    assert_focus_trap,
    assert_form_submit,
    assert_htmx_swap,
    assert_keyboard_navigation,
    assert_link_navigation,
    click_and_assert_state_change,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(**kwargs) -> MagicMock:
    """Return a MagicMock with common Page methods pre-configured."""
    page = MagicMock()
    # Default evaluate returns None unless overridden per-test
    page.evaluate.return_value = None
    page.click.return_value = None
    page.fill.return_value = None
    page.wait_for_function.return_value = None
    page.wait_for_selector.return_value = None
    return page


# ---------------------------------------------------------------------------
# InteractionResult
# ---------------------------------------------------------------------------


class TestInteractionResult:
    def test_passed_when_no_fail_details(self):
        r = InteractionResult(action="test", details=["OK: all good"])
        assert r.passed is True

    def test_failed_when_any_fail_detail(self):
        r = InteractionResult(action="test", details=["OK: fine", "FAIL: broken"])
        assert r.passed is False

    def test_summary_pass(self):
        r = InteractionResult(action="button_clickable", details=["OK: visible"])
        assert "[PASS]" in r.summary()
        assert "all checks passed" in r.summary()

    def test_summary_fail_lists_failures(self):
        r = InteractionResult(
            action="button_clickable",
            details=["OK: visible", "FAIL: disabled"],
        )
        assert "[FAIL]" in r.summary()
        assert "disabled" in r.summary()

    def test_data_stored(self):
        r = InteractionResult(action="test", data={"key": "val"})
        assert r.data["key"] == "val"


# ---------------------------------------------------------------------------
# assert_button_clickable
# ---------------------------------------------------------------------------


class TestAssertButtonClickable:
    def _element_info(self, **overrides):
        defaults = {
            "tagName": "button",
            "disabled": False,
            "hidden": False,
            "cursor": "pointer",
            "role": "",
            "ariaLabel": "Submit",
            "width": 120,
            "height": 36,
            "tabIndex": 0,
        }
        defaults.update(overrides)
        return defaults

    def test_pass_all_checks(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info()
        result = assert_button_clickable(page, "button")
        assert result.passed

    def test_element_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_button_clickable(page, "#missing")
        assert not result.passed
        assert any("not found" in d for d in result.details)

    def test_disabled_fails(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info(disabled=True)
        result = assert_button_clickable(page, "button")
        assert not result.passed
        assert any("disabled" in d for d in result.details)

    def test_hidden_fails(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info(hidden=True)
        result = assert_button_clickable(page, "button")
        assert not result.passed
        assert any("hidden" in d for d in result.details)

    def test_small_touch_target_fails(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info(width=20, height=20)
        result = assert_button_clickable(page, "div[role='button']")
        assert not result.passed
        assert any("24×24" in d and "FAIL" in d for d in result.details)

    def test_non_native_non_pointer_cursor_fails(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info(
            tagName="div", cursor="default", role="button"
        )
        result = assert_button_clickable(page, "div[role='button']")
        assert not result.passed
        assert any("cursor" in d and "FAIL" in d for d in result.details)

    def test_native_element_skips_cursor_check(self):
        """<a> tags do not need cursor:pointer."""
        page = _make_page()
        page.evaluate.return_value = self._element_info(
            tagName="a", cursor="default"
        )
        result = assert_button_clickable(page, "a")
        # Should not fail on cursor for native element
        cursor_failures = [
            d for d in result.details if "cursor" in d and "FAIL" in d
        ]
        assert cursor_failures == []

    def test_missing_label_fails(self):
        page = _make_page()
        page.evaluate.return_value = self._element_info(ariaLabel="")
        result = assert_button_clickable(page, "button")
        assert not result.passed
        assert any("label" in d and "FAIL" in d for d in result.details)


# ---------------------------------------------------------------------------
# click_and_assert_state_change
# ---------------------------------------------------------------------------


class TestClickAndAssertStateChange:
    def test_no_assertions_fails(self):
        page = _make_page()
        result = click_and_assert_state_change(page, "#btn", "#target")
        assert not result.passed
        assert any("at least one" in d for d in result.details)

    def test_click_target_not_found(self):
        page = _make_page()
        page.evaluate.side_effect = [None, None]  # before_text, element_exists
        page.evaluate.return_value = None
        result = click_and_assert_state_change(
            page, "#missing", "#target", expected_text="OK"
        )
        # before_text is first call; exists check second
        # Mock returns None for both, first is before_text
        # We need to configure evaluate correctly
        page2 = _make_page()
        # First call: _JS_INNER_TEXT -> "old text"
        # Second call: _JS_ELEMENT_EXISTS -> None (falsy)
        page2.evaluate.side_effect = ["old text", None]
        result2 = click_and_assert_state_change(
            page2, "#missing", "#target", expected_text="new"
        )
        assert not result2.passed

    def test_text_state_change_passes(self):
        page = _make_page()
        # calls: before_text, element_exists, after_text
        page.evaluate.side_effect = ["old text", True, "new content"]
        page.wait_for_function.return_value = None
        result = click_and_assert_state_change(
            page, "#btn", "#target", expected_text="new"
        )
        assert result.passed

    def test_text_state_change_timeout_fails(self):
        page = _make_page()
        page.evaluate.side_effect = ["old text", True]
        page.wait_for_function.side_effect = Exception("timeout")
        page.evaluate.return_value = "old text"
        # Reset side_effect so subsequent calls work
        page2 = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "old text"  # before_text
            if call_count[0] == 2:
                return True  # element exists
            return "old text"  # after_text

        page2.evaluate.side_effect = evaluate_side_effect
        page2.wait_for_function.side_effect = Exception("Timeout 3000ms exceeded")
        result = click_and_assert_state_change(
            page2, "#btn", "#target", expected_text="new"
        )
        assert not result.passed

    def test_attr_state_change_passes(self):
        page = _make_page()
        page.evaluate.side_effect = ["", True]
        page.wait_for_function.return_value = None
        result = click_and_assert_state_change(
            page, "#btn", "#target", expected_attr=("aria-selected", "true")
        )
        assert result.passed

    def test_class_state_change_passes(self):
        page = _make_page()
        page.evaluate.side_effect = ["", True]
        page.wait_for_function.return_value = None
        result = click_and_assert_state_change(
            page, "#btn", "#target", expected_class="active"
        )
        assert result.passed


# ---------------------------------------------------------------------------
# assert_htmx_swap
# ---------------------------------------------------------------------------


class TestAssertHtmxSwap:
    def test_trigger_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_htmx_swap(page, "#missing", "#table")
        assert not result.passed
        assert any("not found" in d for d in result.details)

    def test_no_hx_attrs_fails(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {}  # hx_attrs — empty dict
            if call_count[0] == 2:
                return "before content"  # before_text
            return "before content"

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.return_value = None
        result = assert_htmx_swap(page, "#btn", "#table")
        assert not result.passed
        assert any("no hx-* attributes" in d for d in result.details)

    def test_swap_target_not_found_before_click(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"hx-get": "/refresh"}  # hx_attrs
            return None  # before_text is None -> target not found

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_htmx_swap(page, "#btn", "#missing")
        assert not result.passed
        assert any("not found before click" in d for d in result.details)

    def test_swap_content_changes_passes(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"hx-get": "/refresh", "hx-target": "#table"}
            if call_count[0] == 2:
                return "old row 1"  # before_text
            return "new row updated"  # after_text

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.return_value = None
        result = assert_htmx_swap(page, "#refresh-btn", "#table")
        assert result.passed

    def test_swap_timeout_fails(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"hx-get": "/refresh"}
            return "same content"

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.side_effect = Exception("Timeout 4000ms exceeded")
        result = assert_htmx_swap(page, "#btn", "#table")
        assert not result.passed
        assert any("did not change" in d for d in result.details)


# ---------------------------------------------------------------------------
# assert_form_submit
# ---------------------------------------------------------------------------


class TestAssertFormSubmit:
    def test_form_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_form_submit(
            page, "#missing-form", {}, "#submit-btn"
        )
        assert not result.passed
        assert any("form not found" in d for d in result.details)

    def test_field_not_found(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # form exists
            if call_count[0] == 2:
                return None  # field not found
            return True  # submit exists

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_form_submit(
            page, "form", {"#missing-field": "value"}, "#submit-btn"
        )
        assert not result.passed
        assert any("field not found" in d for d in result.details)

    def test_submit_not_found(self):
        page = _make_page()
        page.evaluate.side_effect = [True, True, None]  # form, field, submit
        result = assert_form_submit(
            page, "form", {"#name": "Alice"}, "#missing-submit"
        )
        assert not result.passed
        assert any("submit button not found" in d for d in result.details)

    def test_success_selector_passes(self):
        page = _make_page()
        page.evaluate.side_effect = [True, True, True]  # form, field, submit
        page.wait_for_selector.return_value = None
        result = assert_form_submit(
            page, "form", {"#name": "Alice"}, "#submit",
            expected_success_selector=".toast-success",
        )
        assert result.passed

    def test_success_selector_timeout_fails(self):
        page = _make_page()
        page.evaluate.side_effect = [True, True, True]
        page.wait_for_selector.side_effect = Exception("timeout")
        result = assert_form_submit(
            page, "form", {"#name": "Alice"}, "#submit",
            expected_success_selector=".toast-success",
        )
        assert not result.passed

    def test_success_text_passes(self):
        page = _make_page()
        page.evaluate.side_effect = [True, True, True]
        page.wait_for_function.return_value = None
        result = assert_form_submit(
            page, "form", {"#name": "Alice"}, "#submit",
            expected_success_text="Saved!",
        )
        assert result.passed

    def test_error_selector_passes(self):
        """Error path test: we expect an error element to appear."""
        page = _make_page()
        page.evaluate.side_effect = [True, True, True]
        page.wait_for_selector.return_value = None
        result = assert_form_submit(
            page, "form", {}, "#submit",
            expected_error_selector=".form-error",
        )
        assert result.passed


# ---------------------------------------------------------------------------
# assert_keyboard_navigation
# ---------------------------------------------------------------------------


class TestAssertKeyboardNavigation:
    def test_container_not_found(self):
        page = _make_page()
        page.evaluate.side_effect = [None, []]  # container exists, focusable
        # Actually _JS_ELEMENT_EXISTS check is first
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # container not found
            return []

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_keyboard_navigation(page, "#missing")
        assert not result.passed
        assert any("not found" in d for d in result.details)

    def test_min_focusable_met(self):
        page = _make_page()
        focusable = [
            {"tag": "button", "id": "btn1", "label": "Submit", "tabIndex": 0},
            {"tag": "a", "id": "link1", "label": "Home", "tabIndex": 0},
            {"tag": "input", "id": "name", "label": "Name", "tabIndex": 0},
        ]
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # container exists
            return focusable

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_keyboard_navigation(page, "main", min_focusable=2)
        assert result.passed

    def test_min_focusable_unmet(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return [{"tag": "button", "id": "btn1", "label": "X", "tabIndex": 0}]

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_keyboard_navigation(page, "main", min_focusable=3)
        assert not result.passed
        assert any("1 focusable" in d for d in result.details)

    def test_expected_order_match(self):
        page = _make_page()
        focusable = [
            {"tag": "a", "id": "home", "label": "Home", "tabIndex": 0},
            {"tag": "button", "id": "submit", "label": "Submit", "tabIndex": 0},
        ]
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return focusable

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_keyboard_navigation(
            page, "nav", expected_order=["home", "submit"]
        )
        assert result.passed

    def test_expected_order_mismatch(self):
        page = _make_page()
        focusable = [
            {"tag": "a", "id": "home", "label": "Home", "tabIndex": 0},
            {"tag": "button", "id": "submit", "label": "Submit", "tabIndex": 0},
        ]
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return focusable

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_keyboard_navigation(
            page, "nav", expected_order=["submit", "home"]  # reversed order
        )
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_focus_trap
# ---------------------------------------------------------------------------


class TestAssertFocusTrap:
    def test_container_not_found(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # container exists
            return {}

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_focus_trap(page, "#missing")
        assert not result.passed

    def test_missing_role_fails(self):
        page = _make_page()
        call_count = [0]
        focusable = [
            {"tag": "button", "id": "close", "label": "Close"},
            {"tag": "button", "id": "confirm", "label": "Confirm"},
        ]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            if call_count[0] == 2:
                return {"role": None, "ariaModal": None}
            return focusable

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_focus_trap(page, ".modal")
        assert not result.passed
        assert any("role='dialog'" in d and "FAIL" in d for d in result.details)

    def test_dialog_role_passes(self):
        page = _make_page()
        call_count = [0]
        focusable = [
            {"tag": "button", "id": "close"},
            {"tag": "input", "id": "name"},
            {"tag": "button", "id": "save"},
        ]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            if call_count[0] == 2:
                return {"role": "dialog", "ariaModal": "true"}
            return focusable

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_focus_trap(page, "[role='dialog']", min_focusable=2)
        assert result.passed

    def test_insufficient_focusable_fails(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            if call_count[0] == 2:
                return {"role": "dialog", "ariaModal": "true"}
            return [{"tag": "button", "id": "close"}]  # only 1

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_focus_trap(page, "[role='dialog']", min_focusable=2)
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_dropdown_toggle
# ---------------------------------------------------------------------------


class TestAssertDropdownToggle:
    def test_trigger_not_found(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # trigger not found
            return None

        page.evaluate.side_effect = evaluate_side_effect
        result = assert_dropdown_toggle(page, "#missing", "#menu")
        assert not result.passed

    def test_no_aria_expanded_warns(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # exists
            return None  # aria-expanded = None

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.return_value = None  # open succeeds
        # Need one more evaluate for open state + close state
        all_calls = [True, None, "true", "false"]
        page.evaluate.side_effect = iter(all_calls)
        page.wait_for_function.return_value = None
        result = assert_dropdown_toggle(page, "#btn", "#menu")
        # aria-expanded missing is a FAIL
        assert any("aria-expanded" in d and "FAIL" in d for d in result.details)

    def test_open_and_close_passes(self):
        page = _make_page()
        all_calls = [True, "false", "true", "false"]
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # exists
            if call_count[0] == 2:
                return "false"  # aria-expanded before
            if call_count[0] == 3:
                return "true"  # aria-expanded after open
            return "false"  # aria-expanded after close

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.return_value = None  # both open+close succeed
        result = assert_dropdown_toggle(page, "#btn", "#menu")
        assert result.passed

    def test_open_timeout_fails(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return "false"

        page.evaluate.side_effect = evaluate_side_effect
        page.wait_for_function.side_effect = Exception("Timeout 2000ms exceeded")
        result = assert_dropdown_toggle(page, "#btn", "#menu")
        assert not result.passed
        assert any("did not open" in d for d in result.details)

    def test_close_timeout_fails(self):
        page = _make_page()
        call_count = [0]

        def evaluate_side_effect(js, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            if call_count[0] == 2:
                return "false"
            return "true"

        page.evaluate.side_effect = evaluate_side_effect
        wait_count = [0]

        def wait_side_effect(*args, **kwargs):
            wait_count[0] += 1
            if wait_count[0] == 1:
                return None  # open succeeds
            raise Exception("Timeout 2000ms exceeded")  # close fails

        page.wait_for_function.side_effect = wait_side_effect
        result = assert_dropdown_toggle(page, "#btn", "#menu")
        assert not result.passed
        assert any("did not close" in d for d in result.details)


# ---------------------------------------------------------------------------
# assert_copy_button
# ---------------------------------------------------------------------------


class TestAssertCopyButton:
    def _clickable_page(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "button",
            "disabled": False,
            "hidden": False,
            "cursor": "pointer",
            "role": "",
            "ariaLabel": "Copy URL",
            "width": 80,
            "height": 32,
            "tabIndex": 0,
        }
        return page

    def test_pass_with_feedback_selector(self):
        page = self._clickable_page()
        page.wait_for_selector.return_value = None
        result = assert_copy_button(
            page, "#copy-btn", feedback_selector=".copied-indicator"
        )
        assert result.passed

    def test_pass_with_feedback_text(self):
        page = self._clickable_page()
        page.wait_for_function.return_value = None
        result = assert_copy_button(
            page, "#copy-btn", feedback_text="Copied!"
        )
        assert result.passed

    def test_pass_no_feedback_configured(self):
        page = self._clickable_page()
        result = assert_copy_button(page, "#copy-btn")
        assert result.passed

    def test_not_clickable_fails(self):
        page = _make_page()
        page.evaluate.return_value = None  # element not found
        result = assert_copy_button(page, "#missing-btn")
        assert not result.passed

    def test_feedback_timeout_fails(self):
        page = self._clickable_page()
        page.wait_for_selector.side_effect = Exception("timeout")
        result = assert_copy_button(
            page, "#copy-btn", feedback_selector=".copied-indicator"
        )
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_link_navigation
# ---------------------------------------------------------------------------


class TestAssertLinkNavigation:
    def test_link_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_link_navigation(page, "#missing-link")
        assert not result.passed

    def test_non_anchor_tag_fails(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "span",
            "href": "/dashboard",
            "target": "",
            "rel": "",
            "text": "Dashboard",
        }
        result = assert_link_navigation(page, "span.link")
        assert not result.passed
        assert any("<a>" in d and "FAIL" in d for d in result.details)

    def test_empty_href_fails(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "",
            "target": "",
            "rel": "",
            "text": "Home",
        }
        result = assert_link_navigation(page, "a")
        assert not result.passed

    def test_expected_href_match_passes(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "/admin/ui/repos",
            "target": "",
            "rel": "",
            "text": "Repos",
        }
        result = assert_link_navigation(page, "a", expected_href="/admin/ui/repos")
        assert result.passed

    def test_expected_href_mismatch_fails(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "/admin/ui/repos",
            "target": "",
            "rel": "",
            "text": "Repos",
        }
        result = assert_link_navigation(page, "a", expected_href="/dashboard")
        assert not result.passed
        assert any("does not contain" in d for d in result.details)

    def test_new_tab_with_noopener_passes(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "https://docs.example.com",
            "target": "_blank",
            "rel": "noopener noreferrer",
            "text": "Docs",
        }
        result = assert_link_navigation(page, "a", expect_new_tab=True)
        assert result.passed

    def test_new_tab_missing_noopener_fails(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "https://docs.example.com",
            "target": "_blank",
            "rel": "",
            "text": "Docs",
        }
        result = assert_link_navigation(page, "a", expect_new_tab=True)
        assert not result.passed
        assert any("noopener" in d and "FAIL" in d for d in result.details)

    def test_new_tab_wrong_target_fails(self):
        page = _make_page()
        page.evaluate.return_value = {
            "tagName": "a",
            "href": "https://docs.example.com",
            "target": "_self",
            "rel": "noopener",
            "text": "Docs",
        }
        result = assert_link_navigation(page, "a", expect_new_tab=True)
        assert not result.passed
        assert any("_blank" in d and "FAIL" in d for d in result.details)
