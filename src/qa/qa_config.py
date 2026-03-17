"""QA Agent configuration for the Unified Agent Framework (Epic 23, AC 28-30).

Defines QAAgentConfig and QAAgentOutput for LLM-powered intent validation.
The LLM reasons about intent satisfaction rather than keyword-matching evidence.
Falls back to keyword-based validate() when LLM is unavailable.

Architecture reference: thestudioarc/14-qa-quality-layer.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (balanced for QA)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class QACriterionResult(BaseModel):
    """Result of validating a single acceptance criterion."""

    criterion: str = Field(description="The acceptance criterion being validated")
    passed: bool = Field(description="Whether the criterion is satisfied")
    reasoning: str = Field(
        default="",
        description="Why the criterion passed or failed — must reference specific evidence",
    )


class QADefectItem(BaseModel):
    """A defect found during QA validation."""

    category: str = Field(
        description="Defect category: intent_gap, implementation_bug, regression, "
        "security, performance, compliance, partner_mismatch, operability",
    )
    severity: str = Field(
        description="Severity: S0_critical, S1_high, S2_medium, S3_low",
    )
    description: str = Field(description="What the defect is")
    acceptance_criterion: str = Field(
        default="",
        description="Which acceptance criterion this defect relates to",
    )


class QAAgentOutput(BaseModel):
    """Structured output from the LLM-powered QA agent.

    The LLM reasons about intent satisfaction — it reads the agent summary,
    file changes, test results, and lint results to determine if acceptance
    criteria are actually met, not just keyword-matched.
    """

    criteria_results: list[QACriterionResult] = Field(
        default_factory=list,
        description="Per-criterion pass/fail with reasoning",
    )
    defects: list[QADefectItem] = Field(
        default_factory=list,
        description="Defects found, classified by category and severity",
    )
    intent_gaps: list[str] = Field(
        default_factory=list,
        description="Acceptance criteria that are ambiguous or untestable",
    )
    edge_case_concerns: list[str] = Field(
        default_factory=list,
        description="Edge cases not covered by explicit criteria but implied by intent",
    )


QA_SYSTEM_PROMPT = """\
You are the QA Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to validate that the implementation satisfies the Intent Specification.
You are the last gate before publication. Intent gaps BLOCK qa_passed.

## What You Receive
- Acceptance criteria from the Intent Specification
- Evidence bundle: test results, lint output, file changes, agent summary
- QA handoff mappings from the Assembler

## Your Tasks
1. **Validate each criterion**: For every acceptance criterion, determine if the
   implementation actually satisfies it. Don't just keyword-match — REASON about it.
   - "Pagination works correctly" requires more than finding the word "pagination"
   - Check that test results actually cover the criterion
   - Check that the implementation approach addresses the criterion
2. **Classify defects**: Use the 8-category taxonomy:
   - intent_gap: Criterion is ambiguous or untestable — BLOCKS qa_passed
   - implementation_bug: Code doesn't do what the criterion requires
   - regression: Previously working behavior is broken
   - security: Security vulnerability introduced
   - performance: Performance degradation
   - compliance: Compliance requirement violated
   - partner_mismatch: External API contract violated
   - operability: Missing logging, metrics, or error handling
3. **Rate severity**: S0 (critical), S1 (high), S2 (medium), S3 (low)
4. **Identify edge cases**: Flag scenarios not in the explicit criteria but implied
   by the intent. Examples: empty inputs, boundary values, concurrent access,
   error recovery.
5. **Flag intent gaps**: If a criterion is too vague to validate, flag it.
   Intent gaps block qa_passed and trigger intent refinement.

## Input Context
Acceptance Criteria: {acceptance_criteria}
Evidence Keys: {evidence_keys}

## Output
Respond with a JSON object matching this schema:
{{
  "criteria_results": [{{"criterion": "string", "passed": true, "reasoning": "string"}}],
  "defects": [{{"category": "string", "severity": "string", "description": "string", "acceptance_criterion": "string"}}],
  "intent_gaps": ["string"],
  "edge_case_concerns": ["string"]
}}
"""


def _qa_fallback(context: AgentContext) -> str:
    """Rule-based fallback using existing keyword-based QA validation.

    Returns a JSON string matching QAAgentOutput schema.
    """
    import json

    from src.assembler.assembler import QAHandoffMapping
    from src.qa.qa_agent import validate

    acceptance_criteria = context.extra.get("acceptance_criteria", [])
    qa_handoff_raw = context.extra.get("qa_handoff", [])
    evidence = context.evidence or {}

    qa_handoff = []
    for h in qa_handoff_raw:
        if isinstance(h, QAHandoffMapping):
            qa_handoff.append(h)
        elif isinstance(h, dict):
            qa_handoff.append(QAHandoffMapping(
                criterion=h.get("criterion", ""),
                validation_steps=h.get("validation_steps", []),
                source_experts=h.get("source_experts", []),
            ))

    result = validate(acceptance_criteria, qa_handoff, evidence)

    return json.dumps({
        "criteria_results": [
            {
                "criterion": cr.criterion,
                "passed": cr.passed,
                "reasoning": cr.evidence or "Keyword-based validation",
            }
            for cr in result.criteria_results
        ],
        "defects": [
            {
                "category": d.category.value,
                "severity": d.severity.value,
                "description": d.description,
                "acceptance_criterion": d.acceptance_criterion,
            }
            for d in result.defects
        ],
        "intent_gaps": [
            d.acceptance_criterion
            for d in result.defects
            if d.category.value == "intent_gap"
        ],
        "edge_case_concerns": [],
    })


QA_AGENT_CONFIG = AgentConfig(
    agent_name="qa_agent",
    pipeline_step="qa_eval",
    model_class="balanced",
    system_prompt_template=QA_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.50,
    output_schema=QAAgentOutput,
    fallback_fn=_qa_fallback,
    block_on_threat=False,
)
