"""Time-based decay — reduces weights for stale/inactive experts.

Architecture reference: thestudioarc/06-reputation-engine.md lines 90-98

Decay rules:
- Weight reduced by decay_rate per decay_period of inactivity
- Decay floor: weight cannot drop below decay_floor from decay alone
- Decay triggers confidence reduction proportional to time since last outcome
"""

import logging
from datetime import UTC, datetime
from math import exp, log
from typing import Any
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Default decay configuration
DEFAULT_DECAY_RATE = 0.02  # Weight reduction per decay_period
DEFAULT_DECAY_PERIOD_DAYS = 7  # Days between decay applications
DEFAULT_DECAY_FLOOR = 0.3  # Minimum weight from decay alone
DEFAULT_DECAY_HALF_LIFE_DAYS = 90  # Confidence decay half-life


class DecayResult(BaseModel):
    """Result of applying decay to an expert."""

    expert_id: UUID
    context_key: str
    old_weight: float
    new_weight: float
    old_confidence: float
    new_confidence: float
    days_inactive: float
    decay_applied: bool


# Store for decay results (for signal emission)
_decay_results: list[DecayResult] = []


def clear() -> None:
    """Clear stores (for testing)."""
    _decay_results.clear()


def get_decay_results() -> list[DecayResult]:
    """Return all decay results."""
    return list(_decay_results)


def compute_decay_factor(
    last_outcome_at: datetime | None,
    now: datetime | None = None,
    half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS,
) -> float:
    """Compute decay factor based on time since last outcome.

    Decay follows exponential half-life: factor = 0.5 ^ (days / half_life)
    """
    if now is None:
        now = datetime.now(UTC)

    if last_outcome_at is None:
        return 1.0

    # Ensure timezone-aware
    if last_outcome_at.tzinfo is None:
        last_outcome_at = last_outcome_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    days_elapsed = (now - last_outcome_at).total_seconds() / 86400
    if days_elapsed <= 0:
        return 1.0

    # Exponential decay: 2^(-days/half_life) = e^(-days * ln(2) / half_life)
    decay_constant = log(2) / half_life_days
    return exp(-decay_constant * days_elapsed)


def compute_days_inactive(
    last_outcome_at: datetime | None,
    now: datetime | None = None,
) -> float:
    """Compute days since last outcome."""
    if now is None:
        now = datetime.now(UTC)

    if last_outcome_at is None:
        return 0.0

    # Ensure timezone-aware
    if last_outcome_at.tzinfo is None:
        last_outcome_at = last_outcome_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    return (now - last_outcome_at).total_seconds() / 86400


def apply_decay(
    expert_id: UUID,
    context_key: str,
    current_weight: float,
    current_confidence: float,
    last_outcome_at: datetime | None,
    now: datetime | None = None,
    decay_rate: float = DEFAULT_DECAY_RATE,
    decay_period_days: float = DEFAULT_DECAY_PERIOD_DAYS,
    decay_floor: float = DEFAULT_DECAY_FLOOR,
    half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS,
) -> DecayResult:
    """Apply time-based decay to an expert's weight and confidence.

    Per DoD:
    - Weight reduced by decay_rate per decay_period of inactivity
    - Decay floor prevents weight from dropping below minimum from decay alone
    - Confidence reduces proportionally to time since last outcome

    Args:
        expert_id: Expert UUID.
        context_key: Context key for the weight.
        current_weight: Current weight value.
        current_confidence: Current confidence value.
        last_outcome_at: Timestamp of last indicator.
        now: Current time (defaults to now).
        decay_rate: Weight reduction per period (default 0.02).
        decay_period_days: Days between decay applications (default 7).
        decay_floor: Minimum weight from decay alone (default 0.3).
        half_life_days: Confidence half-life (default 90).

    Returns:
        DecayResult with old and new values.
    """
    if now is None:
        now = datetime.now(UTC)

    days_inactive = compute_days_inactive(last_outcome_at, now)

    # Calculate number of decay periods elapsed
    periods_elapsed = days_inactive / decay_period_days

    # Apply weight decay
    if periods_elapsed >= 1:
        # Linear decay: weight -= rate * periods
        weight_reduction = decay_rate * periods_elapsed
        new_weight = max(decay_floor, current_weight - weight_reduction)
    else:
        new_weight = current_weight

    # Apply confidence decay using exponential half-life
    decay_factor = compute_decay_factor(last_outcome_at, now, half_life_days)
    new_confidence = current_confidence * decay_factor

    decay_applied = (new_weight != current_weight) or (new_confidence != current_confidence)

    result = DecayResult(
        expert_id=expert_id,
        context_key=context_key,
        old_weight=current_weight,
        new_weight=new_weight,
        old_confidence=current_confidence,
        new_confidence=new_confidence,
        days_inactive=days_inactive,
        decay_applied=decay_applied,
    )

    if decay_applied:
        _decay_results.append(result)
        logger.info(
            "Applied decay to expert %s in %s: weight %.2f -> %.2f, "
            "confidence %.2f -> %.2f (%.1f days inactive)",
            expert_id, context_key, current_weight, new_weight,
            current_confidence, new_confidence, days_inactive,
        )

    return result


class DecayScheduler:
    """Scheduler for periodic decay application.

    Per DoD: Decay runs on configurable schedule (default: daily at 02:00 UTC).
    Processes all experts with last_outcome_at older than decay_period.
    """

    def __init__(
        self,
        decay_rate: float = DEFAULT_DECAY_RATE,
        decay_period_days: float = DEFAULT_DECAY_PERIOD_DAYS,
        decay_floor: float = DEFAULT_DECAY_FLOOR,
        half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS,
    ) -> None:
        """Initialize the decay scheduler.

        Args:
            decay_rate: Weight reduction per period.
            decay_period_days: Days between decay applications.
            decay_floor: Minimum weight from decay alone.
            half_life_days: Confidence half-life.
        """
        self.decay_rate = decay_rate
        self.decay_period_days = decay_period_days
        self.decay_floor = decay_floor
        self.half_life_days = half_life_days
        self._last_run: datetime | None = None

    def run_decay(
        self,
        get_all_weights_fn: Any,
        update_weight_fn: Any,
        now: datetime | None = None,
    ) -> list[DecayResult]:
        """Run decay on all eligible experts.

        Args:
            get_all_weights_fn: Callable() -> list of weight records.
            update_weight_fn: Callable(expert_id, context_key, new_weight, new_confidence).
            now: Current time (defaults to now).

        Returns:
            List of DecayResult for all affected experts.
        """
        if now is None:
            now = datetime.now(UTC)

        results: list[DecayResult] = []
        weights = get_all_weights_fn()

        for weight_record in weights:
            # Check if decay period has elapsed
            days_inactive = compute_days_inactive(
                getattr(weight_record, "last_indicator_at", None) or
                getattr(weight_record, "last_outcome_at", None),
                now,
            )

            if days_inactive < self.decay_period_days:
                continue

            # Apply decay
            result = apply_decay(
                expert_id=weight_record.expert_id,
                context_key=weight_record.context_key,
                current_weight=weight_record.weight,
                current_confidence=weight_record.confidence,
                last_outcome_at=getattr(weight_record, "last_indicator_at", None),
                now=now,
                decay_rate=self.decay_rate,
                decay_period_days=self.decay_period_days,
                decay_floor=self.decay_floor,
                half_life_days=self.half_life_days,
            )

            if result.decay_applied:
                results.append(result)
                # Update the weight record
                if update_weight_fn is not None:
                    update_weight_fn(
                        weight_record.expert_id,
                        weight_record.context_key,
                        result.new_weight,
                        result.new_confidence,
                    )

        self._last_run = now
        logger.info("Decay scheduler run complete: %d experts affected", len(results))
        return results

    def should_run(self, now: datetime | None = None) -> bool:
        """Check if decay should run based on schedule.

        Default: once per day.
        """
        if now is None:
            now = datetime.now(UTC)

        if self._last_run is None:
            return True

        hours_since_last = (now - self._last_run).total_seconds() / 3600
        return hours_since_last >= 24  # Daily
