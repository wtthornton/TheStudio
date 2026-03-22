"""Pipeline steering API — pause, resume, and abort active TaskPackets.

Endpoints:
- POST /tasks/{task_id}/pause   — pause between activities (202 / 404 / 409)
- POST /tasks/{task_id}/resume  — resume a paused task      (202 / 404 / 409)
- POST /tasks/{task_id}/abort   — abort with reason         (202 / 404 / 409)

Each endpoint validates the current TaskPacket status, then sends the
corresponding Temporal workflow signal.  Status transitions are driven by the
workflow signal handlers — the API layer only guards against obviously invalid
requests (task not found, already in terminal state, wrong precondition).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.models.steering_audit import SteeringAuditLogRead, list_audit_entries_for_task
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["steering"])

# ---------------------------------------------------------------------------
# Terminal statuses — no steering actions allowed once reached
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES: frozenset[TaskPacketStatus] = frozenset(
    {
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.ABORTED,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.AWAITING_APPROVAL_EXPIRED,
    }
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SteeringResponse(BaseModel):
    """Response returned by steering action endpoints."""

    task_id: UUID
    action: str
    status: str = "accepted"


class AbortRequest(BaseModel):
    """Request body for aborting a task."""

    reason: str = Field(..., min_length=1, max_length=500, description="Reason for aborting")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_active_task(session: AsyncSession, task_id: UUID):  # type: ignore[return]
    """Fetch task or raise 404.  Returns the TaskPacketRead."""
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/pause", status_code=202)
async def pause_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SteeringResponse:
    """Pause an active pipeline task between activities.

    Sends the ``pause_task`` Temporal signal.  The workflow will hold after
    the currently-running activity completes.

    Returns:
        202 — signal accepted
        404 — task not found
        409 — task already paused or in a terminal state
    """
    task = await _get_active_task(session, task_id)

    if task.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause task in terminal state: {task.status}",
        )
    if task.status == TaskPacketStatus.PAUSED:
        raise HTTPException(status_code=409, detail="Task is already paused")

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("pause_task", args=["api", str(task_id)])

    logger.info("pause_task signal sent", extra={"task_id": str(task_id), "status": task.status})
    return SteeringResponse(task_id=task_id, action="pause")


@router.post("/tasks/{task_id}/resume", status_code=202)
async def resume_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SteeringResponse:
    """Resume a paused pipeline task.

    Sends the ``resume_task`` Temporal signal.  The workflow will continue
    from the point it was paused.

    Returns:
        202 — signal accepted
        404 — task not found
        409 — task is not currently paused
    """
    task = await _get_active_task(session, task_id)

    if task.status != TaskPacketStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot resume task that is not paused (current status: {task.status})",
        )

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("resume_task", args=["api", str(task_id)])

    logger.info("resume_task signal sent", extra={"task_id": str(task_id)})
    return SteeringResponse(task_id=task_id, action="resume")


@router.post("/tasks/{task_id}/abort", status_code=202)
async def abort_task(
    task_id: UUID,
    body: AbortRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SteeringResponse:
    """Abort a pipeline task with a mandatory reason.

    Sends the ``abort_task`` Temporal signal with the provided reason.  The
    workflow will terminate after the current activity completes.  This is a
    terminal action — the task cannot be resumed once aborted.

    Returns:
        202 — signal accepted
        404 — task not found
        409 — task is already in a terminal state
    """
    task = await _get_active_task(session, task_id)

    if task.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot abort task in terminal state: {task.status}",
        )

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("abort_task", args=[body.reason, "api", str(task_id)])

    logger.info(
        "abort_task signal sent",
        extra={"task_id": str(task_id), "reason": body.reason},
    )
    return SteeringResponse(task_id=task_id, action="abort")


@router.get("/tasks/{task_id}/audit", response_model=list[SteeringAuditLogRead])
async def get_task_audit(
    task_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[SteeringAuditLogRead]:
    """Return steering audit log entries for a specific task, newest first.

    Returns:
        200 — list of audit entries (empty if none exist)
        404 — task not found
    """
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    entries = await list_audit_entries_for_task(session, task_id, limit=limit, offset=offset)
    logger.debug(
        "audit entries fetched",
        extra={"task_id": str(task_id), "count": len(entries)},
    )
    return entries
