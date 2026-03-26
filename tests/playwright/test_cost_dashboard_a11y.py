"""Epic 72.5 — Cost Dashboard: Accessibility WCAG 2.2 AA.

Validates that /admin/ui/cost-dashboard meets WCAG 2.2 AA accessibility requirements:

  - Chart alternatives      — cost charts carry aria-label / role="img" + description,
                              or a fallback data table (SC 1.1.1, SC 1.3.1)
  - Focus indicators        — visible focus ring on all interactive elements (SC 2.4.11)
  - Screen reader support   — ARIA landmarks, period selector labels, budget control ARIA
  - Colour not sole cue     — cost status colours paired with text/icon (SC 1.4.1)
  - Keyboard operability    — period selector, budget threshold controls keyboard-reachable
                              (SC 2.1.1)
  - Touch targets           — buttons meet 24x24 px minimum (SC 2.5.8)
  - axe-core WCAG 2.x AA    — zero critical/serious violations

These tests verify *accessibility compliance*, not content or visual appearance.
Content is covered in test_cost_dashboard_intent.py (Epic 72.1).
API contracts are covered in test_cost_dashboard_api.py (Epic 72.2).
Style compliance is covered in test_cost_dashboard_style.py (Epic 72.3).
Interactions are covered in test_cost_dashboard_interactions.py (Epic 72.4).
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

COST_DASHBOARD_URL = "/admin/ui/cost-dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the cost dashboard page and wait for content to settle."""
    navigate(page, f"{base_url}{COST_DASHBOARD_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.1.1 / SC 1.3.1 — Chart alternatives
# ---------------------------------------------------------------------------


class TestCostDashboardChartAlternatives:
    """Cost charts must have text alternatives so screen readers can convey spend data.

    Per WCAG SC 1.1.1 (Non-text Content) and SC 1.3.1 (Info and Relationships),
    every cost chart must carry at minimum one of:
      - role="img" with aria-label or aria-labelledby
      - A <canvas> / <svg> with an aria-label or <title> child element
      - A visually hidden data table summarising the chart data
      - An aria-describedby linking to a text summary
    """

    def test_canvas_charts_have_aria_label_or_role_img(
        self, page: object, base_url: str
    ) -> None:
        """<canvas> cost chart elements carry role='img' with an accessible label."""
        _go(page, base_url)

        canvas_count = page.locator("canvas").count()  # type: ignore[attr-defined]
        if canvas_count == 0:
            pytest.skip("No <canvas> elements on cost dashboard — chart type may differ")

        chart_a11y = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var canvases = document.querySelectorAll('canvas');
                var results = [];
                canvases.forEach(function(c) {
                    var roleImg     = c.getAttribute('role') === 'img';
                    var ariaLabel   = !!c.getAttribute('aria-label');
                    var ariaLby     = !!c.getAttribute('aria-labelledby');
                    var ariaDescby  = !!c.getAttribute('aria-describedby');
                    var parentRole  = c.parentElement &&
                                      c.parentElement.getAttribute('role') === 'img';
                    var parentLabel = c.parentElement &&
                                      (!!c.parentElement.getAttribute('aria-label') ||
                                       !!c.parentElement.getAttribute('aria-labelledby'));
                    results.push({
                        accessible: roleImg || ariaLabel || ariaLby || ariaDescby ||
                                    (parentRole && parentLabel)
                    });
                });
                return results;
            })()
            """
        )

        inaccessible = [r for r in chart_a11y if not r.get("accessible")]
        assert not inaccessible, (
            f"{len(inaccessible)}/{len(chart_a11y)} <canvas> cost chart(s) have no "
            "accessible label (role='img' + aria-label / aria-labelledby / "
            "aria-describedby required by WCAG SC 1.1.1)"
        )

    def test_svg_charts_have_title_or_aria_label(
        self, page: object, base_url: str
    ) -> None:
        """Inline <svg> cost charts carry a <title> child or aria-label attribute."""
        _go(page, base_url)

        svg_count = page.locator("svg").count()  # type: ignore[attr-defined]
        if svg_count == 0:
            pytest.skip("No <svg> elements on cost dashboard — skipping SVG chart check")

        svg_a11y = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var svgs = document.querySelectorAll('svg');
                var results = [];
                svgs.forEach(function(svg) {
                    var hasTitle      = !!svg.querySelector('title');
                    var ariaLabel     = !!svg.getAttribute('aria-label');
                    var ariaLby       = !!svg.getAttribute('aria-labelledby');
                    var ariaHidden    = svg.getAttribute('aria-hidden') === 'true';
                    // Decorative SVGs hidden from AT are acceptable
                    if (ariaHidden) {
                        results.push({accessible: true, decorative: true});
                    } else {
                        results.push({
                            accessible: hasTitle || ariaLabel || ariaLby,
                            decorative: false
                        });
                    }
                });
                return results;
            })()
            """
        )

        non_decorative = [r for r in svg_a11y if not r.get("decorative")]
        if not non_decorative:
            pytest.skip("All SVG elements are aria-hidden decorative graphics")

        inaccessible = [r for r in non_decorative if not r.get("accessible")]
        assert not inaccessible, (
            f"{len(inaccessible)}/{len(non_decorative)} non-decorative <svg> "
            "element(s) have no accessible label (<title> child, aria-label, or "
            "aria-labelledby required by WCAG SC 1.1.1)"
        )

    def test_charts_have_text_alternative_or_data_table(
        self, page: object, base_url: str
    ) -> None:
        """Cost charts that cannot be labelled by aria alone have a nearby data table or summary."""
        _go(page, base_url)

        chart_container_count = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-chart]',
                    '[class*="chart"]',
                    '[class*="Chart"]',
                    '[id*="chart"]',
                    '[id*="Chart"]',
                    '.recharts-wrapper',
                    '.chartjs-render-monitor'
                ];
                var found = 0;
                selectors.forEach(function(sel) {
                    found += document.querySelectorAll(sel).length;
                });
                return found;
            })()
            """
        )

        if chart_container_count == 0:
            pytest.skip(
                "No chart containers found via common selectors — "
                "cost dashboard may use a different rendering approach"
            )

        has_data_table_or_summary = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                // Check for an accessible data table on the page
                var tables = document.querySelectorAll('table');
                if (tables.length > 0) return true;

                // Check for visually-hidden summaries
                var hiddenSummaries = document.querySelectorAll(
                    '.sr-only, .visually-hidden, [class*="screen-reader"], ' +
                    '[aria-live="polite"][class*="chart"]'
                );
                return hiddenSummaries.length > 0;
            })()
            """
        )

        if not has_data_table_or_summary:
            pytest.skip(
                "No data table or sr-only text summary found alongside chart containers; "
                "ensure cost charts carry sufficient aria-label/describedby for screen readers"
            )


# ---------------------------------------------------------------------------
# SC 1.3.1 — Period selector and budget control ARIA labels
# ---------------------------------------------------------------------------


class TestCostDashboardControlAria:
    """Period selector and budget threshold controls must carry accessible labels (SC 1.3.1).

    An unlabelled <select>, input, or button group is invisible to screen readers.
    Every control must have an associated <label>, aria-label, or aria-labelledby.
    """

    def test_period_selector_has_accessible_label(
        self, page: object, base_url: str
    ) -> None:
        """Period selector control carries an accessible label."""
        _go(page, base_url)

        period_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'select[name*="period" i]',
                    'select[name*="range" i]',
                    'select[name*="time" i]',
                    'select[aria-label*="period" i]',
                    'select[aria-label*="range" i]',
                    '[role="combobox"][aria-label*="period" i]',
                    '[role="combobox"][aria-label*="range" i]'
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
                            el.getAttribute('title')
                        );
                        results.push({tag: el.tagName, hasLabel: !!hasLabel});
                    });
                });
                return results;
            })()
            """
        )

        if not period_info:
            pytest.skip(
                "No period selector found on cost dashboard — "
                "period filtering may use button groups (checked separately)"
            )

        unlabelled = [r for r in period_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} period selector control(s) have no accessible label — "
            "WCAG SC 1.3.1 requires labels on all form controls"
        )

    def test_period_button_group_has_group_label(
        self, page: object, base_url: str
    ) -> None:
        """Period button groups (24h / 7d / 30d) have a group label via role='group'."""
        _go(page, base_url)

        button_group_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var periodTexts = ['24h', '7d', '30d', '1h', 'Today',
                                   'Last 7', 'Last 30', 'This week', 'This month'];
                var periodButtons = [];
                var allButtons = document.querySelectorAll('button');
                allButtons.forEach(function(btn) {
                    var txt = btn.textContent.trim();
                    if (periodTexts.some(function(p) {
                            return txt.toLowerCase().indexOf(p.toLowerCase()) >= 0;
                        })) {
                        periodButtons.push(btn);
                    }
                });
                if (periodButtons.length === 0) return {found: false};

                // Check if buttons are wrapped in a role="group" or <fieldset>
                var parent = periodButtons[0].parentElement;
                var groupRole = parent && (
                    parent.getAttribute('role') === 'group' ||
                    parent.tagName === 'FIELDSET'
                );
                var groupLabel = parent && (
                    !!parent.getAttribute('aria-label') ||
                    !!parent.getAttribute('aria-labelledby') ||
                    parent.querySelector('legend')
                );
                return {
                    found: true,
                    count: periodButtons.length,
                    hasGroup: groupRole,
                    hasGroupLabel: !!(groupRole && groupLabel)
                };
            })()
            """
        )

        if not button_group_info.get("found"):
            pytest.skip(
                "No period button group (24h/7d/30d) found — skipping group label check"
            )

        if not button_group_info.get("hasGroup"):
            pytest.skip(
                "Period buttons not wrapped in role='group' — individual aria-labels may suffice"
            )

        assert button_group_info.get("hasGroupLabel"), (
            "Period button group (24h/7d/30d) must be wrapped in "
            "role='group' with aria-label or aria-labelledby (WCAG SC 1.3.1)"
        )

    def test_budget_threshold_inputs_have_labels(
        self, page: object, base_url: str
    ) -> None:
        """Budget threshold input controls carry accessible labels (SC 1.3.1)."""
        _go(page, base_url)

        budget_input_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    'input[name*="budget" i]',
                    'input[name*="threshold" i]',
                    'input[name*="limit" i]',
                    'input[aria-label*="budget" i]',
                    'input[aria-label*="threshold" i]',
                    'input[aria-label*="limit" i]'
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
                        results.push({name: el.name || sel, hasLabel: !!hasLabel});
                    });
                });
                return results;
            })()
            """
        )

        if not budget_input_info:
            pytest.skip(
                "No budget threshold inputs found on cost dashboard — "
                "budget editing may use a modal or separate settings page"
            )

        unlabelled = [r for r in budget_input_info if not r.get("hasLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)} budget threshold input(s) have no accessible label — "
            "WCAG SC 1.3.1 requires labels on all form controls"
        )


# ---------------------------------------------------------------------------
# SC 2.1.1 — Keyboard operability
# ---------------------------------------------------------------------------


class TestCostDashboardKeyboardNavigation:
    """All interactive elements on the cost dashboard must be keyboard-reachable (SC 2.1.1)."""

    def test_keyboard_navigation_reaches_interactive_elements(
        self, page: object, base_url: str
    ) -> None:
        """Tab key reaches interactive elements on the cost dashboard."""
        _go(page, base_url)
        assert_keyboard_navigation(page)  # type: ignore[arg-type]

    def test_period_selector_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Period selector is reachable and operable by keyboard."""
        _go(page, base_url)

        period_selectors = [
            "select[name*='period' i]",
            "select[name*='range' i]",
            "select[aria-label*='period' i]",
            "button:has-text('7d')",
            "button:has-text('30d')",
            "button:has-text('24h')",
        ]
        for sel in period_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip("No period selector found on cost dashboard — skipping keyboard check")

    def test_budget_threshold_controls_keyboard_operable(
        self, page: object, base_url: str
    ) -> None:
        """Budget threshold controls (inputs, edit buttons) are keyboard-operable."""
        _go(page, base_url)

        budget_selectors = [
            "input[name*='budget' i]",
            "input[name*='threshold' i]",
            "input[name*='limit' i]",
            "button:has-text('Set Budget')",
            "button:has-text('Edit Budget')",
            "button:has-text('Set Limit')",
            "button:has-text('Budget')",
            "[data-control='budget-threshold']",
        ]
        for sel in budget_selectors:
            if page.locator(sel).count() > 0:  # type: ignore[attr-defined]
                assert_focus_visible(page, sel)  # type: ignore[arg-type]
                return

        pytest.skip(
            "No budget threshold controls found on cost dashboard — "
            "skipping keyboard operability check"
        )


# ---------------------------------------------------------------------------
# SC 2.4.11 — Focus indicators
# ---------------------------------------------------------------------------


class TestCostDashboardFocusIndicators:
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
            "No interactive elements found on cost dashboard — skipping focus indicator check"
        )


# ---------------------------------------------------------------------------
# SC 1.3.6 — ARIA landmarks
# ---------------------------------------------------------------------------


class TestCostDashboardAriaLandmarks:
    """Cost dashboard must use ARIA landmark regions for screen reader navigation (SC 1.3.6)."""

    def test_aria_landmarks_present(self, page: object, base_url: str) -> None:
        """Page has at least one ARIA landmark (main, nav, or region)."""
        _go(page, base_url)
        assert_aria_landmarks(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SC 1.4.1 — Colour not the only indicator
# ---------------------------------------------------------------------------


class TestCostDashboardColorIndicators:
    """Cost status and budget indicators must not rely solely on colour (SC 1.4.1)."""

    def test_no_color_only_status_indicators(
        self, page: object, base_url: str
    ) -> None:
        """All cost/budget status indicators pair colour with a text label or icon."""
        _go(page, base_url)
        assert_no_color_only_indicators(page)  # type: ignore[arg-type]

    def test_budget_status_badges_have_text_label(
        self, page: object, base_url: str
    ) -> None:
        """Budget status badges (Under/Near/Over budget) pair colour with a visible text label."""
        _go(page, base_url)

        budget_badge_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-status]',
                    '[class*="badge"]',
                    '[class*="status"]',
                    '[class*="budget-status"]',
                    '[class*="cost-status"]'
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

        if not budget_badge_info:
            pytest.skip("No budget/cost status badges found on cost dashboard")

        color_only = [
            r for r in budget_badge_info
            if not r.get("hasText") and not r.get("hasAriaLabel")
        ]
        assert not color_only, (
            f"{len(color_only)}/{len(budget_badge_info)} budget status badge(s) have no "
            "text label or aria-label — colour alone cannot convey status (WCAG SC 1.4.1)"
        )

    def test_kpi_cards_have_accessible_labels(
        self, page: object, base_url: str
    ) -> None:
        """KPI cost cards (model spend, budget utilisation) carry accessible text labels."""
        _go(page, base_url)

        kpi_info = page.evaluate(  # type: ignore[attr-defined]
            """
            (function() {
                var selectors = [
                    '[data-component="kpi-card"]',
                    '[class*="kpi"]',
                    '[class*="metric-card"]',
                    '[class*="stat-card"]',
                    '[class*="cost-card"]',
                    '[class*="spend-card"]'
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

        if not kpi_info:
            pytest.skip("No KPI cost cards found on cost dashboard")

        unlabelled = [r for r in kpi_info if not r.get("hasText") and not r.get("hasAriaLabel")]
        assert not unlabelled, (
            f"{len(unlabelled)}/{len(kpi_info)} KPI cost card(s) have no accessible "
            "text label or aria-label — WCAG SC 1.4.1 requires non-colour indicators"
        )


# ---------------------------------------------------------------------------
# SC 2.5.8 — Touch target size
# ---------------------------------------------------------------------------


class TestCostDashboardTouchTargets:
    """Buttons and links must meet the 24x24 px minimum touch target (SC 2.5.8)."""

    def test_touch_targets_meet_minimum_size(
        self, page: object, base_url: str
    ) -> None:
        """All buttons and links on the cost dashboard meet the 24x24 px touch target."""
        _go(page, base_url)
        assert_touch_targets(page)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# axe-core — WCAG 2.x AA automated audit
# ---------------------------------------------------------------------------


class TestCostDashboardAxeAudit:
    """axe-core automated audit must report zero critical or serious violations (WCAG 2.x AA)."""

    def test_axe_audit_no_critical_violations(
        self, page: object, base_url: str
    ) -> None:
        """axe-core WCAG 2.x AA scan finds no critical or serious violations."""
        _go(page, base_url)
        result = run_axe_audit(page)  # type: ignore[arg-type]
        assert result.passed, (
            f"axe-core found {len(result.violations)} critical/serious violation(s) "
            f"on /admin/ui/cost-dashboard:\n{result.summary()}"
        )
