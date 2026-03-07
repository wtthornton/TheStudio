"""Intent Correctness Eval — measures how well an Intent Specification matches the source issue.

Compares the generated intent (goal, acceptance criteria) against the original issue text.
Scoring uses keyword/structure matching: overlap of key terms and acceptance criteria coverage.
"""

import re
from dataclasses import dataclass

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType

# Minimum score threshold for a pass
PASS_THRESHOLD = 0.6


@dataclass
class IntentMatch:
    """Breakdown of intent matching analysis."""

    goal_keyword_overlap: float
    criteria_coverage: float
    key_terms_found: list[str]
    key_terms_missing: list[str]


def _extract_key_terms(text: str) -> set[str]:
    """Extract meaningful terms from text, filtering stop words."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "and", "but", "or", "nor", "not", "so",
        "yet", "both", "either", "neither", "each", "every", "all", "any",
        "few", "more", "most", "other", "some", "such", "no", "only", "own",
        "same", "than", "too", "very", "just", "because", "if", "when", "that",
        "this", "it", "its", "which", "what", "who", "whom", "how", "where",
        "there", "then", "here", "up", "out", "about",
    }
    words = re.findall(r"[a-z][a-z_\-]{2,}", text.lower())
    return {w for w in words if w not in stop_words}


def _compute_goal_overlap(issue_text: str, goal: str) -> tuple[float, list[str], list[str]]:
    """Compute keyword overlap between issue text and intent goal."""
    issue_terms = _extract_key_terms(issue_text)
    goal_terms = _extract_key_terms(goal)

    if not issue_terms:
        return 1.0 if not goal_terms else 0.0, [], []

    found = sorted(issue_terms & goal_terms)
    missing = sorted(issue_terms - goal_terms)

    overlap = len(found) / len(issue_terms) if issue_terms else 0.0
    return overlap, found, missing


def _compute_criteria_coverage(
    issue_text: str, acceptance_criteria: list[str]
) -> float:
    """Compute how well acceptance criteria cover the issue requirements.

    Each criterion that shares key terms with the issue contributes to coverage.
    """
    if not acceptance_criteria:
        return 0.0

    issue_terms = _extract_key_terms(issue_text)
    if not issue_terms:
        return 1.0

    covered_terms: set[str] = set()
    for criterion in acceptance_criteria:
        criterion_terms = _extract_key_terms(criterion)
        covered_terms |= (criterion_terms & issue_terms)

    return len(covered_terms) / len(issue_terms) if issue_terms else 0.0


class IntentCorrectnessEval(EvalSuite):
    """Evaluates whether an Intent Specification correctly captures the source issue.

    Input data format:
        issue_text: str — the original issue/ticket text
        goal: str — the generated intent goal
        acceptance_criteria: list[str] — the generated acceptance criteria

    Expected output format:
        match_quality: str — "clear_match", "partial_match", or "mismatch"
    """

    eval_type = EvalType.INTENT_CORRECTNESS

    def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        results = []
        for case in cases:
            if case.eval_type != self.eval_type:
                continue
            result = self._evaluate_case(case)
            results.append(result)
        return results

    def _evaluate_case(self, case: EvalCase) -> EvalResult:
        issue_text = case.input_data.get("issue_text", "")
        goal = case.input_data.get("goal", "")
        acceptance_criteria = case.input_data.get("acceptance_criteria", [])

        goal_overlap, found, missing = _compute_goal_overlap(issue_text, goal)
        criteria_coverage = _compute_criteria_coverage(issue_text, acceptance_criteria)

        # Weighted score: 40% goal overlap, 60% criteria coverage
        score = 0.4 * goal_overlap + 0.6 * criteria_coverage
        passed = score >= PASS_THRESHOLD

        expected_quality = case.expected_output.get("match_quality", "")
        if expected_quality == "clear_match":
            label_correct = passed and score >= 0.7
        elif expected_quality == "partial_match":
            label_correct = 0.3 <= score <= 0.8
        elif expected_quality == "mismatch":
            label_correct = not passed
        else:
            label_correct = True  # No expected label, skip label check

        match = IntentMatch(
            goal_keyword_overlap=round(goal_overlap, 3),
            criteria_coverage=round(criteria_coverage, 3),
            key_terms_found=found,
            key_terms_missing=missing,
        )

        failure_reason = None
        if not label_correct:
            failure_reason = (
                f"Expected {expected_quality} but got score={score:.3f} "
                f"(goal_overlap={goal_overlap:.3f}, criteria_coverage={criteria_coverage:.3f})"
            )

        return EvalResult(
            case_id=case.id,
            eval_type=self.eval_type,
            passed=label_correct,
            score=round(score, 3),
            details={
                "goal_keyword_overlap": match.goal_keyword_overlap,
                "criteria_coverage": match.criteria_coverage,
                "key_terms_found": match.key_terms_found,
                "key_terms_missing": match.key_terms_missing,
                "expected_quality": expected_quality,
            },
            failure_reason=failure_reason,
        )
