"""Model Spend aggregation — spend breakdowns by repo, step, provider, and time window.

Epic 10, AC4: Model Spend Dashboard.
Aggregates ModelCallAudit records into spend summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.admin.model_gateway import ModelCallAudit, get_model_audit_store
from src.agent.framework import PIPELINE_BUDGET_DEFAULTS, get_budget_for_tier


@dataclass
class SpendSummary:
    """Aggregated spend for a grouping key."""

    key: str
    total_cost: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    call_count: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "total_cost": round(self.total_cost, 6),
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "call_count": self.call_count,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "error_count": self.error_count,
        }


@dataclass
class SpendReport:
    """Full spend report with breakdowns.

    Story 32.11: ``cache_hit_rate`` tracks the proportion of input tokens
    served from Anthropic's prompt cache vs total input tokens.
    """

    total_cost: float = 0.0
    total_calls: int = 0
    by_provider: list[SpendSummary] = field(default_factory=list)
    by_step: list[SpendSummary] = field(default_factory=list)
    by_model: list[SpendSummary] = field(default_factory=list)
    by_repo: list[SpendSummary] = field(default_factory=list)
    by_day: list[SpendSummary] = field(default_factory=list)
    window_hours: int = 24
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    cache_hit_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 6),
            "total_calls": self.total_calls,
            "by_provider": [s.to_dict() for s in self.by_provider],
            "by_step": [s.to_dict() for s in self.by_step],
            "by_model": [s.to_dict() for s in self.by_model],
            "by_repo": [s.to_dict() for s in self.by_repo],
            "by_day": [s.to_dict() for s in self.by_day],
            "window_hours": self.window_hours,
            "total_cache_creation_tokens": self.total_cache_creation_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
        }


@dataclass
class TierBudgetUtilization:
    """Budget utilization for a single trust tier."""

    tier: str
    budget_limit: float
    current_spend: float
    active_tasks: int
    utilization_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "budget_limit": round(self.budget_limit, 2),
            "current_spend": round(self.current_spend, 4),
            "active_tasks": self.active_tasks,
            "utilization_pct": round(self.utilization_pct, 1),
        }


def get_budget_utilization(window_hours: int = 24) -> list[TierBudgetUtilization]:
    """Compute budget utilization per trust tier from recent audit records.

    Story 32.14: Groups audit records by repo tier to show how much of each
    tier's budget cap has been consumed in the time window.
    """
    store = get_model_audit_store()
    all_records = store.query(limit=10_000)
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    records = [r for r in all_records if r.created_at >= cutoff]

    # Aggregate spend and distinct tasks per tier
    tier_spend: dict[str, float] = {}
    tier_tasks: dict[str, set[str]] = {}
    for r in records:
        tier = r.role if r.role in PIPELINE_BUDGET_DEFAULTS else "observe"
        tier_spend[tier] = tier_spend.get(tier, 0.0) + r.cost
        tier_tasks.setdefault(tier, set()).add(str(r.task_id) if r.task_id else "unknown")

    result = []
    for tier in ["observe", "suggest", "execute"]:
        limit = get_budget_for_tier(tier)
        spend = tier_spend.get(tier, 0.0)
        tasks = tier_tasks.get(tier, set())
        pct = (spend / limit * 100) if limit > 0 else 0.0
        result.append(TierBudgetUtilization(
            tier=tier,
            budget_limit=limit,
            current_spend=spend,
            active_tasks=len(tasks),
            utilization_pct=pct,
        ))
    return result


def _aggregate(records: list[ModelCallAudit], key_fn: Any) -> list[SpendSummary]:
    """Group audit records by key function and aggregate."""
    groups: dict[str, list[ModelCallAudit]] = {}
    for r in records:
        k = key_fn(r)
        groups.setdefault(k, []).append(r)

    summaries = []
    for key, group in sorted(groups.items()):
        total_cost = sum(r.cost for r in group)
        total_in = sum(r.tokens_in for r in group)
        total_out = sum(r.tokens_out for r in group)
        latencies = [r.latency_ms for r in group if r.latency_ms > 0]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        errors = sum(1 for r in group if r.error_class)

        summaries.append(SpendSummary(
            key=key,
            total_cost=total_cost,
            total_tokens_in=total_in,
            total_tokens_out=total_out,
            call_count=len(group),
            avg_latency_ms=avg_lat,
            error_count=errors,
        ))

    summaries.sort(key=lambda s: s.total_cost, reverse=True)
    return summaries


def get_spend_report(window_hours: int = 24) -> SpendReport:
    """Generate a spend report from audit records within the time window."""
    store = get_model_audit_store()
    all_records = store.query(limit=10_000)

    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    records = [r for r in all_records if r.created_at >= cutoff]

    if not records:
        return SpendReport(window_hours=window_hours)

    total_cost = sum(r.cost for r in records)
    total_cache_creation = sum(r.cache_creation_tokens for r in records)
    total_cache_read = sum(r.cache_read_tokens for r in records)

    # Cache hit rate: proportion of input tokens served from cache
    cache_eligible = total_cache_creation + total_cache_read
    cache_hit_rate = (
        total_cache_read / cache_eligible if cache_eligible > 0 else 0.0
    )

    return SpendReport(
        total_cost=total_cost,
        total_calls=len(records),
        by_provider=_aggregate(records, lambda r: r.provider),
        by_step=_aggregate(records, lambda r: r.step or "unknown"),
        by_model=_aggregate(records, lambda r: r.model or "unknown"),
        by_repo=_aggregate(records, lambda r: r.repo or "unknown"),
        by_day=_aggregate(records, lambda r: r.created_at.strftime("%Y-%m-%d")),
        window_hours=window_hours,
        total_cache_creation_tokens=total_cache_creation,
        total_cache_read_tokens=total_cache_read,
        cache_hit_rate=cache_hit_rate,
    )
