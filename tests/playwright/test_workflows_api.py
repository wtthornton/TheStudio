"""Epic 61.2 — Workflow Console: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/workflows return HTTP 200
with valid JSON schema.

Workflow Console backing endpoints:
  - GET /admin/workflows           — list all workflows (WorkflowListResponse)
  - GET /admin/workflows/{id}      — workflow detail with timeline (WorkflowDetailResponse)
  - GET /admin/workflows/metrics   — aggregate metrics (WorkflowMetricsResponse)
  - GET /admin/ui/partials/workflows?view=kanban — kanban board HTML partial

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_workflows_style.py (Epic 61.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)

pytestmark = pytest.mark.playwright

_WORKFLOWS = "/admin/workflows"
_WORKFLOW_METRICS = "/admin/workflows/metrics"
_WORKFLOWS_PARTIAL_KANBAN = "/admin/ui/partials/workflows?view=kanban"


class TestWorkflowListEndpoint:
    """Workflow list endpoint must return a valid JSON collection.

    The /admin/ui/workflows page renders its table from this endpoint; any schema
    regression here breaks the operator's primary workflow management surface.
    """

    def test_workflows_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/workflows returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_endpoint(page, "GET", _WORKFLOWS, 200)

    def test_workflows_list_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/workflows returns a non-null JSON body."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert data is not None, "GET /admin/workflows must return a non-null JSON body"

    def test_workflows_list_contains_workflows_field(self, page, base_url: str) -> None:
        """GET /admin/workflows response contains a 'workflows' list field."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_returns_data(page, _WORKFLOWS, list_key="workflows", allow_empty=True)

    def test_workflows_list_contains_total_field(self, page, base_url: str) -> None:
        """GET /admin/workflows response contains a numeric 'total' field."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        assert "total" in data, "GET /admin/workflows must contain a 'total' field"
        assert isinstance(data["total"], int), (
            f"Field 'total' must be an integer, got {type(data['total']).__name__!r}"
        )

    def test_workflows_list_contains_filtered_by_field(self, page, base_url: str) -> None:
        """GET /admin/workflows response contains a 'filtered_by' metadata object."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        assert "filtered_by" in data, (
            "GET /admin/workflows must contain a 'filtered_by' field"
        )
        assert isinstance(data["filtered_by"], dict), (
            "The 'filtered_by' field must be a JSON object"
        )

    def test_workflows_total_matches_workflows_length(self, page, base_url: str) -> None:
        """'total' field matches the length of the 'workflows' list."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])
        total = data.get("total", -1)
        assert isinstance(workflows, list), "'workflows' field must be a list"
        assert total == len(workflows), (
            f"'total' ({total}) must equal len(workflows) ({len(workflows)})"
        )

    def test_workflows_list_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each item in the workflows list contains required fields."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — empty list is acceptable for 61.2")

        first = workflows[0]
        assert isinstance(first, dict), "Each item in workflows list must be a JSON object"

        for field in ("workflow_id", "repo_name", "status", "current_step", "started_at"):
            assert field in first, (
                f"Workflow list item must contain '{field}' field"
            )

    def test_workflows_list_status_values_are_valid(self, page, base_url: str) -> None:
        """Each workflow item's 'status' is one of the expected WorkflowStatus values."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — status validation requires at least one workflow")

        valid_statuses = {"running", "stuck", "paused", "completed", "failed", "canceled", "terminated"}
        for wf in workflows:
            status_val = str(wf.get("status", "")).lower()
            assert status_val in valid_statuses, (
                f"Workflow status must be one of {valid_statuses!r}, got {status_val!r}"
            )

    def test_workflows_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/workflows response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_no_error(page, _WORKFLOWS)


class TestWorkflowDetailEndpoint:
    """Workflow detail endpoint must return the full WorkflowDetail for a given ID.

    The sliding inspector panel on /admin/ui/workflows populates from this endpoint.
    Without it the operator cannot view timeline, retry info, or escalation state.
    """

    def test_workflow_detail_returns_200_when_workflow_exists(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} returns HTTP 200 for a valid workflow ID."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — detail endpoint test requires at least one workflow")

        workflow_id = workflows[0]["workflow_id"]
        assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{workflow_id}", 200)

    def test_workflow_detail_schema_when_populated(self, page, base_url: str) -> None:
        """GET /admin/workflows/{id} response contains all WorkflowDetailResponse fields."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — detail schema test requires at least one workflow")

        workflow_id = workflows[0]["workflow_id"]
        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{workflow_id}", 200)

        assert isinstance(detail, dict), (
            f"GET /admin/workflows/{{id}} must return a JSON object, got {type(detail)!r}"
        )

        expected_fields = (
            "workflow_id", "repo_name", "status", "current_step",
            "attempt_count", "complexity", "started_at", "timeline",
            "retry_info", "escalation_info",
        )
        for field in expected_fields:
            assert field in detail, (
                f"WorkflowDetailResponse must contain '{field}' field"
            )

    def test_workflow_detail_timeline_is_list(self, page, base_url: str) -> None:
        """GET /admin/workflows/{id} 'timeline' field is a list."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — timeline test requires at least one workflow")

        workflow_id = workflows[0]["workflow_id"]
        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{workflow_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from workflow detail endpoint"

        timeline = detail.get("timeline")
        assert isinstance(timeline, list), (
            f"'timeline' field must be a list, got {type(timeline)!r}"
        )

    def test_workflow_detail_retry_info_is_object(self, page, base_url: str) -> None:
        """GET /admin/workflows/{id} 'retry_info' field is a JSON object."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — retry_info test requires at least one workflow")

        workflow_id = workflows[0]["workflow_id"]
        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{workflow_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from workflow detail endpoint"

        retry_info = detail.get("retry_info")
        assert isinstance(retry_info, dict), (
            f"'retry_info' must be a JSON object, got {type(retry_info)!r}"
        )

    def test_workflow_detail_returns_404_for_unknown_id(self, page, base_url: str) -> None:
        """GET /admin/workflows/{id} returns 404 for a non-existent workflow ID."""
        page.goto(f"{base_url}/admin/ui/workflows")
        unknown_id = "nonexistent-workflow-id-00000000"
        assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{unknown_id}", 404)

    def test_workflow_detail_no_error_body_for_valid_id(self, page, base_url: str) -> None:
        """GET /admin/workflows/{id} for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOWS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows"
        workflows = data.get("workflows", [])

        if not workflows:
            pytest.skip("No workflows registered — error-body test requires at least one workflow")

        workflow_id = workflows[0]["workflow_id"]
        assert_api_no_error(page, f"{_WORKFLOWS}/{workflow_id}")


class TestWorkflowMetricsEndpoint:
    """Workflow metrics endpoint must return aggregate pipeline health data.

    The fleet dashboard workflow summary section consumes this endpoint to
    surface running, stuck, failed, and queued counts at a glance.
    """

    def test_workflow_metrics_returns_200(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)

    def test_workflow_metrics_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics returns a non-null JSON body."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert data is not None, "GET /admin/workflows/metrics must return a non-null JSON body"
        assert isinstance(data, dict), "GET /admin/workflows/metrics must return a JSON object"

    def test_workflow_metrics_contains_running_field(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains a numeric 'running' field."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows/metrics"
        assert "running" in data, (
            "GET /admin/workflows/metrics must contain a 'running' field"
        )
        assert isinstance(data["running"], int), (
            f"Field 'running' must be an integer, got {type(data['running']).__name__!r}"
        )

    def test_workflow_metrics_contains_stuck_field(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains a numeric 'stuck' field."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows/metrics"
        assert "stuck" in data, (
            "GET /admin/workflows/metrics must contain a 'stuck' field"
        )
        assert isinstance(data["stuck"], int), (
            f"Field 'stuck' must be an integer, got {type(data['stuck']).__name__!r}"
        )

    def test_workflow_metrics_contains_failed_field(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains a numeric 'failed' field."""
        page.goto(f"{base_url}/admin/ui/workflows")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/workflows/metrics"
        assert "failed" in data, (
            "GET /admin/workflows/metrics must contain a 'failed' field"
        )
        assert isinstance(data["failed"], int), (
            f"Field 'failed' must be an integer, got {type(data['failed']).__name__!r}"
        )

    def test_workflow_metrics_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_no_error(page, _WORKFLOW_METRICS)


class TestWorkflowKanbanPartialEndpoint:
    """Kanban partial endpoint must return HTML content for the board view.

    The /admin/ui/workflows page uses HTMX to load this partial when the
    operator switches to kanban view. The endpoint must return 200 with
    non-empty HTML content.
    """

    def test_kanban_partial_returns_200(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/workflows?view=kanban returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/workflows")
        response = page.request.get(f"{base_url}{_WORKFLOWS_PARTIAL_KANBAN}")
        assert response.status == 200, (
            f"GET {_WORKFLOWS_PARTIAL_KANBAN} must return HTTP 200, got {response.status}"
        )

    def test_kanban_partial_returns_html_content(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/workflows?view=kanban returns non-empty HTML."""
        page.goto(f"{base_url}/admin/ui/workflows")
        response = page.request.get(f"{base_url}{_WORKFLOWS_PARTIAL_KANBAN}")
        assert response.status == 200, (
            f"GET {_WORKFLOWS_PARTIAL_KANBAN} must return HTTP 200"
        )
        body = response.text()
        assert len(body.strip()) > 0, (
            f"GET {_WORKFLOWS_PARTIAL_KANBAN} must return non-empty HTML"
        )

    def test_kanban_partial_contains_kanban_structure(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/workflows?view=kanban HTML contains kanban-board markup."""
        page.goto(f"{base_url}/admin/ui/workflows")
        response = page.request.get(f"{base_url}{_WORKFLOWS_PARTIAL_KANBAN}")
        assert response.status == 200, (
            f"GET {_WORKFLOWS_PARTIAL_KANBAN} must return HTTP 200"
        )
        body = response.text().lower()
        kanban_markers = ("kanban", "col", "running", "failed", "completed")
        assert any(marker in body for marker in kanban_markers), (
            f"Kanban partial HTML must contain kanban board structure "
            f"(one of {kanban_markers!r})"
        )

    def test_list_partial_returns_200(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/workflows?view=list returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/workflows")
        response = page.request.get(
            f"{base_url}/admin/ui/partials/workflows?view=list"
        )
        assert response.status == 200, (
            "GET /admin/ui/partials/workflows?view=list must return HTTP 200, "
            f"got {response.status}"
        )
