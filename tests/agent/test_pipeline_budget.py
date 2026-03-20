"""Unit tests for PipelineBudget (Epic 23, Story 1.12).

Tests: consumption, thread safety, exhaustion triggers,
remaining/used properties, and AgentRunner integration.
"""

from __future__ import annotations

import threading
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.adapters.llm import LLMResponse
from src.admin.model_gateway import (
    BudgetExceededError,
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    ModelRouter,
    ProviderConfig,
)
from src.agent.framework import (
    PIPELINE_BUDGET_DEFAULTS,
    AgentConfig,
    AgentContext,
    AgentRunner,
    PipelineBudget,
    get_budget_for_tier,
)

# -- Fixtures ----------------------------------------------------------------

MOCK_PROVIDER = ProviderConfig(
    provider_id="test-provider",
    provider="test",
    model_id="test-model",
    model_class=ModelClass.BALANCED,
    cost_per_1k_tokens=0.001,
)


def _make_config(**overrides: object) -> AgentConfig:
    defaults: dict[str, object] = {
        "agent_name": "test_agent",
        "pipeline_step": "test_step",
        "model_class": "fast",
        "max_budget_usd": 0.50,
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)  # type: ignore[arg-type]


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
        content="ok",
        tokens_in=100,
        tokens_out=50,
        model="test-model",
        stop_reason="end_turn",
    )
    adapter.close = AsyncMock()
    with patch("src.agent.framework.get_llm_adapter", return_value=adapter):
        yield adapter


# -- PipelineBudget unit tests -----------------------------------------------


class TestPipelineBudgetConsumption:
    """Test basic consume / remaining / used behaviour."""

    def test_consume_within_budget(self):
        budget = PipelineBudget(max_total_usd=10.0)
        assert budget.consume(3.0) is True
        assert budget.used == pytest.approx(3.0)
        assert budget.remaining == pytest.approx(7.0)

    def test_consume_exact_budget(self):
        budget = PipelineBudget(max_total_usd=5.0)
        assert budget.consume(5.0) is True
        assert budget.remaining == pytest.approx(0.0)

    def test_consume_exceeds_budget(self):
        budget = PipelineBudget(max_total_usd=2.0)
        assert budget.consume(3.0) is False
        # Nothing was deducted
        assert budget.used == pytest.approx(0.0)
        assert budget.remaining == pytest.approx(2.0)

    def test_multiple_consumes(self):
        budget = PipelineBudget(max_total_usd=5.0)
        assert budget.consume(2.0) is True
        assert budget.consume(2.0) is True
        assert budget.consume(2.0) is False  # would exceed
        assert budget.used == pytest.approx(4.0)
        assert budget.remaining == pytest.approx(1.0)


class TestPipelineBudgetProperties:
    """Test remaining and used properties."""

    def test_initial_state(self):
        budget = PipelineBudget(max_total_usd=10.0)
        assert budget.used == pytest.approx(0.0)
        assert budget.remaining == pytest.approx(10.0)
        assert budget.max_total_usd == pytest.approx(10.0)

    def test_remaining_never_negative(self):
        budget = PipelineBudget(max_total_usd=1.0)
        budget.consume(1.0)
        assert budget.remaining == pytest.approx(0.0)

    def test_used_tracks_cumulative(self):
        budget = PipelineBudget(max_total_usd=10.0)
        budget.consume(1.5)
        budget.consume(2.5)
        assert budget.used == pytest.approx(4.0)


class TestPipelineBudgetThreadSafety:
    """Test that concurrent consume calls are thread-safe."""

    def test_concurrent_consume(self):
        budget = PipelineBudget(max_total_usd=10.0)
        results: list[bool] = []
        lock = threading.Lock()

        def consume_one() -> None:
            ok = budget.consume(0.1)
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=consume_one) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 100 should succeed (100 * 0.1 = 10.0)
        successes = sum(1 for r in results if r)
        assert successes == 100
        assert budget.used == pytest.approx(10.0)
        assert budget.remaining == pytest.approx(0.0)

    def test_concurrent_reads(self):
        budget = PipelineBudget(max_total_usd=5.0)
        budget.consume(2.0)

        errors: list[Exception] = []

        def read_props() -> None:
            try:
                _ = budget.remaining
                _ = budget.used
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=read_props) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


class TestPipelineBudgetExhaustion:
    """Test that exhaustion is detected correctly."""

    def test_exhausted_after_full_spend(self):
        budget = PipelineBudget(max_total_usd=1.0)
        assert budget.consume(1.0) is True
        assert budget.consume(0.01) is False

    def test_exhausted_returns_false_repeatedly(self):
        budget = PipelineBudget(max_total_usd=0.5)
        budget.consume(0.5)
        assert budget.consume(0.1) is False
        assert budget.consume(0.1) is False


class TestPipelineBudgetDefaults:
    """Test the Appendix D defaults constant."""

    def test_observe_tier(self):
        assert PIPELINE_BUDGET_DEFAULTS["observe"] == pytest.approx(5.00)

    def test_suggest_tier(self):
        assert PIPELINE_BUDGET_DEFAULTS["suggest"] == pytest.approx(8.50)

    def test_execute_tier(self):
        assert PIPELINE_BUDGET_DEFAULTS["execute"] == pytest.approx(10.00)


# -- AgentRunner integration -------------------------------------------------


class TestAgentRunnerPipelineBudget:
    """Test that AgentRunner.run() checks pipeline_budget before calling LLM."""

    @pytest.mark.asyncio
    async def test_pipeline_budget_exhausted_raises_error(
        self,
        mock_gateway,
        mock_llm_adapter,
    ):
        """When pipeline budget is exhausted, BudgetExceededError is raised (Story 32.8)."""
        budget = PipelineBudget(max_total_usd=0.10)
        # Pre-spend most of the budget
        budget.consume(0.10)

        config = _make_config(
            max_budget_usd=0.50,
            fallback_fn=lambda ctx: "budget fallback",
        )
        runner = AgentRunner(config)
        ctx = AgentContext(pipeline_budget=budget)

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            with pytest.raises(BudgetExceededError) as exc_info:
                await runner.run(ctx)

        assert exc_info.value.step == "test_step"
        assert exc_info.value.current_spend == pytest.approx(0.10)
        assert exc_info.value.limit == pytest.approx(0.10)
        mock_llm_adapter.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_budget_available_allows_llm(
        self,
        mock_gateway,
        mock_llm_adapter,
    ):
        """When pipeline budget has room, agent proceeds to LLM."""
        budget = PipelineBudget(max_total_usd=10.0)
        config = _make_config(max_budget_usd=0.50)
        runner = AgentRunner(config)
        ctx = AgentContext(pipeline_budget=budget)

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is False
        assert budget.used == pytest.approx(0.50)

    @pytest.mark.asyncio
    async def test_no_pipeline_budget_skips_check(
        self,
        mock_gateway,
        mock_llm_adapter,
    ):
        """When pipeline_budget is None, the check is skipped entirely."""
        config = _make_config()
        runner = AgentRunner(config)
        ctx = AgentContext(pipeline_budget=None)

        with patch(
            "src.agent.framework.settings",
            agent_llm_enabled={"test_agent": True},
        ):
            result = await runner.run(ctx)

        assert result.used_fallback is False

    @pytest.mark.asyncio
    async def test_pipeline_budget_checked_after_per_agent_budget(
        self,
        mock_gateway,
        mock_llm_adapter,
    ):
        """Pipeline budget check happens after per-agent budget check."""
        budget = PipelineBudget(max_total_usd=100.0)
        config = _make_config(
            max_budget_usd=0.50,
            fallback_fn=lambda ctx: "per-agent fallback",
        )
        runner = AgentRunner(config)
        task_id = uuid4()
        ctx = AgentContext(taskpacket_id=task_id, pipeline_budget=budget)

        with (
            patch(
                "src.agent.framework.settings",
                agent_llm_enabled={"test_agent": True},
            ),
            patch.object(
                runner,
                "_check_budget",
                side_effect=BudgetExceededError(str(task_id), 5.0, 1.0),
            ),
        ):
            result = await runner.run(ctx)

        # Per-agent budget triggered first; pipeline budget not consumed
        assert result.used_fallback is True
        assert budget.used == pytest.approx(0.0)


# -- Story 32.6: get_budget_for_tier tests ----------------------------------


class TestGetBudgetForTier:
    """Test that get_budget_for_tier returns settings caps when enabled."""

    def test_returns_defaults_when_routing_disabled(self):
        """When cost_optimization_routing_enabled=False, use PIPELINE_BUDGET_DEFAULTS."""
        with patch(
            "src.agent.framework.settings",
            cost_optimization_routing_enabled=False,
            cost_optimization_budget_tiers={"observe": 2.00, "suggest": 5.00, "execute": 8.00},
        ):
            assert get_budget_for_tier("observe") == pytest.approx(5.00)
            assert get_budget_for_tier("suggest") == pytest.approx(8.50)
            assert get_budget_for_tier("execute") == pytest.approx(10.00)

    def test_returns_settings_caps_when_routing_enabled(self):
        """When cost_optimization_routing_enabled=True, use settings budget tiers."""
        with patch(
            "src.agent.framework.settings",
            cost_optimization_routing_enabled=True,
            cost_optimization_budget_tiers={"observe": 2.00, "suggest": 5.00, "execute": 8.00},
        ):
            assert get_budget_for_tier("observe") == pytest.approx(2.00)
            assert get_budget_for_tier("suggest") == pytest.approx(5.00)
            assert get_budget_for_tier("execute") == pytest.approx(8.00)

    def test_unknown_tier_returns_default_fallback(self):
        """Unknown tier falls back to $5.00 default."""
        with patch(
            "src.agent.framework.settings",
            cost_optimization_routing_enabled=True,
            cost_optimization_budget_tiers={"observe": 2.00},
        ):
            assert get_budget_for_tier("unknown_tier") == pytest.approx(5.00)

    def test_unknown_tier_routing_disabled(self):
        """Unknown tier with routing disabled also falls back to $5.00."""
        with patch(
            "src.agent.framework.settings",
            cost_optimization_routing_enabled=False,
        ):
            assert get_budget_for_tier("unknown_tier") == pytest.approx(5.00)


# -- Story 32.8: BudgetExceededError step attribute tests -------------------


class TestBudgetExceededErrorStep:
    """Test that BudgetExceededError carries step information."""

    def test_step_attribute(self):
        err = BudgetExceededError("task-1", 3.50, 5.00, step="intent")
        assert err.step == "intent"
        assert err.task_id == "task-1"
        assert err.current_spend == pytest.approx(3.50)
        assert err.limit == pytest.approx(5.00)
        assert "intent" in str(err)

    def test_step_none_by_default(self):
        err = BudgetExceededError("task-2", 1.00, 2.00)
        assert err.step is None
        assert "step" not in str(err)

    def test_error_message_format(self):
        err = BudgetExceededError("task-3", 4.50, 5.00, step="assembler")
        assert "at step 'assembler'" in str(err)
        assert "$4.5000" in str(err)
        assert "$5.0000" in str(err)


# -- Story 32.16: batch_eligible config flag --------------------------------


class TestBatchEligible:
    """Test that AgentConfig.batch_eligible defaults to False."""

    def test_default_is_false(self):
        config = AgentConfig(agent_name="test", pipeline_step="intent")
        assert config.batch_eligible is False

    def test_can_be_set_true(self):
        config = AgentConfig(
            agent_name="test", pipeline_step="context", batch_eligible=True,
        )
        assert config.batch_eligible is True

    def test_context_agent_is_batch_eligible(self):
        from src.context.context_config import CONTEXT_AGENT_CONFIG
        assert CONTEXT_AGENT_CONFIG.batch_eligible is True

    def test_interactive_agents_not_batch_eligible(self):
        """Interactive agents (intent, primary, qa) should not be batch eligible."""
        from src.intent.intent_config import INTENT_AGENT_CONFIG
        from src.qa.qa_config import QA_AGENT_CONFIG
        assert INTENT_AGENT_CONFIG.batch_eligible is False
        assert QA_AGENT_CONFIG.batch_eligible is False


# -- Story 32.17: Batch cost discount in audit recording --------------------


class TestBatchCostDiscount:
    """Test that batch calls get 50% cost discount when flag is enabled."""

    def test_record_audit_batch_discount(self, mock_gateway):
        """When batch=True and batch_enabled, cost is halved."""
        config = _make_config()
        runner = AgentRunner(config)
        ctx = AgentContext()

        with patch(
            "src.agent.framework.settings",
            cost_optimization_batch_enabled=True,
        ):
            runner._record_audit(
                context=ctx,
                provider=MOCK_PROVIDER,
                tokens_in=100,
                tokens_out=50,
                cost=0.10,
                batch=True,
            )

        audit_store = mock_gateway["audit_store"]
        records = audit_store.query()
        assert len(records) == 1
        assert records[0].batch is True
        assert records[0].cost == pytest.approx(0.05)  # 50% discount

    def test_record_audit_no_discount_when_flag_off(self, mock_gateway):
        """When batch=True but flag disabled, no discount."""
        config = _make_config()
        runner = AgentRunner(config)
        ctx = AgentContext()

        with patch(
            "src.agent.framework.settings",
            cost_optimization_batch_enabled=False,
        ):
            runner._record_audit(
                context=ctx,
                provider=MOCK_PROVIDER,
                tokens_in=100,
                tokens_out=50,
                cost=0.10,
                batch=True,
            )

        audit_store = mock_gateway["audit_store"]
        records = audit_store.query()
        assert len(records) == 1
        assert records[0].batch is True
        assert records[0].cost == pytest.approx(0.10)  # No discount

    def test_record_audit_no_discount_when_not_batch(self, mock_gateway):
        """When batch=False, no discount regardless of flag."""
        config = _make_config()
        runner = AgentRunner(config)
        ctx = AgentContext()

        with patch(
            "src.agent.framework.settings",
            cost_optimization_batch_enabled=True,
        ):
            runner._record_audit(
                context=ctx,
                provider=MOCK_PROVIDER,
                tokens_in=100,
                tokens_out=50,
                cost=0.10,
                batch=False,
            )

        audit_store = mock_gateway["audit_store"]
        records = audit_store.query()
        assert len(records) == 1
        assert records[0].batch is False
        assert records[0].cost == pytest.approx(0.10)
