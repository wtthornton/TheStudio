"""Reputation Engine — expert trust computation and storage.

Architecture reference: thestudioarc/06-reputation-engine.md

The Reputation Engine:
1. Stores weights by expert + context key
2. Computes confidence from sample size
3. Manages trust tier transitions
4. Applies decay to prevent stale overconfidence
5. Exposes weights to Router queries
"""

import logging
from datetime import UTC, datetime
from math import exp, log
from typing import Protocol, runtime_checkable
from uuid import UUID

from src.reputation.models import (
    CONFIDENCE_BASE,
    CONFIDENCE_MAX,
    CONFIDENCE_SAMPLE_WEIGHT,
    DECAY_HALF_LIFE_DAYS,
    DRIFT_WINDOW_SAMPLES,
    TIER_THRESHOLDS,
    DriftSignal,
    ExpertWeight,
    TrustTier,
    WeightQuery,
    WeightQueryResult,
    WeightUpdate,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class ReputationEngineProtocol(Protocol):
    """Interface for reputation engine implementations."""

    def update_weight(self, update: WeightUpdate) -> ExpertWeight: ...
    def query_weights(self, query: WeightQuery) -> list[WeightQueryResult]: ...
    def get_weight(self, expert_id: UUID, context_key: str) -> ExpertWeight | None: ...
    def get_all_weights(self) -> list[ExpertWeight]: ...
    def get_expert_weights_for_router(
        self, expert_id: UUID, repo: str | None = None, min_confidence: float = 0.0,
    ) -> list[WeightQueryResult]: ...
    def get_best_experts_for_context(
        self, context_key: str, min_confidence: float = 0.0,
        trust_tier: TrustTier | None = None, limit: int = 10,
    ) -> list[WeightQueryResult]: ...
    def clear(self) -> None: ...


# In-memory stores (stub — replaced by DB in Phase 2)
_weights: dict[tuple[UUID, str], ExpertWeight] = {}  # (expert_id, context_key) -> weight
_weight_history: dict[tuple[UUID, str], list[float]] = {}  # For drift detection


def get_weight(expert_id: UUID, context_key: str) -> ExpertWeight | None:
    """Get the current weight for an expert in a context."""
    return _weights.get((expert_id, context_key))


def get_all_weights() -> list[ExpertWeight]:
    """Return all stored weights."""
    return list(_weights.values())


def clear() -> None:
    """Clear all stores (for testing)."""
    _weights.clear()
    _weight_history.clear()


def _compute_confidence(sample_count: int) -> float:
    """Compute confidence from sample size.

    Confidence grows logarithmically with samples, capped at CONFIDENCE_MAX.
    Low sample sizes keep confidence low even if outcomes look good.
    """
    if sample_count <= 0:
        return CONFIDENCE_BASE

    # Logarithmic growth: confidence = base + weight * log(1 + samples)
    raw_confidence = CONFIDENCE_BASE + CONFIDENCE_SAMPLE_WEIGHT * log(1 + sample_count)
    return min(raw_confidence, CONFIDENCE_MAX)


def _compute_decay_factor(last_indicator_at: datetime | None, now: datetime) -> float:
    """Compute decay factor based on time since last indicator.

    Decay follows exponential half-life: factor = 0.5 ^ (days / half_life)
    """
    if last_indicator_at is None:
        return 1.0

    # Ensure both datetimes are timezone-aware for comparison
    if last_indicator_at.tzinfo is None:
        # Assume naive datetime is UTC
        from datetime import UTC
        last_indicator_at = last_indicator_at.replace(tzinfo=UTC)

    days_elapsed = (now - last_indicator_at).total_seconds() / 86400
    if days_elapsed <= 0:
        return 1.0

    # Exponential decay: 2^(-days/half_life) = e^(-days * ln(2) / half_life)
    decay_constant = log(2) / DECAY_HALF_LIFE_DAYS
    return exp(-decay_constant * days_elapsed)


def _compute_weight(raw_weight_sum: float, sample_count: int, decay_factor: float) -> float:
    """Compute normalized weight from raw sum and sample count.

    Weight = (raw_sum / samples) * decay_factor, normalized to [0.0, 1.0]
    Starting point is 0.5 (neutral), positive indicators increase, negative decrease.
    """
    if sample_count <= 0:
        return 0.5  # Neutral weight for no data

    # Average weight per sample, with decay
    avg_weight = (raw_weight_sum / sample_count) * decay_factor

    # Normalize to [0.0, 1.0]: -1.0 -> 0.0, 0.0 -> 0.5, 1.0 -> 1.0
    normalized = (avg_weight + 1.0) / 2.0
    return max(0.0, min(1.0, normalized))


def _compute_drift(weight_history: list[float]) -> DriftSignal:
    """Detect drift from recent weight history.

    Uses a simple linear trend over the last DRIFT_WINDOW_SAMPLES weights.
    """
    if len(weight_history) < 3:
        return DriftSignal.STABLE

    recent = weight_history[-DRIFT_WINDOW_SAMPLES:]
    if len(recent) < 3:
        return DriftSignal.STABLE

    # Simple linear regression slope
    n = len(recent)
    x_mean = (n - 1) / 2.0
    y_mean = sum(recent) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return DriftSignal.STABLE

    slope = numerator / denominator

    # Thresholds for drift detection
    if slope > 0.02:
        return DriftSignal.IMPROVING
    if slope < -0.02:
        return DriftSignal.DECLINING
    return DriftSignal.STABLE


def _compute_trust_tier(
    current_tier: TrustTier,
    weight: float,
    confidence: float,
    sample_count: int,
) -> TrustTier:
    """Compute trust tier based on weight, confidence, and sample count.

    Transitions follow the rules in TIER_THRESHOLDS.
    """
    # Check for promotion
    if current_tier == TrustTier.SHADOW:
        thresholds = TIER_THRESHOLDS["shadow_to_probation"]
        if (
            sample_count >= thresholds["min_samples"]
            and weight >= thresholds["min_weight"]
            and confidence >= thresholds["min_confidence"]
        ):
            logger.info("Expert promoted from SHADOW to PROBATION")
            return TrustTier.PROBATION

    elif current_tier == TrustTier.PROBATION:
        # Check for promotion to trusted
        promo_thresholds = TIER_THRESHOLDS["probation_to_trusted"]
        if (
            sample_count >= promo_thresholds["min_samples"]
            and weight >= promo_thresholds["min_weight"]
            and confidence >= promo_thresholds["min_confidence"]
        ):
            logger.info("Expert promoted from PROBATION to TRUSTED")
            return TrustTier.TRUSTED

        # Check for demotion to shadow
        demo_thresholds = TIER_THRESHOLDS["probation_to_shadow"]
        if (
            sample_count >= demo_thresholds["min_samples"]
            and weight <= demo_thresholds["max_weight"]
        ):
            logger.info("Expert demoted from PROBATION to SHADOW")
            return TrustTier.SHADOW

    elif current_tier == TrustTier.TRUSTED:
        # Check for demotion to probation
        thresholds = TIER_THRESHOLDS["trusted_to_probation"]
        if (
            sample_count >= thresholds["min_samples"]
            and weight <= thresholds["max_weight"]
        ):
            logger.info("Expert demoted from TRUSTED to PROBATION")
            return TrustTier.PROBATION

    return current_tier


def update_weight(update: WeightUpdate) -> ExpertWeight:
    """Apply a weight update from an Outcome Ingestor indicator.

    Creates a new ExpertWeight if none exists for this (expert, context) pair.
    Updates weight, confidence, trust tier, and drift signal.
    """
    key = (update.expert_id, update.context_key)
    now = datetime.now(UTC)

    # Get or create weight record
    existing = _weights.get(key)

    if existing is None:
        # Create new weight record
        weight_record = ExpertWeight(
            expert_id=update.expert_id,
            expert_version=update.expert_version,
            context_key=update.context_key,
            weight=0.5,
            raw_weight_sum=update.normalized_weight,
            sample_count=1,
            confidence=_compute_confidence(1),
            trust_tier=TrustTier.SHADOW,
            drift_signal=DriftSignal.STABLE,
            created_at=now,
            updated_at=now,
            last_indicator_at=update.timestamp,
        )
        # Compute initial weight
        weight_record = weight_record.model_copy(
            update={"weight": _compute_weight(
                weight_record.raw_weight_sum,
                weight_record.sample_count,
                1.0,  # No decay for new records
            )}
        )
        _weights[key] = weight_record
        _weight_history[key] = [weight_record.weight]
        logger.info(
            "Created weight record for expert %s in context %s: weight=%.2f",
            update.expert_id, update.context_key, weight_record.weight,
        )
        return weight_record

    # Update existing record
    new_raw_sum = existing.raw_weight_sum + update.normalized_weight
    new_sample_count = existing.sample_count + 1

    # Apply decay
    decay_factor = _compute_decay_factor(existing.last_indicator_at, now)

    # Compute new weight
    new_weight = _compute_weight(new_raw_sum, new_sample_count, decay_factor)

    # Compute new confidence
    new_confidence = _compute_confidence(new_sample_count)

    # Update history for drift detection
    history = _weight_history.get(key, [])
    history.append(new_weight)
    _weight_history[key] = history

    # Compute drift
    new_drift = _compute_drift(history)

    # Compute trust tier
    new_tier = _compute_trust_tier(
        existing.trust_tier, new_weight, new_confidence, new_sample_count,
    )

    # Create updated record
    updated = existing.model_copy(update={
        "expert_version": update.expert_version,
        "weight": new_weight,
        "raw_weight_sum": new_raw_sum,
        "sample_count": new_sample_count,
        "confidence": new_confidence,
        "trust_tier": new_tier,
        "drift_signal": new_drift,
        "updated_at": now,
        "last_indicator_at": update.timestamp,
    })

    _weights[key] = updated

    logger.info(
        "Updated weight for expert %s in context %s: weight=%.2f, confidence=%.2f, tier=%s",
        update.expert_id, update.context_key, new_weight, new_confidence, new_tier.value,
    )

    return updated


def query_weights(query: WeightQuery) -> list[WeightQueryResult]:
    """Query weights for Router expert selection.

    Filters by expert_id, context_key, repo prefix, trust tier, and min confidence.
    Returns weights sorted by weight descending.
    """
    results: list[WeightQueryResult] = []

    for (expert_id, context_key), weight_record in _weights.items():
        # Apply filters
        if query.expert_id is not None and expert_id != query.expert_id:
            continue

        if query.context_key is not None and context_key != query.context_key:
            continue

        if query.repo is not None and not context_key.startswith(f"{query.repo}:"):
            continue

        if query.trust_tier is not None and weight_record.trust_tier != query.trust_tier:
            continue

        if weight_record.confidence < query.min_confidence:
            continue

        results.append(WeightQueryResult(
            expert_id=weight_record.expert_id,
            expert_version=weight_record.expert_version,
            context_key=weight_record.context_key,
            weight=weight_record.weight,
            confidence=weight_record.confidence,
            trust_tier=weight_record.trust_tier,
            drift_signal=weight_record.drift_signal,
        ))

    # Sort by weight descending
    results.sort(key=lambda r: r.weight, reverse=True)
    return results


def get_expert_weights_for_router(
    expert_id: UUID,
    repo: str | None = None,
    min_confidence: float = 0.0,
) -> list[WeightQueryResult]:
    """Convenience function for Router to get weights for an expert.

    Returns all context weights for the expert, optionally filtered by repo and min confidence.
    """
    query = WeightQuery(
        expert_id=expert_id,
        repo=repo,
        min_confidence=min_confidence,
    )
    return query_weights(query)


def get_best_experts_for_context(
    context_key: str,
    min_confidence: float = 0.0,
    trust_tier: TrustTier | None = None,
    limit: int = 10,
) -> list[WeightQueryResult]:
    """Get the best experts for a given context, sorted by weight.

    Used by Router for expert selection.
    """
    query = WeightQuery(
        context_key=context_key,
        min_confidence=min_confidence,
        trust_tier=trust_tier,
    )
    results = query_weights(query)
    return results[:limit]


class InMemoryReputationEngine:
    """Class wrapper around module-level reputation engine functions.

    Delegates to the module-level functions for backwards compatibility.
    Implements ReputationEngineProtocol for use with persistence adapters.
    """

    def update_weight(self, update: WeightUpdate) -> ExpertWeight:
        return update_weight(update)

    def query_weights(self, query: WeightQuery) -> list[WeightQueryResult]:
        return query_weights(query)

    def get_weight(self, expert_id: UUID, context_key: str) -> ExpertWeight | None:
        return get_weight(expert_id, context_key)

    def get_all_weights(self) -> list[ExpertWeight]:
        return get_all_weights()

    def get_expert_weights_for_router(
        self, expert_id: UUID, repo: str | None = None, min_confidence: float = 0.0,
    ) -> list[WeightQueryResult]:
        return get_expert_weights_for_router(expert_id, repo, min_confidence)

    def get_best_experts_for_context(
        self, context_key: str, min_confidence: float = 0.0,
        trust_tier: TrustTier | None = None, limit: int = 10,
    ) -> list[WeightQueryResult]:
        return get_best_experts_for_context(context_key, min_confidence, trust_tier, limit)

    def clear(self) -> None:
        clear()


_reputation_engine: InMemoryReputationEngine | None = None


def get_reputation_engine() -> ReputationEngineProtocol:
    global _reputation_engine
    if _reputation_engine is None:
        _reputation_engine = InMemoryReputationEngine()
    return _reputation_engine
