"""Trust tier management — tier computation and transition logic.

Architecture reference: thestudioarc/06-reputation-engine.md lines 26-43

Trust tiers:
- shadow: new expert, low confidence, limited selection weight
- probation: passed initial threshold, moderate confidence
- trusted: established track record, high confidence

Tier transitions are computed on indicator write, not on read.
"""

import enum
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TrustTier(enum.StrEnum):
    """Trust tiers for experts."""

    SHADOW = "shadow"
    PROBATION = "probation"
    TRUSTED = "trusted"


class DriftDirection(enum.StrEnum):
    """Drift direction for weight trends."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# Tier transition thresholds (configurable)
DEFAULT_TIER_THRESHOLDS = {
    "shadow_to_probation": {
        "min_samples": 5,
        "min_weight": 0.3,
        "min_confidence": 0.3,
    },
    "probation_to_trusted": {
        "min_samples": 10,
        "min_weight": 0.6,
        "min_confidence": 0.5,
    },
    "trusted_to_probation": {
        "max_weight": 0.4,
        "min_samples": 5,
    },
    "probation_to_shadow": {
        "max_weight": 0.2,
        "min_samples": 5,
    },
}

# Consecutive drift signals required for demotion/promotion
DRIFT_SUSTAINED_COUNT = 3


class TierTransition(BaseModel):
    """Record of a trust tier transition."""

    expert_id: UUID
    context_key: str
    old_tier: TrustTier
    new_tier: TrustTier
    reason: str
    timestamp: datetime


# In-memory store for tier transitions (for signal emission)
_tier_transitions: list[TierTransition] = []
_drift_consecutive_counts: dict[tuple[UUID, str], dict[str, int]] = {}


def clear() -> None:
    """Clear stores (for testing)."""
    _tier_transitions.clear()
    _drift_consecutive_counts.clear()


def get_tier_transitions() -> list[TierTransition]:
    """Return all tier transitions."""
    return list(_tier_transitions)


def compute_tier(
    weight: float,
    confidence: float,
    sample_count: int,
    drift_direction: DriftDirection,
    thresholds: dict[str, Any] | None = None,
) -> TrustTier:
    """Compute the appropriate tier based on metrics.

    Per DoD:
    - shadow: confidence < 0.3 OR sample_count < 5
    - probation: confidence >= 0.3 AND sample_count >= 5 AND (weight < 0.6 OR drift == declining)
    - trusted: confidence >= 0.5 AND sample_count >= 10 AND weight >= 0.6 AND drift != declining
    """
    t = thresholds or DEFAULT_TIER_THRESHOLDS

    # Shadow conditions
    if confidence < t["shadow_to_probation"]["min_confidence"]:
        return TrustTier.SHADOW
    if sample_count < t["shadow_to_probation"]["min_samples"]:
        return TrustTier.SHADOW

    # Trusted conditions
    trusted_thresholds = t["probation_to_trusted"]
    if (
        confidence >= trusted_thresholds["min_confidence"]
        and sample_count >= trusted_thresholds["min_samples"]
        and weight >= trusted_thresholds["min_weight"]
        and drift_direction != DriftDirection.DECLINING
    ):
        return TrustTier.TRUSTED

    # Probation conditions (between shadow and trusted)
    shadow_thresholds = t["shadow_to_probation"]
    if (
        confidence >= shadow_thresholds["min_confidence"]
        and sample_count >= shadow_thresholds["min_samples"]
        and weight >= shadow_thresholds["min_weight"]
    ):
        return TrustTier.PROBATION

    return TrustTier.SHADOW


def compute_tier_transition(
    expert_id: UUID,
    context_key: str,
    current_tier: TrustTier,
    weight: float,
    confidence: float,
    sample_count: int,
    drift_direction: DriftDirection,
    thresholds: dict[str, Any] | None = None,
) -> tuple[TrustTier, TierTransition | None]:
    """Compute tier and emit transition if changed.

    Per DoD:
    - Tier transitions are computed on write, not read
    - If tier changed, update tier_changed_at and emit trust_tier_changed signal

    Returns:
        (new_tier, transition_record if tier changed else None)
    """
    t = thresholds or DEFAULT_TIER_THRESHOLDS
    key = (expert_id, context_key)
    now = datetime.now(UTC)

    # Track consecutive drift signals for drift-triggered transitions
    if key not in _drift_consecutive_counts:
        _drift_consecutive_counts[key] = {"declining": 0, "improving": 0}

    drift_counts = _drift_consecutive_counts[key]

    # Update consecutive counts
    if drift_direction == DriftDirection.DECLINING:
        drift_counts["declining"] += 1
        drift_counts["improving"] = 0
    elif drift_direction == DriftDirection.IMPROVING:
        drift_counts["improving"] += 1
        drift_counts["declining"] = 0
    else:
        # Stable resets both
        drift_counts["declining"] = 0
        drift_counts["improving"] = 0

    # Compute new tier based on metrics
    new_tier = current_tier
    reason = ""

    # Check for drift-triggered demotion (sustained decline)
    if drift_counts["declining"] >= DRIFT_SUSTAINED_COUNT:
        if current_tier == TrustTier.TRUSTED:
            new_tier = TrustTier.PROBATION
            reason = f"Sustained decline ({drift_counts['declining']} consecutive)"
        elif current_tier == TrustTier.PROBATION:
            new_tier = TrustTier.SHADOW
            reason = f"Sustained decline ({drift_counts['declining']} consecutive)"

    # Check for drift-triggered promotion (sustained improvement)
    elif drift_counts["improving"] >= DRIFT_SUSTAINED_COUNT:
        # Promotion still requires meeting thresholds
        promoted_tier = compute_tier(
            weight, confidence, sample_count, drift_direction, t
        )
        if _tier_rank(promoted_tier) > _tier_rank(current_tier):
            new_tier = promoted_tier
            reason = f"Sustained improvement ({drift_counts['improving']} consecutive)"

    # Standard threshold-based transitions (if no drift transition occurred)
    if new_tier == current_tier:
        computed_tier = compute_tier(
            weight, confidence, sample_count, drift_direction, t
        )
        if computed_tier != current_tier:
            new_tier = computed_tier
            reason = _build_transition_reason(
                current_tier, new_tier, weight, confidence, sample_count,
            )

    # Create transition record if tier changed
    if new_tier != current_tier:
        transition = TierTransition(
            expert_id=expert_id,
            context_key=context_key,
            old_tier=current_tier,
            new_tier=new_tier,
            reason=reason,
            timestamp=now,
        )
        _tier_transitions.append(transition)
        logger.info(
            "Trust tier changed for expert %s in %s: %s -> %s (%s)",
            expert_id, context_key, current_tier.value, new_tier.value, reason,
        )
        return (new_tier, transition)

    return (current_tier, None)


def _tier_rank(tier: TrustTier) -> int:
    """Return numeric rank for tier comparison."""
    return {"shadow": 0, "probation": 1, "trusted": 2}[tier.value]


def _build_transition_reason(
    old_tier: TrustTier,
    new_tier: TrustTier,
    weight: float,
    confidence: float,
    sample_count: int,
) -> str:
    """Build a human-readable transition reason."""
    if _tier_rank(new_tier) > _tier_rank(old_tier):
        return f"Promoted: weight={weight:.2f}, confidence={confidence:.2f}, samples={sample_count}"
    else:
        return f"Demoted: weight={weight:.2f}, confidence={confidence:.2f}, samples={sample_count}"
