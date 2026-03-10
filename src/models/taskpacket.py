"""TaskPacket model — the durable work record for a single GitHub work item.

Created by Ingress (Story 0.1), enriched by Context Manager (Story 0.3).
Every downstream component reads from and/or updates the TaskPacket.
"""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
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
        Enum(
            TaskPacketStatus,
            name="taskpacket_status",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TaskPacketStatus.RECEIVED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Enrichment fields (Story 0.3 — Context Manager, upgraded in Story 2.1)
    scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_flags: Mapped[dict[str, bool] | None] = mapped_column(JSON, nullable=True)
    # Complexity Index v1: JSONB with score, band, and dimensions
    # See docs/architecture/complexity-index-v1.md
    complexity_index: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    context_packs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Intent fields (Story 0.4 — Intent Builder)
    intent_spec_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    intent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Verification fields (Story 0.6 — Verification Gate)
    loopback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("delivery_id", "repo", name="ix_taskpacket_delivery_repo"),
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
    scope: dict[str, Any] | None = None
    risk_flags: dict[str, bool] | None = None
    # Complexity Index v1: dict with score, band, and dimensions
    complexity_index: dict[str, Any] | None = None
    context_packs: list[dict[str, Any]] | None = None
    intent_spec_id: UUID | None = None
    intent_version: int | None = None
    loopback_count: int = 0
    created_at: datetime
    updated_at: datetime
