"""Epic 59.2 — Fleet Dashboard: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/dashboard return HTTP 200
with valid JSON schema.

Dashboard backing endpoints:
  - GET /healthz                  — global liveness probe
  - GET /admin/health             — aggregated platform health (Temporal, Postgres, JetStream, Router)
  - GET /admin/workflows/metrics  — workflow summary (running, stuck, failed, queue depth)
  - GET /admin/repos              — registered repository list
  - GET /admin/repos/health       — per-repo health summary for the fleet dashboard

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_dashboard_style.py (Epic 59.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_fields,
    assert_api_no_error,
    assert_api_returns_data,
)

pytestmark = pytest.mark.playwright

# All API routes are relative to the base_url provided by the conftest fixture.
_HEALTHZ = "/healthz"
_ADMIN_HEALTH = "/admin/health"
_WORKFLOW_METRICS = "/admin/workflows/metrics"
_REPOS = "/admin/repos"
_REPOS_HEALTH = "/admin/repos/health"


class TestDashboardLivenessEndpoint:
    """Global liveness probe must be reachable and return a healthy JSON body.

    The conftest ``_require_playwright_stack`` fixture already gates the entire
    session on this endpoint, but we assert the schema here explicitly so that
    future regressions in the response shape are caught.
    """

    def test_healthz_returns_200(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_returns_status_field(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains a 'status' field."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])

    def test_healthz_no_error_body(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_no_error(page, _HEALTHZ)


class TestDashboardSystemHealthEndpoint:
    """Admin health endpoint must return structured per-service status.

    The dashboard System Health section depends on this endpoint to display
    Temporal, Postgres, JetStream, and Router service cards.
    """

    def test_admin_health_returns_200(self, page, base_url: str) -> None:
        """GET /admin/health returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _ADMIN_HEALTH, 200)

    def test_admin_health_has_service_fields(self, page, base_url: str) -> None:
        """GET /admin/health response contains temporal, postgres, jetstream, and router fields."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_fields(
            page,
            _ADMIN_HEALTH,
            required_fields=["temporal", "postgres", "jetstream", "router"],
        )

    def test_admin_health_temporal_has_status(self, page, base_url: str) -> None:
        """Temporal service entry contains a 'status' field."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _ADMIN_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/health"
        temporal = data.get("temporal")
        assert isinstance(temporal, dict), (
            "Field 'temporal' in /admin/health must be a JSON object"
        )
        assert "status" in temporal, (
            "Temporal service object must contain a 'status' field"
        )

    def test_admin_health_postgres_has_status(self, page, base_url: str) -> None:
        """Postgres service entry contains a 'status' field."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _ADMIN_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/health"
        postgres = data.get("postgres")
        assert isinstance(postgres, dict), (
            "Field 'postgres' in /admin/health must be a JSON object"
        )
        assert "status" in postgres, (
            "Postgres service object must contain a 'status' field"
        )

    def test_admin_health_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/health response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_no_error(page, _ADMIN_HEALTH)


class TestDashboardWorkflowMetricsEndpoint:
    """Workflow metrics endpoint must return aggregate counters for the dashboard summary.

    The dashboard Workflow Summary section renders Running / Stuck / Failed / Queue
    counts sourced from this endpoint.
    """

    def test_workflow_metrics_returns_200(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)

    def test_workflow_metrics_has_aggregate_fields(self, page, base_url: str) -> None:
        """Workflow metrics response contains running, stuck, failed, queue_depth fields."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/workflows/metrics"

        # The aggregate may be nested under an 'aggregate' key or at root level.
        aggregate = data.get("aggregate", data)
        assert isinstance(aggregate, dict), (
            "Workflow metrics must contain an 'aggregate' object or top-level fields"
        )

        for field in ("running", "stuck", "failed"):
            assert field in aggregate, (
                f"Workflow metrics aggregate must contain '{field}' field"
            )

    def test_workflow_metrics_queue_depth_present(self, page, base_url: str) -> None:
        """Workflow metrics response contains a queue depth indicator."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/workflows/metrics"

        # Accept queue_depth at root, in aggregate, or as 'queue' key.
        aggregate = data.get("aggregate", data)
        has_queue = (
            "queue_depth" in data
            or "queue_depth" in aggregate
            or "queue" in data
            or "queue" in aggregate
        )
        assert has_queue, (
            "Workflow metrics must contain a queue depth field "
            "('queue_depth' or 'queue') at root or under 'aggregate'"
        )

    def test_workflow_metrics_values_are_numeric(self, page, base_url: str) -> None:
        """Workflow metric counts are integers (including zero for an empty system)."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/workflows/metrics"

        aggregate = data.get("aggregate", data)
        for field in ("running", "stuck", "failed"):
            if field in aggregate:
                assert isinstance(aggregate[field], int), (
                    f"Workflow metrics field '{field}' must be an integer, "
                    f"got {type(aggregate[field]).__name__!r}"
                )

    def test_workflow_metrics_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_no_error(page, _WORKFLOW_METRICS)


class TestDashboardRepoListEndpoint:
    """Repo list endpoint must return a valid JSON collection.

    The dashboard Repo Activity section depends on this endpoint (or the
    /admin/repos/health variant) to populate the per-repo activity table.
    """

    def test_repos_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _REPOS, 200)

    def test_repos_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/repos returns valid JSON (object or list)."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert data is not None, "GET /admin/repos must return a JSON body"

    def test_repos_response_contains_repos_collection(self, page, base_url: str) -> None:
        """GET /admin/repos response contains a 'repos' list."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_returns_data(page, _REPOS, list_key="repos", allow_empty=True)

    def test_repos_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_no_error(page, _REPOS)


class TestDashboardRepoHealthEndpoint:
    """Repo health summary endpoint provides per-repo health data for the dashboard.

    This endpoint backs the Repo Activity table with tier, status, workflow
    counts, and last-activity timestamps.
    """

    def test_repos_health_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

    def test_repos_health_contains_repos_field(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains a 'repos' list."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/repos/health"
        assert "repos" in data, (
            "GET /admin/repos/health must contain a 'repos' field"
        )
        assert isinstance(data["repos"], list), (
            "The 'repos' field in /admin/repos/health must be a list"
        )

    def test_repos_health_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each repo health item contains owner/repo, tier, status, and health fields."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from /admin/repos/health"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — empty health list is acceptable for 59.2")

        first = repos[0]
        assert isinstance(first, dict), "Each item in repos/health must be a JSON object"

        for field in ("tier", "status", "health"):
            assert field in first, (
                f"Repo health item must contain '{field}' field"
            )

    def test_repos_health_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dashboard")
        assert_api_no_error(page, _REPOS_HEALTH)
