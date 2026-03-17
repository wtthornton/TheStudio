"""Tests for Intent Builder Agent configuration and LLM integration (Epic 23, Story 2.9).

Tests cover:
- IntentAgentConfig structure and defaults
- IntentAgentOutput schema validation
- Semantic extraction: invariant identification, implicit criteria synthesis
- Fallback to rule-based build_intent()
- System prompt template rendering
"""

import json

import pytest

from src.agent.framework import AgentConfig, AgentContext, AgentRunner
from src.intent.intent_config import (
    INTENT_AGENT_CONFIG,
    INTENT_SYSTEM_PROMPT,
    IntentAgentOutput,
    _intent_fallback,
)


class TestIntentAgentConfig:
    """Tests for IntentAgentConfig structure."""

    def test_config_is_agent_config(self) -> None:
        assert isinstance(INTENT_AGENT_CONFIG, AgentConfig)

    def test_agent_name(self) -> None:
        assert INTENT_AGENT_CONFIG.agent_name == "intent_agent"

    def test_pipeline_step(self) -> None:
        assert INTENT_AGENT_CONFIG.pipeline_step == "intent"

    def test_model_class_balanced(self) -> None:
        """Intent Builder uses balanced model per doc 26."""
        assert INTENT_AGENT_CONFIG.model_class == "balanced"

    def test_completion_mode(self) -> None:
        """Intent Builder uses completion mode — no tools."""
        assert INTENT_AGENT_CONFIG.tool_allowlist == []

    def test_single_turn(self) -> None:
        assert INTENT_AGENT_CONFIG.max_turns == 1

    def test_budget(self) -> None:
        assert INTENT_AGENT_CONFIG.max_budget_usd == 0.50

    def test_output_schema(self) -> None:
        assert INTENT_AGENT_CONFIG.output_schema is IntentAgentOutput

    def test_fallback_fn(self) -> None:
        assert INTENT_AGENT_CONFIG.fallback_fn is _intent_fallback

    def test_block_on_threat_disabled(self) -> None:
        """Intent builder doesn't block on threat — intake handles that."""
        assert INTENT_AGENT_CONFIG.block_on_threat is False


class TestIntentAgentOutput:
    """Tests for IntentAgentOutput schema."""

    def test_full_output_parses(self) -> None:
        data = {
            "goal": "Add pagination to user list endpoint",
            "constraints": ["Must include tests"],
            "invariants": ["Existing API endpoints must continue to work"],
            "acceptance_criteria": ["Pagination returns correct page"],
            "non_goals": ["UI changes"],
            "assumptions": ["Using cursor-based pagination"],
            "open_questions": ["What is the default page size?"],
        }
        output = IntentAgentOutput.model_validate(data)
        assert output.goal == "Add pagination to user list endpoint"
        assert len(output.invariants) == 1
        assert len(output.open_questions) == 1

    def test_minimal_output_parses(self) -> None:
        data = {"goal": "Fix login bug"}
        output = IntentAgentOutput.model_validate(data)
        assert output.goal == "Fix login bug"
        assert output.constraints == []
        assert output.invariants == []

    def test_invariants_field_exists(self) -> None:
        """AC 17: Invariants are a first-class field (closes gap V7)."""
        output = IntentAgentOutput(
            goal="test",
            invariants=["API contract must not change", "DB schema backward compatible"],
        )
        assert len(output.invariants) == 2

    def test_json_roundtrip(self) -> None:
        output = IntentAgentOutput(
            goal="Refactor auth",
            constraints=["No credential exposure"],
            invariants=["Session management unchanged"],
            acceptance_criteria=["All auth tests pass"],
            non_goals=["UI redesign"],
            assumptions=["Using JWT"],
            open_questions=[],
        )
        json_str = output.model_dump_json()
        parsed = IntentAgentOutput.model_validate_json(json_str)
        assert parsed.goal == output.goal
        assert parsed.invariants == output.invariants


class TestIntentFallback:
    """Tests for the rule-based fallback function."""

    def test_fallback_returns_valid_json(self) -> None:
        context = AgentContext(
            issue_title="Add pagination",
            issue_body="## Requirements\n- Page size configurable\n- Default 20 items",
            risk_flags={},
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert "goal" in data
        assert "constraints" in data
        assert "acceptance_criteria" in data

    def test_fallback_extracts_goal(self) -> None:
        context = AgentContext(
            issue_title="Fix auth timeout bug",
            issue_body="Users are getting logged out after 5 minutes.",
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert "Fix auth timeout bug" in data["goal"]

    def test_fallback_derives_constraints_from_risk_flags(self) -> None:
        context = AgentContext(
            issue_title="Update encryption",
            issue_body="Switch to AES-256",
            risk_flags={"risk_security": True},
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert any("credential" in c.lower() or "secret" in c.lower() for c in data["constraints"])

    def test_fallback_extracts_criteria_from_checkboxes(self) -> None:
        context = AgentContext(
            issue_title="Add feature",
            issue_body="- [ ] First criterion\n- [ ] Second criterion",
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert len(data["acceptance_criteria"]) >= 2

    def test_fallback_extracts_non_goals(self) -> None:
        context = AgentContext(
            issue_title="Refactor",
            issue_body="Out of scope: - UI changes\n- Performance optimization",
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert len(data["non_goals"]) >= 1

    def test_fallback_default_criteria_when_none_found(self) -> None:
        context = AgentContext(
            issue_title="Simple fix",
            issue_body="",
        )
        result = _intent_fallback(context)
        data = json.loads(result)
        assert len(data["acceptance_criteria"]) >= 1

    def test_fallback_invariants_empty(self) -> None:
        """Rule-based fallback doesn't extract invariants — that's LLM-only."""
        context = AgentContext(issue_title="Test", issue_body="")
        result = _intent_fallback(context)
        data = json.loads(result)
        assert data["invariants"] == []


class TestIntentSystemPrompt:
    """Tests for the system prompt template."""

    def test_prompt_template_has_required_placeholders(self) -> None:
        assert "{repo}" in INTENT_SYSTEM_PROMPT
        assert "{risk_flags}" in INTENT_SYSTEM_PROMPT
        assert "{complexity}" in INTENT_SYSTEM_PROMPT

    def test_prompt_mentions_invariants(self) -> None:
        """AC 17: System prompt instructs LLM to extract invariants."""
        assert "invariant" in INTENT_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_implicit_criteria(self) -> None:
        """AC 18: System prompt instructs LLM to synthesize implicit criteria."""
        assert "implicit" in INTENT_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_json_output(self) -> None:
        assert "JSON" in INTENT_SYSTEM_PROMPT

    def test_prompt_renders_with_context(self) -> None:
        runner = AgentRunner(INTENT_AGENT_CONFIG)
        context = AgentContext(
            repo="owner/repo",
            risk_flags={"risk_security": True},
            complexity="medium",
        )
        rendered = runner.build_system_prompt(context)
        assert "owner/repo" in rendered
        assert "risk_security" in rendered
