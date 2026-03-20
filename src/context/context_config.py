"""Context Agent configuration for the Unified Agent Framework (Epic 23, AC 13-15).

Defines ContextAgentConfig and ContextAgentOutput for LLM-powered context
enrichment. Falls back to deterministic enrich_taskpacket() when LLM is unavailable.

Architecture reference: thestudioarc/03-context-manager.md
Model class reference: thestudioarc/26-model-runtime-and-routing.md (fast for context)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agent.framework import AgentConfig, AgentContext


class ContextAgentOutput(BaseModel):
    """Structured output from the LLM-powered context agent.

    The LLM reviews deterministic analysis results plus raw issue content
    to provide enhanced scope, risk, and complexity assessment.
    """

    scope_summary: str = Field(
        description="Brief summary of what this issue affects",
    )
    impacted_services: list[str] = Field(
        default_factory=list,
        description="Services or modules likely impacted by this change",
    )
    risk_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Risk flags — includes both deterministic and LLM-detected flags",
    )
    complexity_rationale: str = Field(
        default="",
        description="Explanation of why the issue has its complexity level",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions the Intent Builder should investigate",
    )
    additional_context_needed: list[str] = Field(
        default_factory=list,
        description="Missing context packs or information sources",
    )


CONTEXT_SYSTEM_PROMPT = """\
You are the Context Manager Agent for TheStudio, an AI-augmented software delivery platform.

Your job is to enrich a TaskPacket with scope analysis, risk assessment, complexity rationale,
and identify open questions before the Intent Builder processes this issue.

## What You Receive
- The GitHub issue title and body
- Results from deterministic analysis (scope, risk flags, complexity score)
- Any available service context packs for this repository

## Your Tasks
1. **Scope Assessment**: Identify which services, modules, and files are likely affected.
   Go beyond the regex-detected components — reason about implicit impacts.
2. **Risk Enhancement**: Review the deterministic risk flags. Add any risks the regex missed.
   Consider: security implications, breaking changes, cross-team dependencies, data risks.
3. **Complexity Rationale**: Explain WHY this issue has its complexity level. Reference
   specific factors (number of services, risk combinations, migration complexity).
4. **Open Questions**: Identify questions that need answers before intent can be built.
   Examples: "Does this affect the public API?", "Are there database migrations needed?"
5. **Missing Context**: Flag any service context packs or documentation that would help.

## Input Context
Repository: {repo}
Deterministic Risk Flags: {risk_flags}
Complexity Band: {complexity}

## Output
Respond with a JSON object matching this schema:
{{
  "scope_summary": "string",
  "impacted_services": ["string"],
  "risk_flags": {{"risk_security": bool, ...}},
  "complexity_rationale": "string",
  "open_questions": ["string"],
  "additional_context_needed": ["string"]
}}
"""


def _context_fallback(context: AgentContext) -> str:
    """Rule-based fallback using existing deterministic analysis.

    Returns a JSON string matching ContextAgentOutput schema.
    """
    import json

    from src.context.risk_flagger import flag_risks
    from src.context.scope_analyzer import analyze_scope

    scope = analyze_scope(context.issue_title, context.issue_body)
    risks = flag_risks(context.issue_title, context.issue_body)

    return json.dumps({
        "scope_summary": f"Affects {scope.affected_files_estimate} file(s), "
        f"components: {', '.join(scope.components) or 'none detected'}",
        "impacted_services": scope.components,
        "risk_flags": risks,
        "complexity_rationale": "Deterministic analysis based on file count and risk flags",
        "open_questions": [],
        "additional_context_needed": [],
    })


CONTEXT_AGENT_CONFIG = AgentConfig(
    agent_name="context_agent",
    pipeline_step="context",
    model_class="fast",
    system_prompt_template=CONTEXT_SYSTEM_PROMPT,
    tool_allowlist=[],
    max_turns=1,
    max_budget_usd=0.20,
    output_schema=ContextAgentOutput,
    fallback_fn=_context_fallback,
    block_on_threat=False,
    batch_eligible=True,
)
