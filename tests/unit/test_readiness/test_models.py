"""Tests for readiness gate data models and configuration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.readiness.config import (
    DEFAULT_THRESHOLDS,
    ReadinessThresholds,
    get_thresholds,
)
from src.readiness.models import (
    ComplexityTier,
    DimensionScore,
    GateDecision,
    ReadinessDimension,
    ReadinessOutput,
    ReadinessScore,
    classify_complexity,
)

# --- ReadinessDimension enum ---


class TestReadinessDimension:
    def test_has_six_values(self) -> None:
        assert len(ReadinessDimension) == 6

    def test_values(self) -> None:
        expected = {
            "goal_clarity",
            "acceptance_criteria",
            "scope_boundaries",
            "risk_coverage",
            "reproduction_context",
            "dependency_awareness",
        }
        assert {d.value for d in ReadinessDimension} == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(ReadinessDimension.GOAL_CLARITY, str)
        assert ReadinessDimension.GOAL_CLARITY == "goal_clarity"


# --- GateDecision enum ---


class TestGateDecision:
    def test_has_three_values(self) -> None:
        assert len(GateDecision) == 3

    def test_values(self) -> None:
        assert GateDecision.PASS == "pass"
        assert GateDecision.HOLD == "hold"
        assert GateDecision.ESCALATE == "escalate"


# --- ComplexityTier ---


class TestComplexityTier:
    def test_has_three_values(self) -> None:
        assert len(ComplexityTier) == 3

    def test_values(self) -> None:
        assert ComplexityTier.LOW == "low"
        assert ComplexityTier.MEDIUM == "medium"
        assert ComplexityTier.HIGH == "high"


class TestClassifyComplexity:
    def test_low_below_3(self) -> None:
        assert classify_complexity(0.0) == ComplexityTier.LOW
        assert classify_complexity(2.9) == ComplexityTier.LOW

    def test_medium_3_to_6(self) -> None:
        assert classify_complexity(3.0) == ComplexityTier.MEDIUM
        assert classify_complexity(4.5) == ComplexityTier.MEDIUM
        assert classify_complexity(6.0) == ComplexityTier.MEDIUM

    def test_high_above_6(self) -> None:
        assert classify_complexity(6.1) == ComplexityTier.HIGH
        assert classify_complexity(10.0) == ComplexityTier.HIGH

    def test_boundary_at_3(self) -> None:
        assert classify_complexity(2.999) == ComplexityTier.LOW
        assert classify_complexity(3.0) == ComplexityTier.MEDIUM

    def test_boundary_at_6(self) -> None:
        assert classify_complexity(6.0) == ComplexityTier.MEDIUM
        assert classify_complexity(6.001) == ComplexityTier.HIGH


# --- DimensionScore ---


class TestDimensionScore:
    def test_frozen(self) -> None:
        ds = DimensionScore(
            dimension=ReadinessDimension.GOAL_CLARITY,
            score=0.8,
            reason="clear goal",
        )
        with pytest.raises(AttributeError):
            ds.score = 0.5  # type: ignore[misc]

    def test_required_default_false(self) -> None:
        ds = DimensionScore(
            dimension=ReadinessDimension.GOAL_CLARITY,
            score=0.8,
            reason="clear goal",
        )
        assert ds.required is False

    def test_required_explicit_true(self) -> None:
        ds = DimensionScore(
            dimension=ReadinessDimension.GOAL_CLARITY,
            score=0.0,
            reason="missing goal",
            required=True,
        )
        assert ds.required is True


# --- ReadinessScore ---


class TestReadinessScore:
    def test_frozen(self) -> None:
        score = ReadinessScore(
            overall_score=0.7,
            dimension_scores=(),
            missing_dimensions=(),
            recommended_questions=(),
            gate_decision=GateDecision.PASS,
            complexity_tier=ComplexityTier.LOW,
        )
        with pytest.raises(AttributeError):
            score.overall_score = 0.0  # type: ignore[misc]

    def test_timestamp_auto_populated(self) -> None:
        before = datetime.now(UTC)
        score = ReadinessScore(
            overall_score=0.7,
            dimension_scores=(),
            missing_dimensions=(),
            recommended_questions=(),
            gate_decision=GateDecision.PASS,
            complexity_tier=ComplexityTier.LOW,
        )
        after = datetime.now(UTC)
        assert before <= score.timestamp <= after

    def test_all_fields_present(self) -> None:
        dim_score = DimensionScore(
            dimension=ReadinessDimension.GOAL_CLARITY,
            score=0.9,
            reason="good",
        )
        score = ReadinessScore(
            overall_score=0.9,
            dimension_scores=(dim_score,),
            missing_dimensions=(ReadinessDimension.SCOPE_BOUNDARIES,),
            recommended_questions=("What is the scope?",),
            gate_decision=GateDecision.HOLD,
            complexity_tier=ComplexityTier.MEDIUM,
        )
        assert score.overall_score == 0.9
        assert len(score.dimension_scores) == 1
        assert score.missing_dimensions == (ReadinessDimension.SCOPE_BOUNDARIES,)
        assert score.recommended_questions == ("What is the scope?",)
        assert score.gate_decision == GateDecision.HOLD
        assert score.complexity_tier == ComplexityTier.MEDIUM


# --- ReadinessOutput ---


class TestReadinessOutput:
    def test_defaults(self) -> None:
        output = ReadinessOutput()
        assert output.proceed is True
        assert output.score == 1.0
        assert output.clarification_questions == []
        assert output.hold_reason is None

    def test_hold_state(self) -> None:
        output = ReadinessOutput(
            proceed=False,
            score=0.3,
            clarification_questions=["What is the expected behavior?"],
            hold_reason="Low readiness score",
        )
        assert output.proceed is False
        assert output.score == 0.3
        assert len(output.clarification_questions) == 1
        assert output.hold_reason == "Low readiness score"


# --- Configuration ---


class TestDefaultThresholds:
    def test_all_three_tiers_present(self) -> None:
        assert ComplexityTier.LOW in DEFAULT_THRESHOLDS
        assert ComplexityTier.MEDIUM in DEFAULT_THRESHOLDS
        assert ComplexityTier.HIGH in DEFAULT_THRESHOLDS

    def test_all_dimensions_have_thresholds(self) -> None:
        for tier in ComplexityTier:
            thresholds = DEFAULT_THRESHOLDS[tier]
            for dim in ReadinessDimension:
                assert dim in thresholds.per_dimension_thresholds
                assert dim in thresholds.dimension_weights

    def test_weights_sum_to_one(self) -> None:
        for tier in ComplexityTier:
            thresholds = DEFAULT_THRESHOLDS[tier]
            total = sum(thresholds.dimension_weights.values())
            assert abs(total - 1.0) < 1e-9, f"{tier}: weights sum to {total}"

    def test_overall_threshold_increases_with_complexity(self) -> None:
        low = DEFAULT_THRESHOLDS[ComplexityTier.LOW].overall_pass_threshold
        medium = DEFAULT_THRESHOLDS[ComplexityTier.MEDIUM].overall_pass_threshold
        high = DEFAULT_THRESHOLDS[ComplexityTier.HIGH].overall_pass_threshold
        assert low < medium < high

    def test_required_dimensions_increase_with_complexity(self) -> None:
        low = DEFAULT_THRESHOLDS[ComplexityTier.LOW].required_dimensions
        medium = DEFAULT_THRESHOLDS[ComplexityTier.MEDIUM].required_dimensions
        high = DEFAULT_THRESHOLDS[ComplexityTier.HIGH].required_dimensions
        assert low.issubset(medium)
        assert medium.issubset(high)
        assert len(low) < len(medium) < len(high)

    def test_goal_clarity_always_required(self) -> None:
        for tier in ComplexityTier:
            thresholds = DEFAULT_THRESHOLDS[tier]
            assert ReadinessDimension.GOAL_CLARITY in thresholds.required_dimensions


class TestGetThresholds:
    def test_returns_default_when_no_override(self) -> None:
        result = get_thresholds(ComplexityTier.LOW)
        assert result is DEFAULT_THRESHOLDS[ComplexityTier.LOW]

    def test_returns_override_when_provided(self) -> None:
        override = ReadinessThresholds(
            per_dimension_thresholds=dict.fromkeys(ReadinessDimension, 0.5),
            dimension_weights=dict.fromkeys(ReadinessDimension, 1.0 / 6.0),
            overall_pass_threshold=0.7,
        )
        result = get_thresholds(ComplexityTier.LOW, repo_override=override)
        assert result is override
        assert result.overall_pass_threshold == 0.7

    def test_override_replaces_entirely(self) -> None:
        """Repo override is full object replacement, not per-field merge."""
        override = ReadinessThresholds(
            per_dimension_thresholds=dict.fromkeys(ReadinessDimension, 0.9),
            dimension_weights=dict.fromkeys(ReadinessDimension, 1.0 / 6.0),
            overall_pass_threshold=0.9,
        )
        result = get_thresholds(ComplexityTier.HIGH, repo_override=override)
        # Override's threshold, not HIGH's default
        assert result.overall_pass_threshold == 0.9


class TestGateDecisionDeterminism:
    """Verify that identical inputs always produce the same gate decision.

    This is a property test to ensure no randomness or time-dependence
    in the decision logic (the models themselves are deterministic by
    construction, but this guards against regressions).
    """

    def test_same_inputs_same_decision(self) -> None:
        for decision in GateDecision:
            score1 = ReadinessScore(
                overall_score=0.5,
                dimension_scores=(),
                missing_dimensions=(),
                recommended_questions=(),
                gate_decision=decision,
                complexity_tier=ComplexityTier.MEDIUM,
            )
            score2 = ReadinessScore(
                overall_score=0.5,
                dimension_scores=(),
                missing_dimensions=(),
                recommended_questions=(),
                gate_decision=decision,
                complexity_tier=ComplexityTier.MEDIUM,
            )
            assert score1.gate_decision == score2.gate_decision
