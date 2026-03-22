"""Dashboard activity endpoints — paginated activity log per task.

Provides the ActivityEntry model and API endpoint for the
Activity Stream panel (Epic 35, Slice 3):
- GET /tasks/:id/activity — paginated activity log with filters
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, String, Text, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.dashboard.events import _verify_token
from src.db.base import Base
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# SQLAlchemy model (S3.B2)
# ---------------------------------------------------------------------------


class ActivityEntryRow(Base):
    """Single activity log entry for a pipeline task."""

    __tablename__ = "activity_entry"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(index=True)
    stage: Mapped[str] = mapped_column(String(50))
    activity_type: Mapped[str] = mapped_column(String(50))
    subphase: Mapped[str] = mapped_column(String(100), default="")
    content: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text, default="")
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"),
    )


# ---------------------------------------------------------------------------
# Pydantic response model
# ---------------------------------------------------------------------------


class ActivityEntryRead(BaseModel):
    """Serialised activity entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    task_id: uuid.UUID
    stage: str
    activity_type: str
    subphase: str
    content: str
    detail: str
    metadata: dict | None = Field(None, alias="extra_metadata", validation_alias="extra_metadata")
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoint (S3.B3)
# ---------------------------------------------------------------------------


@router.get("/tasks/{task_id}/activity")
async def list_task_activity(
    task_id: uuid.UUID,
    token: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    activity_type: str | None = Query(None, description="Filter by activity type"),
    subphase: str | None = Query(None, description="Filter by subphase"),
    order: str = Query("oldest", description="'oldest' (asc) or 'newest' (desc)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Paginated activity log for a specific task (S3.B3).

    Supports filtering by activity_type and subphase.
    Supports both oldest-first and newest-first ordering.
    """
    _verify_token(token)

    stmt = select(ActivityEntryRow).where(ActivityEntryRow.task_id == task_id)
    count_stmt = (
        select(func.count())
        .select_from(ActivityEntryRow)
        .where(ActivityEntryRow.task_id == task_id)
    )

    # Apply filters
    if activity_type is not None:
        stmt = stmt.where(ActivityEntryRow.activity_type == activity_type)
        count_stmt = count_stmt.where(ActivityEntryRow.activity_type == activity_type)
    if subphase is not None:
        stmt = stmt.where(ActivityEntryRow.subphase == subphase)
        count_stmt = count_stmt.where(ActivityEntryRow.subphase == subphase)

    # Total count
    total = (await session.execute(count_stmt)).scalar_one()

    # Ordering
    if order == "newest":
        stmt = stmt.order_by(ActivityEntryRow.created_at.desc())
    else:
        stmt = stmt.order_by(ActivityEntryRow.created_at.asc())

    # Pagination
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [ActivityEntryRead.model_validate(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
