"""TaskPacket model — the durable work record for a single GitHub work item.

Created by Ingress (Story 0.1), enriched by Context Manager (Story 0.3).
Every downstream component reads from and/or updates the TaskPacket.
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class TaskPacketStatus(enum.StrEnum):
    """Valid status values for a TaskPacket."""

    RECEIVED = "received"
    ENRICHED = "enriched"
    INTENT_BUILT = "intent_built"
    IN_PROGRESS = "in_progress"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    PUBLISHED = "published"
    FAILED = "failed"


# Allowed status transitions. Key = current status, value = set of valid next statuses.
ALLOWED_TRANSITIONS: dict[TaskPacketStatus, set[TaskPacketStatus]] = {
    TaskPacketStatus.RECEIVED: {TaskPacketStatus.ENRICHED, TaskPacketStatus.FAILED},
    TaskPacketStatus.ENRICHED: {TaskPacketStatus.INTENT_BUILT, TaskPacketStatus.FAILED},
    TaskPacketStatus.INTENT_BUILT: {TaskPacketStatus.IN_PROGRESS, TaskPacketStatus.FAILED},
    TaskPacketStatus.IN_PROGRESS: {
        TaskPacketStatus.VERIFICATION_PASSED,
        TaskPacketStatus.VERIFICATION_FAILED,
        TaskPacketStatus.FAILED,
    },
    TaskPacketStatus.VERIFICATION_PASSED: {TaskPacketStatus.PUBLISHED, TaskPacketStatus.FAILED},
    TaskPacketStatus.VERIFICATION_FAILED: {
        TaskPacketStatus.IN_PROGRESS,  # loopback
        TaskPacketStatus.FAILED,
    },
    TaskPacketStatus.PUBLISHED: set(),
    TaskPacketStatus.FAILED: set(),
}


class TaskPacketRow(Base):
    """SQLAlchemy ORM model for the taskpacket table."""

    __tablename__ = "taskpacket"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_id: Mapped[int] = mapped_column(nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    status: Mapped[TaskPacketStatus] = mapped_column(
        Enum(TaskPacketStatus, name="taskpacket_status", create_constraint=True),
        nullable=False,
        default=TaskPacketStatus.RECEIVED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        # Dedupe index: (delivery_id, repo) must be unique
        {"comment": "TaskPacket — durable work record"},
    )


class TaskPacketCreate(BaseModel):
    """Pydantic model for TaskPacket creation input."""

    repo: str
    issue_id: int
    delivery_id: str
    correlation_id: UUID = Field(default_factory=uuid4)


class TaskPacketRead(BaseModel):
    """Pydantic model for TaskPacket read output."""

    model_config = {"from_attributes": True}

    id: UUID
    repo: str
    issue_id: int
    delivery_id: str
    correlation_id: UUID
    status: TaskPacketStatus
    created_at: datetime
    updated_at: datetime
