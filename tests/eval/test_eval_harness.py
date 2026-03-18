"""Tests for the evaluation harness, scoring functions, and dataset.

Epic 30, Story 30.1: Validates that the eval infrastructure works
correctly with mock providers (no API key needed). Integration tests
with real LLM are in test_intent_eval.py (Story 30.2).
"""

from __future__ import annotations

import pytest

from src.eval.dataset import load_intent_dataset
from src.eval.harness import (
    default_context_builder,
    run_comparison_eval,
    run_eval,
    score_intent_output,
)
from src.eval.models import EvalCase, EvalResult, ModelComparisonResult
from src.eval.scoring import (
    aggregate_scores,
    score_ac_completeness,
    score_constraint_coverage,
    score_goal_clarity,
    score_invariant_presence,
    score_non_goal_specificity,
)

# ===================================================================
# Dataset tests
# ===================================================================


class TestDataset:
    """Validate the labeled dataset loads correctly."""

    def test_dataset_loads_10_cases(self) -> None:
        cases = load_intent_dataset()
        assert len(cases) == 10

    def test_all_cases_have_required_fields(self) -> None:
        for case in load_intent_dataset():
            assert case.case_id, "Missing case_id"
            assert case.category, f"Missing category for {case.case_id}"
            assert case.issue_title, f"Missing title for {case.case_id}"
            assert case.issue_body, f"Missing body for {case.case_id}"
            assert len(case.issue_body) > 50, f"Body too short for {case.case_id}"

    def test_all_cases_have_expected_keywords(self) -> None:
        for case in load_intent_dataset():
            assert case.expected_goal_keywords, f"Missing expected_goal_keywords for {case.case_id}"

    def test_case_ids_are_unique(self) -> None:
        cases = load_intent_dataset()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids)), "Duplicate case_id found"

    def test_categories_span_expected_types(self) -> None:
        cases = load_intent_dataset()
        categories = {c.category for c in cases}
        expected = {
            "bug_fix",
            "feature",
            "security",
            "refactor",
            "documentation",
            "breaking_change",
            "multi_file",
            "performance",
            "dependency_update",
            "api_design",
        }
        assert categories == expected


# ===================================================================
# Scoring function tests
# ===================================================================


class TestScoreGoalClarity:
    """Tests for score_goal_clarity."""

    def test_empty_goal_returns_zero(self) -> None:
        assert score_goal_clarity("", ["keyword"]) == 0.0

    def test_whitespace_goal_returns_zero(self) -> None:
        assert score_goal_clarity("   ", []) == 0.0

    def test_perfect_keyword_match(self) -> None:
        score = score_goal_clarity(
            "Fix the avatar URL to return a valid Gravatar fallback for default users",
            ["avatar", "gravatar", "default"],
        )
        assert score > 0.8

    def test_no_keyword_match(self) -> None:
        score = score_goal_clarity(
            "Update the README file with new instructions",
            ["avatar", "gravatar"],
        )
        assert score < 0.5

    def test_long_goal_gets_length_bonus(self) -> None:
        short = score_goal_clarity("Fix bug", ["fix"])
        long_goal = score_goal_clarity(
            "Fix the avatar URL to return a valid Gravatar fallback "
            "URL for users with default avatars",
            ["fix"],
        )
        assert long_goal > short

    def test_no_expected_keywords_still_scores(self) -> None:
        score = score_goal_clarity("A reasonable goal statement for the task", [])
        assert 0.0 < score <= 1.0


class TestScoreConstraintCoverage:
    """Tests for score_constraint_coverage."""

    def test_no_expected_with_constraints_returns_one(self) -> None:
        assert score_constraint_coverage(["some constraint"], []) == 1.0

    def test_no_expected_no_constraints_returns_half(self) -> None:
        assert score_constraint_coverage([], []) == 0.5

    def test_no_actual_constraints_returns_zero(self) -> None:
        assert score_constraint_coverage([], ["tests"]) == 0.0

    def test_full_coverage(self) -> None:
        actual = [
            "Must include tests for new behavior",
            "Must maintain backward compatibility",
        ]
        expected = ["tests", "backward"]
        assert score_constraint_coverage(actual, expected) == 1.0

    def test_partial_coverage(self) -> None:
        actual = ["Must include tests"]
        expected = ["tests", "backward", "security"]
        score = score_constraint_coverage(actual, expected)
        assert 0.3 <= score <= 0.4  # 1/3


class TestScoreAcCompleteness:
    """Tests for score_ac_completeness."""

    def test_no_acs_returns_zero(self) -> None:
        assert score_ac_completeness([], ["expected"]) == 0.0

    def test_acs_with_no_expected_returns_high(self) -> None:
        score = score_ac_completeness(
            ["A specific acceptance criterion with enough detail"],
            [],
        )
        assert score > 0.8

    def test_coverage_and_specificity(self) -> None:
        acs = [
            "The avatar_url property returns a valid HTTPS URL for all users",
            "Users without custom avatars get a Gravatar URL based on email hash",
            "Existing custom avatar URLs are not modified by this change",
        ]
        expected = ["avatar_url", "gravatar", "custom"]
        score = score_ac_completeness(acs, expected)
        assert score > 0.7


class TestScoreInvariantPresence:
    """Tests for score_invariant_presence."""

    def test_expected_and_present(self) -> None:
        assert score_invariant_presence(["Existing API must work"], True) == 1.0

    def test_expected_but_empty(self) -> None:
        assert score_invariant_presence([], True) == 0.0

    def test_not_expected_but_present(self) -> None:
        assert score_invariant_presence(["Something preserved"], False) == 1.0

    def test_not_expected_and_empty(self) -> None:
        assert score_invariant_presence([], False) == 0.8

    def test_whitespace_only_invariants_count_as_empty(self) -> None:
        assert score_invariant_presence(["  ", ""], True) == 0.0


class TestScoreNonGoalSpecificity:
    """Tests for score_non_goal_specificity."""

    def test_no_non_goals_returns_zero(self) -> None:
        assert score_non_goal_specificity([], "Some title") == 0.0

    def test_specific_non_goals_score_high(self) -> None:
        score = score_non_goal_specificity(
            [
                "Cursor-based pagination is out of scope for this change",
                "Caching layer will be addressed in a separate issue",
            ],
            "Add pagination to tasks endpoint",
        )
        assert score > 0.7

    def test_title_restatement_penalized(self) -> None:
        # When all non-goals restate the title, restate_score=0
        # but base (0.5) + specificity still contribute
        penalized = score_non_goal_specificity(
            ["Add pagination to tasks endpoint"],
            "Add pagination to tasks endpoint",
        )
        good = score_non_goal_specificity(
            ["Cursor-based pagination is out of scope for this change"],
            "Add pagination to tasks endpoint",
        )
        assert penalized < good


# ===================================================================
# Aggregation tests
# ===================================================================


class TestAggregateScores:
    """Tests for aggregate_scores."""

    def test_empty_results(self) -> None:
        summary = aggregate_scores([], agent_name="test")
        assert summary.total_cases == 0
        assert summary.pass_rate == 0.0

    def test_all_pass(self) -> None:
        results = [
            EvalResult(
                case_id=f"case_{i}",
                agent_name="test",
                passed=True,
                parse_success=True,
                goal_clarity=0.9,
                constraint_coverage=0.8,
                ac_completeness=0.85,
                invariant_presence=1.0,
                non_goal_specificity=0.7,
                cost_usd=0.01,
                duration_ms=100,
            )
            for i in range(5)
        ]
        summary = aggregate_scores(results)
        assert summary.total_cases == 5
        assert summary.pass_rate == 1.0
        assert summary.parse_success_rate == 1.0
        assert summary.mean_goal_clarity == pytest.approx(0.9)
        assert summary.total_cost_usd == pytest.approx(0.05)
        assert summary.mean_duration_ms == pytest.approx(100.0)

    def test_mixed_results(self) -> None:
        results = [
            EvalResult(case_id="pass", agent_name="test", passed=True, parse_success=True),
            EvalResult(case_id="fail", agent_name="test", passed=False, parse_success=True),
            EvalResult(case_id="error", agent_name="test", passed=False, parse_success=False),
        ]
        summary = aggregate_scores(results)
        assert summary.pass_rate == pytest.approx(1 / 3)
        assert summary.parse_success_rate == pytest.approx(2 / 3)


# ===================================================================
# Context builder tests
# ===================================================================


class TestDefaultContextBuilder:
    """Tests for default_context_builder."""

    def test_maps_case_to_context(self) -> None:
        case = EvalCase(
            case_id="test_01",
            category="bug_fix",
            issue_title="Fix avatar bug",
            issue_body="The avatar is broken",
            labels=["bug"],
            risk_flags={"security": True},
            complexity="low",
        )
        ctx = default_context_builder(case)
        assert ctx.issue_title == "Fix avatar bug"
        assert ctx.issue_body == "The avatar is broken"
        assert ctx.labels == ["bug"]
        assert ctx.risk_flags == {"security": True}
        assert ctx.complexity == "low"
        assert ctx.repo == "eval/test-repo"


# ===================================================================
# Score intent output tests
# ===================================================================


class TestScoreIntentOutput:
    """Tests for score_intent_output."""

    def test_none_output_returns_zeros(self) -> None:
        case = load_intent_dataset()[0]
        scores = score_intent_output(None, case)
        assert all(v == 0.0 for v in scores.values())

    def test_dict_output_scores(self) -> None:
        case = load_intent_dataset()[0]  # bug_fix
        output = {
            "goal": "Fix avatar_url to return Gravatar default URL instead of None",
            "constraints": ["Must include tests for new behavior"],
            "acceptance_criteria": [
                "avatar_url returns valid URL for users without custom avatars",
                "Gravatar fallback uses email hash",
                "Custom avatars not affected",
            ],
            "invariants": [],
            "non_goals": ["Not changing the avatar upload flow"],
        }
        scores = score_intent_output(output, case)
        assert scores["goal_clarity"] > 0.5
        assert scores["ac_completeness"] > 0.5
        assert scores["non_goal_specificity"] > 0.0

    def test_pydantic_model_output_scores(self) -> None:
        from src.intent.intent_config import IntentAgentOutput

        case = load_intent_dataset()[0]
        output = IntentAgentOutput(
            goal="Fix the avatar_url property to return a Gravatar URL as default",
            constraints=["Must include tests for the new fallback behavior"],
            invariants=[],
            acceptance_criteria=[
                "avatar_url returns valid URL for default avatar users",
                "Gravatar URL computed from user email hash",
                "Existing custom avatars unchanged",
            ],
            non_goals=["Not redesigning the avatar upload system"],
            assumptions=["Users have email addresses set"],
            open_questions=[],
        )
        scores = score_intent_output(output, case)
        assert scores["goal_clarity"] > 0.5
        assert scores["constraint_coverage"] > 0.0


# ===================================================================
# Harness integration test (mock provider, no API key)
# ===================================================================


class TestRunEvalMock:
    """Test run_eval with the mock LLM adapter (no API key needed).

    The mock adapter returns canned text, which won't parse as JSON.
    This validates the harness handles parse failures gracefully.
    """

    @pytest.mark.asyncio
    async def test_harness_runs_with_mock_provider(self) -> None:
        """Harness completes all cases even when parse fails."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()[:3]  # Subset for speed
        summary = await run_eval(INTENT_AGENT_CONFIG, cases)

        assert summary.total_cases == 3
        assert summary.agent_name == "intent_agent"
        assert len(summary.results) == 3
        # Mock adapter returns "Mock LLM response." which won't parse,
        # so the agent uses fallback. Fallback returns valid JSON, so
        # parse succeeds on the fallback output (but used_fallback=True).
        for result in summary.results:
            assert result.case_id in {c.case_id for c in cases}
            assert result.duration_ms >= 0
            assert result.cost_usd >= 0.0

    @pytest.mark.asyncio
    async def test_harness_produces_summary_metrics(self) -> None:
        """Summary metrics are computed correctly."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()[:2]
        summary = await run_eval(INTENT_AGENT_CONFIG, cases)

        assert 0.0 <= summary.pass_rate <= 1.0
        assert summary.total_duration_ms >= 0
        assert summary.total_cost_usd >= 0.0

    @pytest.mark.asyncio
    async def test_harness_full_dataset(self) -> None:
        """Harness processes all 10 cases without error."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()
        summary = await run_eval(INTENT_AGENT_CONFIG, cases)

        assert summary.total_cases == 10
        assert len(summary.results) == 10
        # All cases should complete (no exceptions)
        for result in summary.results:
            assert result.error == ""


# ===================================================================
# Model comparison mode tests (Epic 32, Story 32.3)
# ===================================================================


class TestModelComparisonResult:
    """Test ModelComparisonResult dataclass."""

    def test_default_values(self) -> None:
        result = ModelComparisonResult(agent_name="test")
        assert result.baseline_class == "balanced"
        assert result.candidate_class == "fast"
        assert result.meets_threshold is False

    def test_comparison_fields(self) -> None:
        result = ModelComparisonResult(
            agent_name="test",
            quality_ratio=0.9,
            cost_savings_pct=60.0,
            meets_threshold=True,
        )
        assert result.quality_ratio == 0.9
        assert result.cost_savings_pct == 60.0
        assert result.meets_threshold is True


class TestRunComparisonEval:
    """Test run_comparison_eval with mock provider."""

    @pytest.mark.asyncio
    async def test_comparison_runs_both_classes(self) -> None:
        """Comparison eval runs baseline and candidate, returns comparison."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()[:2]
        result = await run_comparison_eval(
            INTENT_AGENT_CONFIG,
            cases,
            baseline_class="balanced",
            candidate_class="fast",
        )

        assert result.agent_name == "intent_agent"
        assert result.baseline_class == "balanced"
        assert result.candidate_class == "fast"
        assert result.baseline_summary is not None
        assert result.candidate_summary is not None
        assert result.baseline_summary.total_cases == 2
        assert result.candidate_summary.total_cases == 2

    @pytest.mark.asyncio
    async def test_comparison_computes_metrics(self) -> None:
        """Comparison computes quality ratio and cost savings."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()[:2]
        result = await run_comparison_eval(
            INTENT_AGENT_CONFIG,
            cases,
            quality_threshold=0.5,
        )

        # Both run with mock adapter, so results should be identical
        assert isinstance(result.quality_ratio, float)
        assert isinstance(result.cost_savings_pct, float)
        assert isinstance(result.meets_threshold, bool)

    @pytest.mark.asyncio
    async def test_comparison_high_threshold_fails(self) -> None:
        """When threshold is impossibly high, meets_threshold is False."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG

        cases = load_intent_dataset()[:1]
        result = await run_comparison_eval(
            INTENT_AGENT_CONFIG,
            cases,
            quality_threshold=2.0,  # 200% — impossible
        )

        assert result.meets_threshold is False
