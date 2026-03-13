"""Tests for Sprint 19 Stream A: Model Gateway wiring into Primary Agent.

Stories A1-A6: Gateway-aware role config, budget checks, spend recording,
audit records, and fallback on provider failure.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.admin.model_gateway import (
    BudgetExceededError,
    BudgetSpec,
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelCallAudit,
    ModelClass,
    NoProviderAvailableError,
    ProviderConfig,
)
from src.agent.primary_agent import handle_loopback, implement
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TASK_ID = uuid4()
CORRELATION_ID = uuid4()
INTENT_ID = uuid4()
NOW = datetime.now(UTC)

_PA = "src.agent.primary_agent"


def _make_provider(
    model_id: str = "claude-sonnet-4-6",
    provider: str = "anthropic",
    cost: float = 0.003,
    model_class: ModelClass = ModelClass.BALANCED,
) -> ProviderConfig:
    return ProviderConfig(
        provider_id="test-provider",
        provider=provider,
        model_id=model_id,
        model_class=model_class,
        cost_per_1k_tokens=cost,
    )


@dataclass
class _FakeTaskPacket:
    id: UUID = TASK_ID
    repo: str = "owner/repo"
    issue_id: int = 1
    delivery_id: str = "d-1"
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
    goal: str = "Add a widget"
    constraints: list[str] | None = None
    acceptance_criteria: list[str] | None = None
    non_goals: list[str] | None = None
    created_at: datetime = NOW

    def __post_init__(self) -> None:
        if self.constraints is None:
            self.constraints = ["No new deps"]
        if self.acceptance_criteria is None:
            self.acceptance_criteria = ["Widget renders"]
        if self.non_goals is None:
            self.non_goals = ["Redesign"]


def _mock_gateway(
    provider: ProviderConfig | None = None,
    budget_ok: bool = True,
):
    """Return mock objects for the three gateway singletons."""
    prov = provider or _make_provider()
    router = MagicMock()
    router.select_model.return_value = prov
    router.select_with_fallback.return_value = (
        prov,
        ["escalated:strong"],
    )

    enforcer = MagicMock(spec=InMemoryBudgetEnforcer)
    enforcer.check_budget.return_value = budget_ok
    enforcer.get_budget.return_value = BudgetSpec(per_task_max_spend=5.0)
    enforcer.get_task_spend.return_value = 0.0
    enforcer.record_spend.return_value = None

    audit_store = MagicMock(spec=InMemoryModelAuditStore)
    audit_store.record.return_value = None

    return router, enforcer, audit_store


def _enter_gateway_patches(
    stack: ExitStack,
    router: MagicMock,
    enforcer: MagicMock,
    audit_store: MagicMock,
) -> None:
    """Enter the three gateway singleton patches onto an ExitStack."""
    stack.enter_context(
        patch(f"{_PA}.get_model_router", return_value=router),
    )
    stack.enter_context(
        patch(f"{_PA}.get_budget_enforcer", return_value=enforcer),
    )
    stack.enter_context(
        patch(f"{_PA}.get_model_audit_store", return_value=audit_store),
    )


def _enter_agent_patches(stack: ExitStack):
    """Enter DB + agent runner patches; return (mock_get, mock_intent, mock_run)."""
    mock_get = stack.enter_context(
        patch(f"{_PA}.get_by_id", new_callable=AsyncMock),
    )
    mock_intent = stack.enter_context(
        patch(
            f"{_PA}.get_latest_for_taskpacket",
            new_callable=AsyncMock,
        ),
    )
    stack.enter_context(
        patch(f"{_PA}.update_status", new_callable=AsyncMock),
    )
    mock_run = stack.enter_context(
        patch(f"{_PA}._run_agent", new_callable=AsyncMock),
    )
    mock_get.return_value = _FakeTaskPacket()
    mock_intent.return_value = _FakeIntent()
    mock_run.return_value = "- src/widget.py: added widget"
    return mock_get, mock_intent, mock_run


# ---------------------------------------------------------------------------
# A1: Agent calls route through gateway
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_routes_through_gateway():
    """When role_config is None, implement() uses select_model."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        result = await implement(session, TASK_ID, "/repo")

    router.select_model.assert_called_once_with(
        step="primary_agent",
        role="developer",
        overlays=None,
        repo_tier="",
        complexity="",
    )
    assert result.taskpacket_id == TASK_ID


@pytest.mark.asyncio
async def test_implement_passes_overlays_to_router():
    """Overlays, repo_tier, complexity are forwarded to select_model."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        await implement(
            session,
            TASK_ID,
            "/repo",
            overlays=["security"],
            repo_tier="execute",
            complexity="high",
        )

    router.select_model.assert_called_once_with(
        step="primary_agent",
        role="developer",
        overlays=["security"],
        repo_tier="execute",
        complexity="high",
    )


@pytest.mark.asyncio
async def test_implement_uses_explicit_role_config():
    """When role_config is provided, gateway is NOT called."""
    from src.agent.developer_role import DeveloperRoleConfig

    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()
    explicit_config = DeveloperRoleConfig(model="custom-model", max_turns=5)

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        await implement(
            session,
            TASK_ID,
            "/repo",
            role_config=explicit_config,
        )

    router.select_model.assert_not_called()


# ---------------------------------------------------------------------------
# A2: Budget check blocks over-limit calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_raises_on_budget_exceeded():
    """implement() raises BudgetExceededError when over budget."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(
        provider=provider,
        budget_ok=False,
    )
    enforcer.get_task_spend.return_value = 6.0
    enforcer.get_budget.return_value = BudgetSpec(per_task_max_spend=5.0)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        with pytest.raises(BudgetExceededError):
            await implement(session, TASK_ID, "/repo")


@pytest.mark.asyncio
async def test_handle_loopback_raises_on_budget_exceeded():
    """handle_loopback() raises BudgetExceededError when over budget."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(
        provider=provider,
        budget_ok=False,
    )
    enforcer.get_task_spend.return_value = 6.0
    session = AsyncMock()

    vr = VerificationResult(
        passed=False,
        checks=[
            CheckResult(name="ruff", passed=False, details="lint fail"),
        ],
    )

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        with pytest.raises(BudgetExceededError):
            await handle_loopback(session, TASK_ID, "/repo", vr)


# ---------------------------------------------------------------------------
# A3: Spend is recorded after agent call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_records_spend():
    """After _run_agent, record_spend is called with estimated cost."""
    provider = _make_provider(cost=0.003)
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        await implement(session, TASK_ID, "/repo")

    enforcer.record_spend.assert_called_once()
    call_kwargs = enforcer.record_spend.call_args
    assert call_kwargs.kwargs["task_id"] == str(TASK_ID)
    assert call_kwargs.kwargs["step"] == "primary_agent"
    assert call_kwargs.kwargs["cost"] > 0


# ---------------------------------------------------------------------------
# A4: Audit records are created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_creates_audit_record():
    """After _run_agent, a ModelCallAudit is recorded."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        await implement(session, TASK_ID, "/repo")

    audit_store.record.assert_called_once()
    audit: ModelCallAudit = audit_store.record.call_args[0][0]
    assert audit.step == "primary_agent"
    assert audit.role == "developer"
    assert audit.provider == provider.provider
    assert audit.model == provider.model_id
    assert audit.correlation_id == CORRELATION_ID
    assert audit.task_id == TASK_ID
    assert audit.tokens_in > 0
    assert audit.cost > 0


@pytest.mark.asyncio
async def test_handle_loopback_creates_audit_record():
    """handle_loopback() also creates an audit record."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    vr = VerificationResult(
        passed=False,
        checks=[
            CheckResult(name="ruff", passed=False, details="lint fail"),
        ],
    )

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_agent_patches(stack)

        await handle_loopback(session, TASK_ID, "/repo", vr)

    audit_store.record.assert_called_once()
    audit: ModelCallAudit = audit_store.record.call_args[0][0]
    assert audit.step == "primary_agent"


# ---------------------------------------------------------------------------
# A5: Fallback activates on provider failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_falls_back_on_no_provider():
    """When select_model fails, select_with_fallback is tried."""
    fallback_provider = _make_provider(
        model_id="claude-opus-4-6",
        model_class=ModelClass.STRONG,
        cost=0.015,
    )

    router = MagicMock()
    router.select_model.side_effect = NoProviderAvailableError(
        ModelClass.BALANCED,
    )
    router.select_with_fallback.return_value = (
        fallback_provider,
        ["balanced:exhausted", "escalated:strong"],
    )

    enforcer = MagicMock(spec=InMemoryBudgetEnforcer)
    enforcer.check_budget.return_value = True
    enforcer.get_budget.return_value = BudgetSpec(per_task_max_spend=5.0)
    enforcer.get_task_spend.return_value = 0.0

    audit_store = MagicMock(spec=InMemoryModelAuditStore)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _, _, mock_run = _enter_agent_patches(stack)
        mock_run.return_value = "done with fallback"

        result = await implement(session, TASK_ID, "/repo")

    router.select_with_fallback.assert_called_once()
    # Agent ran with fallback model
    run_call = mock_run.call_args
    role_cfg = run_call[0][3]  # 4th positional arg = role_config
    assert role_cfg.model == "claude-opus-4-6"
    assert result.agent_summary == "done with fallback"


@pytest.mark.asyncio
async def test_fallback_raises_when_all_exhausted():
    """When both select_model and fallback fail, error propagates."""
    router = MagicMock()
    router.select_model.side_effect = NoProviderAvailableError(
        ModelClass.BALANCED,
    )
    router.select_with_fallback.side_effect = NoProviderAvailableError(
        ModelClass.BALANCED,
    )

    enforcer = MagicMock(spec=InMemoryBudgetEnforcer)
    audit_store = MagicMock(spec=InMemoryModelAuditStore)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        with pytest.raises(NoProviderAvailableError):
            await implement(session, TASK_ID, "/repo")
