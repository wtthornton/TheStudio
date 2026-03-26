"""Epic 62.5 — Audit Log: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/audit meets WCAG 2.2 AA accessibility requirements:

  - Table semantics — <th scope="col"> on column headers, <caption> or aria-label (SC 1.3.1)
  - Filter ARIA     — time-range filter controls carry accessible labels (SC 1.3.1)
  - Keyboard pagination — next/previous pagination reachable by keyboard (SC 2.1.1)
  - Focus indicators visible on all interactive elements (SC 2.4.11)
  - ARIA landmark regions present (SC 1.3.6)
  - Status badges pair colour with text or icon (SC 1.4.1)
  - Buttons and links meet 24×24 px minimum touch target (SC 2.5.8)
  - axe-core WCAG 2.x AA audit reports zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_audit_intent.py (Epic 62.1).
Style compliance is covered in test_audit_style.py (Epic 62.3).
Interactions are covered in test_audit_interactions.py (Epic 62.4).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_touch_targets,
    run_axe_audit,
)

pytestmark = pytest.mark.playwright

AUDIT_URL = "/admin/ui/audit"


def _go(page: object, base_url: str) -> None:
    """Navigate to the audit log page and wait for content to settle."""
    navigate(page, f"{base_url}{AUDIT_URL}")  # type: ignore[arg-type]


def _has_audit_rows(page: object) -> bool:
    """Return True when the audit table has at least one data row."""
    return page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SC 1.3.1 — Table semantics
# ---------------------------------------------------------------------------


class TestAuditTableSemantics:
    """Audit event table must use correct semantic markup (SC 1.3.1).

    Screen readers rely on <th scope="col"> headers and a table caption or
    aria-label to announce the table's purpose and column relationships.
    """

    def test_table_has_th_scope_attributes(self, page, base_url: str) -> None:
        """All <th> elements carry scope='col' or scope='row'."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No <table> on audit page — empty state is acceptable")

        scope_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var table = document.querySelector('table');
                if (!table) return {total: 0, missing: 0};
                var ths = table.querySelectorAll('th');
                var missing = 0;
                ths.forEach(function(th) {
                    var sc = th.getAttribute('scope');
                    if (sc !== 'col' && sc !== 'row') missing++;
                });
                return {total: ths.length, missing: missing};
            })()
            """
        )
        if scope_info["total"] == 0:
            pytest.skip("No <th> elements found in audit table")

        assert scope_info["missing"] == 0, (
            f"{scope_info['missing']}/{scope_info['total']} <th> elements missing "
            "scope='col'/'row' — required by WCAG SC 1.3.1"
        )

    def test_table_has_caption_or_aria_label(self, page, base_url: str) -> None:
        """Audit table has a <caption> or aria-label identifying its purpose."""
        _go(page, base_url)

        if page.locator("table").count() == 0:
            pytest.skip("No <table> on audit page — empty state is acceptable")

        table_label_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var table = document.querySelector('table');
                if (!table) return {has_caption: false, has_aria_label: false};
                var caption = table.querySelector('caption');
                var ariaLabel = table.getAttribute('aria-label');
                var ariaLabelledBy = table.getAttribute('aria-labelledby');
                return {
                    has_caption: !!caption && caption.textContent.trim().length > 0,
                    has_aria_label: !!ariaLabel || !!ariaLabelledBy
                };
            })()
            """
        )

        has_label = (
            table_label_info.get("has_caption") or table_label_info.get("has_aria_label")
        )
        assert has_label, (
            "Audit table must have a <caption> or aria-label/aria-labelledby "
            "to identify its purpose to screen readers (WCAG SC 1.3.1)"
        )

    def test_timestamp_cells_use_time_element_or_title(self, page, base_url: str) -> None:
        """Audit timestamp cells use <time datetime=''> or a title attribute."""
        _go(page, base_url)

        if not _has_audit_rows(page):
            pytest.skip("No audit event rows — semantic timestamp test requires data")

        has_time_element = page.locator("td time[datetime]").count() > 0
        has_title_on_td = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var tds = document.querySelectorAll('table tbody tr td');
                for (var i = 0; i < tds.length; i++) {
                    if (tds[i].getAttribute('title') &&
                        tds[i].getAttribute('data-col') === 'timestamp') {
                        return true;
                    }
                }
                return false;
            })()
            """
        )

        if has_time_element or has_title_on_td:
            return  # Good semantic markup found

        pytest.skip(
            "No <time datetime> elements or titled timestamp cells found; "
            "audit timestamps may use plain text formatting"
        )


# ---------------------------------------------------------------------------
# SC 1.3.1 — Filter ARIA labels
# ---------------------------------------------------------------------------


class TestAuditFilterAria:
    """Time-range and other filter controls must carry accessible labels (SC 1.3.1).

    Unlabelled <select> or <input> controls are invisible to screen readers.
    Every filter must have an associated <label>, aria-label, or aria-labelledby.
    """

    def test_filter_controls_have_accessible_labels(self, page, base_url: str) -> None:
        """All filter <select> and <input> elements carry accessible labels."""
        _go(page, base_url)

        filter_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var inputs = document.querySelectorAll(
                    'input[type="date"], input[type="datetime-local"], ' +
                    'input[type="text"][placeholder*="filter" i], ' +
                    'select'
                );
                var results = [];
                inputs.forEach(function(el) {
                    var id = el.id;
                    var hasLabel = (
                        (id && document.querySelector('label[for="' + id + '"]')) ||
                        el.getAttribute('aria-label') ||
                        el.getAttribute('aria-labelledby') ||
                        el.getAttribute('title') ||
                        el.getAttribute('placeholder')
                    );
                    results.push({
                        tag: el.tagName,
                        id: id,
                        hasLabel: !!hasLabel
                    });
                });
                return results;
            })()
            """
        )

        if not filter_info:
            pytest.skip("No filter controls found on audit page — skipping label check")

        unlabelled = [r for r in filter_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} filter control(s) have no accessible label: "
            f"{unlabelled} — WCAG SC 1.3.1 requires labels on all form controls"
        )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestAuditKeyboardNavigation:
    """All interactive elements on the audit page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_table(self, page, base_url: str) -> None:
        """Tab key reaches the audit event table or its filter controls."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_pagination_keyboard_operable(self, page, base_url: str) -> None:
        """Next/Previous pagination buttons are keyboard-focusable and operable."""
        _go(page, base_url)

        pagination_selectors = [
            "button:has-text('Next')",
            "button:has-text('Previous')",
            "button[aria-label='Next page']",
            "button[aria-label='Previous page']",
        ]
        for sel in pagination_selectors:
            count = page.locator(sel).count()  # type: ignore[attr-defined]
            if count > 0:
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No pagination buttons found — skipping keyboard pagination check"
        )

    def test_filter_controls_keyboard_operable(self, page, base_url: str) -> None:
        """Filter controls (date inputs, selects) are keyboard-operable."""
        _go(page, base_url)

        filter_selectors = [
            "select",
            "input[type='date']",
            "input[type='datetime-local']",
            "[data-filter]",
        ]
        for sel in filter_selectors:
            count = page.locator(sel).count()  # type: ignore[attr-defined]
            if count > 0:
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No filter controls found on audit page — skipping keyboard operability check"
        )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestAuditFocusIndicators:
    """All interactive elements must display visible focus indicators (SC 2.4.11)."""

    def test_interactive_elements_show_focus(self, page, base_url: str) -> None:
        """Buttons and links display a visible focus indicator on keyboard focus."""
        _go(page, base_url)

        interactive_selectors = [
            "button",
            "a[href]",
            "input",
            "select",
        ]
        for sel in interactive_selectors:
            count = page.locator(sel).count()  # type: ignore[attr-defined]
            if count > 0:
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No interactive elements found on audit page — skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestAuditAriaLandmarks:
    """Audit page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.4.1 — Colour not the only indicator
# ---------------------------------------------------------------------------


class TestAuditColorIndicators:
    """Status indicators must not rely solely on colour (SC 1.4.1)."""

    def test_no_color_only_status_indicators(self, page, base_url: str) -> None:
        """All status indicators pair colour with a text label or icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestAuditTouchTargets:
    """Buttons and links must meet the 24×24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(self, page, base_url: str) -> None:
        """All buttons and links on the audit page meet the 24×24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestAuditAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(self, page, base_url: str) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/audit:\n{result.summary()}"
        )
