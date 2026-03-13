"""Readiness gate data models.

Defines the scoring dimensions, gate decisions, and activity I/O types
for the issue readiness gate (Epic 16).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime


class ReadinessDimension(enum.StrEnum):
    """The six dimensions used to evaluate issue readiness."""

    GOAL_CLARITY = "goal_clarity"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    SCOPE_BOUNDARIES = "scope_boundaries"
    RISK_COVERAGE = "risk_coverage"
    REPRODUCTION_CONTEXT = "reproduction_context"
    DEPENDENCY_AWARENESS = "dependency_awareness"


class GateDecision(enum.StrEnum):
    """Possible outcomes of the readiness gate evaluation."""

    PASS = "pass"  # noqa: S105
    HOLD = "hold"
    ESCALATE = "escalate"


class ComplexityTier(enum.StrEnum):
    """Complexity tier derived from the complexity index score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def classify_complexity(complexity_score: float) -> ComplexityTier:
    """Map a complexity index score to a tier.

    Ranges: low (<3), medium (3-6), high (>6).
    """
    if complexity_score < 3.0:
        return ComplexityTier.LOW
    if complexity_score <= 6.0:
        return ComplexityTier.MEDIUM
    return ComplexityTier.HIGH


@dataclass(frozen=True)
class DimensionScore:
    """Score for a single readiness dimension."""

    dimension: ReadinessDimension
    score: float  # 0.0 to 1.0
    reason: str
    required: bool = False


@dataclass(frozen=True)
class ReadinessScore:
    """Complete readiness evaluation result."""

    overall_score: float
    dimension_scores: tuple[DimensionScore, ...]
    missing_dimensions: tuple[ReadinessDimension, ...]
    recommended_questions: tuple[str, ...]
    gate_decision: GateDecision
    complexity_tier: ComplexityTier
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ReadinessOutput:
    """Activity output for the readiness gate step.

    Used as the Temporal activity return type.
    """

    proceed: bool = True
    score: float = 1.0
    clarification_questions: list[str] = field(default_factory=list)
    hold_reason: str | None = None
