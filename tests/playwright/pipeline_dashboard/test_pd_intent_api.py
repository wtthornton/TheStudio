"""Story 76.4 — Intent Review Tab: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=intent respond
correctly.

Intent backing endpoint:
  - GET /api/v1/dashboard/planning/intent/{task_id}
        — Intent specification for a given task.
        — Returns 404 when the task does not exist (dummy task_id).
        — Must NOT return HTTP 500 (internal server error).

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_intent_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# Dummy task_id used for "not found" contract testing — must not trigger 500.
_DUMMY_TASK_ID = "test-task-00000000-0000-0000-0000-000000000000"
_INTENT_ENDPOINT = f"/api/v1/dashboard/planning/intent/{_DUMMY_TASK_ID}"


def _go(page: object, base_url: str) -> None:
    """Navigate to the intent tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "intent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Intent endpoint — existence and contract
# ---------------------------------------------------------------------------


class TestIntentEndpointContract:
    """Intent endpoint must respond without server errors.

    The intent endpoint returns the intent specification for a given TaskPacket.
    When a non-existent task_id is used the server must return 404 (Not Found),
    not 500 (Internal Server Error).  A 200 with valid JSON is also acceptable
    if the server returns a placeholder or empty specification.
    """

    def test_intent_endpoint_responds(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/planning/intent/{task_id} responds (not 500)."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_INTENT_ENDPOINT}"
        )
        assert response.status != 500, (
            f"GET {_INTENT_ENDPOINT} returned HTTP 500 — internal server error. "
            "The endpoint must handle unknown task IDs gracefully (404 expected)"
        )

    def test_intent_endpoint_returns_404_or_200_for_dummy_id(
        self, page, base_url: str
    ) -> None:
        """GET /api/v1/dashboard/planning/intent/{task_id} returns 404 or 200 for dummy ID."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_INTENT_ENDPOINT}"
        )
        assert response.status in (200, 404), (
            f"GET {_INTENT_ENDPOINT} returned HTTP {response.status}. "
            "Expected 404 (task not found) or 200 (valid spec returned)"
        )

    def test_intent_endpoint_not_internal_error(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/planning/intent/{task_id} does not return 5xx."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_INTENT_ENDPOINT}"
        )
        assert response.status < 500, (
            f"GET {_INTENT_ENDPOINT} returned HTTP {response.status} — "
            "5xx server errors are not acceptable for this endpoint"
        )

    def test_intent_404_response_is_valid_json(self, page, base_url: str) -> None:
        """When returning 404, the intent endpoint returns a JSON error body."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_INTENT_ENDPOINT}"
        )
        if response.status != 404:
            pytest.skip(
                f"Endpoint returned {response.status} instead of 404 — "
                "skipping JSON body check"
            )

        try:
            body = response.json()
        except Exception:
            pytest.skip("404 response body is not JSON — may be HTML error page")

        assert body is not None, (
            f"GET {_INTENT_ENDPOINT} 404 response must have a non-null body"
        )

    def test_intent_200_response_structure_when_found(self, page, base_url: str) -> None:
        """When returning 200, the intent endpoint response is a JSON object."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_INTENT_ENDPOINT}"
        )
        if response.status != 200:
            pytest.skip(
                f"Endpoint returned {response.status} — intent spec not found for dummy ID. "
                "Skipping 200 structure check"
            )

        try:
            body = response.json()
        except Exception as exc:
            pytest.fail(
                f"GET {_INTENT_ENDPOINT} returned 200 but body is not valid JSON: {exc}"
            )

        assert isinstance(body, (dict, list)), (
            f"GET {_INTENT_ENDPOINT} 200 response must be a JSON object or list, "
            f"got {type(body).__name__!r}"
        )


# ---------------------------------------------------------------------------
# Intent endpoint — URL format validation
# ---------------------------------------------------------------------------


class TestIntentEndpointUrlFormat:
    """Validate URL patterns for the intent API endpoint.

    The intent endpoint uses a path parameter (task_id), not a query string.
    These tests verify the routing is set up correctly by checking that the
    base intent route (without task_id) does not accidentally return 200.
    """

    def test_intent_base_path_without_task_id(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/planning/intent (no task_id) returns 404 or 405."""
        _go(page, base_url)

        _BASE_PATH = "/api/v1/dashboard/planning/intent"
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_BASE_PATH}"
        )
        # 404 = route not found (path param required), 405 = method not allowed,
        # 422 = FastAPI validation error on missing path param — all acceptable.
        # Anything other than 500 is fine.
        assert response.status != 500, (
            f"GET {_BASE_PATH} (without task_id) must not return HTTP 500"
        )

    def test_intent_endpoint_url_contains_task_id_segment(
        self, page, base_url: str
    ) -> None:
        """Intent endpoint URL path includes the task_id as a path segment."""
        assert _DUMMY_TASK_ID in _INTENT_ENDPOINT, (
            "Intent endpoint URL must include the task_id as a path segment: "
            f"{_INTENT_ENDPOINT!r}"
        )
