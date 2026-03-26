"""Epic 67.2 — Compliance Scorecard: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/compliance return HTTP 200
with valid JSON schema.

Compliance page backing endpoints:
  - GET /admin/compliance          — List per-repo compliance status with check results
  - GET /admin/compliance/{id}     — Compliance detail for a specific repo
  - GET /healthz                   — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_compliance_style.py (Epic 67.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_COMPLIANCE_LIST = "/admin/compliance"
_HEALTHZ = "/healthz"


class TestComplianceListEndpoint:
    """Compliance list endpoint must return an array of per-repo compliance summaries.

    The Compliance Scorecard page is sourced from this endpoint; each item must carry
    the repo identifier, compliance status, and check result fields that operators
    rely on to detect policy violations and remediate issues.
    """

    def test_compliance_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/compliance returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/compliance")
        assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)

    def test_compliance_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/compliance returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/compliance")
        data = assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_COMPLIANCE_LIST}, got {type(data).__name__!r}"
        )

    def test_compliance_list_items_have_repo_id(self, page, base_url: str) -> None:
        """Each compliance summary has a 'repo_id' or 'id' field."""
        page.goto(f"{base_url}/admin/ui/compliance")
        data = assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_COMPLIANCE_LIST}"
        if not data:
            pytest.skip("No compliance data — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "repo_id" in item or "id" in item
            assert has_id, (
                "Each compliance summary must contain a 'repo_id' or 'id' field"
            )

    def test_compliance_list_items_have_status(self, page, base_url: str) -> None:
        """Each compliance summary has a 'status' or 'compliance_status' field."""
        page.goto(f"{base_url}/admin/ui/compliance")
        data = assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_COMPLIANCE_LIST}"
        if not data:
            pytest.skip("No compliance data — status check skipped")
        for item in data:
            has_status = "status" in item or "compliance_status" in item
            assert has_status, (
                "Each compliance summary must contain a 'status' or 'compliance_status' field"
            )

    def test_compliance_list_items_have_repo_name(self, page, base_url: str) -> None:
        """Each compliance summary has a 'name', 'repo_name', or 'full_name' field."""
        page.goto(f"{base_url}/admin/ui/compliance")
        data = assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_COMPLIANCE_LIST}"
        if not data:
            pytest.skip("No compliance data — repo name check skipped")
        for item in data:
            has_name = "name" in item or "repo_name" in item or "full_name" in item
            assert has_name, (
                "Each compliance summary must contain a 'name', 'repo_name', or 'full_name' field"
            )

    def test_compliance_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/compliance response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/compliance")
        assert_api_no_error(page, _COMPLIANCE_LIST)


class TestComplianceDetailEndpoint:
    """Compliance detail endpoint must return check results for a given repo.

    The detail panel on the Compliance Scorecard page uses this endpoint to show
    individual check names, their pass/fail/warning outcomes, and remediation hints
    for a selected repo. When no compliance data is registered this test class is skipped.
    """

    def _first_repo_id(self, page, base_url: str) -> str | None:
        """Return the repo_id/id of the first listed compliance entry, or None."""
        data = assert_api_endpoint(page, "GET", _COMPLIANCE_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("repo_id") or item.get("id")

    def test_compliance_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/compliance/{id} returns HTTP 200 for a known repo."""
        page.goto(f"{base_url}/admin/ui/compliance")
        repo_id = self._first_repo_id(page, base_url)
        if repo_id is None:
            pytest.skip("No compliance data — detail endpoint test skipped")

        detail_url = f"{_COMPLIANCE_LIST}/{repo_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_compliance_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/compliance/{id} response includes status and checks fields."""
        page.goto(f"{base_url}/admin/ui/compliance")
        repo_id = self._first_repo_id(page, base_url)
        if repo_id is None:
            pytest.skip("No compliance data — detail fields check skipped")

        detail_url = f"{_COMPLIANCE_LIST}/{repo_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Compliance detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_status = "status" in data or "compliance_status" in data
        assert has_status, "Compliance detail must contain 'status' or 'compliance_status' field"

    def test_compliance_detail_has_checks_field(self, page, base_url: str) -> None:
        """GET /admin/compliance/{id} response includes 'checks' or 'results' field."""
        page.goto(f"{base_url}/admin/ui/compliance")
        repo_id = self._first_repo_id(page, base_url)
        if repo_id is None:
            pytest.skip("No compliance data — checks field check skipped")

        detail_url = f"{_COMPLIANCE_LIST}/{repo_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Compliance detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_checks = "checks" in data or "results" in data or "check_results" in data
        assert has_checks, (
            "Compliance detail must contain a 'checks', 'results', or 'check_results' field"
        )

    def test_compliance_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/compliance/{unknown-id} returns HTTP 404 for an unknown repo."""
        page.goto(f"{base_url}/admin/ui/compliance")
        unknown_url = f"{_COMPLIANCE_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_compliance_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/compliance/{id} response has no error payload for a known repo."""
        page.goto(f"{base_url}/admin/ui/compliance")
        repo_id = self._first_repo_id(page, base_url)
        if repo_id is None:
            pytest.skip("No compliance data — error-body check skipped")

        detail_url = f"{_COMPLIANCE_LIST}/{repo_id}"
        assert_api_no_error(page, detail_url)


class TestComplianceLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Compliance page.

    The Compliance Scorecard page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after compliance routes are added.
    """

    def test_healthz_returns_200_from_compliance_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when compliance page is loaded."""
        page.goto(f"{base_url}/admin/ui/compliance")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_compliance_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (compliance page context)."""
        page.goto(f"{base_url}/admin/ui/compliance")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_compliance_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (compliance page context)."""
        page.goto(f"{base_url}/admin/ui/compliance")
        assert_api_no_error(page, _HEALTHZ)
