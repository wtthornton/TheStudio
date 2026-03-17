"""Unit tests for Context Agent config and LLM conversion (Epic 23, AC 13-15).

Tests ContextAgentConfig, ContextAgentOutput schema, fallback function,
and integration with AgentRunner.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.adapters.llm import LLMResponse
from src.admin.model_gateway import (
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    ModelRouter,
    ProviderConfig,
)
from src.agent.framework import AgentContext, AgentRunner
from src.context.context_config import (
    CONTEXT_AGENT_CONFIG,
    ContextAgentOutput,
    _context_fallback,
)

MOCK_PROVIDER = ProviderConfig(
    provider_id="test-provider",
    provider="test",
    model_id="test-fast-model",
    model_class=ModelClass.FAST,
    cost_per_1k_tokens=0.0005,
)


@pytest.fixture
def mock_gateway():
    """Patch gateway singletons."""
    router = ModelRouter(providers=[MOCK_PROVIDER])
    enforcer = InMemoryBudgetEnforcer()
    audit_store = InMemoryModelAuditStore()

    with (
        patch("src.agent.framework.get_model_router", return_value=router),
        patch("src.agent.framework.get_budget_enforcer", return_value=enforcer),
        patch("src.agent.framework.get_model_audit_store", return_value=audit_store),
    ):
        yield {"router": router, "enforcer": enforcer, "audit_store": audit_store}


class TestContextAgentConfig:
    """Test ContextAgentConfig is correctly defined per AC 13."""

    def test_agent_name(self) -> None:
        assert CONTEXT_AGENT_CONFIG.agent_name == "context_agent"

    def test_pipeline_step(self) -> None:
        assert CONTEXT_AGENT_CONFIG.pipeline_step == "context"

    def test_model_class_is_fast(self) -> None:
        assert CONTEXT_AGENT_CONFIG.model_class == "fast"

    def test_no_tools(self) -> None:
        assert CONTEXT_AGENT_CONFIG.tool_allowlist == []

    def test_single_turn(self) -> None:
        assert CONTEXT_AGENT_CONFIG.max_turns == 1

    def test_budget_limit(self) -> None:
        assert CONTEXT_AGENT_CONFIG.max_budget_usd == 0.20

    def test_output_schema(self) -> None:
        assert CONTEXT_AGENT_CONFIG.output_schema is ContextAgentOutput

    def test_has_fallback(self) -> None:
        assert CONTEXT_AGENT_CONFIG.fallback_fn is not None

    def test_block_on_threat_disabled(self) -> None:
        assert CONTEXT_AGENT_CONFIG.block_on_threat is False

    def test_system_prompt_has_placeholders(self) -> None:
        assert "{repo}" in CONTEXT_AGENT_CONFIG.system_prompt_template
        assert "{risk_flags}" in CONTEXT_AGENT_CONFIG.system_prompt_template
        assert "{complexity}" in CONTEXT_AGENT_CONFIG.system_prompt_template


class TestContextAgentOutput:
    """Test ContextAgentOutput Pydantic model."""

    def test_valid_output(self) -> None:
        output = ContextAgentOutput(
            scope_summary="Affects auth module and database layer",
            impacted_services=["auth", "database"],
            risk_flags={"risk_security": True, "risk_data": True},
            complexity_rationale="Multiple services with security implications",
            open_questions=["Does this affect the public API?"],
            additional_context_needed=["auth-service context pack"],
        )
        assert output.scope_summary == "Affects auth module and database layer"
        assert len(output.impacted_services) == 2

    def test_defaults(self) -> None:
        output = ContextAgentOutput(scope_summary="Simple change")
        assert output.impacted_services == []
        assert output.risk_flags == {}
        assert output.complexity_rationale == ""
        assert output.open_questions == []
        assert output.additional_context_needed == []

    def test_parse_from_json(self) -> None:
        raw = json.dumps({
            "scope_summary": "Database migration",
            "impacted_services": ["database", "api"],
            "risk_flags": {"risk_data": True, "risk_breaking": True},
            "complexity_rationale": "Schema change with breaking API impact",
            "open_questions": ["Is rollback possible?"],
            "additional_context_needed": [],
        })
        output = ContextAgentOutput.model_validate_json(raw)
        assert output.risk_flags["risk_data"] is True
        assert len(output.open_questions) == 1


class TestContextFallback:
    """Test the rule-based fallback function."""

    def test_fallback_simple_issue(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix typo in README",
            issue_body="There is a typo on line 5.",
        )
        result_json = _context_fallback(ctx)
        result = json.loads(result_json)
        assert "scope_summary" in result
        assert isinstance(result["risk_flags"], dict)
        assert result["open_questions"] == []

    def test_fallback_security_issue(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix credential leak",
            issue_body="Credentials are logged to stdout via auth module.",
        )
        result_json = _context_fallback(ctx)
        result = json.loads(result_json)
        assert result["risk_flags"]["risk_security"] is True
        assert "auth" in result["impacted_services"]

    def test_fallback_multi_component(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Refactor api and database layer",
            issue_body="The api and database components need updating.",
        )
        result_json = _context_fallback(ctx)
        result = json.loads(result_json)
        assert len(result["impacted_services"]) >= 2


class TestContextAgentRunner:
    """Test ContextAgent through AgentRunner lifecycle (AC 14-15)."""

    @pytest.mark.asyncio
    async def test_llm_returns_structured_output(self, mock_gateway: dict) -> None:
        """LLM returns valid JSON — parsed into ContextAgentOutput."""
        llm_response = LLMResponse(
            content=json.dumps({
                "scope_summary": "Affects authentication service",
                "impacted_services": ["auth", "user-service"],
                "risk_flags": {"risk_security": True},
                "complexity_rationale": "Auth changes require security review",
                "open_questions": ["Does this affect SSO?"],
                "additional_context_needed": [],
            }),
            tokens_in=200,
            tokens_out=100,
            model="test-fast-model",
            stop_reason="end_turn",
        )

        runner = AgentRunner(CONTEXT_AGENT_CONFIG)
        ctx = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo="owner/repo",
            issue_title="Fix auth bug",
            issue_body="Login is broken for SSO users",
            risk_flags={"risk_security": True},
            complexity="medium",
        )

        with patch.object(
            runner, "_call_llm_completion", new_callable=AsyncMock, return_value=llm_response,
        ), patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"context_agent": True}
            result = await runner.run(ctx)

        assert result.agent_name == "context_agent"
        assert result.used_fallback is False
        assert result.parsed_output is not None
        assert isinstance(result.parsed_output, ContextAgentOutput)
        assert result.parsed_output.risk_flags["risk_security"] is True

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_uses_fallback(self, mock_gateway: dict) -> None:
        """When feature flag is off, deterministic fallback is used."""
        runner = AgentRunner(CONTEXT_AGENT_CONFIG)
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix typo",
            issue_body="Small change",
        )

        with patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"context_agent": False}
            result = await runner.run(ctx)

        assert result.used_fallback is True
        assert result.model_used == "fallback"
        # Fallback should still produce valid output
        output = json.loads(result.raw_output)
        assert "scope_summary" in output

    @pytest.mark.asyncio
    async def test_system_prompt_includes_risk_context(self, mock_gateway: dict) -> None:
        """System prompt renders with risk flags and complexity."""
        runner = AgentRunner(CONTEXT_AGENT_CONFIG)
        ctx = AgentContext(
            repo="owner/repo",
            risk_flags={"risk_security": True, "risk_data": False},
            complexity="medium",
        )
        prompt = runner.build_system_prompt(ctx)
        assert "owner/repo" in prompt
        assert "risk_security" in prompt
        assert "medium" in prompt

    @pytest.mark.asyncio
    async def test_llm_failure_triggers_fallback(self, mock_gateway: dict) -> None:
        """When LLM call fails, deterministic fallback is used."""
        runner = AgentRunner(CONTEXT_AGENT_CONFIG)
        ctx = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo="owner/repo",
            issue_title="Update database schema",
            issue_body="ALTER TABLE users ADD COLUMN verified BOOLEAN",
        )

        with patch.object(
            runner, "_call_llm_completion", new_callable=AsyncMock,
            side_effect=Exception("API timeout"),
        ), patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"context_agent": True}
            result = await runner.run(ctx)

        assert result.used_fallback is True
        output = json.loads(result.raw_output)
        assert output["risk_flags"]["risk_data"] is True
