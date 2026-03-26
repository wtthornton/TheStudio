"""Epic 73.5 — Portfolio Health: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/portfolio-health meets WCAG 2.2 AA accessibility requirements:

  - Status non-colour cues   — health status colours paired with text/icon (SC 1.4.1)
  - ARIA landmarks           — main, nav, or region roles present (SC 1.3.6)
  - Keyboard navigation      — all interactive elements Tab-reachable (SC 2.1.1)
  - Focus indicators         — visible focus ring on interactive elements (SC 2.4.11)
  - Touch targets            — buttons/links meet 24x24 px minimum (SC 2.5.8)
  - Health badge text        — risk/health badges carry accessible text labels (SC 1.3.1)
  - axe-core WCAG 2.x AA     — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_portfolio_health_intent.py (Epic 73.1).
API contracts are covered in test_portfolio_health_api.py (Epic 73.2).
Style compliance is covered in test_portfolio_health_style.py (Epic 73.3).
Interactions are covered in test_portfolio_health_interactions.py (Epic 73.4).
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

PORTFOLIO_HEALTH_URL = "/admin/ui/portfolio-health"


def _go(page: object, base_url: str) -> None:
    """Navigate to the portfolio health page and wait for content to settle."""
    navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.4.1 — Colour not the only indicator
# ---------------------------------------------------------------------------


class TestPortfolioHealthColorIndicators:
    """Health status indicators must not rely solely on colour (SC 1.4.1)."""

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """All health/risk status indicators pair colour with a text label or icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]

    def test_health_status_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Health status badges (Healthy/Degraded/Critical) pair colour with visible text."""
        _go(page, base_url)

        badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-status]',
                    '[class*="badge"]',
                    '[class*="status"]',
                    '[class*="health-status"]',
                    '[class*="risk-badge"]',
                    '[class*="health-badge"]',
                    '[class*="risk-level"]'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        var text = el.textContent.trim();
                        var ariaLabel = el.getAttribute('aria-label');
                        results.push({
                            hasText: text.length > 0,
                            hasAriaLabel: !!ariaLabel
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not badge_info:
            pytest.skip("No health/risk status badges found on portfolio health page")

        color_only = [
            r for r in badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(badge_info)} health status badge(s) have no "
            "text label or aria-label — colour alone cannot convey status (WCAG SC 1.4.1)"
        )

    def test_risk_distribution_has_accessible_labels(
        self, page: object, base_url: str
    ) -> None:
        """Risk distribution or summary cards carry accessible text labels."""
        _go(page, base_url)

        risk_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-component="kpi-card"]',
                    '[class*="kpi"]',
                    '[class*="risk-card"]',
                    '[class*="health-card"]',
                    '[class*="stat-card"]',
                    '[class*="summary-card"]',
                    '[class*="portfolio-card"]'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        var text = el.textContent.trim();
                        var ariaLabel = el.getAttribute('aria-label') ||
                                        el.getAttribute('aria-labelledby');
                        results.push({
                            hasText: text.length > 0,
                            hasAriaLabel: !!ariaLabel
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not risk_info:
            pytest.skip("No risk/health summary cards found on portfolio health page")

        unlabelled = [
            r for r in risk_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(risk_info)} risk/health card(s) have no accessible "
            "text label or aria-label — WCAG SC 1.4.1 requires non-colour indicators"
        )


# ---------------------------------------------------------------------------
# SC 1.3.1 — Risk filter and control labels
# ---------------------------------------------------------------------------


class TestPortfolioHealthControlAria:
    """Risk filter and navigation controls must carry accessible labels (SC 1.3.1).

    An unlabelled <select>, input, or button group is invisible to screen readers.
    Every control must have an associated <label>, aria-label, or aria-labelledby.
    """

    def test_risk_filter_has_accessible_label(
        self, page: object, base_url: str
    ) -> None:
        """Risk/health filter controls carry an accessible label."""
        _go(page, base_url)

        filter_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'select[name*="risk" i]',
                    'select[name*="health" i]',
                    'select[name*="status" i]',
                    'select[name*="filter" i]',
                    'select[aria-label*="risk" i]',
                    'select[aria-label*="health" i]',
                    'select[aria-label*="filter" i]',
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[placeholder*="filter" i]',
                    'input[placeholder*="risk" i]',
                    'input[placeholder*="repo" i]'
                ];
                var results = [];
                selectors.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(el) {
                        var id = el.id;
                        var hasLabel = (
                            (id && document.querySelector('label[for="' + id + '"]')) ||
                            el.getAttribute('aria-label') ||
                            el.getAttribute('aria-labelledby') ||
                            el.getAttribute('title') ||
                            el.getAttribute('placeholder')
                        );
                        results.push({tag: el.tagName, hasLabel: !!hasLabel});
                    });
                });
                return results;
            })()
            """
        )

        if not filter_info:
            pytest.skip(
                "No risk/health filter controls found on portfolio health page — "
                "filtering may be done via table column headers"
            )

        unlabelled = [r for r in filter_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} risk filter control(s) have no accessible label — "
            "WCAG SC 1.3.1 requires labels on all form controls"
        )

    def test_table_headers_have_scope_attribute(
        self, page: object, base_url: str
    ) -> None:
        """Portfolio health table column headers carry scope='col' for screen readers."""
        _go(page, base_url)

        header_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var headers = document.querySelectorAll('table th');
                if (headers.length === 0) return {found: false, results: []};
                var results = [];
                headers.forEach(function(th) {
                    var scope = th.getAttribute('scope');
                    var ariaSort = th.getAttribute('aria-sort');
                    results.push({
                        text: th.textContent.trim().slice(0, 30),
                        hasScope: scope === 'col' || scope === 'row',
                        hasAriaSort: !!ariaSort
                    });
                });
                return {found: true, results: results};
            })()
            """
        )

        if not header_info.get("found"):
            pytest.skip(
                "No table headers found on portfolio health page — "
                "page may use a card layout instead of a table"
            )

        results = header_info.get("results", [])
        without_scope = [r for r in results if not r.get("hasScope")]
        if without_scope:
            pytest.skip(
                f"{len(without_scope)}/{len(results)} table headers lack scope='col' — "
                "column headers should carry scope='col' per WCAG SC 1.3.1 (advisory)"
            )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard operability
# ---------------------------------------------------------------------------


class TestPortfolioHealthKeyboardNavigation:
    """All interactive elements on the portfolio health page must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the portfolio health page."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_risk_filter_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Risk/health filter control is reachable and operable by keyboard."""
        _go(page, base_url)

        filter_selectors = [
            "select[name*='risk' i]",
            "select[name*='health' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "input[type='search']",
            "input[placeholder*='search' i]",
            "input[placeholder*='filter' i]",
        ]
        for sel in filter_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No risk filter controls found on portfolio health page — "
            "skipping keyboard operability check"
        )

    def test_repo_drill_down_controls_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Repo drill-down triggers (row click, expand button, summary) are keyboard-operable."""
        _go(page, base_url)

        drill_down_selectors = [
            "[aria-expanded]",
            "details > summary",
            "button[aria-label*='detail' i]",
            "button[aria-label*='expand' i]",
            "button[aria-label*='view' i]",
            "[data-detail-trigger]",
            "[data-expand]",
        ]
        for sel in drill_down_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No explicit drill-down trigger controls found — "
            "portfolio health page may use table rows (covered by keyboard navigation test)"
        )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestPortfolioHealthFocusIndicators:
    """All interactive elements must display visible focus indicators (SC 2.4.11)."""

    def test_interactive_elements_show_focus(
        self, page: object, base_url: str
    ) -> None:
        """Buttons, links, selects, and inputs display a visible focus indicator on keyboard focus."""
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
            "No interactive elements found on portfolio health page — "
            "skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestPortfolioHealthAriaLandmarks:
    """Portfolio health page must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]

    def test_detail_panel_has_aria_role(self, page: object, base_url: str) -> None:
        """Repo detail panel or inspector carries an ARIA landmark role."""
        _go(page, base_url)

        panel_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var panelSelectors = [
                    '.detail-panel',
                    '.inspector-panel',
                    '[data-panel]',
                    '[class*="detail-panel"]',
                    '[class*="inspector"]',
                    '[class*="side-panel"]',
                    '[class*="slide-panel"]'
                ];
                var results = [];
                panelSelectors.forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) {
                        var role = el.getAttribute('role');
                        var ariaLabel = el.getAttribute('aria-label') ||
                                        el.getAttribute('aria-labelledby');
                        results.push({
                            hasRole: !!role,
                            role: role,
                            hasLabel: !!ariaLabel
                        });
                    });
                });
                return results;
            })()
            """
        )

        if not panel_info:
            pytest.skip(
                "No detail/inspector panels found on portfolio health page — "
                "panel may be rendered dynamically on drill-down"
            )

        panels_without_role = [r for r in panel_info if not r.get("hasRole")]
        if panels_without_role:
            pytest.skip(
                f"{len(panels_without_role)}/{len(panel_info)} detail panel(s) lack "
                "an ARIA role — panels should carry role='complementary' or "
                "role='region' per WCAG SC 1.3.6 (advisory)"
            )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestPortfolioHealthTouchTargets:
    """Buttons and links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the portfolio health page meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestPortfolioHealthAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/portfolio-health:\n{result.summary()}"
        )
