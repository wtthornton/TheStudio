"""Assembler Agent evaluation runner.

Epic 32, Story 32.2: Validates the assembler agent's plan construction,
conflict detection, risk assessment, QA handoff, and provenance tracking.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.agent.framework import AgentContext
from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary
from src.eval.routing_dataset import RoutingEvalCase, load_routing_dataset

logger = logging.getLogger(__name__)


def assembler_context_builder(case: EvalCase) -> AgentContext:
    """Build AgentContext for assembler evaluation.

    Simulates the assembler receiving expert outputs by populating
    expert_outputs with synthetic expert recommendations.
    """
    rcase = case if isinstance(case, RoutingEvalCase) else None

    # Build synthetic expert outputs based on the issue
    expert_outputs = [
        {
            "expert_id": str(uuid4()),
            "expert_version": 1,
            "expert_name": "technical_expert",
            "recommendations": [
                f"Implement changes described in: {case.issue_title}",
                "Add unit tests for all new functionality",
                "Update documentation if public API changes",
            ],
            "risks": ["Regression risk if existing tests are not run"],
            "validations": ["All existing tests pass", "New tests cover edge cases"],
            "assumptions": ["Repository uses standard project structure"],
        },
    ]

    # Add security expert for security-related issues
    if case.risk_flags.get("risk_security"):
        expert_outputs.append({
            "expert_id": str(uuid4()),
            "expert_version": 1,
            "expert_name": "security_expert",
            "recommendations": [
                "Apply input validation and sanitization",
                "Review for OWASP Top 10 vulnerabilities",
            ],
            "risks": ["Security bypass if validation is incomplete"],
            "validations": ["Security scan passes", "No new bandit findings"],
            "assumptions": [],
        })

    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
        overlays=rcase.expected_overlays if rcase else [],
        expert_outputs=expert_outputs,
        extra={
            "intent_goal": case.issue_title,
            "intent_constraints": ["Must not break existing tests"],
            "acceptance_criteria": [
                f"Fix described in: {case.issue_title}",
                "All existing tests pass",
            ],
            "expert_count": len(expert_outputs),
            "intent_version": 1,
        },
    )


def score_assembler_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score assembler agent output against expected plan quality."""
    if parsed is None:
        return {
            "plan_completeness": 0.0,
            "has_checkpoints": 0.0,
            "risk_assessment": 0.0,
            "qa_handoff": 0.0,
            "provenance_tracked": 0.0,
        }

    if hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = vars(parsed) if hasattr(parsed, "__dict__") else {}

    rcase = case if isinstance(case, RoutingEvalCase) else None
    scores: dict[str, float] = {}

    steps = data.get("plan_steps", [])

    # 1. Plan has enough steps
    if rcase:
        min_steps = rcase.expected_min_plan_steps
        scores["plan_completeness"] = (
            1.0 if len(steps) >= min_steps
            else len(steps) / max(min_steps, 1)
        )
    else:
        scores["plan_completeness"] = 1.0 if steps else 0.0

    # 2. Has checkpoints (for high-complexity issues)
    if case.complexity == "high" and steps:
        has_cp = any(
            (s.get("is_checkpoint") if isinstance(s, dict)
             else getattr(s, "is_checkpoint", False))
            for s in steps
        )
        scores["has_checkpoints"] = 1.0 if has_cp else 0.3
    else:
        scores["has_checkpoints"] = 1.0

    # 3. Risk assessment
    risks = data.get("risks", [])
    scores["risk_assessment"] = 1.0 if risks else 0.3

    # 4. QA handoff present
    qa = data.get("qa_handoff", [])
    if rcase and rcase.expected_has_qa_handoff:
        scores["qa_handoff"] = 1.0 if qa else 0.0
    else:
        scores["qa_handoff"] = 1.0

    # 5. Provenance decisions tracked
    provenance = data.get("provenance_decisions", [])
    # Only expected when multiple experts contribute
    if case.risk_flags.get("risk_security"):
        scores["provenance_tracked"] = 1.0 if provenance else 0.5
    else:
        scores["provenance_tracked"] = 1.0

    return scores


async def run_assembler_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the assembler agent evaluation."""
    dataset = cases if cases is not None else load_routing_dataset()
    # Filter to accepted, non-trivial cases
    accepted = [
        c for c in dataset
        if not isinstance(c, RoutingEvalCase) or c.expected_accepted
    ]
    logger.info("Starting assembler eval: %d cases", len(accepted))

    return await run_eval(
        agent_config=ASSEMBLER_AGENT_CONFIG,
        cases=accepted,
        context_builder=assembler_context_builder,
        score_fn=score_assembler_output,
    )
