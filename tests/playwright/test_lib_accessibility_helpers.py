"""Unit tests for accessibility_helpers.py (Epic 58, Story 58.6).

All tests use ``unittest.mock.MagicMock`` to simulate a Playwright ``Page``
object — no live browser is required.

Test matrix:

- AccessibilityResult dataclass: passed/summary behaviour
- assert_focus_visible: all pass, some missing ring, no elements, evaluate error
- assert_keyboard_navigation: enough elements, too few, positive tabindex,
  container not found, evaluate error
- assert_aria_landmarks: main+nav+header present, main missing, nav missing,
  duplicate nav without aria-label, evaluate error
- assert_aria_roles: all match, some mismatch, no elements found, evaluate error
- assert_table_accessibility: all scoped, some missing scope, table not found,
  no th elements, evaluate error
- assert_form_accessibility: all labelled, some unlabelled, no controls,
  container not found, evaluate error
- assert_touch_targets: all meet minimum, some too small, no elements,
  evaluate error
- assert_no_color_only_indicators: all paired, some color-only, no elements,
  evaluate error
- run_axe_audit: no violations, violations returned, load failure
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.playwright.lib.accessibility_helpers import (
    AccessibilityResult,
    assert_aria_landmarks,
    assert_aria_roles,
    assert_focus_visible,
    assert_form_accessibility,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_table_accessibility,
    assert_touch_targets,
    run_axe_audit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page() -> MagicMock:
    """Return a MagicMock with common Page methods pre-configured."""
    page = MagicMock()
    page.evaluate.return_value = None
    page.wait_for_function.return_value = None
    return page


# ---------------------------------------------------------------------------
# AccessibilityResult
# ---------------------------------------------------------------------------


class TestAccessibilityResult:
    def test_passed_when_no_fail_details(self):
        r = AccessibilityResult(check="test", details=["OK: all good"])
        assert r.passed is True

    def test_failed_when_any_fail_detail(self):
        r = AccessibilityResult(check="test", details=["OK: fine", "FAIL: broken"])
        assert r.passed is False

    def test_empty_details_passes(self):
        r = AccessibilityResult(check="test")
        assert r.passed is True

    def test_summary_pass(self):
        r = AccessibilityResult(check="focus_visible", details=["OK: all rings present"])
        assert "PASS" in r.summary()
        assert "focus_visible" in r.summary()

    def test_summary_fail(self):
        r = AccessibilityResult(check="focus_visible", details=["FAIL: missing ring on button"])
        assert "FAIL" in r.summary()
        assert "missing ring" in r.summary()

    def test_summary_multiple_failures(self):
        r = AccessibilityResult(
            check="aria_landmarks",
            details=["FAIL: no main", "FAIL: no nav"],
        )
        assert "no main" in r.summary()
        assert "no nav" in r.summary()


# ---------------------------------------------------------------------------
# assert_focus_visible
# ---------------------------------------------------------------------------


class TestAssertFocusVisible:
    def test_all_have_focus_ring(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "btn1", "label": "Submit", "hasFocusRing": True},
            {"tag": "a", "id": "lnk1", "label": "Home", "hasFocusRing": True},
        ]
        result = assert_focus_visible(page)
        assert result.passed, result.summary()
        assert result.data["elements_checked"] == 2
        assert result.data["missing_focus_ring"] == []

    def test_some_missing_focus_ring(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "btn1", "label": "Submit", "hasFocusRing": True},
            {"tag": "input", "id": "inp1", "label": "Name", "hasFocusRing": False},
        ]
        result = assert_focus_visible(page)
        assert not result.passed
        assert "1 element(s) missing focus ring" in result.summary()

    def test_no_focusable_elements(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_focus_visible(page)
        assert result.passed
        assert "no focusable elements" in result.details[0]

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("timeout")
        result = assert_focus_visible(page)
        assert not result.passed
        assert "Could not evaluate" in result.summary()

    def test_many_missing_truncated(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": f"btn{i}", "label": f"btn{i}", "hasFocusRing": False}
            for i in range(10)
        ]
        result = assert_focus_visible(page)
        assert not result.passed
        # should truncate at 5 + ellipsis
        assert "…" in result.details[-1]


# ---------------------------------------------------------------------------
# assert_keyboard_navigation
# ---------------------------------------------------------------------------


class TestAssertKeyboardNavigation:
    def test_enough_focusable_elements(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "btn1", "label": "OK", "tabIndex": 0},
            {"tag": "a", "id": "lnk1", "label": "Home", "tabIndex": 0},
        ]
        result = assert_keyboard_navigation(page, min_focusable=2)
        assert result.passed, result.summary()
        assert result.data["focusable_count"] == 2

    def test_too_few_focusable_elements(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "btn1", "label": "OK", "tabIndex": 0},
        ]
        result = assert_keyboard_navigation(page, min_focusable=5)
        assert not result.passed
        assert "at least 5" in result.summary()

    def test_positive_tabindex_flagged(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "btn1", "label": "Skip", "tabIndex": 5},
        ]
        result = assert_keyboard_navigation(page)
        assert not result.passed
        assert "tabIndex > 0" in result.summary()

    def test_evaluate_returns_none(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_keyboard_navigation(page)
        assert not result.passed
        assert "not found" in result.summary()

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("JS error")
        result = assert_keyboard_navigation(page)
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_aria_landmarks
# ---------------------------------------------------------------------------


class TestAssertAriaLandmarks:
    def _full_landmarks(self):
        return {
            "nav": [{"tag": "nav", "role": "navigation", "ariaLabel": "Main nav"}],
            "main": [{"tag": "main", "role": "main", "ariaLabel": ""}],
            "header": [{"tag": "header", "role": "banner", "ariaLabel": ""}],
            "aside": [],
        }

    def test_all_landmarks_present(self):
        page = _make_page()
        page.evaluate.return_value = self._full_landmarks()
        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_main_missing(self):
        page = _make_page()
        lm = self._full_landmarks()
        lm["main"] = []
        page.evaluate.return_value = lm
        result = assert_aria_landmarks(page)
        assert not result.passed
        assert "main" in result.summary()

    def test_nav_missing(self):
        page = _make_page()
        lm = self._full_landmarks()
        lm["nav"] = []
        page.evaluate.return_value = lm
        result = assert_aria_landmarks(page)
        assert not result.passed
        assert "nav" in result.summary()

    def test_duplicate_nav_requires_aria_label(self):
        page = _make_page()
        lm = self._full_landmarks()
        lm["nav"] = [
            {"tag": "nav", "role": "navigation", "ariaLabel": ""},
            {"tag": "nav", "role": "navigation", "ariaLabel": ""},
        ]
        page.evaluate.return_value = lm
        result = assert_aria_landmarks(page)
        assert not result.passed
        assert "aria-label" in result.summary()

    def test_duplicate_nav_with_aria_labels_passes(self):
        page = _make_page()
        lm = self._full_landmarks()
        lm["nav"] = [
            {"tag": "nav", "role": "navigation", "ariaLabel": "Primary"},
            {"tag": "nav", "role": "navigation", "ariaLabel": "Secondary"},
        ]
        page.evaluate.return_value = lm
        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("DOM error")
        result = assert_aria_landmarks(page)
        assert not result.passed

    def test_evaluate_returns_none(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_aria_landmarks(page)
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_aria_roles
# ---------------------------------------------------------------------------


class TestAssertAriaRoles:
    def test_all_correct_roles(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "b1", "role": "button", "ariaLabel": "Submit"},
            {"tag": "button", "id": "b2", "role": "button", "ariaLabel": "Cancel"},
        ]
        result = assert_aria_roles(page, "button", "button")
        assert result.passed, result.summary()
        assert result.data["elements_checked"] == 2

    def test_wrong_roles_flagged(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "div", "id": "d1", "role": "dialog", "ariaLabel": "Modal"},
            {"tag": "div", "id": "d2", "role": "region", "ariaLabel": "Panel"},
        ]
        result = assert_aria_roles(page, "[role]", "dialog")
        assert not result.passed
        assert "role='region'" in result.summary()

    def test_no_elements_found(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_aria_roles(page, ".nonexistent", "button")
        assert not result.passed
        assert "no elements found" in result.summary()

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("eval error")
        result = assert_aria_roles(page, "button", "button")
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_table_accessibility
# ---------------------------------------------------------------------------


class TestAssertTableAccessibility:
    def test_all_th_have_scope(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"text": "Name", "scope": "col", "id": ""},
            {"text": "Status", "scope": "col", "id": ""},
            {"text": "Row", "scope": "row", "id": ""},
        ]
        result = assert_table_accessibility(page, "table")
        assert result.passed, result.summary()
        assert result.data["headers_checked"] == 3

    def test_th_missing_scope(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"text": "Name", "scope": "col", "id": ""},
            {"text": "Status", "scope": "", "id": ""},
        ]
        result = assert_table_accessibility(page, "table")
        assert not result.passed
        assert "'Status'" in result.summary()

    def test_table_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_table_accessibility(page, "#nonexistent")
        assert not result.passed
        assert "not found" in result.summary()

    def test_no_th_elements(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_table_accessibility(page, "table")
        assert result.passed
        assert "no <th>" in result.details[0]

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("DOM error")
        result = assert_table_accessibility(page, "table")
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_form_accessibility
# ---------------------------------------------------------------------------


class TestAssertFormAccessibility:
    def test_all_controls_labelled(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "input", "type": "text", "id": "name", "hasLabel": True,
             "ariaLabel": "", "ariaLabelledBy": "", "ariaDescribedBy": ""},
            {"tag": "select", "type": "", "id": "role", "hasLabel": True,
             "ariaLabel": "", "ariaLabelledBy": "", "ariaDescribedBy": ""},
        ]
        result = assert_form_accessibility(page, "form")
        assert result.passed, result.summary()

    def test_unlabelled_control_flagged(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "input", "type": "email", "id": "", "hasLabel": False,
             "ariaLabel": "", "ariaLabelledBy": "", "ariaDescribedBy": ""},
        ]
        result = assert_form_accessibility(page, "form")
        assert not result.passed
        assert "1 form control(s) missing" in result.summary()

    def test_no_controls(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_form_accessibility(page, "form")
        assert result.passed
        assert "no form controls" in result.details[0]

    def test_container_not_found(self):
        page = _make_page()
        page.evaluate.return_value = None
        result = assert_form_accessibility(page, "#missing-form")
        assert not result.passed
        assert "not found" in result.summary()

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("error")
        result = assert_form_accessibility(page, "form")
        assert not result.passed


# ---------------------------------------------------------------------------
# assert_touch_targets
# ---------------------------------------------------------------------------


class TestAssertTouchTargets:
    def test_all_meet_minimum(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "b1", "label": "Submit", "width": 80, "height": 40, "meetsMinimum": True},
            {"tag": "a", "id": "lnk1", "label": "Home", "width": 60, "height": 32, "meetsMinimum": True},
        ]
        result = assert_touch_targets(page)
        assert result.passed, result.summary()
        assert result.data["too_small"] == []

    def test_element_too_small(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": "tiny", "label": "X", "width": 16, "height": 16, "meetsMinimum": False},
        ]
        result = assert_touch_targets(page)
        assert not result.passed
        assert "16×16px" in result.summary()

    def test_no_interactive_elements(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_touch_targets(page)
        assert result.passed
        assert "no buttons" in result.details[0]

    def test_invisible_elements_skipped(self):
        page = _make_page()
        # zero-size elements are invisible — should not count as failures
        page.evaluate.return_value = [
            {"tag": "button", "id": "hidden", "label": "", "width": 0, "height": 0, "meetsMinimum": False},
        ]
        result = assert_touch_targets(page)
        assert result.passed

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("error")
        result = assert_touch_targets(page)
        assert not result.passed

    def test_many_small_truncated(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "button", "id": f"b{i}", "label": f"btn{i}", "width": 10, "height": 10, "meetsMinimum": False}
            for i in range(10)
        ]
        result = assert_touch_targets(page)
        assert not result.passed
        assert "…" in result.details[-1]


# ---------------------------------------------------------------------------
# assert_no_color_only_indicators
# ---------------------------------------------------------------------------


class TestAssertNoColorOnlyIndicators:
    def test_all_paired_with_text(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "span", "id": "s1", "class": "badge-success", "text": "Active", "hasTextOrIcon": True},
            {"tag": "span", "id": "s2", "class": "status-dot", "text": "", "hasTextOrIcon": True},
        ]
        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_color_only_element_flagged(self):
        page = _make_page()
        page.evaluate.return_value = [
            {"tag": "span", "id": "", "class": "status-dot", "text": "", "hasTextOrIcon": False},
        ]
        result = assert_no_color_only_indicators(page)
        assert not result.passed
        assert "colour as the only indicator" in result.summary()

    def test_no_indicators_found(self):
        page = _make_page()
        page.evaluate.return_value = []
        result = assert_no_color_only_indicators(page)
        assert result.passed
        assert "no status indicator" in result.details[0]

    def test_evaluate_raises_error(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("DOM error")
        result = assert_no_color_only_indicators(page)
        assert not result.passed


# ---------------------------------------------------------------------------
# run_axe_audit
# ---------------------------------------------------------------------------


class TestRunAxeAudit:
    def test_no_violations(self):
        page = _make_page()
        page.evaluate.side_effect = [None, []]  # inject + run
        violations = run_axe_audit(page)
        assert violations == []

    def test_violations_returned(self):
        page = _make_page()
        sample_violations = [
            {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Elements must have sufficient color contrast",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/color-contrast",
                "nodes": [{"html": "<button>Click</button>", "target": ["button"], "failureSummary": "Fix contrast"}],
            }
        ]
        page.evaluate.side_effect = [None, sample_violations]
        violations = run_axe_audit(page)
        assert len(violations) == 1
        assert violations[0]["id"] == "color-contrast"
        assert violations[0]["impact"] == "serious"

    def test_axe_load_failure_raises(self):
        page = _make_page()
        page.evaluate.side_effect = Exception("Script load failed")
        with pytest.raises(RuntimeError, match="axe-core audit failed"):
            run_axe_audit(page)

    def test_wait_for_function_called(self):
        page = _make_page()
        page.evaluate.side_effect = [None, []]
        run_axe_audit(page, timeout=5000)
        page.wait_for_function.assert_called_once()
        call_kwargs = page.wait_for_function.call_args
        assert call_kwargs[1]["timeout"] == 5000 or call_kwargs[0][1] == 5000

    def test_returns_empty_list_when_none(self):
        page = _make_page()
        page.evaluate.side_effect = [None, None]
        violations = run_axe_audit(page)
        assert violations == []
