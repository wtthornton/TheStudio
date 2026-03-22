"""Pydantic model validation tests for steering audit models.

Tests cover:
- SteeringAction enum values
- SteeringAuditLogCreate required/optional fields, max_length constraints
- SteeringAuditLogRead from_attributes ORM loading
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.dashboard.models.steering_audit import (
    SteeringAction,
    SteeringAuditLogCreate,
    SteeringAuditLogRead,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)
_TASK_ID = uuid4()
_ENTRY_ID = uuid4()


def _make_orm_row(**overrides: object) -> MagicMock:
    """Return a MagicMock that passes from_attributes validation for SteeringAuditLogRead."""
    row = MagicMock()
    row.id = overrides.get("id", _ENTRY_ID)
    row.task_id = overrides.get("task_id", _TASK_ID)
    row.action = overrides.get("action", SteeringAction.PAUSE)
    row.from_stage = overrides.get("from_stage", None)
    row.to_stage = overrides.get("to_stage", None)
    row.reason = overrides.get("reason", None)
    row.timestamp = overrides.get("timestamp", _NOW)
    row.actor = overrides.get("actor", "system")
    return row


# ---------------------------------------------------------------------------
# SteeringAction enum
# ---------------------------------------------------------------------------


class TestSteeringActionEnum:
    def test_all_values_present(self) -> None:
        expected = {"pause", "resume", "abort", "redirect", "retry",
                    "trust_tier_assigned", "trust_tier_overridden"}
        actual = {a.value for a in SteeringAction}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(SteeringAction.PAUSE, str)
        assert SteeringAction.PAUSE == "pause"

    def test_each_member_accessible(self) -> None:
        assert SteeringAction.PAUSE == "pause"
        assert SteeringAction.RESUME == "resume"
        assert SteeringAction.ABORT == "abort"
        assert SteeringAction.REDIRECT == "redirect"
        assert SteeringAction.RETRY == "retry"
        assert SteeringAction.TRUST_TIER_ASSIGNED == "trust_tier_assigned"
        assert SteeringAction.TRUST_TIER_OVERRIDDEN == "trust_tier_overridden"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            SteeringAction("unknown_action")


# ---------------------------------------------------------------------------
# SteeringAuditLogCreate
# ---------------------------------------------------------------------------


class TestSteeringAuditLogCreate:
    def test_happy_path_required_only(self) -> None:
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.PAUSE,
            timestamp=_NOW,
        )
        assert entry.task_id == _TASK_ID
        assert entry.action == SteeringAction.PAUSE
        assert entry.timestamp == _NOW

    def test_optional_fields_default_to_none(self) -> None:
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.RESUME,
            timestamp=_NOW,
        )
        assert entry.from_stage is None
        assert entry.to_stage is None
        assert entry.reason is None

    def test_actor_default(self) -> None:
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.ABORT,
            timestamp=_NOW,
        )
        assert entry.actor == "system"

    def test_actor_custom(self) -> None:
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.ABORT,
            timestamp=_NOW,
            actor="admin@example.com",
        )
        assert entry.actor == "admin@example.com"

    def test_missing_task_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(action=SteeringAction.PAUSE, timestamp=_NOW)  # type: ignore[call-arg]

    def test_missing_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(task_id=_TASK_ID, timestamp=_NOW)  # type: ignore[call-arg]

    def test_missing_timestamp_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(task_id=_TASK_ID, action=SteeringAction.PAUSE)  # type: ignore[call-arg]

    def test_from_stage_max_length(self) -> None:
        # Exactly 100 characters — valid
        stage_100 = "x" * 100
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.REDIRECT,
            timestamp=_NOW,
            from_stage=stage_100,
        )
        assert len(entry.from_stage) == 100  # type: ignore[arg-type]

    def test_from_stage_exceeds_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action=SteeringAction.REDIRECT,
                timestamp=_NOW,
                from_stage="x" * 101,
            )

    def test_to_stage_max_length(self) -> None:
        stage_100 = "y" * 100
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.REDIRECT,
            timestamp=_NOW,
            to_stage=stage_100,
        )
        assert len(entry.to_stage) == 100  # type: ignore[arg-type]

    def test_to_stage_exceeds_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action=SteeringAction.REDIRECT,
                timestamp=_NOW,
                to_stage="y" * 101,
            )

    def test_reason_max_length(self) -> None:
        reason_2000 = "r" * 2000
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.RETRY,
            timestamp=_NOW,
            reason=reason_2000,
        )
        assert len(entry.reason) == 2000  # type: ignore[arg-type]

    def test_reason_exceeds_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action=SteeringAction.RETRY,
                timestamp=_NOW,
                reason="r" * 2001,
            )

    def test_actor_max_length(self) -> None:
        actor_255 = "a" * 255
        entry = SteeringAuditLogCreate(
            task_id=_TASK_ID,
            action=SteeringAction.PAUSE,
            timestamp=_NOW,
            actor=actor_255,
        )
        assert len(entry.actor) == 255

    def test_actor_exceeds_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action=SteeringAction.PAUSE,
                timestamp=_NOW,
                actor="a" * 256,
            )

    def test_invalid_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action="not_an_action",  # type: ignore[arg-type]
                timestamp=_NOW,
            )

    def test_all_steering_actions_accepted(self) -> None:
        for action in SteeringAction:
            entry = SteeringAuditLogCreate(
                task_id=_TASK_ID,
                action=action,
                timestamp=_NOW,
            )
            assert entry.action == action


# ---------------------------------------------------------------------------
# SteeringAuditLogRead
# ---------------------------------------------------------------------------


class TestSteeringAuditLogRead:
    def test_direct_construction(self) -> None:
        read = SteeringAuditLogRead(
            id=_ENTRY_ID,
            task_id=_TASK_ID,
            action=SteeringAction.PAUSE,
            from_stage=None,
            to_stage=None,
            reason=None,
            timestamp=_NOW,
            actor="system",
        )
        assert read.id == _ENTRY_ID
        assert read.action == SteeringAction.PAUSE

    def test_from_attributes_orm_row(self) -> None:
        row = _make_orm_row(action=SteeringAction.REDIRECT, from_stage="intake", to_stage="context")
        read = SteeringAuditLogRead.model_validate(row)
        assert read.id == _ENTRY_ID
        assert read.task_id == _TASK_ID
        assert read.action == SteeringAction.REDIRECT
        assert read.from_stage == "intake"
        assert read.to_stage == "context"
        assert read.actor == "system"

    def test_from_attributes_with_reason(self) -> None:
        row = _make_orm_row(reason="Manual intervention for testing", actor="operator")
        read = SteeringAuditLogRead.model_validate(row)
        assert read.reason == "Manual intervention for testing"
        assert read.actor == "operator"

    def test_from_attributes_null_optional_fields(self) -> None:
        row = _make_orm_row(from_stage=None, to_stage=None, reason=None)
        read = SteeringAuditLogRead.model_validate(row)
        assert read.from_stage is None
        assert read.to_stage is None
        assert read.reason is None

    def test_model_config_from_attributes_true(self) -> None:
        assert SteeringAuditLogRead.model_config.get("from_attributes") is True

    def test_uuid_fields_are_uuid_type(self) -> None:
        row = _make_orm_row()
        read = SteeringAuditLogRead.model_validate(row)
        assert isinstance(read.id, UUID)
        assert isinstance(read.task_id, UUID)

    def test_each_action_round_trips(self) -> None:
        for action in SteeringAction:
            row = _make_orm_row(action=action)
            read = SteeringAuditLogRead.model_validate(row)
            assert read.action == action
