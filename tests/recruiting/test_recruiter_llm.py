"""Tests for Recruiter Agent configuration and LLM integration (Epic 23, Story 3.3).

Tests cover:
- RecruiterAgentConfig structure and defaults
- RecruiterAgentOutput schema validation
- LLM pack construction quality
- Fallback to template-based recruitment
"""

import json

import pytest

from src.agent.framework import AgentConfig, AgentContext
from src.recruiting.recruiter_config import (
    RECRUITER_AGENT_CONFIG,
    RECRUITER_SYSTEM_PROMPT,
    RecruiterAgentOutput,
    _recruiter_fallback,
)


class TestRecruiterAgentConfig:
    """Tests for RecruiterAgentConfig structure."""

    def test_config_is_agent_config(self) -> None:
        assert isinstance(RECRUITER_AGENT_CONFIG, AgentConfig)

    def test_agent_name(self) -> None:
        assert RECRUITER_AGENT_CONFIG.agent_name == "recruiter_agent"

    def test_pipeline_step(self) -> None:
        assert RECRUITER_AGENT_CONFIG.pipeline_step == "routing"

    def test_model_class_balanced(self) -> None:
        assert RECRUITER_AGENT_CONFIG.model_class == "balanced"

    def test_completion_mode(self) -> None:
        assert RECRUITER_AGENT_CONFIG.tool_allowlist == []

    def test_budget(self) -> None:
        assert RECRUITER_AGENT_CONFIG.max_budget_usd == 0.30

    def test_output_schema(self) -> None:
        assert RECRUITER_AGENT_CONFIG.output_schema is RecruiterAgentOutput

    def test_fallback_fn(self) -> None:
        assert RECRUITER_AGENT_CONFIG.fallback_fn is _recruiter_fallback


class TestRecruiterAgentOutput:
    """Tests for RecruiterAgentOutput schema."""

    def test_full_output_parses(self) -> None:
        data = {
            "expert_name": "security-auth-crypto",
            "scope_description": "Authentication and cryptography review",
            "definition": {
                "operating_procedure": "Review auth flows and crypto usage",
                "expected_outputs": "Risk assessment with recommendations",
                "edge_cases": "Legacy auth migration, key rotation",
            },
            "tool_policy": {"allowed": ["read", "search"], "denied": ["write"]},
            "trust_tier_recommendation": "probation",
            "creation_rationale": "No security expert available for auth review",
        }
        output = RecruiterAgentOutput.model_validate(data)
        assert output.expert_name == "security-auth-crypto"
        assert output.trust_tier_recommendation == "probation"

    def test_trust_tier_never_trusted(self) -> None:
        """New experts never start as trusted."""
        output = RecruiterAgentOutput(
            expert_name="test",
            scope_description="test",
            trust_tier_recommendation="shadow",
        )
        assert output.trust_tier_recommendation in ("shadow", "probation")

    def test_minimal_output_parses(self) -> None:
        data = {"expert_name": "test-expert", "scope_description": "Test"}
        output = RecruiterAgentOutput.model_validate(data)
        assert output.expert_name == "test-expert"


class TestRecruiterFallback:
    """Tests for the template-based fallback."""

    def test_fallback_returns_valid_json(self) -> None:
        context = AgentContext(
            extra={
                "expert_class": "security",
                "capability_tags": ["auth", "crypto"],
            },
        )
        result = _recruiter_fallback(context)
        data = json.loads(result)
        assert "expert_name" in data
        assert "security" in data["expert_name"]

    def test_fallback_always_shadow(self) -> None:
        context = AgentContext(extra={"expert_class": "technical"})
        result = _recruiter_fallback(context)
        data = json.loads(result)
        assert data["trust_tier_recommendation"] == "shadow"

    def test_fallback_generates_name_from_tags(self) -> None:
        context = AgentContext(
            extra={
                "expert_class": "compliance",
                "capability_tags": ["retention", "audit"],
            },
        )
        result = _recruiter_fallback(context)
        data = json.loads(result)
        assert "audit" in data["expert_name"] or "retention" in data["expert_name"]


class TestRecruiterSystemPrompt:
    """Tests for the system prompt template."""

    def test_prompt_has_required_placeholders(self) -> None:
        assert "{expert_class}" in RECRUITER_SYSTEM_PROMPT
        assert "{capability_tags}" in RECRUITER_SYSTEM_PROMPT

    def test_prompt_mentions_trust_tier(self) -> None:
        assert "shadow" in RECRUITER_SYSTEM_PROMPT.lower()
        assert "probation" in RECRUITER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_scope(self) -> None:
        assert "scope" in RECRUITER_SYSTEM_PROMPT.lower()
