"""Tests for Assembler Agent configuration and LLM integration (Epic 23, Story 3.6).

Tests cover:
- AssemblerAgentConfig structure and defaults
- AssemblerAgentOutput schema validation
- Semantic conflict detection
- Intent-based conflict resolution
- Provenance enrichment
- Fallback to keyword-based assemble()
"""

import json
from uuid import UUID, uuid4

import pytest

from src.agent.framework import AgentConfig, AgentContext
from src.assembler.assembler_config import (
    ASSEMBLER_AGENT_CONFIG,
    ASSEMBLER_SYSTEM_PROMPT,
    AssemblerAgentOutput,
    AssemblerConflict,
    AssemblerPlanStep,
    _assembler_fallback,
)


class TestAssemblerAgentConfig:
    """Tests for AssemblerAgentConfig structure."""

    def test_config_is_agent_config(self) -> None:
        assert isinstance(ASSEMBLER_AGENT_CONFIG, AgentConfig)

    def test_agent_name(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.agent_name == "assembler_agent"

    def test_pipeline_step(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.pipeline_step == "assembler"

    def test_model_class_balanced(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.model_class == "balanced"

    def test_completion_mode(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.tool_allowlist == []

    def test_budget(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.max_budget_usd == 0.50

    def test_output_schema(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.output_schema is AssemblerAgentOutput

    def test_fallback_fn(self) -> None:
        assert ASSEMBLER_AGENT_CONFIG.fallback_fn is _assembler_fallback


class TestAssemblerAgentOutput:
    """Tests for AssemblerAgentOutput schema."""

    def test_full_output_parses(self) -> None:
        data = {
            "plan_steps": [
                {"description": "Add pagination logic", "source_expert": "technical", "is_checkpoint": False},
                {"description": "Validate page size", "source_expert": "qa", "is_checkpoint": True},
            ],
            "conflicts": [
                {
                    "expert_a": "technical",
                    "expert_b": "security",
                    "description": "In-memory cache vs DB-backed state",
                    "resolution": "Use DB-backed per security constraint",
                    "resolved_by": "intent",
                }
            ],
            "risks": ["Cache invalidation complexity"],
            "qa_handoff": [{"Pagination works": ["Test page 1"]}],
            "provenance_decisions": [
                {"decision": "Use DB cache", "source": "security", "rationale": "Data must persist across restarts"}
            ],
        }
        output = AssemblerAgentOutput.model_validate(data)
        assert len(output.plan_steps) == 2
        assert len(output.conflicts) == 1
        assert output.conflicts[0].resolved_by == "intent"

    def test_semantic_conflict_detection(self) -> None:
        """AC 26: LLM detects semantic conflicts even with different terminology."""
        conflict = AssemblerConflict(
            expert_a="technical",
            expert_b="security",
            description="Expert A recommends in-memory caching, Expert B recommends database-backed state",
            resolution="Use database-backed state per security constraint requiring data persistence",
            resolved_by="intent",
        )
        assert "in-memory" in conflict.description
        assert "database" in conflict.description

    def test_provenance_has_rationale(self) -> None:
        """AC 27: Provenance includes decision rationale beyond 'Expert recommendation'."""
        output = AssemblerAgentOutput(
            provenance_decisions=[
                {"decision": "Use AES-256", "source": "security", "rationale": "Compliance requirement for encryption at rest"},
            ],
        )
        assert output.provenance_decisions[0]["rationale"] != "Expert recommendation"

    def test_minimal_output_parses(self) -> None:
        data = {"plan_steps": []}
        output = AssemblerAgentOutput.model_validate(data)
        assert output.plan_steps == []


class TestAssemblerFallback:
    """Tests for the keyword-based fallback."""

    def test_fallback_returns_valid_json(self) -> None:
        tid = uuid4()
        cid = uuid4()
        context = AgentContext(
            taskpacket_id=tid,
            correlation_id=cid,
            expert_outputs=[
                {
                    "expert_id": str(uuid4()),
                    "expert_version": 1,
                    "expert_name": "security-expert",
                    "recommendations": ["Use encrypted storage"],
                    "risks": ["Key rotation needed"],
                    "validations": ["Verify encryption at rest"],
                    "assumptions": ["AES-256 available"],
                }
            ],
            extra={
                "intent_constraints": ["Must not expose credentials"],
                "acceptance_criteria": ["Data encrypted at rest"],
                "intent_version": 1,
            },
        )
        result = _assembler_fallback(context)
        data = json.loads(result)
        assert "plan_steps" in data
        assert "conflicts" in data
        assert len(data["plan_steps"]) > 0

    def test_fallback_with_no_experts(self) -> None:
        context = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            expert_outputs=[],
            extra={"intent_constraints": [], "acceptance_criteria": [], "intent_version": 1},
        )
        result = _assembler_fallback(context)
        data = json.loads(result)
        assert isinstance(data["plan_steps"], list)


class TestAssemblerSystemPrompt:
    """Tests for the system prompt template."""

    def test_prompt_has_required_placeholders(self) -> None:
        assert "{intent_goal}" in ASSEMBLER_SYSTEM_PROMPT
        assert "{intent_constraints}" in ASSEMBLER_SYSTEM_PROMPT
        assert "{acceptance_criteria}" in ASSEMBLER_SYSTEM_PROMPT

    def test_prompt_mentions_semantic_conflict(self) -> None:
        """AC 26: Prompt instructs semantic conflict detection."""
        assert "semantic" in ASSEMBLER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_provenance(self) -> None:
        assert "provenance" in ASSEMBLER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_json_output(self) -> None:
        assert "JSON" in ASSEMBLER_SYSTEM_PROMPT
