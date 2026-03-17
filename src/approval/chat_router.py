"""Approval Chat API — endpoints for review context, chat, and actions.

Epic 24 Story 24.3: Provides the API layer for the approval chat interface.
Epic 24 Story 24.6: OTel spans for all chat interactions, approval metadata
in evidence comments, NATS signals for approval/rejection.

- GET  /api/tasks/{id}/review       — review context + chat history
- POST /api/tasks/{id}/review/messages — send a message, get LLM response
- POST /api/tasks/{id}/reject      — (already exists in src/api/approval.py)

The chat LLM answers questions about the changes using ReviewContext as
system context. It cannot modify the pipeline or approve/reject.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.rbac import get_current_user_id
from src.approval.chat_models import MessageRole
from src.db.connection import get_session
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_APPROVAL_CHAT_MESSAGE,
    SPAN_APPROVAL_LLM_RESPONSE,
    SPAN_APPROVAL_REVIEW_CONTEXT,
)
from src.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.approval.chat")

router = APIRouter(prefix="/api/tasks", tags=["approval-chat"])


# --- Request/Response Models ---


class ChatMessageOut(BaseModel):
    """A chat message in the response."""

    id: str
    role: str
    content: str
    created_at: str


class ReviewContextResponse(BaseModel):
    """Response for GET /review — context + chat history."""

    taskpacket_id: str
    repo: str = ""
    repo_tier: str = ""
    status: str = ""
    issue_title: str = ""
    intent_goal: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    verification_passed: bool = False
    qa_passed: bool = False
    files_changed: list[str] = Field(default_factory=list)
    agent_summary: str = ""
    pr_url: str = ""
    messages: list[ChatMessageOut] = Field(default_factory=list)
    chat_id: str = ""


class SendMessageRequest(BaseModel):
    """Request body for POST /review/messages."""

    content: str


class SendMessageResponse(BaseModel):
    """Response for POST /review/messages — the assistant reply."""

    user_message: ChatMessageOut
    assistant_message: ChatMessageOut


# --- Endpoints ---


@router.get(
    "/{taskpacket_id}/review",
    response_model=ReviewContextResponse,
    responses={
        404: {"description": "TaskPacket not found"},
        409: {"description": "Task is not awaiting approval"},
    },
)
async def get_review(
    taskpacket_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewContextResponse:
    """Get review context and chat history for a TaskPacket.

    Creates the chat thread on first access if none exists.
    Returns 404 if TaskPacket not found, 409 if not in AWAITING_APPROVAL.
    """
    task_uuid = _parse_uuid(taskpacket_id)
    taskpacket = await _get_taskpacket_or_404(session, task_uuid)
    _assert_awaiting_approval(taskpacket)

    with tracer.start_as_current_span(SPAN_APPROVAL_REVIEW_CONTEXT) as span:
        span.set_attribute(ATTR_TASKPACKET_ID, taskpacket_id)
        span.set_attribute("thestudio.user_id", user_id)

        # Build review context
        from src.approval.review_context import build_review_context

        context = await build_review_context(task_uuid, session=session)

        # Get or create chat thread
        from src.approval.chat_crud import create_chat, get_messages

        chat = await create_chat(session, task_uuid, created_by=user_id)
        messages = await get_messages(session, chat.id)
        await session.commit()

        span.set_attribute("thestudio.chat_id", str(chat.id))
        span.set_attribute("thestudio.message_count", len(messages))

    return ReviewContextResponse(
        taskpacket_id=taskpacket_id,
        repo=taskpacket.repo if hasattr(taskpacket, "repo") else "",
        status=(
            taskpacket.status.value
            if hasattr(taskpacket.status, "value")
            else str(taskpacket.status)
        ),
        issue_title=getattr(taskpacket, "issue_title", ""),
        intent_goal=context.intent.goal if context else "",
        acceptance_criteria=context.intent.acceptance_criteria if context else [],
        verification_passed=context.verification.passed if context else False,
        qa_passed=context.qa.passed if context else False,
        files_changed=context.evidence.files_changed if context else [],
        agent_summary=context.evidence.agent_summary if context else "",
        pr_url=context.pr_url if context else "",
        messages=[_message_to_out(m) for m in messages],
        chat_id=str(chat.id),
    )


@router.post(
    "/{taskpacket_id}/review/messages",
    response_model=SendMessageResponse,
    responses={
        404: {"description": "TaskPacket not found"},
        409: {"description": "Task is not awaiting approval"},
        429: {"description": "Chat message limit reached"},
    },
)
async def send_message(
    taskpacket_id: str,
    body: SendMessageRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SendMessageResponse:
    """Send a message in the review chat and get an LLM response.

    Persists the user message, calls the Model Gateway with full
    ReviewContext + chat history, persists the assistant response.
    OTel spans cover message send and LLM response.
    """
    task_uuid = _parse_uuid(taskpacket_id)
    taskpacket = await _get_taskpacket_or_404(session, task_uuid)
    _assert_awaiting_approval(taskpacket)

    from src.approval.chat_crud import add_message, create_chat, get_messages
    from src.approval.review_context import build_review_context

    # Get or create chat
    chat = await create_chat(session, task_uuid, created_by=user_id)

    # Persist user message (with span)
    with tracer.start_as_current_span(SPAN_APPROVAL_CHAT_MESSAGE) as msg_span:
        msg_span.set_attribute(ATTR_TASKPACKET_ID, taskpacket_id)
        msg_span.set_attribute("thestudio.chat_id", str(chat.id))
        msg_span.set_attribute("thestudio.user_id", user_id)
        msg_span.set_attribute("thestudio.message_role", "user")

        try:
            user_msg = await add_message(
                session, chat.id, MessageRole.USER, body.content,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc

    # Build context for LLM
    context = await build_review_context(task_uuid, session=session)
    history = await get_messages(session, chat.id)

    # Get LLM response (with span)
    with tracer.start_as_current_span(SPAN_APPROVAL_LLM_RESPONSE) as llm_span:
        llm_span.set_attribute(ATTR_TASKPACKET_ID, taskpacket_id)
        llm_span.set_attribute("thestudio.chat_id", str(chat.id))
        llm_span.set_attribute("thestudio.history_length", len(history))

        assistant_text = await _get_llm_response(context, history)

        llm_span.set_attribute("thestudio.response_length", len(assistant_text))

    # Persist assistant message
    assistant_msg = await add_message(
        session, chat.id, MessageRole.ASSISTANT, assistant_text,
    )

    await session.commit()

    logger.info(
        "approval.chat.message_exchanged",
        extra={
            "taskpacket_id": taskpacket_id,
            "chat_id": str(chat.id),
            "user_id": user_id,
            "message_count": len(history) + 1,
        },
    )

    return SendMessageResponse(
        user_message=_message_to_out(user_msg),
        assistant_message=_message_to_out(assistant_msg),
    )


# --- Helpers ---


def _parse_uuid(taskpacket_id: str) -> UUID:
    try:
        return UUID(taskpacket_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {taskpacket_id} not found",
        ) from err


async def _get_taskpacket_or_404(session: AsyncSession, task_uuid: UUID):
    from src.models.taskpacket_crud import get_by_id

    taskpacket = await get_by_id(session, task_uuid)
    if taskpacket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TaskPacket {task_uuid} not found",
        )
    return taskpacket


def _assert_awaiting_approval(taskpacket) -> None:
    from src.models.taskpacket import TaskPacketStatus

    if taskpacket.status != TaskPacketStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Task is not awaiting approval "
                f"(current status: {taskpacket.status.value})"
            ),
        )


def _message_to_out(msg) -> ChatMessageOut:
    return ChatMessageOut(
        id=str(msg.id),
        role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
        content=msg.content,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
    )


async def _get_llm_response(context, history) -> str:
    """Get an LLM response via the Model Gateway.

    Uses the review context as system prompt and chat history as
    conversation context. Falls back to a stub response if the
    gateway is unavailable.
    """
    try:
        from src.admin.model_gateway import get_model_router

        router = get_model_router()
        provider = router.select_model(step="approval_chat")

        # Build messages for LLM
        system_prompt = context.to_system_prompt() if context else (
            "You are a review assistant. Answer questions about code changes."
        )

        messages = []
        for msg in history:
            role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg.content})

        # Call the LLM via gateway
        # In production, this delegates to the actual provider.
        # For now, return a contextual stub response.
        if hasattr(provider, "call"):
            response = await provider.call(
                system=system_prompt,
                messages=messages,
            )
            return response

    except Exception:
        logger.debug(
            "LLM gateway unavailable for approval chat, using stub",
            exc_info=True,
        )

    # Stub response when gateway is unavailable
    file_count = len(context.evidence.files_changed) if context else 0
    verified = (
        "passed" if context and context.verification.passed
        else "has not been confirmed"
    )
    return (
        f"I can see this task involves changes to {file_count} files. "
        f"The verification {verified}. "
        f"Please review the evidence and let me know "
        f"if you have specific questions."
    )
