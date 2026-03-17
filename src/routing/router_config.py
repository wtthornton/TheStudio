"""Router Agent configuration for the Unified Agent Framework (Epic 23, AC 19-22).

Defines RouterAgentConfig and RouterAgentOutput for LLM-augmented expert routing.
The LLM reviews and adjusts the algorithmic route() output — it does not replace
the scoring formula. Falls back to route() when LLM is unavailable.

Architecture reference: thestudioarc/05-expert-router.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (balanced for routing)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class RouterExpertSelection(BaseModel):
    """A single expert selection with LLM-augmented reasoning."""

    expert_class: str = Field(description="Expert class: security, technical, qa_validation, etc.")
    pattern: str = Field(
        default="parallel",
        description="Consultation pattern: 'parallel' or 'staged'",
    )
    rationale: str = Field(
        default="",
        description="Why this expert class is needed",
    )


class RouterAgentOutput(BaseModel):
    """Structured output from the LLM-augmented router agent.

    The LLM reviews algorithmic routing decisions and can:
    - Recommend staged vs parallel consultation (closing gap V9)
    - Recommend shadow experts for probationary ones (closing gap V8)
    - Flag escalation conditions
    """

    selections: list[RouterExpertSelection] = Field(
        default_factory=list,
        description="Expert selections with consultation pattern",
    )
    shadow_recommendations: list[str] = Field(
        default_factory=list,
        description="Expert classes that should run in shadow mode alongside trusted experts",
    )
    staged_rationale: str = Field(
        default="",
        description="If staged consultation is recommended, explain the dependency chain",
    )
    escalation_flags: list[str] = Field(
        default_factory=list,
        description="Conditions that warrant human escalation",
    )
    adjustments: str = Field(
        default="",
        description="Any adjustments made to the algorithmic routing output",
    )


ROUTER_SYSTEM_PROMPT = """\
You are the Expert Router Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to review and augment expert routing decisions. The algorithmic router has already
selected experts based on reputation scores and mandatory coverage rules. You add judgment.

## What You Review
- The required expert classes based on role policy and risk flags
- The available candidates and their reputation data
- The risk context from the TaskPacket

## Your Tasks
1. **Review selections**: Confirm or adjust the algorithmic routing. If the algorithm
   missed a pattern or selected sub-optimally, explain why.
2. **Parallel vs Staged**: Determine if expert outputs have dependencies. For example:
   - Security review SHOULD complete before partner API review (staged)
   - Technical and QA validation can run simultaneously (parallel)
   If staged is recommended, explain the dependency chain.
3. **Shadow recommendations**: For new/probationary experts, recommend running them in
   shadow mode alongside a trusted expert. This lets us compare outputs without risk.
4. **Escalation flags**: Flag conditions that warrant human review:
   - Budget exhausted before all mandatory classes covered
   - Only low-confidence experts available for high-risk tasks
   - Risk flags indicate privileged access or destructive operations

## Input Context
Base Role: {base_role}
Overlays: {overlays}
Risk Flags: {risk_flags}
Required Expert Classes: {required_classes}

## Output
Respond with a JSON object matching this schema:
{{
  "selections": [{{"expert_class": "string", "pattern": "parallel|staged", "rationale": "string"}}],
  "shadow_recommendations": ["string"],
  "staged_rationale": "string",
  "escalation_flags": ["string"],
  "adjustments": "string"
}}
"""


def _router_fallback(context: AgentContext) -> str:
    """Rule-based fallback using existing algorithmic router.

    Returns a JSON string matching RouterAgentOutput schema.
    """
    import json

    from src.intake.effective_role import BaseRole, EffectiveRolePolicy, Overlay
    from src.routing.router import route

    base_role = context.extra.get("base_role", "developer")
    overlay_strs = context.overlays or []
    overlays = []
    for o in overlay_strs:
        try:
            overlays.append(Overlay(o))
        except ValueError:
            pass

    policy = EffectiveRolePolicy.compute(BaseRole(base_role), overlays)
    risk_flags = {k: bool(v) for k, v in context.risk_flags.items()} if context.risk_flags else None
    plan = route(policy, risk_flags, [])

    return json.dumps({
        "selections": [
            {
                "expert_class": s.expert_class.value,
                "pattern": s.pattern,
                "rationale": "Algorithmic selection",
            }
            for s in plan.selections
        ],
        "shadow_recommendations": [],
        "staged_rationale": "",
        "escalation_flags": [],
        "adjustments": "",
    })


ROUTER_AGENT_CONFIG = AgentConfig(
    agent_name="router_agent",
    pipeline_step="routing",
    model_class="balanced",
    system_prompt_template=ROUTER_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.30,
    output_schema=RouterAgentOutput,
    fallback_fn=_router_fallback,
    block_on_threat=False,
)
