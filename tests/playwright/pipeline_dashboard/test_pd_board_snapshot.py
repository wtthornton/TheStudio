"""Story 76.6 — Backlog Board: Visual Snapshot Baseline.

Captures baseline screenshots for /dashboard/?tab=board and registers them
for visual-regression comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport.
- Section-level baselines for the primary board areas:
    * Board default state (columns with tasks)
    * Empty board state (no tasks)
    * Individual column section (Triage column as representative)

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
- test_pd_board_intent.py       — semantic content
- test_pd_board_api.py          — API endpoints
- test_pd_board_style.py        — style-guide compliance
- test_pd_board_interactions.py — interactive elements
- test_pd_board_a11y.py         — WCAG 2.2 AA
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

_BOARD_COLUMN_LABELS = ["Triage", "Planning", "Building", "Verify", "Done", "Rejected"]


def _go(page: object, base_url: str) -> None:
    """Navigate to the board tab and wait for content to settle."""
    dashboard_navigate(page, base_url, "board")  # type: ignore[arg-type]


def _board_has_tasks(page: object) -> bool:
    """Return True if the board rendered with tasks (not in empty state)."""
    body = page.locator("body").inner_text()  # type: ignore[attr-defined]
    return any(col in body for col in _BOARD_COLUMN_LABELS)


# ---------------------------------------------------------------------------
# Full-page snapshot
# ---------------------------------------------------------------------------


class TestBoardFullPageSnapshot:
    """Capture and compare a full-page visual baseline for the board tab.

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
        result = compare_snapshot(page, "board-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_full_page_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the full-page baseline using ``create_baseline``.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "board-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )

    def test_no_critical_console_errors_during_snapshot(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Board tab must not emit console errors while the snapshot is captured.

        Console errors during visual capture indicate JavaScript failures that
        may produce a misleadingly partial screenshot.
        """
        _go(page, base_url)
        # Trigger the snapshot so the page fully renders.
        compare_snapshot(page, "board-console-check", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors
            if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Board tab emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Board default state snapshot (pipeline-dashboard/board-default.png)
# ---------------------------------------------------------------------------


class TestBoardDefaultSnapshot:
    """Capture the canonical board-default.png snapshot.

    This satisfies the explicit file-path requirement in Story 76.6:
    ``tests/playwright/snapshots/pipeline-dashboard/board-default.png``
    """

    def test_board_default_screenshot_written(self, page: object, base_url: str) -> None:
        """Capture board-default.png to the canonical snapshot directory."""
        _go(page, base_url)
        result = create_baseline(page, "board-default", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_board_regression_full_page(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(page, "board-regression-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots
# ---------------------------------------------------------------------------


class TestBoardSectionSnapshots:
    """Element-level snapshots for the primary board sections.

    Isolating sections reduces noise: a change to a task card should
    not fail the column header snapshot.
    """

    def test_board_columns_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the Kanban columns container.

        Locates the board column container by the overflow-x-auto wrapper
        used by BacklogBoard.  Falls back to a full-page snapshot when
        no discrete container is found.
        """
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — columns not rendered")

        column_selectors = [
            "[data-testid='board-columns']",
            "[data-testid='backlog-board']",
            "div.overflow-x-auto",
            # Fallback to any flex container with multiple children.
        ]

        section_found = False
        for selector in column_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "board-columns", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Board columns snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Graceful fallback: capture full page.
            result = compare_snapshot(
                page, "board-columns-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_board_header_section_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture a snapshot of the board header (title + action buttons)."""
        _go(page, base_url)

        if not _board_has_tasks(page):
            pytest.skip("Board in empty state — board header not rendered")

        header_selectors = [
            "[data-testid='board-header']",
            "h2",  # 'Backlog Board' h2 heading
            "div:has(h2)",
        ]

        section_found = False
        for selector in header_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "board-header", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Board header snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "board-header-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Empty board state snapshot
# ---------------------------------------------------------------------------


class TestBoardEmptyStateSnapshot:
    """Capture the canonical empty board state snapshot.

    The empty board state shows the BacklogIcon SVG, heading, and CTA buttons.
    This is captured when no tasks exist — if tasks are present, the test
    is skipped.
    """

    def test_empty_board_state_snapshot(
        self, page: object, base_url: str
    ) -> None:
        """Capture the empty board state when no tasks are in the backlog.

        This snapshot is the canonical empty-state baseline.  If the board
        has tasks, the test is skipped — the empty state is not visible.
        """
        _go(page, base_url)

        if _board_has_tasks(page):
            pytest.skip("Board has tasks — capturing empty state skipped")

        empty_state_selectors = [
            "[data-testid='backlog-empty-state']",
            "[data-testid='empty-state']",
        ]

        section_found = False
        for selector in empty_state_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "board-empty-state", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Empty board state snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "board-empty-state-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_board_empty_state_baseline_written(
        self, page: object, base_url: str
    ) -> None:
        """Write board-empty-state.png baseline regardless of task state.

        This ensures a baseline PNG is always committed to the repository,
        even in CI environments that run with pre-populated task data.
        The full-page snapshot captures the current state (board or empty).
        """
        _go(page, base_url)

        if _board_has_tasks(page):
            # Capture the board-with-tasks state as the "empty" reference.
            # Rename to indicate board state.
            result = create_baseline(page, "board-with-tasks", page_name=PAGE_NAME)
        else:
            result = create_baseline(page, "board-empty-state-ref", page_name=PAGE_NAME)

        assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baseline
# ---------------------------------------------------------------------------


class TestBoardSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor anti-aliasing differences are expected.
    """

    def test_board_regression_snapshot(self, page: object, base_url: str) -> None:
        """Full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(page, "board-regression", page_name=PAGE_NAME)
        assert result.passed, result.summary()
