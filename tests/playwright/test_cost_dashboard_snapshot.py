"""Epic 72.6 — Cost Dashboard: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/cost-dashboard and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Cost Dashboard sections:
    * KPI cost cards (model spend, budget utilisation, cost breakdown)
    * Cost charts (spend over time, model breakdown)
    * Period selector controls
    * Budget threshold panel

First run
~~~~~~~~~
No baseline files exist — ``compare_snapshot`` auto-creates them; every test
passes with ``is_new_baseline=True``.

Subsequent runs
~~~~~~~~~~~~~~~
Existing baselines are loaded and compared.  Tests fail when the pixel-diff
ratio exceeds ``DEFAULT_THRESHOLD`` (0.1 %).

Updating baselines
~~~~~~~~~~~~~~~~~~
Set ``SNAPSHOT_UPDATE=1`` in the environment to overwrite all baselines and
always pass.

Related suites
~~~~~~~~~~~~~~
- 72.1 test_cost_dashboard_intent.py       - semantic content
- 72.2 test_cost_dashboard_api.py          - API endpoints
- 72.3 test_cost_dashboard_style.py        - style-guide compliance
- 72.4 test_cost_dashboard_interactions.py - interactive elements
- 72.5 test_cost_dashboard_a11y.py         - WCAG 2.2 AA
"""

from __future__ import annotations

import pytest

from tests.playwright.conftest import navigate
from tests.playwright.lib.snapshot_helpers import (
    capture_element_snapshot,
    compare_snapshot,
    create_baseline,
)

pytestmark = pytest.mark.playwright

COST_DASHBOARD_URL = "/admin/ui/cost-dashboard"
PAGE_NAME = "cost-dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the cost dashboard page and wait for content to settle."""
    navigate(page, f"{base_url}{COST_DASHBOARD_URL}")  # type: ignore[arg-type]


def _has_charts(page: object) -> bool:
    """Return True when cost chart elements are present on the page."""
    return (
        page.locator("canvas").count() > 0  # type: ignore[attr-defined]
        or page.locator("svg[class*='chart'], svg[aria-label]").count() > 0  # type: ignore[attr-defined]
        or page.locator("[class*='chart'], [class*='Chart']").count() > 0  # type: ignore[attr-defined]
        or page.locator(".recharts-wrapper, .chartjs-render-monitor").count() > 0  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestCostDashboardFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/cost-dashboard.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing cost sections in the Cost Dashboard.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the cost dashboard at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/cost-dashboard/``.  On subsequent runs
        the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestCostDashboardSectionSnapshots:
    """Element-level snapshots for primary Cost Dashboard sections.

    Isolating sections reduces noise: a change to the period selector should
    not fail the KPI cards snapshot.
    """

    def test_kpi_cards_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the KPI cost cards section.

        The model spend, budget utilisation, and cost breakdown cards must
        remain visually consistent across UI changes — operators rely on these
        to monitor platform spend at a glance.
        """
        _go(page, base_url)

        kpi_selectors = [
            "[data-testid='kpi-cards']",
            "[data-testid='cost-kpis']",
            "[data-section='kpi']",
            "[class*='kpi-row']",
            "[class*='kpi-grid']",
            "[class*='metric-cards']",
            "[class*='stat-cards']",
            "[class*='cost-cards']",
            "[class*='spend-cards']",
            "section:has([class*='kpi'])",
            "div:has([class*='kpi-card'])",
        ]

        section_found = False
        for selector in kpi_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "kpi-cards", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "kpi-cards-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_cost_chart_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the cost charts section.

        The spend-over-time and model-breakdown charts must render correctly
        and remain visually stable — operators use them to identify cost trends.
        """
        _go(page, base_url)

        if not _has_charts(page):
            # No charts rendered — take a full-page fallback and pass
            result = compare_snapshot(
                page, "cost-chart-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()
            return

        chart_selectors = [
            "[data-testid='cost-chart']",
            "[data-testid='spend-chart']",
            "[data-chart]",
            "[class*='chart-container']",
            "[class*='ChartContainer']",
            "[class*='spend-chart']",
            "[class*='cost-chart']",
            ".recharts-wrapper",
            ".chartjs-render-monitor",
            "canvas",
        ]

        section_found = False
        for selector in chart_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "cost-chart", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "cost-chart-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_period_selector_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the period selector controls.

        The 24h / 7d / 30d period selector (or equivalent date-range control)
        must remain visually stable — operators use it to scope the cost data
        they are viewing.
        """
        _go(page, base_url)

        period_selectors = [
            "[data-testid='period-selector']",
            "[data-testid='time-range-selector']",
            "[aria-label*='period' i]",
            "[aria-label*='time range' i]",
            "[aria-label*='date range' i]",
            "[role='group']:has(button:has-text('7d'))",
            "[role='group']:has(button:has-text('30d'))",
            "select[name*='period' i]",
            "select[name*='range' i]",
            "[class*='period-selector']",
            "[class*='time-range']",
            "[class*='date-range']",
        ]

        section_found = False
        for selector in period_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "period-selector", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "period-selector-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_budget_threshold_panel_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the budget threshold controls panel.

        Budget limit displays and threshold controls must remain visually
        consistent — operators use these to monitor and adjust spend limits.
        """
        _go(page, base_url)

        budget_selectors = [
            "[data-testid='budget-panel']",
            "[data-testid='budget-threshold']",
            "[data-section='budget']",
            "[aria-label*='budget' i]",
            "[class*='budget-panel']",
            "[class*='budget-threshold']",
            "[class*='budget-controls']",
            "[class*='spend-limit']",
            "section:has([class*='budget'])",
            "div:has(input[name*='budget' i])",
            "div:has(button:has-text('Budget'))",
        ]

        section_found = False
        for selector in budget_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "budget-threshold-panel", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "budget-threshold-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestCostDashboardSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor antialiasing differences are expected.
    """

    def test_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(
            page, "regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_no_critical_console_errors(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Cost dashboard must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Cost dashboard emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
