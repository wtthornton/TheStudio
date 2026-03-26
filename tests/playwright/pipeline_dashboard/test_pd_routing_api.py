"""Story 76.5 — Routing Review Tab: API Endpoint Verification.

Validates that the backing API endpoint for /dashboard/?tab=routing responds
correctly to the test client.

Routing backing endpoint:
  - GET /api/v1/dashboard/planning/routing/{task_id}
      Returns routing data for a specific task.  A dummy task_id should yield
      404 (task not found) or valid JSON — never a 5xx.

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_routing_style.py (Story 76.5).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_no_error,
    assert_api_endpoint,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_ROUTING_DETAIL = "/api/v1/dashboard/planning/routing/{task_id}"
_DUMMY_TASK_ID = "00000000-0000-0000-0000-000000000001"


def _go(page: object, base_url: str) -> None:
    """Navigate to the routing tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "routing")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Routing detail endpoint
# ---------------------------------------------------------------------------


class TestRoutingDetailEndpoint:
    """The routing detail endpoint must respond without a server error.

    A 404 is acceptable (task does not exist in test data) but a 500 or
    connection error indicates a broken endpoint that would crash the UI.
    """

    def test_routing_endpoint_does_not_500(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/planning/routing/{task_id} does not return 5xx."""
        _go(page, base_url)

        url = _ROUTING_DETAIL.format(task_id=_DUMMY_TASK_ID)
        full_url = f"{base_url}{url}"

        response = page.request.get(full_url)  # type: ignore[attr-defined]
        assert response.status < 500, (
            f"GET {url} returned HTTP {response.status} — server errors (5xx) "
            "indicate a broken routing endpoint that would crash the UI"
        )

    def test_routing_endpoint_returns_json_or_404(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/planning/routing/{task_id} returns JSON or 404."""
        _go(page, base_url)

        url = _ROUTING_DETAIL.format(task_id=_DUMMY_TASK_ID)
        full_url = f"{base_url}{url}"

        response = page.request.get(full_url)  # type: ignore[attr-defined]
        status = response.status

        # 404 is expected for a non-existent task in test data.
        if status == 404:
            return  # Acceptable — endpoint exists, task does not

        # Any 2xx should return parseable JSON.
        assert status < 300, (
            f"GET {url} returned HTTP {status} — expected 2xx or 404"
        )
        try:
            body = response.json()
            assert body is not None, (
                f"GET {url} returned HTTP {status} but body is null"
            )
        except Exception as exc:
            pytest.fail(
                f"GET {url} returned HTTP {status} but body is not parseable JSON: {exc}"
            )

    def test_routing_endpoint_200_has_valid_schema(self, page, base_url: str) -> None:
        """When the routing endpoint returns 200, the body has expected routing fields."""
        _go(page, base_url)

        url = _ROUTING_DETAIL.format(task_id=_DUMMY_TASK_ID)
        full_url = f"{base_url}{url}"

        response = page.request.get(full_url)  # type: ignore[attr-defined]
        if response.status != 200:
            pytest.skip(
                f"GET {url} returned {response.status} — skipping schema check "
                "(404 is expected for dummy task_id in test data)"
            )

        try:
            data = response.json()
        except Exception:
            pytest.fail(f"GET {url} returned 200 but body is not valid JSON")

        assert isinstance(data, dict), (
            f"GET {url} must return a JSON object, got {type(data).__name__!r}"
        )
        # Routing payload should have at minimum an identifying field.
        has_id = "id" in data or "task_id" in data or "selections" in data
        assert has_id, (
            f"GET {url} response missing expected routing fields "
            f"('id', 'task_id', or 'selections'). Keys found: {list(data.keys())!r}"
        )

    def test_routing_endpoint_with_real_task_ids(self, page, base_url: str) -> None:
        """If any tasks exist, the routing endpoint responds for their IDs."""
        _go(page, base_url)

        # Fetch the tasks list to find real task IDs.
        tasks_response = page.request.get(f"{base_url}/api/v1/dashboard/tasks")  # type: ignore[attr-defined]
        if tasks_response.status != 200:
            pytest.skip("Cannot reach /api/v1/dashboard/tasks — skipping live task check")

        try:
            tasks_data = tasks_response.json()
        except Exception:
            pytest.skip("Tasks endpoint returned non-JSON — skipping live task check")

        # Normalise to a list.
        if isinstance(tasks_data, list):
            items = tasks_data
        elif isinstance(tasks_data, dict):
            items = next(
                (tasks_data[k] for k in ("tasks", "items", "data", "results")
                 if isinstance(tasks_data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No tasks returned — skipping live routing endpoint check")

        first_task = items[0]
        task_id = first_task.get("id") or first_task.get("task_id")
        if not task_id:
            pytest.skip("First task has no 'id' field — cannot check routing endpoint")

        url = _ROUTING_DETAIL.format(task_id=task_id)
        full_url = f"{base_url}{url}"

        response = page.request.get(full_url)  # type: ignore[attr-defined]
        assert response.status < 500, (
            f"GET {url} with real task_id={task_id!r} returned HTTP {response.status} "
            "— server error on a real task ID indicates a broken routing endpoint"
        )
