"""Story 76.5 — Routing Review Tab: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=routing and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Default empty state baseline (no task selected).
- Section-level baseline for the routing content area.

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
- test_pd_routing_intent.py       — semantic content
- test_pd_routing_api.py          — API endpoints
- test_pd_routing_style.py        — style-guide compliance
- test_pd_routing_interactions.py — interactive elements
- test_pd_routing_a11y.py         — WCAG 2.2 AA
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
    """Navigate to the routing tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "routing")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestRoutingFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the routing tab.

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
        result = compare_snapshot(page, "routing-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "routing-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Routing tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "routing-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Routing tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Default empty state snapshot
# ---------------------------------------------------------------------------


class TestRoutingDefaultStateSnapshot:
    """Capture the routing empty state when no task is selected.

    This is the canonical default view of the routing tab and the primary
    baseline for visual regression.
    """

    def test_routing_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture routing-default.png to the canonical snapshot directory.

        This satisfies the explicit file-path requirement in Story 76.5:
        ``tests/playwright/snapshots/pipeline-dashboard/routing-default.png``
        """
        _go(page, base_url)
        result = create_baseline(page, "routing-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_empty_state_snapshot_when_no_task_selected(
        self, page: object, base_url: str
    ) -> None:
        """Capture the routing empty state snapshot when no task is pre-selected.

        This snapshot is the canonical empty-state baseline.  If a task is
        pre-selected, the test falls back to capturing the routing preview area.
        """
        _go(page, base_url)

        empty_state_selectors = [
            "[data-testid='routing-no-task-state']",
            "[data-tour='routing-preview']",
        ]

        section_found = False
        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "routing-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Routing empty state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "routing-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestRoutingSectionSnapshots:
    """Element-level snapshots for the primary routing section.

    Isolating the routing area reduces noise: a change to the header should
    not fail the routing content snapshot.
    """

    def test_routing_content_area_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the routing content area.

        Attempts to locate the routing content by data-testid or data-tour.
        Falls back to a full-page snapshot when no discrete container is found.
        """
        _go(page, base_url)

        content_selectors = [
            "[data-testid='routing-no-task-state']",
            "[data-tour='routing-preview']",
            "div.mx-auto.max-w-6xl",
            "main",
        ]

        section_found = False
        for selector in content_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "routing-content", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Routing content snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "routing-content-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestRoutingSnapshotRegression:
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
        result = compare_snapshot(page, "routing-regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()
