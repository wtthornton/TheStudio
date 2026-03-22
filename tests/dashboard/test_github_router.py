"""Tests for GET /api/v1/dashboard/github/issues (Epic 38, Story 38.1) and
POST /api/v1/dashboard/github/import (Epic 38, Story 38.2)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.dashboard.github_router import _cache_clear
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(number: int, title: str = "Fix bug", state: str = "open") -> dict[str, Any]:
    """Return a minimal raw GitHub API issue dict."""
    return {
        "id": 1000 + number,
        "number": number,
        "title": title,
        "body": "Some description",
        "state": state,
        "labels": [{"name": "bug"}, {"name": "help-wanted"}],
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "user": {"login": "alice"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "comments": 3,
    }


def _make_pr(number: int) -> dict[str, Any]:
    """Return a raw GitHub API item that is a pull request (has 'pull_request' key)."""
    pr = _make_issue(number, title="Refactor something")
    pr["pull_request"] = {"url": f"https://api.github.com/repos/owner/repo/pulls/{number}"}
    return pr


def _mock_httpx_response(
    payload: list[dict[str, Any]] | dict[str, Any],
    status_code: int = 200,
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = payload
    return resp


def _make_async_client_ctx(response: MagicMock) -> MagicMock:
    """Return an async context manager mock that yields a client whose get() returns response."""
    client_mock = AsyncMock()
    client_mock.get = AsyncMock(return_value=response)

    ctx_mock = MagicMock()
    ctx_mock.__aenter__ = AsyncMock(return_value=client_mock)
    ctx_mock.__aexit__ = AsyncMock(return_value=None)
    return ctx_mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_github_cache() -> None:
    """Clear the in-memory cache before each test to avoid cross-test pollution."""
    _cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPI test client with GitHub token configured and auth disabled."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "intake_poll_token", "test-token-abc")
    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
    return TestClient(app)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestListGitHubIssuesHappyPath:
    def test_returns_issues_list(self, client: TestClient) -> None:
        """Returns paginated list of issues with correct fields."""
        issues = [_make_issue(1), _make_issue(2)]
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 30
        assert len(data["issues"]) == 2
        # Check first issue fields
        issue = data["issues"][0]
        assert issue["number"] == 1
        assert issue["title"] == "Fix bug"
        assert issue["state"] == "open"
        assert issue["user_login"] == "alice"
        assert issue["labels"] == ["bug", "help-wanted"]
        assert issue["comments"] == 3

    def test_filters_out_pull_requests(self, client: TestClient) -> None:
        """Pull requests (items with 'pull_request' key) are excluded from results."""
        mixed = [_make_issue(1), _make_pr(99), _make_issue(2)]
        resp_mock = _mock_httpx_response(mixed)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        numbers = [i["number"] for i in data["issues"]]
        assert 99 not in numbers

    def test_search_filter_case_insensitive(self, client: TestClient) -> None:
        """Search parameter filters by title (case-insensitive)."""
        issues = [
            _make_issue(1, title="Fix SSO login"),
            _make_issue(2, title="Add dark mode"),
            _make_issue(3, title="sso timeout bug"),
        ]
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo&search=sso")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        titles = [i["title"] for i in data["issues"]]
        assert "Add dark mode" not in titles

    def test_has_next_true_when_full_page(self, client: TestClient) -> None:
        """has_next is True when the raw page contains exactly per_page items."""
        issues = [_make_issue(i) for i in range(1, 31)]  # 30 issues
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo&per_page=30")

        assert resp.json()["has_next"] is True

    def test_has_next_false_when_partial_page(self, client: TestClient) -> None:
        """has_next is False when the page has fewer items than per_page."""
        issues = [_make_issue(1), _make_issue(2)]
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo&per_page=30")

        assert resp.json()["has_next"] is False

    def test_labels_query_param_forwarded(self, client: TestClient) -> None:
        """Labels parameter is passed through to the GitHub API call."""
        resp_mock = _mock_httpx_response([_make_issue(1)])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            client.get("/api/v1/dashboard/github/issues?repo=owner/repo&labels=bug,enhancement")

        # Verify the GET call params contain labels
        get_call_kwargs = mock_cls.return_value.__aenter__.return_value.get.call_args
        params = get_call_kwargs[1]["params"]
        assert params["labels"] == "bug,enhancement"

    def test_state_param_forwarded(self, client: TestClient) -> None:
        """state parameter is passed through to the GitHub API."""
        resp_mock = _mock_httpx_response([])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            client.get("/api/v1/dashboard/github/issues?repo=owner/repo&state=closed")

        get_call_kwargs = mock_cls.return_value.__aenter__.return_value.get.call_args
        params = get_call_kwargs[1]["params"]
        assert params["state"] == "closed"

    def test_issue_with_null_body(self, client: TestClient) -> None:
        """Issues with null body are handled gracefully."""
        raw = _make_issue(5)
        raw["body"] = None
        resp_mock = _mock_httpx_response([raw])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 200
        assert resp.json()["issues"][0]["body"] is None

    def test_issue_with_null_user(self, client: TestClient) -> None:
        """Issues with null user are handled gracefully."""
        raw = _make_issue(6)
        raw["user"] = None
        resp_mock = _mock_httpx_response([raw])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 200
        assert resp.json()["issues"][0]["user_login"] is None

    def test_empty_result(self, client: TestClient) -> None:
        """Returns empty list when GitHub returns no issues."""
        resp_mock = _mock_httpx_response([])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 200
        data = resp.json()
        assert data["issues"] == []
        assert data["total_count"] == 0
        assert data["has_next"] is False


# ---------------------------------------------------------------------------
# Caching tests
# ---------------------------------------------------------------------------


class TestCaching:
    def test_cache_hit_skips_api_call(self, client: TestClient) -> None:
        """Second identical request uses cache and does not call GitHub API again."""
        issues = [_make_issue(1)]
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            r1 = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")
            r2 = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()
        # httpx.AsyncClient was only instantiated once
        assert mock_cls.call_count == 1

    def test_different_params_bypass_cache(self, client: TestClient) -> None:
        """Different query params result in separate cache entries and API calls."""
        resp_mock = _mock_httpx_response([_make_issue(1)])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            client.get("/api/v1/dashboard/github/issues?repo=owner/repo&page=1")
            client.get("/api/v1/dashboard/github/issues?repo=owner/repo&page=2")

        assert mock_cls.call_count == 2

    def test_expired_cache_calls_api_again(self, client: TestClient) -> None:
        """Expired cache entries trigger a fresh API call."""
        import time

        import src.dashboard.github_router as github_mod
        from src.dashboard.github_router import GitHubIssueListResponse

        issues = [_make_issue(1)]
        resp_mock = _mock_httpx_response(issues)
        ctx = _make_async_client_ctx(resp_mock)

        # Pre-populate cache with an already-expired entry
        cache_key = "owner/repo|open||1|30|1"
        stale_data = GitHubIssueListResponse(
            issues=[], total_count=0, page=1, per_page=30, has_next=False
        )
        # Set expiry to 1 second ago
        github_mod._cache[cache_key] = (time.monotonic() - 1.0, stale_data)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        # Should have called the API (expired entry was evicted)
        assert mock_cls.call_count == 1
        # And should return fresh data (1 issue), not the stale empty list
        assert resp.json()["total_count"] == 1


# ---------------------------------------------------------------------------
# Error / validation tests
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_token_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """503 returned when THESTUDIO_INTAKE_POLL_TOKEN is not configured."""
        from src import settings as settings_mod
        from fastapi.testclient import TestClient

        monkeypatch.setattr(settings_mod.settings, "intake_poll_token", "")
        monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
        c = TestClient(app)
        resp = c.get("/api/v1/dashboard/github/issues?repo=owner/repo")
        assert resp.status_code == 503
        assert "token" in resp.json()["detail"].lower()

    def test_invalid_repo_format_returns_400(self, client: TestClient) -> None:
        """400 returned when repo is not in 'owner/repo' format."""
        resp = client.get("/api/v1/dashboard/github/issues?repo=badformat")
        assert resp.status_code == 400
        assert "owner/repo" in resp.json()["detail"]

    def test_repo_with_extra_slash_returns_400(self, client: TestClient) -> None:
        """400 returned when repo has extra slashes."""
        resp = client.get("/api/v1/dashboard/github/issues?repo=a/b/c")
        assert resp.status_code == 400

    def test_github_404_returns_404(self, client: TestClient) -> None:
        """404 returned when GitHub reports the repository does not exist."""
        resp_mock = _mock_httpx_response({"message": "Not Found"}, status_code=404)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/nonexistent")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_github_401_returns_502(self, client: TestClient) -> None:
        """502 returned when GitHub API authentication fails (401)."""
        resp_mock = _mock_httpx_response({"message": "Bad credentials"}, status_code=401)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 502
        assert "authentication" in resp.json()["detail"].lower()

    def test_github_403_returns_502(self, client: TestClient) -> None:
        """502 returned when GitHub API returns 403 Forbidden."""
        resp_mock = _mock_httpx_response({"message": "Forbidden"}, status_code=403)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 502

    def test_github_429_returns_429(self, client: TestClient) -> None:
        """429 returned when GitHub API rate limit is exceeded."""
        resp_mock = _mock_httpx_response(
            {"message": "API rate limit exceeded"}, status_code=429
        )
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()

    def test_github_500_returns_502(self, client: TestClient) -> None:
        """502 returned when GitHub API has a server error."""
        resp_mock = _mock_httpx_response({"message": "Server Error"}, status_code=500)
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 502

    def test_httpx_timeout_returns_504(self, client: TestClient) -> None:
        """504 returned when GitHub API request times out."""
        import httpx

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(
            side_effect=httpx.TimeoutException("timeout", request=MagicMock())
        )
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 504

    def test_httpx_request_error_returns_502(self, client: TestClient) -> None:
        """502 returned when httpx raises a connection error."""
        import httpx

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(
            side_effect=httpx.ConnectError("connection refused", request=MagicMock())
        )
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo")

        assert resp.status_code == 502

    def test_missing_repo_param_returns_422(self, client: TestClient) -> None:
        """422 returned when required 'repo' param is absent."""
        resp = client.get("/api/v1/dashboard/github/issues")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pagination / query params tests
# ---------------------------------------------------------------------------


class TestPagination:
    def test_page_and_per_page_forwarded(self, client: TestClient) -> None:
        """page and per_page are forwarded to the GitHub API request."""
        resp_mock = _mock_httpx_response([])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx) as mock_cls:
            client.get("/api/v1/dashboard/github/issues?repo=owner/repo&page=3&per_page=50")

        get_kwargs = mock_cls.return_value.__aenter__.return_value.get.call_args
        params = get_kwargs[1]["params"]
        assert params["page"] == 3
        assert params["per_page"] == 50

    def test_per_page_max_100_enforced(self, client: TestClient) -> None:
        """per_page > 100 is rejected by query param validation."""
        resp = client.get(
            "/api/v1/dashboard/github/issues?repo=owner/repo&per_page=200"
        )
        assert resp.status_code == 422

    def test_page_min_1_enforced(self, client: TestClient) -> None:
        """page < 1 is rejected by query param validation."""
        resp = client.get("/api/v1/dashboard/github/issues?repo=owner/repo&page=0")
        assert resp.status_code == 422

    def test_page_response_fields(self, client: TestClient) -> None:
        """Response reflects the requested page and per_page values."""
        resp_mock = _mock_httpx_response([_make_issue(1)])
        ctx = _make_async_client_ctx(resp_mock)

        with patch("src.dashboard.github_router.httpx.AsyncClient", return_value=ctx):
            resp = client.get(
                "/api/v1/dashboard/github/issues?repo=owner/repo&page=2&per_page=10"
            )

        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 10


# ---------------------------------------------------------------------------
# POST /github/import tests (Story 38.2)
# ---------------------------------------------------------------------------


def _make_task_read(
    task_id: str | None = None,
    issue_number: int = 1,
    repo: str = "owner/repo",
    status: TaskPacketStatus = TaskPacketStatus.RECEIVED,
) -> MagicMock:
    """Build a minimal MagicMock that resembles a TaskPacketRead."""
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    mock = MagicMock(spec=TaskPacketRead)
    mock.id = UUID(task_id) if task_id else uuid4()
    mock.correlation_id = uuid4()
    mock.repo = repo
    mock.issue_id = issue_number
    mock.status = status
    mock.delivery_id = f"dashboard_import-{repo}-{issue_number}"
    mock.source_name = "dashboard_import"
    mock.created_at = datetime.now(UTC)
    mock.updated_at = datetime.now(UTC)
    return mock


def _import_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with GitHub token set and dashboard auth disabled."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "intake_poll_token", "test-token-abc")
    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
    monkeypatch.setattr(settings_mod.settings, "triage_mode_enabled", False)
    return TestClient(app)


def _import_payload(
    repo: str = "owner/repo",
    issues: list[dict] | None = None,
    triage_override: bool | None = None,
) -> dict:
    """Build a minimal import request payload."""
    if issues is None:
        issues = [{"number": 1, "title": "Fix login bug"}]
    body: dict = {"repo": repo, "issues": issues}
    if triage_override is not None:
        body["triage_override"] = triage_override
    return body


def _mock_session() -> AsyncMock:
    """Return a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


class TestImportGitHubIssues:
    """Tests for POST /api/v1/dashboard/github/import."""

    def test_happy_path_creates_task_received(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Single issue imported in RECEIVED mode starts workflow."""
        client = _import_client(monkeypatch)
        task = _make_task_read(issue_number=1)

        session_mock = _mock_session()
        app.dependency_overrides[get_session] = lambda: session_mock

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)),
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock(return_value="run-id")),
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(),
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        assert data["duplicates"] == 0
        assert data["errors"] == 0
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["number"] == 1
        assert result["status"] == "created"
        assert result["task_id"] == str(task.id)

    def test_happy_path_triage_mode_no_workflow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With triage_override=True task is created in TRIAGE; no workflow started."""
        client = _import_client(monkeypatch)
        task = _make_task_read(issue_number=2, status=TaskPacketStatus.TRIAGE)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)) as mock_create,
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock()) as mock_wf,
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(
                        issues=[{"number": 2, "title": "Add feature"}],
                        triage_override=True,
                    ),
                )
                # Workflow must NOT be called when triage mode is on
                mock_wf.assert_not_called()
                # create_taskpacket must have been called with TRIAGE status
                call_kwargs = mock_create.call_args
                assert call_kwargs[1]["initial_status"] == TaskPacketStatus.TRIAGE
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        result = data["results"][0]
        assert result["status"] == "created"
        assert result["workflow_started"] is False

    def test_duplicate_issue_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Issue already in pipeline is marked duplicate; no new TaskPacket created."""
        client = _import_client(monkeypatch)
        existing = _make_task_read(issue_number=5)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=existing)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock()) as mock_create,
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(issues=[{"number": 5, "title": "Old issue"}]),
                )
                mock_create.assert_not_called()
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["duplicates"] == 1
        assert data["created"] == 0
        result = data["results"][0]
        assert result["status"] == "duplicate"
        assert result["task_id"] == str(existing.id)

    def test_batch_mixed_created_and_duplicate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Batch with 1 new + 1 duplicate returns correct counts."""
        client = _import_client(monkeypatch)
        new_task = _make_task_read(issue_number=10)
        existing_task = _make_task_read(issue_number=20)

        async def _get_by_repo_and_issue(session, repo, issue_number):
            if issue_number == 20:
                return existing_task
            return None

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=_get_by_repo_and_issue),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=new_task)),
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock()),
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(
                        issues=[
                            {"number": 10, "title": "New issue"},
                            {"number": 20, "title": "Already imported"},
                        ]
                    ),
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        assert data["duplicates"] == 1
        statuses = {r["number"]: r["status"] for r in data["results"]}
        assert statuses[10] == "created"
        assert statuses[20] == "duplicate"

    def test_uses_settings_triage_mode_when_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When triage_override is absent, server triage_mode_enabled is respected."""
        from src import settings as settings_mod

        monkeypatch.setattr(settings_mod.settings, "intake_poll_token", "test-token-abc")
        monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
        monkeypatch.setattr(settings_mod.settings, "triage_mode_enabled", True)

        client = TestClient(app)
        task = _make_task_read(issue_number=7, status=TaskPacketStatus.TRIAGE)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)) as mock_create,
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock()) as mock_wf,
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(issues=[{"number": 7, "title": "Feature X"}]),
                )
                mock_wf.assert_not_called()
                assert mock_create.call_args[1]["initial_status"] == TaskPacketStatus.TRIAGE
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200

    def test_create_error_marked_as_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If TaskPacket creation raises an exception the result is 'error'."""
        client = _import_client(monkeypatch)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(side_effect=RuntimeError("DB down"))),
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(issues=[{"number": 3, "title": "Broken"}]),
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["errors"] == 1
        assert data["created"] == 0
        result = data["results"][0]
        assert result["status"] == "error"
        assert "DB down" in result["error"]

    def test_invalid_repo_format_returns_400(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """400 returned when repo is not in 'owner/repo' format."""
        client = _import_client(monkeypatch)
        resp = client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(repo="badformat"),
        )
        assert resp.status_code == 400
        assert "owner/repo" in resp.json()["detail"]

    def test_repo_with_extra_slash_returns_400(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """400 returned when repo has extra slashes."""
        client = _import_client(monkeypatch)
        resp = client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(repo="a/b/c"),
        )
        assert resp.status_code == 400

    def test_empty_issues_list_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """422 returned when issues list is empty."""
        client = _import_client(monkeypatch)
        resp = client.post(
            "/api/v1/dashboard/github/import",
            json={"repo": "owner/repo", "issues": []},
        )
        assert resp.status_code == 422

    def test_source_name_is_dashboard_import(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TaskPacketCreate is always called with source_name='dashboard_import'."""
        client = _import_client(monkeypatch)
        task = _make_task_read(issue_number=1)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)) as mock_create,
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock()),
            ):
                client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(),
                )
                call_args = mock_create.call_args
                task_data = call_args[0][1]  # second positional arg is TaskPacketCreate
                assert task_data.source_name == "dashboard_import"
        finally:
            app.dependency_overrides.clear()

    def test_workflow_failure_does_not_fail_import(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Workflow start failure is logged but import result is still 'created'."""
        client = _import_client(monkeypatch)
        task = _make_task_read(issue_number=1)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)),
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock(side_effect=Exception("Temporal down"))),
            ):
                resp = client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(triage_override=False),
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        result = data["results"][0]
        assert result["status"] == "created"
        assert result["workflow_started"] is False

    def test_labels_passed_to_workflow(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Labels from the issue are forwarded to start_workflow."""
        client = _import_client(monkeypatch)
        task = _make_task_read(issue_number=1)

        app.dependency_overrides[get_session] = lambda: _mock_session()

        try:
            with (
                patch("src.dashboard.github_router.get_by_repo_and_issue", new=AsyncMock(return_value=None)),
                patch("src.dashboard.github_router.create_taskpacket", new=AsyncMock(return_value=task)),
                patch("src.ingress.workflow_trigger.start_workflow", new=AsyncMock()) as mock_wf,
            ):
                client.post(
                    "/api/v1/dashboard/github/import",
                    json=_import_payload(
                        issues=[{
                            "number": 1,
                            "title": "Fix bug",
                            "labels": ["bug", "priority-high"],
                        }],
                        triage_override=False,
                    ),
                )
                call_kwargs = mock_wf.call_args[1]
                assert call_kwargs["labels"] == ["bug", "priority-high"]
        finally:
            app.dependency_overrides.clear()
