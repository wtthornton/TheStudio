"""Recruiter Agent configuration for the Unified Agent Framework (Epic 23, AC 23-24).

Defines RecruiterAgentConfig and RecruiterAgentOutput for LLM-powered expert
pack construction. Falls back to template-based recruitment when LLM is unavailable.

Architecture reference: thestudioarc/04-expert-recruiter.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (balanced for recruiter)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class RecruiterAgentOutput(BaseModel):
    """Structured output from the LLM-powered recruiter agent.

    The LLM constructs richer expert packs with nuanced scope boundaries,
    operating procedures, and edge case documentation.
    """

    expert_name: str = Field(description="Generated name for the new expert")
    scope_description: str = Field(
        description="What this expert covers and its boundaries",
    )
    definition: dict[str, str] = Field(
        default_factory=dict,
        description="Expert definition: operating_procedure, expected_outputs, edge_cases",
    )
    tool_policy: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Tool access policy: allowed/denied tool categories",
    )
    trust_tier_recommendation: str = Field(
        default="shadow",
        description="Recommended trust tier: shadow or probation (never trusted for new)",
    )
    creation_rationale: str = Field(
        default="",
        description="Why this expert was created and what gap it fills",
    )


RECRUITER_SYSTEM_PROMPT = """\
You are the Expert Recruiter Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to construct a new expert pack when the Router reports a capability gap.
The expert you create will be registered in the Expert Library and used in future tasks.

## What You Receive
- The expert class needed (e.g., security, compliance, technical)
- Capability tags describing the gap
- The reason the Router requested recruitment

## Your Tasks
1. **Name the expert**: Generate a descriptive name (e.g., "security-auth-crypto")
2. **Define scope**: Clearly describe what this expert covers and its boundaries.
   Be specific about what's IN scope and OUT of scope.
3. **Operating procedure**: Write step-by-step instructions the expert should follow
   when consulted. Include: what to look for, what to recommend, what to flag.
4. **Expected outputs**: Describe the structure of the expert's recommendations,
   risks, validations, and assumptions.
5. **Edge cases**: Document tricky scenarios the expert should handle.
6. **Tool policy**: Define which tool categories the expert may use.
7. **Trust tier**: Always recommend 'shadow' or 'probation' — never 'trusted' for new experts.
   Compliance experts always start as 'shadow'.

## Input Context
Expert Class: {expert_class}
Capability Tags: {capability_tags}
Recruitment Reason: {recruitment_reason}

## Output
Respond with a JSON object matching this schema:
{{
  "expert_name": "string",
  "scope_description": "string",
  "definition": {{"operating_procedure": "string", "expected_outputs": "string", "edge_cases": "string"}},
  "tool_policy": {{"allowed": ["string"], "denied": ["string"]}},
  "trust_tier_recommendation": "shadow|probation",
  "creation_rationale": "string"
}}
"""


def _recruiter_fallback(context: AgentContext) -> str:
    """Rule-based fallback returning a template-based expert skeleton.

    Returns a JSON string matching RecruiterAgentOutput schema.
    """
    import json

    expert_class = context.extra.get("expert_class", "technical")
    capability_tags = context.extra.get("capability_tags", [])
    tag_suffix = "-".join(sorted(capability_tags)[:2]) if capability_tags else "general"

    return json.dumps({
        "expert_name": f"{expert_class}-{tag_suffix}",
        "scope_description": f"Auto-generated {expert_class} expert for {tag_suffix}",
        "definition": {
            "operating_procedure": "Review relevant code and provide recommendations",
            "expected_outputs": "Recommendations, risks, validations",
            "edge_cases": "None documented",
        },
        "tool_policy": {"allowed": ["read", "search"], "denied": ["write", "execute"]},
        "trust_tier_recommendation": "shadow",
        "creation_rationale": f"Template-based creation for {expert_class} gap",
    })


RECRUITER_AGENT_CONFIG = AgentConfig(
    agent_name="recruiter_agent",
    pipeline_step="routing",
    model_class="balanced",
    system_prompt_template=RECRUITER_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.30,
    output_schema=RecruiterAgentOutput,
    fallback_fn=_recruiter_fallback,
    block_on_threat=False,
)
