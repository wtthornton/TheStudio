"""Metrics Service — single-pass success, loopback breakdown, reopen rate.

Reads from Outcome Ingestor signals and Reopen Event Processor to compute
aggregate quality metrics.

Architecture reference: thestudioarc/23-admin-control-ui.md (Metrics and Trends)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.outcome.ingestor import get_signals
from src.outcome.models import OutcomeType, SignalEvent
from src.outcome.reopen import (
    ReopenClassification,
    get_reopen_outcomes,
)


# Maps signal events to loopback categories
LOOPBACK_CATEGORIES = {
    "lint": ["verify_lint", "lint"],
    "test": ["verify_test", "test"],
    "security": ["verify_security", "security"],
}


@dataclass
class SinglePassMetrics:
    """Single-pass success rate metrics."""

    overall_rate_7d: float = 0.0
    overall_rate_30d: float = 0.0
    total_workflows_7d: int = 0
    total_workflows_30d: int = 0
    successful_7d: int = 0
    successful_30d: int = 0
    by_repo: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_rate_7d": round(self.overall_rate_7d, 3),
            "overall_rate_30d": round(self.overall_rate_30d, 3),
            "total_workflows_7d": self.total_workflows_7d,
            "total_workflows_30d": self.total_workflows_30d,
            "successful_7d": self.successful_7d,
            "successful_30d": self.successful_30d,
            "by_repo": self.by_repo,
        }


@dataclass
class LoopbackEntry:
    """A single loopback category entry."""

    category: str
    count: int = 0
    percentage: float = 0.0


@dataclass
class LoopbackMetrics:
    """Verification loopback breakdown metrics."""

    total_loopbacks: int = 0
    categories: list[LoopbackEntry] = field(default_factory=list)
    by_repo: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_loopbacks": self.total_loopbacks,
            "categories": [
                {
                    "category": c.category,
                    "count": c.count,
                    "percentage": round(c.percentage, 1),
                }
                for c in self.categories
            ],
            "by_repo": self.by_repo,
        }


@dataclass
class ReopenMetrics:
    """Reopen rate and attribution breakdown."""

    total_merged: int = 0
    total_reopened: int = 0
    reopen_rate: float = 0.0
    attribution: dict[str, int] = field(default_factory=dict)
    by_repo: dict[str, float] = field(default_factory=dict)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "total_merged": self.total_merged,
            "total_reopened": self.total_reopened,
            "reopen_rate": round(self.reopen_rate, 3),
            "attribution": self.attribution,
            "by_repo": self.by_repo,
        }
        if self.note:
            result["note"] = self.note
        return result


class MetricsService:
    """Computes quality metrics from outcome and reopen data."""

    def get_single_pass(self, repo_filter: str | None = None) -> SinglePassMetrics:
        """Compute single-pass success rate.

        Single-pass success = workflows where verification + QA passed on first attempt.
        A workflow is identified by its correlation_id.
        """
        signals = get_signals()
        now = datetime.now(UTC)
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)

        # Group signals by correlation_id (workflow)
        workflows: dict[str, list] = {}
        for signal in signals:
            repo_id = signal.payload.get("repo_id", "unknown")
            if repo_filter and repo_id != repo_filter:
                continue
            key = str(signal.correlation_id)
            if key not in workflows:
                workflows[key] = []
            workflows[key].append(signal)

        metrics = SinglePassMetrics()
        repo_data: dict[str, dict[str, int]] = {}

        for _corr_id, wf_signals in workflows.items():
            # Determine if this workflow had single-pass success
            has_failure = any(
                s.event in (
                    SignalEvent.VERIFICATION_FAILED,
                    SignalEvent.VERIFICATION_EXHAUSTED,
                    SignalEvent.QA_DEFECT,
                    SignalEvent.QA_REWORK,
                )
                for s in wf_signals
            )
            has_success = any(
                s.event in (SignalEvent.VERIFICATION_PASSED, SignalEvent.QA_PASSED)
                for s in wf_signals
            )
            is_single_pass = has_success and not has_failure

            # Get timestamp and repo from first signal
            ts = wf_signals[0].timestamp
            repo = wf_signals[0].payload.get("repo_id", "unknown")

            if repo not in repo_data:
                repo_data[repo] = {"total_7d": 0, "success_7d": 0, "total_30d": 0, "success_30d": 0}

            if ts >= cutoff_30d:
                metrics.total_workflows_30d += 1
                repo_data[repo]["total_30d"] += 1
                if is_single_pass:
                    metrics.successful_30d += 1
                    repo_data[repo]["success_30d"] += 1

            if ts >= cutoff_7d:
                metrics.total_workflows_7d += 1
                repo_data[repo]["total_7d"] += 1
                if is_single_pass:
                    metrics.successful_7d += 1
                    repo_data[repo]["success_7d"] += 1

        if metrics.total_workflows_7d:
            metrics.overall_rate_7d = metrics.successful_7d / metrics.total_workflows_7d
        if metrics.total_workflows_30d:
            metrics.overall_rate_30d = metrics.successful_30d / metrics.total_workflows_30d

        for repo, data in repo_data.items():
            rate_7d = data["success_7d"] / data["total_7d"] if data["total_7d"] else 0.0
            rate_30d = data["success_30d"] / data["total_30d"] if data["total_30d"] else 0.0
            metrics.by_repo[repo] = {
                "rate_7d": round(rate_7d, 3),
                "rate_30d": round(rate_30d, 3),
            }

        return metrics

    def get_loopbacks(self, repo_filter: str | None = None) -> LoopbackMetrics:
        """Compute verification loopback breakdown.

        Loopbacks = VERIFICATION_FAILED signals, categorized by step type.
        """
        signals = get_signals()
        metrics = LoopbackMetrics()
        category_counts: dict[str, int] = {"lint": 0, "test": 0, "security": 0, "other": 0}

        for signal in signals:
            if signal.event != SignalEvent.VERIFICATION_FAILED:
                continue

            repo_id = signal.payload.get("repo_id", "unknown")
            if repo_filter and repo_id != repo_filter:
                continue

            metrics.total_loopbacks += 1
            metrics.by_repo[repo_id] = metrics.by_repo.get(repo_id, 0) + 1

            step = signal.payload.get("step", "").lower()
            categorized = False
            for cat, keywords in LOOPBACK_CATEGORIES.items():
                if any(kw in step for kw in keywords):
                    category_counts[cat] += 1
                    categorized = True
                    break
            if not categorized:
                category_counts["other"] += 1

        for cat, count in sorted(category_counts.items()):
            pct = (count / metrics.total_loopbacks * 100) if metrics.total_loopbacks else 0.0
            metrics.categories.append(LoopbackEntry(category=cat, count=count, percentage=pct))

        return metrics

    def get_reopen(self, repo_filter: str | None = None) -> ReopenMetrics:
        """Compute reopen rate and attribution breakdown.

        Reads from reopen outcomes. Returns zeros with note if no data.
        """
        outcomes = get_reopen_outcomes()
        if repo_filter:
            outcomes = [o for o in outcomes if o.repo_id == repo_filter]

        metrics = ReopenMetrics()

        if not outcomes:
            metrics.note = "No reopen data available yet. Reopen tracking is active but no events have been recorded."
            return metrics

        metrics.total_reopened = len(outcomes)

        # Attribution breakdown
        attribution: dict[str, int] = {
            "intent_gap": 0,
            "implementation_bug": 0,
            "regression": 0,
            "governance_failure": 0,
        }
        repo_counts: dict[str, int] = {}

        for outcome in outcomes:
            attribution[outcome.classification.value] += 1
            repo_counts[outcome.repo_id] = repo_counts.get(outcome.repo_id, 0) + 1

        metrics.attribution = attribution
        metrics.by_repo = {r: float(c) for r, c in repo_counts.items()}

        return metrics


# Global instance
_metrics_service: MetricsService | None = None


def get_metrics_service() -> MetricsService:
    """Get or create the global MetricsService instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
