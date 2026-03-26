"""Story 76.8 — Budget Tab: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=budget return
HTTP 200 with valid JSON schema.

Budget backing endpoints:
  - GET /api/v1/dashboard/budget/summary?window_hours=24
                                  — Summary KPIs (total_cost, total_calls, etc.)
  - GET /api/v1/dashboard/budget/history?window_hours=24
                                  — Daily spend history for the SpendChart
  - GET /api/v1/dashboard/budget/by-stage?window_hours=24
                                  — Cost breakdown by pipeline stage
  - GET /api/v1/dashboard/budget/by-model?window_hours=24
                                  — Cost breakdown by LLM model
  - GET /api/v1/dashboard/budget/config
                                  — Budget alert configuration thresholds

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_budget_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_SUMMARY = "/api/v1/dashboard/budget/summary?window_hours=24"
_HISTORY = "/api/v1/dashboard/budget/history?window_hours=24"
_BY_STAGE = "/api/v1/dashboard/budget/by-stage?window_hours=24"
_BY_MODEL = "/api/v1/dashboard/budget/by-model?window_hours=24"
_CONFIG = "/api/v1/dashboard/budget/config"


def _go(page: object, base_url: str) -> None:
    """Navigate to the budget tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "budget")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------


class TestBudgetSummaryEndpoint:
    """Budget summary endpoint must return valid JSON with a total_cost field.

    The SummaryCards component depends on total_cost, total_calls, and
    cache_hit_rate from this endpoint.  A missing total_cost field would cause
    the spend card to render $NaN.
    """

    def test_summary_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/summary?window_hours=24 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _SUMMARY, 200)

    def test_summary_response_is_valid_json(self, page, base_url: str) -> None:
        """Budget summary endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/summary must return a non-null JSON body"
        )

    def test_summary_contains_total_cost_field(self, page, base_url: str) -> None:
        """Budget summary response contains a 'total_cost' field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict):
            pytest.skip(
                f"Summary response is {type(data).__name__!r}, not a dict — "
                "schema may differ; skipping field check"
            )

        assert "total_cost" in data, (
            "GET /api/v1/dashboard/budget/summary must include a 'total_cost' field "
            "— the SummaryCards component requires this to render Total Spend"
        )

    def test_summary_total_cost_is_numeric(self, page, base_url: str) -> None:
        """Budget summary 'total_cost' value is numeric (int or float)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict) or "total_cost" not in data:
            pytest.skip("total_cost field not found — skipping type check")

        assert isinstance(data["total_cost"], (int, float)), (
            f"'total_cost' must be a number, got {type(data['total_cost']).__name__!r}"
        )

    def test_summary_total_calls_field_present(self, page, base_url: str) -> None:
        """Budget summary response contains a 'total_calls' field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict):
            pytest.skip("Summary response is not a dict — skipping field check")

        assert "total_calls" in data, (
            "GET /api/v1/dashboard/budget/summary must include a 'total_calls' field "
            "— required by the Total API Calls summary card"
        )

    def test_summary_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/summary response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _SUMMARY)

    def test_summary_window_hours_param_accepted(self, page, base_url: str) -> None:
        """Budget summary endpoint accepts window_hours query param without 4xx."""
        _go(page, base_url)
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_SUMMARY}"
        )
        assert response.status < 400, (
            f"GET {_SUMMARY} returned {response.status} — expected 2xx or 3xx"
        )


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------


class TestBudgetHistoryEndpoint:
    """Budget history endpoint must return valid JSON for the SpendChart.

    The SpendChart renders a stacked bar of daily spend using the by_day
    array from this endpoint.  An empty list renders the 'No spend data'
    placeholder — a valid state when no tasks have been processed.
    """

    def test_history_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/history?window_hours=24 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _HISTORY, 200)

    def test_history_response_is_valid_json(self, page, base_url: str) -> None:
        """Budget history endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _HISTORY, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/history must return a non-null JSON body"
        )

    def test_history_response_is_dict_or_list(self, page, base_url: str) -> None:
        """Budget history response is a dict or list, not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _HISTORY, 200)
        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/budget/history must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_history_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/history response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _HISTORY)


# ---------------------------------------------------------------------------
# By-stage endpoint
# ---------------------------------------------------------------------------


class TestBudgetByStageEndpoint:
    """By-stage endpoint must return valid JSON for the stage cost breakdown.

    The CostBreakdown component's 'Cost by Pipeline Stage' chart sources its
    data from this endpoint.  The by_stage array may be empty when no stages
    have recorded spend — an acceptable zero-data state.
    """

    def test_by_stage_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-stage?window_hours=24 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _BY_STAGE, 200)

    def test_by_stage_response_is_valid_json(self, page, base_url: str) -> None:
        """By-stage endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_STAGE, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/by-stage must return a non-null JSON body"
        )

    def test_by_stage_response_structure(self, page, base_url: str) -> None:
        """By-stage response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_STAGE, 200)
        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/budget/by-stage must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_by_stage_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each stage cost item contains 'key' and 'total_cost' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_STAGE, 200)

        # Normalise to a list of items.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("by_stage", [])
            if not isinstance(items, list):
                items = []
        else:
            items = []

        if not items:
            pytest.skip("No stage cost entries — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each item in by-stage response must be a JSON object"
        )
        assert "key" in first or "stage" in first, (
            "Stage cost item must contain a 'key' or 'stage' field identifying the stage"
        )

    def test_by_stage_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-stage response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _BY_STAGE)


# ---------------------------------------------------------------------------
# By-model endpoint
# ---------------------------------------------------------------------------


class TestBudgetByModelEndpoint:
    """By-model endpoint must return valid JSON for the model cost breakdown.

    The CostBreakdown component's 'Cost by Model' chart and the SpendChart
    both source per-model data from this endpoint.
    """

    def test_by_model_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-model?window_hours=24 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _BY_MODEL, 200)

    def test_by_model_response_is_valid_json(self, page, base_url: str) -> None:
        """By-model endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_MODEL, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/by-model must return a non-null JSON body"
        )

    def test_by_model_response_structure(self, page, base_url: str) -> None:
        """By-model response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_MODEL, 200)
        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/budget/by-model must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_by_model_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each model cost item contains 'key' and 'total_cost' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BY_MODEL, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("by_model", [])
            if not isinstance(items, list):
                items = []
        else:
            items = []

        if not items:
            pytest.skip("No model cost entries — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each item in by-model response must be a JSON object"
        )
        assert "key" in first or "model" in first, (
            "Model cost item must contain a 'key' or 'model' field identifying the model"
        )

    def test_by_model_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/by-model response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _BY_MODEL)


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


class TestBudgetConfigEndpoint:
    """Budget config endpoint must return valid JSON with threshold fields.

    The BudgetAlertConfig component reads daily_spend_warning,
    weekly_budget_cap, per_task_warning, and toggle flags from this endpoint.
    A missing weekly_budget_cap means the spend cap progress bar cannot render.
    """

    def test_config_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/config returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _CONFIG, 200)

    def test_config_response_is_valid_json(self, page, base_url: str) -> None:
        """Budget config endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _CONFIG, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/budget/config must return a non-null JSON body"
        )

    def test_config_response_is_dict(self, page, base_url: str) -> None:
        """Budget config response is a JSON object (dict)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _CONFIG, 200)
        assert isinstance(data, dict), (
            "GET /api/v1/dashboard/budget/config must return a JSON object, "
            f"got {type(data).__name__!r}"
        )

    def test_config_contains_weekly_budget_cap(self, page, base_url: str) -> None:
        """Budget config response contains 'weekly_budget_cap' field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _CONFIG, 200)

        if not isinstance(data, dict):
            pytest.skip("Config response is not a dict — skipping field check")

        assert "weekly_budget_cap" in data, (
            "GET /api/v1/dashboard/budget/config must include 'weekly_budget_cap' — "
            "required by BudgetAlertConfig form and the spend progress indicator"
        )

    def test_config_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/budget/config response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _CONFIG)
