"""CRUD operations for Intent Specification."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.intent.intent_spec import IntentSpecCreate, IntentSpecRead, IntentSpecRow


async def create_intent(session: AsyncSession, data: IntentSpecCreate) -> IntentSpecRead:
    """Create an Intent Specification."""
    row = IntentSpecRow(
        taskpacket_id=data.taskpacket_id,
        version=data.version,
        goal=data.goal,
        constraints=data.constraints,
        acceptance_criteria=data.acceptance_criteria,
        non_goals=data.non_goals,
        source=data.source,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return IntentSpecRead.model_validate(row)


async def get_by_id(session: AsyncSession, intent_id: UUID) -> IntentSpecRead | None:
    """Get an Intent Specification by ID."""
    row = await session.get(IntentSpecRow, intent_id)
    if row is None:
        return None
    return IntentSpecRead.model_validate(row)


async def get_latest_for_taskpacket(
    session: AsyncSession, taskpacket_id: UUID
) -> IntentSpecRead | None:
    """Get the latest (highest version) Intent Specification for a TaskPacket."""
    stmt = (
        select(IntentSpecRow)
        .where(IntentSpecRow.taskpacket_id == taskpacket_id)
        .order_by(IntentSpecRow.version.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return IntentSpecRead.model_validate(row)


async def get_all_versions(
    session: AsyncSession, taskpacket_id: UUID
) -> list[IntentSpecRead]:
    """Get all Intent Specification versions for a TaskPacket, ordered by version."""
    stmt = (
        select(IntentSpecRow)
        .where(IntentSpecRow.taskpacket_id == taskpacket_id)
        .order_by(IntentSpecRow.version.asc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [IntentSpecRead.model_validate(r) for r in rows]
