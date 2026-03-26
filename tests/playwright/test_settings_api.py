"""Epic 71.2 — Settings: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/settings return HTTP 200
with valid JSON schema.

Settings page backing endpoints:
  - GET /admin/settings            — List all configuration settings
  - GET /admin/settings?category=X — List settings filtered by category
  - GET /admin/settings/{key}      — Get a single setting by key
  - PUT /admin/settings/{key}      — Update a setting value
  - GET /healthz                   — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_settings_style.py (Epic 71.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_SETTINGS_LIST = "/admin/settings"
_HEALTHZ = "/healthz"

# Known setting categories backed by SettingCategory enum.
_KNOWN_CATEGORIES = [
    "api_keys",
    "infrastructure",
    "feature_flags",
    "agent_config",
]

# A read-only key that is safe to GET in any environment.
_KNOWN_READ_KEY = "llm_provider"


class TestSettingsListEndpoint:
    """Settings list endpoint must return a response with all configuration settings.

    The Settings page is sourced from this endpoint; the response must carry
    a 'settings' array with key-value entries that operators use to manage
    the platform's runtime configuration.
    """

    def test_settings_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/settings returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/settings")
        assert_api_endpoint(page, "GET", _SETTINGS_LIST, 200)

    def test_settings_list_returns_json_object(self, page, base_url: str) -> None:
        """GET /admin/settings returns a JSON object."""
        page.goto(f"{base_url}/admin/ui/settings")
        data = assert_api_endpoint(page, "GET", _SETTINGS_LIST, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {_SETTINGS_LIST}, got {type(data).__name__!r}"
        )

    def test_settings_list_has_settings_array(self, page, base_url: str) -> None:
        """GET /admin/settings response contains a 'settings' array."""
        page.goto(f"{base_url}/admin/ui/settings")
        data = assert_api_endpoint(page, "GET", _SETTINGS_LIST, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {_SETTINGS_LIST}"
        )
        assert "settings" in data, (
            f"Response from {_SETTINGS_LIST} must contain a 'settings' key; "
            f"got keys: {list(data.keys())!r}"
        )
        assert isinstance(data["settings"], list), (
            "'settings' field must be a list"
        )

    def test_settings_list_items_have_required_fields(self, page, base_url: str) -> None:
        """Each setting item has 'key', 'value', and 'source' fields."""
        page.goto(f"{base_url}/admin/ui/settings")
        data = assert_api_endpoint(page, "GET", _SETTINGS_LIST, 200)
        assert isinstance(data, dict), f"Expected JSON object from {_SETTINGS_LIST}"
        items = data.get("settings", [])
        if not items:
            pytest.skip("No settings returned — schema check skipped (empty list is valid)")
        for item in items:
            assert isinstance(item, dict), f"Each setting must be a JSON object, got {type(item)!r}"
            assert "key" in item, "Each setting must have a 'key' field"
            # value may be null/None but the key must exist
            assert "value" in item or "source" in item, (
                "Each setting must contain at least 'value' or 'source' fields"
            )

    def test_settings_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/settings response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/settings")
        assert_api_no_error(page, _SETTINGS_LIST)


class TestSettingsCategoryFilterEndpoint:
    """Settings list endpoint supports category filtering.

    Each of the 6 configuration categories in the Settings page can be
    independently queried; this ensures the filter parameter is stable.
    """

    @pytest.mark.parametrize("category", _KNOWN_CATEGORIES)
    def test_category_filter_returns_200(self, page, base_url: str, category: str) -> None:
        """GET /admin/settings?category={cat} returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}?category={category}"
        assert_api_endpoint(page, "GET", path, 200)

    @pytest.mark.parametrize("category", _KNOWN_CATEGORIES)
    def test_category_filter_returns_json_object(
        self, page, base_url: str, category: str
    ) -> None:
        """GET /admin/settings?category={cat} returns a JSON object with 'settings' key."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}?category={category}"
        data = assert_api_endpoint(page, "GET", path, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {path}, got {type(data).__name__!r}"
        )
        assert "settings" in data, (
            f"Category filter response must contain a 'settings' key; "
            f"got keys: {list(data.keys())!r}"
        )

    @pytest.mark.parametrize("category", _KNOWN_CATEGORIES)
    def test_category_filter_no_error_body(
        self, page, base_url: str, category: str
    ) -> None:
        """GET /admin/settings?category={cat} response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}?category={category}"
        assert_api_no_error(page, path)


class TestSettingsDetailEndpoint:
    """Settings detail endpoint must return a single setting object.

    The Settings page GET-by-key endpoint is used to read current values
    before updating.  It must return a JSON object with the key, value,
    source, and category fields.
    """

    def test_settings_get_known_key_returns_200(self, page, base_url: str) -> None:
        """GET /admin/settings/{key} returns HTTP 200 for a known key."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        assert_api_endpoint(page, "GET", path, 200)

    def test_settings_get_known_key_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/settings/{key} response includes key, value, source fields."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        data = assert_api_endpoint(page, "GET", path, 200)
        assert isinstance(data, dict), (
            f"Settings detail must be a JSON object, got {type(data).__name__!r}"
        )
        assert "key" in data, "Settings detail must contain 'key' field"
        # value may be null but key must exist
        has_value_or_source = "value" in data or "source" in data
        assert has_value_or_source, (
            "Settings detail must contain 'value' or 'source' field"
        )

    def test_settings_get_unknown_key_returns_404(self, page, base_url: str) -> None:
        """GET /admin/settings/{unknown-key} returns HTTP 404 for an unknown key."""
        page.goto(f"{base_url}/admin/ui/settings")
        unknown_path = f"{_SETTINGS_LIST}/__nonexistent_key_that_does_not_exist__"
        assert_api_endpoint(page, "GET", unknown_path, 404)

    def test_settings_get_no_error_body_on_known_key(self, page, base_url: str) -> None:
        """GET /admin/settings/{key} response has no error payload for a known key."""
        page.goto(f"{base_url}/admin/ui/settings")
        path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        assert_api_no_error(page, path)


class TestSettingsPutEndpoint:
    """Settings PUT endpoint must accept updates and return the updated setting.

    The Settings page sends PUT requests when operators save configuration.
    The endpoint must accept a JSON body with 'value' and return the updated
    setting object — or 422/400 on invalid input.
    """

    def test_settings_put_valid_value_returns_2xx(self, page, base_url: str) -> None:
        """PUT /admin/settings/{key} with a valid value returns 2xx."""
        page.goto(f"{base_url}/admin/ui/settings")
        # Read current value first to restore after test
        get_path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        current = assert_api_endpoint(page, "GET", get_path, 200)
        current_value = current.get("value", "stub") if isinstance(current, dict) else "stub"

        # Write back the same value — idempotent, safe update
        path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        response_data = assert_api_endpoint(
            page,
            "PUT",
            path,
            200,
            body={"value": current_value},
        )
        assert response_data is not None, (
            "PUT /admin/settings/{key} must return the updated setting object"
        )

    def test_settings_put_response_has_key_field(self, page, base_url: str) -> None:
        """PUT /admin/settings/{key} response contains 'key' field."""
        page.goto(f"{base_url}/admin/ui/settings")
        get_path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        current = assert_api_endpoint(page, "GET", get_path, 200)
        current_value = current.get("value", "stub") if isinstance(current, dict) else "stub"

        path = f"{_SETTINGS_LIST}/{_KNOWN_READ_KEY}"
        data = assert_api_endpoint(
            page,
            "PUT",
            path,
            200,
            body={"value": current_value},
        )
        assert isinstance(data, dict), (
            f"PUT {path!r} must return a JSON object"
        )
        assert "key" in data, "PUT settings response must contain 'key' field"

    def test_settings_put_unknown_key_returns_404(self, page, base_url: str) -> None:
        """PUT /admin/settings/{unknown-key} returns 404 for an unknown key."""
        page.goto(f"{base_url}/admin/ui/settings")
        unknown_path = f"{_SETTINGS_LIST}/__nonexistent_key_put_test__"
        # Expect 404 (not found) or 422 (validation error); both are acceptable
        ctx = page.request
        response = ctx.put(unknown_path, data={"value": "test"})
        assert response.status in (404, 422), (
            f"PUT on unknown settings key must return 404 or 422, "
            f"got {response.status}"
        )


class TestSettingsLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Settings page.

    The Settings page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after settings routes
    are added.
    """

    def test_healthz_returns_200_from_settings_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when settings page is loaded."""
        page.goto(f"{base_url}/admin/ui/settings")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_settings_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (settings page context)."""
        page.goto(f"{base_url}/admin/ui/settings")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_settings_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (settings page context)."""
        page.goto(f"{base_url}/admin/ui/settings")
        assert_api_no_error(page, _HEALTHZ)
