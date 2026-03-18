"""Preflight Agent configuration for the Unified Agent Framework (Epic 28).

Defines PREFLIGHT_AGENT_CONFIG and PreflightOutput for lightweight plan review.
Three checks: criteria coverage, constraint compliance, step specificity.
Falls back to approving all plans when LLM is unavailable.

Architecture reference: docs/epics/epic-28-preflight-plan-review-gate.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (fast for preflight)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class PreflightOutput(BaseModel):
    """Structured output from the preflight plan review agent.

    Three checks evaluated per AC 2:
    - Criteria coverage: every acceptance criterion has a plan step
    - Constraint compliance: no plan steps contradict constraints
    - Step specificity: no vague steps that require guessing
    """

    approved: bool = Field(
        description="Whether the plan passes preflight review",
    )
    uncovered_criteria: list[str] = Field(
        default_factory=list,
        description="Acceptance criteria with no corresponding plan step",
    )
    constraint_violations: list[str] = Field(
        default_factory=list,
        description="Plan steps that contradict intent constraints",
    )
    vague_steps: list[str] = Field(
        default_factory=list,
        description="Plan steps too vague to implement without guessing",
    )
    summary: str = Field(
        default="",
        description="One-sentence summary of the review result",
    )


PREFLIGHT_SYSTEM_PROMPT = """\
You are the Preflight Agent for TheStudio, an AI-augmented software delivery platform.

Your job is a fast, single-pass plan quality review. You check three things and
produce a structured verdict. You are NOT Meridian (the VP who reviews epics and
sprint plans). You are the checklist on the clipboard — fast, automated, inline.

## What You Receive
- Plan steps: ordered implementation steps from the Assembler
- Acceptance criteria: from the Intent Specification
- Constraints: from the Intent Specification

## Your Three Checks

### 1. Criteria Coverage
Does every acceptance criterion have at least one plan step that addresses it?
- List any criterion that has NO corresponding plan step.
- A criterion is "covered" if a plan step clearly relates to fulfilling it.

### 2. Constraint Compliance
Do any plan steps contradict the intent constraints?
- List any plan step that violates a constraint.
- A step "violates" a constraint if implementing it would break the constraint.

### 3. Step Specificity
Are all plan steps specific enough to implement without guessing?
- Flag any step that uses vague language: "figure out", "determine the best",
  "handle appropriately", "implement as needed", or equivalent.
- A good step says WHAT to do. A vague step says "do the right thing."

## Decision
- approved=true if: no uncovered criteria AND no constraint violations AND no vague steps.
- approved=false if: ANY of the above checks finds issues.

## Input Context
Plan Steps: {plan_steps}
Acceptance Criteria: {acceptance_criteria}
Constraints: {constraints}

## Output
Respond with a JSON object matching this schema:
{{
  "approved": true,
  "uncovered_criteria": [],
  "constraint_violations": [],
  "vague_steps": [],
  "summary": "One sentence summary"
}}
"""


def _preflight_fallback(context: AgentContext) -> str:
    """Rule-based fallback: approve the plan when LLM is unavailable.

    Per AC 4: fallback returns approved=True with a skip message.
    Preflight never blocks the pipeline on its own failure.
    """
    import json

    plan_steps = context.extra.get("plan_steps", [])
    acceptance_criteria = context.extra.get("acceptance_criteria", [])

    # Simple rule-based checks when LLM is unavailable
    uncovered: list[str] = []
    vague: list[str] = []

    # Check for completely empty plans
    if not plan_steps:
        return json.dumps({
            "approved": False,
            "uncovered_criteria": acceptance_criteria,
            "constraint_violations": [],
            "vague_steps": [],
            "summary": "Plan has no steps",
        })

    # Check for vague steps (keyword match)
    vague_markers = [
        "figure out",
        "determine the best",
        "handle appropriately",
        "implement as needed",
        "as necessary",
        "tbd",
        "todo",
    ]
    for step in plan_steps:
        step_lower = step.lower()
        if any(marker in step_lower for marker in vague_markers):
            vague.append(step)

    approved = len(uncovered) == 0 and len(vague) == 0
    summary = (
        "Preflight passed (rule-based)"
        if approved
        else (
            f"Preflight flagged {len(uncovered)} uncovered criteria, "
            f"{len(vague)} vague steps (rule-based)"
        )
    )

    return json.dumps({
        "approved": approved,
        "uncovered_criteria": uncovered,
        "constraint_violations": [],
        "vague_steps": vague,
        "summary": summary,
    })


PREFLIGHT_AGENT_CONFIG = AgentConfig(
    agent_name="preflight_agent",
    pipeline_step="preflight",
    model_class="fast",
    system_prompt_template=PREFLIGHT_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.50,
    output_schema=PreflightOutput,
    fallback_fn=_preflight_fallback,
    block_on_threat=False,
)
