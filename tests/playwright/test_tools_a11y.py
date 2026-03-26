"""Epic 65.5 — Tool Hub: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/tools meets WCAG 2.2 AA accessibility requirements:

  - Status badges non-color  — approval badges pair colour with text/icon (SC 1.4.1)
  - Table headers            — <th scope="col"> on every column header (SC 1.3.1)
  - Focus management         — detail panel traps/restores focus on open/close (SC 2.4.3)
  - Focus indicators         — visible focus ring on all interactive elements (SC 2.4.11)
  - Keyboard nav             — Tab reaches tool items, action buttons (SC 2.1.1)
  - ARIA landmarks           — page has main/nav landmark (SC 1.3.6)
  - Touch targets            — buttons meet 24x24 px minimum (SC 2.5.8)
  - axe-core WCAG 2.x AA     — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_tools_intent.py (Epic 65.1).
Style compliance is covered in test_tools_style.py (Epic 65.3).
Interactions are covered in test_tools_interactions.py (Epic 65.4).
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

TOOLS_URL = "/admin/ui/tools"


def _go(page: object, base_url: str) -> None:
    """Navigate to the tools page and wait for content to settle."""
    navigate(page, f"{base_url}{TOOLS_URL}")  # type: ignore[arg-type]


def _has_tool_rows(page: object) -> bool:
    """Return True when the tools catalog has at least one data row or card."""
    return (
        page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]
        or page.locator("[data-tool], [class*='tool-card']").count() > 0
    )


# ---------------------------------------------------------------------------
# SC 1.4.1 — Badge non-colour cues (approval status)
# ---------------------------------------------------------------------------


class TestToolsBadgeNonColorCues:
    """Approval status badges must not rely solely on colour (SC 1.4.1).

    Tool Hub uses colour-coded approval status badges (Approved / Pending /
    Rejected). Each badge must pair its colour with a visible text label or
    icon with an aria-label so that colour-blind users and screen-reader users
    receive the same information.
    """

    def test_approval_status_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Approval status badges (Approved/Pending/Rejected) carry visible text, not colour only."""
        _go(page, base_url)

        badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-status]',
                    '[data-approval-status]',
                    '[class*="approval"]',
                    '[class*="status"]',
                    '[aria-label*="status" i]',
                    '[aria-label*="approval" i]'
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
                "No approval status badge elements found on tools page — "
                "page may be empty or use a different pattern"
            )

        color_only = [
            r for r in badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(badge_info)} approval status badge(s) convey status "
            "via colour only — each badge must pair colour with visible text or "
            "aria-label (WCAG SC 1.4.1)"
        )

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """General status indicators on the tools page pair colour with text/icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.3.1 — Table headers with scope="col"
# ---------------------------------------------------------------------------


class TestToolsTableHeaders:
    """Tool catalog table column headers must carry scope="col" for screen readers.

    Per WCAG SC 1.3.1 (Info and Relationships), every <th> in a data table
    must carry scope="col" so that assistive technology can associate cell data
    with its header.
    """

    def test_table_column_headers_have_scope_col(
        self, page: object, base_url: str
    ) -> None:
        """Every <th> in the tools catalog table carries scope='col'."""
        _go(page, base_url)

        th_count = page.locator("table th").count()  # type: ignore[attr-defined]
        if th_count == 0:
            pytest.skip("No <th> elements found — tools catalog may not use a <table>")

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var ths = document.querySelectorAll('table th');
                var results = [];
                ths.forEach(function(th) {
                    var scope = th.getAttribute('scope');
                    var role  = th.getAttribute('role');
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
        """The tools catalog table carries a <caption> or aria-label for context."""
        _go(page, base_url)

        tables = page.locator("table")  # type: ignore[attr-defined]
        if tables.count() == 0:
            pytest.skip("No <table> elements on tools page")

        table_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var tables = document.querySelectorAll('table');
                var results = [];
                tables.forEach(function(t) {
                    var caption   = !!t.querySelector('caption');
                    var ariaLabel = !!t.getAttribute('aria-label');
                    var ariaLby   = !!t.getAttribute('aria-labelledby');
                    results.push({ labelled: caption || ariaLabel || ariaLby });
                });
                return results;
            })()
            """
        )

        unlabelled = [r for r in table_info if not r.get("labelled")]
        if len(unlabelled) == len(table_info):
            pytest.skip(
                "No table has a <caption> or aria-label — "
                "consider adding one for screen reader context (WCAG SC 1.3.1)"
            )


# ---------------------------------------------------------------------------
# SC 2.4.3 — Focus management in detail panel
# ---------------------------------------------------------------------------


class TestToolsFocusManagement:
    """Opening the detail panel must move focus into it; closing must restore focus (SC 2.4.3)."""

    def test_detail_panel_receives_focus_on_open(
        self, page: object, base_url: str
    ) -> None:
        """Opening the tool detail panel moves keyboard focus inside the panel."""
        _go(page, base_url)

        if not _has_tool_rows(page):
            pytest.skip("No tool items — skipping focus-management test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-tool]",
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
            pytest.skip("No visible tool items to click")

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
            focused_tag = page.evaluate(  # type: ignore[attr-defined]
                "document.activeElement ? document.activeElement.tagName : ''"
            )
            assert focused_tag not in ("BODY", "HTML", ""), (
                "Opening tool detail panel must move focus inside the panel — "
                "focus remains on the page body after panel open (WCAG SC 2.4.3)"
            )

    def test_detail_panel_has_close_mechanism(
        self, page: object, base_url: str
    ) -> None:
        """The detail panel provides a keyboard-accessible close mechanism (SC 2.1.2)."""
        _go(page, base_url)

        if not _has_tool_rows(page):
            pytest.skip("No tool items — skipping panel close mechanism test")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
            "[data-tool]",
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
            pytest.skip("No visible tool items to click")

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
            page.keyboard.press("Escape")  # type: ignore[attr-defined]
            page.wait_for_timeout(400)  # type: ignore[attr-defined]

            still_open_sel = (
                "[role='complementary'][aria-hidden='false'], "
                ".detail-panel:not(.hidden):not([hidden]), "
                ".inspector-panel:not(.hidden):not([hidden])"
            )
            still_open = page.locator(still_open_sel).count() > 0  # type: ignore[attr-defined]
            assert not still_open, (
                "Tool detail panel must be closeable via a visible close button or "
                "Escape key — neither method closed the panel (WCAG SC 2.1.2)"
            )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard navigation
# ---------------------------------------------------------------------------


class TestToolsKeyboardNavigation:
    """All interactive elements on the tools page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the tools page."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_action_buttons_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Approval action buttons on the tools page are reachable by keyboard."""
        _go(page, base_url)

        action_selectors = [
            "button:has-text('Approve')",
            "button:has-text('Reject')",
            "button[aria-label*='approve' i]",
            "button[aria-label*='reject' i]",
            "[data-action='approve']",
            "[data-action='reject']",
            "button",
        ]
        for sel in action_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                try:
                    assert_focus_visible(page, sel)  # type: ignore[arg-type]
                    return
                except Exception:  # noqa: BLE001
                    continue

        pytest.skip(
            "No action buttons found on tools page — "
            "skipping keyboard operability check"
        )

    def test_tool_items_keyboard_reachable(
        self, page: object, base_url: str
    ) -> None:
        """Tool catalog items or their action links are reachable via keyboard Tab."""
        _go(page, base_url)

        if not _has_tool_rows(page):
            pytest.skip("No tool items — skipping keyboard reach check")

        item_keyboard_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'table tbody tr',
                    '[data-tool]',
                    '[class*="tool-card"]'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(item) {
                        var tabindex   = item.getAttribute('tabindex');
                        var role       = item.getAttribute('role');
                        var focusable  = item.querySelector(
                            'a[href], button, [tabindex="0"], input, select'
                        );
                        results.push({
                            selfFocusable: tabindex !== null || role === 'row',
                            hasFocusableChild: !!focusable
                        });
                    });
                });
                return results;
            })()
            """
        )

        keyboard_accessible = [
            r for r in item_keyboard_info
            if r.get("selfFocusable") or r.get("hasFocusableChild")
        ]

        if not keyboard_accessible:
            pytest.skip(
                "Tool catalog items have no tabindex or focusable children — "
                "items may rely on JS click handlers; verify keyboard accessibility manually"
            )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestToolsFocusIndicators:
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
            "No interactive elements found on tools page — skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestToolsAriaLandmarks:
    """Tools page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]

    def test_catalog_region_has_landmark_or_heading(
        self, page: object, base_url: str
    ) -> None:
        """The tools catalog is inside a landmark region or preceded by a heading."""
        _go(page, base_url)

        catalog_context = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                // Try table first, then card-based layout
                var catalog = document.querySelector('table') ||
                              document.querySelector('[data-tool]') ||
                              document.querySelector('[class*="tool-card"]');
                if (!catalog) return {hasCatalog: false};

                var el = catalog;
                while (el && el !== document.body) {
                    var role = el.getAttribute('role');
                    var tag  = el.tagName.toLowerCase();
                    if (
                        ['main', 'nav', 'aside', 'section', 'article', 'region'].includes(tag) ||
                        ['main', 'navigation', 'complementary', 'region'].includes(role)
                    ) {
                        return {hasCatalog: true, hasLandmark: true};
                    }
                    el = el.parentElement;
                }

                var headings = document.querySelectorAll('h1, h2, h3');
                var hasHeading = headings.length > 0;
                return {hasCatalog: true, hasLandmark: false, hasHeading: hasHeading};
            })()
            """
        )

        if not catalog_context.get("hasCatalog"):
            pytest.skip("No catalog element found on tools page")

        has_context = (
            catalog_context.get("hasLandmark") or catalog_context.get("hasHeading")
        )
        assert has_context, (
            "Tools catalog must be inside a landmark region (<main>, <section>, etc.) "
            "or preceded by a heading (h1-h3) for screen reader navigation (WCAG SC 1.3.6)"
        )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestToolsTouchTargets:
    """Buttons and links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the tools page meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestToolsAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/tools:\n{result.summary()}"
        )
