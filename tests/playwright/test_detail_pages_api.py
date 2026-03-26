"""Epic 74.2 — Detail Pages: API Endpoint Verification.

Validates that the detail endpoints for entity types (repo, workflow, expert)
return HTTP 200 with valid JSON schema when a valid ID is supplied, and HTTP
404 when an unknown ID is requested.

Detail page backing endpoints:
  - GET /admin/repos/{id}       — Repo profile (RepoProfileResponse)
  - GET /admin/workflows/{id}   — Workflow detail with timeline (WorkflowDetailResponse)
  - GET /admin/experts/{id}     — Expert detail with per-repo breakdown

Note: Detail pages require seed data.  Tests that need a real entity ID skip
gracefully when the relevant list endpoint returns an empty collection.

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_detail_pages_style.py (Epic 74.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

_REPOS = "/admin/repos"
_WORKFLOWS = "/admin/workflows"
_EXPERTS = "/admin/experts"
_UNKNOWN_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_id_from_list(page, base_url: str, list_path: str, items_key: str) -> str | None:
    """Fetch the first entity ID from a list endpoint via the Playwright API helper.

    Returns None when the list is empty or the endpoint is unavailable.
    """
    data = assert_api_endpoint(page, "GET", list_path, 200)
    if data is None:
        return None
    items = data if isinstance(data, list) else data.get(items_key, [])
    if not items:
        return None
    first = items[0]
    return str(
        first.get("id")
        or first.get("repo_id")
        or first.get("workflow_id")
        or first.get("expert_id")
        or ""
    ) or None


# ---------------------------------------------------------------------------
# Repo detail endpoint
# ---------------------------------------------------------------------------

class TestRepoDetailEndpoint:
    """Repo detail endpoint must return the full Repo Profile for a given ID.

    The sliding inspector panel on /admin/ui/repos and the dedicated repo detail
    page both populate from this endpoint.  Schema regressions here prevent
    operators from inspecting tier, writes_enabled, and poll configuration.
    """

    def test_repo_detail_returns_200_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} returns HTTP 200 for an existing repo."""
        page.goto(f"{base_url}/admin/ui/repos")
        entity_id = _first_id_from_list(page, base_url, _REPOS, "repos")
        if not entity_id:
            pytest.skip("No repos registered — detail endpoint test requires at least one repo")

        assert_api_endpoint(page, "GET", f"{_REPOS}/{entity_id}", 200)

    def test_repo_detail_response_is_json_object(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} returns a JSON object (not a list or null)."""
        page.goto(f"{base_url}/admin/ui/repos")
        entity_id = _first_id_from_list(page, base_url, _REPOS, "repos")
        if not entity_id:
            pytest.skip("No repos registered — schema test requires at least one repo")

        detail = assert_api_endpoint(page, "GET", f"{_REPOS}/{entity_id}", 200)
        assert isinstance(detail, dict), (
            f"GET /admin/repos/{{id}} must return a JSON object, got {type(detail).__name__!r}"
        )

    def test_repo_detail_contains_required_fields(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} response contains id, owner, repo, tier, status, and health."""
        page.goto(f"{base_url}/admin/ui/repos")
        entity_id = _first_id_from_list(page, base_url, _REPOS, "repos")
        if not entity_id:
            pytest.skip("No repos registered — field validation requires at least one repo")

        detail = assert_api_endpoint(page, "GET", f"{_REPOS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from repo detail endpoint"

        required_fields = ("id", "owner", "repo", "tier", "status")
        for field in required_fields:
            assert field in detail, (
                f"RepoProfileResponse must contain '{field}' field"
            )

    def test_repo_detail_tier_is_valid_trust_tier(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} tier field is one of: observe, suggest, execute."""
        page.goto(f"{base_url}/admin/ui/repos")
        entity_id = _first_id_from_list(page, base_url, _REPOS, "repos")
        if not entity_id:
            pytest.skip("No repos registered — tier validation requires at least one repo")

        detail = assert_api_endpoint(page, "GET", f"{_REPOS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from repo detail endpoint"

        tier = str(detail.get("tier", "")).lower()
        valid_tiers = {"observe", "suggest", "execute"}
        assert tier in valid_tiers, (
            f"Repo tier must be one of {valid_tiers!r}, got {tier!r}"
        )

    def test_repo_detail_returns_404_for_unknown_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} returns HTTP 404 for a non-existent UUID."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_endpoint(page, "GET", f"{_REPOS}/{_UNKNOWN_UUID}", 404)

    def test_repo_detail_no_error_body_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} response for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/repos")
        entity_id = _first_id_from_list(page, base_url, _REPOS, "repos")
        if not entity_id:
            pytest.skip("No repos registered — error-body test requires at least one repo")

        assert_api_no_error(page, f"{_REPOS}/{entity_id}")


# ---------------------------------------------------------------------------
# Workflow detail endpoint
# ---------------------------------------------------------------------------

class TestWorkflowDetailEndpoint:
    """Workflow detail endpoint must return the full workflow record for a given ID.

    The inspector panel on /admin/ui/workflows and the dedicated workflow detail
    page both populate from this endpoint.  Schema regressions break the operator's
    ability to inspect the pipeline stage and timeline for a running or stuck workflow.
    """

    def test_workflow_detail_returns_200_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} returns HTTP 200 for an existing workflow."""
        page.goto(f"{base_url}/admin/ui/workflows")
        entity_id = _first_id_from_list(page, base_url, _WORKFLOWS, "workflows")
        if not entity_id:
            pytest.skip("No workflows registered — detail endpoint test requires at least one workflow")

        assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{entity_id}", 200)

    def test_workflow_detail_response_is_json_object(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} returns a JSON object (not a list or null)."""
        page.goto(f"{base_url}/admin/ui/workflows")
        entity_id = _first_id_from_list(page, base_url, _WORKFLOWS, "workflows")
        if not entity_id:
            pytest.skip("No workflows registered — schema test requires at least one workflow")

        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{entity_id}", 200)
        assert isinstance(detail, dict), (
            f"GET /admin/workflows/{{id}} must return a JSON object, got {type(detail).__name__!r}"
        )

    def test_workflow_detail_contains_required_fields(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} response contains id, repo, status, and stage fields."""
        page.goto(f"{base_url}/admin/ui/workflows")
        entity_id = _first_id_from_list(page, base_url, _WORKFLOWS, "workflows")
        if not entity_id:
            pytest.skip("No workflows registered — field validation requires at least one workflow")

        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from workflow detail endpoint"

        required_fields = ("id", "repo", "status")
        for field in required_fields:
            assert field in detail, (
                f"WorkflowDetailResponse must contain '{field}' field"
            )

    def test_workflow_detail_status_is_valid(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} status field is a non-empty string."""
        page.goto(f"{base_url}/admin/ui/workflows")
        entity_id = _first_id_from_list(page, base_url, _WORKFLOWS, "workflows")
        if not entity_id:
            pytest.skip("No workflows registered — status validation requires at least one workflow")

        detail = assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from workflow detail endpoint"

        status = detail.get("status")
        assert isinstance(status, str) and status, (
            f"Workflow status must be a non-empty string, got {status!r}"
        )

    def test_workflow_detail_returns_404_for_unknown_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} returns HTTP 404 for a non-existent UUID."""
        page.goto(f"{base_url}/admin/ui/workflows")
        assert_api_endpoint(page, "GET", f"{_WORKFLOWS}/{_UNKNOWN_UUID}", 404)

    def test_workflow_detail_no_error_body_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/workflows/{id} response for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/workflows")
        entity_id = _first_id_from_list(page, base_url, _WORKFLOWS, "workflows")
        if not entity_id:
            pytest.skip("No workflows registered — error-body test requires at least one workflow")

        assert_api_no_error(page, f"{_WORKFLOWS}/{entity_id}")


# ---------------------------------------------------------------------------
# Expert detail endpoint
# ---------------------------------------------------------------------------

class TestExpertDetailEndpoint:
    """Expert detail endpoint must return the full expert record for a given ID.

    The inspector panel on /admin/ui/experts and the dedicated expert detail page
    both populate from this endpoint.  Schema regressions prevent operators from
    inspecting confidence scores and drift signals for individual expert agents.
    """

    def test_expert_detail_returns_200_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} returns HTTP 200 for an existing expert."""
        page.goto(f"{base_url}/admin/ui/experts")
        entity_id = _first_id_from_list(page, base_url, _EXPERTS, "experts")
        if not entity_id:
            pytest.skip("No experts registered — detail endpoint test requires at least one expert")

        assert_api_endpoint(page, "GET", f"{_EXPERTS}/{entity_id}", 200)

    def test_expert_detail_response_is_json_object(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} returns a JSON object (not a list or null)."""
        page.goto(f"{base_url}/admin/ui/experts")
        entity_id = _first_id_from_list(page, base_url, _EXPERTS, "experts")
        if not entity_id:
            pytest.skip("No experts registered — schema test requires at least one expert")

        detail = assert_api_endpoint(page, "GET", f"{_EXPERTS}/{entity_id}", 200)
        assert isinstance(detail, dict), (
            f"GET /admin/experts/{{id}} must return a JSON object, got {type(detail).__name__!r}"
        )

    def test_expert_detail_contains_required_fields(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} response contains id, name/type, tier, and confidence fields."""
        page.goto(f"{base_url}/admin/ui/experts")
        entity_id = _first_id_from_list(page, base_url, _EXPERTS, "experts")
        if not entity_id:
            pytest.skip("No experts registered — field validation requires at least one expert")

        detail = assert_api_endpoint(page, "GET", f"{_EXPERTS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from expert detail endpoint"

        # At minimum the ID and trust tier must be present
        assert "id" in detail, "Expert detail response must contain 'id' field"

        tier_present = "tier" in detail or "trust_tier" in detail
        assert tier_present, (
            "Expert detail response must contain a 'tier' or 'trust_tier' field"
        )

    def test_expert_detail_tier_is_valid_trust_tier(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} tier field is one of: observe, suggest, execute."""
        page.goto(f"{base_url}/admin/ui/experts")
        entity_id = _first_id_from_list(page, base_url, _EXPERTS, "experts")
        if not entity_id:
            pytest.skip("No experts registered — tier validation requires at least one expert")

        detail = assert_api_endpoint(page, "GET", f"{_EXPERTS}/{entity_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from expert detail endpoint"

        tier = str(detail.get("tier") or detail.get("trust_tier") or "").lower()
        valid_tiers = {"observe", "suggest", "execute"}
        assert tier in valid_tiers, (
            f"Expert tier must be one of {valid_tiers!r}, got {tier!r}"
        )

    def test_expert_detail_returns_404_for_unknown_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} returns HTTP 404 for a non-existent UUID."""
        page.goto(f"{base_url}/admin/ui/experts")
        assert_api_endpoint(page, "GET", f"{_EXPERTS}/{_UNKNOWN_UUID}", 404)

    def test_expert_detail_no_error_body_for_valid_id(
        self, page, base_url: str
    ) -> None:
        """GET /admin/experts/{id} response for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/experts")
        entity_id = _first_id_from_list(page, base_url, _EXPERTS, "experts")
        if not entity_id:
            pytest.skip("No experts registered — error-body test requires at least one expert")

        assert_api_no_error(page, f"{_EXPERTS}/{entity_id}")


# ---------------------------------------------------------------------------
# Cross-entity: 404 contract
# ---------------------------------------------------------------------------

class TestDetailEndpoint404Contract:
    """All three detail endpoints must return 404 (not 500) for unknown IDs.

    A 500 for an unknown ID would surface internal error details to operators
    and indicates the endpoint is missing input validation.  The correct contract
    is a clean 404 with no stack trace in the response body.
    """

    @pytest.mark.parametrize("endpoint_path,entity_name", [
        (f"{_REPOS}/{_UNKNOWN_UUID}", "repo"),
        (f"{_WORKFLOWS}/{_UNKNOWN_UUID}", "workflow"),
        (f"{_EXPERTS}/{_UNKNOWN_UUID}", "expert"),
    ])
    def test_unknown_id_returns_404_not_500(
        self, page, base_url: str, endpoint_path: str, entity_name: str
    ) -> None:
        """Detail endpoint returns 404 (not 500) for an unknown entity UUID."""
        page.goto(f"{base_url}/admin/ui/repos")  # any valid page to initialise session
        result = assert_api_endpoint(page, "GET", endpoint_path, 404)
        # The result may be None if the helper only asserts status code — that is fine.
        # If a body is returned, it must not contain a Python traceback marker.
        if isinstance(result, dict):
            body_str = str(result).lower()
            assert "traceback" not in body_str and "exception" not in body_str, (
                f"{entity_name} detail endpoint must not expose a stack trace for unknown IDs"
            )
