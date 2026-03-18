"""Intent Agent evaluation runner.

Epic 30, Story 30.2: Runs the intent agent against all 10 labeled test
cases using the real Anthropic LLM provider. Scores each output across
5 quality dimensions (goal clarity, constraint coverage, AC completeness,
invariant presence, non-goal specificity) and returns an EvalSummary.
"""

from __future__ import annotations

import logging

from src.eval.dataset import load_intent_dataset
from src.eval.harness import run_eval, score_intent_output
from src.eval.models import EvalCase, EvalSummary
from src.intent.intent_config import INTENT_AGENT_CONFIG

logger = logging.getLogger(__name__)


async def run_intent_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the intent agent evaluation against labeled test cases.

    Args:
        cases: Optional subset of cases. Defaults to the full 10-case
            intent dataset from ``load_intent_dataset()``.

    Returns:
        EvalSummary with per-case results and aggregated metrics.
    """
    dataset = cases if cases is not None else load_intent_dataset()
    logger.info(
        "Starting intent agent eval: %d cases, config=%s",
        len(dataset),
        INTENT_AGENT_CONFIG.agent_name,
    )

    summary = await run_eval(
        agent_config=INTENT_AGENT_CONFIG,
        cases=dataset,
        score_fn=score_intent_output,
    )

    logger.info(
        "Intent eval complete: pass_rate=%.0f%% (%d/%d), "
        "parse_success=%.0f%%, cost=$%.4f, duration=%dms",
        summary.pass_rate * 100,
        summary.passed_count,
        summary.total_cases,
        summary.parse_success_rate * 100,
        summary.total_cost_usd,
        summary.total_duration_ms,
    )

    return summary
