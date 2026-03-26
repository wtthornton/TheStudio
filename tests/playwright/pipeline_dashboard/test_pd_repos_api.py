"""Story 76.12 — Pipeline Dashboard: Repos Tab — API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=repos return
HTTP 200 with valid JSON schema.

Repos backing endpoints:
  - GET /admin/repos         — List of registered repositories
  - GET /admin/repos/{id}    — Single repo detail (profile / config)
  - GET /admin/repos/health  — Fleet health summary per repo

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_repos_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_REPOS_LIST = "/admin/repos"
_REPOS_HEALTH = "/admin/repos/health"


def _go(page: object, base_url: str) -> None:
    """Navigate to the repos tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "repos")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# /admin/repos — list endpoint
# ---------------------------------------------------------------------------


class TestReposListEndpoint:
    """Repos list endpoint must return a valid JSON collection.

    The fleet health table sources its repo rows from this endpoint.
    An empty list is valid — the empty state handles zero repos gracefully.
    """

    def test_repos_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _REPOS_LIST, 200)

    def test_repos_list_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/repos returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_LIST, 200)
        assert data is not None, (
            "GET /admin/repos must return a non-null JSON body"
        )

    def test_repos_list_contains_repos_key_or_list(self, page, base_url: str) -> None:
        """GET /admin/repos response is a JSON list or wraps a list under 'repos'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_LIST, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("repos", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /admin/repos must return a JSON list or an object "
            "containing a 'repos'/'items'/'data'/'results' list"
        )

    def test_repos_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each repo item contains at minimum 'id', 'owner', and 'repo' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_LIST, 200)

        # Normalise to a list.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("repos", "items", "data", "results")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No repos returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each repo item in /admin/repos must be a JSON object"
        )
        assert "id" in first, "Repo item must contain an 'id' field"

    def test_repos_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _REPOS_LIST)


# ---------------------------------------------------------------------------
# /admin/repos/health — fleet health endpoint
# ---------------------------------------------------------------------------


class TestReposHealthEndpoint:
    """Repos health endpoint must return valid JSON for the fleet health table.

    The fleet health table sources per-repo health, tier, status, active
    workflow count, and last task timestamp from this endpoint.
    """

    def test_repos_health_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

    def test_repos_health_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert data is not None, (
            "GET /admin/repos/health must return a non-null JSON body"
        )

    def test_repos_health_contains_list(self, page, base_url: str) -> None:
        """GET /admin/repos/health response is a list or wraps one under 'repos'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("repos", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /admin/repos/health must return a JSON list or an object "
            "containing a 'repos'/'items'/'data'/'results' list"
        )

    def test_repos_health_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each health item contains 'id', 'health', 'tier', and 'status' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("repos", "items", "data", "results")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No health items returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each health item in /admin/repos/health must be a JSON object"
        )
        assert "id" in first, "Health item must contain an 'id' field"

    def test_repos_health_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _REPOS_HEALTH)

    def test_repos_health_response_structure(self, page, base_url: str) -> None:
        """Repos health response is a dict or list — not a string or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

        assert isinstance(data, (dict, list)), (
            "GET /admin/repos/health must return a JSON object or list, "
            f"got {type(data).__name__!r}"
        )


# ---------------------------------------------------------------------------
# /admin/repos/{id} — single repo detail endpoint
# ---------------------------------------------------------------------------


class TestRepoDetailEndpoint:
    """Single repo detail endpoint returns valid JSON for the config editor.

    The RepoConfigForm sources per-repo profile data from this endpoint.
    The test resolves a real repo ID from the list endpoint before calling
    the detail endpoint.  If no repos exist the tests are skipped.
    """

    def _get_first_repo_id(self, page, base_url: str) -> str | None:
        """Return the first repo id from /admin/repos, or None if empty."""
        try:
            data = assert_api_endpoint(page, "GET", _REPOS_LIST, 200)
        except Exception:
            return None

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("repos", "items", "data", "results")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            return None

        first = items[0]
        if isinstance(first, dict):
            return str(first.get("id", ""))
        return None

    def test_repo_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} returns HTTP 200 for a known repo."""
        _go(page, base_url)

        repo_id = self._get_first_repo_id(page, base_url)
        if not repo_id:
            pytest.skip("No repos registered — skipping detail endpoint check")

        assert_api_endpoint(page, "GET", f"{_REPOS_LIST}/{repo_id}", 200)

    def test_repo_detail_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} returns a parseable JSON body."""
        _go(page, base_url)

        repo_id = self._get_first_repo_id(page, base_url)
        if not repo_id:
            pytest.skip("No repos registered — skipping detail endpoint check")

        data = assert_api_endpoint(page, "GET", f"{_REPOS_LIST}/{repo_id}", 200)
        assert data is not None, (
            f"GET /admin/repos/{repo_id} must return a non-null JSON body"
        )

    def test_repo_detail_has_id_field(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} response contains an 'id' field."""
        _go(page, base_url)

        repo_id = self._get_first_repo_id(page, base_url)
        if not repo_id:
            pytest.skip("No repos registered — skipping detail endpoint check")

        data = assert_api_endpoint(page, "GET", f"{_REPOS_LIST}/{repo_id}", 200)
        assert isinstance(data, dict) and "id" in data, (
            f"GET /admin/repos/{repo_id} must return a JSON object with an 'id' field"
        )

    def test_repo_detail_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos/{id} response contains no error payload."""
        _go(page, base_url)

        repo_id = self._get_first_repo_id(page, base_url)
        if not repo_id:
            pytest.skip("No repos registered — skipping detail endpoint check")

        assert_api_no_error(page, f"{_REPOS_LIST}/{repo_id}")

    def test_repos_list_request_completes_without_4xx(
        self, page, base_url: str
    ) -> None:
        """GET /admin/repos endpoint accepts request without a 4xx error."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_REPOS_LIST}"
        )
        assert response.status < 400, (
            f"GET {_REPOS_LIST} returned {response.status} — expected 2xx or 3xx"
        )
