"""Pydantic model validation tests for notification models.

Tests cover:
- NotificationType enum values
- NotificationCreate required fields, max_length constraint
- NotificationRead from_attributes ORM loading
- NotificationListResponse construction and field types
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.dashboard.models.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationRead,
    NotificationType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)
_NOTIFICATION_ID = uuid4()
_TASK_ID = uuid4()


def _make_notification_row(**overrides: Any) -> MagicMock:
    """Return a MagicMock suitable for NotificationRead.model_validate."""
    row = MagicMock()
    row.id = overrides.get("id", _NOTIFICATION_ID)
    row.type = overrides.get("type", NotificationType.GATE_FAIL)
    row.title = overrides.get("title", "Gate failed")
    row.message = overrides.get("message", "Verification gate failed for task.")
    row.task_id = overrides.get("task_id", _TASK_ID)
    row.read = overrides.get("read", False)
    row.created_at = overrides.get("created_at", _NOW)
    return row


def _make_notification_read(**overrides: Any) -> NotificationRead:
    return NotificationRead(
        id=overrides.get("id", _NOTIFICATION_ID),
        type=overrides.get("type", NotificationType.GATE_FAIL),
        title=overrides.get("title", "Gate failed"),
        message=overrides.get("message", "Verification gate failed."),
        task_id=overrides.get("task_id", _TASK_ID),
        read=overrides.get("read", False),
        created_at=overrides.get("created_at", _NOW),
    )


# ---------------------------------------------------------------------------
# NotificationType enum
# ---------------------------------------------------------------------------


class TestNotificationTypeEnum:
    def test_all_four_values(self) -> None:
        expected = {"gate_fail", "cost_update", "steering_action", "trust_tier_assigned"}
        assert {t.value for t in NotificationType} == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(NotificationType.GATE_FAIL, str)

    def test_each_member(self) -> None:
        assert NotificationType.GATE_FAIL == "gate_fail"
        assert NotificationType.COST_UPDATE == "cost_update"
        assert NotificationType.STEERING_ACTION == "steering_action"
        assert NotificationType.TRUST_TIER_ASSIGNED == "trust_tier_assigned"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            NotificationType("unknown_event")


# ---------------------------------------------------------------------------
# NotificationCreate
# ---------------------------------------------------------------------------


class TestNotificationCreate:
    def test_happy_path_required_only(self) -> None:
        create = NotificationCreate(
            type=NotificationType.GATE_FAIL,
            title="Gate failed",
            message="Verification gate failed.",
        )
        assert create.type == NotificationType.GATE_FAIL
        assert create.title == "Gate failed"
        assert create.message == "Verification gate failed."

    def test_task_id_optional_defaults_none(self) -> None:
        create = NotificationCreate(
            type=NotificationType.COST_UPDATE,
            title="Cost update",
            message="Spend exceeded threshold.",
        )
        assert create.task_id is None

    def test_task_id_provided(self) -> None:
        create = NotificationCreate(
            type=NotificationType.STEERING_ACTION,
            title="Task paused",
            message="Task was paused by operator.",
            task_id=_TASK_ID,
        )
        assert create.task_id == _TASK_ID

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationCreate(title="x", message="y")  # type: ignore[call-arg]

    def test_missing_title_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationCreate(type=NotificationType.GATE_FAIL, message="y")  # type: ignore[call-arg]

    def test_missing_message_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationCreate(type=NotificationType.GATE_FAIL, title="x")  # type: ignore[call-arg]

    def test_title_max_length_500(self) -> None:
        title_500 = "t" * 500
        create = NotificationCreate(
            type=NotificationType.GATE_FAIL,
            title=title_500,
            message="msg",
        )
        assert len(create.title) == 500

    def test_title_exceeds_500_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationCreate(
                type=NotificationType.GATE_FAIL,
                title="t" * 501,
                message="msg",
            )

    def test_all_notification_types_accepted(self) -> None:
        for ntype in NotificationType:
            create = NotificationCreate(
                type=ntype,
                title="Title",
                message="Message",
            )
            assert create.type == ntype

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationCreate(
                type="unknown",  # type: ignore[arg-type]
                title="x",
                message="y",
            )

    def test_message_accepts_long_text(self) -> None:
        long_message = "word " * 1000
        create = NotificationCreate(
            type=NotificationType.COST_UPDATE,
            title="Long message",
            message=long_message,
        )
        assert len(create.message) > 0


# ---------------------------------------------------------------------------
# NotificationRead
# ---------------------------------------------------------------------------


class TestNotificationRead:
    def test_direct_construction(self) -> None:
        read = _make_notification_read()
        assert read.id == _NOTIFICATION_ID
        assert read.type == NotificationType.GATE_FAIL
        assert read.read is False

    def test_from_attributes_orm_row(self) -> None:
        row = _make_notification_row()
        read = NotificationRead.model_validate(row)
        assert read.id == _NOTIFICATION_ID
        assert read.type == NotificationType.GATE_FAIL
        assert read.title == "Gate failed"
        assert read.message == "Verification gate failed for task."
        assert read.task_id == _TASK_ID
        assert read.read is False
        assert read.created_at == _NOW

    def test_from_attributes_read_true(self) -> None:
        row = _make_notification_row(read=True)
        read = NotificationRead.model_validate(row)
        assert read.read is True

    def test_from_attributes_null_task_id(self) -> None:
        row = _make_notification_row(task_id=None)
        read = NotificationRead.model_validate(row)
        assert read.task_id is None

    def test_from_attributes_all_notification_types(self) -> None:
        for ntype in NotificationType:
            row = _make_notification_row(type=ntype)
            read = NotificationRead.model_validate(row)
            assert read.type == ntype

    def test_model_config_from_attributes(self) -> None:
        assert NotificationRead.model_config.get("from_attributes") is True

    def test_uuid_fields_are_uuid_type(self) -> None:
        row = _make_notification_row()
        read = NotificationRead.model_validate(row)
        assert isinstance(read.id, UUID)
        assert isinstance(read.task_id, UUID)

    def test_uuid_task_id_none(self) -> None:
        row = _make_notification_row(task_id=None)
        read = NotificationRead.model_validate(row)
        assert read.task_id is None


# ---------------------------------------------------------------------------
# NotificationListResponse
# ---------------------------------------------------------------------------


class TestNotificationListResponse:
    def test_empty_items(self) -> None:
        response = NotificationListResponse(
            items=[],
            total=0,
            unread_count=0,
            limit=50,
            offset=0,
        )
        assert response.items == []
        assert response.total == 0
        assert response.unread_count == 0

    def test_with_items(self) -> None:
        items = [_make_notification_read(), _make_notification_read(id=uuid4(), read=True)]
        response = NotificationListResponse(
            items=items,
            total=10,
            unread_count=1,
            limit=2,
            offset=0,
        )
        assert len(response.items) == 2
        assert response.total == 10
        assert response.unread_count == 1
        assert response.limit == 2
        assert response.offset == 0

    def test_missing_items_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationListResponse(  # type: ignore[call-arg]
                total=0,
                unread_count=0,
                limit=50,
                offset=0,
            )

    def test_missing_total_raises(self) -> None:
        with pytest.raises(ValidationError):
            NotificationListResponse(  # type: ignore[call-arg]
                items=[],
                unread_count=0,
                limit=50,
                offset=0,
            )

    def test_pagination_fields(self) -> None:
        response = NotificationListResponse(
            items=[],
            total=100,
            unread_count=5,
            limit=20,
            offset=40,
        )
        assert response.limit == 20
        assert response.offset == 40

    def test_items_are_notification_read_instances(self) -> None:
        item = _make_notification_read()
        response = NotificationListResponse(
            items=[item],
            total=1,
            unread_count=1,
            limit=50,
            offset=0,
        )
        assert isinstance(response.items[0], NotificationRead)
