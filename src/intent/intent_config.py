"""Intent Builder Agent configuration for the Unified Agent Framework (Epic 23, AC 16-18).

Defines IntentAgentConfig and IntentAgentOutput for LLM-powered intent
extraction. Falls back to build_intent() when LLM is unavailable.

Architecture reference: thestudioarc/11-intent-layer.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (balanced for intent)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class IntentAgentOutput(BaseModel):
    """Structured output from the LLM-powered intent builder agent.

    The LLM extracts semantic intent from issue content, including
    invariants (what must not change) — closing architecture gap V7.
    """

    goal: str = Field(description="Clear goal statement derived from issue title and body")
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints derived from risk flags and issue content",
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="What must NOT change — preserves existing behavior",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Explicit and implicit acceptance criteria",
    )
    non_goals: list[str] = Field(
        default_factory=list,
        description="Explicitly out-of-scope items",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made during intent extraction",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions that need clarification before implementation",
    )


INTENT_SYSTEM_PROMPT = """\
You are the Intent Builder Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to produce an Intent Specification from a GitHub issue. Intent is the definition
of correctness — everything downstream (implementation, verification, QA) validates against it.

## Your Tasks
1. **Goal Statement**: Extract a clear, actionable goal from the issue title and body.
   The goal should describe WHAT needs to happen, not HOW.
2. **Constraints**: Derive constraints from risk flags and issue content:
   - Security risks → credential/secret protection constraints
   - Breaking changes → backward compatibility constraints
   - Cross-team impact → notification/coordination constraints
   - Data risks → migration safety constraints
   - Always include: "Must include tests for new or changed behavior"
3. **Invariants**: Identify what must NOT change. These are existing behaviors, APIs,
   or contracts that the implementation must preserve. Examples:
   - "Existing API endpoints must continue to work"
   - "Current test suite must pass without modification"
   - "Database schema backward compatibility must be maintained"
4. **Acceptance Criteria**: Extract explicit criteria from checkboxes or requirements
   sections. Then synthesize IMPLICIT criteria the issue assumes but doesn't state.
   For example, "add pagination" implies: default page size, total count returned,
   existing filters still work, empty result handling.
5. **Non-Goals**: Extract from "out of scope" or "won't do" sections. If none exist,
   infer reasonable non-goals to prevent scope creep.
6. **Assumptions**: State what you're assuming about the codebase, environment, or
   requirements that could be wrong.
7. **Open Questions**: Flag ambiguities that could affect implementation correctness.

## Input Context
Repository: {repo}
Risk Flags: {risk_flags}
Complexity: {complexity}

## Output
Respond with a JSON object matching this schema:
{{
  "goal": "string",
  "constraints": ["string"],
  "invariants": ["string"],
  "acceptance_criteria": ["string"],
  "non_goals": ["string"],
  "assumptions": ["string"],
  "open_questions": ["string"]
}}
"""


def _intent_fallback(context: AgentContext) -> str:
    """Rule-based fallback using existing intent extraction functions.

    Returns a JSON string matching IntentAgentOutput schema.
    """
    import json

    from src.intent.intent_builder import (
        derive_constraints,
        extract_acceptance_criteria,
        extract_goal,
        extract_non_goals,
    )

    goal = extract_goal(context.issue_title, context.issue_body)
    constraints = derive_constraints(
        {k: bool(v) for k, v in context.risk_flags.items()} if context.risk_flags else None
    )
    criteria = extract_acceptance_criteria(context.issue_body)
    non_goals = extract_non_goals(context.issue_body)

    if not criteria:
        criteria = [f"Implementation satisfies: {context.issue_title}"]

    return json.dumps({
        "goal": goal,
        "constraints": constraints,
        "invariants": [],
        "acceptance_criteria": criteria,
        "non_goals": non_goals,
        "assumptions": [],
        "open_questions": [],
    })


INTENT_AGENT_CONFIG = AgentConfig(
    agent_name="intent_agent",
    pipeline_step="intent",
    model_class="balanced",
    system_prompt_template=INTENT_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.50,
    output_schema=IntentAgentOutput,
    fallback_fn=_intent_fallback,
    block_on_threat=False,
)
