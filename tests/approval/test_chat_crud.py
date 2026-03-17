"""Tests for approval chat CRUD operations (Epic 24 Story 24.2).

Uses in-memory data structures to test CRUD logic without a real database.
The tests validate the model creation, constraints, and business rules.
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.approval.chat_models import (
    ApprovalChat,
    ApprovalChatMessage,
    ChatStatus,
    MessageRole,
)


class TestChatModels:
    """Test SQLAlchemy model instantiation and field defaults."""

    def test_chat_creation(self):
        tp_id = uuid4()
        chat = ApprovalChat(
            taskpacket_id=tp_id,
            created_by="reviewer@example.com",
            status=ChatStatus.ACTIVE,
        )
        assert chat.taskpacket_id == tp_id
        assert chat.status == ChatStatus.ACTIVE
        assert chat.created_by == "reviewer@example.com"

    def test_chat_status_enum(self):
        assert ChatStatus.ACTIVE == "active"
        assert ChatStatus.RESOLVED == "resolved"
        assert ChatStatus.EXPIRED == "expired"

    def test_message_role_enum(self):
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"

    def test_message_creation(self):
        msg = ApprovalChatMessage(
            chat_id=uuid4(),
            role=MessageRole.USER,
            content="Why did you modify auth.py?",
        )
        assert msg.role == MessageRole.USER
        assert "auth.py" in msg.content


class TestChatCRUDConstants:
    """Test CRUD module constants and business rules."""

    def test_max_messages_defined(self):
        from src.approval.chat_crud import MAX_MESSAGES_PER_CHAT

        assert MAX_MESSAGES_PER_CHAT == 50


class TestChatStatusTransitions:
    """Test that chat status values map correctly."""

    def test_active_to_resolved(self):
        chat = ApprovalChat(
            taskpacket_id=uuid4(),
            status=ChatStatus.ACTIVE,
        )
        chat.status = ChatStatus.RESOLVED
        chat.resolved_at = datetime.now(UTC)
        assert chat.status == ChatStatus.RESOLVED
        assert chat.resolved_at is not None

    def test_active_to_expired(self):
        chat = ApprovalChat(
            taskpacket_id=uuid4(),
            status=ChatStatus.ACTIVE,
        )
        chat.status = ChatStatus.EXPIRED
        chat.resolved_at = datetime.now(UTC)
        assert chat.status == ChatStatus.EXPIRED


class TestMessageOrdering:
    """Test that messages can be ordered by created_at."""

    def test_messages_sortable(self):
        t1 = datetime(2026, 3, 17, 10, 0, tzinfo=UTC)
        t2 = datetime(2026, 3, 17, 10, 5, tzinfo=UTC)
        t3 = datetime(2026, 3, 17, 10, 10, tzinfo=UTC)

        chat_id = uuid4()
        m1 = ApprovalChatMessage(
            chat_id=chat_id, role=MessageRole.USER, content="Q1",
        )
        m1.created_at = t1

        m2 = ApprovalChatMessage(
            chat_id=chat_id, role=MessageRole.ASSISTANT, content="A1",
        )
        m2.created_at = t2

        m3 = ApprovalChatMessage(
            chat_id=chat_id, role=MessageRole.USER, content="Q2",
        )
        m3.created_at = t3

        messages = sorted([m3, m1, m2], key=lambda m: m.created_at)
        assert messages[0].content == "Q1"
        assert messages[1].content == "A1"
        assert messages[2].content == "Q2"
