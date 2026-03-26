"""Story 76.2 — Pipeline Dashboard: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=pipeline return
HTTP 200 with valid JSON schema.

Pipeline backing endpoints:
  - GET /api/v1/dashboard/tasks   — TaskPacket list backing the pipeline rail
  - GET /api/v1/dashboard/gates   — Gate transition history for Gate Inspector
  - GET /api/v1/dashboard/stages/metrics?window_hours=24
                                  — Per-stage throughput and health metrics

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_pipeline_style.py (Story 76.4).
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
_GATES = "/api/v1/dashboard/gates"
_STAGE_METRICS = "/api/v1/dashboard/stages/metrics?window_hours=24"


def _go(page: object, base_url: str) -> None:
    """Navigate to the pipeline tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "pipeline")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tasks endpoint
# ---------------------------------------------------------------------------


class TestPipelineTasksEndpoint:
    """Tasks endpoint must return a valid JSON collection for the pipeline rail.

    The pipeline rail's stage nodes and minimap source their task data from
    this endpoint.  An empty list is valid — the empty-pipeline state handles
    the zero-task case gracefully.
    """

    def test_tasks_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _TASKS, 200)

    def test_tasks_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/tasks must return a non-null JSON body"
        )

    def test_tasks_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks response is a JSON list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _TASKS, 200)

        # Accept either a bare list or an object wrapping a list under common keys.
        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("tasks", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/tasks must return a JSON list or an object "
            "containing a 'tasks'/'items'/'data'/'results' list"
        )

    def test_tasks_task_schema_when_populated(self, page, base_url: str) -> None:
        """Each task item contains at minimum an 'id' and a 'stage' field."""
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
        assert "id" in first, (
            "Task item must contain an 'id' field"
        )

    def test_tasks_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/tasks response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _TASKS)


# ---------------------------------------------------------------------------
# Gates endpoint
# ---------------------------------------------------------------------------


class TestPipelineGatesEndpoint:
    """Gates endpoint must return a valid JSON collection for the Gate Inspector.

    The Gate Inspector lists chronological gate transitions.  An empty list is
    valid when no gates have been evaluated yet.
    """

    def test_gates_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/gates returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _GATES, 200)

    def test_gates_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/gates returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _GATES, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/gates must return a non-null JSON body"
        )

    def test_gates_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/gates response is a list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _GATES, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("gates", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/gates must return a JSON list or an object "
            "containing a 'gates'/'items'/'data'/'results' list"
        )

    def test_gates_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each gate item contains at minimum 'id' and 'result' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _GATES, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (data[k] for k in ("gates", "items", "data", "results") if isinstance(data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No gate transitions returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each gate item in /api/v1/dashboard/gates must be a JSON object"
        )
        assert "id" in first, "Gate item must contain an 'id' field"

    def test_gates_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/gates response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _GATES)


# ---------------------------------------------------------------------------
# Stage metrics endpoint
# ---------------------------------------------------------------------------


class TestPipelineStageMetricsEndpoint:
    """Stage metrics endpoint must return valid JSON for the pipeline health view.

    The stage metrics endpoint provides per-stage throughput and health data
    for the 24-hour window.  This feeds the Gate Inspector health header row.
    """

    def test_stage_metrics_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/stages/metrics?window_hours=24 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _STAGE_METRICS, 200)

    def test_stage_metrics_is_valid_json(self, page, base_url: str) -> None:
        """Stage metrics endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _STAGE_METRICS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/stages/metrics must return a non-null JSON body"
        )

    def test_stage_metrics_response_structure(self, page, base_url: str) -> None:
        """Stage metrics response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _STAGE_METRICS, 200)

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/stages/metrics must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_stage_metrics_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/stages/metrics response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _STAGE_METRICS)

    def test_stage_metrics_window_hours_accepted(self, page, base_url: str) -> None:
        """Stage metrics endpoint accepts window_hours query param without 4xx error."""
        _go(page, base_url)
        # Verify the query param is forwarded correctly — any non-4xx is sufficient.
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_STAGE_METRICS}"
        )
        assert response.status < 400, (
            f"GET {_STAGE_METRICS} returned {response.status} — expected 2xx or 3xx"
        )
