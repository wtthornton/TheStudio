"""Epic 72.2 — Cost Dashboard: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/cost-dashboard return HTTP 200
with valid JSON schema.

Cost Dashboard backing endpoints:
  - GET /api/v1/dashboard/budget/summary   — total spend, call count, cache stats
  - GET /api/v1/dashboard/budget/history   — time-series spend by model and day
  - GET /api/v1/dashboard/budget/by-stage  — spend aggregated by pipeline stage
  - GET /api/v1/dashboard/budget/by-model  — spend aggregated by model identifier
  - GET /api/v1/dashboard/budget/config    — budget configuration (thresholds, actions)
  - GET /healthz                           — liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_cost_dashboard_style.py (Epic 72.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_BUDGET_SUMMARY = "/api/v1/dashboard/budget/summary"
_BUDGET_HISTORY = "/api/v1/dashboard/budget/history"
_BUDGET_BY_STAGE = "/api/v1/dashboard/budget/by-stage"
_BUDGET_BY_MODEL = "/api/v1/dashboard/budget/by-model"
_BUDGET_CONFIG = "/api/v1/dashboard/budget/config"
_HEALTHZ = "/healthz"

_COST_DASHBOARD_PAGE = "/admin/ui/cost-dashboard"


class TestBudgetSummaryEndpoint:
    """Budget summary endpoint must return aggregate spend data for the time window.

    The Cost Dashboard surfaces total model spend, call counts, and cache hit
    rates sourced from this endpoint so operators can track AI inference costs
    at a glance.
    """

    def test_budget_summary_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/summary returns HTTP 200."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)

    def test_budget_summary_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/summary returns a non-null JSON object."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/summary"
        )

    def test_budget_summary_has_total_cost(self, page, base_url: str) -> None:
        """Budget summary response contains 'total_cost' field."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/summary"
        )
        assert "total_cost" in data, (
            "Budget summary must contain a 'total_cost' field "
            "(required for the Cost Dashboard spend display)"
        )

    def test_budget_summary_total_cost_is_numeric(self, page, base_url: str) -> None:
        """Budget summary 'total_cost' is a non-negative numeric value."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/summary"
        )
        total_cost = data.get("total_cost")
        assert isinstance(total_cost, (int, float)) and total_cost >= 0, (
            f"Budget summary 'total_cost' must be a non-negative number, got {total_cost!r}"
        )

    def test_budget_summary_has_total_calls(self, page, base_url: str) -> None:
        """Budget summary response contains 'total_calls' field."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/summary"
        )
        assert "total_calls" in data, (
            "Budget summary must contain a 'total_calls' field"
        )

    def test_budget_summary_has_window_hours(self, page, base_url: str) -> None:
        """Budget summary response contains 'window_hours' field."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_SUMMARY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/summary"
        )
        assert "window_hours" in data, (
            "Budget summary must contain a 'window_hours' field"
        )

    def test_budget_summary_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/summary response contains no error payload."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _BUDGET_SUMMARY)


class TestBudgetHistoryEndpoint:
    """Budget history endpoint must return time-series spend by model and day.

    The Cost Dashboard chart section relies on this endpoint to render
    stacked-bar or line charts showing how model spend trends over time.
    """

    def test_budget_history_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/history returns HTTP 200."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _BUDGET_HISTORY, 200)

    def test_budget_history_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/history returns a non-null JSON object."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_HISTORY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/history"
        )

    def test_budget_history_has_by_day(self, page, base_url: str) -> None:
        """Budget history response contains 'by_day' list for time-series chart."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_HISTORY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/history"
        )
        assert "by_day" in data, (
            "Budget history must contain a 'by_day' field "
            "(required for the time-series chart)"
        )
        assert isinstance(data["by_day"], list), (
            "Budget history 'by_day' must be a JSON array"
        )

    def test_budget_history_has_by_model(self, page, base_url: str) -> None:
        """Budget history response contains 'by_model' list for per-model totals."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_HISTORY, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/history"
        )
        assert "by_model" in data, (
            "Budget history must contain a 'by_model' field"
        )
        assert isinstance(data["by_model"], list), (
            "Budget history 'by_model' must be a JSON array"
        )

    def test_budget_history_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/history response contains no error payload."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _BUDGET_HISTORY)


class TestBudgetByStageEndpoint:
    """Budget by-stage endpoint must return spend broken down by pipeline stage.

    The Cost Dashboard cost breakdown section uses this endpoint to show which
    pipeline stages (intake, context, intent, agent, etc.) consume the most
    model spend — helping operators identify optimization opportunities.
    """

    def test_budget_by_stage_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-stage returns HTTP 200."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _BUDGET_BY_STAGE, 200)

    def test_budget_by_stage_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-stage returns a non-null JSON object."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_STAGE, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-stage"
        )

    def test_budget_by_stage_has_by_stage(self, page, base_url: str) -> None:
        """Budget by-stage response contains 'by_stage' list."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_STAGE, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-stage"
        )
        assert "by_stage" in data, (
            "Budget by-stage response must contain a 'by_stage' field "
            "(required for the pipeline cost breakdown)"
        )
        assert isinstance(data["by_stage"], list), (
            "Budget by-stage 'by_stage' must be a JSON array"
        )

    def test_budget_by_stage_has_total_cost(self, page, base_url: str) -> None:
        """Budget by-stage response contains 'total_cost' field."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_STAGE, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-stage"
        )
        assert "total_cost" in data, (
            "Budget by-stage response must contain a 'total_cost' field"
        )

    def test_budget_by_stage_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-stage response contains no error payload."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _BUDGET_BY_STAGE)


class TestBudgetByModelEndpoint:
    """Budget by-model endpoint must return spend broken down by model identifier.

    The Cost Dashboard model spend section uses this data to show per-model
    cost contributions so operators can compare model costs and make routing
    decisions to optimize spend.
    """

    def test_budget_by_model_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-model returns HTTP 200."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _BUDGET_BY_MODEL, 200)

    def test_budget_by_model_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-model returns a non-null JSON object."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_MODEL, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-model"
        )

    def test_budget_by_model_has_by_model(self, page, base_url: str) -> None:
        """Budget by-model response contains 'by_model' list."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_MODEL, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-model"
        )
        assert "by_model" in data, (
            "Budget by-model response must contain a 'by_model' field "
            "(required for the per-model cost display)"
        )
        assert isinstance(data["by_model"], list), (
            "Budget by-model 'by_model' must be a JSON array"
        )

    def test_budget_by_model_has_total_cost(self, page, base_url: str) -> None:
        """Budget by-model response contains 'total_cost' field."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_BY_MODEL, 200)
        assert isinstance(data, dict), (
            "Expected JSON object from /api/v1/dashboard/budget/by-model"
        )
        assert "total_cost" in data, (
            "Budget by-model response must contain a 'total_cost' field"
        )

    def test_budget_by_model_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-model response contains no error payload."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _BUDGET_BY_MODEL)


class TestBudgetConfigEndpoint:
    """Budget config endpoint must return the singleton budget configuration.

    The Cost Dashboard budget threshold controls are driven by this endpoint,
    which surfaces warning and hard-cap thresholds so operators can see and
    adjust automated budget-enforcement behavior.
    """

    def test_budget_config_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/config returns HTTP 200."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _BUDGET_CONFIG, 200)

    def test_budget_config_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/config returns a non-null JSON object."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _BUDGET_CONFIG, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/config must return a non-null JSON body"
        )

    def test_budget_config_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/config response contains no error payload."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _BUDGET_CONFIG)


class TestCostDashboardLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Cost Dashboard.

    The Cost Dashboard shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after cost routes are added.
    """

    def test_healthz_returns_200_from_cost_dashboard(
        self, page, base_url: str
    ) -> None:
        """GET /healthz returns HTTP 200 when cost dashboard is loaded."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_cost_dashboard(
        self, page, base_url: str
    ) -> None:
        """GET /healthz JSON body contains 'status' field (cost dashboard context)."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_cost_dashboard(
        self, page, base_url: str
    ) -> None:
        """GET /healthz response contains no error payload (cost dashboard context)."""
        page.goto(f"{base_url}{_COST_DASHBOARD_PAGE}")
        assert_api_no_error(page, _HEALTHZ)
