"""Reputation Engine models — weights, confidence, and trust tiers.

Architecture reference: thestudioarc/06-reputation-engine.md
"""

import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TrustTier(enum.StrEnum):
    """Trust tiers for experts.

    Transition rules (per 06-reputation-engine.md):
    - shadow: new expert, low confidence, limited selection weight
    - probation: passed initial threshold, moderate confidence
    - trusted: established track record, high confidence
    """

    SHADOW = "shadow"
    PROBATION = "probation"
    TRUSTED = "trusted"


class DriftSignal(enum.StrEnum):
    """Drift signals for weight trends."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# Trust tier transition thresholds
TIER_THRESHOLDS = {
    "shadow_to_probation": {"min_samples": 5, "min_weight": 0.3, "min_confidence": 0.3},
    "probation_to_trusted": {"min_samples": 20, "min_weight": 0.5, "min_confidence": 0.6},
    "trusted_to_probation": {"max_weight": 0.2, "min_samples": 10},
    "probation_to_shadow": {"max_weight": 0.0, "min_samples": 5},
}

# Confidence computation parameters
CONFIDENCE_BASE = 0.1  # Minimum confidence with 1 sample
CONFIDENCE_SAMPLE_WEIGHT = 0.05  # Each sample adds this to confidence
CONFIDENCE_MAX = 0.95  # Cap confidence even with many samples

# Decay parameters
DECAY_HALF_LIFE_DAYS = 90  # Weight impact halves after this period
DRIFT_WINDOW_SAMPLES = 10  # Rolling window for drift detection


class ExpertWeight(BaseModel):
    """Weight record for an expert in a specific context.

    Stored per (expert_id, context_key) pair.
    """

    expert_id: UUID
    expert_version: int
    context_key: str  # Format: "{repo}:{risk_class}:{complexity_band}"

    # Weight data
    weight: float = 0.5  # Normalized weight [0.0, 1.0]
    raw_weight_sum: float = 0.0  # Sum of normalized indicator weights
    sample_count: int = 0  # Number of indicators contributing
    confidence: float = CONFIDENCE_BASE  # Confidence in the weight

    # Trust tier
    trust_tier: TrustTier = TrustTier.SHADOW
    drift_signal: DriftSignal = DriftSignal.STABLE

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_indicator_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "expert_id": str(self.expert_id),
            "expert_version": self.expert_version,
            "context_key": self.context_key,
            "weight": self.weight,
            "raw_weight_sum": self.raw_weight_sum,
            "sample_count": self.sample_count,
            "confidence": self.confidence,
            "trust_tier": self.trust_tier.value,
            "drift_signal": self.drift_signal.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_indicator_at": (
                self.last_indicator_at.isoformat() if self.last_indicator_at else None
            ),
        }


class WeightQuery(BaseModel):
    """Query parameters for fetching expert weights."""

    expert_id: UUID | None = None
    context_key: str | None = None
    repo: str | None = None  # Filter by repo prefix in context_key
    trust_tier: TrustTier | None = None
    min_confidence: float = 0.0


class WeightQueryResult(BaseModel):
    """Result from a weight query."""

    expert_id: UUID
    expert_version: int
    context_key: str
    weight: float
    confidence: float
    trust_tier: TrustTier
    drift_signal: DriftSignal


class WeightUpdate(BaseModel):
    """Incoming weight update from Outcome Ingestor indicators."""

    expert_id: UUID
    expert_version: int
    context_key: str
    normalized_weight: float  # From indicator, complexity-adjusted
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
