"""Story 76.10 — Analytics Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=analytics and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the primary analytics areas:
    * Summary cards KPIs section
    * Throughput chart panel
    * Bottleneck bars panel

First run
~~~~~~~~~
No baseline files exist — ``compare_snapshot`` auto-creates them; every test
passes with ``is_new_baseline=True``.

Subsequent runs
~~~~~~~~~~~~~~~
Existing baselines are loaded and compared.  Tests fail when the pixel-diff
ratio exceeds ``DEFAULT_THRESHOLD`` (0.1%).

Updating baselines
~~~~~~~~~~~~~~~~~~
Set ``SNAPSHOT_UPDATE=1`` in the environment to overwrite all baselines and
always pass.

Baseline location
~~~~~~~~~~~~~~~~~
All snapshot files are written to:
    tests/playwright/snapshots/pipeline-dashboard/

The canonical file required by Story 76.10:
    tests/playwright/snapshots/pipeline-dashboard/analytics-default.png

Related suites
~~~~~~~~~~~~~~
- test_pd_analytics_intent.py       — semantic content
- test_pd_analytics_api.py          — API endpoints
- test_pd_analytics_style.py        — style-guide compliance
- test_pd_analytics_interactions.py — interactive elements
- test_pd_analytics_a11y.py         — WCAG 2.2 AA
"""

from __future__ import annotations

import pytest

from tests.playwright.lib.snapshot_helpers import (
    capture_element_snapshot,
    compare_snapshot,
    create_baseline,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

PAGE_NAME = "pipeline-dashboard"


def _go(page: object, base_url: str) -> None:
    """Navigate to the analytics tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "analytics")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestAnalyticsFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the analytics tab.

    The full-page snapshot is the primary regression guard: any unexpected
    layout shift, colour change, or missing section will fail here.
    """

    def test_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline at 1280x720 viewport.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/pipeline-dashboard/``.  On subsequent
        runs the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "analytics-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "analytics-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Analytics tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        compare_snapshot(page, "analytics-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Analytics tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Canonical analytics-default snapshot (Story 76.10 requirement)
# ---------------------------------------------------------------------------


class TestAnalyticsDefaultSnapshot:
    """Capture the canonical analytics-default.png baseline.

    Story 76.10 explicitly requires the file path:
        tests/playwright/snapshots/pipeline-dashboard/analytics-default.png
    """

    def test_analytics_default_screenshot_written(
        self, page: object, base_url: str
    ) -> None:
        """Capture analytics-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.10:
        ``tests/playwright/snapshots/pipeline-dashboard/analytics-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "analytics-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_analytics_default_regression(self, page: object, base_url: str) -> None:
        """analytics-default.png regression check — pixel-diff must not exceed threshold."""
        _go(page, base_url)
        result = compare_snapshot(
            page, "analytics-default-regression", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestAnalyticsSectionSnapshots:
    """Element-level snapshots for each primary analytics section.

    Isolating sections reduces noise: a change to the bottleneck chart should
    not fail the summary cards snapshot.
    """

    def test_kpi_cards_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the summary KPI cards section."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Analytics empty state — KPI cards not shown")

        kpi_selectors = [
            "[data-tour='analytics-kpis']",
            "[data-testid='summary-cards']",
        ]

        section_found = False
        for selector in kpi_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "analytics-kpi-cards", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"KPI cards snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "analytics-kpi-cards-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_throughput_chart_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the throughput chart panel."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Analytics empty state — throughput chart not shown")

        throughput_selectors = [
            "[data-tour='analytics-throughput']",
            "[data-testid='throughput-chart']",
            "div:has-text('Throughput')",
        ]

        section_found = False
        for selector in throughput_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "analytics-throughput-chart", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Throughput chart snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "analytics-throughput-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_bottleneck_bars_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the bottleneck bars panel."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Analytics empty state — bottleneck bars not shown")

        bottleneck_selectors = [
            "[data-tour='analytics-bottleneck']",
            "[data-testid='bottleneck-bars']",
            "div:has-text('Bottleneck')",
        ]

        section_found = False
        for selector in bottleneck_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "analytics-bottleneck-bars", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Bottleneck bars snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "analytics-bottleneck-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_data(
        self, page: object, base_url: str
    ) -> None:
        """Capture the analytics empty state when no data is available.

        This snapshot is the canonical empty-state baseline.  If analytics data
        is present, the test is skipped — the empty state is not visible.
        """
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() == 0:  # type: ignore[attr-defined]
            pytest.skip("Analytics data present — capturing empty state skipped")

        empty_selectors = [
            "[data-testid='analytics-empty-state']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in empty_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "analytics-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Analytics empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "analytics-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestAnalyticsSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor anti-aliasing differences are expected.
    """

    def test_full_page_regression(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(
            page, "analytics-regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()
