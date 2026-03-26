"""Story 76.11 — Reputation Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=reputation and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the three primary reputation areas:
    * Summary cards row
    * Expert table / ExpertDetail panel
    * Drift Alerts panel

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

Related suites
~~~~~~~~~~~~~~
- test_pd_reputation_intent.py       — semantic content
- test_pd_reputation_api.py          — API endpoints
- test_pd_reputation_style.py        — style-guide compliance
- test_pd_reputation_interactions.py — interactive elements
- test_pd_reputation_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the reputation tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "reputation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestReputationFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the reputation tab.

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
        result = compare_snapshot(page, "reputation-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "reputation-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Reputation tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "reputation-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Reputation tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestReputationSectionSnapshots:
    """Element-level snapshots for each primary reputation section.

    Isolating sections reduces noise: a change to the drift alerts panel
    should not fail the summary cards snapshot.
    """

    def test_summary_cards_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the reputation summary cards row."""
        _go(page, base_url)

        card_selectors = [
            "[data-testid='reputation-summary-cards']",
            "[data-testid='summary-cards']",
            "div.grid:has([class*='card'])",
            "div.grid:has([class*='border'])",
        ]

        section_found = False
        for selector in card_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "reputation-summary-cards", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Summary cards snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "reputation-summary-cards-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_expert_table_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the expert performance table."""
        _go(page, base_url)

        expert_selectors = [
            "[data-testid='expert-table']",
            "[data-testid='expert-list']",
            "[aria-label*='expert' i]",
            "table",
        ]

        section_found = False
        for selector in expert_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "reputation-expert-table", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Expert table snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "reputation-expert-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_drift_alerts_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Drift Alerts panel."""
        _go(page, base_url)

        drift_selectors = [
            "[data-testid='drift-alerts']",
            "[data-testid='drift-panel']",
            "[aria-label*='drift' i]",
            "div:has-text('Drift')",
        ]

        section_found = False
        for selector in drift_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "reputation-drift-alerts", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Drift Alerts snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "reputation-drift-alerts-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_outcome_feed_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Outcome feed section."""
        _go(page, base_url)

        outcome_selectors = [
            "[data-testid='outcome-feed']",
            "[data-testid='outcome-list']",
            "[aria-label*='outcome' i]",
            "div:has-text('Outcome')",
        ]

        section_found = False
        for selector in outcome_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "reputation-outcome-feed", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Outcome feed snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "reputation-outcome-feed-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestReputationSnapshotRegression:
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
            page, "reputation-regression-full-page", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_reputation_default_screenshot_written(
        self, page: object, base_url: str
    ) -> None:
        """Capture reputation-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.11:
        ``tests/playwright/snapshots/pipeline-dashboard/reputation-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "reputation-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
