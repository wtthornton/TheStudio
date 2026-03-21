"""Dashboard task list API — paginated TaskPacket listing with filters."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.events import _verify_token
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRead, TaskPacketRow, TaskPacketStatus

router = APIRouter()


class StageCost(BaseModel):
    """Cost breakdown for a single pipeline stage."""

    stage: str
    cost: float = 0.0
    model: str | None = None


class TaskPacketDetail(TaskPacketRead):
    """Extended TaskPacket with per-stage cost and model info."""

    cost_by_stage: list[StageCost] = Field(default_factory=list)
    total_cost: float = 0.0


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


def _extract_cost_by_stage(stage_timings: dict[str, Any] | None) -> list[StageCost]:
    """Build per-stage cost list from stage_timings metadata.

    Stage timings may include optional ``cost`` and ``model`` keys per stage.
    Returns an empty list when no timings are available.
    """
    if not stage_timings:
        return []
    stages: list[StageCost] = []
    for name, data in stage_timings.items():
        if not isinstance(data, dict):
            continue
        stages.append(
            StageCost(
                stage=name,
                cost=data.get("cost", 0.0),
                model=data.get("model"),
            )
        )
    return stages


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TaskPacketDetail:
    """Get a single TaskPacket by ID with stage timestamps and cost breakdown.

    Returns 404 when the task ID is not found.
    """
    _verify_token(token)

    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    base = TaskPacketRead.model_validate(row)
    cost_by_stage = _extract_cost_by_stage(row.stage_timings)
    total_cost = sum(s.cost for s in cost_by_stage)

    return TaskPacketDetail(
        **base.model_dump(),
        cost_by_stage=cost_by_stage,
        total_cost=total_cost,
    )
