"""Router Agent evaluation runner.

Epic 32, Story 32.2: Validates the expert routing agent's expert selection,
consultation pattern decisions, shadow recommendations, and escalation flags.
Covers both router and recruiter behavior (combined expert_routing step).
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent.framework import AgentContext
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary
from src.eval.routing_dataset import RoutingEvalCase, load_routing_dataset
from src.routing.router_config import ROUTER_AGENT_CONFIG

logger = logging.getLogger(__name__)


def router_context_builder(case: EvalCase) -> AgentContext:
    """Build AgentContext for router evaluation."""
    rcase = case if isinstance(case, RoutingEvalCase) else None
    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
        overlays=rcase.expected_overlays if rcase else [],
        extra={
            "base_role": rcase.expected_base_role if rcase else "developer",
            "required_classes": (
                rcase.expected_expert_classes if rcase else ["technical"]
            ),
        },
    )


def score_router_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score router agent output against expected expert selection."""
    if parsed is None:
        return {
            "expert_coverage": 0.0,
            "min_experts_met": 0.0,
            "pattern_specified": 0.0,
            "escalation_appropriate": 0.0,
            "has_adjustments": 0.0,
        }

    if hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = vars(parsed) if hasattr(parsed, "__dict__") else {}

    rcase = case if isinstance(case, RoutingEvalCase) else None
    scores: dict[str, float] = {}

    selections = data.get("selections", [])
    selected_classes = {
        s.get("expert_class", "") if isinstance(s, dict) else getattr(s, "expert_class", "")
        for s in selections
    }

    # 1. Expert class coverage
    if rcase and rcase.expected_expert_classes:
        expected = set(rcase.expected_expert_classes)
        found = len(selected_classes & expected)
        scores["expert_coverage"] = found / len(expected)
    else:
        scores["expert_coverage"] = 1.0 if selections else 0.0

    # 2. Minimum expert count met
    if rcase:
        scores["min_experts_met"] = (
            1.0 if len(selections) >= rcase.expected_min_experts else 0.0
        )
    else:
        scores["min_experts_met"] = 1.0 if selections else 0.0

    # 3. Consultation pattern specified for each selection
    if selections:
        has_pattern = sum(
            1 for s in selections
            if (s.get("pattern", "") if isinstance(s, dict)
                else getattr(s, "pattern", "")) in ("parallel", "staged")
        )
        scores["pattern_specified"] = has_pattern / len(selections)
    else:
        scores["pattern_specified"] = 0.0

    # 4. Escalation flags appropriate (high-risk should have flags)
    escalation = data.get("escalation_flags", [])
    has_security_risk = case.risk_flags.get("risk_security", False)
    if has_security_risk:
        scores["escalation_appropriate"] = 1.0 if escalation else 0.5
    else:
        scores["escalation_appropriate"] = 1.0

    # 5. Has adjustments or rationale
    adjustments = data.get("adjustments", "")
    staged = data.get("staged_rationale", "")
    scores["has_adjustments"] = 1.0 if (adjustments or staged) else 0.5

    return scores


async def run_router_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the router agent evaluation."""
    dataset = cases if cases is not None else load_routing_dataset()
    # Filter to accepted cases only
    accepted = [
        c for c in dataset
        if not isinstance(c, RoutingEvalCase) or c.expected_accepted
    ]
    logger.info("Starting router eval: %d cases", len(accepted))

    return await run_eval(
        agent_config=ROUTER_AGENT_CONFIG,
        cases=accepted,
        context_builder=router_context_builder,
        score_fn=score_router_output,
    )
