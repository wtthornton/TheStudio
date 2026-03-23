"""Operational Analytics API endpoints (Epic 39, Slice 1).

Endpoints:
- GET /analytics/throughput  — tasks completed per day/week over a period
- GET /analytics/bottlenecks — avg time per pipeline stage
- GET /analytics/categories  — task breakdown by triage category
- GET /analytics/failures    — gate failures grouped by stage and type
- GET /analytics/summary     — summary cards with trend indicators

All endpoints accept ``period`` (7d | 30d | 90d, default 30d) as a query
parameter.  Data is sourced from the TaskPacket, gate_evidence, and
model_call_audit tables using the query functions in analytics_queries.py.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.analytics_queries import (
    query_bottlenecks,
    query_categories,
    query_failures,
    query_summary,
    query_throughput,
)
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Valid period values
PeriodType = Literal["7d", "30d", "90d"]
BucketType = Literal["day", "week"]


@router.get("/throughput")
async def get_throughput(
    period: PeriodType = Query("30d", description="Time period: 7d, 30d, or 90d"),
    bucket: BucketType = Query("day", description="Bucket size: day or week"),
    repo: str | None = Query(None, description="Filter by repo full_name (owner/repo)"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Throughput chart data — completed tasks per time bucket (Story 39.1).

    Groups all completed TaskPackets (status in PUBLISHED, REJECTED, FAILED,
    ABORTED) by their ``completed_at`` date, bucketed by day or week.

    When ``repo`` is provided, only tasks from that repository are counted.
    """
    return await query_throughput(session, period=period, bucket=bucket, repo=repo)


@router.get("/bottlenecks")
async def get_bottlenecks(
    period: PeriodType = Query("30d", description="Time period: 7d, 30d, or 90d"),
    repo: str | None = Query(None, description="Filter by repo full_name (owner/repo)"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Pipeline bottleneck analysis — avg time per stage (Story 39.2).

    Computes average and standard deviation of elapsed time per pipeline
    stage from the ``stage_timings`` JSONB column on completed TaskPackets.
    Highlights the slowest stage (highest avg) and most variable stage
    (highest stddev).

    When ``repo`` is provided, only tasks from that repository are included.
    """
    return await query_bottlenecks(session, period=period, repo=repo)


@router.get("/categories")
async def get_categories(
    period: PeriodType = Query("30d", description="Time period: 7d, 30d, or 90d"),
    repo: str | None = Query(None, description="Filter by repo full_name (owner/repo)"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Category breakdown — tasks grouped by triage category (Story 39.3).

    Groups completed tasks by ``triage_enrichment->>'category'``.  For
    each category, computes count, PR merge rate, average model cost,
    average pipeline time, and a low-sample warning flag (count < 3).

    When ``repo`` is provided, only tasks from that repository are included.
    """
    return await query_categories(session, period=period, repo=repo)


@router.get("/failures")
async def get_failures(
    period: PeriodType = Query("30d", description="Time period: 7d, 30d, or 90d"),
    repo: str | None = Query(None, description="Filter by repo full_name (owner/repo)"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Failure analysis — gate failures grouped by stage and type (Story 39.4).

    Groups gate_evidence failure records by stage and defect_category.
    Compares the current period against the previous period of the same
    length to compute a trend indicator (increasing / decreasing / stable).

    When ``repo`` is provided, gate evidence is filtered via a join to taskpacket.
    """
    return await query_failures(session, period=period, repo=repo)


@router.get("/summary")
async def get_summary(
    period: PeriodType = Query("30d", description="Time period: 7d, 30d, or 90d"),
    repo: str | None = Query(None, description="Filter by repo full_name (owner/repo)"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Summary cards — key metrics with trend indicators (Story 39.5).

    Returns four summary cards:
    - tasks_completed: total tasks reaching terminal status in the period
    - avg_pipeline_seconds: average time from creation to completion
    - pr_merge_rate: fraction of published PRs that were merged
    - total_spend_usd: total model API spend in the period

    Each card includes a ``trend`` field comparing the current period
    against the previous period of the same length (up / down / stable).

    When ``repo`` is provided, metrics are scoped to that repository only.
    """
    return await query_summary(session, period=period, repo=repo)
