"""CRUD operations for Expert Library."""

from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.experts.expert import (
    ExpertClass,
    ExpertCreate,
    ExpertRead,
    ExpertRow,
    ExpertVersionRead,
    ExpertVersionRow,
    LifecycleState,
    TrustTier,
)


async def create_expert(session: AsyncSession, data: ExpertCreate) -> ExpertRead:
    """Create a new expert with its initial version definition."""
    row = ExpertRow(
        name=data.name,
        expert_class=data.expert_class,
        capability_tags=data.capability_tags,
        scope_description=data.scope_description,
        tool_policy=data.tool_policy,
        trust_tier=data.trust_tier,
        current_version=1,
    )
    session.add(row)
    await session.flush()

    version_row = ExpertVersionRow(
        expert_id=row.id,
        version=1,
        definition=data.definition,
    )
    session.add(version_row)
    await session.commit()
    await session.refresh(row)
    return ExpertRead.model_validate(row)


async def get_expert(session: AsyncSession, expert_id: UUID) -> ExpertRead | None:
    """Get an expert by primary key."""
    row = await session.get(ExpertRow, expert_id)
    if row is None:
        return None
    return ExpertRead.model_validate(row)


async def get_expert_by_name(session: AsyncSession, name: str) -> ExpertRead | None:
    """Get an expert by unique name."""
    stmt = select(ExpertRow).where(ExpertRow.name == name)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return ExpertRead.model_validate(row)


async def update_expert_version(
    session: AsyncSession,
    expert_id: UUID,
    definition: dict[str, object],
) -> ExpertRead:
    """Create a new version of an existing expert (increment version, preserve prior)."""
    row = await session.get(ExpertRow, expert_id)
    if row is None:
        raise ValueError(f"Expert {expert_id} not found")

    new_version = row.current_version + 1
    row.current_version = new_version

    version_row = ExpertVersionRow(
        expert_id=expert_id,
        version=new_version,
        definition=definition,
    )
    session.add(version_row)
    await session.commit()
    await session.refresh(row)
    return ExpertRead.model_validate(row)


async def deprecate_expert(session: AsyncSession, expert_id: UUID) -> ExpertRead:
    """Mark an expert as deprecated (discoverable but ineligible for routing)."""
    row = await session.get(ExpertRow, expert_id)
    if row is None:
        raise ValueError(f"Expert {expert_id} not found")
    row.lifecycle_state = LifecycleState.DEPRECATED
    await session.commit()
    await session.refresh(row)
    return ExpertRead.model_validate(row)


async def retire_expert(session: AsyncSession, expert_id: UUID) -> ExpertRead:
    """Mark an expert as retired."""
    row = await session.get(ExpertRow, expert_id)
    if row is None:
        raise ValueError(f"Expert {expert_id} not found")
    row.lifecycle_state = LifecycleState.RETIRED
    await session.commit()
    await session.refresh(row)
    return ExpertRead.model_validate(row)


async def search_experts(
    session: AsyncSession,
    expert_class: ExpertClass | None = None,
    capability_tags: list[str] | None = None,
    include_deprecated: bool = False,
) -> list[ExpertRead]:
    """Search experts by class and capability tags.

    Results are ordered by trust_tier (trusted > probation > shadow).
    Retired experts are always excluded. Deprecated experts excluded by default.
    """
    stmt = select(ExpertRow)

    # Exclude retired always
    if include_deprecated:
        stmt = stmt.where(ExpertRow.lifecycle_state != LifecycleState.RETIRED)
    else:
        stmt = stmt.where(ExpertRow.lifecycle_state == LifecycleState.ACTIVE)

    if expert_class is not None:
        stmt = stmt.where(ExpertRow.expert_class == expert_class)

    if capability_tags:
        # Match experts whose capability_tags overlap with requested tags
        stmt = stmt.where(ExpertRow.capability_tags.overlap(capability_tags))

    # Order by trust tier descending (trusted=3, probation=2, shadow=1)
    tier_order = case(
        (ExpertRow.trust_tier == TrustTier.TRUSTED, 3),
        (ExpertRow.trust_tier == TrustTier.PROBATION, 2),
        else_=1,
    )
    stmt = stmt.order_by(tier_order.desc(), ExpertRow.name.asc())

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [ExpertRead.model_validate(r) for r in rows]


async def get_expert_versions(
    session: AsyncSession, expert_id: UUID
) -> list[ExpertVersionRead]:
    """Get all versions of an expert, ordered by version ascending."""
    stmt = (
        select(ExpertVersionRow)
        .where(ExpertVersionRow.expert_id == expert_id)
        .order_by(ExpertVersionRow.version.asc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [ExpertVersionRead.model_validate(r) for r in rows]
