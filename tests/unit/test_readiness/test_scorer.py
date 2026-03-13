"""Tests for the readiness scoring engine."""

from __future__ import annotations

from src.readiness.models import (
    ComplexityTier,
    GateDecision,
    ReadinessDimension,
)
from src.readiness.scorer import score_readiness

# --- Helpers ---


def _well_formed_body() -> str:
    """An issue body that should score highly across all dimensions."""
    return (
        "## Problem\n\n"
        "The login page times out after 30 seconds when users attempt to "
        "authenticate with SSO. This affects all users on the production "
        "environment since the last deployment.\n\n"
        "## Acceptance Criteria\n\n"
        "- [ ] SSO login completes within 5 seconds\n"
        "- [ ] Error handling displays a user-friendly message on timeout\n"
        "- [ ] Existing password-based login is unaffected\n\n"
        "## Out of Scope\n\n"
        "- Redesigning the login UI\n"
        "- Adding new SSO providers\n\n"
        "## Steps to Reproduce\n\n"
        "1. Navigate to /login\n"
        "2. Click 'Sign in with SSO'\n"
        "3. Wait 30 seconds\n"
        "4. Expected: redirect to dashboard\n"
        "5. Actual: timeout error\n\n"
        "Environment: Chrome 120, Windows 11\n\n"
        "## Dependencies\n\n"
        "Depends on #42 (SSO provider config update)\n"
    )


def _minimal_body() -> str:
    """A minimal body that should score poorly."""
    return "fix it"


# --- Goal Clarity ---


class TestGoalClarity:
    def test_well_formed_scores_high(self) -> None:
        result = score_readiness(
            issue_title="Fix SSO login timeout",
            issue_body=_well_formed_body(),
            complexity_tier=ComplexityTier.LOW,
        )
        goal = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.GOAL_CLARITY
        )
        assert goal.score >= 0.8

    def test_empty_body_scores_zero(self) -> None:
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
        )
        goal = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.GOAL_CLARITY
        )
        assert goal.score == 0.0

    def test_title_only_scores_low(self) -> None:
        result = score_readiness(
            issue_title="Fix login",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
        )
        goal = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.GOAL_CLARITY
        )
        assert goal.score < 0.5

    def test_short_body_with_keyword(self) -> None:
        result = score_readiness(
            issue_title="Bug report",
            issue_body="There is a bug in the login page",
            complexity_tier=ComplexityTier.LOW,
        )
        goal = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.GOAL_CLARITY
        )
        # Has keyword ("bug") but short body
        assert 0.0 < goal.score < 1.0


# --- Acceptance Criteria ---


class TestAcceptanceCriteria:
    def test_checkboxes_score_perfect(self) -> None:
        body = "## Criteria\n- [ ] First thing works\n- [ ] Second thing works\n"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
        )
        ac = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.ACCEPTANCE_CRITERIA
        )
        assert ac.score == 1.0

    def test_no_criteria_scores_zero(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Just do the thing",
            complexity_tier=ComplexityTier.LOW,
        )
        ac = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.ACCEPTANCE_CRITERIA
        )
        assert ac.score == 0.0

    def test_single_criterion_scores_half(self) -> None:
        body = "## Acceptance Criteria\n- The button should work correctly\n"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
        )
        ac = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.ACCEPTANCE_CRITERIA
        )
        assert ac.score == 0.5


# --- Scope Boundaries ---


class TestScopeBoundaries:
    def test_explicit_section_scores_perfect(self) -> None:
        body = "## Out of Scope\n- No UI changes\n- No new features\n"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.MEDIUM,
        )
        scope = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.SCOPE_BOUNDARIES
        )
        assert scope.score == 1.0

    def test_no_scope_low_complexity_lenient(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Simple change needed",
            complexity_tier=ComplexityTier.LOW,
        )
        scope = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.SCOPE_BOUNDARIES
        )
        assert scope.score == 0.5  # lenient for low complexity

    def test_no_scope_medium_complexity_zero(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Change needed but no scope defined",
            complexity_tier=ComplexityTier.MEDIUM,
        )
        scope = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.SCOPE_BOUNDARIES
        )
        assert scope.score == 0.0


# --- Risk Coverage ---


class TestRiskCoverage:
    def test_no_flags_scores_perfect(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Simple change",
            complexity_tier=ComplexityTier.LOW,
            risk_flags=None,
        )
        risk = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.RISK_COVERAGE
        )
        assert risk.score == 1.0

    def test_covered_flags_score_high(self) -> None:
        body = "This change affects security and authentication tokens"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
            risk_flags={"risk_security": True},
        )
        risk = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.RISK_COVERAGE
        )
        assert risk.score == 1.0

    def test_uncovered_flags_score_zero(self) -> None:
        body = "Simple text change"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
            risk_flags={"risk_security": True},
        )
        risk = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.RISK_COVERAGE
        )
        assert risk.score == 0.0

    def test_partial_coverage(self) -> None:
        body = "This involves security changes"
        result = score_readiness(
            issue_title="Test",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
            risk_flags={"risk_security": True, "risk_performance": True},
        )
        risk = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.RISK_COVERAGE
        )
        assert 0.0 < risk.score < 1.0


# --- Reproduction Context ---


class TestReproductionContext:
    def test_non_bug_scores_perfect(self) -> None:
        result = score_readiness(
            issue_title="Add new feature",
            issue_body="Please add dark mode support",
            complexity_tier=ComplexityTier.LOW,
            labels=["enhancement"],
        )
        repro = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.REPRODUCTION_CONTEXT
        )
        assert repro.score == 1.0

    def test_bug_with_repro_steps(self) -> None:
        body = (
            "Steps to reproduce:\n"
            "1. Click login\n"
            "Expected behavior: success\n"
            "Actual behavior: crash\n"
            "Environment: Chrome 120\n"
        )
        result = score_readiness(
            issue_title="Login crash",
            issue_body=body,
            complexity_tier=ComplexityTier.LOW,
            labels=["bug"],
        )
        repro = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.REPRODUCTION_CONTEXT
        )
        assert repro.score >= 0.7

    def test_bug_without_repro_scores_zero(self) -> None:
        result = score_readiness(
            issue_title="Login broken",
            issue_body="Login is broken please fix",
            complexity_tier=ComplexityTier.LOW,
            labels=["bug"],
        )
        repro = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.REPRODUCTION_CONTEXT
        )
        assert repro.score == 0.0


# --- Dependency Awareness ---


class TestDependencyAwareness:
    def test_low_complexity_always_passes(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Simple change",
            complexity_tier=ComplexityTier.LOW,
        )
        dep = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.DEPENDENCY_AWARENESS
        )
        assert dep.score == 1.0

    def test_high_complexity_with_deps(self) -> None:
        body = "This depends on #42 being merged first"
        result = score_readiness(
            issue_title="Complex change",
            issue_body=body,
            complexity_tier=ComplexityTier.HIGH,
        )
        dep = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.DEPENDENCY_AWARENESS
        )
        assert dep.score == 1.0

    def test_high_complexity_without_deps(self) -> None:
        body = "Complex change needed across multiple services"
        result = score_readiness(
            issue_title="Complex change",
            issue_body=body,
            complexity_tier=ComplexityTier.HIGH,
        )
        dep = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.DEPENDENCY_AWARENESS
        )
        assert dep.score == 0.0


# --- Gate Decision ---


class TestGateDecision:
    def test_observe_always_passes(self) -> None:
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.HIGH,
            trust_tier="observe",
        )
        assert result.gate_decision == GateDecision.PASS

    def test_suggest_high_score_passes(self) -> None:
        result = score_readiness(
            issue_title="Fix SSO login timeout",
            issue_body=_well_formed_body(),
            complexity_tier=ComplexityTier.LOW,
            trust_tier="suggest",
            labels=["bug"],
        )
        assert result.gate_decision == GateDecision.PASS

    def test_suggest_low_score_holds(self) -> None:
        result = score_readiness(
            issue_title="fix",
            issue_body="",
            complexity_tier=ComplexityTier.MEDIUM,
            trust_tier="suggest",
        )
        assert result.gate_decision == GateDecision.HOLD

    def test_required_dimension_zero_forces_hold(self) -> None:
        """A required dimension scoring 0 forces HOLD regardless of overall score."""
        # Goal clarity is always required. Empty title + empty body = 0 goal clarity.
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
            trust_tier="suggest",
        )
        assert result.gate_decision == GateDecision.HOLD

    def test_execute_enforces_like_suggest(self) -> None:
        result = score_readiness(
            issue_title="fix",
            issue_body="",
            complexity_tier=ComplexityTier.MEDIUM,
            trust_tier="execute",
        )
        assert result.gate_decision == GateDecision.HOLD


# --- Overall Score ---


class TestOverallScore:
    def test_well_formed_issue_scores_high(self) -> None:
        result = score_readiness(
            issue_title="Fix SSO login timeout",
            issue_body=_well_formed_body(),
            complexity_tier=ComplexityTier.MEDIUM,
            labels=["bug"],
        )
        assert result.overall_score >= 0.7

    def test_empty_issue_scores_low(self) -> None:
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
        )
        # N/A dimensions (risk, repro, deps) score 1.0 for low complexity,
        # so empty issues still get credit for non-applicable dimensions.
        assert result.overall_score < 0.6

    def test_minimal_body_scores_low(self) -> None:
        result = score_readiness(
            issue_title="fix",
            issue_body=_minimal_body(),
            complexity_tier=ComplexityTier.LOW,
        )
        # Minimal body still gets credit from N/A dimensions at low complexity.
        assert result.overall_score < 0.7

    def test_score_bounded_0_to_1(self) -> None:
        result = score_readiness(
            issue_title="Fix SSO login timeout",
            issue_body=_well_formed_body(),
            complexity_tier=ComplexityTier.LOW,
            labels=["bug"],
        )
        assert 0.0 <= result.overall_score <= 1.0

    def test_all_six_dimensions_scored(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Test body",
            complexity_tier=ComplexityTier.LOW,
        )
        assert len(result.dimension_scores) == 6
        scored_dims = {ds.dimension for ds in result.dimension_scores}
        assert scored_dims == set(ReadinessDimension)


# --- Missing Dimensions and Questions ---


class TestQuestionsAndMissing:
    def test_missing_dimensions_tracked(self) -> None:
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
        )
        assert len(result.missing_dimensions) > 0

    def test_questions_generated_for_missing(self) -> None:
        result = score_readiness(
            issue_title="",
            issue_body="",
            complexity_tier=ComplexityTier.LOW,
        )
        assert len(result.recommended_questions) > 0
        # Each question should be a non-empty string
        for q in result.recommended_questions:
            assert isinstance(q, str)
            assert len(q) > 10

    def test_well_formed_has_few_missing(self) -> None:
        result = score_readiness(
            issue_title="Fix SSO login timeout",
            issue_body=_well_formed_body(),
            complexity_tier=ComplexityTier.LOW,
            labels=["bug"],
        )
        assert len(result.missing_dimensions) <= 2

    def test_complexity_tier_recorded(self) -> None:
        result = score_readiness(
            issue_title="Test",
            issue_body="Test",
            complexity_tier=ComplexityTier.HIGH,
        )
        assert result.complexity_tier == ComplexityTier.HIGH


# --- Edge Cases ---


class TestEdgeCases:
    def test_single_line_issue(self) -> None:
        """Single-line issues should not crash the scorer."""
        result = score_readiness(
            issue_title="Fix it",
            issue_body="broken",
            complexity_tier=ComplexityTier.LOW,
        )
        assert result.overall_score >= 0.0

    def test_no_labels(self) -> None:
        """No labels should not crash the scorer."""
        result = score_readiness(
            issue_title="Test",
            issue_body="Test body with enough words to be coherent paragraph",
            complexity_tier=ComplexityTier.LOW,
            labels=[],
        )
        assert result.overall_score >= 0.0

    def test_all_risk_flags_set(self) -> None:
        """All risk flags set should not crash the scorer."""
        result = score_readiness(
            issue_title="Test",
            issue_body="Test body",
            complexity_tier=ComplexityTier.LOW,
            risk_flags={
                "risk_security": True,
                "risk_data": True,
                "risk_performance": True,
                "risk_destructive": True,
                "risk_privileged_access": True,
                "risk_migration": True,
            },
        )
        assert result.overall_score >= 0.0

    def test_unknown_risk_flag_not_penalized(self) -> None:
        """Unknown risk flags should not penalize the score."""
        result = score_readiness(
            issue_title="Test",
            issue_body="Test body",
            complexity_tier=ComplexityTier.LOW,
            risk_flags={"risk_unknown_future_flag": True},
        )
        risk = next(
            ds for ds in result.dimension_scores
            if ds.dimension == ReadinessDimension.RISK_COVERAGE
        )
        assert risk.score == 1.0
