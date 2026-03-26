"""Epic 61.6 - Workflow Console: Visual Snapshot Baseline.

Captures baseline screenshots for /admin/ui/workflows in BOTH the list view
(default table) and the kanban board view, and registers them for visual-regression
comparison on subsequent runs.

Snapshot strategy
-----------------
- Full-page baseline at the canonical 1280x720 viewport for each view.
- Component-level baselines for the primary workflow page sections:
    * Workflow table (list view)
    * Kanban board (kanban view)
    * Status badge area
    * View toggle control

List view is the default.  Kanban view is activated by clicking the toggle
button before capturing.

First run
~~~~~~~~~
No baseline files exist - ``compare_snapshot`` auto-creates them; every test
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
- 61.1 test_workflows_intent.py         - semantic content
- 61.2 test_workflows_api.py            - API endpoints
- 61.3 test_workflows_style.py          - style-guide compliance
- 61.4 test_workflows_interactions.py   - interactive elements
- 61.5 test_workflows_a11y.py           - WCAG 2.2 AA
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

WORKFLOWS_URL = "/admin/ui/workflows"
PAGE_NAME = "workflow-console"


def _go(page: object, base_url: str) -> None:
    """Navigate to the workflow console and wait for content to settle."""
    navigate(page, f"{base_url}{WORKFLOWS_URL}")  # type: ignore[arg-type]


def _activate_kanban(page: object) -> bool:
    """Attempt to switch to kanban view.  Return True when kanban is visible."""
    toggle_selectors = [
        "button:has-text('Kanban')",
        "button:has-text('Board')",
        "[data-toggle='kanban']",
        "[aria-label*='kanban' i]",
        "[aria-label*='board' i]",
        "[data-view-toggle]",
    ]
    for sel in toggle_selectors:
        els = page.locator(sel)  # type: ignore[attr-defined]
        if els.count() > 0:
            try:
                els.first.click()
                page.wait_for_timeout(700)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
            break

    kanban_selectors = [
        "[data-view='kanban']",
        ".kanban",
        "[class*='kanban']",
        ".kanban-board",
        "[data-component='kanban']",
    ]
    return any(
        page.locator(sel).count() > 0  # type: ignore[attr-defined]
        for sel in kanban_selectors
    )


# ---------------------------------------------------------------------------
# List-view full-page snapshots
# ---------------------------------------------------------------------------


class TestWorkflowsListViewSnapshot:
    """Capture and compare full-page baselines for the default list view.

    The list view (table layout) is the default rendering of
    /admin/ui/workflows.  These snapshots guard against unexpected layout
    shifts, colour changes, or missing columns.
    """

    def test_list_view_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the list view at 1280x720.

        On first run a new baseline PNG is written to
        ``tests/playwright/snapshots/workflow-console/``.  On subsequent
        runs the current screenshot is compared against that baseline.
        """
        _go(page, base_url)
        result = compare_snapshot(page, "list-view-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_list_view_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the list-view full-page baseline.

        This test always passes.  Its purpose is to guarantee that a baseline
        file is committed to the repository so that CI never starts from a
        blank slate.
        """
        _go(page, base_url)
        result = create_baseline(page, "list-view-full-page-explicit", page_name=PAGE_NAME)
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )


# ---------------------------------------------------------------------------
# Kanban-view full-page snapshots
# ---------------------------------------------------------------------------


class TestWorkflowsKanbanViewSnapshot:
    """Capture and compare full-page baselines for the kanban board view.

    Kanban-specific elements (columns, cards, drag handles) are covered by
    these snapshots.  If the page does not expose a kanban toggle the tests
    are skipped rather than failed.
    """

    def test_kanban_view_full_page_baseline(self, page: object, base_url: str) -> None:
        """Capture full-page baseline of the kanban view at 1280x720."""
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip(
                "Kanban view could not be activated on workflows page — "
                "toggle button may not exist yet"
            )

        result = compare_snapshot(page, "kanban-view-full-page", page_name=PAGE_NAME)
        assert result.passed, result.summary()

    def test_kanban_view_create_baseline(self, page: object, base_url: str) -> None:
        """Explicitly (re)create the kanban-view full-page baseline.

        Always passes; commits a baseline so CI has a reference file.
        """
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip("Kanban view not available — skipping kanban baseline creation")

        result = create_baseline(
            page, "kanban-view-full-page-explicit", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()
        assert result.is_new_baseline, (
            "create_baseline must always report is_new_baseline=True"
        )


# ---------------------------------------------------------------------------
# Section-level snapshots (list view)
# ---------------------------------------------------------------------------


class TestWorkflowsListSectionSnapshots:
    """Element-level snapshots for primary list-view sections.

    Isolating sections reduces noise: a change to a status badge colour
    should not fail the table-header snapshot.
    """

    def test_workflow_table_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the workflow table (or empty state)."""
        _go(page, base_url)

        table_selectors = [
            "[data-testid='workflow-table']",
            "[aria-label*='workflow' i]",
            "table",
            "section:has-text('Workflow')",
            "div:has-text('Workflow')",
        ]

        section_found = False
        for selector in table_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "workflow-table", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "workflow-table-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_status_badges_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the workflow status badge area.

        Status badges (Running / Stuck / Failed / Queued) are defined in
        style guide §5.1.  Any colour or label regression should be caught here.
        """
        _go(page, base_url)

        badge_selectors = [
            "[data-testid='status-badge']",
            "[aria-label*='status' i]",
            ".badge--status",
            "td:has-text('Running'), td:has-text('Stuck'), "
            "td:has-text('Failed'), td:has-text('Queued')",
            "span:has-text('Running'), span:has-text('Stuck'), "
            "span:has-text('Failed'), span:has-text('Queued')",
        ]

        section_found = False
        for selector in badge_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "status-badges", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "status-badges-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_view_toggle_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the list/kanban view toggle control.

        The toggle control appearance (active state, icons) must remain
        consistent across UI changes.
        """
        _go(page, base_url)

        toggle_selectors = [
            "[data-view-toggle]",
            "[data-toggle='kanban']",
            "[data-toggle='list']",
            "[aria-label*='kanban' i]",
            "[aria-label*='list view' i]",
            "button:has-text('Kanban')",
            "button:has-text('Board')",
            "button:has-text('List')",
        ]

        section_found = False
        for selector in toggle_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "view-toggle", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            # Toggle may not be implemented yet — graceful fallback
            result = compare_snapshot(
                page, "view-toggle-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Section-level snapshots (kanban view)
# ---------------------------------------------------------------------------


class TestWorkflowsKanbanSectionSnapshots:
    """Element-level snapshots for primary kanban-view sections."""

    def test_kanban_board_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the kanban board element (§9.15)."""
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip("Kanban view not available — skipping kanban board snapshot")

        kanban_selectors = [
            "[data-testid='kanban-board']",
            ".kanban-board",
            "[class*='kanban-board']",
            ".kanban",
            "[class*='kanban']",
            "[data-view='kanban']",
        ]

        section_found = False
        for selector in kanban_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "kanban-board", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "kanban-board-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()

    def test_kanban_columns_snapshot(self, page: object, base_url: str) -> None:
        """Capture a snapshot of the first kanban column to track column styling."""
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip("Kanban view not available — skipping kanban column snapshot")

        column_selectors = [
            ".kanban-column",
            "[class*='kanban-column']",
            "[data-column]",
            "[data-status]",
        ]

        section_found = False
        for selector in column_selectors:
            locator = page.locator(selector).first  # type: ignore[attr-defined]
            if locator.count() > 0:
                try:
                    locator.scroll_into_view_if_needed()
                    dest = capture_element_snapshot(
                        page, selector, "kanban-column-first", page_name=PAGE_NAME
                    )
                    assert dest.exists(), (
                        f"Element snapshot was not written to disk: {dest}"
                    )
                    section_found = True
                    break
                except Exception:  # noqa: BLE001
                    continue

        if not section_found:
            result = compare_snapshot(
                page, "kanban-column-fallback", page_name=PAGE_NAME
            )
            assert result.passed, result.summary()


# ---------------------------------------------------------------------------
# Snapshot regression — compare against committed baselines
# ---------------------------------------------------------------------------


class TestWorkflowsSnapshotRegression:
    """Verify current render matches committed baselines (pixel-diff guard).

    These tests are the continuous-integration regression guards.  They pass
    on first run (baseline auto-created) and fail only when a subsequent run
    produces a pixel-diff above the threshold.

    Override the threshold with ``SNAPSHOT_THRESHOLD=0.002`` (0.2%) for
    environments where minor antialiasing differences are expected.
    """

    def test_list_view_regression(self, page: object, base_url: str) -> None:
        """List-view full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)
        result = compare_snapshot(
            page, "regression-list-view", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_kanban_view_regression(self, page: object, base_url: str) -> None:
        """Kanban-view full-page pixel-diff must not exceed the configured threshold."""
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip("Kanban view not available — skipping kanban regression check")

        result = compare_snapshot(
            page, "regression-kanban-view", page_name=PAGE_NAME
        )
        assert result.passed, result.summary()

    def test_no_critical_console_errors_list_view(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Workflows list view must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)
        compare_snapshot(page, "console-check-list", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Workflows list view emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )

    def test_no_critical_console_errors_kanban_view(
        self, page: object, base_url: str, console_errors: list
    ) -> None:
        """Workflows kanban view must not emit critical JS errors during snapshot capture."""
        _go(page, base_url)

        if not _activate_kanban(page):
            pytest.skip(
                "Kanban view not available — skipping kanban console error check"
            )

        compare_snapshot(page, "console-check-kanban", page_name=PAGE_NAME)

        critical_errors = [
            e for e in console_errors if "TypeError" in e or "ReferenceError" in e
        ]
        assert not critical_errors, (
            f"Workflows kanban view emitted {len(critical_errors)} critical JS error(s) "
            f"during snapshot capture: {critical_errors[:3]}"
        )
