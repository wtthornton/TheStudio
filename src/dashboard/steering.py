"""Pipeline steering API — pause, resume, abort, redirect, and retry active TaskPackets.

Endpoints:
- POST /tasks/{task_id}/pause      — pause between activities    (202 / 404 / 409)
- POST /tasks/{task_id}/resume     — resume a paused task        (202 / 404 / 409)
- POST /tasks/{task_id}/abort      — abort with reason           (202 / 404 / 409)
- POST /tasks/{task_id}/redirect   — redirect to earlier stage   (202 / 400 / 404 / 409)
- POST /tasks/{task_id}/retry      — retry the current stage     (202 / 400 / 404 / 409)

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

from src.dashboard.models.steering_audit import (
    SteeringAction,
    SteeringAuditLogRead,
    list_all_audit_entries,
    list_audit_entries_for_task,
)
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id
from src.workflow.pipeline import STAGE_ORDER

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


class RedirectRequest(BaseModel):
    """Request body for redirecting a task to an earlier pipeline stage."""

    target_stage: str = Field(..., description="Target pipeline stage to re-enter")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for redirecting")


class RetryRequest(BaseModel):
    """Request body for retrying the current pipeline stage."""

    reason: str = Field(
        "manual retry requested",
        min_length=1,
        max_length=500,
        description="Reason for retrying",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_active_task(session: AsyncSession, task_id: UUID):  # type: ignore[return]
    """Fetch task or raise 404.  Returns the TaskPacketRead."""
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


def _detect_current_stage(stage_timings: dict | None) -> str | None:
    """Return the pipeline stage that has started but not yet ended, or None.

    ``stage_timings`` maps stage name → ``{"start": iso_ts, "end": iso_ts|null}``.
    The active stage is the one whose ``end`` value is null/absent.  If multiple
    stages qualify (shouldn't happen in practice), the one with the highest
    STAGE_ORDER value is returned.
    """
    if not stage_timings:
        return None
    candidates = [
        stage
        for stage, timing in stage_timings.items()
        if isinstance(timing, dict) and timing.get("start") and not timing.get("end")
    ]
    if not candidates:
        return None
    # Return the furthest-along stage (highest order index).
    return max(candidates, key=lambda s: STAGE_ORDER.get(s, 0))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/pause", status_code=202)
async def pause_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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


@router.post("/tasks/{task_id}/redirect", status_code=202)
async def redirect_task(
    task_id: UUID,
    body: RedirectRequest,
    session: AsyncSession = Depends(get_session),
) -> SteeringResponse:
    """Redirect the pipeline to re-enter at an earlier stage.

    ``target_stage`` must be a known pipeline stage and must be earlier (lower
    order index) than the task's current stage.  The redirect takes effect at
    the next inter-activity checkpoint.

    Returns:
        202 — signal accepted
        400 — unknown target_stage or target is not earlier than current stage
        404 — task not found
        409 — task is in a terminal state
    """
    task = await _get_active_task(session, task_id)

    if task.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot redirect task in terminal state: {task.status}",
        )

    if body.target_stage not in STAGE_ORDER:
        known = sorted(STAGE_ORDER.keys(), key=lambda s: STAGE_ORDER[s])
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target_stage '{body.target_stage}'. Known stages: {known}",
        )

    current_stage = _detect_current_stage(task.stage_timings)
    if current_stage is not None:
        target_order = STAGE_ORDER[body.target_stage]
        current_order = STAGE_ORDER.get(current_stage, 999)
        if target_order >= current_order:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"target_stage '{body.target_stage}' (order {target_order}) must be earlier "
                    f"than current stage '{current_stage}' (order {current_order})"
                ),
            )

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("redirect_task", args=[body.target_stage, body.reason, "api", str(task_id)])

    logger.info(
        "redirect_task signal sent",
        extra={
            "task_id": str(task_id),
            "target_stage": body.target_stage,
            "current_stage": current_stage,
            "reason": body.reason,
        },
    )
    return SteeringResponse(task_id=task_id, action="redirect")


@router.post("/tasks/{task_id}/retry", status_code=202)
async def retry_task(
    task_id: UUID,
    body: RetryRequest,
    session: AsyncSession = Depends(get_session),
) -> SteeringResponse:
    """Retry the current pipeline stage from the beginning.

    Clears artifacts for the current stage and re-enters it.  Differs from
    redirect in that the target IS the current stage (no direction validation
    on the API layer; the workflow validates that a current stage exists).

    Returns:
        202 — signal accepted
        400 — task has no active stage to retry
        404 — task not found
        409 — task is in a terminal state
    """
    task = await _get_active_task(session, task_id)

    if task.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry task in terminal state: {task.status}",
        )

    current_stage = _detect_current_stage(task.stage_timings)
    if current_stage is None and task.status not in {TaskPacketStatus.PAUSED}:
        # If we cannot determine a current stage and the task isn't paused, the
        # workflow may not have a retryable stage.  Warn but still send the
        # signal — the workflow's own guard will handle it gracefully.
        logger.warning(
            "retry_stage: no deterministic current stage found, sending signal anyway",
            extra={"task_id": str(task_id), "status": task.status},
        )

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("retry_stage", args=[body.reason, "api", str(task_id)])

    logger.info(
        "retry_stage signal sent",
        extra={"task_id": str(task_id), "current_stage": current_stage, "reason": body.reason},
    )
    return SteeringResponse(task_id=task_id, action="retry")


@router.get("/steering/audit", response_model=list[SteeringAuditLogRead])
async def list_all_steering_audit(
    action: SteeringAction | None = Query(None, description="Filter by steering action type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SteeringAuditLogRead]:
    """Return all steering audit log entries across all tasks, newest first.

    Optional ``action`` filter narrows results to a specific action type.
    Supports pagination via ``limit`` and ``offset``.

    Returns:
        200 — list of audit entries (empty if none exist)
    """
    entries = await list_all_audit_entries(session, action=action, limit=limit, offset=offset)
    logger.debug(
        "all steering audit entries fetched",
        extra={"action_filter": action, "count": len(entries)},
    )
    return entries


@router.get("/tasks/{task_id}/audit", response_model=list[SteeringAuditLogRead])
async def get_task_audit(
    task_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
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
