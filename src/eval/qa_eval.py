"""QA Agent evaluation runner.

Epic 30, Story 30.3: Runs the QA agent against synthetic evidence bundles
with planted defects (and clean bundles) to validate defect detection,
classification, and false positive rate.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent.framework import AgentContext
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary
from src.eval.qa_dataset import QAEvalCase, load_qa_dataset
from src.qa.qa_config import QA_AGENT_CONFIG, QAAgentOutput

logger = logging.getLogger(__name__)


def qa_context_builder(case: EvalCase) -> AgentContext:
    """Build an AgentContext from a QAEvalCase for the QA agent.

    Populates context.extra with acceptance_criteria and evidence_keys
    that the QA system prompt template expects.
    """
    if not isinstance(case, QAEvalCase):
        raise TypeError(f"Expected QAEvalCase, got {type(case)}")

    evidence = {
        "agent_summary": case.agent_summary,
        "test_results": case.test_results,
        "lint_results": case.lint_results,
        "file_changes": case.file_changes,
    }
    evidence_keys = ", ".join(evidence.keys())
    criteria_str = "\n".join(f"- {ac}" for ac in case.acceptance_criteria)

    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.description,
        issue_body=case.description,
        evidence=evidence,
        extra={
            "acceptance_criteria": criteria_str,
            "evidence_keys": evidence_keys,
        },
    )


def score_qa_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score QA agent output against expected defect characteristics.

    Scores:
    - defect_detection: fraction of expected defects found
    - defect_classification: category match rate
    - false_positive_rate: penalizes S0/S1 defects on clean bundles
    - criteria_coverage: fraction of acceptance criteria evaluated
    - reasoning_quality: whether criteria results have non-empty reasoning
    """
    if not isinstance(case, QAEvalCase):
        return {"defect_detection": 0.0, "defect_classification": 0.0,
                "false_positive_rate": 1.0, "criteria_coverage": 0.0,
                "reasoning_quality": 0.0}

    if parsed is None:
        return {"defect_detection": 0.0, "defect_classification": 0.0,
                "false_positive_rate": 0.0 if case.is_clean else 1.0,
                "criteria_coverage": 0.0, "reasoning_quality": 0.0}

    if isinstance(parsed, QAAgentOutput):
        output = parsed
    else:
        return {"defect_detection": 0.0, "defect_classification": 0.0,
                "false_positive_rate": 0.0, "criteria_coverage": 0.0,
                "reasoning_quality": 0.0}

    # 1. Defect detection (for planted defect cases)
    if case.expects_defects and case.expected_defect_count > 0:
        found = len(output.defects) + len(output.intent_gaps)
        detection = min(found / case.expected_defect_count, 1.0)
    elif case.is_clean:
        # Clean: full score if no defects found
        detection = 1.0 if len(output.defects) == 0 else 0.0
    else:
        detection = 1.0

    # 2. Defect classification (category match)
    if case.expected_defect_categories:
        found_categories = {d.category for d in output.defects}
        # intent_gaps also count as intent_gap category
        if output.intent_gaps:
            found_categories.add("intent_gap")
        matches = sum(
            1 for cat in case.expected_defect_categories
            if cat in found_categories
        )
        classification = matches / len(case.expected_defect_categories)
    else:
        classification = 1.0

    # 3. False positive rate (penalize S0/S1 on clean bundles)
    if case.is_clean:
        severe = [
            d for d in output.defects
            if d.severity in ("S0_critical", "S1_high")
        ]
        false_positive = 1.0 if not severe else 0.0
    else:
        false_positive = 1.0  # not applicable for defect cases

    # 4. Criteria coverage
    if case.acceptance_criteria:
        evaluated = len(output.criteria_results)
        criteria_coverage = min(evaluated / len(case.acceptance_criteria), 1.0)
    else:
        criteria_coverage = 1.0

    # 5. Reasoning quality
    if output.criteria_results:
        with_reasoning = sum(
            1 for cr in output.criteria_results if cr.reasoning.strip()
        )
        reasoning_quality = with_reasoning / len(output.criteria_results)
    else:
        reasoning_quality = 0.0

    return {
        "defect_detection": detection,
        "defect_classification": classification,
        "false_positive_rate": false_positive,
        "criteria_coverage": criteria_coverage,
        "reasoning_quality": reasoning_quality,
    }


async def run_qa_eval(
    cases: list[QAEvalCase] | None = None,
) -> EvalSummary:
    """Run the QA agent evaluation against synthetic evidence bundles.

    Args:
        cases: Optional subset of cases. Defaults to the full 10-case
            QA dataset.

    Returns:
        EvalSummary with per-case results and aggregated metrics.
    """
    dataset = cases if cases is not None else load_qa_dataset()
    logger.info(
        "Starting QA agent eval: %d cases (planted=%d, clean=%d)",
        len(dataset),
        sum(1 for c in dataset if c.expects_defects),
        sum(1 for c in dataset if c.is_clean),
    )

    summary = await run_eval(
        agent_config=QA_AGENT_CONFIG,
        cases=dataset,  # type: ignore[arg-type]
        context_builder=qa_context_builder,  # type: ignore[arg-type]
        score_fn=score_qa_output,  # type: ignore[arg-type]
    )

    logger.info(
        "QA eval complete: pass_rate=%.0f%% (%d/%d), "
        "parse_success=%.0f%%, cost=$%.4f",
        summary.pass_rate * 100,
        summary.passed_count,
        summary.total_cases,
        summary.parse_success_rate * 100,
        summary.total_cost_usd,
    )

    return summary
