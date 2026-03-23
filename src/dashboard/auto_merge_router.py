"""Auto-merge dashboard API endpoints (Epic 42 Story 42.12).

Endpoints:
- GET /auto-merge/outcomes?period=7d  — paginated list of auto-merge outcomes
- GET /auto-merge/rule-health          — per-rule success rates and health

Both endpoints accept a ``period`` query parameter (1d | 7d | 30d, default 7d).
The ``outcomes`` endpoint also supports ``repo`` and ``outcome`` filters.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.models.auto_merge_outcomes import list_outcomes
from src.dashboard.rule_health import get_rule_health_summary
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auto-merge", tags=["auto-merge"])

# Valid period values and their day equivalents
_PERIOD_DAYS: dict[str, int] = {"1d": 1, "7d": 7, "30d": 30}

PeriodType = Literal["1d", "7d", "30d"]


@router.get("/outcomes")
async def get_auto_merge_outcomes(
    period: PeriodType = Query("7d", description="Time range: 1d, 7d, or 30d"),
    repo: str | None = Query(None, description="Filter by repo (owner/repo)"),
    outcome: str | None = Query(
        None, description="Filter by outcome: succeeded | reverted | issue_detected"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Auto-merge outcome list with time-range and filter support (Story 42.12 AC5).

    Returns a paginated list of auto-merge outcomes within the given period.

    **Fields per outcome:**
    - ``id`` — outcome record UUID
    - ``taskpacket_id`` — UUID of the TaskPacket
    - ``rule_id`` — UUID of the matched trust-tier rule (may be null)
    - ``pr_number`` — GitHub PR number
    - ``repo`` — repository full name (owner/repo)
    - ``merged_at`` — ISO-8601 timestamp when auto-merge was enabled
    - ``outcome`` — "succeeded" | "reverted" | "issue_detected"
    - ``detected_at`` — ISO-8601 timestamp when the event was detected
    - ``revert_sha`` — Git SHA of the revert commit (only for "reverted")
    - ``linked_issue_number`` — GitHub issue number (only for "issue_detected")
    - ``created_at`` — ISO-8601 timestamp when this record was created
    """
    period_days = _PERIOD_DAYS.get(period, 7)

    rows = await list_outcomes(
        session,
        period_days=period_days,
        repo=repo,
        outcome=outcome,
        limit=limit,
        offset=offset,
    )

    outcomes_data = []
    for row in rows:
        outcomes_data.append({
            "id": str(row.id),
            "taskpacket_id": str(row.taskpacket_id),
            "rule_id": str(row.rule_id) if row.rule_id else None,
            "pr_number": row.pr_number,
            "repo": row.repo,
            "merged_at": row.merged_at.isoformat() if row.merged_at else None,
            "outcome": row.outcome,
            "detected_at": row.detected_at.isoformat() if row.detected_at else None,
            "revert_sha": row.revert_sha,
            "linked_issue_number": row.linked_issue_number,
            "created_at": row.created_at.isoformat(),
        })

    return {
        "period": period,
        "outcomes": outcomes_data,
        "count": len(outcomes_data),
        "limit": limit,
        "offset": offset,
    }


@router.get("/rule-health")
async def get_rule_health(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Per-rule success rates for Execute-tier trust rules (Story 42.12 AC5).

    Returns a list of health metrics for every Execute-tier trust-tier rule,
    including success rates based on auto-merge outcome counters.

    **Fields per rule:**
    - ``rule_id`` — UUID of the trust-tier rule
    - ``priority`` — rule evaluation priority (lower = earlier)
    - ``description`` — human-readable rule description
    - ``active`` — whether the rule is currently active
    - ``dry_run`` — whether the rule is in dry-run mode
    - ``merge_count`` — total auto-merges attributed to this rule
    - ``revert_count`` — reverts detected for auto-merges under this rule
    - ``success_rate`` — float 0-100 or null when merge_count < 20
    - ``deactivation_reason`` — why the rule was auto-deactivated (null if active)
    - ``sample_warning`` — true when merge_count < 20 (insufficient data)
    """
    health = await get_rule_health_summary(session)

    return {
        "rules": health,
        "count": len(health),
        "threshold_pct": 90,
        "min_samples": 20,
    }
