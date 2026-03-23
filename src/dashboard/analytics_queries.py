"""Analytics SQL query functions for operational analytics endpoints (Epic 39, Slice 1).

Provides async query helpers that execute aggregation queries against
TaskPacketRow and related tables (gate_evidence, model_call_audit).
All functions accept an AsyncSession and return plain dicts suitable
for direct JSON serialization by the analytics router.

Design rationale:
- Uses ``text()`` for complex aggregations rather than ORM queries because
  multi-table aggregations with window functions are clearer in raw SQL.
- Each function handles missing/empty data gracefully (returns empty lists,
  zero values) rather than raising errors.
- Period arithmetic uses PostgreSQL ``interval`` casting for reliability.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Terminal statuses that count as "completed"
_TERMINAL_STATUSES = ("published", "rejected", "failed", "aborted")

# Canonical pipeline stages in order
_PIPELINE_STAGES = (
    "intake", "context", "intent", "routing", "assembler",
    "agent", "verification", "qa", "publisher",
)


def _period_to_interval(period: str) -> str:
    """Convert a period string (7d, 30d, 90d) to a PostgreSQL interval literal."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    return f"{days} days"


def _period_days(period: str) -> int:
    """Return the number of days in a period string."""
    return {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)


# ---------------------------------------------------------------------------
# 39.1 — Throughput
# ---------------------------------------------------------------------------


async def query_throughput(
    session: AsyncSession,
    period: str = "30d",
    bucket: str = "day",
    repo: str | None = None,
) -> dict[str, Any]:
    """Group completed TaskPackets by date bucket within the period.

    Args:
        session: Active DB session.
        period: Lookback period (7d, 30d, 90d).
        bucket: Aggregation bucket size (day or week).
        repo: Optional repo full_name filter (owner/repo).

    Returns ``{"period": "30d", "bucket": "day", "data": [{"date": "...", "count": N}, ...]}``.
    """
    interval = _period_to_interval(period)
    trunc = "day" if bucket == "day" else "week"

    sql = text("""
        SELECT date_trunc(:trunc, completed_at)::date AS bucket_date,
               count(*)::int AS cnt
        FROM taskpacket
        WHERE status IN ('published', 'rejected', 'failed', 'aborted')
          AND completed_at IS NOT NULL
          AND completed_at >= now() - :interval ::interval
          AND (:repo IS NULL OR repo = :repo)
        GROUP BY bucket_date
        ORDER BY bucket_date
    """)
    result = await session.execute(sql, {"trunc": trunc, "interval": interval, "repo": repo})
    rows = result.fetchall()

    return {
        "period": period,
        "bucket": bucket,
        "data": [{"date": str(r.bucket_date), "count": r.cnt} for r in rows],
    }


# ---------------------------------------------------------------------------
# 39.2 — Bottlenecks
# ---------------------------------------------------------------------------


async def query_bottlenecks(
    session: AsyncSession,
    period: str = "30d",
    repo: str | None = None,
) -> dict[str, Any]:
    """Compute avg and stddev of elapsed time per pipeline stage.

    Uses the ``stage_timings`` JSONB column.  Each entry is
    ``{stage_name: {"start": iso, "end": iso|null}}``.  Stages without
    an ``end`` timestamp are skipped.

    Args:
        session: Active DB session.
        period: Lookback period (7d, 30d, 90d).
        repo: Optional repo full_name filter (owner/repo).

    Returns ``{"period": "...", "stages": [...]}``.
    """
    interval = _period_to_interval(period)

    # Extract stage timings from JSONB, compute duration per stage
    sql = text("""
        WITH stage_data AS (
            SELECT
                key AS stage_name,
                EXTRACT(EPOCH FROM (
                    (value->>'end')::timestamptz - (value->>'start')::timestamptz
                )) AS duration_seconds
            FROM taskpacket,
                 jsonb_each(stage_timings::jsonb) AS kv(key, value)
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - :interval ::interval
              AND stage_timings IS NOT NULL
              AND value->>'end' IS NOT NULL
              AND value->>'start' IS NOT NULL
              AND (:repo IS NULL OR repo = :repo)
        ),
        stage_stats AS (
            SELECT
                stage_name,
                round(avg(duration_seconds)::numeric, 2) AS avg_seconds,
                round(coalesce(stddev_samp(duration_seconds), 0)::numeric, 2) AS stddev_seconds
            FROM stage_data
            WHERE duration_seconds >= 0
            GROUP BY stage_name
        )
        SELECT
            stage_name,
            avg_seconds,
            stddev_seconds,
            avg_seconds = (SELECT max(avg_seconds) FROM stage_stats) AS is_slowest,
            stddev_seconds = (SELECT max(stddev_seconds) FROM stage_stats) AS is_most_variable
        FROM stage_stats
        ORDER BY avg_seconds DESC
    """)
    result = await session.execute(sql, {"interval": interval, "repo": repo})
    rows = result.fetchall()

    return {
        "period": period,
        "stages": [
            {
                "stage": r.stage_name,
                "avg_seconds": float(r.avg_seconds),
                "stddev_seconds": float(r.stddev_seconds),
                "is_slowest": bool(r.is_slowest),
                "is_most_variable": bool(r.is_most_variable),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# 39.3 — Categories
# ---------------------------------------------------------------------------


async def query_categories(
    session: AsyncSession,
    period: str = "30d",
    repo: str | None = None,
) -> dict[str, Any]:
    """Group completed tasks by triage category with merge rate and cost.

    merge_rate = count of PUBLISHED with pr_merge_status='merged'
                 / count of PUBLISHED (in that category).
    avg_cost_usd: average cost from model_call_audit joined on task_id.
    low_sample: true if count < 3.

    Args:
        session: Active DB session.
        period: Lookback period (7d, 30d, 90d).
        repo: Optional repo full_name filter (owner/repo).
    """
    interval = _period_to_interval(period)

    sql = text("""
        WITH categorised AS (
            SELECT
                t.id,
                t.status,
                t.pr_merge_status,
                coalesce(t.triage_enrichment->>'category', 'other') AS category
            FROM taskpacket t
            WHERE t.status IN ('published', 'rejected', 'failed', 'aborted')
              AND t.completed_at IS NOT NULL
              AND t.completed_at >= now() - :interval ::interval
              AND (:repo IS NULL OR t.repo = :repo)
        ),
        cost_per_task AS (
            SELECT
                task_id,
                sum(cost) AS total_cost
            FROM model_call_audit
            WHERE task_id IS NOT NULL
            GROUP BY task_id
        ),
        timing_per_task AS (
            SELECT
                t.id AS task_id,
                EXTRACT(EPOCH FROM (t.completed_at - t.created_at)) AS pipeline_seconds
            FROM taskpacket t
            WHERE t.status IN ('published', 'rejected', 'failed', 'aborted')
              AND t.completed_at IS NOT NULL
              AND t.completed_at >= now() - :interval ::interval
              AND (:repo IS NULL OR t.repo = :repo)
        )
        SELECT
            c.category,
            count(*)::int AS cnt,
            count(*) FILTER (WHERE c.status = 'published' AND c.pr_merge_status = 'merged')::int AS merged_count,
            count(*) FILTER (WHERE c.status = 'published')::int AS published_count,
            round(coalesce(avg(cpt.total_cost), 0)::numeric, 6) AS avg_cost_usd,
            round(coalesce(avg(tpt.pipeline_seconds), 0)::numeric, 1) AS avg_pipeline_seconds
        FROM categorised c
        LEFT JOIN cost_per_task cpt ON cpt.task_id = c.id
        LEFT JOIN timing_per_task tpt ON tpt.task_id = c.id
        GROUP BY c.category
        ORDER BY cnt DESC
    """)

    result = await session.execute(sql, {"interval": interval, "repo": repo})
    rows = result.fetchall()

    categories = []
    for r in rows:
        merge_rate = (
            round(r.merged_count / r.published_count, 4)
            if r.published_count > 0
            else 0.0
        )
        categories.append({
            "category": r.category,
            "count": r.cnt,
            "merge_rate": merge_rate,
            "avg_cost_usd": float(r.avg_cost_usd),
            "avg_pipeline_seconds": float(r.avg_pipeline_seconds),
            "low_sample": r.cnt < 3,
        })

    return {"period": period, "categories": categories}


# ---------------------------------------------------------------------------
# 39.4 — Failures
# ---------------------------------------------------------------------------


async def query_failures(
    session: AsyncSession,
    period: str = "30d",
    repo: str | None = None,
) -> dict[str, Any]:
    """Gate failures grouped by stage, then by failure type.

    Trend compares count in current period vs same-length previous period.

    Args:
        session: Active DB session.
        period: Lookback period (7d, 30d, 90d).
        repo: Optional repo full_name filter — joins gate_evidence to taskpacket.
    """
    days = _period_days(period)
    interval = _period_to_interval(period)

    # Current period failures — join taskpacket when repo filter is needed
    sql = text("""
        WITH current_period AS (
            SELECT ge.stage, ge.defect_category, count(*)::int AS cnt
            FROM gate_evidence ge
            LEFT JOIN taskpacket t ON t.id = ge.task_id
            WHERE ge.result = 'fail'
              AND ge.created_at >= now() - :interval ::interval
              AND (:repo IS NULL OR t.repo = :repo)
            GROUP BY ge.stage, ge.defect_category
        ),
        previous_period AS (
            SELECT ge.stage, ge.defect_category, count(*)::int AS cnt
            FROM gate_evidence ge
            LEFT JOIN taskpacket t ON t.id = ge.task_id
            WHERE ge.result = 'fail'
              AND ge.created_at >= now() - (:days * 2)::int * interval '1 day'
              AND ge.created_at < now() - :interval ::interval
              AND (:repo IS NULL OR t.repo = :repo)
            GROUP BY ge.stage, ge.defect_category
        )
        SELECT
            cp.stage,
            coalesce(cp.defect_category, 'unknown') AS failure_type,
            cp.cnt AS current_count,
            coalesce(pp.cnt, 0) AS previous_count
        FROM current_period cp
        LEFT JOIN previous_period pp
          ON cp.stage = pp.stage
          AND coalesce(cp.defect_category, 'unknown') = coalesce(pp.defect_category, 'unknown')
        ORDER BY cp.stage, cp.cnt DESC
    """)

    result = await session.execute(sql, {"interval": interval, "days": days, "repo": repo})
    rows = result.fetchall()

    # Group by stage
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        stage = r.stage
        current = r.current_count
        previous = r.previous_count

        if current > previous:
            trend = "increasing"
        elif current < previous:
            trend = "decreasing"
        else:
            trend = "stable"

        if stage not in by_stage:
            by_stage[stage] = []
        by_stage[stage].append({
            "type": r.failure_type,
            "count": current,
            "trend": trend,
        })

    return {
        "period": period,
        "by_stage": [
            {"stage": stage, "failures": failures}
            for stage, failures in by_stage.items()
        ],
    }


# ---------------------------------------------------------------------------
# 39.5 — Summary cards
# ---------------------------------------------------------------------------


async def query_summary(
    session: AsyncSession,
    period: str = "30d",
    repo: str | None = None,
) -> dict[str, Any]:
    """Summary cards with trend comparison vs previous period.

    Cards: tasks_completed, avg_pipeline_seconds, pr_merge_rate, total_spend_usd.
    Each has ``value`` and ``trend`` (up | down | stable).

    Note: total_spend_usd is filtered by repo via a JOIN to taskpacket when
    ``repo`` is provided. When ``repo=None`` (All Repos), spend is global.

    Args:
        session: Active DB session.
        period: Lookback period (7d, 30d, 90d).
        repo: Optional repo full_name filter (owner/repo).
    """
    interval = _period_to_interval(period)
    days = _period_days(period)

    # Current period stats — repo filter applied to taskpacket; spend joined to taskpacket
    sql = text("""
        WITH current_tasks AS (
            SELECT
                count(*)::int AS completed,
                round(coalesce(avg(EXTRACT(EPOCH FROM (completed_at - created_at))), 0)::numeric, 1) AS avg_pipeline_seconds,
                count(*) FILTER (WHERE status = 'published' AND pr_merge_status = 'merged')::int AS merged_count,
                count(*) FILTER (WHERE status = 'published')::int AS published_count
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - :interval ::interval
              AND (:repo IS NULL OR repo = :repo)
        ),
        previous_tasks AS (
            SELECT
                count(*)::int AS completed,
                round(coalesce(avg(EXTRACT(EPOCH FROM (completed_at - created_at))), 0)::numeric, 1) AS avg_pipeline_seconds,
                count(*) FILTER (WHERE status = 'published' AND pr_merge_status = 'merged')::int AS merged_count,
                count(*) FILTER (WHERE status = 'published')::int AS published_count
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - (:days * 2)::int * interval '1 day'
              AND completed_at < now() - :interval ::interval
              AND (:repo IS NULL OR repo = :repo)
        ),
        current_spend AS (
            SELECT round(coalesce(sum(mca.cost), 0)::numeric, 6) AS total
            FROM model_call_audit mca
            LEFT JOIN taskpacket t ON t.id = mca.task_id
            WHERE mca.created_at >= now() - :interval ::interval
              AND (:repo IS NULL OR mca.task_id IS NULL OR t.repo = :repo)
        ),
        previous_spend AS (
            SELECT round(coalesce(sum(mca.cost), 0)::numeric, 6) AS total
            FROM model_call_audit mca
            LEFT JOIN taskpacket t ON t.id = mca.task_id
            WHERE mca.created_at >= now() - (:days * 2)::int * interval '1 day'
              AND mca.created_at < now() - :interval ::interval
              AND (:repo IS NULL OR mca.task_id IS NULL OR t.repo = :repo)
        )
        SELECT
            ct.completed AS cur_completed,
            pt.completed AS prev_completed,
            ct.avg_pipeline_seconds AS cur_avg_pipeline,
            pt.avg_pipeline_seconds AS prev_avg_pipeline,
            ct.merged_count AS cur_merged,
            ct.published_count AS cur_published,
            pt.merged_count AS prev_merged,
            pt.published_count AS prev_published,
            cs.total AS cur_spend,
            ps.total AS prev_spend
        FROM current_tasks ct, previous_tasks pt, current_spend cs, previous_spend ps
    """)

    result = await session.execute(sql, {"interval": interval, "days": days, "repo": repo})
    row = result.fetchone()

    if row is None:
        # Should not happen due to aggregate nature, but handle gracefully
        return {
            "period": period,
            "cards": {
                "tasks_completed": {"value": 0, "trend": "stable"},
                "avg_pipeline_seconds": {"value": 0.0, "trend": "stable"},
                "pr_merge_rate": {"value": 0.0, "trend": "stable"},
                "total_spend_usd": {"value": 0.0, "trend": "stable"},
            },
        }

    def _trend(current: float, previous: float) -> str:
        if current > previous:
            return "up"
        elif current < previous:
            return "down"
        return "stable"

    cur_merge_rate = (
        round(row.cur_merged / row.cur_published, 4)
        if row.cur_published > 0
        else 0.0
    )
    prev_merge_rate = (
        round(row.prev_merged / row.prev_published, 4)
        if row.prev_published > 0
        else 0.0
    )

    return {
        "period": period,
        "cards": {
            "tasks_completed": {
                "value": row.cur_completed,
                "trend": _trend(row.cur_completed, row.prev_completed),
            },
            "avg_pipeline_seconds": {
                "value": float(row.cur_avg_pipeline),
                "trend": _trend(float(row.cur_avg_pipeline), float(row.prev_avg_pipeline)),
            },
            "pr_merge_rate": {
                "value": cur_merge_rate,
                "trend": _trend(cur_merge_rate, prev_merge_rate),
            },
            "total_spend_usd": {
                "value": float(row.cur_spend),
                "trend": _trend(float(row.cur_spend), float(row.prev_spend)),
            },
        },
    }
