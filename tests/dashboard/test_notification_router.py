"""Tests for src/dashboard/notification_router.py.

Covers:
- GET /notifications               — default, unread_only filter, type filter, pagination,
                                     param validation, empty result
- PATCH /notifications/:id/read    — happy path, 404 not found, already-read idempotency,
                                     invalid UUID
- POST /notifications/mark-all-read — count returned, zero case (all already read)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.dashboard.models.notification import (
    NotificationListResponse,
    NotificationRead,
    NotificationType,
)
from src.db.connection import get_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "http://test"
_PATH = "/api/v1/dashboard/notifications"


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_notification(
    *,
    notification_id: UUID | None = None,
    notification_type: NotificationType = NotificationType.GATE_FAIL,
    read: bool = False,
    task_id: UUID | None = None,
) -> NotificationRead:
    """Return a NotificationRead instance with sensible defaults."""
    return NotificationRead(
        id=notification_id or uuid4(),
        type=notification_type,
        title="Test notification",
        message="Something happened in the pipeline.",
        task_id=task_id,
        read=read,
        created_at=datetime.now(UTC),
    )


def _make_list_response(
    items: list[NotificationRead],
    *,
    total: int | None = None,
    unread_count: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    """Return a NotificationListResponse for use as mock return value."""
    return NotificationListResponse(
        items=items,
        total=total if total is not None else len(items),
        unread_count=unread_count if unread_count is not None else sum(1 for n in items if not n.read),
        limit=limit,
        offset=offset,
    )


def _mock_session() -> AsyncMock:
    """Return a mocked AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ===========================================================================
# GET /notifications — list endpoint
# ===========================================================================


@pytest.mark.asyncio
async def test_list_default_returns_all_notifications(no_dashboard_auth: None) -> None:
    """GET /notifications without filters returns paginated list of all notifications."""
    items = [
        _make_notification(read=False),
        _make_notification(read=True, notification_type=NotificationType.COST_UPDATE),
    ]
    response_data = _make_list_response(items, unread_count=1)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(_PATH)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 2
    assert body["unread_count"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    mock_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_unread_only_true_forwarded(no_dashboard_auth: None) -> None:
    """?unread_only=true passes unread_only=True to list_notifications."""
    items = [_make_notification(read=False)]
    response_data = _make_list_response(items, unread_count=1)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?unread_only=true")

    assert resp.status_code == 200
    assert mock_list.call_args.kwargs["unread_only"] is True


@pytest.mark.asyncio
async def test_list_unread_only_false_is_default(no_dashboard_auth: None) -> None:
    """?unread_only=false (the default) passes unread_only=False to list_notifications."""
    response_data = _make_list_response([])

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(_PATH)

    assert resp.status_code == 200
    assert mock_list.call_args.kwargs["unread_only"] is False


@pytest.mark.asyncio
async def test_list_type_filter_cost_update(no_dashboard_auth: None) -> None:
    """?notification_type=cost_update sets type_filter on list_notifications call."""
    items = [_make_notification(notification_type=NotificationType.COST_UPDATE)]
    response_data = _make_list_response(items)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?notification_type=cost_update")

    assert resp.status_code == 200
    assert mock_list.call_args.kwargs["type_filter"] == NotificationType.COST_UPDATE


@pytest.mark.asyncio
async def test_list_type_filter_all_valid_types(no_dashboard_auth: None) -> None:
    """All four NotificationType values are accepted by the type filter param."""
    response_data = _make_list_response([])

    valid_types = [
        "gate_fail",
        "cost_update",
        "steering_action",
        "trust_tier_assigned",
    ]
    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            for nt in valid_types:
                resp = await client.get(f"{_PATH}?notification_type={nt}")
                assert resp.status_code == 200, f"Expected 200 for type={nt}, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_invalid_type_filter_rejected(no_dashboard_auth: None) -> None:
    """?notification_type=unknown_event is rejected with 422."""
    with patch("src.dashboard.notification_router.list_notifications"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?notification_type=unknown_event")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_pagination_limit_and_offset_forwarded(no_dashboard_auth: None) -> None:
    """?limit=10&offset=20 is forwarded correctly to list_notifications."""
    response_data = _make_list_response([], total=100, unread_count=5, limit=10, offset=20)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?limit=10&offset=20")

    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 10
    assert body["offset"] == 20
    kwargs = mock_list.call_args.kwargs
    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 20


@pytest.mark.asyncio
async def test_list_limit_too_large_rejected(no_dashboard_auth: None) -> None:
    """?limit=201 exceeds max=200 and is rejected with 422."""
    with patch("src.dashboard.notification_router.list_notifications"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?limit=201")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_limit_zero_rejected(no_dashboard_auth: None) -> None:
    """?limit=0 violates ge=1 constraint and is rejected with 422."""
    with patch("src.dashboard.notification_router.list_notifications"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?limit=0")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_limit_max_accepted(no_dashboard_auth: None) -> None:
    """?limit=200 (boundary max) is accepted."""
    response_data = _make_list_response([], limit=200)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?limit=200")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_negative_offset_rejected(no_dashboard_auth: None) -> None:
    """?offset=-1 violates ge=0 constraint and is rejected with 422."""
    with patch("src.dashboard.notification_router.list_notifications"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}?offset=-1")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_empty_result(no_dashboard_auth: None) -> None:
    """GET /notifications with empty DB returns empty items list and zero counts."""
    response_data = _make_list_response([], total=0, unread_count=0)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(_PATH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_response_item_shape(no_dashboard_auth: None) -> None:
    """Each notification item has the expected fields."""
    task_id = uuid4()
    items = [
        _make_notification(
            notification_type=NotificationType.STEERING_ACTION,
            task_id=task_id,
            read=False,
        )
    ]
    response_data = _make_list_response(items, unread_count=1)

    with patch(
        "src.dashboard.notification_router.list_notifications",
        AsyncMock(return_value=response_data),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(_PATH)

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "id" in item
    assert item["type"] == "steering_action"
    assert item["title"] == "Test notification"
    assert item["message"] == "Something happened in the pipeline."
    assert item["task_id"] == str(task_id)
    assert item["read"] is False
    assert "created_at" in item


# ===========================================================================
# PATCH /notifications/:id/read — mark single notification as read
# ===========================================================================


@pytest.mark.asyncio
async def test_mark_read_happy_path(no_dashboard_auth: None) -> None:
    """PATCH /{id}/read returns 200 with the updated NotificationRead (read=True)."""
    notification_id = uuid4()
    updated = _make_notification(notification_id=notification_id, read=True)

    with patch(
        "src.dashboard.notification_router.mark_notification_read",
        AsyncMock(return_value=updated),
    ) as mock_mark:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.patch(f"{_PATH}/{notification_id}/read")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(notification_id)
    assert body["read"] is True
    mock_mark.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_read_not_found_returns_404(no_dashboard_auth: None) -> None:
    """PATCH /{id}/read returns 404 when the notification ID does not exist."""
    notification_id = uuid4()

    with patch(
        "src.dashboard.notification_router.mark_notification_read",
        AsyncMock(return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.patch(f"{_PATH}/{notification_id}/read")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mark_read_already_read_is_idempotent(no_dashboard_auth: None) -> None:
    """PATCH /{id}/read on an already-read notification returns 200 unchanged."""
    notification_id = uuid4()
    already_read = _make_notification(notification_id=notification_id, read=True)

    with patch(
        "src.dashboard.notification_router.mark_notification_read",
        AsyncMock(return_value=already_read),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.patch(f"{_PATH}/{notification_id}/read")

    assert resp.status_code == 200
    assert resp.json()["read"] is True


@pytest.mark.asyncio
async def test_mark_read_invalid_uuid_rejected(no_dashboard_auth: None) -> None:
    """PATCH /not-a-uuid/read is rejected with 422 (UUID path param validation)."""
    with patch("src.dashboard.notification_router.mark_notification_read"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.patch(f"{_PATH}/not-a-uuid/read")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_mark_read_response_shape(no_dashboard_auth: None) -> None:
    """PATCH /{id}/read response contains all NotificationRead fields."""
    notification_id = uuid4()
    task_id = uuid4()
    updated = _make_notification(
        notification_id=notification_id,
        notification_type=NotificationType.TRUST_TIER_ASSIGNED,
        read=True,
        task_id=task_id,
    )

    with patch(
        "src.dashboard.notification_router.mark_notification_read",
        AsyncMock(return_value=updated),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.patch(f"{_PATH}/{notification_id}/read")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(notification_id)
    assert body["type"] == "trust_tier_assigned"
    assert body["task_id"] == str(task_id)
    assert body["read"] is True
    assert "created_at" in body
    assert "title" in body
    assert "message" in body


# ===========================================================================
# POST /notifications/mark-all-read
# ===========================================================================


@pytest.mark.asyncio
async def test_mark_all_read_returns_updated_count(no_dashboard_auth: None) -> None:
    """POST /mark-all-read returns {'updated': N} with count of newly read notifications."""
    with patch(
        "src.dashboard.notification_router.mark_all_notifications_read",
        AsyncMock(return_value=5),
    ) as mock_all:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.post(f"{_PATH}/mark-all-read")

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"updated": 5}
    mock_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_all_read_zero_when_none_unread(no_dashboard_auth: None) -> None:
    """POST /mark-all-read returns 0 when all notifications are already read."""
    with patch(
        "src.dashboard.notification_router.mark_all_notifications_read",
        AsyncMock(return_value=0),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.post(f"{_PATH}/mark-all-read")

    assert resp.status_code == 200
    assert resp.json()["updated"] == 0


@pytest.mark.asyncio
async def test_mark_all_read_response_structure(no_dashboard_auth: None) -> None:
    """POST /mark-all-read response has exactly the 'updated' key."""
    with patch(
        "src.dashboard.notification_router.mark_all_notifications_read",
        AsyncMock(return_value=3),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.post(f"{_PATH}/mark-all-read")

    assert resp.status_code == 200
    body = resp.json()
    assert list(body.keys()) == ["updated"]
    assert isinstance(body["updated"], int)
