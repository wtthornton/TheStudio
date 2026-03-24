"""CRUD operations for TaskPacket."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.taskpacket import (
    ALLOWED_TRANSITIONS,
    PrMergeStatus,
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
    # Set completed_at on first transition to a terminal status (Epic 39.0a)
    if new_status in _TERMINAL_STATUSES and row.completed_at is None:
        row.completed_at = datetime.now(UTC)
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


async def update_routing_result(
    session: AsyncSession,
    task_id: UUID,
    routing_result: dict[str, Any],
) -> TaskPacketRead:
    """Persist the full ConsultPlan (routing_result) to the TaskPacket.

    Called from router_activity after routing completes so the planning
    dashboard can display and review expert selections.
    """
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.routing_result = routing_result
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)


async def increment_loopback(session: AsyncSession, task_id: UUID) -> int:
    """Increment and return the loopback count."""
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    row.loopback_count += 1
    await session.commit()
    await session.refresh(row)
    return row.loopback_count


_TERMINAL_STATUSES = frozenset({
    TaskPacketStatus.PUBLISHED,
    TaskPacketStatus.FAILED,
    TaskPacketStatus.REJECTED,
    TaskPacketStatus.ABORTED,
})


async def list_active(session: AsyncSession) -> list[TaskPacketRow]:
    """Return all non-terminal TaskPacketRows.

    Epic 38.17 (force sync): Used to enumerate tasks that should be pushed
    to the GitHub Projects v2 board. Terminal tasks (PUBLISHED, FAILED,
    REJECTED, ABORTED) are excluded.
    """
    result = await session.execute(
        select(TaskPacketRow).where(
            TaskPacketRow.status.notin_([s.value for s in _TERMINAL_STATUSES])
        )
    )
    return list(result.scalars().all())


async def get_by_repo_and_pr_number(
    session: AsyncSession, repo: str, pr_number: int
) -> TaskPacketRow | None:
    """Get the TaskPacket for a repo + PR number.

    Used by the Epic 38 webhook bridge to resolve a pull_request event
    back to the originating TaskPacket for pr_merge_status updates (Epic 39.0b).

    Returns the raw ORM row (not a Pydantic read model) so callers can
    update fields directly in the same session.
    """
    stmt = (
        select(TaskPacketRow)
        .where(TaskPacketRow.repo == repo, TaskPacketRow.pr_number == pr_number)
        .order_by(TaskPacketRow.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_pr_merge_status(
    session: AsyncSession,
    task_id: UUID,
    merge_status: PrMergeStatus,
) -> TaskPacketRead:
    """Update the pr_merge_status field on a TaskPacket.

    Called by the Epic 38 webhook bridge (Story 38.24) or a manual update endpoint.
    Requires the task to exist and have a PR (pr_number not None).

    Epic 39.0b.
    """
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise ValueError(f"TaskPacket {task_id} not found")
    if row.pr_number is None:
        raise ValueError(f"TaskPacket {task_id} has no associated PR")
    row.pr_merge_status = merge_status
    await session.commit()
    await session.refresh(row)
    return TaskPacketRead.model_validate(row)

