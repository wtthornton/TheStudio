"""Budget configuration — ORM model, Pydantic schemas, and CRUD.

Stores operator-defined budget thresholds and automated response actions.
A singleton row (fixed UUID) is the canonical source of truth.

Table:
  * ``budget_config`` — singleton row with spend limits and action flags

Migration: ``src/db/migrations/039_budget_config.py``
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float
from sqlalchemy import Uuid as SaUuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class BudgetConfigRow(Base):
    """Singleton row holding budget configuration for the platform.

    Only one row should ever exist (``id == SINGLETON_ID``).  All threshold
    values are in USD.  ``downgrade_threshold_percent`` is in the range 0–100.
    """

    __tablename__ = "budget_config"

    #: Fixed sentinel UUID so there is always exactly one row.
    SINGLETON_ID: UUID = UUID("00000000-0000-0000-0000-000000000002")

    id: Mapped[UUID] = mapped_column(SaUuid, primary_key=True, default=uuid4)

    # --- Spend thresholds (USD) ---
    daily_spend_warning: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Daily spend warning threshold in USD"
    )
    weekly_budget_cap: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Hard weekly budget cap in USD"
    )
    per_task_warning: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Per-task spend warning threshold in USD"
    )

    # --- Automated response actions ---
    pause_on_budget_exceeded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Pause all active workflows when weekly_budget_cap is breached"
    )
    model_downgrade_on_approach: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Switch to cheaper models when spend approaches the cap"
    )
    downgrade_threshold_percent: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0,
        comment="Percent of weekly_budget_cap that triggers model downgrade (0–100)"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class BudgetConfigRead(BaseModel):
    """Output schema for budget configuration."""

    daily_spend_warning: float | None
    weekly_budget_cap: float | None
    per_task_warning: float | None
    pause_on_budget_exceeded: bool
    model_downgrade_on_approach: bool
    downgrade_threshold_percent: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetConfigUpdate(BaseModel):
    """Input schema for updating budget configuration (all fields optional)."""

    daily_spend_warning: float | None = Field(
        None, ge=0.0, description="Daily spend warning threshold in USD"
    )
    weekly_budget_cap: float | None = Field(
        None, ge=0.0, description="Hard weekly budget cap in USD"
    )
    per_task_warning: float | None = Field(
        None, ge=0.0, description="Per-task spend warning threshold in USD"
    )
    pause_on_budget_exceeded: bool | None = Field(
        None,
        description="Pause all active workflows when weekly_budget_cap is breached",
    )
    model_downgrade_on_approach: bool | None = Field(
        None,
        description="Switch to cheaper models when spend approaches the cap",
    )
    downgrade_threshold_percent: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Percent of weekly_budget_cap that triggers model downgrade",
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


async def get_budget_config(session: AsyncSession) -> BudgetConfigRead:
    """Return the budget config singleton, creating defaults if absent."""
    row = await session.get(BudgetConfigRow, BudgetConfigRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_config(session)
    return BudgetConfigRead.model_validate(row)


async def update_budget_config(
    session: AsyncSession,
    payload: BudgetConfigUpdate,
) -> BudgetConfigRead:
    """Apply a partial update to the budget config singleton."""
    row = await session.get(BudgetConfigRow, BudgetConfigRow.SINGLETON_ID)
    if row is None:
        row = await _create_default_config(session)

    if payload.daily_spend_warning is not None:
        row.daily_spend_warning = payload.daily_spend_warning
    if payload.weekly_budget_cap is not None:
        row.weekly_budget_cap = payload.weekly_budget_cap
    if payload.per_task_warning is not None:
        row.per_task_warning = payload.per_task_warning
    if payload.pause_on_budget_exceeded is not None:
        row.pause_on_budget_exceeded = payload.pause_on_budget_exceeded
    if payload.model_downgrade_on_approach is not None:
        row.model_downgrade_on_approach = payload.model_downgrade_on_approach
    if payload.downgrade_threshold_percent is not None:
        row.downgrade_threshold_percent = payload.downgrade_threshold_percent

    row.updated_at = _utcnow()
    await session.flush()
    return BudgetConfigRead.model_validate(row)


async def _create_default_config(session: AsyncSession) -> BudgetConfigRow:
    """Insert the budget config singleton with safe defaults."""
    row = BudgetConfigRow(
        id=BudgetConfigRow.SINGLETON_ID,
        daily_spend_warning=None,
        weekly_budget_cap=None,
        per_task_warning=None,
        pause_on_budget_exceeded=False,
        model_downgrade_on_approach=False,
        downgrade_threshold_percent=80.0,
        updated_at=_utcnow(),
    )
    session.add(row)
    await session.flush()
    return row
