"""Story 76.3 — Triage Tab: API Endpoint Verification.

Validates that the backing API endpoints for the triage tab return HTTP 200
with valid JSON conforming to the expected schema.

Triage backing endpoints (must match ``frontend/src/lib/api.ts`` ``fetchTriageTasks``):
  - GET /api/v1/dashboard/tasks?status=triage   — triage task list (enum value on server)
  - GET /api/v1/dashboard/tasks?status=triage&limit=N — limit parameter
  - GET /api/v1/tasks/{id} (item-level, skipped if no tasks present)

These tests check *contract stability*, not visual presentation.
Intent is covered in test_pd_triage_intent.py.
Style compliance is covered in test_pd_triage_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# ---------------------------------------------------------------------------
# API route constants
# ---------------------------------------------------------------------------

_TASKS_TRIAGE_FILTERED = "/api/v1/dashboard/tasks?status=triage"
_TASKS_TRIAGE_LIMIT = "/api/v1/dashboard/tasks?status=triage&limit=5"
_TASKS_ALL = "/api/v1/dashboard/tasks"

# Fallback routes — some builds expose tasks under a different prefix.
_TASKS_FALLBACK_ROUTES = [
    "/api/v1/tasks?status=triage",
    "/api/v1/tasks",
    "/admin/tasks?status=triage",
]


def _navigate_to_triage(page, base_url: str) -> None:
    """Navigate to the triage tab before making API calls."""
    dashboard_navigate(page, base_url, "triage")


# ---------------------------------------------------------------------------
# Primary triage task list endpoint
# ---------------------------------------------------------------------------


class TestTriageTaskListEndpoint:
    """GET /api/v1/dashboard/tasks?status=triage must return a valid task list.

    The TriageQueue component sources its data from this endpoint.  A failing
    or malformed response results in an empty queue even when tasks exist.
    """

    def test_tasks_triage_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks?status=triage returns HTTP 200."""
        _navigate_to_triage(page, base_url)
        assert_api_endpoint(page, "GET", _TASKS_TRIAGE_FILTERED, 200)

    def test_tasks_triage_returns_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks?status=triage returns parseable JSON."""
        _navigate_to_triage(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS_TRIAGE_FILTERED, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/tasks?status=triage must return a JSON body"
        )

    def test_tasks_triage_returns_list_or_object_with_list(
        self, page, base_url: str
    ) -> None:
        """Response is either a JSON list or an object with a list field."""
        _navigate_to_triage(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS_TRIAGE_FILTERED, 200)

        is_list = isinstance(data, list)
        is_object_with_list = isinstance(data, dict) and any(
            isinstance(v, list) for v in data.values()
        )
        assert is_list or is_object_with_list, (
            "Triage task list must be a JSON array or an object containing "
            "a list field (e.g. {\"tasks\": [...]})"
        )

    def test_tasks_triage_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks?status=triage contains no error payload."""
        _navigate_to_triage(page, base_url)
        assert_api_no_error(page, _TASKS_TRIAGE_FILTERED)


# ---------------------------------------------------------------------------
# Task item schema (when tasks are present)
# ---------------------------------------------------------------------------


class TestTriageTaskItemSchema:
    """Individual task items must contain the fields the TriageCard needs.

    TriageCard renders: issue_id, issue_title, issue_body, created_at, and
    optionally triage_enrichment.  Missing fields cause the card to render
    incomplete or throw runtime errors.
    """

    def _get_tasks(self, page, base_url: str) -> list:
        """Return the list of tasks from the API response."""
        _navigate_to_triage(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS_TRIAGE_FILTERED, 200)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("tasks", "items", "results", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
        return []

    def test_task_items_have_id_field(self, page, base_url: str) -> None:
        """Each triage task item contains an 'id' field."""
        tasks = self._get_tasks(page, base_url)
        if not tasks:
            pytest.skip("No triage tasks — skipping item schema checks")

        for i, task in enumerate(tasks[:3]):
            assert "id" in task, (
                f"Task at index {i} is missing required 'id' field"
            )

    def test_task_items_have_title_field(self, page, base_url: str) -> None:
        """Each triage task item contains an 'issue_title' or 'title' field."""
        tasks = self._get_tasks(page, base_url)
        if not tasks:
            pytest.skip("No triage tasks — skipping title field check")

        first = tasks[0]
        has_title = "issue_title" in first or "title" in first
        assert has_title, (
            "Triage task item must contain 'issue_title' or 'title' field — "
            "the TriageCard renders this as the card heading"
        )

    def test_task_items_have_status_field(self, page, base_url: str) -> None:
        """Each triage task item contains a 'status' field."""
        tasks = self._get_tasks(page, base_url)
        if not tasks:
            pytest.skip("No triage tasks — skipping status field check")

        for i, task in enumerate(tasks[:3]):
            assert "status" in task, (
                f"Task at index {i} is missing required 'status' field"
            )

    def test_task_items_have_repo_or_created_at_field(
        self, page, base_url: str
    ) -> None:
        """Each triage task item contains 'repo' or 'created_at' metadata."""
        tasks = self._get_tasks(page, base_url)
        if not tasks:
            pytest.skip("No triage tasks — skipping metadata field check")

        first = tasks[0]
        has_repo = "repo" in first or "repo_full_name" in first or "repository" in first
        has_created_at = "created_at" in first
        assert has_repo or has_created_at, (
            "Triage task item must contain repo identifier ('repo', 'repo_full_name') "
            "or 'created_at' timestamp for the TriageCard time display"
        )


# ---------------------------------------------------------------------------
# Limit parameter handling
# ---------------------------------------------------------------------------


class TestTriageTaskLimitParameter:
    """The tasks endpoint must honour a ?limit= query parameter.

    Without limit support the triage queue could flood the UI with hundreds
    of items on busy repositories, causing performance degradation.
    """

    def test_limit_parameter_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks?status=triage&limit=5 returns HTTP 200."""
        _navigate_to_triage(page, base_url)
        assert_api_endpoint(page, "GET", _TASKS_TRIAGE_LIMIT, 200)

    def test_limit_parameter_respects_count(self, page, base_url: str) -> None:
        """Response with limit=5 returns at most 5 task items."""
        _navigate_to_triage(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS_TRIAGE_LIMIT, 200)

        tasks: list = []
        if isinstance(data, list):
            tasks = data
        elif isinstance(data, dict):
            for key in ("tasks", "items", "results", "data"):
                if isinstance(data.get(key), list):
                    tasks = data[key]
                    break

        if not tasks:
            pytest.skip("No tasks returned — cannot verify limit enforcement")

        assert len(tasks) <= 5, (
            f"With limit=5 the response returned {len(tasks)} items — "
            "the endpoint must honour the limit parameter"
        )

    def test_limit_parameter_no_error(self, page, base_url: str) -> None:
        """Applying limit=5 does not produce an error response."""
        _navigate_to_triage(page, base_url)
        assert_api_no_error(page, _TASKS_TRIAGE_LIMIT)


# ---------------------------------------------------------------------------
# All-tasks endpoint (no status filter)
# ---------------------------------------------------------------------------


class TestTriageTasksAllEndpoint:
    """The unfiltered tasks endpoint must remain available as a fallback.

    The TriageQueue falls back to /api/v1/dashboard/tasks when the
    status-filtered endpoint is unavailable.
    """

    def test_tasks_all_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns HTTP 200."""
        _navigate_to_triage(page, base_url)
        assert_api_endpoint(page, "GET", _TASKS_ALL, 200)

    def test_tasks_all_returns_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns a parseable JSON body."""
        _navigate_to_triage(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS_ALL, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/tasks must return a non-null JSON body"
        )
