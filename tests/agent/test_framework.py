"""Unit tests for the Unified Agent Framework (Epic 23, Story 1.9).

Tests AgentRunner lifecycle: provider resolution, budget check, audit recording,
fallback dispatch, feature flag, structured output parsing, observability spans.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.adapters.llm import LLMResponse
from src.admin.model_gateway import (
    BudgetExceededError,
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    ModelRouter,
    NoProviderAvailableError,
    ProviderConfig,
)
from src.agent.framework import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentRunner,
    _extract_json_block,
)

# -- Fixtures ----------------------------------------------------------------


MOCK_PROVIDER = ProviderConfig(
    provider_id="test-provider",
    provider="test",
    model_id="test-model",
    model_class=ModelClass.BALANCED,
    cost_per_1k_tokens=0.001,
)


class SampleOutput(BaseModel):
    """Test output schema."""

    category: str
    confidence: float


def _make_config(**overrides: object) -> AgentConfig:
    defaults = {
        "agent_name": "test_agent",
        "pipeline_step": "test_step",
        "model_class": "fast",
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)  # type: ignore[arg-type]


def _make_context(**overrides: object) -> AgentContext:
    return AgentContext(**overrides)  # type: ignore[arg-type]


@pytest.fixture
def mock_gateway():
    """Patch gateway singletons for all tests."""
    router = ModelRouter(providers=[MOCK_PROVIDER])
    enforcer = InMemoryBudgetEnforcer()
    audit_store = InMemoryModelAuditStore()

    with (
        patch("src.agent.framework.get_model_router", return_value=router),
        patch("src.agent.framework.get_budget_enforcer", return_value=enforcer),
        patch("src.agent.framework.get_model_audit_store", return_value=audit_store),
    ):
        yield {"router": router, "enforcer": enforcer, "audit_store": audit_store}


@pytest.fixture
def mock_llm_adapter():
    """Patch LLM adapter to return canned response."""
    adapter = AsyncMock()
    adapter.complete.return_value = LLMResponse(
        content='{"category": "bug", "confidence": 0.95}',
        tokens_in=100,
        tokens_out=50,
        model="test-model",
        stop_reason="end_turn",
    )
    adapter.close = AsyncMock()
    with patch("src.agent.framework.get_llm_adapter", return_value=adapter):
        yield adapter


# -- Story 1.1: Dataclass tests ---------------------------------------------


class TestDataclasses:
    def test_agent_config_frozen(self):
        config = _make_config()
        with pytest.raises(AttributeError):
            config.agent_name = "changed"  # type: ignore[misc]

    def test_agent_config_defaults(self):
        config = _make_config()
        assert config.max_turns == 1
        assert config.max_budget_usd == 0.50
        assert config.tool_allowlist == []
        assert config.output_schema is None
        assert config.fallback_fn is None
        assert config.block_on_threat is False

    def test_agent_context_mutable(self):
        ctx = _make_context()
        ctx.repo = "updated"
        assert ctx.repo == "updated"

    def test_agent_context_defaults(self):
        ctx = _make_context()
        assert ctx.taskpacket_id is None
        assert ctx.labels == []
        assert ctx.extra == {}

    def test_agent_result_defaults(self):
        result = AgentResult(agent_name="test")
        assert result.used_fallback is False
        assert result.parsed_output is None
        assert result.threat_flags == []


# -- Story 1.5: JSON extraction tests ---------------------------------------


class TestJsonExtraction:
    def test_raw_json(self):
        assert _extract_json_block('{"key": "val"}') == '{"key": "val"}'

    def test_fenced_json(self):
        raw = '```json\n{"key": "val"}\n```'
        assert _extract_json_block(raw) == '{"key": "val"}'

    def test_json_with_preamble(self):
        raw = 'Here is the result:\n{"key": "val"}'
        assert _extract_json_block(raw) == '{"key": "val"}'

    def test_array_json(self):
        assert _extract_json_block('[1, 2, 3]') == '[1, 2, 3]'

    def test_no_json_returns_raw(self):
        assert _extract_json_block("plain text") == "plain text"

    def test_fenced_without_language(self):
        raw = '```\n{"a": 1}\n```'
        assert _extract_json_block(raw) == '{"a": 1}'


# -- Story 1.6: Feature flag tests ------------------------------------------


class TestFeatureFlag:
    @pytest.mark.asyncio
    async def test_flag_disabled_triggers_fallback(self, mock_gateway):
        """When feature flag is off, agent uses fallback without calling LLM."""
        fallback_called = False

        def fallback(ctx: AgentContext) -> str:
            nonlocal fallback_called
            fallback_called = True
            return "fallback result"

        config = _make_config(fallback_fn=fallback)
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch.object(
            type(runner), "_call_llm_completion", new_callable=AsyncMock,
        ) as mock_llm:
            result = await runner.run(ctx)

        assert result.used_fallback is True
        assert result.raw_output == "fallback result"
        assert fallback_called
        mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_flag_enabled_calls_llm(
        self, mock_gateway, mock_llm_adapter,
    ):
        """When feature flag is on, agent calls LLM."""
        config = _make_config(output_schema=SampleOutput)
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is False
        assert result.parsed_output is not None
        assert result.parsed_output.category == "bug"  # type: ignore[union-attr]


# -- Story 1.2: Provider resolution tests -----------------------------------


class TestProviderResolution:
    @pytest.mark.asyncio
    async def test_resolves_provider_from_gateway(
        self, mock_gateway, mock_llm_adapter,
    ):
        config = _make_config()
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.model_used == "test-model"

    @pytest.mark.asyncio
    async def test_no_provider_triggers_fallback(self, mock_gateway):
        """When no provider is available, fall back gracefully."""
        config = _make_config(fallback_fn=lambda ctx: "fallback")
        runner = AgentRunner(config)
        ctx = _make_context()

        with (
            patch(
                "src.agent.framework.settings",
                agent_llm_enabled={"test_agent": True},
            ),
            patch.object(
                runner, "_resolve_provider",
                side_effect=NoProviderAvailableError(ModelClass.FAST),
            ),
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is True


# -- Story 1.2: Budget check tests ------------------------------------------


class TestBudgetCheck:
    @pytest.mark.asyncio
    async def test_budget_exceeded_triggers_fallback(self, mock_gateway):
        config = _make_config(fallback_fn=lambda ctx: "budget fallback")
        runner = AgentRunner(config)
        task_id = uuid4()
        ctx = _make_context(taskpacket_id=task_id)

        with (
            patch(
                "src.agent.framework.settings",
                agent_llm_enabled={"test_agent": True},
            ),
            patch.object(
                runner, "_check_budget",
                side_effect=BudgetExceededError(str(task_id), 5.0, 1.0),
            ),
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is True
        assert result.raw_output == "budget fallback"


# -- Story 1.2: Audit recording tests ---------------------------------------


class TestAuditRecording:
    @pytest.mark.asyncio
    async def test_audit_recorded_after_llm_call(
        self, mock_gateway, mock_llm_adapter,
    ):
        config = _make_config()
        runner = AgentRunner(config)
        task_id = uuid4()
        corr_id = uuid4()
        ctx = _make_context(taskpacket_id=task_id, correlation_id=corr_id)

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            await runner.run(ctx)

        audit_store = mock_gateway["audit_store"]
        records = audit_store.query(step="test_step")
        assert len(records) == 1
        assert records[0].step == "test_step"
        assert records[0].role == "test_agent"


# -- Story 1.5: Structured output parsing tests -----------------------------


class TestOutputParsing:
    @pytest.mark.asyncio
    async def test_valid_json_parses_to_model(
        self, mock_gateway, mock_llm_adapter,
    ):
        config = _make_config(output_schema=SampleOutput)
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.parsed_output is not None
        assert isinstance(result.parsed_output, SampleOutput)
        assert result.parsed_output.category == "bug"
        assert result.parsed_output.confidence == 0.95

    @pytest.mark.asyncio
    async def test_invalid_json_triggers_fallback(
        self, mock_gateway, mock_llm_adapter,
    ):
        mock_llm_adapter.complete.return_value = LLMResponse(
            content="not json at all",
            tokens_in=10,
            tokens_out=5,
            model="test-model",
        )
        config = _make_config(
            output_schema=SampleOutput,
            fallback_fn=lambda ctx: "parse fallback",
        )
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_no_schema_returns_raw(
        self, mock_gateway, mock_llm_adapter,
    ):
        mock_llm_adapter.complete.return_value = LLMResponse(
            content="plain text response",
            tokens_in=10,
            tokens_out=5,
            model="test-model",
        )
        config = _make_config(output_schema=None)
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.parsed_output is None
        assert result.raw_output == "plain text response"


# -- Story 1.6: Fallback dispatch tests -------------------------------------


class TestFallbackDispatch:
    @pytest.mark.asyncio
    async def test_sync_fallback_fn(self, mock_gateway):
        config = _make_config(fallback_fn=lambda ctx: "sync result")
        runner = AgentRunner(config)
        ctx = _make_context()

        result = await runner.run(ctx)
        assert result.used_fallback is True
        assert result.raw_output == "sync result"

    @pytest.mark.asyncio
    async def test_async_fallback_fn(self, mock_gateway):
        async def async_fallback(ctx: AgentContext) -> str:
            return "async result"

        config = _make_config(fallback_fn=async_fallback)
        runner = AgentRunner(config)
        ctx = _make_context()

        result = await runner.run(ctx)
        assert result.used_fallback is True
        assert result.raw_output == "async result"

    @pytest.mark.asyncio
    async def test_no_fallback_fn_returns_empty(self, mock_gateway):
        config = _make_config(fallback_fn=None)
        runner = AgentRunner(config)
        ctx = _make_context()

        result = await runner.run(ctx)
        assert result.used_fallback is True
        assert result.raw_output == ""


# -- Story 1.6: System prompt building tests --------------------------------


class TestPromptBuilding:
    def test_template_rendering(self):
        config = _make_config(
            system_prompt_template="Agent: {agent_name}, Repo: {repo}",
        )
        runner = AgentRunner(config)
        ctx = _make_context(repo="my-repo")

        prompt = runner.build_system_prompt(ctx)
        assert "test_agent" in prompt
        assert "my-repo" in prompt

    def test_empty_template_uses_default(self):
        config = _make_config(system_prompt_template="")
        runner = AgentRunner(config)
        ctx = _make_context()

        prompt = runner.build_system_prompt(ctx)
        assert "test_agent" in prompt

    def test_extra_context_in_template(self):
        config = _make_config(
            system_prompt_template="Custom: {custom_key}",
        )
        runner = AgentRunner(config)
        ctx = _make_context(extra={"custom_key": "custom_value"})

        prompt = runner.build_system_prompt(ctx)
        assert "custom_value" in prompt

    def test_user_prompt_from_issue(self):
        config = _make_config()
        runner = AgentRunner(config)
        ctx = _make_context(
            issue_title="Fix the bug",
            issue_body="The bug is in module X",
        )

        prompt = runner.build_user_prompt(ctx)
        assert "Fix the bug" in prompt
        assert "module X" in prompt


# -- Story 1.6: Observability span tests ------------------------------------


class TestObservability:
    @pytest.mark.asyncio
    async def test_span_attributes_set(
        self, mock_gateway, mock_llm_adapter,
    ):
        config = _make_config()
        runner = AgentRunner(config)
        task_id = uuid4()
        ctx = _make_context(taskpacket_id=task_id)

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        # If we got here without error, spans were created.
        # The tracer is real (OTel noop in tests), so we just verify no crash.
        assert result.agent_name == "test_agent"

    @pytest.mark.asyncio
    async def test_duration_tracked(
        self, mock_gateway, mock_llm_adapter,
    ):
        config = _make_config()
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.duration_ms >= 0


# -- Story 1.4: Completion mode tests ---------------------------------------


class TestCompletionMode:
    @pytest.mark.asyncio
    async def test_completion_mode_no_tools(
        self, mock_gateway, mock_llm_adapter,
    ):
        """Agent with empty tool_allowlist uses completion mode."""
        config = _make_config(tool_allowlist=[])
        runner = AgentRunner(config)
        ctx = _make_context()

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        mock_llm_adapter.complete.assert_called_once()
        assert result.used_fallback is False


# -- Story 1.3: Agentic mode test (mocked SDK) ------------------------------


class TestAgenticMode:
    @pytest.mark.asyncio
    async def test_agentic_mode_with_tools(self, mock_gateway):
        """Agent with tool_allowlist uses agentic mode (SDK)."""
        config = _make_config(tool_allowlist=["Read", "Write", "Bash"])
        runner = AgentRunner(config)
        ctx = _make_context(extra={"repo_path": "/tmp/repo"})

        mock_response = LLMResponse(
            content="done",
            tokens_in=50,
            tokens_out=25,
            model="test-model",
        )

        with (
            patch(
                "src.agent.framework.settings",
                agent_llm_enabled={"test_agent": True},
            ),
            patch.object(
                runner, "_call_llm_agentic",
                new_callable=AsyncMock,
                return_value=mock_response,
            ) as mock_agentic,
        ):
            result = await runner.run(ctx)

        mock_agentic.assert_called_once()
        assert result.raw_output == "done"
