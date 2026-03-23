"""Reputation & Outcomes SQL query functions (Epic 39, Slice 2).

Provides async query helpers for:
- query_experts: Expert performance table (Story 39.12)
- query_expert_detail: Single-expert detail with weight history (Story 39.18)
- query_outcomes: Recent outcome signals feed (Story 39.13)
- query_drift: Drift detection alerts with composite score (Stories 39.14 + 39.15)
- query_reputation_summary: Reputation summary cards (Story 39.16)

All functions accept an AsyncSession and return plain dicts suitable
for direct JSON serialization by the reputation router.

Design rationale:
- Uses ``text()`` for complex aggregations (consistent with analytics_queries.py).
- Each function handles missing/empty data gracefully.
- Drift detection uses a fixed 14-day window (MVP constraint; configurable
  windows are a post-MVP enhancement per epic section 5).
- Minimum 20 tasks required in the drift window to avoid false positives
  (per epic risk R3).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Minimum tasks required in the drift window before generating alerts (epic R3)
_MIN_TASKS_FOR_DRIFT = 20

# Drift window is 14 days (hardcoded for MVP per epic business rule)
_DRIFT_WINDOW_DAYS = 14

# Thresholds that trigger a drift alert
_GATE_PASS_RATE_DRIFT_THRESHOLD = 0.10  # >=10% change in gate pass rate
_EXPERT_DECLINING_FRACTION = 0.30  # >=30% of experts showing declining trend
_COST_DRIFT_THRESHOLD = 0.20  # >=20% cost increase
_LOOPBACK_RATE_DRIFT_THRESHOLD = 0.10  # >=10% loopback rate increase


# ---------------------------------------------------------------------------
# 39.12 — Expert performance table
# ---------------------------------------------------------------------------


async def query_experts(session: AsyncSession) -> dict[str, Any]:
    """Expert performance table — weights, task counts, confidence, trend.

    Groups ``expert_reputation`` rows by expert_id.  Each expert may have
    multiple context_key rows (one per repo:risk_class:complexity_band
    combination); this query aggregates to one row per expert with averaged
    metrics.

    Pass rate is inferred from the normalized weight, which the reputation
    engine derives from cumulative gate-pass/fail outcome indicators.

    Returns ``{"experts": [...]}``.
    """
    sql = text("""
        SELECT
            expert_id::text                            AS expert_id,
            count(*)                                   AS context_count,
            round(avg(weight)::numeric, 4)             AS avg_weight,
            sum(sample_count)                          AS total_samples,
            round(avg(confidence)::numeric, 4)         AS avg_confidence,
            mode() WITHIN GROUP (ORDER BY trust_tier)  AS trust_tier,
            CASE
                WHEN bool_or(drift_direction = 'declining') THEN 'declining'
                WHEN bool_or(drift_direction = 'improving') THEN 'improving'
                ELSE 'stable'
            END                                        AS drift_signal,
            max(updated_at)                            AS last_updated_at
        FROM expert_reputation
        GROUP BY expert_id
        ORDER BY avg_weight DESC
    """)
    result = await session.execute(sql)
    rows = result.fetchall()

    experts = []
    for r in rows:
        experts.append({
            "expert_id": r.expert_id,
            "context_count": int(r.context_count),
            "avg_weight": float(r.avg_weight),
            "total_samples": int(r.total_samples),
            "avg_confidence": float(r.avg_confidence),
            "trust_tier": r.trust_tier,
            "drift_signal": r.drift_signal,
            "last_updated_at": (
                r.last_updated_at.isoformat() if r.last_updated_at else None
            ),
        })

    return {"experts": experts}


async def query_expert_detail(
    session: AsyncSession,
    expert_id: str,
) -> dict[str, Any] | None:
    """Expert detail — all context rows for a single expert with weight history.

    Returns ``{"expert_id": "...", "contexts": [...]}``, or ``None`` if the
    expert_id is not found in the database.

    The ``weight_history`` list supports a trend sparkline on the frontend
    (Story 39.18).
    """
    sql = text("""
        SELECT
            expert_id::text  AS expert_id,
            context_key,
            weight,
            sample_count,
            confidence,
            trust_tier,
            drift_direction  AS drift_signal,
            weight_history,
            updated_at       AS last_updated_at
        FROM expert_reputation
        WHERE expert_id::text = :expert_id
        ORDER BY weight DESC
    """)
    result = await session.execute(sql, {"expert_id": expert_id})
    rows = result.fetchall()

    if not rows:
        return None

    contexts = []
    for r in rows:
        contexts.append({
            "context_key": r.context_key,
            "weight": float(r.weight),
            "sample_count": int(r.sample_count),
            "confidence": float(r.confidence),
            "trust_tier": r.trust_tier,
            "drift_signal": r.drift_signal,
            "weight_history": list(r.weight_history) if r.weight_history else [],
            "last_updated_at": (
                r.last_updated_at.isoformat() if r.last_updated_at else None
            ),
        })

    return {"expert_id": expert_id, "contexts": contexts}


# ---------------------------------------------------------------------------
# 39.13 — Outcome signals feed
# ---------------------------------------------------------------------------


async def query_outcomes(
    session: AsyncSession,
    limit: int = 50,
) -> dict[str, Any]:
    """Recent outcome signals feed — chronological with task context.

    Joins ``outcome_signals`` with ``taskpacket`` for repo and issue_id
    context.  Classifies each signal into a human-readable outcome_type:
    - success: qa_passed, verification_passed
    - failure: qa_defect, verification_failed, verification_exhausted
    - loopback: qa_rework

    Extracts learnings from failure signal payloads where available.

    Returns ``{"outcomes": [...], "total": N}``.
    """
    sql = text("""
        SELECT
            os.id::text     AS id,
            os.task_id::text AS task_id,
            os.signal_type,
            os.signal_at,
            os.payload,
            t.issue_id,
            t.repo,
            t.status        AS task_status,
            CASE
                WHEN os.signal_type IN ('qa_passed', 'verification_passed')
                    THEN 'success'
                WHEN os.signal_type IN (
                    'qa_defect', 'verification_failed', 'verification_exhausted'
                )
                    THEN 'failure'
                WHEN os.signal_type = 'qa_rework'
                    THEN 'loopback'
                ELSE 'unknown'
            END             AS outcome_type
        FROM outcome_signals os
        LEFT JOIN taskpacket t ON t.id = os.task_id
        ORDER BY os.signal_at DESC
        LIMIT :limit
    """)

    count_sql = text("SELECT count(*) AS total FROM outcome_signals")

    result = await session.execute(sql, {"limit": limit})
    rows = result.fetchall()

    count_result = await session.execute(count_sql)
    count_row = count_result.fetchone()
    total = int(count_row.total) if count_row else 0

    outcomes = []
    for r in rows:
        payload = dict(r.payload) if r.payload else {}
        # Extract learnings from failure payloads (defect_category, learnings)
        learnings: str | None = (
            payload.get("learnings")
            or payload.get("defect_category")
            or None
        )

        outcomes.append({
            "id": r.id,
            "task_id": r.task_id,
            "signal_type": r.signal_type,
            "outcome_type": r.outcome_type,
            "signal_at": r.signal_at.isoformat() if r.signal_at else None,
            "issue_id": r.issue_id,
            "repo": r.repo,
            "task_status": r.task_status,
            "learnings": learnings,
        })

    return {"outcomes": outcomes, "total": total}


# ---------------------------------------------------------------------------
# 39.14 + 39.15 — Drift detection + composite drift score
# ---------------------------------------------------------------------------


def _drift_score_label(composite: float) -> str:
    """Classify a 0.0-1.0 composite drift score as low / moderate / high."""
    if composite >= 0.6:
        return "high"
    elif composite >= 0.3:
        return "moderate"
    return "low"


async def query_drift(session: AsyncSession) -> dict[str, Any]:
    """Drift detection alerts with composite drift score (Stories 39.14 + 39.15).

    Compares metrics over the current 14-day window vs the previous 14-day
    period.  Tracks four metrics:
    1. Gate pass rate (from gate_evidence)
    2. Expert weight decline (from expert_reputation)
    3. Model cost trend (from model_call_audit)
    4. Loopback rate (from taskpacket.loopback_count)

    Each metric that crosses its alert threshold contributes 0.25 to the
    composite score.  Score thresholds: low < 0.3, 0.3 <= moderate < 0.6,
    high >= 0.6.

    Requires at least _MIN_TASKS_FOR_DRIFT completed tasks in the current
    window to generate alerts (avoids false positives with sparse data per
    epic risk R3).

    Returns:
        {
            "window_days": 14,
            "drift_score": "low" | "moderate" | "high",
            "composite_score": 0.0-1.0,
            "alerts": [...],
            "insufficient_data": bool,
            "task_count": int,
        }
    """
    window = _DRIFT_WINDOW_DAYS

    # Gate: minimum task count in window before alerting
    count_sql = text("""
        SELECT count(*) AS cnt
        FROM taskpacket
        WHERE status IN ('published', 'rejected', 'failed', 'aborted')
          AND completed_at IS NOT NULL
          AND completed_at >= now() - :window ::int * interval '1 day'
    """)
    count_result = await session.execute(count_sql, {"window": window})
    count_row = count_result.fetchone()
    task_count = int(count_row.cnt) if count_row else 0

    if task_count < _MIN_TASKS_FOR_DRIFT:
        return {
            "window_days": window,
            "drift_score": "low",
            "composite_score": 0.0,
            "alerts": [],
            "insufficient_data": True,
            "task_count": task_count,
            "min_tasks_required": _MIN_TASKS_FOR_DRIFT,
        }

    alerts: list[dict[str, Any]] = []

    # --- Metric 1: Gate pass rate ---
    gate_sql = text("""
        WITH current_period AS (
            SELECT
                count(*) FILTER (WHERE result = 'pass')::float
                    / NULLIF(count(*), 0) AS pass_rate
            FROM gate_evidence
            WHERE created_at >= now() - :window ::int * interval '1 day'
        ),
        previous_period AS (
            SELECT
                count(*) FILTER (WHERE result = 'pass')::float
                    / NULLIF(count(*), 0) AS pass_rate
            FROM gate_evidence
            WHERE created_at >= now() - (:window * 2)::int * interval '1 day'
              AND created_at <  now() - :window ::int * interval '1 day'
        )
        SELECT
            coalesce(cp.pass_rate, 0) AS cur_pass_rate,
            coalesce(pp.pass_rate, 0) AS prev_pass_rate
        FROM current_period cp, previous_period pp
    """)
    gate_result = await session.execute(gate_sql, {"window": window})
    gate_row = gate_result.fetchone()

    if gate_row and gate_row.prev_pass_rate > 0:
        delta = gate_row.cur_pass_rate - gate_row.prev_pass_rate
        pct_change = abs(delta) / gate_row.prev_pass_rate

        if pct_change >= _GATE_PASS_RATE_DRIFT_THRESHOLD:
            direction = "up" if delta > 0 else "down"
            alerts.append({
                "metric": "gate_pass_rate",
                "direction": direction,
                "magnitude": round(pct_change, 4),
                "current_value": round(float(gate_row.cur_pass_rate), 4),
                "previous_value": round(float(gate_row.prev_pass_rate), 4),
                "possible_cause": (
                    "Improving code quality or easier task mix"
                    if direction == "up"
                    else "Regression in code quality, harder tasks, or expert degradation"
                ),
            })

    # --- Metric 2: Expert weight decline fraction ---
    expert_sql = text("""
        SELECT
            round(avg(weight)::numeric, 4) AS avg_weight,
            sum(CASE WHEN drift_direction = 'declining' THEN 1 ELSE 0 END)
                AS declining_count,
            count(*) AS total_experts
        FROM expert_reputation
    """)
    expert_result = await session.execute(expert_sql)
    expert_row = expert_result.fetchone()

    if expert_row and int(expert_row.total_experts) > 0:
        declining_fraction = (
            int(expert_row.declining_count) / int(expert_row.total_experts)
        )
        if declining_fraction >= _EXPERT_DECLINING_FRACTION:
            alerts.append({
                "metric": "expert_weights",
                "direction": "down",
                "magnitude": round(declining_fraction, 4),
                "current_value": float(expert_row.avg_weight),
                "previous_value": None,
                "possible_cause": (
                    f"{int(expert_row.declining_count)} of "
                    f"{int(expert_row.total_experts)} experts show declining "
                    "reputation. Review routing decisions and gate outcomes "
                    "for affected experts."
                ),
            })

    # --- Metric 3: Model cost trend ---
    cost_sql = text("""
        WITH current_period AS (
            SELECT coalesce(sum(cost), 0) AS total
            FROM model_call_audit
            WHERE created_at >= now() - :window ::int * interval '1 day'
        ),
        previous_period AS (
            SELECT coalesce(sum(cost), 0) AS total
            FROM model_call_audit
            WHERE created_at >= now() - (:window * 2)::int * interval '1 day'
              AND created_at <  now() - :window ::int * interval '1 day'
        )
        SELECT cp.total AS cur_cost, pp.total AS prev_cost
        FROM current_period cp, previous_period pp
    """)
    cost_result = await session.execute(cost_sql, {"window": window})
    cost_row = cost_result.fetchone()

    if cost_row and float(cost_row.prev_cost) > 0:
        cost_delta = float(cost_row.cur_cost) - float(cost_row.prev_cost)
        cost_pct = cost_delta / float(cost_row.prev_cost)

        if cost_pct >= _COST_DRIFT_THRESHOLD:
            alerts.append({
                "metric": "model_cost",
                "direction": "up",
                "magnitude": round(cost_pct, 4),
                "current_value": round(float(cost_row.cur_cost), 6),
                "previous_value": round(float(cost_row.prev_cost), 6),
                "possible_cause": (
                    "Significant cost increase detected. Check for increased task "
                    "volume, more complex tasks, or inefficient routing to expensive "
                    "models."
                ),
            })

    # --- Metric 4: Average loopback rate ---
    loopback_sql = text("""
        WITH current_period AS (
            SELECT round(coalesce(avg(loopback_count), 0)::numeric, 4)
                AS avg_loopbacks
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - :window ::int * interval '1 day'
        ),
        previous_period AS (
            SELECT round(coalesce(avg(loopback_count), 0)::numeric, 4)
                AS avg_loopbacks
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - (:window * 2)::int * interval '1 day'
              AND completed_at <  now() - :window ::int * interval '1 day'
        )
        SELECT
            cp.avg_loopbacks AS cur_loopbacks,
            pp.avg_loopbacks AS prev_loopbacks
        FROM current_period cp, previous_period pp
    """)
    loopback_result = await session.execute(loopback_sql, {"window": window})
    loopback_row = loopback_result.fetchone()

    if loopback_row and float(loopback_row.prev_loopbacks) > 0:
        lb_delta = float(loopback_row.cur_loopbacks) - float(loopback_row.prev_loopbacks)
        lb_pct = lb_delta / float(loopback_row.prev_loopbacks)

        if lb_pct >= _LOOPBACK_RATE_DRIFT_THRESHOLD:
            alerts.append({
                "metric": "loopback_rate",
                "direction": "up",
                "magnitude": round(lb_pct, 4),
                "current_value": float(loopback_row.cur_loopbacks),
                "previous_value": float(loopback_row.prev_loopbacks),
                "possible_cause": (
                    "More tasks requiring rework. Check for intent quality issues, "
                    "complex task types, or expert performance degradation."
                ),
            })

    # Composite score: fraction of the 4 tracked metrics that are drifting
    num_metrics = 4
    composite_score = round(len(alerts) / num_metrics, 4)
    drift_score = _drift_score_label(composite_score)

    return {
        "window_days": window,
        "drift_score": drift_score,
        "composite_score": composite_score,
        "alerts": alerts,
        "insufficient_data": False,
        "task_count": task_count,
    }


# ---------------------------------------------------------------------------
# 39.16 — Reputation summary cards
# ---------------------------------------------------------------------------


async def query_reputation_summary(session: AsyncSession) -> dict[str, Any]:
    """Reputation summary cards with trend indicators (Story 39.16).

    Four summary cards for the 14-day rolling window:
    - success_rate: QA pass fraction (qa_passed / (qa_passed + qa_defect))
    - avg_loopbacks: average loopback_count per completed task
    - pr_merge_rate: fraction of published PRs that were merged
    - drift_score: composite drift level (low / moderate / high, no trend)

    Each numeric card includes a ``trend`` field (up / down / stable)
    comparing the current 14-day window vs the previous 14-day period.

    Returns ``{"cards": {...}}``.
    """
    window = _DRIFT_WINDOW_DAYS

    sql = text("""
        WITH current_outcomes AS (
            SELECT
                count(*) FILTER (WHERE signal_type = 'qa_passed')::float
                    AS qa_passed,
                count(*) FILTER (
                    WHERE signal_type IN ('qa_passed', 'qa_defect')
                )::float AS qa_total
            FROM outcome_signals
            WHERE signal_at >= now() - :window ::int * interval '1 day'
        ),
        previous_outcomes AS (
            SELECT
                count(*) FILTER (WHERE signal_type = 'qa_passed')::float
                    AS qa_passed,
                count(*) FILTER (
                    WHERE signal_type IN ('qa_passed', 'qa_defect')
                )::float AS qa_total
            FROM outcome_signals
            WHERE signal_at >= now() - (:window * 2)::int * interval '1 day'
              AND signal_at <  now() - :window ::int * interval '1 day'
        ),
        current_tasks AS (
            SELECT
                round(coalesce(avg(loopback_count), 0)::numeric, 4)
                    AS avg_loopbacks,
                count(*) FILTER (
                    WHERE status = 'published' AND pr_merge_status = 'merged'
                )::int AS merged,
                count(*) FILTER (WHERE status = 'published')::int AS published
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - :window ::int * interval '1 day'
        ),
        previous_tasks AS (
            SELECT
                round(coalesce(avg(loopback_count), 0)::numeric, 4)
                    AS avg_loopbacks,
                count(*) FILTER (
                    WHERE status = 'published' AND pr_merge_status = 'merged'
                )::int AS merged,
                count(*) FILTER (WHERE status = 'published')::int AS published
            FROM taskpacket
            WHERE status IN ('published', 'rejected', 'failed', 'aborted')
              AND completed_at IS NOT NULL
              AND completed_at >= now() - (:window * 2)::int * interval '1 day'
              AND completed_at <  now() - :window ::int * interval '1 day'
        )
        SELECT
            co.qa_passed         AS cur_qa_passed,
            co.qa_total          AS cur_qa_total,
            po.qa_passed         AS prev_qa_passed,
            po.qa_total          AS prev_qa_total,
            ct.avg_loopbacks     AS cur_avg_loopbacks,
            pt.avg_loopbacks     AS prev_avg_loopbacks,
            ct.merged            AS cur_merged,
            ct.published         AS cur_published,
            pt.merged            AS prev_merged,
            pt.published         AS prev_published
        FROM current_outcomes co, previous_outcomes po,
             current_tasks ct, previous_tasks pt
    """)

    result = await session.execute(sql, {"window": window})
    row = result.fetchone()

    def _trend(current: float, previous: float) -> str:
        if current > previous:
            return "up"
        elif current < previous:
            return "down"
        return "stable"

    if row is None:
        return _empty_reputation_summary()

    cur_success_rate = (
        round(float(row.cur_qa_passed) / float(row.cur_qa_total), 4)
        if row.cur_qa_total and float(row.cur_qa_total) > 0
        else 0.0
    )
    prev_success_rate = (
        round(float(row.prev_qa_passed) / float(row.prev_qa_total), 4)
        if row.prev_qa_total and float(row.prev_qa_total) > 0
        else 0.0
    )
    cur_merge_rate = (
        round(int(row.cur_merged) / int(row.cur_published), 4)
        if int(row.cur_published) > 0
        else 0.0
    )
    prev_merge_rate = (
        round(int(row.prev_merged) / int(row.prev_published), 4)
        if int(row.prev_published) > 0
        else 0.0
    )

    # Get drift score (reuse query_drift for consistency)
    drift_data = await query_drift(session)
    drift_label = drift_data["drift_score"]

    return {
        "cards": {
            "success_rate": {
                "value": cur_success_rate,
                "trend": _trend(cur_success_rate, prev_success_rate),
            },
            "avg_loopbacks": {
                "value": float(row.cur_avg_loopbacks),
                "trend": _trend(
                    float(row.cur_avg_loopbacks), float(row.prev_avg_loopbacks)
                ),
            },
            "pr_merge_rate": {
                "value": cur_merge_rate,
                "trend": _trend(cur_merge_rate, prev_merge_rate),
            },
            "drift_score": {
                "value": drift_label,
                "score": drift_label,
            },
        },
    }


def _empty_reputation_summary() -> dict[str, Any]:
    """Return zeroed-out reputation summary when no data is available."""
    return {
        "cards": {
            "success_rate": {"value": 0.0, "trend": "stable"},
            "avg_loopbacks": {"value": 0.0, "trend": "stable"},
            "pr_merge_rate": {"value": 0.0, "trend": "stable"},
            "drift_score": {"value": "low", "score": "low"},
        },
    }
