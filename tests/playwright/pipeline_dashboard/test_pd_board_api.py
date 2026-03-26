"""Story 76.6 — Backlog Board: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=board return
HTTP 200 with valid JSON schema.

Board backing endpoints:
  - GET /api/v1/dashboard/tasks           — TaskPacket list (shared with pipeline)
  - GET /api/v1/dashboard/board/preferences — Board view preferences (column order, filters)

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_board_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_TASKS = "/api/v1/dashboard/tasks"
_BOARD_PREFS = "/api/v1/dashboard/board/preferences"


def _go(page: object, base_url: str) -> None:
    """Navigate to the board tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "board")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tasks endpoint (board context)
# ---------------------------------------------------------------------------


class TestBoardTasksEndpoint:
    """Tasks endpoint must return a valid JSON collection for the board columns.

    The Kanban board groups all TaskPackets from this endpoint into the six
    workflow columns.  An empty list is valid — the empty-board state handles
    the zero-task case gracefully.
    """

    def test_tasks_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns HTTP 200 from board context."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _TASKS, 200)

    def test_tasks_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/tasks must return a non-null JSON body "
            "(board context)"
        )

    def test_tasks_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks response is a JSON list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("tasks", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/tasks must return a JSON list or an object "
            "containing a 'tasks'/'items'/'data'/'results' list (board context)"
        )

    def test_tasks_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each task item contains at minimum 'id' and 'status' fields for board routing."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)

        # Normalise to a list.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (data[k] for k in ("tasks", "items", "data", "results") if isinstance(data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No tasks returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each task item in /api/v1/dashboard/tasks must be a JSON object"
        )
        assert "id" in first, "Task item must contain an 'id' field for board card rendering"

    def test_tasks_status_field_present_for_column_routing(self, page, base_url: str) -> None:
        """Task items contain a 'status' field so the board can route them to columns."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (data[k] for k in ("tasks", "items", "data", "results") if isinstance(data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No tasks returned — status field check not applicable")

        first = items[0]
        assert "status" in first, (
            "Task item must contain a 'status' field — "
            "the board uses status to assign tasks to columns "
            "(Triage / Planning / Building / Verify / Done / Rejected)"
        )

    def test_tasks_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _TASKS)

    def test_tasks_accepts_limit_param(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks accepts a 'limit' query parameter."""
        _go(page, base_url)
        url_with_limit = f"{_TASKS}?limit=200"
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{url_with_limit}"
        )
        assert response.status < 400, (
            f"GET {url_with_limit} returned {response.status} — "
            "expected 2xx or 3xx (board loads up to 200 tasks)"
        )


# ---------------------------------------------------------------------------
# Board preferences endpoint
# ---------------------------------------------------------------------------


class TestBoardPreferencesEndpoint:
    """Board preferences endpoint must return a valid JSON object.

    The board/preferences endpoint stores per-user view preferences such as
    column ordering and filter state.  A 404 or 200 with defaults is acceptable —
    the board renders without preferences.
    """

    def test_board_prefs_endpoint_reachable(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/board/preferences responds (2xx or 404)."""
        _go(page, base_url)
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_BOARD_PREFS}"
        )
        # 200 = preferences found, 404 = endpoint not yet implemented, both acceptable.
        assert response.status in (200, 404), (
            f"GET {_BOARD_PREFS} returned {response.status} — "
            "expected 200 (preferences found) or 404 (not yet implemented)"
        )

    def test_board_prefs_returns_json_when_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/board/preferences returns JSON when it returns 200."""
        _go(page, base_url)
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_BOARD_PREFS}"
        )
        if response.status == 404:
            pytest.skip(
                "Board preferences endpoint returns 404 — "
                "endpoint not yet implemented, JSON check skipped"
            )

        assert response.status == 200, (
            f"GET {_BOARD_PREFS} returned {response.status}"
        )
        try:
            data = response.json()
        except Exception as exc:
            raise AssertionError(
                f"GET {_BOARD_PREFS} returned non-JSON body: {exc}"
            ) from exc

        assert data is not None, (
            "GET /api/v1/dashboard/board/preferences must return a non-null body"
        )

    def test_board_prefs_no_server_error(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/board/preferences does not return a 5xx error."""
        _go(page, base_url)
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_BOARD_PREFS}"
        )
        assert response.status < 500, (
            f"GET {_BOARD_PREFS} returned server error {response.status} — "
            "must not return 5xx"
        )


# ---------------------------------------------------------------------------
# Cross-tab API consistency
# ---------------------------------------------------------------------------


class TestBoardApiConsistency:
    """Board API responses must be consistent with the pipeline tab API.

    Both the pipeline rail and the Kanban board consume the same tasks endpoint.
    Responses must not differ in shape based on which tab navigated first.
    """

    def test_tasks_same_response_from_board_and_pipeline(
        self, page, base_url: str
    ) -> None:
        """Tasks endpoint returns consistent schema regardless of active tab."""
        # Navigate to board first.
        _go(page, base_url)
        board_data = assert_api_endpoint(page, "GET", _TASKS, 200)

        # Now navigate to pipeline and check again.
        dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]
        pipeline_data = assert_api_endpoint(page, "GET", _TASKS, 200)

        # Both must return the same top-level type (list or dict).
        assert type(board_data) is type(pipeline_data), (
            "Tasks endpoint must return the same JSON type (list vs dict) "
            "regardless of which dashboard tab is active"
        )

    def test_tasks_endpoint_idempotent(self, page, base_url: str) -> None:
        """Two consecutive GET requests to /api/v1/dashboard/tasks return same schema."""
        _go(page, base_url)

        first = assert_api_endpoint(page, "GET", _TASKS, 200)
        second = assert_api_endpoint(page, "GET", _TASKS, 200)

        assert type(first) is type(second), (
            "Consecutive GET /api/v1/dashboard/tasks calls must return the same JSON type"
        )
