"""Readiness gate configuration — thresholds and weights per complexity tier.

Initial calibration uses equal weights for low complexity and shifts weight
toward acceptance criteria and scope boundaries for medium/high complexity.
Adjusted by Story 16.6 (outcome signal feedback).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.readiness.models import ComplexityTier, ReadinessDimension


@dataclass(frozen=True)
class ReadinessThresholds:
    """Threshold configuration for readiness scoring.

    Per-dimension pass thresholds define the minimum score for each dimension.
    Dimension weights control the weighted average for the overall score.
    The overall pass threshold is the minimum overall score for a PASS decision.
    """

    per_dimension_thresholds: dict[ReadinessDimension, float]
    dimension_weights: dict[ReadinessDimension, float]
    overall_pass_threshold: float
    required_dimensions: frozenset[ReadinessDimension] = field(
        default_factory=frozenset
    )


def _equal_weights() -> dict[ReadinessDimension, float]:
    """Equal weight (1/6) for each dimension."""
    w = 1.0 / 6.0
    return dict.fromkeys(ReadinessDimension, w)


def _medium_weights() -> dict[ReadinessDimension, float]:
    """Shift weight toward acceptance criteria and scope for medium complexity."""
    return {
        ReadinessDimension.GOAL_CLARITY: 0.15,
        ReadinessDimension.ACCEPTANCE_CRITERIA: 0.25,
        ReadinessDimension.SCOPE_BOUNDARIES: 0.20,
        ReadinessDimension.RISK_COVERAGE: 0.15,
        ReadinessDimension.REPRODUCTION_CONTEXT: 0.10,
        ReadinessDimension.DEPENDENCY_AWARENESS: 0.15,
    }


def _high_weights() -> dict[ReadinessDimension, float]:
    """Shift weight further toward acceptance criteria, scope, and deps for high complexity."""
    return {
        ReadinessDimension.GOAL_CLARITY: 0.10,
        ReadinessDimension.ACCEPTANCE_CRITERIA: 0.25,
        ReadinessDimension.SCOPE_BOUNDARIES: 0.20,
        ReadinessDimension.RISK_COVERAGE: 0.15,
        ReadinessDimension.REPRODUCTION_CONTEXT: 0.10,
        ReadinessDimension.DEPENDENCY_AWARENESS: 0.20,
    }


_DEFAULT_DIMENSION_THRESHOLDS: dict[ReadinessDimension, float] = {
    ReadinessDimension.GOAL_CLARITY: 0.3,
    ReadinessDimension.ACCEPTANCE_CRITERIA: 0.3,
    ReadinessDimension.SCOPE_BOUNDARIES: 0.2,
    ReadinessDimension.RISK_COVERAGE: 0.2,
    ReadinessDimension.REPRODUCTION_CONTEXT: 0.2,
    ReadinessDimension.DEPENDENCY_AWARENESS: 0.2,
}

# Required dimensions that force HOLD if they score 0, regardless of overall score.
_LOW_REQUIRED = frozenset({ReadinessDimension.GOAL_CLARITY})
_MEDIUM_REQUIRED = frozenset(
    {ReadinessDimension.GOAL_CLARITY, ReadinessDimension.ACCEPTANCE_CRITERIA}
)
_HIGH_REQUIRED = frozenset(
    {
        ReadinessDimension.GOAL_CLARITY,
        ReadinessDimension.ACCEPTANCE_CRITERIA,
        ReadinessDimension.SCOPE_BOUNDARIES,
    }
)


DEFAULT_THRESHOLDS: dict[ComplexityTier, ReadinessThresholds] = {
    ComplexityTier.LOW: ReadinessThresholds(
        per_dimension_thresholds=_DEFAULT_DIMENSION_THRESHOLDS,
        dimension_weights=_equal_weights(),
        overall_pass_threshold=0.4,
        required_dimensions=_LOW_REQUIRED,
    ),
    ComplexityTier.MEDIUM: ReadinessThresholds(
        per_dimension_thresholds=_DEFAULT_DIMENSION_THRESHOLDS,
        dimension_weights=_medium_weights(),
        overall_pass_threshold=0.5,
        required_dimensions=_MEDIUM_REQUIRED,
    ),
    ComplexityTier.HIGH: ReadinessThresholds(
        per_dimension_thresholds=_DEFAULT_DIMENSION_THRESHOLDS,
        dimension_weights=_high_weights(),
        overall_pass_threshold=0.6,
        required_dimensions=_HIGH_REQUIRED,
    ),
}


def get_thresholds(
    complexity_tier: ComplexityTier,
    repo_override: ReadinessThresholds | None = None,
) -> ReadinessThresholds:
    """Return thresholds for the given complexity tier.

    If a repo-level override is provided, it replaces the default entirely
    (full object replacement, not per-field merge). This keeps the override
    logic simple and predictable.
    """
    if repo_override is not None:
        return repo_override
    return DEFAULT_THRESHOLDS[complexity_tier]
