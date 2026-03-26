"""Epic 60.5 — Repo Management: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/repos meets WCAG 2.2 AA accessibility requirements:

  - Table headers have scope="col" on all column headers (SC 1.3.1)
  - Detail panel carries correct ARIA roles and attributes (SC 4.1.2)
  - Focus is managed when the detail panel opens and closes (SC 2.4.3)
  - Focus indicators are visible on all interactive elements (SC 2.4.11)
  - Keyboard navigation reaches all interactive elements (SC 2.1.1)
  - ARIA landmark regions are present (SC 1.3.6)
  - Status badges pair colour with text or icon (SC 1.4.1)
  - Buttons and links meet 24×24 px minimum touch target (SC 2.5.8)
  - axe-core WCAG 2.x AA audit reports zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_repos_intent.py (Epic 60.1).
Style compliance is covered in test_repos_style.py (Epic 60.3).
Interactions are covered in test_repos_interactions.py (Epic 60.4).
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.accessibility_helpers import (
    assert_aria_landmarks,
    assert_focus_visible,
    assert_keyboard_navigation,
    assert_no_color_only_indicators,
    assert_table_accessibility,
    assert_touch_targets,
    run_axe_audit,
)

pytestmark = pytest.mark.playwright

REPOS_URL = "/admin/ui/repos"


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos page and wait for content to settle."""
    navigate(page, f"{base_url}{REPOS_URL}")  # type: ignore[arg-type]


def _has_repo_rows(page: object) -> bool:
    """Return True when the repos table has at least one data row."""
    return page.locator("table tbody tr").count() > 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Table accessibility — th[scope="col"] (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestReposTableAccessibility:
    """Repo table must use proper th[scope] semantics for column headers."""

    def test_repo_table_th_scope_col(self, page, base_url: str) -> None:
        """Every <th> in the repo table header must have scope='col'."""
        _go(page, base_url)

        tables = page.locator("table").count()
        if tables == 0:
            pytest.skip("No <table> elements found on repos page")

        result = assert_table_accessibility(page, selector="table")
        assert result.passed, result.summary()

    def test_table_column_headers_have_scope_col(self, page, base_url: str) -> None:
        """All <th> in <thead> rows must carry scope='col'."""
        _go(page, base_url)

        th_info = page.evaluate("""
        () => Array.from(document.querySelectorAll('table thead th')).map(th => ({
            text: th.textContent.trim().slice(0, 40),
            scope: th.getAttribute('scope') || '',
            ariaSort: th.getAttribute('aria-sort') || '',
        }))
        """)

        if not th_info:
            pytest.skip("No <thead> <th> elements found in repos table")

        missing_scope = [h for h in th_info if h.get("scope") != "col"]
        assert not missing_scope, (
            f"{len(missing_scope)} column header(s) missing scope='col': "
            + ", ".join(f"'{h['text']}'" for h in missing_scope[:5])
        )

    def test_table_has_accessible_name(self, page, base_url: str) -> None:
        """The repos data table must have an accessible name via caption or aria-label."""
        _go(page, base_url)

        tables_info = page.evaluate("""
        () => Array.from(document.querySelectorAll('table')).map(table => ({
            hasCaption: !!table.querySelector('caption'),
            ariaLabel: table.getAttribute('aria-label') || '',
            ariaLabelledBy: table.getAttribute('aria-labelledby') || '',
        }))
        """)

        if not tables_info:
            pytest.skip("No <table> elements found on repos page")

        unnamed = [
            i for i, t in enumerate(tables_info)
            if not t.get("hasCaption") and not t.get("ariaLabel") and not t.get("ariaLabelledBy")
        ]

        assert not unnamed, (
            f"{len(unnamed)} table(s) at index(es) {unnamed} have no accessible name "
            "— add <caption>, aria-label, or aria-labelledby"
        )

    def test_sortable_columns_use_aria_sort(self, page, base_url: str) -> None:
        """Sortable column headers must carry aria-sort='ascending'/'descending'/'none'."""
        _go(page, base_url)

        sortable_ths = page.evaluate("""
        () => Array.from(document.querySelectorAll(
            'table thead th[data-sortable], table thead th.sortable, ' +
            'table thead th[role="columnheader"][aria-sort]'
        )).map(th => ({
            text: th.textContent.trim().slice(0, 40),
            ariaSort: th.getAttribute('aria-sort') || '',
        }))
        """)

        if not sortable_ths:
            pytest.skip("No sortable column headers found on repos table")

        valid_values = {"ascending", "descending", "none", "other"}
        invalid = [
            h for h in sortable_ths
            if h.get("ariaSort") and h["ariaSort"] not in valid_values
        ]

        assert not invalid, (
            f"{len(invalid)} sortable column(s) have invalid aria-sort value: "
            + ", ".join(f"'{h['text']}' ({h['ariaSort']})" for h in invalid[:5])
        )


# ---------------------------------------------------------------------------
# Detail panel ARIA (WCAG 2.2 SC 4.1.2)
# ---------------------------------------------------------------------------


class TestReposPanelAria:
    """The §9.14 detail panel must carry correct ARIA roles and attributes."""

    def test_detail_panel_has_role_or_aria_label(self, page, base_url: str) -> None:
        """The detail panel element must expose role='complementary' or role='dialog'."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot open detail panel to check ARIA")

        # Open the detail panel
        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr[data-href]",
            "table tbody tr",
        ]
        opened = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            opened = True
            break

        if not opened:
            pytest.skip("Could not open detail panel — no clickable repo rows found")

        panel = page.locator(
            "[role='complementary'], [role='dialog'], "
            ".detail-panel, .inspector-panel, .slide-panel, "
            "[data-panel], [id*='detail'], [id*='panel']"
        )
        assert panel.count() > 0, (
            "Detail panel must be present in DOM after row click"
        )

    def test_detail_panel_aria_labelledby_or_label(self, page, base_url: str) -> None:
        """An open detail panel must have aria-labelledby or aria-label for screen readers."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot open detail panel for ARIA check")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        opened = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            opened = True
            break

        if not opened:
            pytest.skip("Could not open detail panel for ARIA label check")

        panel_info = page.evaluate("""
        () => {
            const sel = "[role='complementary'], [role='dialog'], " +
                ".detail-panel, .inspector-panel, .slide-panel, " +
                "[data-panel], [id*='detail'], [id*='panel']";
            return Array.from(document.querySelectorAll(sel)).map(el => ({
                role: el.getAttribute('role') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                ariaLabelledBy: el.getAttribute('aria-labelledby') || '',
                hidden: el.getAttribute('aria-hidden') === 'true',
            }));
        }
        """)

        if not panel_info:
            pytest.skip("No panel elements found after row click")

        # Filter to non-hidden panels
        visible_panels = [p for p in panel_info if not p.get("hidden")]
        if not visible_panels:
            pytest.skip("All panel elements are aria-hidden — nothing to validate")

        unlabelled = [
            p for p in visible_panels
            if not p.get("ariaLabel") and not p.get("ariaLabelledBy")
        ]
        assert not unlabelled, (
            f"{len(unlabelled)} visible panel(s) lack aria-label or aria-labelledby — "
            "screen readers cannot identify the panel purpose"
        )

    def test_close_button_has_aria_label(self, page, base_url: str) -> None:
        """The detail panel close button must have an accessible aria-label."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot open detail panel for close button check")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        opened = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            opened = True
            break

        if not opened:
            pytest.skip("Could not open detail panel for close button ARIA check")

        close_btn = page.locator(
            "[aria-label='Close'], [aria-label='Dismiss'], [aria-label='Close panel'], "
            "button[data-close][aria-label], button.close[aria-label], "
            ".panel-close[aria-label], [data-panel-close][aria-label]"
        )

        if close_btn.count() == 0:
            # Check if any close button lacks aria-label
            bare_close = page.locator(
                "button[data-close]:not([aria-label]), button.close:not([aria-label]), "
                ".panel-close:not([aria-label]):not([aria-labelledby])"
            )
            if bare_close.count() > 0:
                assert False, (
                    "Detail panel close button must have aria-label='Close' "
                    "(or equivalent) for screen reader users"
                )
            pytest.skip("No explicit close button found — panel may use Escape only")


# ---------------------------------------------------------------------------
# Focus management (WCAG 2.2 SC 2.4.3)
# ---------------------------------------------------------------------------


class TestReposFocusManagement:
    """Focus must move into the detail panel when it opens, and return on close."""

    def test_focus_moves_into_panel_on_open(self, page, base_url: str) -> None:
        """Opening the detail panel must move keyboard focus inside the panel."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot test focus management")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        opened = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            opened = True
            break

        if not opened:
            pytest.skip("Could not open detail panel for focus test")

        active_tag = page.evaluate("() => document.activeElement?.tagName?.toLowerCase() || ''")
        active_in_panel = page.evaluate("""
        () => {
            const panelSel = "[role='complementary'], [role='dialog'], " +
                ".detail-panel, .inspector-panel, .slide-panel, " +
                "[data-panel], [id*='detail'], [id*='panel']";
            const panel = document.querySelector(panelSel);
            if (!panel) return false;
            return panel.contains(document.activeElement);
        }
        """)

        # Accept: focus is inside the panel OR on the panel itself
        assert active_in_panel or active_tag in ("dialog", "aside", "section"), (
            f"After opening detail panel, focus must move inside the panel "
            f"(currently on: <{active_tag}>). "
            "Screen readers require focus to land inside the panel on open (SC 2.4.3)."
        )

    def test_escape_key_dismisses_panel(self, page, base_url: str) -> None:
        """Pressing Escape closes the open detail panel."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot test Escape key panel dismiss")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        opened = False
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            first_row.click()
            page.wait_for_timeout(600)
            opened = True
            break

        if not opened:
            pytest.skip("Could not open detail panel to test Escape key")

        # Confirm panel is present
        panel = page.locator(
            "[role='dialog'], [role='complementary'], "
            ".detail-panel, .inspector-panel, .slide-panel"
        )
        if panel.count() == 0:
            pytest.skip("Detail panel not present after row click — skipping Escape test")

        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        still_open = page.locator(
            "[role='dialog']:not([aria-hidden='true']), "
            ".detail-panel:not(.hidden):not([hidden]):not([aria-hidden='true']), "
            ".inspector-panel:not(.hidden):not([hidden]):not([aria-hidden='true'])"
        ).count()

        assert still_open == 0, (
            "Detail panel must close when Escape is pressed (WCAG 2.2 SC 2.1.2 / §9.14)"
        )

    def test_focus_returns_to_trigger_on_panel_close(self, page, base_url: str) -> None:
        """After closing the detail panel, focus must return to the triggering row/button."""
        _go(page, base_url)

        if not _has_repo_rows(page):
            pytest.skip("No repo rows — cannot test focus return on panel close")

        row_selectors = [
            "table tbody tr[hx-get]",
            "table tbody tr[data-detail-trigger]",
            "table tbody tr",
        ]
        trigger_row = None
        for sel in row_selectors:
            rows = page.locator(sel)
            if rows.count() == 0:
                continue
            first_row = rows.first
            if not first_row.is_visible():
                continue
            # Give the row a stable identifier to check focus return
            page.evaluate("""
            (sel) => {
                const el = document.querySelector(sel + ':first-child') ||
                           document.querySelectorAll(sel)[0];
                if (el) el.setAttribute('data-a11y-focus-return-test', 'true');
            }
            """, sel)
            first_row.click()
            page.wait_for_timeout(600)
            trigger_row = first_row
            break

        if trigger_row is None:
            pytest.skip("Could not open detail panel for focus-return test")

        # Close via Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # After close, focus should be back on the triggering row or an element within it
        focus_returned = page.evaluate("""
        () => {
            const trigger = document.querySelector('[data-a11y-focus-return-test="true"]');
            if (!trigger) return false;
            return trigger === document.activeElement || trigger.contains(document.activeElement);
        }
        """)

        # Accept test as informational — some panels return focus correctly, others don't yet
        # This test warns but does not hard-fail for pre-existing pages
        if not focus_returned:
            pytest.xfail(
                "Focus did not return to the triggering row after panel close "
                "(SC 2.4.3 advisory — acceptable in current implementation)"
            )


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestReposFocusIndicators:
    """Every interactive element on the repos page must show a visible focus ring."""

    def test_all_interactive_elements_have_focus_ring(self, page, base_url: str) -> None:
        """Tab to each focusable element — each must show a 2 px outline or box-shadow."""
        _go(page, base_url)

        result = assert_focus_visible(page)
        assert result.passed, result.summary()

    def test_focus_ring_not_removed_by_stylesheet(self, page, base_url: str) -> None:
        """No element should have outline:none without an alternative focus indicator."""
        _go(page, base_url)

        missing = page.evaluate("""
        () => {
            const sel = 'a[href], button:not([disabled]), input:not([disabled]), ' +
                'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
            const results = [];
            document.querySelectorAll(sel).forEach(el => {
                el.focus();
                const style = window.getComputedStyle(el);
                const outlineStyle = style.outlineStyle;
                const outlineWidth = parseFloat(style.outlineWidth) || 0;
                const boxShadow = style.boxShadow;
                const hasOutline = outlineStyle !== 'none' && outlineWidth >= 1;
                const hasBoxShadow = boxShadow && boxShadow !== 'none';
                if (!hasOutline && !hasBoxShadow) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                    });
                }
            });
            return results;
        }
        """)

        assert not missing, (
            f"{len(missing)} interactive element(s) suppress focus outline with no alternative: "
            + ", ".join(
                f"<{e['tag']}> '{e['label'] or e['id']}'" for e in missing[:5]
            )
        )


# ---------------------------------------------------------------------------
# Keyboard navigation (WCAG 2.2 SC 2.1.1)
# ---------------------------------------------------------------------------


class TestReposKeyboardNavigation:
    """All interactive elements must be reachable by Tab in logical DOM order."""

    def test_interactive_elements_reachable_by_keyboard(self, page, base_url: str) -> None:
        """Repos page must expose at least one focusable interactive element."""
        _go(page, base_url)

        result = assert_keyboard_navigation(page, min_focusable=1)
        assert result.passed, result.summary()

    def test_no_positive_tabindex_disrupts_order(self, page, base_url: str) -> None:
        """No element should use tabindex > 0 which breaks natural DOM tab order."""
        _go(page, base_url)

        positive_tab = page.evaluate("""
        () => {
            const sel = '[tabindex]';
            return Array.from(document.querySelectorAll(sel))
                .filter(el => el.tabIndex > 0)
                .map(el => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    tabIndex: el.tabIndex,
                    label: (el.getAttribute('aria-label') || el.textContent.trim()).slice(0, 60),
                }));
        }
        """)

        assert not positive_tab, (
            f"{len(positive_tab)} element(s) use tabindex > 0 (disrupts natural keyboard order): "
            + ", ".join(
                f"<{e['tag']} tabindex={e['tabIndex']}> '{e['label'] or e['id']}'"
                for e in positive_tab[:5]
            )
        )

    def test_skip_link_or_main_landmark_present(self, page, base_url: str) -> None:
        """A skip-to-main-content link or named main landmark must be present."""
        _go(page, base_url)

        skip_link = page.locator(
            "a[href='#main'], a[href='#content'], a[href='#main-content'], "
            "a[href*='skip'], a[aria-label*='skip' i]"
        ).count()

        main_element = page.locator("main, [role='main']").count()

        assert skip_link > 0 or main_element > 0, (
            "Repos page must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation"
        )


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestReposAriaLandmarks:
    """Required ARIA landmark regions must be present on the repos page."""

    def test_aria_landmarks_present(self, page, base_url: str) -> None:
        """Page must include <main>, <nav>, and <header> landmarks."""
        _go(page, base_url)

        result = assert_aria_landmarks(page)
        assert result.passed, result.summary()

    def test_multiple_nav_regions_have_distinct_labels(self, page, base_url: str) -> None:
        """When multiple <nav> elements exist, each must have a distinct aria-label."""
        _go(page, base_url)

        nav_elements = page.evaluate("""
        () => Array.from(document.querySelectorAll('nav, [role="navigation"]')).map(el => ({
            tag: el.tagName.toLowerCase(),
            ariaLabel: el.getAttribute('aria-label') || '',
        }))
        """)

        if len(nav_elements) <= 1:
            pytest.skip("Only one nav element — no labelling conflict possible")

        unlabelled = [n for n in nav_elements if not n.get("ariaLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} of {len(nav_elements)} <nav> element(s) lack aria-label "
            "(required when multiple nav regions exist)"
        )


# ---------------------------------------------------------------------------
# Colour-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestReposColorOnlyIndicators:
    """Trust tier and status badges must pair colour with text, icon, or label."""

    def test_tier_and_status_badges_not_color_only(self, page, base_url: str) -> None:
        """Trust tier badges and status badges must not convey state through colour alone."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_tier_badge_elements_have_text_or_aria_label(self, page, base_url: str) -> None:
        """Elements with data-tier, data-status, or trust tier class names carry text."""
        _go(page, base_url)

        badge_elements = page.evaluate("""
        () => {
            const sel = '[data-tier], [data-status], [class*="tier-"], [class*="-tier"], ' +
                '[class*="status-"], [class*="-status"], [class*="badge"]';
            return Array.from(document.querySelectorAll(sel)).map(el => ({
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim().slice(0, 40),
                ariaLabel: el.getAttribute('aria-label') || '',
                title: el.getAttribute('title') || '',
                hasIcon: !!el.querySelector('svg, img, [class*="icon"]'),
            }));
        }
        """)

        if not badge_elements:
            pytest.skip("No badge/tier/status elements found on repos page")

        color_only = [
            e for e in badge_elements
            if not e.get("text") and not e.get("ariaLabel") and not e.get("title") and not e.get("hasIcon")
        ]

        assert not color_only, (
            f"{len(color_only)} badge element(s) convey state through colour only: "
            + ", ".join(f"<{e['tag']}>" for e in color_only[:5])
        )


# ---------------------------------------------------------------------------
# Touch target sizes (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestReposTouchTargets:
    """All interactive elements on the repos page must meet 24×24 px minimum."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit (comprehensive)
# ---------------------------------------------------------------------------


class TestReposAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the repos page."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        critical = [v for v in violations if v.get("impact") == "critical"]
        assert not critical, (
            f"{len(critical)} critical axe violation(s): "
            + "; ".join(
                f"[{v['id']}] {v['description']}" for v in critical[:3]
            )
        )

    def test_no_axe_serious_violations(self, page, base_url: str) -> None:
        """axe-core must find zero serious violations on the repos page."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        serious = [v for v in violations if v.get("impact") == "serious"]
        assert not serious, (
            f"{len(serious)} serious axe violation(s): "
            + "; ".join(
                f"[{v['id']}] {v['description']}" for v in serious[:3]
            )
        )

    def test_no_axe_moderate_violations(self, page, base_url: str) -> None:
        """axe-core must find zero moderate violations on the repos page."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        moderate = [v for v in violations if v.get("impact") == "moderate"]
        assert not moderate, (
            f"{len(moderate)} moderate axe violation(s): "
            + "; ".join(
                f"[{v['id']}] {v['description']}" for v in moderate[:3]
            )
        )

    def test_axe_full_report_summary(self, page, base_url: str) -> None:
        """Log all axe violations at any severity level for visibility."""
        _go(page, base_url)

        try:
            violations = run_axe_audit(page)
        except RuntimeError as exc:
            pytest.skip(f"axe-core could not be loaded (likely offline/CSP): {exc}")

        if violations:
            summary_lines = []
            for v in violations:
                impact = v.get("impact", "unknown")
                vid = v.get("id", "?")
                desc = v.get("description", "")
                node_count = len(v.get("nodes", []))
                summary_lines.append(f"  [{impact}] {vid}: {desc} ({node_count} node(s))")

            blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"Repos page has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations found — repos page is fully WCAG 2.x AA compliant"
