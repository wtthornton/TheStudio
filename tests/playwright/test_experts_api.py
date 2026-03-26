"""Epic 64.2 — Expert Performance: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/experts return HTTP 200
with valid JSON schema.

Experts page backing endpoints:
  - GET /admin/experts          — List experts with trust tier, confidence, drift
  - GET /admin/experts/{id}     — Expert detail with per-repo breakdown
  - GET /healthz                — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_experts_style.py (Epic 64.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_EXPERTS_LIST = "/admin/experts"
_HEALTHZ = "/healthz"


class TestExpertsListEndpoint:
    """Expert list endpoint must return an array of expert summaries.

    The Experts page table is sourced from this endpoint; each item must carry
    the trust-tier, confidence, and drift-signal fields that operators rely on
    to evaluate expert health at a glance.
    """

    def test_experts_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/experts returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/experts")
        assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)

    def test_experts_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/experts returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_EXPERTS_LIST}, got {type(data).__name__!r}"
        )

    def test_experts_list_items_have_expert_id(self, page, base_url: str) -> None:
        """Each expert summary has an 'expert_id' field."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_EXPERTS_LIST}"
        )
        if not data:
            pytest.skip("No experts registered — schema check skipped (empty list is valid)")
        for item in data:
            assert "expert_id" in item, (
                "Each expert summary must contain an 'expert_id' field"
            )
            assert isinstance(item["expert_id"], str), (
                f"expert_id must be a string, got {type(item['expert_id']).__name__!r}"
            )

    def test_experts_list_items_have_trust_tier(self, page, base_url: str) -> None:
        """Each expert summary has a 'trust_tier' field."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_EXPERTS_LIST}"
        )
        if not data:
            pytest.skip("No experts registered — trust_tier check skipped")
        for item in data:
            assert "trust_tier" in item, (
                "Each expert summary must contain a 'trust_tier' field"
            )
            assert item["trust_tier"] in ("shadow", "probation", "trusted"), (
                f"trust_tier must be shadow/probation/trusted, got {item['trust_tier']!r}"
            )

    def test_experts_list_items_have_confidence(self, page, base_url: str) -> None:
        """Each expert summary has a numeric 'confidence' field."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_EXPERTS_LIST}"
        )
        if not data:
            pytest.skip("No experts registered — confidence check skipped")
        for item in data:
            assert "confidence" in item, (
                "Each expert summary must contain a 'confidence' field"
            )
            assert isinstance(item["confidence"], (int, float)), (
                f"confidence must be numeric, got {type(item['confidence']).__name__!r}"
            )

    def test_experts_list_items_have_drift_signal(self, page, base_url: str) -> None:
        """Each expert summary has a 'drift_signal' field."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_EXPERTS_LIST}"
        )
        if not data:
            pytest.skip("No experts registered — drift_signal check skipped")
        for item in data:
            assert "drift_signal" in item, (
                "Each expert summary must contain a 'drift_signal' field"
            )

    def test_experts_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/experts response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/experts")
        assert_api_no_error(page, _EXPERTS_LIST)


class TestExpertsDetailEndpoint:
    """Expert detail endpoint must return per-repo breakdown for a given expert.

    The detail panel on the Experts page uses this endpoint to show weight
    history and per-repo consultation breakdown for a selected expert.
    When no experts are registered this test class is skipped.
    """

    def _first_expert_id(self, page, base_url: str) -> str | None:
        """Return the expert_id of the first listed expert, or None."""
        data = assert_api_endpoint(page, "GET", _EXPERTS_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("expert_id")

    def test_expert_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/experts/{id} returns HTTP 200 for a known expert."""
        page.goto(f"{base_url}/admin/ui/experts")
        expert_id = self._first_expert_id(page, base_url)
        if expert_id is None:
            pytest.skip("No experts registered — detail endpoint test skipped")

        detail_url = f"{_EXPERTS_LIST}/{expert_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_expert_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/experts/{id} response includes expert_id, trust_tier, confidence, weight."""
        page.goto(f"{base_url}/admin/ui/experts")
        expert_id = self._first_expert_id(page, base_url)
        if expert_id is None:
            pytest.skip("No experts registered — detail fields check skipped")

        detail_url = f"{_EXPERTS_LIST}/{expert_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Expert detail must be a JSON object, got {type(data).__name__!r}"
        )
        for field in ("expert_id", "trust_tier", "confidence", "weight", "drift_signal"):
            assert field in data, (
                f"Expert detail must contain '{field}' field"
            )

    def test_expert_detail_repos_is_array(self, page, base_url: str) -> None:
        """Expert detail response includes a 'repos' array for per-repo breakdown."""
        page.goto(f"{base_url}/admin/ui/experts")
        expert_id = self._first_expert_id(page, base_url)
        if expert_id is None:
            pytest.skip("No experts registered — repos array check skipped")

        detail_url = f"{_EXPERTS_LIST}/{expert_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Expert detail must be a JSON object"
        )
        assert "repos" in data, (
            "Expert detail must contain a 'repos' field for per-repo breakdown"
        )
        assert isinstance(data["repos"], list), (
            f"Expert detail 'repos' must be a JSON array, got {type(data['repos']).__name__!r}"
        )

    def test_expert_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/experts/{unknown-id} returns HTTP 404 for an unknown expert."""
        page.goto(f"{base_url}/admin/ui/experts")
        unknown_url = f"{_EXPERTS_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_expert_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/experts/{id} response has no error payload for a known expert."""
        page.goto(f"{base_url}/admin/ui/experts")
        expert_id = self._first_expert_id(page, base_url)
        if expert_id is None:
            pytest.skip("No experts registered — error-body check skipped")

        detail_url = f"{_EXPERTS_LIST}/{expert_id}"
        assert_api_no_error(page, detail_url)


class TestExpertsLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Experts page.

    The Experts page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after expert routes are added.
    """

    def test_healthz_returns_200_from_experts_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz returns HTTP 200 when experts page is loaded."""
        page.goto(f"{base_url}/admin/ui/experts")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_experts_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz JSON body contains 'status' field (experts page context)."""
        page.goto(f"{base_url}/admin/ui/experts")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_experts_page(
        self, page, base_url: str
    ) -> None:
        """GET /healthz response contains no error payload (experts page context)."""
        page.goto(f"{base_url}/admin/ui/experts")
        assert_api_no_error(page, _HEALTHZ)
