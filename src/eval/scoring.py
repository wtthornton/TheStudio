"""Dimension-specific scoring functions for agent evaluation.

Epic 30, Story 30.1: Each function scores a specific quality dimension
of agent output on a 0.0-1.0 scale. Designed for IntentAgentOutput but
generic enough for other structured outputs.
"""

from __future__ import annotations

from src.eval.models import EvalResult, EvalSummary


def score_goal_clarity(goal: str, expected_keywords: list[str]) -> float:
    """Score goal statement quality based on keyword overlap and length.

    Returns 0.0-1.0. Checks:
    - Goal is non-empty (0 if empty)
    - Goal contains expected keywords (weighted 0.7)
    - Goal is substantive (>10 words, weighted 0.3)
    """
    if not goal or not goal.strip():
        return 0.0

    words = goal.lower().split()

    # Keyword overlap (70% weight)
    if expected_keywords:
        matches = sum(1 for kw in expected_keywords if kw.lower() in goal.lower())
        keyword_score = min(matches / len(expected_keywords), 1.0)
    else:
        keyword_score = 1.0 if len(words) > 5 else 0.5

    # Substantiveness (30% weight): penalize very short goals
    length_score = min(len(words) / 10, 1.0)

    return keyword_score * 0.7 + length_score * 0.3


def score_constraint_coverage(
    constraints: list[str],
    expected_constraints: list[str],
) -> float:
    """Score constraint coverage as fraction of expected constraints present.

    Returns 0.0-1.0. Uses case-insensitive substring matching:
    an expected constraint is "covered" if any actual constraint
    contains it as a substring.
    """
    if not expected_constraints:
        return 1.0 if constraints else 0.5

    if not constraints:
        return 0.0

    constraints_lower = [c.lower() for c in constraints]
    matches = 0
    for expected in expected_constraints:
        expected_lower = expected.lower()
        if any(expected_lower in c for c in constraints_lower):
            matches += 1

    return matches / len(expected_constraints)


def score_ac_completeness(
    acceptance_criteria: list[str],
    expected_acs: list[str],
) -> float:
    """Score acceptance criteria completeness.

    Returns 0.0-1.0. Checks:
    - Expected ACs are covered (substring match, weighted 0.6)
    - ACs are specific (avg length > 8 words, weighted 0.2)
    - ACs exist at all (weighted 0.2)
    """
    if not acceptance_criteria:
        return 0.0

    # Existence (20% weight)
    existence_score = 1.0

    # Coverage (60% weight)
    if expected_acs:
        acs_lower = [ac.lower() for ac in acceptance_criteria]
        matches = 0
        for expected in expected_acs:
            expected_lower = expected.lower()
            if any(expected_lower in c for c in acs_lower):
                matches += 1
        coverage_score = matches / len(expected_acs)
    else:
        coverage_score = 1.0

    # Specificity (20% weight): average word count > 8
    avg_words = sum(len(ac.split()) for ac in acceptance_criteria) / len(acceptance_criteria)
    specificity_score = min(avg_words / 8, 1.0)

    return existence_score * 0.2 + coverage_score * 0.6 + specificity_score * 0.2


def score_invariant_presence(
    invariants: list[str],
    expects_invariants: bool,
) -> float:
    """Score invariant presence.

    Returns 0.0-1.0.
    - If invariants expected and present: 1.0
    - If invariants expected but empty: 0.0
    - If invariants not expected but present: 1.0 (bonus, no penalty)
    - If invariants not expected and empty: 0.8 (slight penalty for
      not identifying any, since most changes have implicit invariants)
    """
    has_invariants = bool(invariants and any(i.strip() for i in invariants))

    if expects_invariants:
        return 1.0 if has_invariants else 0.0
    return 1.0 if has_invariants else 0.8


def score_non_goal_specificity(non_goals: list[str], issue_title: str = "") -> float:
    """Score non-goal quality.

    Returns 0.0-1.0. Checks:
    - Non-goals are present (0.5 base)
    - Non-goals don't just restate the title (0.25)
    - Non-goals are specific (avg > 5 words, 0.25)
    """
    if not non_goals:
        return 0.0

    # Base: they exist
    base_score = 0.5

    # Not just restating title (25%)
    if issue_title:
        title_lower = issue_title.lower()
        restates = sum(1 for ng in non_goals if ng.lower().strip() == title_lower.strip())
        restate_score = 0.0 if restates == len(non_goals) else 0.25
    else:
        restate_score = 0.25

    # Specificity (25%)
    avg_words = sum(len(ng.split()) for ng in non_goals) / len(non_goals)
    specificity_score = min(avg_words / 5, 1.0) * 0.25

    return base_score + restate_score + specificity_score


def aggregate_scores(results: list[EvalResult], agent_name: str = "") -> EvalSummary:
    """Aggregate per-case results into an EvalSummary."""
    if not results:
        return EvalSummary(agent_name=agent_name)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    parsed = sum(1 for r in results if r.parse_success)

    return EvalSummary(
        agent_name=agent_name or (results[0].agent_name if results else ""),
        total_cases=total,
        passed_count=passed,
        pass_rate=passed / total,
        parse_success_rate=parsed / total,
        mean_goal_clarity=sum(r.goal_clarity for r in results) / total,
        mean_constraint_coverage=sum(r.constraint_coverage for r in results) / total,
        mean_ac_completeness=sum(r.ac_completeness for r in results) / total,
        mean_invariant_presence=sum(r.invariant_presence for r in results) / total,
        mean_non_goal_specificity=sum(r.non_goal_specificity for r in results) / total,
        total_cost_usd=sum(r.cost_usd for r in results),
        total_duration_ms=sum(r.duration_ms for r in results),
        mean_duration_ms=sum(r.duration_ms for r in results) / total,
        results=results,
    )
