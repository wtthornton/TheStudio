"""Integration tests for PR Evidence Explorer (Epic 38, Story 38.12).

Tests the following flows against a real PostgreSQL database:
- Evidence JSON generated for a published TaskPacket
- Approve action calls GitHub merge API
- Request-changes calls review API
- Error cases: task not found, task has no PR
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRow, TaskPacketStatus
from src.settings import settings

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_REPO = "test-org/pr-explorer-repo"


@pytest.fixture
async def db_engine():
    """Create a transient in-test PostgreSQL engine with fresh schema."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine):
    """Yield a live database session for assertion helpers."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def http_client(db_engine, monkeypatch: pytest.MonkeyPatch):
    """Async HTTP client wired to the FastAPI app with real DB and no auth.

    * ``get_session`` dependency is overridden to use the test-scoped engine.
    * Dashboard token auth is disabled.
    * GitHub token is set to a stub value.
    """
    # Configure settings
    monkeypatch.setattr(settings, "dashboard_token", "")
    monkeypatch.setattr(settings, "intake_poll_token", "test-github-token")

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


async def _create_published_task(
    session: AsyncSession,
    *,
    repo: str = _REPO,
    issue_number: int = 1,
    pr_number: int | None = 42,
    pr_url: str | None = None,
    status: TaskPacketStatus = TaskPacketStatus.PUBLISHED,
) -> TaskPacketRow:
    """Insert a TaskPacket row directly, bypassing transition validation."""
    row = TaskPacketRow(
        repo=repo,
        issue_id=issue_number,
        delivery_id=f"delivery-{uuid4().hex}",
        correlation_id=uuid4(),
        source_name="test",
        status=status,
        pr_number=pr_number,
        pr_url=pr_url or (f"https://github.com/{repo}/pull/{pr_number}" if pr_number else None),
        issue_title="Fix SSO login timeout",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


def _make_github_client_mock(
    *,
    method: str = "put",
    status_code: int = 200,
    json_body: dict | None = None,
) -> MagicMock:
    """Build an httpx.AsyncClient mock that returns a fake response.

    Args:
        method: HTTP method to mock ("put" or "post").
        status_code: HTTP status code to return.
        json_body: JSON payload returned by ``response.json()``.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.is_success = 200 <= status_code < 300
    mock_response.json.return_value = json_body or {}
    mock_response.text = ""

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    setattr(mock_client, method, AsyncMock(return_value=mock_response))
    return mock_client


# ---------------------------------------------------------------------------
# Section 1 — Evidence JSON for published TaskPacket
# ---------------------------------------------------------------------------


async def test_evidence_json_for_published_task(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """GET /tasks/:id/evidence returns EvidencePayload JSON for a published task."""
    row = await _create_published_task(session, pr_number=42, issue_number=100)

    resp = await http_client.get(f"/api/v1/dashboard/tasks/{row.id}/evidence")

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Schema-level fields
    assert data["schema_version"] == "1.0"
    assert data["generated_at"] is not None

    # task_summary section
    ts = data["task_summary"]
    assert ts["taskpacket_id"] == str(row.id)
    assert ts["repo"] == _REPO
    assert ts["issue_id"] == 100
    assert ts["status"] == "published"
    assert ts["pr_number"] == 42
    assert ts["pr_url"] == f"https://github.com/{_REPO}/pull/42"
    assert ts["issue_title"] == "Fix SSO login timeout"

    # Sections not yet persisted should be null / empty
    assert data["intent"] is None
    assert data["gate_results"] is None
    assert data["cost_breakdown"] is None
    assert data["provenance"] is None
    assert data["files_changed"] == []


async def test_evidence_json_404_for_unknown_task(
    http_client: AsyncClient,
) -> None:
    """GET /tasks/:id/evidence returns 404 when the task does not exist."""
    missing_id = uuid4()
    resp = await http_client.get(f"/api/v1/dashboard/tasks/{missing_id}/evidence")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_evidence_json_task_without_pr(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """GET /tasks/:id/evidence returns a payload with null PR fields when task has no PR."""
    row = await _create_published_task(
        session,
        pr_number=None,
        pr_url=None,
        status=TaskPacketStatus.IN_PROGRESS,
        issue_number=101,
    )

    resp = await http_client.get(f"/api/v1/dashboard/tasks/{row.id}/evidence")

    assert resp.status_code == 200, resp.text
    ts = resp.json()["task_summary"]
    assert ts["pr_number"] is None
    assert ts["pr_url"] is None
    assert ts["status"] == "in_progress"


# ---------------------------------------------------------------------------
# Section 2 — Approve action calls GitHub merge API
# ---------------------------------------------------------------------------


async def test_approve_pr_calls_github_merge_api(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/approve calls GitHub PUT merge endpoint and returns 200."""
    row = await _create_published_task(session, pr_number=55, issue_number=200)

    merge_response_body = {
        "sha": "deadbeef1234",
        "message": "Pull request successfully merged",
    }
    mock_client = _make_github_client_mock(
        method="put",
        status_code=200,
        json_body=merge_response_body,
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await http_client.post(f"/api/v1/dashboard/tasks/{row.id}/pr/approve")

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["task_id"] == str(row.id)
    assert data["pr_number"] == 55
    assert data["merged"] is True
    assert data["sha"] == "deadbeef1234"

    # Verify the GitHub merge endpoint was called with squash merge
    mock_client.put.assert_called_once()
    call_args = mock_client.put.call_args
    assert "/pulls/55/merge" in call_args.args[0]
    assert call_args.kwargs["json"]["merge_method"] == "squash"


async def test_approve_pr_404_task_not_found(
    http_client: AsyncClient,
) -> None:
    """POST /tasks/:id/pr/approve returns 404 when task does not exist."""
    missing_id = uuid4()
    resp = await http_client.post(f"/api/v1/dashboard/tasks/{missing_id}/pr/approve")

    assert resp.status_code == 404
    assert str(missing_id) in resp.json()["detail"]


async def test_approve_pr_409_task_has_no_pr(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/approve returns 409 when task has no associated PR."""
    row = await _create_published_task(
        session,
        pr_number=None,
        pr_url=None,
        issue_number=201,
    )

    resp = await http_client.post(f"/api/v1/dashboard/tasks/{row.id}/pr/approve")

    assert resp.status_code == 409
    assert "no associated pull request" in resp.json()["detail"]


async def test_approve_pr_github_api_error_returns_502(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/approve returns 502 when GitHub API returns an error."""
    row = await _create_published_task(session, pr_number=66, issue_number=202)

    mock_client = _make_github_client_mock(method="put", status_code=500)

    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await http_client.post(f"/api/v1/dashboard/tasks/{row.id}/pr/approve")

    assert resp.status_code == 502
    assert "GitHub API error" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Section 3 — Request-changes calls review API
# ---------------------------------------------------------------------------


async def test_request_changes_calls_github_review_api(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/request-changes calls GitHub POST reviews endpoint and returns 200."""
    row = await _create_published_task(session, pr_number=77, issue_number=300)

    review_response_body = {
        "id": 999,
        "body": "Please fix the failing tests",
        "state": "CHANGES_REQUESTED",
    }
    mock_client = _make_github_client_mock(
        method="post",
        status_code=200,
        json_body=review_response_body,
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await http_client.post(
            f"/api/v1/dashboard/tasks/{row.id}/pr/request-changes",
            json={"body": "Please fix the failing tests", "trigger_loopback": False},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["task_id"] == str(row.id)
    assert data["pr_number"] == 77
    assert data["review_id"] == 999
    assert data["message"] == "Review submitted: changes requested"

    # Verify the GitHub reviews endpoint was called with correct payload
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/pulls/77/reviews" in call_args.args[0]
    assert call_args.kwargs["json"]["event"] == "REQUEST_CHANGES"
    assert call_args.kwargs["json"]["body"] == "Please fix the failing tests"


async def test_request_changes_404_task_not_found(
    http_client: AsyncClient,
) -> None:
    """POST /tasks/:id/pr/request-changes returns 404 when task does not exist."""
    missing_id = uuid4()
    resp = await http_client.post(
        f"/api/v1/dashboard/tasks/{missing_id}/pr/request-changes",
        json={"body": "Some feedback", "trigger_loopback": False},
    )

    assert resp.status_code == 404
    assert str(missing_id) in resp.json()["detail"]


async def test_request_changes_409_task_has_no_pr(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/request-changes returns 409 when task has no associated PR."""
    row = await _create_published_task(
        session,
        pr_number=None,
        pr_url=None,
        issue_number=301,
    )

    resp = await http_client.post(
        f"/api/v1/dashboard/tasks/{row.id}/pr/request-changes",
        json={"body": "Some feedback", "trigger_loopback": False},
    )

    assert resp.status_code == 409
    assert "no associated pull request" in resp.json()["detail"]


async def test_request_changes_github_auth_error_returns_502(
    http_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /tasks/:id/pr/request-changes returns 502 when GitHub returns 401."""
    row = await _create_published_task(session, pr_number=88, issue_number=302)

    mock_client = _make_github_client_mock(method="post", status_code=401)

    with patch("httpx.AsyncClient", return_value=mock_client):
        resp = await http_client.post(
            f"/api/v1/dashboard/tasks/{row.id}/pr/request-changes",
            json={"body": "Some feedback", "trigger_loopback": False},
        )

    assert resp.status_code == 502
    assert "authentication" in resp.json()["detail"].lower()
