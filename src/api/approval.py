"""Approval API — endpoints for signaling human approval or rejection to waiting workflows.

Sends the ``approve_publish`` or ``reject_publish`` Temporal signal to a
pipeline workflow that is in the ``AWAITING_APPROVAL`` state.

Architecture reference: Epic 21, Story 5; Epic 24 (rejection flow)
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.rbac import get_current_user_id
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["approval"])


class ApprovalRequest(BaseModel):
    """Request body for the approval endpoint."""

    approved_by: str


class ApprovalResponse(BaseModel):
    """Response body for the approval endpoint."""

    status: str
    taskpacket_id: str


class RejectionRequest(BaseModel):
    """Request body for the rejection endpoint."""

    rejected_by: str
    reason: str


async def _send_approval_signal(
    taskpacket_id: str, approved_by: str,
) -> None:
    """Send the approve_publish signal to the Temporal workflow."""
    from temporalio.client import Client

    from src.settings import settings

    client = await Client.connect(settings.temporal_host)
    workflow_id = f"pipeline-{taskpacket_id}"
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("approve_publish", args=[approved_by, "api"])


async def _send_rejection_signal(
    taskpacket_id: str, rejected_by: str, reason: str,
) -> None:
    """Send the reject_publish signal to the Temporal workflow."""
    from temporalio.client import Client

    from src.settings import settings

    client = await Client.connect(settings.temporal_host)
    workflow_id = f"pipeline-{taskpacket_id}"
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("reject_publish", args=[rejected_by, reason])


@router.post(
    "/{taskpacket_id}/approve",
    response_model=ApprovalResponse,
    responses={
        404: {"description": "TaskPacket or workflow not found"},
        409: {"description": "Task is not awaiting approval"},
    },
)
async def approve_task(
    taskpacket_id: str,
    body: ApprovalRequest,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApprovalResponse:
    """Signal approval to a waiting pipeline workflow.

    Looks up the TaskPacket, validates it is in AWAITING_APPROVAL state,
    then sends the ``approve_publish`` signal to the corresponding Temporal
    workflow.

    Idempotent: approving an already-approved task returns 200.
    """
    try:
        task_uuid = UUID(taskpacket_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {taskpacket_id} not found",
        ) from err

    taskpacket = await get_by_id(session, task_uuid)
    if taskpacket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {taskpacket_id} not found",
        )

    # Allow approval if awaiting or already published (idempotent)
    if taskpacket.status == TaskPacketStatus.PUBLISHED:
        return ApprovalResponse(status="approved", taskpacket_id=taskpacket_id)

    if taskpacket.status != TaskPacketStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is not awaiting approval (current status: {taskpacket.status.value})",
        )

    try:
        await _send_approval_signal(taskpacket_id, body.approved_by)
    except Exception as exc:
        logger.exception(
            "Failed to send approval signal",
            extra={"taskpacket_id": taskpacket_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow for TaskPacket {taskpacket_id} not found",
        ) from exc

    logger.info(
        "approval.signaled",
        extra={
            "taskpacket_id": taskpacket_id,
            "approved_by": body.approved_by,
            "user_id": user_id,
        },
    )

    return ApprovalResponse(status="approved", taskpacket_id=taskpacket_id)


@router.post(
    "/{taskpacket_id}/reject",
    response_model=ApprovalResponse,
    responses={
        404: {"description": "TaskPacket or workflow not found"},
        409: {"description": "Task is not awaiting approval"},
    },
)
async def reject_task(
    taskpacket_id: str,
    body: RejectionRequest,
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApprovalResponse:
    """Signal rejection to a waiting pipeline workflow.

    Looks up the TaskPacket, validates it is in AWAITING_APPROVAL state,
    then sends the ``reject_publish`` signal to the corresponding Temporal
    workflow. Requires a reason for audit trail.

    Idempotent: rejecting an already-rejected task returns 200.
    """
    try:
        task_uuid = UUID(taskpacket_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {taskpacket_id} not found",
        ) from err

    taskpacket = await get_by_id(session, task_uuid)
    if taskpacket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {taskpacket_id} not found",
        )

    # Idempotent: already rejected
    if taskpacket.status == TaskPacketStatus.REJECTED:
        return ApprovalResponse(status="rejected", taskpacket_id=taskpacket_id)

    if taskpacket.status != TaskPacketStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is not awaiting approval (current status: {taskpacket.status.value})",
        )

    try:
        await _send_rejection_signal(taskpacket_id, body.rejected_by, body.reason)
    except Exception as exc:
        logger.exception(
            "Failed to send rejection signal",
            extra={"taskpacket_id": taskpacket_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow for TaskPacket {taskpacket_id} not found",
        ) from exc

    logger.info(
        "rejection.signaled",
        extra={
            "taskpacket_id": taskpacket_id,
            "rejected_by": body.rejected_by,
            "reason": body.reason,
            "user_id": user_id,
        },
    )

    return ApprovalResponse(status="rejected", taskpacket_id=taskpacket_id)
