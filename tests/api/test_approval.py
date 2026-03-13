"""Unit tests for the approval API endpoint (Epic 21, Story 7)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.models.taskpacket import TaskPacketStatus


def _make_taskpacket_read(tp_status: TaskPacketStatus, task_id=None):
    """Create a minimal TaskPacketRead-like object for mocking."""
    from datetime import UTC, datetime
    from uuid import uuid4 as _uuid4

    from src.models.taskpacket import TaskPacketRead

    tid = task_id or _uuid4()
    return TaskPacketRead(
        id=tid,
        repo="owner/repo",
        issue_id=1,
        delivery_id="delivery-1",
        correlation_id=_uuid4(),
        status=tp_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_approve_returns_200_for_awaiting_task():
    """POST /api/tasks/{id}/approve returns 200 for a task in AWAITING_APPROVAL."""
    task_id = str(uuid4())
    tp = _make_taskpacket_read(TaskPacketStatus.AWAITING_APPROVAL)

    with (
        patch("src.api.approval.get_by_id", new_callable=AsyncMock, return_value=tp),
        patch("src.api.approval._send_approval_signal", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/tasks/{task_id}/approve",
                json={"approved_by": "admin@test.com"},
                headers={"X-User-ID": "test-user"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["taskpacket_id"] == task_id


@pytest.mark.asyncio
async def test_approve_returns_404_for_unknown_task():
    """POST /api/tasks/{id}/approve returns 404 when TaskPacket not found."""
    task_id = str(uuid4())

    with patch("src.api.approval.get_by_id", new_callable=AsyncMock, return_value=None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/tasks/{task_id}/approve",
                json={"approved_by": "admin@test.com"},
                headers={"X-User-ID": "test-user"},
            )

        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_returns_409_for_wrong_status():
    """POST /api/tasks/{id}/approve returns 409 when task is not awaiting approval."""
    task_id = str(uuid4())
    tp = _make_taskpacket_read(TaskPacketStatus.RECEIVED)

    with patch("src.api.approval.get_by_id", new_callable=AsyncMock, return_value=tp):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/tasks/{task_id}/approve",
                json={"approved_by": "admin@test.com"},
                headers={"X-User-ID": "test-user"},
            )

        assert resp.status_code == 409
        assert "not awaiting approval" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_approve_idempotent_for_published_task():
    """POST /api/tasks/{id}/approve returns 200 for already-published task."""
    task_id = str(uuid4())
    tp = _make_taskpacket_read(TaskPacketStatus.PUBLISHED)

    with patch("src.api.approval.get_by_id", new_callable=AsyncMock, return_value=tp):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/tasks/{task_id}/approve",
                json={"approved_by": "admin@test.com"},
                headers={"X-User-ID": "test-user"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
