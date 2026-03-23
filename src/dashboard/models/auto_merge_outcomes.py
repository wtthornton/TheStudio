"""Auto-merge outcome tracking — ORM model, Pydantic schemas, and CRUD.

Records the outcome of each auto-merged PR (succeeded, reverted, or issue_detected)
for rule health analysis and dashboard visibility.

Table: ``auto_merge_outcomes``
Migration: ``src/db/migrations/046_auto_merge_outcomes.py``

Epic 42 Story 42.10.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy import Uuid as SaUuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

# Valid outcome values
OutcomeValue = Literal["succeeded", "reverted", "issue_detected"]


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class AutoMergeOutcomeRow(Base):
    """One row per auto-merged PR, recording its post-merge outcome.

    Created by the ``monitor_post_merge_activity`` after the 24-hour
    monitoring window closes (or earlier if a revert/issue is detected).
    """

    __tablename__ = "auto_merge_outcomes"

    id: Mapped[UUID] = mapped_column(SaUuid, primary_key=True, default=uuid4)
    taskpacket_id: Mapped[UUID] = mapped_column(SaUuid, nullable=False)
    rule_id: Mapped[UUID | None] = mapped_column(SaUuid, nullable=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo: Mapped[str] = mapped_column(String(500), nullable=False)
    merged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        String(50), nullable=False, default="succeeded"
    )  # succeeded | reverted | issue_detected
    detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revert_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linked_issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AutoMergeOutcomeCreate(BaseModel):
    """Input schema for recording an auto-merge outcome."""

    taskpacket_id: UUID
    rule_id: UUID | None = None
    pr_number: int
    repo: str
    merged_at: datetime
    outcome: str = "succeeded"
    detected_at: datetime | None = None
    revert_sha: str | None = None
    linked_issue_number: int | None = None
    notes: str | None = None


class AutoMergeOutcomeRead(BaseModel):
    """Output schema for an auto-merge outcome record."""

    id: UUID
    taskpacket_id: UUID
    rule_id: UUID | None
    pr_number: int
    repo: str
    merged_at: datetime
    outcome: str
    detected_at: datetime | None
    revert_sha: str | None
    linked_issue_number: int | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_outcome(
    session: AsyncSession,
    payload: AutoMergeOutcomeCreate,
) -> AutoMergeOutcomeRead:
    """Persist a new auto-merge outcome record."""
    now = _utcnow()
    row = AutoMergeOutcomeRow(
        id=uuid4(),
        taskpacket_id=payload.taskpacket_id,
        rule_id=payload.rule_id,
        pr_number=payload.pr_number,
        repo=payload.repo,
        merged_at=payload.merged_at,
        outcome=payload.outcome,
        detected_at=payload.detected_at,
        revert_sha=payload.revert_sha,
        linked_issue_number=payload.linked_issue_number,
        notes=payload.notes,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return AutoMergeOutcomeRead.model_validate(row)


async def list_outcomes(
    session: AsyncSession,
    *,
    period_days: int = 7,
    repo: str | None = None,
    outcome: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AutoMergeOutcomeRead]:
    """Return auto-merge outcomes filtered by period, repo, and outcome type."""
    from datetime import timedelta

    cutoff = _utcnow() - timedelta(days=period_days)
    stmt = (
        select(AutoMergeOutcomeRow)
        .where(AutoMergeOutcomeRow.created_at >= cutoff)
        .order_by(AutoMergeOutcomeRow.created_at.desc())
    )
    if repo:
        stmt = stmt.where(AutoMergeOutcomeRow.repo == repo)
    if outcome:
        stmt = stmt.where(AutoMergeOutcomeRow.outcome == outcome)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [AutoMergeOutcomeRead.model_validate(r) for r in result.scalars()]


async def list_outcomes_for_rule(
    session: AsyncSession,
    rule_id: UUID,
    *,
    period_days: int = 30,
) -> list[AutoMergeOutcomeRead]:
    """Return all outcomes for a specific rule within the period."""
    from datetime import timedelta

    cutoff = _utcnow() - timedelta(days=period_days)
    stmt = (
        select(AutoMergeOutcomeRow)
        .where(
            AutoMergeOutcomeRow.rule_id == rule_id,
            AutoMergeOutcomeRow.created_at >= cutoff,
        )
        .order_by(AutoMergeOutcomeRow.created_at.desc())
    )
    result = await session.execute(stmt)
    return [AutoMergeOutcomeRead.model_validate(r) for r in result.scalars()]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
