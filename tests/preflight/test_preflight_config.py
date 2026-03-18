"""Unit tests for preflight agent config and output model (Epic 28 Story 28.1).

Tests:
- PreflightOutput model validation
- PREFLIGHT_AGENT_CONFIG fields match AC 1
- System prompt contains three checks (AC 2)
- Fallback function behavior (AC 4)
"""

import json

from src.agent.framework import AgentContext
from src.preflight.preflight_config import (
    PREFLIGHT_AGENT_CONFIG,
    PREFLIGHT_SYSTEM_PROMPT,
    PreflightOutput,
    _preflight_fallback,
)


class TestPreflightOutput:
    """AC 3: PreflightOutput Pydantic model."""

    def test_approved_plan(self) -> None:
        output = PreflightOutput(
            approved=True,
            summary="All checks passed",
        )
        assert output.approved is True
        assert output.uncovered_criteria == []
        assert output.constraint_violations == []
        assert output.vague_steps == []

    def test_rejected_plan_with_issues(self) -> None:
        output = PreflightOutput(
            approved=False,
            uncovered_criteria=["Widget works", "Error handling"],
            constraint_violations=["Uses global mutable state"],
            vague_steps=["Figure out the best approach"],
            summary="3 issues found",
        )
        assert output.approved is False
        assert len(output.uncovered_criteria) == 2
        assert len(output.constraint_violations) == 1
        assert len(output.vague_steps) == 1

    def test_serialization_roundtrip(self) -> None:
        output = PreflightOutput(
            approved=False,
            uncovered_criteria=["AC1"],
            summary="One gap",
        )
        data = output.model_dump()
        restored = PreflightOutput(**data)
        assert restored == output


class TestPreflightAgentConfig:
    """AC 1: PREFLIGHT_AGENT_CONFIG fields."""

    def test_agent_name(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.agent_name == "preflight_agent"

    def test_pipeline_step(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.pipeline_step == "preflight"

    def test_max_turns(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.max_turns == 1

    def test_max_budget(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.max_budget_usd == 0.50

    def test_output_schema(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.output_schema is PreflightOutput

    def test_has_fallback(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.fallback_fn is not None

    def test_no_tool_use(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.tool_allowlist == []

    def test_does_not_block_on_threat(self) -> None:
        assert PREFLIGHT_AGENT_CONFIG.block_on_threat is False


class TestPreflightSystemPrompt:
    """AC 2: System prompt implements three checks."""

    def test_criteria_coverage_check(self) -> None:
        assert "Criteria Coverage" in PREFLIGHT_SYSTEM_PROMPT

    def test_constraint_compliance_check(self) -> None:
        assert "Constraint Compliance" in PREFLIGHT_SYSTEM_PROMPT

    def test_step_specificity_check(self) -> None:
        assert "Step Specificity" in PREFLIGHT_SYSTEM_PROMPT

    def test_not_meridian_disclaimer(self) -> None:
        assert "NOT Meridian" in PREFLIGHT_SYSTEM_PROMPT

    def test_includes_template_variables(self) -> None:
        assert "{plan_steps}" in PREFLIGHT_SYSTEM_PROMPT
        assert "{acceptance_criteria}" in PREFLIGHT_SYSTEM_PROMPT
        assert "{constraints}" in PREFLIGHT_SYSTEM_PROMPT


class TestPreflightFallback:
    """AC 4: Fallback returns approved=True on provider error."""

    def test_fallback_approves_normal_plan(self) -> None:
        ctx = AgentContext(
            extra={
                "plan_steps": ["Add validation to endpoint", "Write unit tests"],
                "acceptance_criteria": ["Endpoint validates input"],
                "constraints": [],
            },
        )
        raw = _preflight_fallback(ctx)
        data = json.loads(raw)
        assert data["approved"] is True
        assert data["summary"] == "Preflight passed (rule-based)"

    def test_fallback_rejects_empty_plan(self) -> None:
        ctx = AgentContext(
            extra={
                "plan_steps": [],
                "acceptance_criteria": ["Something works"],
                "constraints": [],
            },
        )
        raw = _preflight_fallback(ctx)
        data = json.loads(raw)
        assert data["approved"] is False
        assert "Something works" in data["uncovered_criteria"]

    def test_fallback_catches_vague_steps(self) -> None:
        ctx = AgentContext(
            extra={
                "plan_steps": [
                    "Figure out the best caching strategy",
                    "Implement the cache",
                ],
                "acceptance_criteria": [],
                "constraints": [],
            },
        )
        raw = _preflight_fallback(ctx)
        data = json.loads(raw)
        assert data["approved"] is False
        assert len(data["vague_steps"]) == 1
        assert "Figure out" in data["vague_steps"][0]

    def test_fallback_catches_tbd_steps(self) -> None:
        ctx = AgentContext(
            extra={
                "plan_steps": ["TBD — decide later"],
                "acceptance_criteria": [],
                "constraints": [],
            },
        )
        raw = _preflight_fallback(ctx)
        data = json.loads(raw)
        assert data["approved"] is False

    def test_fallback_with_no_context(self) -> None:
        ctx = AgentContext(extra={})
        raw = _preflight_fallback(ctx)
        data = json.loads(raw)
        # Empty plan → rejected
        assert data["approved"] is False
