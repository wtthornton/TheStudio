"""Dashboard task list API — paginated TaskPacket listing with filters."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.events import _verify_token
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRead, TaskPacketRow, TaskPacketStatus

router = APIRouter()


@router.get("/tasks")
async def list_tasks(
    token: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: TaskPacketStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    repo: str | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """List TaskPackets with pagination and optional filters.

    Returns JSON with ``items`` (array of TaskPacketRead) and ``total`` count.
    Requires ``?token=`` query param when ``dashboard_token`` is set.
    """
    _verify_token(token)

    # Build base query
    stmt = select(TaskPacketRow)
    count_stmt = select(func.count()).select_from(TaskPacketRow)

    # Apply filters
    if status is not None:
        stmt = stmt.where(TaskPacketRow.status == status)
        count_stmt = count_stmt.where(TaskPacketRow.status == status)
    if created_after is not None:
        stmt = stmt.where(TaskPacketRow.created_at >= created_after)
        count_stmt = count_stmt.where(TaskPacketRow.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(TaskPacketRow.created_at <= created_before)
        count_stmt = count_stmt.where(TaskPacketRow.created_at <= created_before)
    if repo is not None:
        stmt = stmt.where(TaskPacketRow.repo == repo)
        count_stmt = count_stmt.where(TaskPacketRow.repo == repo)

    # Get total count
    total = (await session.execute(count_stmt)).scalar_one()

    # Apply ordering and pagination
    stmt = stmt.order_by(TaskPacketRow.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "items": [TaskPacketRead.model_validate(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
