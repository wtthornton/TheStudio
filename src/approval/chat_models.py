"""Approval Chat SQLAlchemy models — persistent chat threads for review.

Epic 24 Story 24.2: One chat thread per TaskPacket awaiting approval.
Messages are ordered by created_at. Thread status tracks lifecycle:
active → resolved (on approve/reject) or expired (on timeout).
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class ChatStatus(enum.StrEnum):
    """Lifecycle status of an approval chat thread."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class MessageRole(enum.StrEnum):
    """Role of a chat message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ApprovalChat(Base):
    """A chat thread for a TaskPacket approval review.

    One active chat per TaskPacket (enforced by unique constraint).
    """

    __tablename__ = "approval_chat"
    __table_args__ = (
        UniqueConstraint(
            "taskpacket_id",
            "status",
            name="uq_approval_chat_taskpacket_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4,
    )
    taskpacket_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("taskpacket.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[ChatStatus] = mapped_column(
        Enum(
            ChatStatus,
            name="chat_status",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ChatStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    messages: Mapped[list[ApprovalChatMessage]] = relationship(
        back_populates="chat",
        order_by="ApprovalChatMessage.created_at",
        cascade="all, delete-orphan",
    )


class ApprovalChatMessage(Base):
    """A single message in an approval chat thread."""

    __tablename__ = "approval_chat_message"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4,
    )
    chat_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_chat.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(
            MessageRole,
            name="message_role",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    chat: Mapped[ApprovalChat] = relationship(back_populates="messages")
