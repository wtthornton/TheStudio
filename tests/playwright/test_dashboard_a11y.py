"""Epic 59.5 — Fleet Dashboard: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/dashboard meets WCAG 2.2 AA accessibility requirements:

  - Focus indicators are visible on all interactive elements (SC 2.4.11)
  - Keyboard navigation reaches all interactive elements in logical order (SC 2.1.1)
  - ARIA landmark regions are present (SC 1.3.6)
  - Repo activity table headers have scope attributes (SC 1.3.1)
  - Status/health indicator elements pair colour with text or icon (SC 1.4.1)
  - Buttons and links meet minimum 24×24 px touch target size (SC 2.5.8)
  - axe-core WCAG 2.x AA audit reports zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_dashboard_intent.py (Epic 59.1).
Style compliance is covered in test_dashboard_style.py (Epic 59.3).
Interactions are covered in test_dashboard_interactions.py (Epic 59.4).
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

DASHBOARD_URL = "/admin/ui/dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the dashboard and wait for content to settle."""
    navigate(page, f"{base_url}{DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Focus indicators (WCAG 2.2 SC 2.4.11)
# ---------------------------------------------------------------------------


class TestDashboardFocusIndicators:
    """Every interactive element must show a visible focus ring on keyboard focus."""

    def test_all_interactive_elements_have_focus_ring(self, page, base_url: str) -> None:
        """Tab to each focusable element — each must show a 2 px outline or box-shadow ring."""
        _go(page, base_url)

        result = assert_focus_visible(page)
        assert result.passed, result.summary()

    def test_focus_ring_not_removed_by_stylesheet(self, page, base_url: str) -> None:
        """No element should have outline:none without an alternative focus indicator."""
        _go(page, base_url)

        # Use JS to check for outline:none without box-shadow replacement
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


class TestDashboardKeyboardNavigation:
    """All interactive elements must be reachable by Tab in a logical DOM order."""

    def test_interactive_elements_reachable_by_keyboard(self, page, base_url: str) -> None:
        """Dashboard must expose at least one focusable interactive element."""
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

    def test_skip_link_or_main_anchor_present(self, page, base_url: str) -> None:
        """A skip-to-main-content link or named main landmark must be present."""
        _go(page, base_url)

        # Accept either a skip link or at least one <main> element
        skip_link = page.locator(
            "a[href='#main'], a[href='#content'], a[href='#main-content'], "
            "a[href*='skip'], a[aria-label*='skip' i]"
        ).count()

        main_element = page.locator("main, [role='main']").count()

        assert skip_link > 0 or main_element > 0, (
            "Dashboard must have a skip-to-main link or a <main> landmark "
            "so keyboard users can bypass repeated navigation"
        )


# ---------------------------------------------------------------------------
# ARIA landmark regions (WCAG 2.2 SC 1.3.6)
# ---------------------------------------------------------------------------


class TestDashboardAriaLandmarks:
    """Required ARIA landmark regions must be present."""

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
            "(required when multiple nav regions exist so screen-reader users can distinguish them)"
        )


# ---------------------------------------------------------------------------
# Table accessibility — repo activity table (WCAG 2.2 SC 1.3.1)
# ---------------------------------------------------------------------------


class TestDashboardTableAccessibility:
    """Repo activity table must use proper th[scope] semantics."""

    def test_repo_activity_table_th_scope(self, page, base_url: str) -> None:
        """Every <th> in the repo activity table must have scope='col' or scope='row'."""
        _go(page, base_url)

        tables = page.locator("table").count()
        if tables == 0:
            pytest.skip("No <table> elements found — repo activity may not be loaded")

        result = assert_table_accessibility(page, selector="table")
        assert result.passed, result.summary()

    def test_table_has_caption_or_aria_label(self, page, base_url: str) -> None:
        """Data tables must have an accessible name via <caption> or aria-label."""
        _go(page, base_url)

        tables_info = page.evaluate("""
        () => Array.from(document.querySelectorAll('table')).map(table => ({
            hasCaption: !!table.querySelector('caption'),
            ariaLabel: table.getAttribute('aria-label') || '',
            ariaLabelledBy: table.getAttribute('aria-labelledby') || '',
        }))
        """)

        if not tables_info:
            pytest.skip("No <table> elements found")

        unnamed = [
            i for i, t in enumerate(tables_info)
            if not t.get("hasCaption") and not t.get("ariaLabel") and not t.get("ariaLabelledBy")
        ]

        assert not unnamed, (
            f"{len(unnamed)} table(s) at index(es) {unnamed} have no accessible name "
            "— add <caption>, aria-label, or aria-labelledby"
        )


# ---------------------------------------------------------------------------
# Colour-only status indicators (WCAG 2.2 SC 1.4.1)
# ---------------------------------------------------------------------------


class TestDashboardColorOnlyIndicators:
    """Status indicators must pair colour with text, icon, or accessible label."""

    def test_health_status_badges_not_color_only(self, page, base_url: str) -> None:
        """System health and workflow status badges must not rely on colour alone."""
        _go(page, base_url)

        result = assert_no_color_only_indicators(page)
        assert result.passed, result.summary()

    def test_status_elements_have_text_or_aria_label(self, page, base_url: str) -> None:
        """Elements with data-status or common status class names carry visible text or aria-label."""
        _go(page, base_url)

        status_elements = page.evaluate("""
        () => {
            const sel = '[data-status], [class*="status-"], [class*="-status"]';
            return Array.from(document.querySelectorAll(sel)).map(el => ({
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim().slice(0, 40),
                ariaLabel: el.getAttribute('aria-label') || '',
                title: el.getAttribute('title') || '',
                hasIcon: !!el.querySelector('svg, img, [class*="icon"]'),
            }));
        }
        """)

        if not status_elements:
            pytest.skip("No [data-status] or status-class elements found on dashboard")

        color_only = [
            e for e in status_elements
            if not e.get("text") and not e.get("ariaLabel") and not e.get("title") and not e.get("hasIcon")
        ]

        assert not color_only, (
            f"{len(color_only)} status element(s) convey state through colour only: "
            + ", ".join(f"<{e['tag']}>" for e in color_only[:5])
        )


# ---------------------------------------------------------------------------
# Touch target sizes (WCAG 2.2 SC 2.5.8)
# ---------------------------------------------------------------------------


class TestDashboardTouchTargets:
    """All interactive elements must meet the 24×24 px minimum touch target."""

    def test_buttons_and_links_meet_minimum_size(self, page, base_url: str) -> None:
        """Visible buttons and links must be at least 24×24 px."""
        _go(page, base_url)

        result = assert_touch_targets(page, min_width=24, min_height=24)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# axe-core WCAG 2.x AA audit (comprehensive)
# ---------------------------------------------------------------------------


class TestDashboardAxeAudit:
    """Full axe-core WCAG 2.x AA audit must report zero critical/serious violations."""

    def test_no_axe_critical_violations(self, page, base_url: str) -> None:
        """axe-core must find zero critical violations on the dashboard."""
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
        """axe-core must find zero serious violations on the dashboard."""
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
        """axe-core must find zero moderate violations on the dashboard."""
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

            # Fail only if critical or serious — moderate/minor are advisory here
            blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
            report = "\n".join(summary_lines)
            assert not blocking, (
                f"Dashboard has {len(blocking)} blocking axe violation(s) "
                f"({len(violations)} total):\n{report}"
            )
        else:
            assert True, "No axe violations found — dashboard is fully WCAG 2.x AA compliant"
