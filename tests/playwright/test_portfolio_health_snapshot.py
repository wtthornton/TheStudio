"""Epic 73.6 — Portfolio Health: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/portfolio-health and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary Portfolio Health sections:
    * Health summary / KPI cards (healthy/degraded/critical counts)
    * Risk distribution cards or chart
    * Repo health table or card grid
    * Risk filter controls

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
- 73.1 test_portfolio_health_intent.py       - semantic content
- 73.2 test_portfolio_health_api.py          - API endpoints
- 73.3 test_portfolio_health_style.py        - style-guide compliance
- 73.4 test_portfolio_health_interactions.py - interactive elements
- 73.5 test_portfolio_health_a11y.py         - WCAG 2.2 AA
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

PORTFOLIO_HEALTH_URL = "/admin/ui/portfolio-health"
PAGE_NAME = "portfolio-health"


def _go(page: object, base_url: str) -> None:
    """Navigate to the portfolio health page and wait for content to settle."""
    navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")  # type: ignore[arg-type]


def _has_charts(page: object) -> bool:
    """Return True when chart elements are present on the page."""
    return (
        page.locator("canvas").count() > 0  # type: ignore[attr-defined]
        or page.locator("svg[class*='chart'], svg[aria-label]").count() > 0  # type: ignore[attr-defined]
        or page.locator("[class*='chart'], [class*='Chart']").count() > 0  # type: ignore[attr-defined]
        or page.locator(".recharts-wrapper, .chartjs-render-monitor").count() > 0  # type: ignore[attr-defined]
    )


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestPortfolioHealthFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/portfolio-health.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing health sections in the Portfolio Health page.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the portfolio health page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/portfolio-health/``.  On subsequent runs
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
        assert result.is_new_baseline, "create_baseline must always report is_new_baseline=True"


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestPortfolioHealthSectionSnapshots:
    """Element-level snapshots for primary Portfolio Health sections.

    Isolating sections reduces noise: a change to the risk filter should
    not fail the health summary cards snapshot.
    """

    def test_health_summary_cards_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the health summary / KPI cards section.

        The healthy/degraded/critical repo count cards must remain visually
        consistent — operators rely on these to assess portfolio health at a
        glance.
        """
        _go(page, base_url)

        kpi_selectors = [
            "[data-testid='health-summary']",
            "[data-testid='health-kpis']",
            "[data-testid='kpi-cards']",
            "[data-section='health-summary']",
            "[class*='health-summary']",
            "[class*='kpi-row']",
            "[class*='kpi-grid']",
            "[class*='health-cards']",
            "[class*='summary-cards']",
            "[class*='stat-cards']",
            "[class*='portfolio-kpis']",
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
                        page, selector, "health-summary-cards", page_name=PAGE_NAME
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(page, "health-summary-cards-fallback", page_name=PAGE_NAME)
            assert result.passed, result.summary()

    def test_risk_distribution_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the risk distribution section.

        The risk distribution chart or card grid must render correctly and
        remain visually stable — operators use it to understand the spread of
        risk across repositories.
        """
        _go(page, base_url)

        risk_selectors = [
            "[data-testid='risk-distribution']",
            "[data-testid='risk-chart']",
            "[data-section='risk']",
            "[class*='risk-distribution']",
            "[class*='risk-chart']",
            "[class*='risk-breakdown']",
            "[class*='risk-grid']",
            "[class*='risk-cards']",
            "section:has([class*='risk'])",
            "div:has([class*='risk-badge'])",
        ]

        # Fall back to chart capture if no named risk section is found
        if not any(
            page.locator(sel).count() > 0  # type: ignore[attr-defined]
            for sel in risk_selectors
        ) and _has_charts(page):
            chart_selectors = [
                "[data-chart]",
                "[class*='chart-container']",
                "[class*='ChartContainer']",
                ".recharts-wrapper",
                ".chartjs-render-monitor",
                "canvas",
            ]
            for selector in chart_selectors:
                locator = page.locator(selector).first  # type: ignore[attr-defined]
                if locator.count() > 0:
                    try:
                        locator.scroll_into_view_if_needed()
                        dest = capture_element_snapshot(
                            page, selector, "risk-distribution-chart", page_name=PAGE_NAME
                        )
                        assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                        return
                    except Exception:  # noqa: S112
                        continue

        section_found = False
        for selector in risk_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "risk-distribution", page_name=PAGE_NAME
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(page, "risk-distribution-fallback", page_name=PAGE_NAME)
            assert result.passed, result.summary()

    def test_repo_health_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the repo health table or card grid.

        The per-repository health listing must remain visually consistent —
        operators use it to identify which repositories need attention.
        """
        _go(page, base_url)

        table_selectors = [
            "[data-testid='repo-health-table']",
            "[data-testid='portfolio-table']",
            "[data-section='repo-list']",
            "table[class*='health']",
            "table[class*='portfolio']",
            "table[class*='repo']",
            "[class*='repo-health-table']",
            "[class*='portfolio-table']",
            "[class*='repo-list']",
            "[class*='repo-grid']",
            "table",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "repo-health-table", page_name=PAGE_NAME
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(page, "repo-health-table-fallback", page_name=PAGE_NAME)
            assert result.passed, result.summary()

    def test_risk_filter_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the risk filter controls.

        The risk/health filter (All / Healthy / Degraded / Critical) must
        remain visually stable — operators use it to scope the portfolio view.
        """
        _go(page, base_url)

        filter_selectors = [
            "[data-testid='risk-filter']",
            "[data-testid='health-filter']",
            "[aria-label*='risk' i]",
            "[aria-label*='health filter' i]",
            "[aria-label*='status filter' i]",
            "[role='group']:has(button:has-text('Healthy'))",
            "[role='group']:has(button:has-text('Critical'))",
            "select[name*='risk' i]",
            "select[name*='health' i]",
            "select[name*='status' i]",
            "select[name*='filter' i]",
            "[class*='risk-filter']",
            "[class*='health-filter']",
            "[class*='status-filter']",
            "[class*='filter-controls']",
        ]

        section_found = False
        for selector in filter_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "risk-filter", page_name=PAGE_NAME
                    )
                    assert dest.exists(), f"Element snapshot was not written to disk: {dest}"
                    section_found = True
                    break
                except Exception:  # noqa: S112
                    continue

        if not section_found:
            result = compare_snapshot(page, "risk-filter-fallback", page_name=PAGE_NAME)
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestPortfolioHealthSnapshotRegression:
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
        result = compare_snapshot(page, "regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_no_critical_console_errors(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Portfolio health page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [e for e in console_errors if "TypeError" in e or "ReferenceError" in e]
        assert not critical_errors, (
            f"Portfolio health page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
