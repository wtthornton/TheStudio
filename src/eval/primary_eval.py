"""Primary Agent evaluation runner.

Epic 30, Story 30.4: Runs the primary (developer) agent against 3 simple
labeled issues using real Claude. Validates that the agent produces
coherent summaries and file change suggestions within budget.

Note: Runs in completion mode (no tool use) to avoid claude_agent_sdk
dependency. Validates output quality, not code execution.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent.framework import AgentConfig, AgentContext
from src.eval.dataset import load_intent_dataset
from src.eval.harness import run_eval
from src.eval.models import EvalCase, EvalSummary

logger = logging.getLogger(__name__)


def _primary_fallback(context: AgentContext) -> str:
    """Rule-based fallback for the primary agent."""
    import json
    return json.dumps({
        "agent_summary": f"Fallback: Would implement changes for: {context.issue_title}",
        "file_changes": [],
        "approach": "Rule-based fallback — no LLM available",
        "risks": ["No LLM analysis performed"],
        "estimated_complexity": "unknown",
    })


# Use completion mode (empty tool_allowlist) to avoid claude_agent_sdk dep.
# This tests output quality; agentic execution is validated in Sprint 2.
PRIMARY_EVAL_CONFIG = AgentConfig(
    agent_name="developer",
    pipeline_step="primary_agent",
    model_class="balanced",
    system_prompt_template="""\
You are the Developer agent for TheStudio. Your task is to analyze a GitHub
issue and produce a structured implementation plan.

Respond with a JSON object:
{{
  "agent_summary": "A clear summary of what changes you would make",
  "file_changes": ["list of file paths that would be modified"],
  "approach": "Brief description of the implementation approach",
  "risks": ["potential risks or concerns"],
  "estimated_complexity": "low|medium|high"
}}
""",
    tool_allowlist=[],  # completion mode — no tools
    max_turns=1,
    max_budget_usd=5.00,
    output_schema=None,  # We parse manually since output format is flexible
    fallback_fn=_primary_fallback,
)


def primary_context_builder(case: EvalCase) -> AgentContext:
    """Build an AgentContext for the primary agent from an EvalCase."""
    system_prompt = PRIMARY_EVAL_CONFIG.system_prompt_template
    user_prompt = (
        f"## Issue\n\n"
        f"**{case.issue_title}**\n\n"
        f"{case.issue_body}\n\n"
        f"Analyze this issue and produce your implementation plan as JSON."
    )
    return AgentContext(
        repo="eval/test-repo",
        issue_title=case.issue_title,
        issue_body=case.issue_body,
        labels=case.labels,
        risk_flags=dict(case.risk_flags),
        complexity=case.complexity,
        extra={
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )


def score_primary_output(parsed: Any, case: EvalCase) -> dict[str, float]:
    """Score primary agent output for basic quality checks.

    Since the primary agent uses flexible output format, we score
    the raw output string for coherence rather than parsed structure.
    """
    # We receive parsed=None since output_schema is None.
    # Score will be applied on the raw_output in the EvalResult instead.
    # Return default scores that the harness uses.
    return {
        "goal_clarity": 0.5,
        "constraint_coverage": 0.5,
        "ac_completeness": 0.5,
        "invariant_presence": 0.5,
        "non_goal_specificity": 0.5,
    }


def score_primary_raw(raw_output: str, case: EvalCase) -> dict[str, float]:
    """Score raw output from primary agent for quality signals."""
    import json

    if not raw_output or not raw_output.strip():
        return {
            "has_summary": 0.0,
            "has_file_changes": 0.0,
            "coherence": 0.0,
            "relevance": 0.0,
        }

    # Try to parse as JSON
    try:
        # Extract JSON from potential wrapper text
        stripped = raw_output.strip()
        if not stripped.startswith("{"):
            first_brace = stripped.find("{")
            last_brace = stripped.rfind("}")
            if first_brace != -1 and last_brace > first_brace:
                stripped = stripped[first_brace:last_brace + 1]
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        data = {}

    # Score dimensions
    summary = data.get("agent_summary", "")
    files = data.get("file_changes", [])
    approach = data.get("approach", "")

    has_summary = 1.0 if summary and len(summary) > 20 else 0.0
    has_files = 1.0 if files and len(files) > 0 else 0.0

    # Coherence: summary mentions something from the issue
    title_words = set(case.issue_title.lower().split())
    summary_words = set(summary.lower().split()) if summary else set()
    overlap = title_words & summary_words - {"the", "a", "an", "to", "and", "or", "is", "in", "for"}
    coherence = min(len(overlap) / max(len(title_words) / 2, 1), 1.0)

    # Relevance: approach or summary references the domain
    relevance = 1.0 if approach and len(approach) > 10 else 0.5

    return {
        "has_summary": has_summary,
        "has_file_changes": has_files,
        "coherence": coherence,
        "relevance": relevance,
    }


# Select the 3 simplest cases for primary eval (to control cost)
_SIMPLE_CASE_IDS = {"bug_fix_01", "docs_05", "dep_update_09"}


async def run_primary_eval(
    cases: list[EvalCase] | None = None,
) -> EvalSummary:
    """Run the primary agent evaluation against 3 simple labeled issues.

    Args:
        cases: Optional override. Defaults to 3 simplest cases from
            the intent dataset.

    Returns:
        EvalSummary with per-case results.
    """
    if cases is None:
        all_cases = load_intent_dataset()
        dataset = [c for c in all_cases if c.case_id in _SIMPLE_CASE_IDS]
    else:
        dataset = cases

    logger.info("Starting primary agent eval: %d cases", len(dataset))

    summary = await run_eval(
        agent_config=PRIMARY_EVAL_CONFIG,
        cases=dataset,
        context_builder=primary_context_builder,
        score_fn=score_primary_output,
    )

    # Enhance with raw-output scoring
    for result in summary.results:
        matching = [c for c in dataset if c.case_id == result.case_id]
        if matching and result.raw_output:
            raw_scores = score_primary_raw(result.raw_output, matching[0])
            # Override pass/fail based on raw scores
            has_content = (
                raw_scores["has_summary"] > 0
                and raw_scores["coherence"] > 0.2
            )
            result.passed = has_content

    # Recompute summary stats
    from src.eval.scoring import aggregate_scores
    summary = aggregate_scores(summary.results, agent_name="developer")

    logger.info(
        "Primary eval complete: pass_rate=%.0f%% (%d/%d), cost=$%.4f",
        summary.pass_rate * 100,
        summary.passed_count,
        summary.total_cases,
        summary.total_cost_usd,
    )

    return summary
