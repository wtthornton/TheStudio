"""Tests for GET /api/v1/dashboard/tasks endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRow, TaskPacketStatus


def _make_row(**overrides) -> MagicMock:
    """Build a mock TaskPacketRow with sensible defaults."""
    now = datetime.now(UTC)
    defaults = {
        "id": uuid4(),
        "repo": "owner/repo",
        "issue_id": 1,
        "delivery_id": "d-1",
        "correlation_id": uuid4(),
        "source_name": "github",
        "status": TaskPacketStatus.RECEIVED,
        "created_at": now,
        "updated_at": now,
        "scope": None,
        "risk_flags": None,
        "complexity_index": None,
        "context_packs": None,
        "intent_spec_id": None,
        "intent_version": None,
        "readiness_evaluation_count": 0,
        "readiness_hold_comment_id": None,
        "readiness_score": None,
        "readiness_miss": False,
        "stage_timings": None,
        "loopback_count": 0,
    }
    defaults.update(overrides)
    row = MagicMock(spec=TaskPacketRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _mock_session(rows: list, total: int = 0):
    """Return a mock AsyncSession that returns *rows* for scalars and *total* for count."""
    session = AsyncMock()

    # Track call order to return count first, then rows
    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # First call is the count query
            result.scalar_one.return_value = total
        else:
            # Second call is the data query
            result.scalars.return_value.all.return_value = rows
        return result

    session.execute = _execute
    return session


@pytest.fixture
def _no_auth(monkeypatch):
    """Disable dashboard auth for tests."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_no_auth")
async def test_list_tasks_empty():
    """Empty DB returns zero items."""
    session = _mock_session(rows=[], total=0)
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard/tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["offset"] == 0
        assert body["limit"] == 20
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
@pytest.mark.usefixtures("_no_auth")
async def test_list_tasks_with_results():
    """Returns serialized TaskPackets with pagination metadata."""
    rows = [_make_row(issue_id=i) for i in range(3)]
    session = _mock_session(rows=rows, total=3)
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard/tasks?offset=0&limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["total"] == 3
        assert body["limit"] == 10
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_tasks_requires_auth(monkeypatch):
    """Returns 401 when dashboard_token is set and no token provided."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "secret123")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/dashboard/tasks")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tasks_auth_valid(monkeypatch):
    """Returns 200 when correct token is supplied."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "secret123")
    session = _mock_session(rows=[], total=0)
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard/tasks?token=secret123")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)
