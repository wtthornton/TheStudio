"""Operational Targets — lead time, cycle time, and reopen target tracking.

Story 7.9: Lead Time, Cycle Time & Reopen Target Tracking
Architecture reference: thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md (Phase 4 targets)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.admin.metrics import get_metrics_service

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 28
DEFAULT_REOPEN_TARGET = 0.05  # <5%
DEFAULT_MIN_SAMPLES = 10


@dataclass
class LeadTimeMetrics:
    """Lead time from intake to PR opened (in hours)."""

    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    sample_count: int = 0
    window_days: int = DEFAULT_WINDOW_DAYS
    insufficient_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "p50_hours": round(self.p50, 2),
            "p95_hours": round(self.p95, 2),
            "p99_hours": round(self.p99, 2),
            "sample_count": self.sample_count,
            "window_days": self.window_days,
            "insufficient_data": self.insufficient_data,
        }


@dataclass
class CycleTimeMetrics:
    """Cycle time from PR opened to merge-ready (in hours)."""

    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    sample_count: int = 0
    window_days: int = DEFAULT_WINDOW_DAYS
    insufficient_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "p50_hours": round(self.p50, 2),
            "p95_hours": round(self.p95, 2),
            "p99_hours": round(self.p99, 2),
            "sample_count": self.sample_count,
            "window_days": self.window_days,
            "insufficient_data": self.insufficient_data,
        }


@dataclass
class ReopenTargetMetrics:
    """Reopen rate vs <5% target."""

    current_rate: float = 0.0
    target: float = DEFAULT_REOPEN_TARGET
    met: bool = True
    sample_count: int = 0
    window_days: int = DEFAULT_WINDOW_DAYS
    insufficient_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_rate": round(self.current_rate, 4),
            "target": self.target,
            "met": self.met,
            "sample_count": self.sample_count,
            "window_days": self.window_days,
            "insufficient_data": self.insufficient_data,
        }


def _compute_percentiles(values: list[float]) -> tuple[float, float, float]:
    """Compute p50, p95, p99 from sorted values."""
    if not values:
        return 0.0, 0.0, 0.0
    values = sorted(values)
    n = len(values)

    def _pct(p: float) -> float:
        idx = int(p * n)
        return values[min(idx, n - 1)]

    return _pct(0.50), _pct(0.95), _pct(0.99)


@dataclass
class TimingEvent:
    """A recorded timing event from a workflow completion."""

    repo_id: str
    intake_created_at: datetime
    pr_opened_at: datetime | None = None
    merge_ready_at: datetime | None = None

    @property
    def lead_time_hours(self) -> float | None:
        """Hours from intake to PR opened."""
        if self.pr_opened_at is None:
            return None
        delta = self.pr_opened_at - self.intake_created_at
        return delta.total_seconds() / 3600.0

    @property
    def cycle_time_hours(self) -> float | None:
        """Hours from PR opened to merge-ready."""
        if self.pr_opened_at is None or self.merge_ready_at is None:
            return None
        delta = self.merge_ready_at - self.pr_opened_at
        return delta.total_seconds() / 3600.0


# In-memory timing event store
_timing_events: list[TimingEvent] = []


def record_timing(event: TimingEvent) -> None:
    """Record a workflow timing event for lead/cycle time tracking."""
    _timing_events.append(event)
    logger.info(
        "Recorded timing event for repo=%s lead=%.2fh cycle=%sh",
        event.repo_id,
        event.lead_time_hours or 0.0,
        f"{event.cycle_time_hours:.2f}" if event.cycle_time_hours else "N/A",
    )


def clear_timing_events() -> None:
    """Clear all timing events (for testing)."""
    _timing_events.clear()


class OperationalTargetsService:
    """Computes lead time, cycle time, and reopen rate against targets."""

    def __init__(
        self,
        lead_times: list[float] | None = None,
        cycle_times: list[float] | None = None,
    ) -> None:
        # Legacy injected values for backwards compatibility.
        self._injected_lead_times = lead_times or []
        self._injected_cycle_times = cycle_times or []

    def _get_lead_times(self, repo_filter: str | None, window_days: int) -> list[float]:
        """Get lead times from timing events, falling back to injected values."""
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        values = []
        for evt in _timing_events:
            if repo_filter and evt.repo_id != repo_filter:
                continue
            if evt.intake_created_at < cutoff:
                continue
            lt = evt.lead_time_hours
            if lt is not None:
                values.append(lt)
        return values if values else self._injected_lead_times

    def _get_cycle_times(self, repo_filter: str | None, window_days: int) -> list[float]:
        """Get cycle times from timing events, falling back to injected values."""
        cutoff = datetime.now(UTC) - timedelta(days=window_days)
        values = []
        for evt in _timing_events:
            if repo_filter and evt.repo_id != repo_filter:
                continue
            if evt.intake_created_at < cutoff:
                continue
            ct = evt.cycle_time_hours
            if ct is not None:
                values.append(ct)
        return values if values else self._injected_cycle_times

    def get_lead_time(
        self,
        repo_filter: str | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> LeadTimeMetrics:
        """Compute lead time percentiles (intake to PR opened)."""
        values = self._get_lead_times(repo_filter, window_days)
        sample_count = len(values)

        if sample_count < min_samples:
            p50, p95, p99 = _compute_percentiles(values) if values else (0.0, 0.0, 0.0)
            return LeadTimeMetrics(
                p50=p50, p95=p95, p99=p99,
                sample_count=sample_count,
                window_days=window_days,
                insufficient_data=True,
            )

        p50, p95, p99 = _compute_percentiles(values)
        return LeadTimeMetrics(
            p50=p50, p95=p95, p99=p99,
            sample_count=sample_count,
            window_days=window_days,
        )

    def get_cycle_time(
        self,
        repo_filter: str | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> CycleTimeMetrics:
        """Compute cycle time percentiles (PR opened to merge-ready)."""
        values = self._get_cycle_times(repo_filter, window_days)
        sample_count = len(values)

        if sample_count < min_samples:
            p50, p95, p99 = _compute_percentiles(values) if values else (0.0, 0.0, 0.0)
            return CycleTimeMetrics(
                p50=p50, p95=p95, p99=p99,
                sample_count=sample_count,
                window_days=window_days,
                insufficient_data=True,
            )

        p50, p95, p99 = _compute_percentiles(values)
        return CycleTimeMetrics(
            p50=p50, p95=p95, p99=p99,
            sample_count=sample_count,
            window_days=window_days,
        )

    def get_reopen_target(
        self,
        repo_filter: str | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> ReopenTargetMetrics:
        """Check reopen rate against <5% target."""
        metrics_svc = get_metrics_service()
        reopen = metrics_svc.get_reopen(repo_filter=repo_filter)

        sample_count = reopen.total_reopened + reopen.total_merged
        current_rate = reopen.reopen_rate

        if sample_count < min_samples:
            return ReopenTargetMetrics(
                current_rate=current_rate,
                target=DEFAULT_REOPEN_TARGET,
                met=True,
                sample_count=sample_count,
                window_days=window_days,
                insufficient_data=True,
            )

        return ReopenTargetMetrics(
            current_rate=current_rate,
            target=DEFAULT_REOPEN_TARGET,
            met=current_rate <= DEFAULT_REOPEN_TARGET,
            sample_count=sample_count,
            window_days=window_days,
        )


# Global instance
_targets_service: OperationalTargetsService | None = None


def get_targets_service() -> OperationalTargetsService:
    global _targets_service
    if _targets_service is None:
        _targets_service = OperationalTargetsService()
    return _targets_service
