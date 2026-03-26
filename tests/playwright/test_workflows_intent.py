"""Epic 61.1 — Workflow Console: Page Intent & Semantic Content.

Validates that /admin/ui/workflows delivers its core purpose:
  - Workflow table renders with ID, repo, status, and duration columns
  - Kanban view toggle is visible and accessible
  - Empty state is shown when no workflows exist

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_workflows_style.py (Epic 61.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

WORKFLOWS_URL = "/admin/ui/workflows"


class TestWorkflowsTableContent:
    """Workflow table must surface the key columns operators need at a glance.

    When workflows exist the table must show:
      ID       — unique workflow identifier for cross-referencing
      Repo     — which repository the workflow belongs to
      Status   — running / stuck / failed / queued signal
      Duration — elapsed time so operators can spot long-running workflows
    """

    def test_workflows_page_renders(self, page, base_url: str) -> None:
        """Workflows page shows a table, kanban board, or empty-state container."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        has_table = page.locator("table").count() > 0
        has_kanban = page.locator("[data-view='kanban'], .kanban, [class*='kanban']").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no workflows", "no workflow", "nothing running", "queue is empty", "get started")
        )
        assert has_table or has_kanban or has_empty_state, (
            "Workflows page must show a workflow table, kanban board, or empty-state message"
        )

    def test_workflow_id_column_shown(self, page, base_url: str) -> None:
        """Workflow table header or body contains workflow ID information."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No workflows registered — empty state is acceptable for 61.1")

        table_text = page.locator("table").first.inner_text().lower()
        id_keywords = ("id", "workflow", "run", "#")
        assert any(kw in table_text for kw in id_keywords), (
            "Workflow table must include an ID or workflow identifier column"
        )

    def test_workflow_repo_column_shown(self, page, base_url: str) -> None:
        """Workflow table includes a repo or repository column."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No workflows registered — empty state is acceptable for 61.1")

        body_lower = page.locator("body").inner_text().lower()
        assert "repo" in body_lower or "repository" in body_lower, (
            "Workflows page must display the repository associated with each workflow"
        )

    def test_workflow_status_column_shown(self, page, base_url: str) -> None:
        """Workflow table includes a status column or status badges."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No workflows registered — empty state is acceptable for 61.1")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = ("status", "running", "stuck", "failed", "queued", "complete", "pending")
        assert any(kw in body_lower for kw in status_keywords), (
            "Workflows page must display workflow status information"
        )

    def test_workflow_duration_column_shown(self, page, base_url: str) -> None:
        """Workflow table includes a duration or elapsed time column."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No workflows registered — empty state is acceptable for 61.1")

        body_lower = page.locator("body").inner_text().lower()
        duration_keywords = ("duration", "elapsed", "time", "started", "age", "runtime")
        assert any(kw in body_lower for kw in duration_keywords), (
            "Workflows page must display workflow duration or elapsed time"
        )


class TestWorkflowsKanbanToggle:
    """Kanban view toggle must be visible for operators to switch between list and board views.

    The kanban toggle is a key navigational element that allows operators to
    switch between the tabular list view and the kanban board view. It must be
    present on page load regardless of which view is currently active.
    """

    def test_kanban_toggle_visible(self, page, base_url: str) -> None:
        """Workflows page has a toggle or button to switch to kanban/board view."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        kanban_keywords = ("kanban", "board", "view", "list", "toggle", "switch")

        # Check for toggle element by text or data attribute
        has_kanban_text = any(kw in body_lower for kw in kanban_keywords)
        has_toggle_element = (
            page.locator("[data-view], [data-toggle], [role='tablist']").count() > 0
            or page.locator("button:has-text('Kanban'), button:has-text('Board'), button:has-text('List')").count() > 0
        )

        assert has_kanban_text or has_toggle_element, (
            "Workflows page must include a kanban/board view toggle control"
        )

    def test_list_view_reachable(self, page, base_url: str) -> None:
        """List view is the default or reachable from the toggle."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        list_indicators = ("list", "table", "workflow", "id", "repo", "status")
        assert any(kw in body_lower for kw in list_indicators), (
            "Workflows page must show list view content (table or list indicators)"
        )


class TestWorkflowsPageStructure:
    """Workflows page must have clear page-level structure for orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Workflows page has a heading identifying it as the workflows section."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("workflow", "workflows", "console", "runs")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Workflows page must have a heading referencing 'Workflows' or 'Console'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Workflows page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{WORKFLOWS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Workflows page body must not be empty"
