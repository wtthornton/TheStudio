"""Intake Agent evaluation runner.

Epic 32, Story 32.2: Validates the intake agent's eligibility classification,
role selection, overlay detection, and risk flagging against labeled test cases.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent.framework import AgentContext
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary
from src.eval.routing_dataset import RoutingEvalCase, load_routing_dataset
from src.intake.intake_config import INTAKE_AGENT_CONFIG

logger = logging.getLogger(__name__)


def intake_context_builder(case: EvalCase) -> AgentContext:
    """Build AgentContext for intake evaluation."""
    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
        extra={
            "repo_registered": True,
            "repo_paused": False,
            "has_active_workflow": False,
            "event_id": f"eval-{case.case_id}",
        },
    )


def score_intake_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score intake agent output against expected classification."""
    if parsed is None:
        return {
            "accepted_correct": 0.0,
            "role_correct": 0.0,
            "overlay_coverage": 0.0,
            "risk_detection": 0.0,
            "has_reasoning": 0.0,
        }

    if hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
    elif isinstance(parsed, dict):
        data = parsed
    else:
        data = vars(parsed) if hasattr(parsed, "__dict__") else {}

    rcase = case if isinstance(case, RoutingEvalCase) else None
    scores: dict[str, float] = {}

    # 1. Accepted/rejected classification
    accepted = data.get("accepted", False)
    expected = rcase.expected_accepted if rcase else True
    scores["accepted_correct"] = 1.0 if accepted == expected else 0.0

    # 2. Base role selection (only scored if accepted)
    if expected and rcase:
        role = data.get("base_role", "").lower()
        scores["role_correct"] = 1.0 if role == rcase.expected_base_role else 0.0
    else:
        scores["role_correct"] = 1.0  # N/A for rejected issues

    # 3. Overlay detection
    if rcase and rcase.expected_overlays:
        detected = set(data.get("overlays", []))
        expected_overlays = set(rcase.expected_overlays)
        if expected_overlays:
            scores["overlay_coverage"] = len(
                detected & expected_overlays
            ) / len(expected_overlays)
        else:
            scores["overlay_coverage"] = 1.0 if not detected else 0.5
    else:
        scores["overlay_coverage"] = 1.0

    # 4. Risk flag detection
    if rcase and rcase.expected_risk_keys:
        detected_risks = data.get("risk_flags", {})
        expected_keys = set(rcase.expected_risk_keys)
        found = sum(1 for k in expected_keys if detected_risks.get(k))
        scores["risk_detection"] = found / len(expected_keys)
    else:
        scores["risk_detection"] = 1.0

    # 5. Has reasoning
    reasoning = data.get("reasoning", "")
    scores["has_reasoning"] = 1.0 if len(reasoning) > 10 else 0.0

    return scores


async def run_intake_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the intake agent evaluation."""
    dataset = cases if cases is not None else load_routing_dataset()
    logger.info("Starting intake eval: %d cases", len(dataset))

    return await run_eval(
        agent_config=INTAKE_AGENT_CONFIG,
        cases=dataset,
        context_builder=intake_context_builder,
        score_fn=score_intake_output,
        pass_threshold=0.5,
    )
