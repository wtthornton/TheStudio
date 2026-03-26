"""Epic 73.2 — Portfolio Health: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/portfolio-health return HTTP 200
with valid response schema.

Portfolio Health page backing endpoints:
  - GET /admin/ui/partials/portfolio-health  — HTMX partial delivering review data HTML
  - GET /admin/repos/health                  — Per-repo health summary (JSON)
  - GET /healthz                             — Liveness probe (shared health gate)

The portfolio health page renders Meridian periodic review data server-side via an
HTMX partial rather than a client-side JSON fetch.  The tests below verify both the
HTMX partial (200, non-empty HTML) and the underlying repo-health JSON endpoint that
surfaces the per-repository health signals the page depends on.

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_portfolio_health_style.py (Epic 73.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_PORTFOLIO_PARTIAL = "/admin/ui/partials/portfolio-health"
_REPOS_HEALTH = "/admin/repos/health"
_HEALTHZ = "/healthz"

_PORTFOLIO_HEALTH_PAGE = "/admin/ui/portfolio-health"


class TestPortfolioHealthPartialEndpoint:
    """HTMX partial endpoint must return the portfolio review HTML with no errors.

    The Portfolio Health page bootstraps with an empty shell and fires an HTMX
    ``hx-trigger="load"`` request to this partial.  The partial queries the
    ``portfolio_reviews`` table and renders the latest Meridian review data.
    A 200 status with non-empty body is the minimum contract for the UI to load.
    """

    def test_portfolio_partial_returns_200(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/portfolio-health returns HTTP 200."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_endpoint(page, "GET", _PORTFOLIO_PARTIAL, 200)

    def test_portfolio_partial_returns_non_empty_body(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/portfolio-health returns a non-empty response body."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        ctx = page.request
        response = ctx.get(_PORTFOLIO_PARTIAL)
        assert response.status == 200, (
            f"Expected 200 from {_PORTFOLIO_PARTIAL}, got {response.status}"
        )
        body = response.text()
        assert body, f"Portfolio health partial at {_PORTFOLIO_PARTIAL} returned an empty body"
        assert len(body.strip()) > 0, (
            f"Portfolio health partial at {_PORTFOLIO_PARTIAL} returned a whitespace-only body"
        )

    def test_portfolio_partial_no_error_status(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/portfolio-health does not return a 4xx/5xx status."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_no_error(page, _PORTFOLIO_PARTIAL)

    def test_portfolio_partial_content_type_is_html(self, page, base_url: str) -> None:
        """GET /admin/ui/partials/portfolio-health Content-Type header contains 'html'."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        ctx = page.request
        response = ctx.get(_PORTFOLIO_PARTIAL)
        assert response.status == 200, (
            f"Expected 200 from {_PORTFOLIO_PARTIAL}, got {response.status}"
        )
        content_type = response.headers.get("content-type", "")
        assert "html" in content_type.lower(), (
            f"Portfolio health partial must return HTML content; "
            f"got Content-Type: {content_type!r}"
        )


class TestReposHealthEndpoint:
    """Repos health endpoint must return per-repository health summaries.

    The Portfolio Health page surfaces cross-repo health signals; the
    ``/admin/repos/health`` endpoint is the JSON source that backs the per-repo
    health state shown in the portfolio view.  Each item must carry at minimum
    a repo identity and a health indicator so operators can see at a glance
    which repos are healthy, degraded, or idle.
    """

    def test_repos_health_returns_200(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns HTTP 200."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)

    def test_repos_health_is_valid_json_object(self, page, base_url: str) -> None:
        """GET /admin/repos/health returns a non-null JSON object."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {_REPOS_HEALTH}, got {type(data).__name__!r}"
        )

    def test_repos_health_has_repos_list(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains a 'repos' list."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {_REPOS_HEALTH}"
        )
        assert "repos" in data, (
            f"Repos health response must contain a 'repos' key "
            f"(required to populate the portfolio health view). "
            f"Present keys: {list(data.keys())!r}"
        )
        assert isinstance(data["repos"], list), (
            f"'repos' field from {_REPOS_HEALTH} must be a JSON array"
        )

    def test_repos_health_has_total(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains a 'total' count."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), (
            f"Expected JSON object from {_REPOS_HEALTH}"
        )
        assert "total" in data, (
            f"Repos health response must contain a 'total' field. "
            f"Present keys: {list(data.keys())!r}"
        )
        assert isinstance(data["total"], int), (
            f"'total' from {_REPOS_HEALTH} must be an integer, got {data.get('total')!r}"
        )
        assert data["total"] >= 0, (
            f"'total' from {_REPOS_HEALTH} must be non-negative, got {data.get('total')!r}"
        )

    def test_repos_health_items_have_identity(self, page, base_url: str) -> None:
        """Each repo health item has an identity field ('id', 'repo_id', or 'name')."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), f"Expected JSON object from {_REPOS_HEALTH}"
        repos = data.get("repos", [])
        if not repos:
            pytest.skip(
                "No repos registered — identity check skipped (empty list is valid)"
            )
        for item in repos:
            has_identity = any(k in item for k in ("id", "repo_id", "name", "full_name"))
            assert has_identity, (
                "Each repo health item must contain an identity field "
                "('id', 'repo_id', 'name', or 'full_name'). "
                f"Got keys: {list(item.keys())!r}"
            )

    def test_repos_health_items_have_health_field(self, page, base_url: str) -> None:
        """Each repo health item has a 'health' or 'status' field."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), f"Expected JSON object from {_REPOS_HEALTH}"
        repos = data.get("repos", [])
        if not repos:
            pytest.skip(
                "No repos registered — health field check skipped (empty list is valid)"
            )
        for item in repos:
            has_health = "health" in item or "status" in item
            assert has_health, (
                "Each repo health item must contain a 'health' or 'status' field "
                f"(required for portfolio risk distribution). Got keys: {list(item.keys())!r}"
            )

    def test_repos_health_items_health_values_valid(self, page, base_url: str) -> None:
        """Each repo health item 'health' value is one of the expected states."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _REPOS_HEALTH, 200)
        assert isinstance(data, dict), f"Expected JSON object from {_REPOS_HEALTH}"
        repos = data.get("repos", [])
        if not repos:
            pytest.skip("No repos registered — health values check skipped")
        valid_health_states = {"ok", "degraded", "idle", "healthy", "warning", "critical"}
        for item in repos:
            health_val = item.get("health") or item.get("status")
            if health_val is not None:
                assert str(health_val).lower() in valid_health_states, (
                    f"Repo health item 'health'/'status' value {health_val!r} is not one of "
                    f"{sorted(valid_health_states)}. "
                    "Portfolio risk distribution depends on well-defined health states."
                )

    def test_repos_health_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/repos/health response contains no error payload."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_no_error(page, _REPOS_HEALTH)


class TestPortfolioHealthLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Portfolio Health page.

    The Portfolio Health page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after portfolio routes are added.
    """

    def test_healthz_returns_200_from_portfolio_health(
        self, page, base_url: str
    ) -> None:
        """GET /healthz returns HTTP 200 when portfolio health page is loaded."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_portfolio_health(
        self, page, base_url: str
    ) -> None:
        """GET /healthz JSON body contains 'status' field (portfolio health context)."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_portfolio_health(
        self, page, base_url: str
    ) -> None:
        """GET /healthz response contains no error payload (portfolio health context)."""
        page.goto(f"{base_url}{_PORTFOLIO_HEALTH_PAGE}")
        assert_api_no_error(page, _HEALTHZ)
