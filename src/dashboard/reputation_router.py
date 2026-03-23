"""Reputation & Outcomes API endpoints (Epic 39, Slice 2).

Endpoints:
- GET /reputation/experts         — Expert performance table (Story 39.12)
- GET /reputation/experts/{id}    — Expert detail + weight history (Story 39.18)
- GET /reputation/outcomes        — Recent outcome signals feed (Story 39.13)
- GET /reputation/drift           — Drift detection alerts + score (Stories 39.14+39.15)
- GET /reputation/summary         — Reputation summary cards (Story 39.16)

All endpoints are read-only. The reputation and outcome systems are the sole
authorities for their respective data; the dashboard reads but never writes.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.reputation_queries import (
    query_drift,
    query_expert_detail,
    query_experts,
    query_outcomes,
    query_reputation_summary,
)
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.get("/experts")
async def get_experts(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Expert performance table (Story 39.12).

    Returns all tracked experts with aggregated reputation weights,
    sample counts, confidence, trust tiers, and drift signals.
    Experts are sorted by average weight descending.
    """
    return await query_experts(session)


@router.get("/experts/{expert_id}")
async def get_expert_detail(
    expert_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Expert detail view — all contexts + weight history (Story 39.18).

    Returns per-context reputation rows for a single expert_id, including
    the ``weight_history`` array for trend sparkline rendering.

    Raises 404 if the expert_id is not found in the database.
    """
    data = await query_expert_detail(session, expert_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Expert {expert_id!r} not found")
    return data


@router.get("/outcomes")
async def get_outcomes(
    limit: int = Query(
        50, ge=1, le=200, description="Number of outcome entries to return"
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Outcome signals feed — recent outcomes chronologically (Story 39.13).

    Returns up to ``limit`` outcome signals with task context (issue_id,
    repo, status), outcome classification (success / failure / loopback),
    and extracted learnings for failure signals.

    Includes a ``total`` count of all persisted outcome signals.
    """
    return await query_outcomes(session, limit=limit)


@router.get("/drift")
async def get_drift(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Drift detection alerts with composite score (Stories 39.14 + 39.15).

    Compares four metrics over the current 14-day rolling window vs the
    previous equivalent period:
    1. Gate pass rate (from gate_evidence)
    2. Expert weight decline fraction (from expert_reputation)
    3. Model cost trend (from model_call_audit)
    4. Average loopback rate (from taskpacket.loopback_count)

    Each metric that crosses its threshold contributes to the composite
    drift score (low / moderate / high).

    Returns ``insufficient_data: true`` with an empty alerts list when fewer
    than 20 completed tasks exist in the window (avoids false positives).
    """
    return await query_drift(session)


@router.get("/summary")
async def get_reputation_summary(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Reputation summary cards (Story 39.16).

    Returns four summary cards for the 14-day rolling window:
    - success_rate: QA pass fraction with trend indicator
    - avg_loopbacks: average rework count per completed task with trend
    - pr_merge_rate: fraction of published PRs merged with trend
    - drift_score: composite drift level (low / moderate / high, no trend)
    """
    return await query_reputation_summary(session)
