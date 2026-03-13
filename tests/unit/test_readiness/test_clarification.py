"""Tests for the clarification comment formatter."""

from __future__ import annotations

from src.readiness.clarification import format_clarification_comment
from src.readiness.models import (
    ComplexityTier,
    DimensionScore,
    GateDecision,
    ReadinessDimension,
    ReadinessScore,
)

# --- Helpers ---


def _score_with_questions(*questions: str) -> ReadinessScore:
    """Build a ReadinessScore with the given recommended questions."""
    return ReadinessScore(
        overall_score=0.3,
        dimension_scores=(
            DimensionScore(
                dimension=ReadinessDimension.GOAL_CLARITY,
                score=0.0,
                reason="empty",
                required=True,
            ),
        ),
        missing_dimensions=(ReadinessDimension.GOAL_CLARITY,),
        recommended_questions=tuple(questions),
        gate_decision=GateDecision.HOLD,
        complexity_tier=ComplexityTier.LOW,
    )


def _score_no_questions() -> ReadinessScore:
    """Build a ReadinessScore with no recommended questions."""
    return ReadinessScore(
        overall_score=0.9,
        dimension_scores=(),
        missing_dimensions=(),
        recommended_questions=(),
        gate_decision=GateDecision.PASS,
        complexity_tier=ComplexityTier.LOW,
    )


# --- Structure Tests ---


class TestCommentStructure:
    def test_contains_marker(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "<!-- thestudio-readiness -->" in comment

    def test_contains_header(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "## More Information Needed" in comment

    def test_contains_intro(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "could you provide a bit more detail" in comment

    def test_contains_repo_name(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "acme/widgets" in comment

    def test_contains_re_evaluation_note(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "re-evaluate" in comment


# --- Question Rendering ---


class TestQuestionRendering:
    def test_single_question_numbered(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        assert "1. [ ] What is the goal?" in comment

    def test_two_questions_numbered(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?", "What are the requirements?"),
            "acme/widgets",
        )
        assert "1. [ ] What is the goal?" in comment
        assert "2. [ ] What are the requirements?" in comment

    def test_no_questions_still_valid(self) -> None:
        comment = format_clarification_comment(
            _score_no_questions(), "acme/widgets"
        )
        assert "## More Information Needed" in comment
        assert "<!-- thestudio-readiness -->" in comment


# --- Forbidden Terms ---


class TestForbiddenTerms:
    """Comment must NOT contain internal pipeline terminology."""

    FORBIDDEN: tuple[str, ...] = (
        "score",
        "threshold",
        "complexity index",
        "weight",
        "dimension",
    )

    def test_no_forbidden_terms_single_question(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions("What is the goal?"), "acme/widgets"
        )
        lower = comment.lower()
        for term in self.FORBIDDEN:
            assert term not in lower, f"Found forbidden term: {term!r}"

    def test_no_forbidden_terms_multiple_questions(self) -> None:
        comment = format_clarification_comment(
            _score_with_questions(
                "Could you describe the problem?",
                "What would need to be true for this to be resolved?",
                "Are there any areas that should be left out?",
            ),
            "test/repo",
        )
        lower = comment.lower()
        for term in self.FORBIDDEN:
            assert term not in lower, f"Found forbidden term: {term!r}"


# --- Length Constraint ---


class TestLengthConstraint:
    def test_two_questions_under_1000_chars(self) -> None:
        """Sprint goal 6: under 1000 characters for a 2-question scenario."""
        comment = format_clarification_comment(
            _score_with_questions(
                "Could you describe the problem or feature in more detail?",
                "What would need to be true for this issue to be resolved?",
            ),
            "acme/widgets",
        )
        assert len(comment) < 1000, f"Comment is {len(comment)} chars, expected < 1000"

    def test_six_questions_reasonable_length(self) -> None:
        """Even with all 6 dimensions missing, keep it manageable."""
        comment = format_clarification_comment(
            _score_with_questions(
                "Could you describe the problem?",
                "What are the acceptance criteria?",
                "What is out of scope?",
                "Are there risks to consider?",
                "How can this be reproduced?",
                "Are there dependencies?",
            ),
            "acme/widgets",
        )
        assert len(comment) < 1500
