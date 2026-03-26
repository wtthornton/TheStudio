"""Epic 66.2 — Model Gateway: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/models return HTTP 200
with valid JSON schema.

Models page backing endpoints:
  - GET /admin/models          — List model providers with routing rules and cost info
  - GET /admin/models/{id}     — Model/provider detail with configuration
  - GET /healthz               — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_models_style.py (Epic 66.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_MODELS_LIST = "/admin/models"
_HEALTHZ = "/healthz"


class TestModelsListEndpoint:
    """Model list endpoint must return an array of model provider summaries.

    The Models page catalog is sourced from this endpoint; each item must carry
    the name, routing rules, and cost fields that operators rely on
    to manage model access and budget at a glance.
    """

    def test_models_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/models returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/models")
        assert_api_endpoint(page, "GET", _MODELS_LIST, 200)

    def test_models_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/models returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/models")
        data = assert_api_endpoint(page, "GET", _MODELS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_MODELS_LIST}, got {type(data).__name__!r}"
        )

    def test_models_list_items_have_model_id(self, page, base_url: str) -> None:
        """Each model summary has a 'model_id' or 'id' field."""
        page.goto(f"{base_url}/admin/ui/models")
        data = assert_api_endpoint(page, "GET", _MODELS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_MODELS_LIST}"
        if not data:
            pytest.skip("No models registered — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "model_id" in item or "id" in item
            assert has_id, (
                "Each model summary must contain a 'model_id' or 'id' field"
            )

    def test_models_list_items_have_name(self, page, base_url: str) -> None:
        """Each model summary has a 'name' or 'provider' field."""
        page.goto(f"{base_url}/admin/ui/models")
        data = assert_api_endpoint(page, "GET", _MODELS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_MODELS_LIST}"
        if not data:
            pytest.skip("No models registered — name check skipped")
        for item in data:
            has_name = "name" in item or "provider" in item
            assert has_name, (
                "Each model summary must contain a 'name' or 'provider' field"
            )
            name_val = item.get("name") or item.get("provider")
            assert isinstance(name_val, str), (
                f"name/provider must be a string, got {type(name_val).__name__!r}"
            )

    def test_models_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/models response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/models")
        assert_api_no_error(page, _MODELS_LIST)


class TestModelsDetailEndpoint:
    """Model detail endpoint must return routing config and cost info for a given model.

    The detail panel on the Models page uses this endpoint to show provider
    configuration, routing rules, and cost metadata for a selected model.
    When no models are registered this test class is skipped.
    """

    def _first_model_id(self, page, base_url: str) -> str | None:
        """Return the model_id/id of the first listed model, or None."""
        data = assert_api_endpoint(page, "GET", _MODELS_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("model_id") or item.get("id")

    def test_model_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/models/{id} returns HTTP 200 for a known model."""
        page.goto(f"{base_url}/admin/ui/models")
        model_id = self._first_model_id(page, base_url)
        if model_id is None:
            pytest.skip("No models registered — detail endpoint test skipped")

        detail_url = f"{_MODELS_LIST}/{model_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_model_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/models/{id} response includes name or provider field."""
        page.goto(f"{base_url}/admin/ui/models")
        model_id = self._first_model_id(page, base_url)
        if model_id is None:
            pytest.skip("No models registered — detail fields check skipped")

        detail_url = f"{_MODELS_LIST}/{model_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Model detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_name = "name" in data or "provider" in data
        assert has_name, "Model detail must contain 'name' or 'provider' field"

    def test_model_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/models/{unknown-id} returns HTTP 404 for an unknown model."""
        page.goto(f"{base_url}/admin/ui/models")
        unknown_url = f"{_MODELS_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_model_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/models/{id} response has no error payload for a known model."""
        page.goto(f"{base_url}/admin/ui/models")
        model_id = self._first_model_id(page, base_url)
        if model_id is None:
            pytest.skip("No models registered — error-body check skipped")

        detail_url = f"{_MODELS_LIST}/{model_id}"
        assert_api_no_error(page, detail_url)


class TestModelsLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Models page.

    The Models page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after model routes are added.
    """

    def test_healthz_returns_200_from_models_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when models page is loaded."""
        page.goto(f"{base_url}/admin/ui/models")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_models_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (models page context)."""
        page.goto(f"{base_url}/admin/ui/models")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_models_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (models page context)."""
        page.goto(f"{base_url}/admin/ui/models")
        assert_api_no_error(page, _HEALTHZ)
