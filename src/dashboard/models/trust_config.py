"""Trust tier configuration — ORM models, Pydantic schemas, and CRUD.

Stores operator-defined rules that map TaskPacket metadata to a trust tier
(observe / suggest / execute).  A companion SafetyBounds singleton limits the
blast radius of automated actions regardless of tier.

Tables:
  * ``trust_tier_rules``   — ordered list of conditional tier rules
  * ``trust_safety_bounds`` — singleton row that caps automated actions

Migration: ``src/db/migrations/035_trust_config.py``
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy import Uuid as SaUuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssignedTier(enum.StrEnum):
    """Trust tier values used by the dashboard rule engine.

    These map to the pipeline trust-tier contract (observe → suggest →
    execute) rather than the reputation-tier taxonomy in
    ``src/reputation/tiers.py`` (shadow / probation / trusted).
    """

    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


class ConditionOperator(enum.StrEnum):
    """Supported comparison operators for rule conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    CONTAINS = "contains"
    MATCHES_GLOB = "matches_glob"


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class TrustTierRuleRow(Base):
    """One row in the ordered list of trust-tier assignment rules.

    Conditions are stored as a JSON array of objects:
    ``[{"field": "complexity_index", "op": "greater_than", "value": 0.8}]``

    All conditions in a rule must match (AND logic).  Rules are evaluated in
    ascending ``priority`` order; the first match wins.
    """

    __tablename__ = "trust_tier_rules"

    id: Mapped[UUID] = mapped_column(SaUuid, primary_key=True, default=uuid4)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    assigned_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dry_run: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class TrustSafetyBoundsRow(Base):
    """Singleton row that caps automated-action scope regardless of tier.

    Only one row should ever exist (id = fixed sentinel UUID).
    ``mandatory_review_patterns`` is a JSON array of glob strings.
    ``default_tier`` is the fallback tier when no rule matches.
    """

    __tablename__ = "trust_safety_bounds"

    #: Fixed sentinel UUID so there is always exactly one row.
    SINGLETON_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")

    id: Mapped[UUID] = mapped_column(SaUuid, primary_key=True, default=uuid4)
    max_auto_merge_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_auto_merge_cost: Mapped[float | None] = mapped_column(
        # Store as integer cents to avoid float precision issues
        Integer,
        nullable=True,
        comment="Max auto-merge cost in USD cents",
    )
    max_loopbacks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mandatory_review_patterns: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    default_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="observe"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas — conditions
# ---------------------------------------------------------------------------


class RuleCondition(BaseModel):
    """One atomic condition within a trust-tier rule."""

    field: str = Field(..., description="TaskPacket field path, e.g. 'complexity_index'")
    op: ConditionOperator
    value: Any = Field(..., description="Scalar value to compare against")


# ---------------------------------------------------------------------------
# Pydantic schemas — TrustTierRule
# ---------------------------------------------------------------------------


class TrustTierRuleCreate(BaseModel):
    """Input schema for creating a new trust-tier rule."""

    priority: int = Field(100, ge=1, le=9999)
    conditions: list[RuleCondition] = Field(default_factory=list)
    assigned_tier: AssignedTier
    active: bool = True
    dry_run: bool = False
    description: str | None = Field(None, max_length=500)


class TrustTierRuleUpdate(BaseModel):
    """Partial update schema for a trust-tier rule (all fields optional)."""

    priority: int | None = Field(None, ge=1, le=9999)
    conditions: list[RuleCondition] | None = None
    assigned_tier: AssignedTier | None = None
    active: bool | None = None
    dry_run: bool | None = None
    description: str | None = Field(None, max_length=500)


class TrustTierRuleRead(BaseModel):
    """Output schema for a trust-tier rule."""

    id: UUID
    priority: int
    conditions: list[RuleCondition]
    assigned_tier: AssignedTier
    active: bool
    dry_run: bool = False
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pydantic schemas — SafetyBounds
# ---------------------------------------------------------------------------


class SafeBoundsUpdate(BaseModel):
    """Input schema for updating safety bounds (all fields optional)."""

    max_auto_merge_lines: int | None = Field(None, ge=1)
    max_auto_merge_cost: int | None = Field(
        None, ge=0, description="Max cost in USD cents"
    )
    max_loopbacks: int | None = Field(None, ge=0)
    mandatory_review_patterns: list[str] | None = None


class SafeBoundsRead(BaseModel):
    """Output schema for safety bounds."""

    max_auto_merge_lines: int | None
    max_auto_merge_cost: int | None
    max_loopbacks: int | None
    mandatory_review_patterns: list[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pydantic schemas — DefaultTier
# ---------------------------------------------------------------------------


class DefaultTierRead(BaseModel):
    """Output schema for the default trust tier."""

    default_tier: AssignedTier
    updated_at: datetime

    model_config = {"from_attributes": True}


class DefaultTierUpdate(BaseModel):
    """Input schema for setting the default trust tier."""

    default_tier: AssignedTier


# ---------------------------------------------------------------------------
# CRUD — TrustTierRule
# ---------------------------------------------------------------------------


async def create_rule(
    session: AsyncSession,
    payload: TrustTierRuleCreate,
) -> TrustTierRuleRead:
    """Persist a new trust-tier rule and return the read schema."""
    now = _utcnow()
    row = TrustTierRuleRow(
        id=uuid4(),
        priority=payload.priority,
        conditions=[c.model_dump() for c in payload.conditions],
        assigned_tier=payload.assigned_tier.value,
        active=payload.active,
        dry_run=payload.dry_run,
        description=payload.description,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return _rule_read(row)


async def get_rule(session: AsyncSession, rule_id: UUID) -> TrustTierRuleRead | None:
    """Return a single trust-tier rule or None if not found."""
    row = await session.get(TrustTierRuleRow, rule_id)
    return _rule_read(row) if row else None


async def list_rules(
    session: AsyncSession,
    *,
    active_only: bool = False,
) -> list[TrustTierRuleRead]:
    """Return all rules ordered by priority ascending."""
    stmt = select(TrustTierRuleRow).order_by(TrustTierRuleRow.priority.asc())
    if active_only:
        stmt = stmt.where(TrustTierRuleRow.active.is_(True))
    result = await session.execute(stmt)
    return [_rule_read(r) for r in result.scalars()]


async def update_rule(
    session: AsyncSession,
    rule_id: UUID,
    payload: TrustTierRuleUpdate,
) -> TrustTierRuleRead | None:
    """Apply a partial update to an existing rule.  Returns None if not found."""
    row = await session.get(TrustTierRuleRow, rule_id)
    if row is None:
        return None
    if payload.priority is not None:
        row.priority = payload.priority
    if payload.conditions is not None:
        row.conditions = [c.model_dump() for c in payload.conditions]
    if payload.assigned_tier is not None:
        row.assigned_tier = payload.assigned_tier.value
    if payload.active is not None:
        row.active = payload.active
    if payload.dry_run is not None:
        row.dry_run = payload.dry_run
    if payload.description is not None:
        row.description = payload.description
    row.updated_at = _utcnow()
    await session.flush()
    return _rule_read(row)


async def delete_rule(session: AsyncSession, rule_id: UUID) -> bool:
    """Delete a rule by ID.  Returns True if deleted, False if not found."""
    row = await session.get(TrustTierRuleRow, rule_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


# ---------------------------------------------------------------------------
# CRUD — SafetyBounds
# ---------------------------------------------------------------------------


async def get_safety_bounds(session: AsyncSession) -> SafeBoundsRead:
    """Return the safety bounds singleton, creating defaults if absent."""
    row = await session.get(TrustSafetyBoundsRow, TrustSafetyBoundsRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_bounds(session)
    return SafeBoundsRead.model_validate(row)


async def update_safety_bounds(
    session: AsyncSession,
    payload: SafeBoundsUpdate,
) -> SafeBoundsRead:
    """Update the safety bounds singleton, creating defaults if absent."""
    row = await session.get(TrustSafetyBoundsRow, TrustSafetyBoundsRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_bounds(session)
    if payload.max_auto_merge_lines is not None:
        row.max_auto_merge_lines = payload.max_auto_merge_lines
    if payload.max_auto_merge_cost is not None:
        row.max_auto_merge_cost = payload.max_auto_merge_cost
    if payload.max_loopbacks is not None:
        row.max_loopbacks = payload.max_loopbacks
    if payload.mandatory_review_patterns is not None:
        row.mandatory_review_patterns = payload.mandatory_review_patterns
    row.updated_at = _utcnow()
    await session.flush()
    return SafeBoundsRead.model_validate(row)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return current UTC time (timezone-naive for SQLAlchemy compat)."""

    return datetime.now(tz=UTC)


async def get_default_tier(session: AsyncSession) -> DefaultTierRead:
    """Return the default trust tier from the singleton, creating defaults if absent."""
    row = await session.get(TrustSafetyBoundsRow, TrustSafetyBoundsRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_bounds(session)
    return DefaultTierRead(
        default_tier=AssignedTier(row.default_tier),
        updated_at=row.updated_at,
    )


async def update_default_tier(
    session: AsyncSession,
    payload: DefaultTierUpdate,
) -> DefaultTierRead:
    """Update the default trust tier on the singleton."""
    row = await session.get(TrustSafetyBoundsRow, TrustSafetyBoundsRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_bounds(session)
    row.default_tier = payload.default_tier.value
    row.updated_at = _utcnow()
    await session.flush()
    return DefaultTierRead(
        default_tier=AssignedTier(row.default_tier),
        updated_at=row.updated_at,
    )


async def _create_default_bounds(session: AsyncSession) -> TrustSafetyBoundsRow:
    """Insert the safety bounds singleton with sensible defaults."""
    row = TrustSafetyBoundsRow(
        id=TrustSafetyBoundsRow.SINGLETON_ID,
        max_auto_merge_lines=500,
        max_auto_merge_cost=500,  # $5.00 in cents
        max_loopbacks=3,
        mandatory_review_patterns=["**/migrations/**", "**/settings*"],
        default_tier="observe",
        updated_at=_utcnow(),
    )
    session.add(row)
    await session.flush()
    return row


def _rule_read(row: TrustTierRuleRow) -> TrustTierRuleRead:
    """Convert an ORM row to a read schema, deserialising conditions."""
    conditions = [RuleCondition.model_validate(c) for c in (row.conditions or [])]
    return TrustTierRuleRead(
        id=row.id,
        priority=row.priority,
        conditions=conditions,
        assigned_tier=AssignedTier(row.assigned_tier),
        active=row.active,
        dry_run=getattr(row, "dry_run", False),
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
