"""Expert Performance API — wraps Reputation Engine for admin visibility.

Provides expert list, detail, and drift data.
Architecture reference: thestudioarc/23-admin-control-ui.md (Expert Performance Console)
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.reputation.engine import get_all_weights, query_weights
from src.reputation.models import DriftSignal, TrustTier, WeightQuery


@dataclass
class ExpertSummary:
    """Summary of an expert's performance."""

    expert_id: str
    expert_version: int
    trust_tier: str
    confidence: float
    weight: float
    drift_signal: str
    context_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "expert_version": self.expert_version,
            "trust_tier": self.trust_tier,
            "confidence": round(self.confidence, 3),
            "weight": round(self.weight, 3),
            "drift_signal": self.drift_signal,
            "context_count": self.context_count,
        }


@dataclass
class ExpertRepoBreakdown:
    """Per-repo breakdown for an expert."""

    repo: str
    consults: int
    avg_weight: float
    drift_signal: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "consults": self.consults,
            "avg_weight": round(self.avg_weight, 3),
            "drift_signal": self.drift_signal,
        }


@dataclass
class ExpertDetail:
    """Detailed expert information with per-repo breakdown."""

    expert_id: str
    expert_version: int
    trust_tier: str
    confidence: float
    weight: float
    drift_signal: str
    sample_count: int
    repos: list[ExpertRepoBreakdown] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "expert_version": self.expert_version,
            "trust_tier": self.trust_tier,
            "confidence": round(self.confidence, 3),
            "weight": round(self.weight, 3),
            "drift_signal": self.drift_signal,
            "sample_count": self.sample_count,
            "repos": [r.to_dict() for r in self.repos],
        }


@dataclass
class ExpertDrift:
    """Drift data for an expert."""

    expert_id: str
    trend: str  # improving, stable, declining
    change_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "trend": self.trend,
            "change_pct": round(self.change_pct, 1),
        }


class ExpertPerformanceService:
    """Provides expert performance data from the Reputation Engine."""

    def list_experts(
        self,
        repo_filter: str | None = None,
        tier_filter: str | None = None,
    ) -> list[ExpertSummary]:
        """List all experts with summary metrics."""
        weights = get_all_weights()

        # Group by expert_id
        expert_data: dict[str, list] = {}
        for w in weights:
            eid = str(w.expert_id)
            if repo_filter and not w.context_key.startswith(f"{repo_filter}:"):
                continue
            if eid not in expert_data:
                expert_data[eid] = []
            expert_data[eid].append(w)

        summaries = []
        for eid, expert_weights in expert_data.items():
            # Aggregate across contexts
            avg_weight = sum(w.weight for w in expert_weights) / len(expert_weights)
            max_confidence = max(w.confidence for w in expert_weights)
            # Use the highest tier
            tier_order = {TrustTier.SHADOW: 0, TrustTier.PROBATION: 1, TrustTier.TRUSTED: 2}
            best_tier = max(expert_weights, key=lambda w: tier_order.get(w.trust_tier, 0))
            # Determine overall drift from majority
            drift_counts: dict[str, int] = {}
            for w in expert_weights:
                drift_counts[w.drift_signal.value] = drift_counts.get(w.drift_signal.value, 0) + 1
            overall_drift = max(drift_counts, key=lambda k: drift_counts[k])

            if tier_filter and best_tier.trust_tier.value != tier_filter:
                continue

            summaries.append(ExpertSummary(
                expert_id=eid,
                expert_version=expert_weights[0].expert_version,
                trust_tier=best_tier.trust_tier.value,
                confidence=max_confidence,
                weight=avg_weight,
                drift_signal=overall_drift,
                context_count=len(expert_weights),
            ))

        return summaries

    def get_expert(self, expert_id: str) -> ExpertDetail | None:
        """Get detailed expert info with per-repo breakdown."""
        uid = UUID(expert_id)
        results = query_weights(WeightQuery(expert_id=uid))

        if not results:
            return None

        # Group by repo (first part of context_key)
        repo_data: dict[str, list] = {}
        for r in results:
            repo = r.context_key.split(":")[0] if ":" in r.context_key else r.context_key
            if repo not in repo_data:
                repo_data[repo] = []
            repo_data[repo].append(r)

        repos = []
        for repo, rweights in repo_data.items():
            avg_w = sum(r.weight for r in rweights) / len(rweights)
            drift_counts: dict[str, int] = {}
            for r in rweights:
                drift_counts[r.drift_signal.value] = drift_counts.get(r.drift_signal.value, 0) + 1
            drift = max(drift_counts, key=lambda k: drift_counts[k])
            repos.append(ExpertRepoBreakdown(
                repo=repo,
                consults=len(rweights),
                avg_weight=avg_w,
                drift_signal=drift,
            ))

        all_weights = get_all_weights()
        expert_weights = [w for w in all_weights if w.expert_id == uid]
        total_samples = sum(w.sample_count for w in expert_weights)
        avg_weight = sum(r.weight for r in results) / len(results)
        max_conf = max(r.confidence for r in results)
        tier_order = {TrustTier.SHADOW: 0, TrustTier.PROBATION: 1, TrustTier.TRUSTED: 2}
        best = max(expert_weights, key=lambda w: tier_order.get(w.trust_tier, 0))
        drift_counts_all: dict[str, int] = {}
        for r in results:
            drift_counts_all[r.drift_signal.value] = (
                drift_counts_all.get(r.drift_signal.value, 0) + 1
            )
        overall_drift = max(drift_counts_all, key=lambda k: drift_counts_all[k])

        return ExpertDetail(
            expert_id=expert_id,
            expert_version=best.expert_version,
            trust_tier=best.trust_tier.value,
            confidence=max_conf,
            weight=avg_weight,
            drift_signal=overall_drift,
            sample_count=total_samples,
            repos=repos,
        )

    def get_expert_drift(self, expert_id: str) -> ExpertDrift | None:
        """Get drift data for an expert."""
        uid = UUID(expert_id)
        results = query_weights(WeightQuery(expert_id=uid))

        if not results:
            return None

        # Determine overall drift
        drift_counts: dict[str, int] = {}
        for r in results:
            drift_counts[r.drift_signal.value] = drift_counts.get(r.drift_signal.value, 0) + 1
        trend = max(drift_counts, key=lambda k: drift_counts[k])

        # Compute a rough change percentage from weight spread
        weights = [r.weight for r in results]
        if len(weights) >= 2:
            change_pct = (max(weights) - min(weights)) / max(max(weights), 0.01) * 100
        else:
            change_pct = 0.0

        return ExpertDrift(
            expert_id=expert_id,
            trend=trend,
            change_pct=change_pct,
        )


# Global instance
_expert_service: ExpertPerformanceService | None = None


def get_expert_service() -> ExpertPerformanceService:
    """Get or create the global ExpertPerformanceService instance."""
    global _expert_service
    if _expert_service is None:
        _expert_service = ExpertPerformanceService()
    return _expert_service
