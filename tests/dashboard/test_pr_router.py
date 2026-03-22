"""Tests for POST /api/v1/dashboard/tasks/{task_id}/pr/approve (Epic 38, Story 38.9)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    task_id: UUID | None = None,
    repo: str = "owner/repo",
    pr_number: int | None = 42,
    status: TaskPacketStatus = TaskPacketStatus.PUBLISHED,
) -> TaskPacketRead:
    """Build a minimal TaskPacketRead for use in tests."""
    return TaskPacketRead(
        id=task_id or uuid4(),
        repo=repo,
        issue_id=1,
        delivery_id="delivery-123",
        correlation_id=uuid4(),
        source_name="github",
        status=status,
        pr_number=pr_number,
        pr_url=f"https://github.com/{repo}/pull/{pr_number}" if pr_number else None,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-02T00:00:00Z",
    )


def _mock_httpx_put_response(
    payload: dict[str, Any],
    status_code: int = 200,
) -> MagicMock:
    """Build a mock httpx.Response for a PUT request."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = payload
    return resp


def _make_async_client_ctx(put_response: MagicMock) -> MagicMock:
    """Return an async context manager whose client.put() returns the given response."""
    client_mock = AsyncMock()
    client_mock.put = AsyncMock(return_value=put_response)

    ctx_mock = MagicMock()
    ctx_mock.__aenter__ = AsyncMock(return_value=client_mock)
    ctx_mock.__aexit__ = AsyncMock(return_value=None)
    return ctx_mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPI test client with GitHub token configured and auth disabled."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "intake_poll_token", "test-token-abc")
    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper to mock the DB session + get_by_id
# ---------------------------------------------------------------------------


def _patch_get_by_id(task: TaskPacketRead | None):
    """Patch taskpacket_crud.get_by_id to return *task* and override DB session dep."""

    async def _fake_get_by_id(session: Any, task_id: UUID) -> TaskPacketRead | None:
        return task

    async def _fake_session():
        yield MagicMock()

    return (
        patch("src.dashboard.pr_router.get_by_id", side_effect=_fake_get_by_id),
        patch.object(app.dependency_overrides, "__setitem__"),  # handled by override below
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestApprovePRHappyPath:
    def test_approve_returns_200_and_merged_true(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Successfully merging a PR returns 200 with merged=True and sha."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        merge_payload = {
            "sha": "abc123def456",
            "merged": True,
            "message": "Pull request successfully merged",
        }
        resp_mock = _mock_httpx_put_response(merge_payload, status_code=200)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == str(task_id)
        assert data["pr_number"] == 42
        assert data["merged"] is True
        assert data["sha"] == "abc123def456"

    def test_approve_passes_squash_merge_method(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The merge request payload uses squash merge method."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        merge_payload = {"sha": "deadbeef", "merged": True, "message": "merged"}
        resp_mock = _mock_httpx_put_response(merge_payload, status_code=200)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        # Verify put() was called with squash payload
        ctx.__aenter__.return_value.put.assert_called_once()
        call_kwargs = ctx.__aenter__.return_value.put.call_args
        assert call_kwargs.kwargs["json"]["merge_method"] == "squash"


# ---------------------------------------------------------------------------
# 404 tests
# ---------------------------------------------------------------------------


class TestApprovePR404:
    def test_returns_404_when_task_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Returns 404 when the TaskPacket does not exist."""
        task_id = uuid4()

        async def fake_get_by_id(session: Any, tid: UUID) -> None:
            return None

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 404
        assert str(task_id) in resp.json()["detail"]

    def test_returns_404_when_github_pr_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Returns 404 when the PR number exists in DB but GitHub returns 404."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=404)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 404
        assert "42" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 409 tests
# ---------------------------------------------------------------------------


class TestApprovePR409:
    def test_returns_409_when_no_pr_number(
        self,
        client: TestClient,
    ) -> None:
        """Returns 409 when task exists but has no associated PR."""
        task_id = uuid4()
        task = _make_task(task_id=task_id, pr_number=None)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 409
        assert "no associated pull request" in resp.json()["detail"]

    def test_returns_409_when_not_mergeable(
        self,
        client: TestClient,
    ) -> None:
        """Returns 409 when GitHub returns 405 (PR not mergeable)."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=405)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 409
        assert "not mergeable" in resp.json()["detail"]

    def test_returns_409_on_merge_conflict(
        self,
        client: TestClient,
    ) -> None:
        """Returns 409 when GitHub returns 409 (merge conflict)."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=409)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 409
        assert "merge conflict" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GitHub API error tests
# ---------------------------------------------------------------------------


class TestApprovePRGitHubErrors:
    def test_returns_502_on_auth_failure(self, client: TestClient) -> None:
        """Returns 502 when GitHub returns 401/403."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=401)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 502
        assert "authentication" in resp.json()["detail"]

    def test_returns_429_on_rate_limit(self, client: TestClient) -> None:
        """Returns 429 when GitHub rate-limits the request."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=429)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 429

    def test_returns_502_on_unexpected_github_status(self, client: TestClient) -> None:
        """Returns 502 for unexpected GitHub error status codes (e.g., 500)."""
        task_id = uuid4()
        task = _make_task(task_id=task_id)

        resp_mock = _mock_httpx_put_response({}, status_code=500)
        ctx = _make_async_client_ctx(resp_mock)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 502
        assert "HTTP 500" in resp.json()["detail"]

    def test_returns_504_on_timeout(self, client: TestClient) -> None:
        """Returns 504 when the GitHub API request times out."""
        import httpx as _httpx

        task_id = uuid4()
        task = _make_task(task_id=task_id)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        # Simulate a timeout by raising TimeoutException inside __aenter__
        client_mock = AsyncMock()
        client_mock.put = AsyncMock(side_effect=_httpx.TimeoutException("timed out"))
        ctx_mock = MagicMock()
        ctx_mock.__aenter__ = AsyncMock(return_value=client_mock)
        ctx_mock.__aexit__ = AsyncMock(return_value=None)

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx_mock):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"]

    def test_returns_502_on_request_error(self, client: TestClient) -> None:
        """Returns 502 when a network-level httpx.RequestError occurs."""
        import httpx as _httpx

        task_id = uuid4()
        task = _make_task(task_id=task_id)

        async def fake_get_by_id(session: Any, tid: UUID) -> TaskPacketRead:
            return task

        async def fake_session():
            yield MagicMock()

        app.dependency_overrides[get_session] = fake_session

        client_mock = AsyncMock()
        client_mock.put = AsyncMock(
            side_effect=_httpx.RequestError("connection refused", request=MagicMock())
        )
        ctx_mock = MagicMock()
        ctx_mock.__aenter__ = AsyncMock(return_value=client_mock)
        ctx_mock.__aexit__ = AsyncMock(return_value=None)

        try:
            with patch("src.dashboard.pr_router.get_by_id", side_effect=fake_get_by_id):
                with patch("src.dashboard.pr_router.httpx.AsyncClient", return_value=ctx_mock):
                    resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 502

    def test_returns_503_when_no_token_configured(self, client: TestClient) -> None:
        """Returns 503 when THESTUDIO_INTAKE_POLL_TOKEN is not set."""
        from src import settings as settings_mod

        task_id = uuid4()

        # No DB call needed — token check happens first
        app.dependency_overrides.pop(get_session, None)

        # Temporarily clear the token that the fixture set
        original = settings_mod.settings.intake_poll_token
        settings_mod.settings.intake_poll_token = ""

        try:
            resp = client.post(f"/api/v1/dashboard/tasks/{task_id}/pr/approve")
        finally:
            settings_mod.settings.intake_poll_token = original

        assert resp.status_code == 503
        assert "token not configured" in resp.json()["detail"]
