"""Integration tests: Primary Agent through AgentRunner framework (Epic 23, Story 1.10).

End-to-end tests that let the full AgentRunner lifecycle execute:
  implement() → AgentRunner.run() → provider resolution → budget check →
  prompt build → LLM call → audit recording → evidence bundle

Only the LLM call itself and the DB layer are mocked. Everything else
(gateway routing, budget enforcement, audit store, prompt building,
evidence construction) runs for real via in-memory implementations.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.adapters.llm import LLMResponse
from src.admin.model_gateway import (
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    ModelRouter,
    ProviderConfig,
)
from src.agent.primary_agent import handle_loopback, implement
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

TASK_ID = uuid4()
CORRELATION_ID = uuid4()
INTENT_ID = uuid4()
NOW = datetime.now(UTC)

_PA = "src.agent.primary_agent"
_FW = "src.agent.framework"

PROVIDER = ProviderConfig(
    provider_id="integration-provider",
    provider="anthropic",
    model_id="claude-sonnet-4-6",
    model_class=ModelClass.BALANCED,
    cost_per_1k_tokens=0.003,
)

LLM_RESPONSE = LLMResponse(
    content="- src/widget.py: added widget component\n- tests/test_widget.py: added tests",
    tokens_in=150,
    tokens_out=80,
    model="claude-sonnet-4-6",
    stop_reason="end_turn",
)

# ---------------------------------------------------------------------------
# Fake domain objects (DB layer is mocked, these are returned)
# ---------------------------------------------------------------------------


@dataclass
class _FakeTaskPacket:
    id: UUID = TASK_ID
    repo: str = "owner/repo"
    issue_id: int = 42
    delivery_id: str = "d-42"
    correlation_id: UUID = CORRELATION_ID
    status: str = "intent_built"
    scope: dict | None = None
    risk_flags: dict | None = None
    complexity_index: dict | None = None
    context_packs: list | None = None
    intent_spec_id: UUID | None = None
    intent_version: int | None = None
    loopback_count: int = 0
    created_at: datetime = NOW
    updated_at: datetime = NOW


@dataclass
class _FakeIntent:
    id: UUID = INTENT_ID
    taskpacket_id: UUID = TASK_ID
    version: int = 1
    goal: str = "Add a widget component"
    constraints: list[str] | None = None
    acceptance_criteria: list[str] | None = None
    non_goals: list[str] | None = None
    created_at: datetime = NOW

    def __post_init__(self) -> None:
        if self.constraints is None:
            self.constraints = ["No new dependencies"]
        if self.acceptance_criteria is None:
            self.acceptance_criteria = ["Widget renders correctly"]
        if self.non_goals is None:
            self.non_goals = ["Redesign existing UI"]


# ---------------------------------------------------------------------------
# Fixtures: real gateway components (in-memory), mocked LLM + DB
# ---------------------------------------------------------------------------


@pytest.fixture
def gateway():
    """Real in-memory gateway components for integration testing."""
    router = ModelRouter(providers=[PROVIDER])
    enforcer = InMemoryBudgetEnforcer()
    audit_store = InMemoryModelAuditStore()
    return router, enforcer, audit_store



def _enter_integration_patches(
    stack: ExitStack,
    router: ModelRouter,
    enforcer: InMemoryBudgetEnforcer,
    audit_store: InMemoryModelAuditStore,
    llm_response: LLMResponse = LLM_RESPONSE,
) -> tuple[AsyncMock, AsyncMock]:
    """Wire up real gateway + mock LLM (agentic mode) + mock DB.

    Returns (mock_get, mock_intent).
    Primary Agent has tools → uses agentic mode → we mock _call_llm_agentic.
    """
    # Gateway patches — real in-memory implementations
    stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
    stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
    stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))

    # Mock the agentic LLM call (Primary Agent has tools → agentic mode)
    stack.enter_context(
        patch(
            f"{_FW}.AgentRunner._call_llm_agentic",
            new_callable=AsyncMock,
            return_value=llm_response,
        ),
    )

    # Feature flag — enable developer agent
    stack.enter_context(
        patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
    )

    # DB patches — mock
    mock_get = stack.enter_context(patch(f"{_PA}.get_by_id", new_callable=AsyncMock))
    mock_intent = stack.enter_context(
        patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock),
    )
    stack.enter_context(patch(f"{_PA}.update_status", new_callable=AsyncMock))

    mock_get.return_value = _FakeTaskPacket()
    mock_intent.return_value = _FakeIntent()

    return mock_get, mock_intent


def _enter_db_patches(stack: ExitStack) -> tuple[AsyncMock, AsyncMock]:
    """Enter DB patches only. Returns (mock_get, mock_intent)."""
    mock_get = stack.enter_context(patch(f"{_PA}.get_by_id", new_callable=AsyncMock))
    mock_intent = stack.enter_context(
        patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock),
    )
    stack.enter_context(patch(f"{_PA}.update_status", new_callable=AsyncMock))

    mock_get.return_value = _FakeTaskPacket()
    mock_intent.return_value = _FakeIntent()
    return mock_get, mock_intent


# ---------------------------------------------------------------------------
# Integration test: implement() end-to-end
# ---------------------------------------------------------------------------


class TestImplementIntegration:
    """End-to-end: implement() → AgentRunner lifecycle → EvidenceBundle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_produces_evidence(self, gateway):
        """implement() flows through the full AgentRunner lifecycle and
        produces a valid EvidenceBundle with correct fields."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        with ExitStack() as stack:
            _enter_integration_patches(stack, router, enforcer, audit_store)
            evidence = await implement(session, TASK_ID, "/tmp/repo")

        # Evidence bundle is correct
        assert evidence.taskpacket_id == TASK_ID
        assert evidence.intent_version == 1
        assert evidence.files_changed == ["src/widget.py", "tests/test_widget.py"]
        assert "added widget" in evidence.agent_summary
        assert evidence.loopback_attempt == 0

    @pytest.mark.asyncio
    async def test_gateway_selects_model(self, gateway):
        """The Model Gateway's select_model is called by the framework
        (not bypassed) to resolve the provider."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        with ExitStack() as stack:
            _enter_integration_patches(stack, router, enforcer, audit_store)

            # Spy on router.select_model
            original_select = router.select_model
            select_calls: list[dict] = []

            def spy_select(**kwargs):
                select_calls.append(kwargs)
                return original_select(**kwargs)

            router.select_model = spy_select

            await implement(session, TASK_ID, "/tmp/repo")

        assert len(select_calls) == 1
        assert select_calls[0]["step"] == "primary_agent"
        assert select_calls[0]["role"] == "developer"

    @pytest.mark.asyncio
    async def test_audit_record_created(self, gateway):
        """After the LLM call, the framework creates an audit record
        with correct correlation_id, task_id, step, provider, and cost."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        with ExitStack() as stack:
            _enter_integration_patches(stack, router, enforcer, audit_store)
            await implement(session, TASK_ID, "/tmp/repo")

        records = audit_store.query(step="primary_agent")
        assert len(records) == 1

        audit = records[0]
        assert audit.step == "primary_agent"
        assert audit.role == "developer"
        assert audit.provider == "anthropic"
        assert audit.model == "claude-sonnet-4-6"
        assert audit.correlation_id == CORRELATION_ID
        assert audit.task_id == TASK_ID
        assert audit.tokens_in == 150
        assert audit.tokens_out == 80
        assert audit.cost > 0

    @pytest.mark.asyncio
    async def test_spend_recorded(self, gateway):
        """After the LLM call, the framework records spend on the budget enforcer."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        with ExitStack() as stack:
            _enter_integration_patches(stack, router, enforcer, audit_store)
            await implement(session, TASK_ID, "/tmp/repo")

        task_spend = enforcer.get_task_spend(str(TASK_ID))
        assert task_spend > 0

    @pytest.mark.asyncio
    async def test_llm_receives_correct_prompts(self, gateway):
        """The agentic LLM call receives system and user prompts
        built from the IntentSpec and TaskPacket."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()
        captured_calls: list[tuple] = []

        async def capture_agentic(self, system, user, context, provider):
            captured_calls.append((system, user))
            return LLM_RESPONSE

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )
            stack.enter_context(
                patch(f"{_FW}.AgentRunner._call_llm_agentic", capture_agentic),
            )
            mock_get, mock_intent = _enter_db_patches(stack)

            await implement(session, TASK_ID, "/tmp/repo")

        assert len(captured_calls) == 1
        system, user = captured_calls[0]
        assert "Add a widget component" in system
        assert "No new dependencies" in system
        assert "Add a widget component" in user

    @pytest.mark.asyncio
    async def test_agentic_mode_invoked_for_tool_agent(self, gateway):
        """Primary Agent (with tools) uses agentic mode, not completion mode."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        agentic_response = LLMResponse(
            content="- src/widget.py: added widget",
            tokens_in=100,
            tokens_out=50,
            model="claude-sonnet-4-6",
            stop_reason="end_turn",
        )

        with ExitStack() as stack:
            # Gateway
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )

            # Mock _call_llm_agentic (the SDK call) directly
            mock_agentic = stack.enter_context(
                patch(
                    f"{_FW}.AgentRunner._call_llm_agentic",
                    new_callable=AsyncMock,
                    return_value=agentic_response,
                ),
            )

            # DB
            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket()

            evidence = await implement(session, TASK_ID, "/tmp/repo")

        # Agentic mode was called (not completion mode)
        mock_agentic.assert_called_once()
        # Verify system prompt contains intent content
        call_args = mock_agentic.call_args
        system_prompt = call_args[0][0]
        assert "Add a widget component" in system_prompt
        assert "No new dependencies" in system_prompt

    @pytest.mark.asyncio
    async def test_overlays_and_complexity_flow_through(self, gateway):
        """Overlays, repo_tier, and complexity pass from implement()
        through AgentContext to the gateway."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        agentic_response = LLMResponse(
            content="- src/widget.py: done",
            tokens_in=100,
            tokens_out=50,
            model="claude-sonnet-4-6",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )

            # Spy on select_model to capture args
            original_select = router.select_model
            captured: list[dict] = []

            def spy(**kwargs):
                captured.append(kwargs)
                return original_select(**kwargs)

            router.select_model = spy

            stack.enter_context(
                patch(
                    f"{_FW}.AgentRunner._call_llm_agentic",
                    new_callable=AsyncMock,
                    return_value=agentic_response,
                ),
            )
            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket()

            await implement(
                session, TASK_ID, "/tmp/repo",
                overlays=["security"],
                repo_tier="execute",
                complexity="high",
            )

        assert len(captured) == 1
        assert captured[0]["overlays"] == ["security"]
        assert captured[0]["repo_tier"] == "execute"
        assert captured[0]["complexity"] == "high"


# ---------------------------------------------------------------------------
# Integration test: handle_loopback() end-to-end
# ---------------------------------------------------------------------------


class TestHandleLoopbackIntegration:
    """End-to-end: handle_loopback() → AgentRunner lifecycle → EvidenceBundle."""

    @pytest.fixture
    def verification_failure(self):
        return VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="ruff", passed=False, details="E501 line too long"),
                CheckResult(name="pytest", passed=True, details="12 passed"),
            ],
        )

    @pytest.mark.asyncio
    async def test_loopback_full_lifecycle(self, gateway, verification_failure):
        """handle_loopback() flows through AgentRunner and produces evidence."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        loopback_response = LLMResponse(
            content="- src/widget.py: fixed line length",
            tokens_in=200,
            tokens_out=60,
            model="claude-sonnet-4-6",
            stop_reason="end_turn",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )
            stack.enter_context(
                patch(
                    f"{_FW}.AgentRunner._call_llm_agentic",
                    new_callable=AsyncMock,
                    return_value=loopback_response,
                ),
            )

            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket(loopback_count=2)

            evidence = await handle_loopback(
                session, TASK_ID, "/tmp/repo", verification_failure,
            )

        assert evidence.taskpacket_id == TASK_ID
        assert evidence.loopback_attempt == 2
        assert "fixed line length" in evidence.agent_summary

    @pytest.mark.asyncio
    async def test_loopback_audit_recorded(self, gateway, verification_failure):
        """handle_loopback() also produces an audit record."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        loopback_response = LLMResponse(
            content="- src/widget.py: fixed",
            tokens_in=200,
            tokens_out=60,
            model="claude-sonnet-4-6",
            stop_reason="end_turn",
        )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )
            stack.enter_context(
                patch(
                    f"{_FW}.AgentRunner._call_llm_agentic",
                    new_callable=AsyncMock,
                    return_value=loopback_response,
                ),
            )

            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket(loopback_count=1)

            await handle_loopback(
                session, TASK_ID, "/tmp/repo", verification_failure,
            )

        records = audit_store.query(step="primary_agent")
        assert len(records) == 1
        assert records[0].role == "developer"
        assert records[0].correlation_id == CORRELATION_ID

    @pytest.mark.asyncio
    async def test_loopback_includes_failure_in_prompt(
        self, gateway, verification_failure,
    ):
        """handle_loopback() passes verification failures to the LLM prompt."""
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        captured_prompts: list[str] = []

        async def capture_agentic(self, system, user, context, provider):
            captured_prompts.append(user)
            return LLMResponse(
                content="- src/widget.py: fixed",
                tokens_in=100, tokens_out=50,
                model="claude-sonnet-4-6",
            )

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))
            stack.enter_context(
                patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
            )
            stack.enter_context(
                patch(
                    f"{_FW}.AgentRunner._call_llm_agentic",
                    capture_agentic,
                ),
            )

            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket(loopback_count=1)

            await handle_loopback(
                session, TASK_ID, "/tmp/repo", verification_failure,
            )

        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "ruff" in prompt
        assert "FAILED" in prompt
        assert "E501 line too long" in prompt
        assert "loopback attempt 1" in prompt


# ---------------------------------------------------------------------------
# Integration: feature flag off → fallback (no LLM call)
# ---------------------------------------------------------------------------


class TestFeatureFlagIntegration:
    """When the developer flag is off, the full pipeline falls back
    without calling the LLM — but still returns a valid EvidenceBundle."""

    @pytest.mark.asyncio
    async def test_flag_off_skips_llm_returns_evidence(self, gateway):
        router, enforcer, audit_store = gateway
        session = AsyncMock()

        with ExitStack() as stack:
            stack.enter_context(patch(f"{_FW}.get_model_router", return_value=router))
            stack.enter_context(patch(f"{_FW}.get_budget_enforcer", return_value=enforcer))
            stack.enter_context(patch(f"{_FW}.get_model_audit_store", return_value=audit_store))

            # Feature flag OFF (default — no agent_llm_enabled entry)
            mock_get = stack.enter_context(
                patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
            )
            stack.enter_context(
                patch(f"{_PA}.get_latest_for_taskpacket", new_callable=AsyncMock,
                      return_value=_FakeIntent()),
            )
            stack.enter_context(
                patch(f"{_PA}.update_status", new_callable=AsyncMock),
            )
            mock_get.return_value = _FakeTaskPacket()

            evidence = await implement(session, TASK_ID, "/tmp/repo")

        # Evidence is returned (empty, from fallback) — no crash
        assert evidence.taskpacket_id == TASK_ID
        # No audit record since LLM was never called
        records = audit_store.query(step="primary_agent")
        assert len(records) == 0
