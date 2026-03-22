"""Steering audit log — ORM model, Pydantic schema, and CRUD.

Every pipeline steering action (pause / resume / abort / redirect / retry)
is written here so operators can trace the full lifecycle of manual
interventions.

Table: ``steering_audit_log``
Migration: ``src/db/migrations/034_steering_audit_log.py``
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, Index, String, Text, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

# ---------------------------------------------------------------------------
# Action enum
# ---------------------------------------------------------------------------


class SteeringAction(enum.StrEnum):
    """Discrete actions that a steering operator can take on a pipeline task."""

    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"
    REDIRECT = "redirect"
    RETRY = "retry"


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class SteeringAuditLogRow(Base):
    """Persistence row for a single pipeline steering action."""

    __tablename__ = "steering_audit_log"
    __table_args__ = (
        Index("ix_steering_audit_log_task_id", "task_id"),
        Index("ix_steering_audit_log_timestamp", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(
        Enum(SteeringAction, name="steering_action", create_type=True),
        nullable=False,
    )
    from_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    to_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SteeringAuditLogCreate(BaseModel):
    """Input schema for creating a new audit log entry."""

    task_id: UUID
    action: SteeringAction
    from_stage: str | None = Field(None, max_length=100)
    to_stage: str | None = Field(None, max_length=100)
    reason: str | None = Field(None, max_length=2000)
    timestamp: datetime
    actor: str = Field("system", max_length=255)


class SteeringAuditLogRead(BaseModel):
    """Output schema for a steering audit log entry."""

    id: UUID
    task_id: UUID
    action: SteeringAction
    from_stage: str | None
    to_stage: str | None
    reason: str | None
    timestamp: datetime
    actor: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_audit_entry(
    session: AsyncSession,
    entry: SteeringAuditLogCreate,
) -> SteeringAuditLogRead:
    """Persist a new steering audit log entry and return the read schema."""
    row = SteeringAuditLogRow(
        id=uuid4(),
        task_id=entry.task_id,
        action=entry.action,
        from_stage=entry.from_stage,
        to_stage=entry.to_stage,
        reason=entry.reason,
        timestamp=entry.timestamp,
        actor=entry.actor,
    )
    session.add(row)
    await session.flush()
    return SteeringAuditLogRead.model_validate(row)


async def list_audit_entries_for_task(
    session: AsyncSession,
    task_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[SteeringAuditLogRead]:
    """Return steering audit entries for a specific task, newest first."""
    stmt = (
        select(SteeringAuditLogRow)
        .where(SteeringAuditLogRow.task_id == task_id)
        .order_by(SteeringAuditLogRow.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return [SteeringAuditLogRead.model_validate(row) for row in result.scalars()]


async def list_all_audit_entries(
    session: AsyncSession,
    *,
    action: SteeringAction | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SteeringAuditLogRead]:
    """Return all steering audit entries, optionally filtered by action, newest first."""
    stmt = select(SteeringAuditLogRow).order_by(SteeringAuditLogRow.timestamp.desc())
    if action is not None:
        stmt = stmt.where(SteeringAuditLogRow.action == action)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [SteeringAuditLogRead.model_validate(row) for row in result.scalars()]
