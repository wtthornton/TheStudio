"""Story 76.13 — API Reference Tab: API Endpoint Verification.

Validates that the backing API endpoint for /dashboard/?tab=api returns
HTTP 200 with a valid OpenAPI JSON schema.

API reference backing endpoint:
  - GET /openapi.json  — The FastAPI-generated OpenAPI 3.x specification that
                         powers the embedded Scalar viewer.

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_api_style.py (Story 76.13).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_OPENAPI_JSON = "/openapi.json"


def _go(page: object, base_url: str) -> None:
    """Navigate to the API tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "api")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# /openapi.json — primary spec endpoint
# ---------------------------------------------------------------------------


class TestOpenApiJsonEndpoint:
    """GET /openapi.json must return HTTP 200 with a valid OpenAPI 3.x document.

    The Scalar viewer sources the spec from /openapi.json on the same origin.
    A non-200 response or invalid JSON means the API reference viewer will
    silently fail to render any endpoints.
    """

    def test_openapi_json_returns_200(self, page, base_url: str) -> None:
        """GET /openapi.json returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

    def test_openapi_json_is_valid_json(self, page, base_url: str) -> None:
        """GET /openapi.json returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)
        assert data is not None, (
            "GET /openapi.json must return a non-null JSON body"
        )

    def test_openapi_json_is_object(self, page, base_url: str) -> None:
        """GET /openapi.json response is a JSON object (not a list or string)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

        assert isinstance(data, dict), (
            f"GET /openapi.json must return a JSON object, "
            f"got {type(data).__name__!r}"
        )

    def test_openapi_json_has_openapi_version_field(self, page, base_url: str) -> None:
        """GET /openapi.json contains an 'openapi' version field (OpenAPI 3.x)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

        assert isinstance(data, dict), "Response must be a JSON object"
        assert "openapi" in data, (
            "GET /openapi.json must contain an 'openapi' version field "
            "(e.g. '3.0.0' or '3.1.0') — required by OpenAPI 3.x specification"
        )

    def test_openapi_version_is_3x(self, page, base_url: str) -> None:
        """The 'openapi' version field starts with '3.' (OpenAPI 3.x)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

        assert isinstance(data, dict), "Response must be a JSON object"
        version = data.get("openapi", "")
        assert str(version).startswith("3."), (
            f"GET /openapi.json 'openapi' field is {version!r} — "
            "expected a 3.x version string (e.g. '3.0.0' or '3.1.0')"
        )

    def test_openapi_json_has_info_block(self, page, base_url: str) -> None:
        """GET /openapi.json contains an 'info' block with 'title' and 'version'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

        assert isinstance(data, dict), "Response must be a JSON object"
        info = data.get("info")
        assert isinstance(info, dict), (
            "GET /openapi.json must contain an 'info' block — required by OpenAPI 3.x"
        )
        assert "title" in info, (
            "OpenAPI 'info' block must contain a 'title' field"
        )
        assert "version" in info, (
            "OpenAPI 'info' block must contain a 'version' field"
        )

    def test_openapi_json_has_paths_block(self, page, base_url: str) -> None:
        """GET /openapi.json contains a 'paths' block with at least one endpoint."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _OPENAPI_JSON, 200)

        assert isinstance(data, dict), "Response must be a JSON object"
        paths = data.get("paths")
        assert isinstance(paths, dict), (
            "GET /openapi.json must contain a 'paths' block — required by OpenAPI 3.x"
        )
        assert len(paths) > 0, (
            "GET /openapi.json 'paths' block must contain at least one endpoint"
        )

    def test_openapi_json_no_error_body(self, page, base_url: str) -> None:
        """GET /openapi.json response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _OPENAPI_JSON)

    def test_openapi_json_content_type_json(self, page, base_url: str) -> None:
        """GET /openapi.json response carries a JSON content-type header."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_OPENAPI_JSON}"
        )
        assert response.status == 200, (
            f"GET /openapi.json returned {response.status} — expected 200"
        )

        content_type = response.headers.get("content-type", "")
        assert "json" in content_type.lower(), (
            f"GET /openapi.json content-type {content_type!r} — "
            "expected 'application/json' or similar JSON content-type"
        )


# ---------------------------------------------------------------------------
# Dashboard tab route — returns 200 regardless of ?tab= param
# ---------------------------------------------------------------------------


class TestApiTabRoute:
    """The /dashboard/?tab=api route must return HTTP 200 (SPA catch-all).

    The dashboard is a React SPA — all tab routes resolve to the same HTML
    shell at /dashboard/.  A non-200 response would break the entire tab.
    """

    def test_api_tab_route_returns_200(self, page, base_url: str) -> None:
        """GET /dashboard/?tab=api returns HTTP 200 (SPA shell)."""
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}/dashboard/?tab=api"
        )
        assert response.status == 200, (
            f"GET /dashboard/?tab=api returned {response.status} — "
            "expected 200 (SPA catch-all must always return HTTP 200)"
        )

    def test_dashboard_route_returns_html(self, page, base_url: str) -> None:
        """GET /dashboard/?tab=api returns an HTML content-type."""
        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}/dashboard/?tab=api"
        )
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower(), (
            f"GET /dashboard/?tab=api returned content-type {content_type!r} — "
            "expected HTML (SPA shell delivery)"
        )
