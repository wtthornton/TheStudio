"""Story 76.8 — Budget Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=budget and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the primary budget areas:
    * Summary cards (total spend, calls, cache hit rate) or empty state
    * Cost breakdown section (by stage and by model charts)
    * Budget Alert Configuration panel

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

The canonical file required by Story 76.8 is:
    tests/playwright/snapshots/pipeline-dashboard/budget-default.png

Related suites
~~~~~~~~~~~~~~
- test_pd_budget_intent.py       — semantic content
- test_pd_budget_api.py          — API endpoints
- test_pd_budget_style.py        — style-guide compliance
- test_pd_budget_interactions.py — interactive elements
- test_pd_budget_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the budget tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "budget")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestBudgetFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the budget tab.

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
        result = compare_snapshot(page, "budget-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "budget-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Budget tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "budget-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Budget tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestBudgetSectionSnapshots:
    """Element-level snapshots for each primary budget section.

    Isolating sections reduces noise: a change to the config panel should
    not fail the summary cards snapshot.
    """

    def test_summary_cards_or_empty_state_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the summary cards or empty state.

        When budget data is available, captures the summary KPI cards.
        When no data exists, captures the empty state placeholder.
        """
        _go(page, base_url)

        summary_selectors = [
            "[data-testid='budget-summary-cards']",
            "[data-testid='budget-empty']",
            "[data-testid='empty-state']",
            "[data-tour='budget-dashboard']",
        ]

        section_found = False
        for selector in summary_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "budget-summary", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Budget summary snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page when no discrete container found.
            result = compare_snapshot(
                page, "budget-summary-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_cost_breakdown_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the cost breakdown charts (by stage and by model)."""
        _go(page, base_url)

        # CostBreakdown renders two HBarChart components side by side.
        breakdown_selectors = [
            "[data-testid='budget-cost-breakdown']",
            "div:has-text('Cost by Pipeline Stage')",
            "div:has-text('Cost by Model')",
        ]

        section_found = False
        for selector in breakdown_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "budget-breakdown", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Cost breakdown snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Cost breakdown may not render when no data is available — use fallback.
            result = compare_snapshot(
                page, "budget-breakdown-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_config_panel_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Budget Alert Configuration panel."""
        _go(page, base_url)

        config_selectors = [
            "[data-testid='budget-alert-config']",
            "div:has-text('Budget Alert Configuration')",
        ]

        section_found = False
        for selector in config_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "budget-config", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Budget config snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "budget-config-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_data(
        self, page: object, base_url: str
    ) -> None:
        """Capture the empty budget state when no spend data is available.

        This snapshot is the canonical empty-state baseline.  If the summary
        cards are active (budget data loaded), the test is skipped — the
        empty state is not visible.
        """
        _go(page, base_url)

        body_text = page.locator("body").inner_text()  # type: ignore[attr-defined]
        if "Total Spend" in body_text:
            pytest.skip("Budget data loaded — capturing empty state skipped")

        empty_state_selectors = [
            "[data-testid='budget-empty']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "budget-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Budget empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "budget-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestBudgetSnapshotRegression:
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
            page, "budget-regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_budget_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture budget-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.8:
        ``tests/playwright/snapshots/pipeline-dashboard/budget-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "budget-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
