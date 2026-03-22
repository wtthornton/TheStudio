"""Notification data model — ORM model, Pydantic schema, and CRUD.

Notifications are generated from NATS pipeline events and surfaced to
operators via the NotificationBell in the dashboard.

Table: ``notifications``
Migration: ``src/db/migrations/040_notifications.py``
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text, Uuid, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

# ---------------------------------------------------------------------------
# Notification type enum
# ---------------------------------------------------------------------------


class NotificationType(enum.StrEnum):
    """Pipeline event types that generate user-visible notifications."""

    GATE_FAIL = "gate_fail"
    COST_UPDATE = "cost_update"
    STEERING_ACTION = "steering_action"
    TRUST_TIER_ASSIGNED = "trust_tier_assigned"


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class NotificationRow(Base):
    """Persistence row for a single operator notification."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_task_id", "task_id"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_read", "read"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(
        Enum(NotificationType, name="notification_type", create_type=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class NotificationCreate(BaseModel):
    """Input schema for creating a new notification."""

    type: NotificationType
    title: str = Field(..., max_length=500)
    message: str
    task_id: UUID | None = None


class NotificationRead(BaseModel):
    """Output schema for a single notification."""

    id: UUID
    type: NotificationType
    title: str
    message: str
    task_id: UUID | None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with unread count."""

    items: list[NotificationRead]
    total: int
    unread_count: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_notification(
    session: AsyncSession,
    payload: NotificationCreate,
) -> NotificationRead:
    """Persist a new notification and return the read schema."""
    row = NotificationRow(
        id=uuid4(),
        type=payload.type,
        title=payload.title,
        message=payload.message,
        task_id=payload.task_id,
        read=False,
    )
    session.add(row)
    await session.flush()
    return NotificationRead.model_validate(row)


async def list_notifications(
    session: AsyncSession,
    *,
    unread_only: bool = False,
    type_filter: NotificationType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    """Return paginated notifications, newest first, with unread count."""
    base_stmt = select(NotificationRow)
    if unread_only:
        base_stmt = base_stmt.where(NotificationRow.read.is_(False))
    if type_filter is not None:
        base_stmt = base_stmt.where(NotificationRow.type == type_filter)

    # Unread count (always across full table, ignoring pagination filters)
    unread_stmt = select(func.count()).select_from(NotificationRow).where(
        NotificationRow.read.is_(False)
    )
    unread_result = await session.execute(unread_stmt)
    unread_count = unread_result.scalar_one()

    # Total for current filter
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # Paginated items
    page_stmt = (
        base_stmt.order_by(NotificationRow.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    page_result = await session.execute(page_stmt)
    items = [NotificationRead.model_validate(row) for row in page_result.scalars()]

    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


async def mark_notification_read(
    session: AsyncSession,
    notification_id: UUID,
) -> NotificationRead | None:
    """Mark a single notification as read. Returns None if not found."""
    stmt = select(NotificationRow).where(NotificationRow.id == notification_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    row.read = True
    await session.flush()
    return NotificationRead.model_validate(row)


async def mark_all_notifications_read(session: AsyncSession) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    stmt = select(NotificationRow).where(NotificationRow.read.is_(False))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    for row in rows:
        row.read = True
    await session.flush()
    return len(rows)


async def get_notification(
    session: AsyncSession,
    notification_id: UUID,
) -> NotificationRead | None:
    """Fetch a single notification by ID. Returns None if not found."""
    stmt = select(NotificationRow).where(NotificationRow.id == notification_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return NotificationRead.model_validate(row)
