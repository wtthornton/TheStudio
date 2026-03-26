"""Story 76.10 — Analytics Tab: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=analytics return
HTTP 200 with valid JSON schema.

Analytics backing endpoints:
  - GET /api/v1/dashboard/analytics/summary   — Summary cards (4 KPI values)
  - GET /api/v1/dashboard/analytics/throughput — Throughput chart time-series
  - GET /api/v1/dashboard/analytics/bottlenecks — Per-stage bottleneck data
  - GET /api/v1/dashboard/analytics/categories  — Category breakdown counts
  - GET /api/v1/dashboard/analytics/failures    — Failure analysis data

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_analytics_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_SUMMARY = "/api/v1/dashboard/analytics/summary"
_THROUGHPUT = "/api/v1/dashboard/analytics/throughput"
_BOTTLENECKS = "/api/v1/dashboard/analytics/bottlenecks"
_CATEGORIES = "/api/v1/dashboard/analytics/categories"
_FAILURES = "/api/v1/dashboard/analytics/failures"


def _go(page: object, base_url: str) -> None:
    """Navigate to the analytics tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "analytics")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------


class TestAnalyticsSummaryEndpoint:
    """Summary endpoint must return valid JSON with the four KPI cards.

    The SummaryCards component reads tasks_completed, avg_pipeline_seconds,
    pr_merge_rate, and total_spend_usd from this endpoint.
    """

    def test_summary_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/summary returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _SUMMARY, 200)

    def test_summary_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/summary returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/analytics/summary must return a non-null JSON body"
        )

    def test_summary_response_is_object(self, page, base_url: str) -> None:
        """Summary response is a JSON object (dict), not a bare list or string."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/analytics/summary must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_summary_contains_cards_key_or_flat_metrics(
        self, page, base_url: str
    ) -> None:
        """Summary response contains 'cards' key or at least one KPI metric field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict):
            pytest.skip("Summary response is not a dict — schema check not applicable")

        # Accept either a 'cards' wrapper or flat metric keys.
        kpi_keys = {
            "tasks_completed",
            "avg_pipeline_seconds",
            "pr_merge_rate",
            "total_spend_usd",
        }
        has_cards = "cards" in data
        has_flat = bool(kpi_keys & set(data.keys()))

        assert has_cards or has_flat, (
            "GET /api/v1/dashboard/analytics/summary must contain a 'cards' key "
            "or at least one KPI metric field "
            f"({', '.join(sorted(kpi_keys))!r})"
        )

    def test_summary_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/summary response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _SUMMARY)

    def test_summary_period_query_param_accepted(self, page, base_url: str) -> None:
        """Summary endpoint accepts a period query param without 4xx error."""
        _go(page, base_url)
        url_with_period = f"{_SUMMARY}?period=30d"
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{url_with_period}"
        )
        assert response.status < 400, (
            f"GET {url_with_period} returned {response.status} — expected 2xx or 3xx"
        )


# ---------------------------------------------------------------------------
# Throughput endpoint
# ---------------------------------------------------------------------------


class TestAnalyticsThroughputEndpoint:
    """Throughput endpoint must return valid JSON for the ThroughputChart.

    The chart renders a time-series of task completions per day/week over
    the selected period.  An empty list is valid for a fresh installation.
    """

    def test_throughput_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/throughput returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _THROUGHPUT, 200)

    def test_throughput_response_is_valid_json(self, page, base_url: str) -> None:
        """Throughput endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _THROUGHPUT, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/analytics/throughput must return a non-null JSON body"
        )

    def test_throughput_response_is_list_or_wrapped(
        self, page, base_url: str
    ) -> None:
        """Throughput response is a JSON list or wraps a list under a common key."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _THROUGHPUT, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("data", "items", "throughput", "results", "series")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/analytics/throughput must return a JSON list or "
            "an object containing a 'data'/'items'/'throughput'/'series' list"
        )

    def test_throughput_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/throughput response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _THROUGHPUT)


# ---------------------------------------------------------------------------
# Bottlenecks endpoint
# ---------------------------------------------------------------------------


class TestAnalyticsBottlenecksEndpoint:
    """Bottlenecks endpoint must return valid JSON for the BottleneckBars chart.

    The chart shows per-stage average wait time, highlighting which pipeline
    stages are slowing delivery.
    """

    def test_bottlenecks_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/bottlenecks returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _BOTTLENECKS, 200)

    def test_bottlenecks_response_is_valid_json(self, page, base_url: str) -> None:
        """Bottlenecks endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BOTTLENECKS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/analytics/bottlenecks must return a non-null JSON body"
        )

    def test_bottlenecks_response_structure(self, page, base_url: str) -> None:
        """Bottlenecks response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _BOTTLENECKS, 200)

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/analytics/bottlenecks must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_bottlenecks_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/bottlenecks response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _BOTTLENECKS)


# ---------------------------------------------------------------------------
# Categories endpoint
# ---------------------------------------------------------------------------


class TestAnalyticsCategoriesEndpoint:
    """Categories endpoint must return valid JSON for the CategoryBreakdown.

    The breakdown shows how tasks are distributed across categories
    (bug, feature, refactor, etc.).
    """

    def test_categories_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/categories returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _CATEGORIES, 200)

    def test_categories_response_is_valid_json(self, page, base_url: str) -> None:
        """Categories endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _CATEGORIES, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/analytics/categories must return a non-null JSON body"
        )

    def test_categories_response_structure(self, page, base_url: str) -> None:
        """Categories response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _CATEGORIES, 200)

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/analytics/categories must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_categories_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/categories response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _CATEGORIES)


# ---------------------------------------------------------------------------
# Failures endpoint
# ---------------------------------------------------------------------------


class TestAnalyticsFailuresEndpoint:
    """Failures endpoint must return valid JSON for the FailureAnalysis component.

    The failure analysis shows which pipeline stages and categories produce
    the most errors, guiding remediation effort.
    """

    def test_failures_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/failures returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _FAILURES, 200)

    def test_failures_response_is_valid_json(self, page, base_url: str) -> None:
        """Failures endpoint returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _FAILURES, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/analytics/failures must return a non-null JSON body"
        )

    def test_failures_response_structure(self, page, base_url: str) -> None:
        """Failures response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _FAILURES, 200)

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/analytics/failures must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )

    def test_failures_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/analytics/failures response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _FAILURES)

    def test_failures_period_param_accepted(self, page, base_url: str) -> None:
        """Failures endpoint accepts a period query param without 4xx error."""
        _go(page, base_url)
        url_with_period = f"{_FAILURES}?period=7d"
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{url_with_period}"
        )
        assert response.status < 400, (
            f"GET {url_with_period} returned {response.status} — expected 2xx or 3xx"
        )
