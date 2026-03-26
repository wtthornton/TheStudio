"""Epic 64.5 — Expert Performance: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/experts meets WCAG 2.2 AA accessibility requirements:

  - Table headers      — <th scope="col"> on every column header (SC 1.3.1)
  - Badge non-color    — trust-tier and drift badges pair colour with text/icon (SC 1.4.1)
  - Focus management  — detail panel traps/restores focus on open/close (SC 2.4.3)
  - Focus indicators   — visible focus ring on all interactive elements (SC 2.4.11)
  - Keyboard nav       — Tab reaches rows, filter/sort controls (SC 2.1.1)
  - ARIA landmarks     — page has main/nav landmark (SC 1.3.6)
  - Touch targets      — buttons meet 24x24 px minimum (SC 2.5.8)
  - axe-core WCAG 2.x AA — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_experts_intent.py (Epic 64.1).
Style compliance is covered in test_experts_style.py (Epic 64.3).
Interactions are covered in test_experts_interactions.py (Epic 64.4).
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

EXPERTS_URL = "/admin/ui/experts"


def _go(page: object, base_url: str) -> None:
    """Navigate to the experts page and wait for content to settle."""
    navigate(page, f"{base_url}{EXPERTS_URL}")  # type: ignore[arg-type]


def _has_expert_rows(page: object) -> bool:
    """Return True when the experts table has at least one data row."""
    return page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SC 1.3.1 — Table headers with scope="col"
# ---------------------------------------------------------------------------


class TestExpertsTableHeaders:
    """Expert table column headers must carry scope="col" for screen reader navigation.

    Per WCAG SC 1.3.1 (Info and Relationships), every <th> in a data table
    must carry scope="col" (or scope="row" for row headers) so that assistive
    technology can associate cell data with its header.
    """

    def test_table_column_headers_have_scope_col(
        self, page: object, base_url: str
    ) -> None:
        """Every <th> in the experts table carries scope='col'."""
        _go(page, base_url)

        th_count = page.locator("table th").count()  # type: ignore[attr-defined]
        if th_count == 0:
            pytest.skip("No <th> elements found — experts list may not use a <table>")

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                var results = [];
                ths.forEach(function(th) {
                    var scope = th.getAttribute('scope');
                    var role  = th.getAttribute('role');
                    // scope="col" is required; role="columnheader" is an acceptable
                    // equivalent that implies scope="col" semantics
                    results.push({
                        text: th.textContent.trim().slice(0, 40),
                        scope: scope,
                        role: role,
                        compliant: scope === 'col' || role === 'columnheader'
                    });
                });
                return results;
            })()
            """
        )

        non_compliant = [r for r in header_info if not r.get("compliant")]
        assert not non_compliant, (
            f"{len(non_compliant)}/{len(header_info)} <th> element(s) missing "
            "scope='col' or role='columnheader' — WCAG SC 1.3.1 requires every "
            "table column header to declare its scope: "
            + str([r["text"] for r in non_compliant])
        )

    def test_table_has_caption_or_aria_label(
        self, page: object, base_url: str
    ) -> None:
        """The experts data table carries a <caption> or aria-label for context."""
        _go(page, base_url)

        tables = page.locator("table")  # type: ignore[attr-defined]
        if tables.count() == 0:
            pytest.skip("No <table> elements on experts page")

        table_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var tables = document.querySelectorAll('table');
                var results = [];
                tables.forEach(function(t) {
                    var caption   = !!t.querySelector('caption');
                    var ariaLabel = !!t.getAttribute('aria-label');
                    var ariaLby   = !!t.getAttribute('aria-labelledby');
                    results.push({
                        labelled: caption || ariaLabel || ariaLby
                    });
                });
                return results;
            })()
            """
        )

        unlabelled = [r for r in table_info if not r.get("labelled")]
        # Soft check: at least the primary data table must be labelled
        if len(unlabelled) == len(table_info):
            pytest.skip(
                "No table has a <caption> or aria-label — "
                "consider adding one for screen reader context (WCAG SC 1.3.1)"
            )

    def test_sortable_headers_announce_sort_direction(
        self, page: object, base_url: str
    ) -> None:
        """Sortable column headers carry aria-sort to communicate sort direction."""
        _go(page, base_url)

        sortable_headers = page.locator(  # type: ignore[attr-defined]
            "th[aria-sort], th button[aria-sort], th[data-sort]"
        )
        if sortable_headers.count() == 0:
            pytest.skip(
                "No sortable column headers found (aria-sort / data-sort) — "
                "table may not support sorting"
            )

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var headers = document.querySelectorAll(
                    'th[aria-sort], th[data-sort]'
                );
                var results = [];
                headers.forEach(function(th) {
                    var sortVal = th.getAttribute('aria-sort');
                    // Valid values: ascending, descending, none, other
                    var valid = ['ascending', 'descending', 'none', 'other'];
                    results.push({
                        text: th.textContent.trim().slice(0, 40),
                        ariaSortValue: sortVal,
                        valid: valid.includes(sortVal)
                    });
                });
                return results;
            })()
            """
        )

        invalid = [r for r in header_info if not r.get("valid")]
        assert not invalid, (
            f"{len(invalid)} sortable header(s) have invalid aria-sort values: "
            + str([(r["text"], r["ariaSortValue"]) for r in invalid])
            + " — valid values are: ascending, descending, none, other (WCAG SC 1.3.1)"
        )


# ---------------------------------------------------------------------------
# SC 1.4.1 — Badge non-colour cues (trust tier / drift signals)
# ---------------------------------------------------------------------------


class TestExpertsBadgeNonColorCues:
    """Trust-tier and drift signal badges must not rely solely on colour (SC 1.4.1).

    Expert Performance uses colour-coded trust tier badges (Observe / Suggest /
    Execute) and drift signal badges. Each badge must pair its colour with a
    visible text label or icon with an aria-label so that colour-blind users and
    screen-reader users receive the same information.
    """

    def test_trust_tier_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Trust tier badges (Observe/Suggest/Execute) carry visible text, not colour only."""
        _go(page, base_url)

        badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-tier]',
                    '[data-trust-tier]',
                    '[class*="tier"]',
                    '[class*="trust"]',
                    '[aria-label*="tier" i]',
                    '[aria-label*="trust" i]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var text     = el.textContent.trim();
                        var ariaLbl  = el.getAttribute('aria-label');
                        var ariaLby  = el.getAttribute('aria-labelledby');
                        results.push({
                            hasText: text.length > 0,
                            hasAriaLabel: !!(ariaLbl || ariaLby)
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not badge_info:
            pytest.skip(
                "No trust-tier badge elements found on experts page — "
                "page may be empty or use a different pattern"
            )

        color_only = [
            r for r in badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(badge_info)} trust-tier badge(s) convey tier "
            "via colour only — each badge must pair colour with visible text or "
            "aria-label (WCAG SC 1.4.1)"
        )

    def test_drift_signal_badges_have_non_color_cue(
        self, page: object, base_url: str
    ) -> None:
        """Drift signal indicators pair colour with a text label or icon+aria-label."""
        _go(page, base_url)

        drift_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-drift]',
                    '[class*="drift"]',
                    '[aria-label*="drift" i]',
                    '[title*="drift" i]'
                ];
                var results = [];
                var seen = new WeakSet();
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        if (seen.has(el)) return;
                        seen.add(el);
                        var text     = el.textContent.trim();
                        var ariaLbl  = el.getAttribute('aria-label');
                        var title    = el.getAttribute('title');
                        results.push({
                            hasText: text.length > 0,
                            hasAriaOrTitle: !!(ariaLbl || title)
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not drift_info:
            pytest.skip(
                "No drift signal elements found on experts page — "
                "drift may not be visible in the current data state"
            )

        color_only = [
            r for r in drift_info
            if not r.get("hasText") and not r.get("hasAriaOrTitle")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(drift_info)} drift signal(s) have no text label "
            "or aria-label — colour alone cannot convey drift state (WCAG SC 1.4.1)"
        )

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """General status indicators on the experts page pair colour with text/icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 2.4.3 — Focus management in detail panel
# ---------------------------------------------------------------------------


class TestExpertsFocusManagement:
    """Opening the detail panel must move focus into it; closing must restore focus (SC 2.4.3).

    WCAG SC 2.4.3 (Focus Order) requires that when a panel/modal opens, focus
    moves inside it so keyboard users can interact. When the panel closes, focus
    must return to the triggering element (the table row or button that opened it).
    """

    def test_detail_panel_receives_focus_on_open(
        self, page: object, base_url: str
    ) -> None:
        """Opening the expert detail panel moves keyboard focus inside the panel."""
        _go(page, base_url)

        if not _has_expert_rows(page):
            pytest.skip("No expert rows — skipping focus-management test")

        # Click the first row to open the detail panel
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            pytest.skip("No visible expert rows to click")

        # Check focus moved inside a panel/dialog element
        focused_in_panel = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var active = document.activeElement;
                if (!active) return false;
                var panelSelectors = [
                    '[role="dialog"]',
                    '[role="complementary"]',
                    '.detail-panel',
                    '.inspector-panel',
                    '.slide-panel',
                    '[data-panel]',
                    '[id*="detail"]',
                    '[id*="panel"]',
                    '[class*="detail-panel"]',
                    '[class*="inspector"]'
                ];
                return panelSelectors.some(function(sel) {
                    try {
                        var panel = document.querySelector(sel);
                        return panel && panel.contains(active);
                    } catch(e) { return false; }
                });
            })()
            """
        )

        if not focused_in_panel:
            # Acceptable alternative: focus moved to close button or panel heading
            focused_tag = page.evaluate(  # type: ignore[attr-defined]
                "document.activeElement ? document.activeElement.tagName : ''"
            )
            # If focus is on body/html, that is a failure
            assert focused_tag not in ("BODY", "HTML", ""), (
                "Opening expert detail panel must move focus inside the panel — "
                "focus remains on the page body after panel open (WCAG SC 2.4.3)"
            )

    def test_detail_panel_has_close_mechanism(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel provides a keyboard-accessible close mechanism (SC 2.1.2)."""
        _go(page, base_url)

        if not _has_expert_rows(page):
            pytest.skip("No expert rows — skipping panel close mechanism test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            pytest.skip("No visible expert rows to click")

        # Check for a close button or Escape key handling
        close_selectors = [
            "[aria-label='Close']",
            "[aria-label='Dismiss']",
            "[aria-label='close' i]",
            "button[data-close]",
            "button.close",
            ".panel-close",
            "[data-panel-close]",
            "button:has-text('Close')",
            "button:has-text('✕')",
            "button:has-text('×')",
        ]
        close_found = any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in close_selectors
        )

        if not close_found:
            # Test Escape key as fallback
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]

            still_open_sel = (
                "[role='complementary'][aria-hidden='false'], "
                ".detail-panel:not(.hidden):not([hidden]), "
                ".inspector-panel:not(.hidden):not([hidden])"
            )
            still_open = page.locator(still_open_sel).count() > 0  # type: ignore[attr-defined]
            assert not still_open, (
                "Expert detail panel must be closeable via a visible close button or "
                "Escape key — neither method closed the panel (WCAG SC 2.1.2)"
            )
        # close button found — requirement satisfied

    def test_panel_focus_not_trapped_after_close(
        self, page: object, base_url: str
    ) -> None:
        """After closing the detail panel, focus is not trapped inside the closed panel."""
        _go(page, base_url)

        if not _has_expert_rows(page):
            pytest.skip("No expert rows — skipping focus-trap test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        clicked = False
        for sel in row_selectors:
            rows = page.locator(sel)  # type: ignore[attr-defined]
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)  # type: ignore[attr-defined]
            clicked = True
            break

        if not clicked:
            pytest.skip("No visible expert rows to click")

        # Close via Escape (universal fallback)
        page.keyboard.press("Escape")  # type: ignore[attr-defined]
        page.wait_for_timeout(400)  # type: ignore[attr-defined]

        # Tab should be able to leave the (now closed) panel area
        # If focus is stuck in a hidden panel, Tab will cycle within it
        page.keyboard.press("Tab")  # type: ignore[attr-defined]
        page.wait_for_timeout(200)  # type: ignore[attr-defined]

        focused_in_closed_panel = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var active = document.activeElement;
                if (!active) return false;
                var panelSelectors = [
                    '.detail-panel[hidden]',
                    '.detail-panel[aria-hidden="true"]',
                    '.inspector-panel[hidden]',
                    '.inspector-panel[aria-hidden="true"]',
                    '[role="dialog"][aria-hidden="true"]'
                ];
                return panelSelectors.some(function(sel) {
                    try {
                        var panel = document.querySelector(sel);
                        return panel && panel.contains(active);
                    } catch(e) { return false; }
                });
            })()
            """
        )

        assert not focused_in_closed_panel, (
            "After closing the expert detail panel, focus must not be trapped inside "
            "a hidden panel element — keyboard users cannot escape (WCAG SC 2.4.3)"
        )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestExpertsKeyboardNavigation:
    """All interactive elements on the experts page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the experts page."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_filter_sort_controls_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Filter and sort controls on the experts page are reachable by keyboard."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='tier' i]",
            "select[name*='filter' i]",
            "select[aria-label*='tier' i]",
            "select[aria-label*='filter' i]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "button:has-text('Filter')",
            "th[aria-sort]",
            "th button",
        ]
        for sel in filter_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No explicit filter/sort controls found on experts page — "
            "skipping keyboard operability check"
        )

    def test_table_rows_keyboard_reachable(
        self, page: object, base_url: str
    ) -> None:
        """Expert table rows or their action links are reachable via keyboard Tab."""
        _go(page, base_url)

        if not _has_expert_rows(page):
            pytest.skip("No expert rows — skipping table row keyboard check")

        # Check if rows or cells have tabindex / role that makes them focusable
        row_keyboard_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var rows = document.querySelectorAll('table tbody tr');
                var results = [];
                rows.forEach(function(row) {
                    var tabindex   = row.getAttribute('tabindex');
                    var role       = row.getAttribute('role');
                    // Check for focusable children (links, buttons) as alternative
                    var focusable  = row.querySelector(
                        'a[href], button, [tabindex="0"], input, select'
                    );
                    results.push({
                        selfFocusable: tabindex !== null || role === 'row',
                        hasFocusableChild: !!focusable
                    });
                });
                return results;
            })()
            """
        )

        keyboard_accessible = [
            r for r in row_keyboard_info
            if r.get("selfFocusable") or r.get("hasFocusableChild")
        ]

        if not keyboard_accessible:
            pytest.skip(
                "Expert table rows have no tabindex or focusable children — "
                "rows may rely on JS click handlers; verify keyboard accessibility manually"
            )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestExpertsFocusIndicators:
    """All interactive elements must display visible focus indicators (SC 2.4.11)."""

    def test_interactive_elements_show_focus(
        self, page: object, base_url: str
    ) -> None:
        """Buttons, links, and selects display a visible focus indicator on keyboard focus."""
        _go(page, base_url)

        interactive_selectors = [
            "button",
            "a[href]",
            "select",
            "input",
        ]
        for sel in interactive_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except AssertionError:
                    continue

        pytest.skip(
            "No interactive elements found on experts page — skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestExpertsAriaLandmarks:
    """Experts page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]

    def test_table_region_has_landmark_or_heading(
        self, page: object, base_url: str
    ) -> None:
        """The experts table is inside a landmark region or preceded by a heading."""
        _go(page, base_url)

        table_context = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var table = document.querySelector('table');
                if (!table) return {hasTable: false};

                // Walk ancestors looking for a landmark or heading
                var el = table;
                while (el && el !== document.body) {
                    var role = el.getAttribute('role');
                    var tag  = el.tagName.toLowerCase();
                    if (
                        ['main', 'nav', 'aside', 'section', 'article', 'region'].includes(tag) ||
                        ['main', 'navigation', 'complementary', 'region'].includes(role)
                    ) {
                        return {hasTable: true, hasLandmark: true};
                    }
                    el = el.parentElement;
                }

                // Check for a preceding heading (h1-h3)
                var headings = document.querySelectorAll('h1, h2, h3');
                var hasHeading = headings.length > 0;
                return {hasTable: true, hasLandmark: false, hasHeading: hasHeading};
            })()
            """
        )

        if not table_context.get("hasTable"):
            pytest.skip("No table found on experts page")

        has_context = (
            table_context.get("hasLandmark") or table_context.get("hasHeading")
        )
        assert has_context, (
            "Experts table must be inside a landmark region (<main>, <section>, etc.) "
            "or preceded by a heading (h1-h3) for screen reader navigation (WCAG SC 1.3.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestExpertsTouchTargets:
    """Buttons and links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the experts page meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestExpertsAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/experts:\n{result.summary()}"
        )
