"""Tests for Router Agent configuration and LLM integration (Epic 23, Story 2.12).

Tests cover:
- RouterAgentConfig structure and defaults
- RouterAgentOutput schema validation
- Staged consultation recommendation (closing gap V9)
- Shadow expert recommendation (closing gap V8)
- Escalation reasoning
- Fallback to algorithmic route()
"""

import json

import pytest

from src.agent.framework import AgentConfig, AgentContext, AgentRunner
from src.routing.router_config import (
    ROUTER_AGENT_CONFIG,
    ROUTER_SYSTEM_PROMPT,
    RouterAgentOutput,
    RouterExpertSelection,
    _router_fallback,
)


class TestRouterAgentConfig:
    """Tests for RouterAgentConfig structure."""

    def test_config_is_agent_config(self) -> None:
        assert isinstance(ROUTER_AGENT_CONFIG, AgentConfig)

    def test_agent_name(self) -> None:
        assert ROUTER_AGENT_CONFIG.agent_name == "router_agent"

    def test_pipeline_step(self) -> None:
        assert ROUTER_AGENT_CONFIG.pipeline_step == "routing"

    def test_model_class_balanced(self) -> None:
        assert ROUTER_AGENT_CONFIG.model_class == "balanced"

    def test_completion_mode(self) -> None:
        assert ROUTER_AGENT_CONFIG.tool_allowlist == []

    def test_single_turn(self) -> None:
        assert ROUTER_AGENT_CONFIG.max_turns == 1

    def test_budget(self) -> None:
        assert ROUTER_AGENT_CONFIG.max_budget_usd == 0.30

    def test_output_schema(self) -> None:
        assert ROUTER_AGENT_CONFIG.output_schema is RouterAgentOutput

    def test_fallback_fn(self) -> None:
        assert ROUTER_AGENT_CONFIG.fallback_fn is _router_fallback


class TestRouterAgentOutput:
    """Tests for RouterAgentOutput schema."""

    def test_full_output_parses(self) -> None:
        data = {
            "selections": [
                {"expert_class": "security", "pattern": "staged", "rationale": "Security first"},
                {"expert_class": "technical", "pattern": "parallel", "rationale": "Standard review"},
            ],
            "shadow_recommendations": ["compliance"],
            "staged_rationale": "Security review must complete before partner API review",
            "escalation_flags": ["Low confidence on security expert"],
            "adjustments": "Switched partner_api from parallel to staged",
        }
        output = RouterAgentOutput.model_validate(data)
        assert len(output.selections) == 2
        assert output.selections[0].pattern == "staged"
        assert len(output.shadow_recommendations) == 1

    def test_minimal_output_parses(self) -> None:
        data = {"selections": []}
        output = RouterAgentOutput.model_validate(data)
        assert output.selections == []
        assert output.shadow_recommendations == []

    def test_staged_consultation_field(self) -> None:
        """AC 20: LLM can recommend staged consultation (closes gap V9)."""
        output = RouterAgentOutput(
            selections=[
                RouterExpertSelection(expert_class="security", pattern="staged", rationale="Must go first"),
                RouterExpertSelection(expert_class="partner", pattern="staged", rationale="Depends on security"),
            ],
            staged_rationale="Security review informs partner API boundaries",
        )
        staged = [s for s in output.selections if s.pattern == "staged"]
        assert len(staged) == 2
        assert output.staged_rationale != ""

    def test_shadow_recommendation_field(self) -> None:
        """AC 21: LLM can recommend shadow experts (closes gap V8)."""
        output = RouterAgentOutput(
            shadow_recommendations=["compliance", "qa_validation"],
        )
        assert len(output.shadow_recommendations) == 2

    def test_escalation_flags_field(self) -> None:
        output = RouterAgentOutput(
            escalation_flags=["Budget exhausted with uncovered mandatory classes"],
        )
        assert len(output.escalation_flags) == 1


class TestRouterFallback:
    """Tests for the rule-based fallback function."""

    def test_fallback_returns_valid_json(self) -> None:
        context = AgentContext(
            risk_flags={"risk_security": True},
            overlays=["security"],
            extra={"base_role": "developer"},
        )
        result = _router_fallback(context)
        data = json.loads(result)
        assert "selections" in data
        assert "shadow_recommendations" in data

    def test_fallback_with_no_risk_flags(self) -> None:
        context = AgentContext(
            risk_flags={},
            overlays=[],
            extra={"base_role": "developer"},
        )
        result = _router_fallback(context)
        data = json.loads(result)
        assert isinstance(data["selections"], list)

    def test_fallback_shadow_recommendations_empty(self) -> None:
        """Rule-based fallback doesn't produce shadow recommendations."""
        context = AgentContext(
            risk_flags={},
            overlays=[],
            extra={"base_role": "developer"},
        )
        result = _router_fallback(context)
        data = json.loads(result)
        assert data["shadow_recommendations"] == []

    def test_fallback_with_invalid_overlay_graceful(self) -> None:
        context = AgentContext(
            risk_flags={},
            overlays=["nonexistent_overlay"],
            extra={"base_role": "developer"},
        )
        result = _router_fallback(context)
        data = json.loads(result)
        assert isinstance(data["selections"], list)


class TestRouterSystemPrompt:
    """Tests for the system prompt template."""

    def test_prompt_has_required_placeholders(self) -> None:
        assert "{base_role}" in ROUTER_SYSTEM_PROMPT
        assert "{risk_flags}" in ROUTER_SYSTEM_PROMPT
        assert "{required_classes}" in ROUTER_SYSTEM_PROMPT

    def test_prompt_mentions_staged(self) -> None:
        """AC 20: Prompt instructs LLM about staged consultation."""
        assert "staged" in ROUTER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_shadow(self) -> None:
        """AC 21: Prompt instructs LLM about shadow experts."""
        assert "shadow" in ROUTER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_escalation(self) -> None:
        assert "escalation" in ROUTER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_json_output(self) -> None:
        assert "JSON" in ROUTER_SYSTEM_PROMPT
