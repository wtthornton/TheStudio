"""Assembler Agent configuration for the Unified Agent Framework (Epic 23, AC 25-27).

Defines AssemblerAgentConfig and AssemblerAgentOutput for LLM-powered plan
assembly with semantic conflict detection. Falls back to keyword-based
assemble() when LLM is unavailable.

Architecture reference: thestudioarc/07-assembler.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (balanced for assembler)
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.agent.framework import AgentConfig, AgentContext


class QAHandoffItem(BaseModel):
    """A single QA handoff mapping: acceptance criterion → validation steps."""

    criterion: str = Field(description="Acceptance criterion text")
    validation_steps: list[str] = Field(
        default_factory=list,
        description="Steps to validate this criterion",
    )

    @field_validator("criterion", mode="before")
    @classmethod
    def coerce_criterion(cls, v: object) -> str:
        """Coerce list[str] to str — LLMs sometimes return a list."""
        if isinstance(v, list):
            return "; ".join(str(item) for item in v)
        return str(v)


class AssemblerConflict(BaseModel):
    """A conflict between expert recommendations with resolution."""

    expert_a: str = Field(description="First expert name")
    expert_b: str = Field(description="Second expert name")
    description: str = Field(description="What the conflict is about")
    resolution: str = Field(description="How the conflict was resolved")
    resolved_by: str = Field(
        default="intent",
        description="Resolution method: intent, risk_priority, or unresolved",
    )


class AssemblerPlanStep(BaseModel):
    """A single step in the implementation plan."""

    description: str = Field(description="What this step does")
    source_expert: str = Field(description="Which expert contributed this step")
    is_checkpoint: bool = Field(default=False, description="Whether this is a validation checkpoint")


class AssemblerAgentOutput(BaseModel):
    """Structured output from the LLM-powered assembler agent.

    The LLM performs semantic conflict detection — identifying contradictions
    even when experts use different terminology. Provides richer provenance
    with decision rationale.
    """

    plan_steps: list[AssemblerPlanStep] = Field(
        default_factory=list,
        description="Ordered implementation steps with checkpoints",
    )
    conflicts: list[AssemblerConflict] = Field(
        default_factory=list,
        description="Detected conflicts with resolutions",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Identified risks with mitigations",
    )
    qa_handoff: list[QAHandoffItem] = Field(
        default_factory=list,
        description="Acceptance criteria mapped to validation steps",
    )
    provenance_decisions: list[dict[str, str]] = Field(
        default_factory=list,
        description="Decision rationale: why expert A's recommendation was preferred",
    )


ASSEMBLER_SYSTEM_PROMPT = """\
You are the Assembler Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to merge expert outputs into a single, coherent implementation plan. You are
the last step before the Primary Agent receives its implementation instructions.

## What You Receive
- Expert outputs: recommendations, risks, validations, assumptions from each expert
- Intent constraints: what the implementation MUST satisfy
- Acceptance criteria: what QA will validate against

## Your Tasks
1. **Merge recommendations**: Combine expert recommendations into ordered plan steps.
   Group related steps. Add checkpoints after high-risk steps.
2. **Detect conflicts SEMANTICALLY**: Don't just look for keyword overlap. Identify when
   experts recommend contradictory approaches even with different terminology:
   - "Use in-memory caching" vs "Persist all state to database" = conflict
   - "Add retry logic" vs "Fail fast on first error" = conflict
   Use intent constraints as tie-breaker. If intent doesn't resolve it, mark as unresolved.
3. **Assess risks**: Collect risks from all experts. Add risks the experts may have missed
   based on the combination of their recommendations.
4. **Build QA handoff**: Map each acceptance criterion to specific validation steps.
   QA needs to know exactly what to check and how.
5. **Record provenance**: For each decision where you chose one expert's recommendation
   over another's, record WHY. "Expert recommendation" is not a rationale.

## Input Context
Intent Goal: {intent_goal}
Intent Constraints: {intent_constraints}
Acceptance Criteria: {acceptance_criteria}
Expert Count: {expert_count}

## Output
Respond with a JSON object matching this schema:
{{
  "plan_steps": [{{"description": "string", "source_expert": "string", "is_checkpoint": false}}],
  "conflicts": [{{"expert_a": "string", "expert_b": "string", "description": "string", "resolution": "string", "resolved_by": "intent|risk_priority|unresolved"}}],
  "risks": ["string"],
  "qa_handoff": [{{"criterion": "string", "validation_steps": ["string"]}}],
  "provenance_decisions": [{{"decision": "string", "source": "string", "rationale": "string"}}]
}}
"""


def _assembler_fallback(context: AgentContext) -> str:
    """Rule-based fallback using existing keyword-based assembler.

    Returns a JSON string matching AssemblerAgentOutput schema.
    """
    import json

    from src.assembler.assembler import ExpertOutput, assemble

    expert_outputs_raw = context.expert_outputs or []
    expert_outputs = []
    for eo in expert_outputs_raw:
        if isinstance(eo, ExpertOutput):
            expert_outputs.append(eo)
        elif isinstance(eo, dict):
            from uuid import UUID

            expert_outputs.append(ExpertOutput(
                expert_id=UUID(eo.get("expert_id", "00000000-0000-0000-0000-000000000000")),
                expert_version=eo.get("expert_version", 1),
                expert_name=eo.get("expert_name", "unknown"),
                recommendations=eo.get("recommendations", []),
                risks=eo.get("risks", []),
                validations=eo.get("validations", []),
                assumptions=eo.get("assumptions", []),
            ))

    intent_constraints = context.extra.get("intent_constraints", [])
    acceptance_criteria = context.extra.get("acceptance_criteria", [])
    taskpacket_id = context.taskpacket_id or __import__("uuid").UUID(int=0)
    correlation_id = context.correlation_id or __import__("uuid").UUID(int=0)
    intent_version = context.extra.get("intent_version", 1)

    plan = assemble(
        expert_outputs=expert_outputs,
        intent_constraints=intent_constraints,
        acceptance_criteria=acceptance_criteria,
        taskpacket_id=taskpacket_id,
        correlation_id=correlation_id,
        intent_version=intent_version,
    )

    return json.dumps({
        "plan_steps": [
            {
                "description": s.description,
                "source_expert": s.source_expert,
                "is_checkpoint": s.is_checkpoint,
            }
            for s in plan.steps
        ],
        "conflicts": [
            {
                "expert_a": c.expert_a,
                "expert_b": c.expert_b,
                "description": c.description,
                "resolution": c.resolution,
                "resolved_by": c.resolved_by,
            }
            for c in plan.conflicts
        ],
        "risks": [r.description for r in plan.risks],
        "qa_handoff": [
            {"criterion": h.criterion, "validation_steps": h.validation_steps}
            for h in plan.qa_handoff
        ],
        "provenance_decisions": (
            plan.provenance.decision_provenance if plan.provenance else []
        ),
    })


ASSEMBLER_AGENT_CONFIG = AgentConfig(
    agent_name="assembler_agent",
    pipeline_step="assembler",
    model_class="balanced",
    system_prompt_template=ASSEMBLER_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.50,
    output_schema=AssemblerAgentOutput,
    fallback_fn=_assembler_fallback,
    block_on_threat=False,
)
