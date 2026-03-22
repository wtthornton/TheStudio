"""Budget API endpoints — spend summary, history, and breakdowns.

Endpoints:
- GET /budget/summary      — total spend, call count, cache stats for a time window
- GET /budget/history      — time-series spend by model (daily buckets)
- GET /budget/by-stage     — spend aggregated by pipeline stage (step)
- GET /budget/by-model     — spend aggregated by model

All data is sourced from ModelCallAudit records via the existing
``get_spend_report`` and ``_aggregate`` helpers in ``src.admin.model_spend``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from src.admin.model_spend import SpendSummary, get_spend_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/budget", tags=["budget"])


def _summary_to_dict(s: SpendSummary) -> dict[str, Any]:
    return s.to_dict()


# ---------------------------------------------------------------------------
# Budget endpoints
# ---------------------------------------------------------------------------


@router.get("/summary")
async def get_budget_summary(
    window_hours: int = Query(24, ge=1, le=8760, description="Look-back window in hours"),
) -> dict[str, Any]:
    """Return total spend summary for the given time window.

    Aggregates all ModelCallAudit records within ``window_hours`` and returns
    totals for cost, call count, tokens, and cache statistics.
    """
    report = get_spend_report(window_hours=window_hours)
    return {
        "window_hours": report.window_hours,
        "total_cost": round(report.total_cost, 6),
        "total_calls": report.total_calls,
        "total_cache_creation_tokens": report.total_cache_creation_tokens,
        "total_cache_read_tokens": report.total_cache_read_tokens,
        "cache_hit_rate": round(report.cache_hit_rate, 4),
    }


@router.get("/history")
async def get_budget_history(
    window_hours: int = Query(168, ge=1, le=8760, description="Look-back window in hours (default 7 days)"),
) -> dict[str, Any]:
    """Return time-series spend broken down by model, bucketed by day.

    Each entry in ``by_day`` carries the date as key and aggregated cost
    across all models.  ``by_model`` gives the per-model totals for the
    full window — useful for stacked-bar chart rendering.
    """
    report = get_spend_report(window_hours=window_hours)
    return {
        "window_hours": report.window_hours,
        "total_cost": round(report.total_cost, 6),
        "total_calls": report.total_calls,
        "by_day": [_summary_to_dict(s) for s in report.by_day],
        "by_model": [_summary_to_dict(s) for s in report.by_model],
    }


@router.get("/by-stage")
async def get_budget_by_stage(
    window_hours: int = Query(24, ge=1, le=8760, description="Look-back window in hours"),
) -> dict[str, Any]:
    """Return spend aggregated by pipeline stage (step field on ModelCallAudit).

    Stages correspond to the 9-step pipeline (intake, context, intent,
    routing, assembler, agent, verification, qa, publisher).  Records
    without a step are grouped under ``unknown``.
    """
    report = get_spend_report(window_hours=window_hours)
    return {
        "window_hours": report.window_hours,
        "total_cost": round(report.total_cost, 6),
        "total_calls": report.total_calls,
        "by_stage": [_summary_to_dict(s) for s in report.by_step],
    }


@router.get("/by-model")
async def get_budget_by_model(
    window_hours: int = Query(24, ge=1, le=8760, description="Look-back window in hours"),
) -> dict[str, Any]:
    """Return spend aggregated by model identifier.

    Each entry includes total cost, token counts, call count, average
    latency, and error count for that model within the time window.
    """
    report = get_spend_report(window_hours=window_hours)
    return {
        "window_hours": report.window_hours,
        "total_cost": round(report.total_cost, 6),
        "total_calls": report.total_calls,
        "by_model": [_summary_to_dict(s) for s in report.by_model],
    }
