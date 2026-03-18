"""Context Agent evaluation runner.

Epic 32, Story 32.2: Validates the context agent's scope analysis,
risk enhancement, complexity rationale, and open question identification.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent.framework import AgentContext
from src.context.context_config import CONTEXT_AGENT_CONFIG
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary
from src.eval.routing_dataset import RoutingEvalCase, load_routing_dataset

logger = logging.getLogger(__name__)


def context_context_builder(case: EvalCase) -> AgentContext:
    """Build AgentContext for context evaluation."""
    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
    )


def score_context_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score context agent output against expected enrichment."""
    if parsed is None:
        return {
            "scope_relevance": 0.0,
            "service_coverage": 0.0,
            "risk_enhancement": 0.0,
            "has_complexity_rationale": 0.0,
            "actionable_questions": 0.0,
        }

    if hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = vars(parsed) if hasattr(parsed, "__dict__") else {}

    rcase = case if isinstance(case, RoutingEvalCase) else None
    scores: dict[str, float] = {}

    # 1. Scope summary contains relevant keywords
    scope = data.get("scope_summary", "").lower()
    if rcase and rcase.expected_scope_keywords:
        found = sum(
            1 for kw in rcase.expected_scope_keywords
            if kw.lower() in scope
        )
        scores["scope_relevance"] = min(
            found / max(len(rcase.expected_scope_keywords), 1), 1.0
        )
    else:
        scores["scope_relevance"] = 1.0 if len(scope) > 10 else 0.0

    # 2. Impacted services count
    services = data.get("impacted_services", [])
    if rcase:
        min_count = rcase.expected_impacted_count_min
        scores["service_coverage"] = (
            1.0 if len(services) >= min_count else len(services) / max(min_count, 1)
        )
    else:
        scores["service_coverage"] = 1.0 if services else 0.0

    # 3. Risk flags enhanced beyond input
    risk_flags = data.get("risk_flags", {})
    if rcase and rcase.expected_risk_keys:
        found = sum(1 for k in rcase.expected_risk_keys if risk_flags.get(k))
        scores["risk_enhancement"] = found / len(rcase.expected_risk_keys)
    else:
        scores["risk_enhancement"] = 1.0

    # 4. Has complexity rationale
    rationale = data.get("complexity_rationale", "")
    scores["has_complexity_rationale"] = 1.0 if len(rationale) > 20 else 0.0

    # 5. Open questions are actionable (non-empty)
    questions = data.get("open_questions", [])
    # For complex issues, we expect questions; for simple ones, none is ok
    if case.complexity == "high":
        scores["actionable_questions"] = 1.0 if questions else 0.5
    else:
        scores["actionable_questions"] = 1.0

    return scores


async def run_context_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the context agent evaluation."""
    dataset = cases if cases is not None else load_routing_dataset()
    # Filter to accepted cases only (context agent doesn't process rejected issues)
    accepted = [
        c for c in dataset
        if not isinstance(c, RoutingEvalCase) or c.expected_accepted
    ]
    logger.info("Starting context eval: %d cases", len(accepted))

    return await run_eval(
        agent_config=CONTEXT_AGENT_CONFIG,
        cases=accepted,
        context_builder=context_context_builder,
        score_fn=score_context_output,
    )
