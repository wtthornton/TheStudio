"""Epic 65.2 — Tool Hub: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/tools return HTTP 200
with valid JSON schema.

Tools page backing endpoints:
  - GET /admin/tools          — List tools with approval status and profiles
  - GET /admin/tools/{id}     — Tool detail with approval history
  - GET /healthz              — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_tools_style.py (Epic 65.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_TOOLS_LIST = "/admin/tools"
_HEALTHZ = "/healthz"


class TestToolsListEndpoint:
    """Tool list endpoint must return an array of tool summaries.

    The Tools page catalog is sourced from this endpoint; each item must carry
    the name, approval status, and profile fields that operators rely on
    to manage tool access at a glance.
    """

    def test_tools_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/tools returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/tools")
        assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)

    def test_tools_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/tools returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/tools")
        data = assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_TOOLS_LIST}, got {type(data).__name__!r}"
        )

    def test_tools_list_items_have_tool_id(self, page, base_url: str) -> None:
        """Each tool summary has a 'tool_id' or 'id' field."""
        page.goto(f"{base_url}/admin/ui/tools")
        data = assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_TOOLS_LIST}"
        if not data:
            pytest.skip("No tools registered — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "tool_id" in item or "id" in item
            assert has_id, (
                "Each tool summary must contain a 'tool_id' or 'id' field"
            )

    def test_tools_list_items_have_approval_status(self, page, base_url: str) -> None:
        """Each tool summary has an 'approval_status' or 'status' field."""
        page.goto(f"{base_url}/admin/ui/tools")
        data = assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_TOOLS_LIST}"
        if not data:
            pytest.skip("No tools registered — approval_status check skipped")
        for item in data:
            has_status = "approval_status" in item or "status" in item
            assert has_status, (
                "Each tool summary must contain an 'approval_status' or 'status' field"
            )

    def test_tools_list_items_have_name(self, page, base_url: str) -> None:
        """Each tool summary has a 'name' field."""
        page.goto(f"{base_url}/admin/ui/tools")
        data = assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_TOOLS_LIST}"
        if not data:
            pytest.skip("No tools registered — name check skipped")
        for item in data:
            assert "name" in item, (
                "Each tool summary must contain a 'name' field"
            )
            assert isinstance(item["name"], str), (
                f"name must be a string, got {type(item['name']).__name__!r}"
            )

    def test_tools_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/tools response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/tools")
        assert_api_no_error(page, _TOOLS_LIST)


class TestToolsDetailEndpoint:
    """Tool detail endpoint must return approval history and profile for a given tool.

    The detail panel on the Tools page uses this endpoint to show approval
    history and capabilities for a selected tool.
    When no tools are registered this test class is skipped.
    """

    def _first_tool_id(self, page, base_url: str) -> str | None:
        """Return the tool_id/id of the first listed tool, or None."""
        data = assert_api_endpoint(page, "GET", _TOOLS_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("tool_id") or item.get("id")

    def test_tool_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/tools/{id} returns HTTP 200 for a known tool."""
        page.goto(f"{base_url}/admin/ui/tools")
        tool_id = self._first_tool_id(page, base_url)
        if tool_id is None:
            pytest.skip("No tools registered — detail endpoint test skipped")

        detail_url = f"{_TOOLS_LIST}/{tool_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_tool_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/tools/{id} response includes name, approval_status or status."""
        page.goto(f"{base_url}/admin/ui/tools")
        tool_id = self._first_tool_id(page, base_url)
        if tool_id is None:
            pytest.skip("No tools registered — detail fields check skipped")

        detail_url = f"{_TOOLS_LIST}/{tool_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Tool detail must be a JSON object, got {type(data).__name__!r}"
        )
        assert "name" in data, "Tool detail must contain 'name' field"
        has_status = "approval_status" in data or "status" in data
        assert has_status, "Tool detail must contain 'approval_status' or 'status' field"

    def test_tool_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/tools/{unknown-id} returns HTTP 404 for an unknown tool."""
        page.goto(f"{base_url}/admin/ui/tools")
        unknown_url = f"{_TOOLS_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_tool_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/tools/{id} response has no error payload for a known tool."""
        page.goto(f"{base_url}/admin/ui/tools")
        tool_id = self._first_tool_id(page, base_url)
        if tool_id is None:
            pytest.skip("No tools registered — error-body check skipped")

        detail_url = f"{_TOOLS_LIST}/{tool_id}"
        assert_api_no_error(page, detail_url)


class TestToolsLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Tools page.

    The Tools page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after tool routes are added.
    """

    def test_healthz_returns_200_from_tools_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when tools page is loaded."""
        page.goto(f"{base_url}/admin/ui/tools")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_tools_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (tools page context)."""
        page.goto(f"{base_url}/admin/ui/tools")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_tools_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (tools page context)."""
        page.goto(f"{base_url}/admin/ui/tools")
        assert_api_no_error(page, _HEALTHZ)
