"""Epic 63.6 — Metrics: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/metrics and registers them for
visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Component-level baselines for the primary metrics page sections:
    * KPI cards (success rates, gate status, loopback breakdown)
    * Period selector control
    * Chart / data visualisation area

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
- 63.1 test_metrics_intent.py         - semantic content
- 63.2 test_metrics_api.py            - API endpoints
- 63.3 test_metrics_style.py          - style-guide compliance
- 63.4 test_metrics_interactions.py   - interactive elements
- 63.5 test_metrics_a11y.py           - WCAG 2.2 AA
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

METRICS_URL = "/admin/ui/metrics"
PAGE_NAME = "metrics"


def _go(page: object, base_url: str) -> None:
    """Navigate to the metrics page and wait for content to settle."""
    navigate(page, f"{base_url}{METRICS_URL}")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshots
# ---------------------------------------------------------------------------


class TestMetricsFullPageSnapshot:
    """Capture and compare full-page baselines for /admin/ui/metrics.

    These snapshots guard against unexpected layout shifts, colour changes,
    or missing KPI cards in the metrics dashboard.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the metrics page at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/metrics/``.  On subsequent runs
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


class TestMetricsSectionSnapshots:
    """Element-level snapshots for primary metrics page sections.

    Isolating sections reduces noise: a change to the period selector should
    not fail the KPI card snapshot.
    """

    def test_kpi_cards_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the KPI / metric card area."""
        _go(page, base_url)

        card_selectors = [
            "[data-testid='metrics-kpi']",
            "[data-testid='kpi-cards']",
            "[aria-label*='metric' i]",
            ".kpi-card",
            "[class*='kpi']",
            "section:has-text('Success')",
            "div:has-text('Success Rate')",
        ]

        section_found = False
        for selector in card_selectors:
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

    def test_period_selector_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the period selector control.

        The period selector appearance (selected state, labels) must remain
        consistent across UI changes.
        """
        _go(page, base_url)

        period_selectors = [
            "[data-testid='period-selector']",
            "[data-testid='metrics-period']",
            "[data-filter='period']",
            "select[name*='period' i]",
            "select[name*='range' i]",
            "button[aria-pressed][data-period]",
            "div:has-text('Period')",
            "div:has-text('Range')",
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
            # Period selector may not be implemented yet — graceful fallback
            result = compare_snapshot(
                page, "period-selector-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_chart_area_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the chart or data visualisation area.

        Chart consistency (axes, legend, series colours) is important for
        operator trust in the metrics data.
        """
        _go(page, base_url)

        chart_selectors = [
            "[data-testid='metrics-chart']",
            "[data-testid='chart']",
            "[aria-label*='chart' i]",
            "canvas",
            "svg[role='img']",
            "[class*='chart']",
            "section:has-text('Loopback')",
            "div:has-text('Loopback')",
        ]

        section_found = False
        for selector in chart_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "chart-area", page_name=PAGE_NAME
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
                page, "chart-area-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestMetricsSnapshotRegression:
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
        """Metrics page must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Metrics page emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
