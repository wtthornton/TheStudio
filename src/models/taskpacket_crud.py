"""CRUD operations for TaskPacket."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.taskpacket import (
    ALLOWED_TRANSITIONS,
    TaskPacketCreate,
    TaskPacketRead,
    TaskPacketRow,
    TaskPacketStatus,
)


class InvalidStatusTransitionError(Exception):
    """Raised when a status transition is not allowed."""

    def __init__(self, current: TaskPacketStatus, target: TaskPacketStatus) -> None:
        super().__init__(f"Cannot transition from {current.value} to {target.value}")
        self.current = current
        self.target = target


async def create(
    session: AsyncSession,
    data: TaskPacketCreate,
    initial_status: TaskPacketStatus = TaskPacketStatus.RECEIVED,
) -> TaskPacketRead:
    """Create a TaskPacket. Returns existing record if (delivery_id, repo) already exists."""
    # Use INSERT ... ON CONFLICT DO NOTHING for atomic dedupe
    values: dict[str, Any] = {
        "repo": data.repo,
        "issue_id": data.issue_id,
        "delivery_id": data.delivery_id,
        "correlation_id": data.correlation_id,
        "source_name": data.source_name,
        "status": initial_status,
    }
    if data.issue_title is not None:
        values["issue_title"] = data.issue_title
    if data.issue_body is not None:
        values["issue_body"] = data.issue_body
    if data.triage_enrichment is not None:
        values["triage_enrichment"] = data.triage_enrichment
    stmt = (
        pg_insert(TaskPacketRow)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["delivery_id", "repo"])
        .returning(TaskPacketRow)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is not None:
        await session.commit()
        return TaskPacketRead.model_validate(row)

    # Conflict — fetch existing record
    existing = await get_by_delivery(session, data.delivery_id, data.repo)
    if existing is None:
        raise RuntimeError("TaskPacket insert returned None but no existing record found")
    return existing


async def get_by_id(session: AsyncSession, task_id: UUID) -> TaskPacketRead | None:
    """Get a TaskPacket by its primary key."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        return None
    return TaskPacketRead.model_validate(row)


async def get_by_delivery(
    session: AsyncSession, delivery_id: str, repo: str
) -> TaskPacketRead | None:
    """Get a TaskPacket by delivery_id + repo (dedupe lookup)."""
    stmt = select(TaskPacketRow).where(
        TaskPacketRow.delivery_id == delivery_id,
        TaskPacketRow.repo == repo,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return TaskPacketRead.model_validate(row)


async def get_by_correlation_id(
    session: AsyncSession, correlation_id: UUID
) -> TaskPacketRead | None:
    """Get a TaskPacket by correlation_id."""
    stmt = select(TaskPacketRow).where(TaskPacketRow.correlation_id == correlation_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return TaskPacketRead.model_validate(row)


async def update_status(
    session: AsyncSession, task_id: UUID, new_status: TaskPacketStatus
) -> TaskPacketRead:
    """Update the status of a TaskPacket with transition validation."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")

    current = row.status
    if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionError(current, new_status)

    row.status = new_status
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def update_enrichment(
    session: AsyncSession,
    task_id: UUID,
    scope: dict[str, Any],
    risk_flags: dict[str, bool],
    complexity_index: dict[str, Any],
    context_packs: list[dict[str, Any]],
) -> TaskPacketRead:
    """Update enrichment fields and transition status to ENRICHED."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")

    current = row.status
    if TaskPacketStatus.ENRICHED not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionError(current, TaskPacketStatus.ENRICHED)

    row.scope = scope
    row.risk_flags = risk_flags
    row.complexity_index = complexity_index
    row.context_packs = context_packs
    row.status = TaskPacketStatus.ENRICHED
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def update_intent(
    session: AsyncSession,
    task_id: UUID,
    intent_spec_id: UUID,
    intent_version: int,
) -> TaskPacketRead:
    """Update intent reference and transition status to INTENT_BUILT."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")

    current = row.status
    if TaskPacketStatus.INTENT_BUILT not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidStatusTransitionError(current, TaskPacketStatus.INTENT_BUILT)

    row.intent_spec_id = intent_spec_id
    row.intent_version = intent_version
    row.status = TaskPacketStatus.INTENT_BUILT
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def update_intent_version(
    session: AsyncSession,
    task_id: UUID,
    intent_spec_id: UUID,
    intent_version: int,
) -> TaskPacketRead:
    """Update intent reference without changing status (for refinement)."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")

    row.intent_spec_id = intent_spec_id
    row.intent_version = intent_version
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def get_by_repo_and_issue(
    session: AsyncSession, repo: str, issue_id: int
) -> TaskPacketRead | None:
    """Get the most recent TaskPacket for a repo + issue number."""
    stmt = (
        select(TaskPacketRow)
        .where(TaskPacketRow.repo == repo, TaskPacketRow.issue_id == issue_id)
        .order_by(TaskPacketRow.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return TaskPacketRead.model_validate(row)


async def update_readiness_hold(
    session: AsyncSession,
    task_id: UUID,
    comment_id: str,
    readiness_score: float,
    evaluation_count: int,
) -> TaskPacketRead:
    """Record readiness hold data on a TaskPacket."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.readiness_hold_comment_id = comment_id
    row.readiness_score = readiness_score
    row.readiness_evaluation_count = evaluation_count
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def increment_readiness_evaluation(
    session: AsyncSession, task_id: UUID
) -> int:
    """Increment and return the readiness evaluation count."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.readiness_evaluation_count += 1
    await session.commit()
    await session.refresh(row)
    return row.readiness_evaluation_count


async def mark_readiness_miss(session: AsyncSession, task_id: UUID) -> None:
    """Flag a TaskPacket as a readiness miss (for calibration)."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.readiness_miss = True
    await session.commit()


async def increment_loopback(session: AsyncSession, task_id: UUID) -> int:
    """Increment and return the loopback count."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.loopback_count += 1
    await session.commit()
    await session.refresh(row)
    return row.loopback_count
