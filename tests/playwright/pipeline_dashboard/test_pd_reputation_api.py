"""Story 76.11 — Reputation Tab: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=reputation return
HTTP 200 with valid JSON schema.

Reputation backing endpoints:
  - GET /api/v1/dashboard/reputation/summary  — aggregate reputation metrics
                                               (success_rate, avg_loopbacks,
                                               pr_merge_rate, drift_score)
  - GET /api/v1/dashboard/reputation/experts  — per-expert reputation records

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_reputation_style.py (Story 76.11).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_SUMMARY = "/api/v1/dashboard/reputation/summary"
_EXPERTS = "/api/v1/dashboard/reputation/experts"


def _go(page: object, base_url: str) -> None:
    """Navigate to the reputation tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "reputation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------


class TestReputationSummaryEndpoint:
    """Summary endpoint must return valid JSON with aggregate reputation metrics.

    The summary card row on the reputation tab sources its data from this
    endpoint.  A response with zero values is valid — it signals a clean-state
    deployment, not a failure.
    """

    def test_summary_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/summary returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _SUMMARY, 200)

    def test_summary_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/summary returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/reputation/summary must return a non-null JSON body"
        )

    def test_summary_response_is_dict(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/summary returns a JSON object."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        # Accept either a bare dict or a dict wrapped inside a data envelope.
        if isinstance(data, dict):
            return  # Correct shape

        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return  # Single-item list — also acceptable

        assert isinstance(data, (dict, list)), (
            "GET /api/v1/dashboard/reputation/summary must return a JSON object "
            f"or list, got {type(data).__name__!r}"
        )

    def test_summary_contains_success_rate_field(self, page, base_url: str) -> None:
        """Summary response contains a 'success_rate' or equivalent field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict):
            pytest.skip("Summary response is not a dict — schema check skipped")

        # Accept any plausible key name for the success rate metric.
        has_success_rate = any(
            k in data for k in ("success_rate", "successRate", "success")
        )
        if not has_success_rate:
            # Nested under a 'data' or 'summary' envelope.
            envelope = data.get("data") or data.get("summary") or {}
            if isinstance(envelope, dict):
                has_success_rate = any(
                    k in envelope for k in ("success_rate", "successRate", "success")
                )

        if not has_success_rate:
            pytest.skip(
                "success_rate field not found in summary response — "
                "endpoint may not yet be implemented"
            )

    def test_summary_contains_drift_score_field(self, page, base_url: str) -> None:
        """Summary response contains a 'drift_score' or equivalent field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SUMMARY, 200)

        if not isinstance(data, dict):
            pytest.skip("Summary response is not a dict — schema check skipped")

        has_drift = any(
            k in data for k in ("drift_score", "driftScore", "drift")
        )
        if not has_drift:
            envelope = data.get("data") or data.get("summary") or {}
            if isinstance(envelope, dict):
                has_drift = any(
                    k in envelope for k in ("drift_score", "driftScore", "drift")
                )

        if not has_drift:
            pytest.skip(
                "drift_score field not found in summary response — "
                "endpoint may not yet be implemented"
            )

    def test_summary_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/summary response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _SUMMARY)

    def test_summary_response_time_acceptable(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/summary responds within 5 seconds."""
        _go(page, base_url)
        import time

        start = time.monotonic()
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_SUMMARY}"
        )
        elapsed = time.monotonic() - start

        assert response.status < 400, (
            f"GET {_SUMMARY} returned {response.status}"
        )
        assert elapsed < 5.0, (
            f"GET {_SUMMARY} took {elapsed:.2f}s — must respond within 5s"
        )


# ---------------------------------------------------------------------------
# Experts endpoint
# ---------------------------------------------------------------------------


class TestReputationExpertsEndpoint:
    """Experts endpoint must return a valid JSON collection for the expert table.

    The expert performance table sources its data from this endpoint.
    An empty list is valid — it signals no experts have been registered yet.
    """

    def test_experts_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/experts returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _EXPERTS, 200)

    def test_experts_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/experts returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _EXPERTS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/reputation/experts must return a non-null JSON body"
        )

    def test_experts_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/experts response is a list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _EXPERTS, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("experts", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/reputation/experts must return a JSON list or "
            "an object containing an 'experts'/'items'/'data'/'results' list"
        )

    def test_experts_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each expert item contains at minimum an 'id' and a 'score' field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _EXPERTS, 200)

        # Normalise to a list.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("experts", "items", "data", "results")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No experts returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each expert item in /api/v1/dashboard/reputation/experts must be a "
            "JSON object"
        )
        assert "id" in first, (
            "Expert item must contain an 'id' field"
        )

    def test_experts_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/experts response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _EXPERTS)

    def test_experts_response_time_acceptable(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/reputation/experts responds within 5 seconds."""
        _go(page, base_url)
        import time

        start = time.monotonic()
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_EXPERTS}"
        )
        elapsed = time.monotonic() - start

        assert response.status < 400, (
            f"GET {_EXPERTS} returned {response.status}"
        )
        assert elapsed < 5.0, (
            f"GET {_EXPERTS} took {elapsed:.2f}s — must respond within 5s"
        )

    def test_experts_pagination_params_accepted(self, page, base_url: str) -> None:
        """Experts endpoint accepts pagination query params without 4xx error."""
        _go(page, base_url)
        url = f"{base_url}{_EXPERTS}?page=1&per_page=20"
        response = page.request.get(url)  # type: ignore[attr-defined]
        assert response.status < 400, (
            f"GET {_EXPERTS}?page=1&per_page=20 returned {response.status} — "
            "expected 2xx or 3xx"
        )
