"""Planning API endpoints — triage + intent review (Epic 36).

Provides endpoints for the triage workflow:
- POST /tasks/{task_id}/accept — accept a triaged task into the pipeline
- POST /tasks/{task_id}/reject — reject a triaged task with reason
- PATCH /tasks/{task_id} — edit a triaged task before accepting

Intent review endpoints (Sprint 3):
- GET /tasks/{task_id}/intent — current spec + version history
- POST /tasks/{task_id}/intent/approve — send approve_intent signal
- POST /tasks/{task_id}/intent/reject — send reject_intent signal
- PUT /tasks/{task_id}/intent — create new version with source=developer
- POST /tasks/{task_id}/intent/refine — create refinement version
"""

import enum
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.intent.intent_crud import (
    create_intent,
    get_all_versions,
    get_latest_for_taskpacket,
)
from src.intent.intent_spec import IntentSpecCreate, IntentSpecRead
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus
from src.models.taskpacket_crud import get_by_id, update_intent_version, update_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["planning"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RejectionReason(enum.StrEnum):
    """Valid reasons for rejecting a triaged task."""

    DUPLICATE = "duplicate"
    OUT_OF_SCOPE = "out_of_scope"
    NEEDS_INFO = "needs_info"
    WONT_FIX = "wont_fix"


class RejectRequest(BaseModel):
    """Request body for rejecting a triaged task."""

    reason: RejectionReason


class TriageEditRequest(BaseModel):
    """Request body for editing a triaged task."""

    issue_title: str | None = None
    issue_body: str | None = None
    # Future: category, priority


class AcceptResponse(BaseModel):
    """Response after accepting a triaged task."""

    task: TaskPacketRead
    workflow_started: bool


class IntentResponse(BaseModel):
    """Response for GET /tasks/{id}/intent."""

    current: IntentSpecRead
    versions: list[IntentSpecRead]


class IntentRejectRequest(BaseModel):
    """Request body for rejecting an intent spec."""

    reason: str


class IntentEditRequest(BaseModel):
    """Request body for editing an intent spec (creates new version)."""

    goal: str
    constraints: list[str]
    acceptance_criteria: list[str]
    non_goals: list[str]


class IntentRefineRequest(BaseModel):
    """Request body for requesting intent refinement."""

    feedback: str


class IntentActionResponse(BaseModel):
    """Response after approve/reject intent."""

    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_task(
    session: AsyncSession, task_id: UUID,
) -> TaskPacketRead:
    """Fetch a TaskPacket or 404."""
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")
    return task


async def _get_intent_built_task(
    session: AsyncSession, task_id: UUID,
) -> TaskPacketRead:
    """Fetch a TaskPacket and verify it is in INTENT_BUILT status."""
    task = await _get_task(session, task_id)
    if task.status != TaskPacketStatus.INTENT_BUILT:
        raise HTTPException(
            status_code=409,
            detail=f"TaskPacket is in {task.status.value} status, not intent_built",
        )
    return task


async def _get_triage_task(
    session: AsyncSession, task_id: UUID,
) -> TaskPacketRead:
    """Fetch a TaskPacket and verify it is in TRIAGE status."""
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")
    if task.status != TaskPacketStatus.TRIAGE:
        raise HTTPException(
            status_code=409,
            detail=f"TaskPacket is in {task.status.value} status, not triage",
        )
    return task


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/accept")
async def accept_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> AcceptResponse:
    """Accept a triaged task: transition TRIAGE -> RECEIVED, start workflow."""
    await _get_triage_task(session, task_id)

    # Transition to RECEIVED
    updated = await update_status(session, task_id, TaskPacketStatus.RECEIVED)

    # Start Temporal workflow
    workflow_started = False
    try:
        from src.ingress.workflow_trigger import start_workflow

        await start_workflow(
            updated.id,
            updated.correlation_id,
            repo=updated.repo,
            issue_title=updated.issue_title or "",
            issue_body=updated.issue_body or "",
            labels=[],
        )
        workflow_started = True
    except Exception:
        logger.exception(
            "Failed to start workflow for accepted task %s", task_id,
        )

    # Emit SSE event
    from src.dashboard.events_publisher import emit_triage_accepted

    await emit_triage_accepted(str(task_id))

    return AcceptResponse(task=updated, workflow_started=workflow_started)


@router.post("/tasks/{task_id}/reject")
async def reject_task(
    task_id: UUID,
    body: RejectRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TaskPacketRead:
    """Reject a triaged task with a reason."""
    await _get_triage_task(session, task_id)

    # Store rejection reason
    from src.models.taskpacket import TaskPacketRow

    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")
    row.rejection_reason = body.reason.value
    row.status = TaskPacketStatus.REJECTED
    await session.commit()
    await session.refresh(row)

    # Emit SSE event
    from src.dashboard.events_publisher import emit_triage_rejected

    await emit_triage_rejected(str(task_id), body.reason.value)

    return TaskPacketRead.model_validate(row)


@router.patch("/tasks/{task_id}")
async def edit_triage_task(
    task_id: UUID,
    body: TriageEditRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TaskPacketRead:
    """Edit a triaged task before accepting."""
    await _get_triage_task(session, task_id)

    from src.models.taskpacket import TaskPacketRow

    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    if body.issue_title is not None:
        row.issue_title = body.issue_title
    if body.issue_body is not None:
        row.issue_body = body.issue_body

    await session.commit()
    await session.refresh(row)

    return TaskPacketRead.model_validate(row)


# ---------------------------------------------------------------------------
# Intent review endpoints (Sprint 3 — Stories 36.9, 36.10)
# ---------------------------------------------------------------------------


@router.get("/tasks/{task_id}/intent")
async def get_intent(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IntentResponse:
    """Get the current intent spec and version history for a task."""
    await _get_task(session, task_id)

    current = await get_latest_for_taskpacket(session, task_id)
    if current is None:
        raise HTTPException(status_code=404, detail="No intent spec found for this task")

    versions = await get_all_versions(session, task_id)
    return IntentResponse(current=current, versions=versions)


@router.post("/tasks/{task_id}/intent/approve")
async def approve_intent(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IntentActionResponse:
    """Approve the intent spec — sends approve_intent signal to Temporal."""
    await _get_intent_built_task(session, task_id)

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("approve_intent", args=["dashboard_user"])

    return IntentActionResponse(status="approved")


@router.post("/tasks/{task_id}/intent/reject")
async def reject_intent(
    task_id: UUID,
    body: IntentRejectRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IntentActionResponse:
    """Reject the intent spec — sends reject_intent signal to Temporal."""
    await _get_intent_built_task(session, task_id)

    from src.ingress.workflow_trigger import get_temporal_client

    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("reject_intent", args=["dashboard_user", body.reason])

    return IntentActionResponse(status="rejected")


@router.put("/tasks/{task_id}/intent")
async def edit_intent(
    task_id: UUID,
    body: IntentEditRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IntentSpecRead:
    """Edit the intent spec — creates a new version with source=developer."""
    await _get_intent_built_task(session, task_id)

    current = await get_latest_for_taskpacket(session, task_id)
    if current is None:
        raise HTTPException(status_code=404, detail="No intent spec found for this task")

    new_version = current.version + 1
    intent_data = IntentSpecCreate(
        taskpacket_id=task_id,
        version=new_version,
        goal=body.goal,
        constraints=body.constraints,
        acceptance_criteria=body.acceptance_criteria,
        non_goals=body.non_goals,
        source="developer",
    )
    created = await create_intent(session, intent_data)
    await update_intent_version(session, task_id, created.id, created.version)
    return created


@router.post("/tasks/{task_id}/intent/refine")
async def refine_intent_endpoint(
    task_id: UUID,
    body: IntentRefineRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IntentSpecRead:
    """Request intent refinement — constructs RefinementTrigger and creates new version."""
    await _get_intent_built_task(session, task_id)

    from src.intent.refinement import RefinementTrigger, refine_intent

    trigger = RefinementTrigger(source="developer", questions=[body.feedback])
    refined = await refine_intent(session, task_id, trigger)
    return refined
