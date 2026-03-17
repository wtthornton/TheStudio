"""Approval Chat CRUD — persistence operations for chat threads and messages.

Epic 24 Story 24.2: Create, read, update operations for approval chat
threads and their messages. All functions take an AsyncSession for
database access.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.approval.chat_models import (
    ApprovalChat,
    ApprovalChatMessage,
    ChatStatus,
    MessageRole,
)

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_CHAT = 50


async def create_chat(
    session: AsyncSession,
    taskpacket_id: UUID,
    created_by: str = "",
) -> ApprovalChat:
    """Create a new active chat thread for a TaskPacket.

    If an active chat already exists for this TaskPacket, returns
    the existing one (idempotent).
    """
    existing = await get_chat_by_taskpacket(session, taskpacket_id)
    if existing is not None:
        return existing

    chat = ApprovalChat(
        taskpacket_id=taskpacket_id,
        created_by=created_by,
        status=ChatStatus.ACTIVE,
    )
    session.add(chat)
    await session.flush()

    logger.info(
        "approval.chat.created",
        extra={
            "chat_id": str(chat.id),
            "taskpacket_id": str(taskpacket_id),
            "created_by": created_by,
        },
    )
    return chat


async def get_chat_by_taskpacket(
    session: AsyncSession,
    taskpacket_id: UUID,
) -> ApprovalChat | None:
    """Get the active chat for a TaskPacket, or None."""
    stmt = (
        select(ApprovalChat)
        .options(selectinload(ApprovalChat.messages))
        .where(
            ApprovalChat.taskpacket_id == taskpacket_id,
            ApprovalChat.status == ChatStatus.ACTIVE,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_chat_by_id(
    session: AsyncSession,
    chat_id: UUID,
) -> ApprovalChat | None:
    """Get a chat by its ID."""
    stmt = (
        select(ApprovalChat)
        .options(selectinload(ApprovalChat.messages))
        .where(ApprovalChat.id == chat_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_message(
    session: AsyncSession,
    chat_id: UUID,
    role: MessageRole,
    content: str,
) -> ApprovalChatMessage:
    """Add a message to a chat thread.

    Raises ValueError if the chat has reached MAX_MESSAGES_PER_CHAT.
    """
    # Check message count
    count_stmt = (
        select(ApprovalChatMessage)
        .where(ApprovalChatMessage.chat_id == chat_id)
    )
    result = await session.execute(count_stmt)
    existing_count = len(result.scalars().all())

    if existing_count >= MAX_MESSAGES_PER_CHAT:
        raise ValueError(
            f"Chat {chat_id} has reached the maximum of "
            f"{MAX_MESSAGES_PER_CHAT} messages"
        )

    message = ApprovalChatMessage(
        chat_id=chat_id,
        role=role,
        content=content,
    )
    session.add(message)
    await session.flush()

    logger.info(
        "approval.chat.message_added",
        extra={
            "chat_id": str(chat_id),
            "message_id": str(message.id),
            "role": role.value,
        },
    )
    return message


async def get_messages(
    session: AsyncSession,
    chat_id: UUID,
    *,
    limit: int | None = None,
) -> list[ApprovalChatMessage]:
    """Get messages for a chat, ordered by created_at."""
    stmt = (
        select(ApprovalChatMessage)
        .where(ApprovalChatMessage.chat_id == chat_id)
        .order_by(ApprovalChatMessage.created_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def resolve_chat(
    session: AsyncSession,
    chat_id: UUID,
) -> ApprovalChat | None:
    """Mark a chat as resolved (approval/rejection completed)."""
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        return None

    chat.status = ChatStatus.RESOLVED
    chat.resolved_at = datetime.now(UTC)
    await session.flush()

    logger.info(
        "approval.chat.resolved",
        extra={"chat_id": str(chat_id)},
    )
    return chat


async def expire_chat(
    session: AsyncSession,
    chat_id: UUID,
) -> ApprovalChat | None:
    """Mark a chat as expired (approval timeout)."""
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        return None

    chat.status = ChatStatus.EXPIRED
    chat.resolved_at = datetime.now(UTC)
    await session.flush()

    logger.info(
        "approval.chat.expired",
        extra={"chat_id": str(chat_id)},
    )
    return chat


async def resolve_chat_by_taskpacket(
    session: AsyncSession,
    taskpacket_id: UUID,
) -> ApprovalChat | None:
    """Resolve the active chat for a TaskPacket (if any).

    Called when approval or rejection happens to close the thread.
    """
    chat = await get_chat_by_taskpacket(session, taskpacket_id)
    if chat is None:
        return None
    return await resolve_chat(session, chat.id)
