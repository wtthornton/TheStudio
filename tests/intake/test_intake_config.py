"""Unit tests for Intake Agent config and LLM conversion (Epic 23, AC 9-12).

Tests IntakeAgentConfig, IntakeAgentOutput schema, fallback function,
and integration with AgentRunner.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.adapters.llm import LLMResponse
from src.admin.model_gateway import (
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    ModelRouter,
    ProviderConfig,
)
from src.agent.framework import AgentContext, AgentRunner
from src.intake.intake_config import (
    INTAKE_AGENT_CONFIG,
    IntakeAgentOutput,
    _intake_fallback,
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


class TestIntakeAgentConfig:
    """Test IntakeAgentConfig is correctly defined per AC 9."""

    def test_agent_name(self) -> None:
        assert INTAKE_AGENT_CONFIG.agent_name == "intake_agent"

    def test_pipeline_step(self) -> None:
        assert INTAKE_AGENT_CONFIG.pipeline_step == "intake"

    def test_model_class_is_fast(self) -> None:
        assert INTAKE_AGENT_CONFIG.model_class == "fast"

    def test_no_tools(self) -> None:
        assert INTAKE_AGENT_CONFIG.tool_allowlist == []

    def test_single_turn(self) -> None:
        assert INTAKE_AGENT_CONFIG.max_turns == 1

    def test_budget_limit(self) -> None:
        assert INTAKE_AGENT_CONFIG.max_budget_usd == 0.10

    def test_output_schema(self) -> None:
        assert INTAKE_AGENT_CONFIG.output_schema is IntakeAgentOutput

    def test_has_fallback(self) -> None:
        assert INTAKE_AGENT_CONFIG.fallback_fn is not None

    def test_block_on_threat_enabled(self) -> None:
        assert INTAKE_AGENT_CONFIG.block_on_threat is True

    def test_system_prompt_template_has_placeholders(self) -> None:
        assert "{repo}" in INTAKE_AGENT_CONFIG.system_prompt_template
        assert "{labels}" in INTAKE_AGENT_CONFIG.system_prompt_template


class TestIntakeAgentOutput:
    """Test IntakeAgentOutput Pydantic model."""

    def test_valid_accepted_output(self) -> None:
        output = IntakeAgentOutput(
            accepted=True,
            base_role="developer",
            overlays=["security"],
            risk_flags={"risk_security": True},
            reasoning="Issue involves auth changes",
        )
        assert output.accepted is True
        assert output.base_role == "developer"

    def test_valid_rejected_output(self) -> None:
        output = IntakeAgentOutput(
            accepted=False,
            rejection_reason="Missing agent:run label",
            reasoning="No automation trigger label",
        )
        assert output.accepted is False
        assert output.rejection_reason == "Missing agent:run label"

    def test_defaults(self) -> None:
        output = IntakeAgentOutput(accepted=True)
        assert output.rejection_reason == ""
        assert output.base_role == "developer"
        assert output.overlays == []
        assert output.risk_flags == {}
        assert output.reasoning == ""

    def test_parse_from_json(self) -> None:
        raw = json.dumps({
            "accepted": True,
            "rejection_reason": "",
            "base_role": "architect",
            "overlays": ["migration", "security"],
            "risk_flags": {"risk_breaking": True, "risk_security": True},
            "reasoning": "Refactoring with security implications",
        })
        output = IntakeAgentOutput.model_validate_json(raw)
        assert output.base_role == "architect"
        assert "migration" in output.overlays


class TestIntakeFallback:
    """Test the rule-based fallback function."""

    def test_fallback_accepted(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix bug in auth",
            issue_body="The login page is broken",
            labels=["agent:run", "type:bug"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-001",
            },
        )
        result_json = _intake_fallback(ctx)
        result = json.loads(result_json)
        assert result["accepted"] is True
        assert result["base_role"] == "developer"

    def test_fallback_rejected_no_label(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix bug",
            issue_body="",
            labels=["type:bug"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-002",
            },
        )
        result_json = _intake_fallback(ctx)
        result = json.loads(result_json)
        assert result["accepted"] is False
        assert "agent:run" in result["rejection_reason"]

    def test_fallback_with_overlays(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix auth vulnerability",
            issue_body="Security issue in auth module",
            labels=["agent:run", "type:security", "risk:auth"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-003",
            },
        )
        result_json = _intake_fallback(ctx)
        result = json.loads(result_json)
        assert result["accepted"] is True
        assert "security" in result["overlays"]

    def test_fallback_refactor_is_architect(self) -> None:
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Refactor auth middleware",
            issue_body="Restructure the auth module",
            labels=["agent:run", "type:refactor"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-004",
            },
        )
        result_json = _intake_fallback(ctx)
        result = json.loads(result_json)
        assert result["accepted"] is True
        assert result["base_role"] == "architect"


class TestIntakeAgentRunner:
    """Test IntakeAgent through AgentRunner lifecycle (AC 12)."""

    @pytest.mark.asyncio
    async def test_llm_returns_structured_output(self, mock_gateway: dict) -> None:
        """LLM returns valid JSON — parsed into IntakeAgentOutput."""
        llm_response = LLMResponse(
            content=json.dumps({
                "accepted": True,
                "rejection_reason": "",
                "base_role": "developer",
                "overlays": ["security"],
                "risk_flags": {"risk_security": True},
                "reasoning": "Auth-related bug fix",
            }),
            tokens_in=100,
            tokens_out=50,
            model="test-fast-model",
            stop_reason="end_turn",
        )

        runner = AgentRunner(INTAKE_AGENT_CONFIG)
        ctx = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo="owner/repo",
            issue_title="Fix auth bug",
            issue_body="Login is broken",
            labels=["agent:run", "type:bug", "risk:auth"],
        )

        with patch.object(
            runner, "_call_llm_completion", new_callable=AsyncMock, return_value=llm_response,
        ), patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"intake_agent": True}
            result = await runner.run(ctx)

        assert result.agent_name == "intake_agent"
        assert result.used_fallback is False
        assert result.parsed_output is not None
        assert isinstance(result.parsed_output, IntakeAgentOutput)
        assert result.parsed_output.accepted is True

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_uses_fallback(self, mock_gateway: dict) -> None:
        """When feature flag is off, fallback is used."""
        runner = AgentRunner(INTAKE_AGENT_CONFIG)
        ctx = AgentContext(
            repo="owner/repo",
            issue_title="Fix bug",
            issue_body="Something is broken",
            labels=["agent:run", "type:bug"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-flag",
            },
        )

        with patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"intake_agent": False}
            result = await runner.run(ctx)

        assert result.used_fallback is True
        assert result.model_used == "fallback"

    @pytest.mark.asyncio
    async def test_malformed_llm_output_triggers_fallback(self, mock_gateway: dict) -> None:
        """When LLM returns unparseable output, fallback is used."""
        llm_response = LLMResponse(
            content="I don't understand the request",
            tokens_in=50,
            tokens_out=20,
            model="test-fast-model",
            stop_reason="end_turn",
        )

        runner = AgentRunner(INTAKE_AGENT_CONFIG)
        ctx = AgentContext(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo="owner/repo",
            issue_title="Fix bug",
            issue_body="Something broke",
            labels=["agent:run", "type:bug"],
            extra={
                "repo_registered": True,
                "repo_paused": False,
                "has_active_workflow": False,
                "event_id": "evt-malformed",
            },
        )

        with patch.object(
            runner, "_call_llm_completion", new_callable=AsyncMock, return_value=llm_response,
        ), patch("src.agent.framework.settings") as mock_settings:
            mock_settings.agent_llm_enabled = {"intake_agent": True}
            result = await runner.run(ctx)

        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_system_prompt_rendered(self, mock_gateway: dict) -> None:
        """System prompt template renders with context variables."""
        runner = AgentRunner(INTAKE_AGENT_CONFIG)
        ctx = AgentContext(
            repo="owner/my-repo",
            labels=["agent:run", "type:bug", "risk:auth"],
        )
        prompt = runner.build_system_prompt(ctx)
        assert "owner/my-repo" in prompt
        assert "agent:run" in prompt
