"""Success Gate Service — enforces single-pass success threshold.

Wraps MetricsService to check whether the single-pass success rate meets
the configured threshold over a rolling window.
"""

from dataclasses import dataclass, field
from typing import Any

from src.admin.metrics import get_metrics_service


DEFAULT_THRESHOLD = 0.60
DEFAULT_MIN_SAMPLES = 10
DEFAULT_WINDOW_DAYS = 28


@dataclass
class SuccessGateResult:
    """Result of a success gate check."""

    met: bool
    current_rate: float
    threshold: float
    sample_count: int
    window_days: int
    insufficient_data: bool = False
    category_breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "met": self.met,
            "current_rate": round(self.current_rate, 3),
            "threshold": self.threshold,
            "sample_count": self.sample_count,
            "window_days": self.window_days,
            "insufficient_data": self.insufficient_data,
            "category_breakdown": self.category_breakdown,
        }


class SuccessGateService:
    """Evaluates whether single-pass success meets the configured threshold."""

    def check(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        window_days: int = DEFAULT_WINDOW_DAYS,
        repo_filter: str | None = None,
    ) -> SuccessGateResult:
        """Check if single-pass success rate meets the threshold.

        Uses the 30-day rate from MetricsService (closest to the 28-day window).
        If sample count is below min_samples, returns met=True with insufficient_data=True.
        """
        metrics_svc = get_metrics_service()
        single_pass = metrics_svc.get_single_pass(repo_filter=repo_filter)
        loopbacks = metrics_svc.get_loopbacks(repo_filter=repo_filter)

        sample_count = single_pass.total_workflows_30d
        current_rate = single_pass.overall_rate_30d

        # Build category breakdown from loopback data
        category_breakdown = {
            cat.category: cat.count for cat in loopbacks.categories
        }

        if sample_count < min_samples:
            return SuccessGateResult(
                met=True,
                current_rate=current_rate,
                threshold=threshold,
                sample_count=sample_count,
                window_days=window_days,
                insufficient_data=True,
                category_breakdown=category_breakdown,
            )

        return SuccessGateResult(
            met=current_rate >= threshold,
            current_rate=current_rate,
            threshold=threshold,
            sample_count=sample_count,
            window_days=window_days,
            insufficient_data=False,
            category_breakdown=category_breakdown,
        )


# Global instance
_success_gate_service: SuccessGateService | None = None


def get_success_gate_service() -> SuccessGateService:
    """Get or create the global SuccessGateService instance."""
    global _success_gate_service
    if _success_gate_service is None:
        _success_gate_service = SuccessGateService()
    return _success_gate_service
