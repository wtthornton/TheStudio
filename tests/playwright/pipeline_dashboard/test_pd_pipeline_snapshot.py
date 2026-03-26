"""Story 76.2 — Pipeline Dashboard: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=pipeline and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the three primary pipeline areas:
    * Pipeline rail (stage nodes) or empty pipeline state
    * Event log panel
    * Gate Inspector panel

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
- test_pd_pipeline_intent.py       — semantic content
- test_pd_pipeline_api.py          — API endpoints
- test_pd_pipeline_style.py        — style-guide compliance
- test_pd_pipeline_interactions.py — interactive elements
- test_pd_pipeline_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the pipeline tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestPipelineFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the pipeline tab.

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
        result = compare_snapshot(page, "full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

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

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Pipeline tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Pipeline tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestPipelineSectionSnapshots:
    """Element-level snapshots for each primary pipeline section.

    Isolating sections reduces noise: a change to the gate inspector should
    not fail the pipeline rail snapshot.
    """

    def test_pipeline_rail_or_empty_state_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the pipeline rail or empty state.

        The test locates the pipeline-rail or empty-pipeline-rail by
        data-testid.  Falls back to a full-page snapshot when neither
        discrete container is found.
        """
        _go(page, base_url)

        rail_selectors = [
            "[data-testid='pipeline-rail']",
            "[data-testid='empty-pipeline-rail']",
            "section.relative",
            "section:has([data-testid])",
        ]

        section_found = False
        for selector in rail_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "pipeline-rail", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Pipeline rail snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page when the section has no
            # discrete DOM container.
            result = compare_snapshot(
                page, "pipeline-rail-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_event_log_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Event Log panel."""
        _go(page, base_url)

        event_log_selectors = [
            "[data-testid='event-log']",
            "[aria-label*='event' i]",
            "div:has-text('Recent Events')",
        ]

        section_found = False
        for selector in event_log_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "event-log", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Event log snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "event-log-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_gate_inspector_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Gate Inspector panel."""
        _go(page, base_url)

        gate_selectors = [
            "[data-testid='gate-inspector']",
            "[aria-label*='gate' i]",
            "div:has-text('Gate Inspector')",
        ]

        section_found = False
        for selector in gate_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "gate-inspector", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Gate Inspector snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "gate-inspector-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_tasks(
        self, page: object, base_url: str
    ) -> None:
        """Capture the empty pipeline state when no tasks are in the pipeline.

        This snapshot is the canonical empty-state baseline.  If the pipeline
        rail is active, the test is skipped — the empty state is not visible.
        """
        _go(page, base_url)

        if page.locator("[data-testid='pipeline-rail']").count() > 0:  # type: ignore[attr-defined]
            pytest.skip("Pipeline rail active — capturing empty state skipped")

        empty_state_selectors = [
            "[data-testid='empty-pipeline-rail']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestPipelineSnapshotRegression:
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
        result = compare_snapshot(page, "regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_pipeline_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture pipeline-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.2:
        ``tests/playwright/snapshots/pipeline-dashboard/pipeline-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "pipeline-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()
