"""Epic 60.2 — Repo Management: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/repos return HTTP 200
with valid JSON schema.

Repo Management backing endpoints:
  - GET /admin/repos           — list all registered repositories (RepoListResponse)
  - GET /admin/repos/{id}      — repo detail / full profile (RepoProfileResponse)
  - GET /admin/repos/health    — per-repo health summary for fleet dashboard

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_repos_style.py (Epic 60.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)

pytestmark = pytest.mark.playwright

_REPOS = "/admin/repos"
_REPOS_HEALTH = "/admin/repos/health"


class TestRepoListEndpoint:
    """Repo list endpoint must return a valid JSON collection.

    The /admin/ui/repos page renders its table from this endpoint; any schema
    regression here breaks the operator's primary navigation surface.
    """

    def test_repos_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_endpoint(page, "GET", _REPOS, 200)

    def test_repos_list_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/repos returns a valid JSON body."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert data is not None, "GET /admin/repos must return a non-null JSON body"

    def test_repos_list_contains_repos_field(self, page, base_url: str) -> None:
        """GET /admin/repos response contains a 'repos' list field."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_returns_data(page, _REPOS, list_key="repos", allow_empty=True)

    def test_repos_list_contains_total_field(self, page, base_url: str) -> None:
        """GET /admin/repos response contains a numeric 'total' field."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        assert "total" in data, (
            "GET /admin/repos must contain a 'total' field"
        )
        assert isinstance(data["total"], int), (
            f"Field 'total' must be an integer, got {type(data['total']).__name__!r}"
        )

    def test_repos_list_total_matches_repos_length(self, page, base_url: str) -> None:
        """'total' field matches the length of the 'repos' list."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])
        total = data.get("total", -1)
        assert isinstance(repos, list), "'repos' field must be a list"
        assert total == len(repos), (
            f"'total' ({total}) must equal len(repos) ({len(repos)})"
        )

    def test_repos_list_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each item in the repos list contains id, owner, repo, tier, and status fields."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — empty list is acceptable for 60.2")

        first = repos[0]
        assert isinstance(first, dict), "Each item in repos list must be a JSON object"

        for field in ("id", "owner", "repo", "tier", "status"):
            assert field in first, (
                f"Repo list item must contain '{field}' field"
            )

    def test_repos_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_no_error(page, _REPOS)


class TestRepoDetailEndpoint:
    """Repo detail endpoint must return the full Repo Profile for a given ID.

    The sliding inspector panel on /admin/ui/repos populates from this endpoint.
    Without it the operator cannot inspect tier, writes_enabled, or poll settings.
    """

    def test_repo_detail_returns_200_when_repo_exists(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos/{id} returns HTTP 200 for a valid repo ID."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — detail endpoint test requires at least one repo")

        repo_id = repos[0]["id"]
        assert_api_endpoint(page, "GET", f"{_REPOS}/{repo_id}", 200)

    def test_repo_detail_schema_when_populated(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} response contains all RepoProfileResponse fields."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — detail schema test requires at least one repo")

        repo_id = repos[0]["id"]
        detail = assert_api_endpoint(page, "GET", f"{_REPOS}/{repo_id}", 200)

        assert isinstance(detail, dict), (
            f"GET /admin/repos/{{id}} must return a JSON object, got {type(detail)!r}"
        )

        expected_fields = (
            "id", "owner", "repo", "tier", "status",
            "installation_id", "default_branch", "writes_enabled", "health",
        )
        for field in expected_fields:
            assert field in detail, (
                f"RepoProfileResponse must contain '{field}' field"
            )

    def test_repo_detail_tier_is_valid(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} tier field is one of the expected trust tier values."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — tier validation requires at least one repo")

        repo_id = repos[0]["id"]
        detail = assert_api_endpoint(page, "GET", f"{_REPOS}/{repo_id}", 200)
        assert isinstance(detail, dict), "Expected JSON object from repo detail endpoint"

        tier = detail.get("tier")
        valid_tiers = {"observe", "suggest", "execute"}
        assert str(tier).lower() in valid_tiers, (
            f"Repo tier must be one of {valid_tiers!r}, got {tier!r}"
        )

    def test_repo_detail_returns_404_for_unknown_id(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} returns 404 for a non-existent UUID."""
        page.goto(f"{base_url}/admin/ui/repos")
        unknown_id = "00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", f"{_REPOS}/{unknown_id}", 404)

    def test_repo_detail_no_error_body_for_valid_id(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} response for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — error-body test requires at least one repo")

        repo_id = repos[0]["id"]
        assert_api_no_error(page, f"{_REPOS}/{repo_id}")


class TestRepoHealthEndpoint:
    """Repo health endpoint must return per-repo health summaries.

    The fleet dashboard Repo Activity table and the repos page both consume
    this endpoint to surface tier, status, and active workflow counts.
    """

    def test_repos_health_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

    def test_repos_health_contains_repos_field(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains a 'repos' list."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos/health"
        assert "repos" in data, "GET /admin/repos/health must contain a 'repos' field"
        assert isinstance(data["repos"], list), (
            "The 'repos' field in /admin/repos/health must be a list"
        )

    def test_repos_health_contains_total_field(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains a numeric 'total' field."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos/health"
        assert "total" in data, (
            "GET /admin/repos/health must contain a 'total' field"
        )
        assert isinstance(data["total"], int), (
            f"Field 'total' in /admin/repos/health must be an integer, "
            f"got {type(data['total']).__name__!r}"
        )

    def test_repos_health_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each repo health item contains tier, status, and health fields."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos/health"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — empty health list is acceptable for 60.2")

        first = repos[0]
        assert isinstance(first, dict), (
            "Each item in /admin/repos/health 'repos' must be a JSON object"
        )

        for field in ("tier", "status", "health"):
            assert field in first, (
                f"Repo health item must contain '{field}' field"
            )

    def test_repos_health_item_health_values_are_valid(
        self, page, base_url: str
    ) -> None:
        """Each repo health item's 'health' field is one of: ok, degraded, idle."""
        page.goto(f"{base_url}/admin/ui/repos")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/repos/health"
        repos = data.get("repos", [])

        if not repos:
            pytest.skip("No repos registered — health value validation requires at least one repo")

        valid_health_values = {"ok", "degraded", "idle"}
        for item in repos:
            health_val = str(item.get("health", "")).lower()
            assert health_val in valid_health_values, (
                f"Repo health value must be one of {valid_health_values!r}, "
                f"got {health_val!r}"
            )

    def test_repos_health_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/repos")
        assert_api_no_error(page, _REPOS_HEALTH)
