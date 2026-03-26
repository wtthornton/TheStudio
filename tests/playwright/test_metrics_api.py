"""Epic 63.2 — Metrics: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/metrics return HTTP 200
with valid JSON schema.

Metrics page backing endpoints:
  - GET /admin/workflows/metrics     — aggregate workflow counts + 24h pass rate
  - GET /admin/readiness/metrics     — readiness gate pass/hold/escalate counts
  - GET /healthz                     — liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_metrics_style.py (Epic 63.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_WORKFLOW_METRICS = "/admin/workflows/metrics"
_READINESS_METRICS = "/admin/readiness/metrics"
_HEALTHZ = "/healthz"


class TestMetricsWorkflowEndpoint:
    """Workflow metrics endpoint must return aggregate counters with pass rate.

    The Metrics page surfaces pipeline pass/fail rates and workflow counts
    sourced from this endpoint to give operators a quick health summary.
    """

    def test_workflow_metrics_returns_200(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)

    def test_workflow_metrics_has_aggregate_field(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains an 'aggregate' object."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/workflows/metrics"
        )
        assert "aggregate" in data, (
            "Workflow metrics must contain an 'aggregate' field"
        )
        assert isinstance(data["aggregate"], dict), (
            "Workflow metrics 'aggregate' must be a JSON object"
        )

    def test_workflow_metrics_aggregate_has_counts(self, page, base_url: str) -> None:
        """Workflow metrics aggregate contains running, stuck, failed, completed."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/workflows/metrics"
        )
        aggregate = data.get("aggregate", {})
        assert isinstance(aggregate, dict), (
            "Workflow metrics 'aggregate' must be a JSON object"
        )
        for field in ("running", "stuck", "failed"):
            assert field in aggregate, (
                f"Workflow metrics aggregate must contain '{field}' field"
            )

    def test_workflow_metrics_has_pass_rate(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains a pass_rate_24h field."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/workflows/metrics"
        )
        assert "pass_rate_24h" in data, (
            "Workflow metrics must contain a 'pass_rate_24h' field "
            "(required for the Metrics page success-rate display)"
        )

    def test_workflow_metrics_pass_rate_is_numeric(self, page, base_url: str) -> None:
        """Workflow metrics pass_rate_24h is a numeric value."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _WORKFLOW_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/workflows/metrics"
        )
        pass_rate = data.get("pass_rate_24h")
        assert isinstance(pass_rate, (int, float)), (
            f"pass_rate_24h must be numeric, got {type(pass_rate).__name__!r}"
        )

    def test_workflow_metrics_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/workflows/metrics response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_no_error(page, _WORKFLOW_METRICS)


class TestMetricsReadinessEndpoint:
    """Readiness metrics endpoint must return gate pass/hold/escalate counts.

    The Metrics page gate status section relies on this endpoint to show
    how many evaluations passed, were held, or escalated — giving operators
    visibility into gate behavior over time.
    """

    def test_readiness_metrics_returns_200(self, page, base_url: str) -> None:
        """GET /admin/readiness/metrics returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)

    def test_readiness_metrics_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/readiness/metrics returns a non-null JSON body."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)
        assert data is not None, (
            "GET /admin/readiness/metrics must return a non-null JSON body"
        )

    def test_readiness_metrics_has_pass_count(self, page, base_url: str) -> None:
        """Readiness metrics response contains pass_count field."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/readiness/metrics"
        )
        assert "pass_count" in data, (
            "Readiness metrics must contain a 'pass_count' field"
        )

    def test_readiness_metrics_has_hold_and_escalate_counts(
        self, page, base_url: str
    ) -> None:
        """Readiness metrics response contains hold_count and escalate_count."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/readiness/metrics"
        )
        for field in ("hold_count", "escalate_count"):
            assert field in data, (
                f"Readiness metrics must contain '{field}' field"
            )

    def test_readiness_metrics_has_total_evaluations(
        self, page, base_url: str
    ) -> None:
        """Readiness metrics response contains total_evaluations field."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/readiness/metrics"
        )
        assert "total_evaluations" in data, (
            "Readiness metrics must contain a 'total_evaluations' field"
        )

    def test_readiness_metrics_counts_are_non_negative(
        self, page, base_url: str
    ) -> None:
        """Readiness metric counts are non-negative integers."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _READINESS_METRICS, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /admin/readiness/metrics"
        )
        for field in ("total_evaluations", "pass_count", "hold_count", "escalate_count"):
            if field in data:
                assert isinstance(data[field], int) and data[field] >= 0, (
                    f"Readiness metrics field '{field}' must be a non-negative integer, "
                    f"got {data[field]!r}"
                )

    def test_readiness_metrics_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/readiness/metrics response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_no_error(page, _READINESS_METRICS)


class TestMetricsLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Metrics page.

    The Metrics page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after metrics routes are added.
    """

    def test_healthz_returns_200_from_metrics_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz returns HTTP 200 when metrics page is loaded."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_metrics_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz JSON body contains 'status' field (metrics page context)."""
        page.goto(f"{base_url}/admin/ui/metrics")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_metrics_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz response contains no error payload (metrics page context)."""
        page.goto(f"{base_url}/admin/ui/metrics")
        assert_api_no_error(page, _HEALTHZ)
