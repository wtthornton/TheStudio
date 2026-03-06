"""Unit tests for TaskPacket model validation (Story 0.2)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.taskpacket import (
    ALLOWED_TRANSITIONS,
    TaskPacketCreate,
    TaskPacketRead,
    TaskPacketStatus,
)


class TestTaskPacketCreate:
    def test_valid_create(self) -> None:
        data = TaskPacketCreate(repo="owner/repo", issue_id=42, delivery_id="abc-123")
        assert data.repo == "owner/repo"
        assert data.issue_id == 42
        assert data.delivery_id == "abc-123"
        assert data.correlation_id is not None

    def test_create_with_explicit_correlation_id(self) -> None:
        cid = uuid4()
        data = TaskPacketCreate(
            repo="owner/repo", issue_id=1, delivery_id="def-456", correlation_id=cid
        )
        assert data.correlation_id == cid

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            TaskPacketCreate()  # type: ignore[call-arg]

    def test_missing_repo(self) -> None:
        with pytest.raises(ValidationError):
            TaskPacketCreate(issue_id=1, delivery_id="x")  # type: ignore[call-arg]


class TestTaskPacketRead:
    def test_from_attributes(self) -> None:
        """Verify from_attributes works for ORM model mapping."""

        class FakeRow:
            id = uuid4()
            repo = "owner/repo"
            issue_id = 1
            delivery_id = "abc"
            correlation_id = uuid4()
            status = TaskPacketStatus.RECEIVED
            created_at = "2026-01-01T00:00:00+00:00"
            updated_at = "2026-01-01T00:00:00+00:00"

        result = TaskPacketRead.model_validate(FakeRow(), from_attributes=True)
        assert result.id == FakeRow.id
        assert result.status == TaskPacketStatus.RECEIVED


class TestStatusTransitions:
    def test_received_can_transition_to_enriched(self) -> None:
        assert TaskPacketStatus.ENRICHED in ALLOWED_TRANSITIONS[TaskPacketStatus.RECEIVED]

    def test_received_cannot_transition_to_published(self) -> None:
        assert TaskPacketStatus.PUBLISHED not in ALLOWED_TRANSITIONS[TaskPacketStatus.RECEIVED]

    def test_published_is_terminal(self) -> None:
        assert len(ALLOWED_TRANSITIONS[TaskPacketStatus.PUBLISHED]) == 0

    def test_failed_is_terminal(self) -> None:
        assert len(ALLOWED_TRANSITIONS[TaskPacketStatus.FAILED]) == 0

    def test_verification_failed_can_loopback(self) -> None:
        assert (
            TaskPacketStatus.IN_PROGRESS
            in ALLOWED_TRANSITIONS[TaskPacketStatus.VERIFICATION_FAILED]
        )

    def test_all_statuses_have_transitions_defined(self) -> None:
        for status in TaskPacketStatus:
            assert status in ALLOWED_TRANSITIONS

    def test_all_non_terminal_can_fail(self) -> None:
        terminal = {TaskPacketStatus.PUBLISHED, TaskPacketStatus.FAILED}
        for status in TaskPacketStatus:
            if status not in terminal:
                assert TaskPacketStatus.FAILED in ALLOWED_TRANSITIONS[status]

    def test_invalid_status_value(self) -> None:
        with pytest.raises(ValueError, match="nonexistent"):
            TaskPacketStatus("nonexistent")
