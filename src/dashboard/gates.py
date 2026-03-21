"""Dashboard gate endpoints — gate evidence listing, detail, and metrics.

Provides endpoints for the Gate Inspector panel (Epic 35, Slice 2):
- GET /tasks/:id/gates — gate results for a specific task
- GET /gates — paginated list of all gate events
- GET /gates/:id — gate detail with full evidence
- GET /gates/metrics — aggregated gate health metrics
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, DateTime, String, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.dashboard.events import _verify_token
from src.db.base import Base
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# SQLAlchemy model (S2.B2a)
# ---------------------------------------------------------------------------


class GateEvidenceRow(Base):
    """Gate pass/fail evidence record."""

    __tablename__ = "gate_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(index=True)
    stage: Mapped[str] = mapped_column(String(50))
    result: Mapped[str] = mapped_column(String(20))  # "pass" or "fail"
    checks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    defect_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_artifact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"),
    )


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class GateEvidenceRead(BaseModel):
    """Serialised gate evidence record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    stage: str
    result: str
    checks: dict | list | None = None
    defect_category: str | None = None
    evidence_artifact: dict | None = None
    created_at: datetime


class GateMetrics(BaseModel):
    """Aggregated gate health metrics over a time window."""

    window_hours: int
    total_gates: int
    pass_rate: float | None = None
    avg_issues: float | None = None
    top_failure_type: str | None = None
    loopback_rate: float | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks/{task_id}/gates")
async def list_task_gates(
    task_id: uuid.UUID,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[GateEvidenceRead]:
    """Gate results for a specific task, chronological order (S2.B1).

    Returns all GateEvidence entries associated with *task_id*,
    ordered by ``created_at`` ascending.
    """
    _verify_token(token)

    stmt = (
        select(GateEvidenceRow)
        .where(GateEvidenceRow.task_id == task_id)
        .order_by(GateEvidenceRow.created_at.asc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [GateEvidenceRead.model_validate(r) for r in rows]


@router.get("/gates/metrics")
async def gate_metrics(
    token: str | None = Query(None),
    window_hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GateMetrics:
    """Aggregated gate health metrics over a configurable window (S2.B5).

    Computes pass rate, average issues per gate, top failure type,
    and loopback rate within the specified time window.
    """
    _verify_token(token)

    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)

    # Total gates in window
    count_stmt = (
        select(func.count())
        .select_from(GateEvidenceRow)
        .where(GateEvidenceRow.created_at >= cutoff)
    )
    total_gates = (await session.execute(count_stmt)).scalar_one()

    if total_gates == 0:
        return GateMetrics(window_hours=window_hours, total_gates=0)

    # Pass count
    pass_count_stmt = (
        select(func.count())
        .select_from(GateEvidenceRow)
        .where(GateEvidenceRow.created_at >= cutoff)
        .where(GateEvidenceRow.result == "pass")
    )
    pass_count = (await session.execute(pass_count_stmt)).scalar_one()
    pass_rate = pass_count / total_gates if total_gates > 0 else None

    # Average issues: count non-null defect_category entries as "issues"
    issue_count_stmt = (
        select(func.count())
        .select_from(GateEvidenceRow)
        .where(GateEvidenceRow.created_at >= cutoff)
        .where(GateEvidenceRow.defect_category.isnot(None))
    )
    issue_count = (await session.execute(issue_count_stmt)).scalar_one()
    avg_issues = issue_count / total_gates if total_gates > 0 else None

    # Top failure type: most common defect_category among failures
    top_failure_type: str | None = None
    top_fail_stmt = (
        select(GateEvidenceRow.defect_category, func.count().label("cnt"))
        .where(GateEvidenceRow.created_at >= cutoff)
        .where(GateEvidenceRow.result == "fail")
        .where(GateEvidenceRow.defect_category.isnot(None))
        .group_by(GateEvidenceRow.defect_category)
        .order_by(func.count().desc())
        .limit(1)
    )
    top_fail_result = (await session.execute(top_fail_stmt)).first()
    if top_fail_result:
        top_failure_type = top_fail_result[0]

    # Loopback rate: tasks that have >1 gate entry for the same stage
    # (indicates a retry / loopback)
    loopback_rate: float | None = None
    loopback_stmt = select(func.count(func.distinct(GateEvidenceRow.task_id))).where(
        GateEvidenceRow.created_at >= cutoff
    )
    unique_tasks = (await session.execute(loopback_stmt)).scalar_one()
    if unique_tasks > 0:
        # Count tasks with duplicate stage entries (same task + stage > 1 row)
        loopback_sub = (
            select(GateEvidenceRow.task_id)
            .where(GateEvidenceRow.created_at >= cutoff)
            .group_by(GateEvidenceRow.task_id, GateEvidenceRow.stage)
            .having(func.count() > 1)
        )
        loopback_count_stmt = select(func.count(func.distinct(loopback_sub.c.task_id))).select_from(
            loopback_sub.subquery()
        )
        loopback_tasks = (await session.execute(loopback_count_stmt)).scalar_one()
        loopback_rate = loopback_tasks / unique_tasks

    return GateMetrics(
        window_hours=window_hours,
        total_gates=total_gates,
        pass_rate=round(pass_rate, 4) if pass_rate is not None else None,
        avg_issues=round(avg_issues, 4) if avg_issues is not None else None,
        top_failure_type=top_failure_type,
        loopback_rate=round(loopback_rate, 4) if loopback_rate is not None else None,
    )


@router.get("/gates/{gate_id}")
async def get_gate(
    gate_id: uuid.UUID,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GateEvidenceRead:
    """Gate detail with full evidence, checks, and decision rule (S2.B4).

    Returns 404 when the gate ID is not found.
    """
    _verify_token(token)

    row = await session.get(GateEvidenceRow, gate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Gate evidence not found")
    return GateEvidenceRead.model_validate(row)


@router.get("/gates")
async def list_gates(
    token: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    result: str | None = Query(None, description="Filter by 'pass' or 'fail'"),
    stage: str | None = Query(None),
    task_id: uuid.UUID | None = Query(None),  # noqa: B008
    created_after: datetime | None = Query(None),  # noqa: B008
    created_before: datetime | None = Query(None),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """List all gate events with pagination and filters (S2.B3).

    Supports filtering by result (pass/fail), stage, task_id, and date range.
    Returns newest-first ordering.
    """
    _verify_token(token)

    stmt = select(GateEvidenceRow)
    count_stmt = select(func.count()).select_from(GateEvidenceRow)

    # Apply filters
    if result is not None:
        stmt = stmt.where(GateEvidenceRow.result == result)
        count_stmt = count_stmt.where(GateEvidenceRow.result == result)
    if stage is not None:
        stmt = stmt.where(GateEvidenceRow.stage == stage)
        count_stmt = count_stmt.where(GateEvidenceRow.stage == stage)
    if task_id is not None:
        stmt = stmt.where(GateEvidenceRow.task_id == task_id)
        count_stmt = count_stmt.where(GateEvidenceRow.task_id == task_id)
    if created_after is not None:
        stmt = stmt.where(GateEvidenceRow.created_at >= created_after)
        count_stmt = count_stmt.where(GateEvidenceRow.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(GateEvidenceRow.created_at <= created_before)
        count_stmt = count_stmt.where(GateEvidenceRow.created_at <= created_before)

    # Get total count
    total = (await session.execute(count_stmt)).scalar_one()

    # Newest first, paginated
    stmt = stmt.order_by(GateEvidenceRow.created_at.desc()).offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [GateEvidenceRead.model_validate(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
