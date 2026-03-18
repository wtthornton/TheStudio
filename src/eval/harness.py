"""Evaluation harness — runs agents against labeled test cases.

Epic 30, Story 30.1: Orchestrates agent execution, captures results,
scores outputs, and produces structured EvalResult/EvalSummary objects.
Works with both mock and real LLM providers.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from src.agent.framework import AgentConfig, AgentContext, AgentRunner
from src.eval.models import EvalCase, EvalResult, EvalSummary, ModelComparisonResult
from src.eval.scoring import (
    aggregate_scores,
    score_ac_completeness,
    score_constraint_coverage,
    score_goal_clarity,
    score_invariant_presence,
    score_non_goal_specificity,
)

logger = logging.getLogger(__name__)

# Minimum weighted score across all dimensions to count as "passed"
PASS_THRESHOLD = 0.6


async def run_eval(
    agent_config: AgentConfig,
    cases: list[EvalCase],
    *,
    context_builder: ContextBuilder | None = None,
    score_fn: ScoreFn | None = None,
    pass_threshold: float = PASS_THRESHOLD,
) -> EvalSummary:
    """Run an agent against all test cases and return aggregated results.

    Args:
        agent_config: The agent configuration to evaluate.
        cases: Labeled test cases to run against.
        context_builder: Optional function to build AgentContext from an EvalCase.
            Defaults to ``default_context_builder``.
        score_fn: Optional function to score parsed output against expected values.
            Defaults to ``score_intent_output``.
        pass_threshold: Minimum weighted score to count a case as passed.

    Returns:
        EvalSummary with per-case results and aggregated metrics.
    """
    runner = AgentRunner(agent_config)
    build_context = context_builder or default_context_builder
    score = score_fn or score_intent_output
    results: list[EvalResult] = []

    for case in cases:
        result = await _run_single(
            runner=runner,
            config=agent_config,
            case=case,
            build_context=build_context,
            score=score,
            pass_threshold=pass_threshold,
        )
        results.append(result)
        logger.info(
            "Case %s: passed=%s, parse=%s, cost=$%.4f, duration=%dms",
            case.case_id,
            result.passed,
            result.parse_success,
            result.cost_usd,
            result.duration_ms,
        )

    return aggregate_scores(results, agent_name=agent_config.agent_name)


# -- Type aliases for pluggable components ----------------------------------

ContextBuilder = Callable[[EvalCase], AgentContext]
ScoreFn = Callable[[Any, EvalCase], dict[str, float]]


# -- Default implementations ------------------------------------------------


def default_context_builder(case: EvalCase) -> AgentContext:
    """Build an AgentContext from an EvalCase for intent-style agents."""
    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
    )


def score_intent_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score an IntentAgentOutput-shaped object against expected values.

    Works with any object that has goal, constraints, acceptance_criteria,
    invariants, and non_goals attributes (or dict keys).
    """
    if parsed is None:
        return {
            "goal_clarity": 0.0,
            "constraint_coverage": 0.0,
            "ac_completeness": 0.0,
            "invariant_presence": 0.0,
            "non_goal_specificity": 0.0,
        }

    # Support both Pydantic models and dicts
    if isinstance(parsed, BaseModel):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = vars(parsed) if hasattr(parsed, "__dict__") else {}

    goal = data.get("goal", "")
    constraints = data.get("constraints", [])
    acs = data.get("acceptance_criteria", [])
    invariants = data.get("invariants", [])
    non_goals = data.get("non_goals", [])

    return {
        "goal_clarity": score_goal_clarity(goal, case.expected_goal_keywords),
        "constraint_coverage": score_constraint_coverage(
            constraints,
            case.expected_constraints,
        ),
        "ac_completeness": score_ac_completeness(acs, case.expected_acs),
        "invariant_presence": score_invariant_presence(
            invariants,
            case.expects_invariants,
        ),
        "non_goal_specificity": score_non_goal_specificity(
            non_goals,
            case.issue_title,
        ),
    }


async def run_comparison_eval(
    agent_config: AgentConfig,
    cases: list[EvalCase],
    *,
    baseline_class: str = "balanced",
    candidate_class: str = "fast",
    context_builder: ContextBuilder | None = None,
    score_fn: ScoreFn | None = None,
    pass_threshold: float = PASS_THRESHOLD,
    quality_threshold: float = 0.8,
) -> ModelComparisonResult:
    """Run an agent eval on two model classes and compare results.

    Epic 32, Story 32.3: Creates modified copies of the agent config
    with different model_class values and runs both. Returns a
    ModelComparisonResult with pass_rate delta, cost savings, and
    whether the candidate meets the quality threshold.

    Args:
        agent_config: Base agent configuration.
        cases: Labeled test cases.
        baseline_class: Model class for the baseline run (default: "balanced").
        candidate_class: Model class for the candidate run (default: "fast").
        quality_threshold: Minimum quality_ratio to pass (default: 0.8 = 80%).
    """
    import dataclasses

    # Create configs for each model class
    baseline_config = dataclasses.replace(agent_config, model_class=baseline_class)
    candidate_config = dataclasses.replace(agent_config, model_class=candidate_class)

    logger.info(
        "Starting comparison eval: %s vs %s for %s (%d cases)",
        baseline_class, candidate_class, agent_config.agent_name, len(cases),
    )

    # Run both
    baseline_summary = await run_eval(
        baseline_config, cases,
        context_builder=context_builder, score_fn=score_fn,
        pass_threshold=pass_threshold,
    )
    candidate_summary = await run_eval(
        candidate_config, cases,
        context_builder=context_builder, score_fn=score_fn,
        pass_threshold=pass_threshold,
    )

    # Calculate comparison metrics
    baseline_rate = baseline_summary.pass_rate or 0.001  # avoid division by zero
    candidate_rate = candidate_summary.pass_rate
    quality_ratio = candidate_rate / baseline_rate
    pass_rate_delta = candidate_rate - baseline_summary.pass_rate

    baseline_cost = baseline_summary.total_cost_usd or 0.001
    cost_savings = (baseline_cost - candidate_summary.total_cost_usd) / baseline_cost

    result = ModelComparisonResult(
        agent_name=agent_config.agent_name,
        baseline_class=baseline_class,
        candidate_class=candidate_class,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        pass_rate_delta=pass_rate_delta,
        cost_savings_pct=cost_savings * 100,
        quality_ratio=quality_ratio,
        meets_threshold=quality_ratio >= quality_threshold,
    )

    logger.info(
        "Comparison complete: %s — baseline=%.0f%%, candidate=%.0f%%, "
        "quality_ratio=%.2f, cost_savings=%.1f%%, meets_threshold=%s",
        agent_config.agent_name,
        baseline_summary.pass_rate * 100,
        candidate_summary.pass_rate * 100,
        quality_ratio,
        result.cost_savings_pct,
        result.meets_threshold,
    )

    return result


async def _run_single(
    *,
    runner: AgentRunner,
    config: AgentConfig,
    case: EvalCase,
    build_context: ContextBuilder,
    score: ScoreFn,
    pass_threshold: float,
) -> EvalResult:
    """Run a single evaluation case and return scored result."""
    context = build_context(case)
    start = time.monotonic()

    try:
        agent_result = await runner.run(context)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("Agent error on case %s", case.case_id)
        return EvalResult(
            case_id=case.case_id,
            agent_name=config.agent_name,
            passed=False,
            parse_success=False,
            error=str(exc),
            duration_ms=elapsed_ms,
        )

    elapsed_ms = int((time.monotonic() - start) * 1000)
    parse_success = agent_result.parsed_output is not None

    # Score the output
    scores = score(agent_result.parsed_output, case)

    # Weighted average to determine pass/fail
    weights = {
        "goal_clarity": 0.30,
        "constraint_coverage": 0.20,
        "ac_completeness": 0.25,
        "invariant_presence": 0.15,
        "non_goal_specificity": 0.10,
    }
    weighted_score = sum(scores.get(dim, 0.0) * w for dim, w in weights.items())

    return EvalResult(
        case_id=case.case_id,
        agent_name=config.agent_name,
        passed=weighted_score >= pass_threshold,
        goal_clarity=scores.get("goal_clarity", 0.0),
        constraint_coverage=scores.get("constraint_coverage", 0.0),
        ac_completeness=scores.get("ac_completeness", 0.0),
        invariant_presence=scores.get("invariant_presence", 0.0),
        non_goal_specificity=scores.get("non_goal_specificity", 0.0),
        parse_success=parse_success,
        raw_output=agent_result.raw_output,
        cost_usd=agent_result.cost_estimated,
        duration_ms=elapsed_ms,
        parsed=agent_result.parsed_output,
    )
