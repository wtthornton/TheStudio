"""Epic 70.2 — Execution Planes: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/planes return HTTP 200
with valid JSON schema.

Planes page backing endpoints:
  - GET /admin/planes          — List execution planes with health and registration status
  - GET /admin/planes/{id}     — Plane detail with worker cluster info
  - GET /healthz               — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_planes_style.py (Epic 70.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_PLANES_LIST = "/admin/planes"
_HEALTHZ = "/healthz"


class TestPlanesListEndpoint:
    """Planes list endpoint must return an array of execution plane summaries.

    The Execution Planes page is sourced from this endpoint; each item must carry
    the plane identity, health status, and registration status fields that
    operators rely on to manage worker clusters at a glance.
    """

    def test_planes_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/planes returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/planes")
        assert_api_endpoint(page, "GET", _PLANES_LIST, 200)

    def test_planes_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/planes returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/planes")
        data = assert_api_endpoint(page, "GET", _PLANES_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_PLANES_LIST}, got {type(data).__name__!r}"
        )

    def test_planes_list_items_have_plane_id(self, page, base_url: str) -> None:
        """Each plane summary has a 'plane_id' or 'id' field."""
        page.goto(f"{base_url}/admin/ui/planes")
        data = assert_api_endpoint(page, "GET", _PLANES_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_PLANES_LIST}"
        if not data:
            pytest.skip("No execution planes registered — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "plane_id" in item or "id" in item
            assert has_id, (
                "Each plane summary must contain a 'plane_id' or 'id' field"
            )

    def test_planes_list_items_have_health_status(self, page, base_url: str) -> None:
        """Each plane summary has a 'health' or 'health_status' or 'status' field."""
        page.goto(f"{base_url}/admin/ui/planes")
        data = assert_api_endpoint(page, "GET", _PLANES_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_PLANES_LIST}"
        if not data:
            pytest.skip("No execution planes registered — health_status check skipped")
        for item in data:
            has_health = "health" in item or "health_status" in item or "status" in item
            assert has_health, (
                "Each plane summary must contain a 'health', 'health_status', or 'status' field"
            )

    def test_planes_list_items_have_name_or_label(self, page, base_url: str) -> None:
        """Each plane summary has a 'name' or 'label' or 'cluster_name' field."""
        page.goto(f"{base_url}/admin/ui/planes")
        data = assert_api_endpoint(page, "GET", _PLANES_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_PLANES_LIST}"
        if not data:
            pytest.skip("No execution planes registered — name check skipped")
        for item in data:
            has_name = "name" in item or "label" in item or "cluster_name" in item
            assert has_name, (
                "Each plane summary must contain a 'name', 'label', or 'cluster_name' field"
            )

    def test_planes_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/planes response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/planes")
        assert_api_no_error(page, _PLANES_LIST)


class TestPlanesDetailEndpoint:
    """Plane detail endpoint must return worker cluster info for a given plane.

    The detail panel on the Execution Planes page uses this endpoint to show
    health, registration status, and cluster configuration for a selected plane.
    When no planes are registered this test class is skipped.
    """

    def _first_plane_id(self, page, base_url: str) -> str | None:
        """Return the plane_id/id of the first listed plane, or None."""
        data = assert_api_endpoint(page, "GET", _PLANES_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("plane_id") or item.get("id")

    def test_plane_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/planes/{id} returns HTTP 200 for a known plane."""
        page.goto(f"{base_url}/admin/ui/planes")
        plane_id = self._first_plane_id(page, base_url)
        if plane_id is None:
            pytest.skip("No execution planes registered — detail endpoint test skipped")

        detail_url = f"{_PLANES_LIST}/{plane_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_plane_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/planes/{id} response includes identity and status fields."""
        page.goto(f"{base_url}/admin/ui/planes")
        plane_id = self._first_plane_id(page, base_url)
        if plane_id is None:
            pytest.skip("No execution planes registered — detail fields check skipped")

        detail_url = f"{_PLANES_LIST}/{plane_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Plane detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_id = "plane_id" in data or "id" in data
        assert has_id, "Plane detail must contain 'plane_id' or 'id' field"
        has_status = "health" in data or "health_status" in data or "status" in data
        assert has_status, "Plane detail must contain 'health', 'health_status', or 'status' field"

    def test_plane_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/planes/{unknown-id} returns HTTP 404 for an unknown plane."""
        page.goto(f"{base_url}/admin/ui/planes")
        unknown_url = f"{_PLANES_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_plane_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/planes/{id} response has no error payload for a known plane."""
        page.goto(f"{base_url}/admin/ui/planes")
        plane_id = self._first_plane_id(page, base_url)
        if plane_id is None:
            pytest.skip("No execution planes registered — error-body check skipped")

        detail_url = f"{_PLANES_LIST}/{plane_id}"
        assert_api_no_error(page, detail_url)


class TestPlanesLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Execution Planes page.

    The Planes page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after planes routes are added.
    """

    def test_healthz_returns_200_from_planes_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when planes page is loaded."""
        page.goto(f"{base_url}/admin/ui/planes")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_planes_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (planes page context)."""
        page.goto(f"{base_url}/admin/ui/planes")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_planes_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (planes page context)."""
        page.goto(f"{base_url}/admin/ui/planes")
        assert_api_no_error(page, _HEALTHZ)
