"""Tests for Primary Agent using the Unified Agent Framework (AgentRunner).

Story 1.8: Verifies that implement() and handle_loopback() use AgentRunner
instead of direct gateway/SDK calls. Gateway integration (provider resolution,
budget, audit) is now handled by the framework; these tests verify the
Primary Agent correctly builds AgentContext and converts AgentResult to
EvidenceBundle.

Original coverage (Sprint 19 Stream A stories A1-A6) is preserved via
framework-level mocking.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.admin.model_gateway import (
    BudgetSpec,
    InMemoryBudgetEnforcer,
    InMemoryModelAuditStore,
    ModelClass,
    NoProviderAvailableError,
    ProviderConfig,
)
from src.agent.framework import AgentResult
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
_FW = "src.agent.framework"


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


def _make_agent_result(raw_output: str = "- src/widget.py: added widget") -> AgentResult:
    """Create a mock AgentResult matching what AgentRunner.run() returns."""
    return AgentResult(
        agent_name="developer",
        raw_output=raw_output,
        model_used="claude-sonnet-4-6",
        tokens_in=100,
        tokens_out=50,
        cost_estimated=0.0003,
        duration_ms=500,
        used_fallback=False,
    )


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
    """Enter gateway patches on the FRAMEWORK module (where AgentRunner calls them)."""
    stack.enter_context(
        patch(f"{_FW}.get_model_router", return_value=router),
    )
    stack.enter_context(
        patch(f"{_FW}.get_budget_enforcer", return_value=enforcer),
    )
    stack.enter_context(
        patch(f"{_FW}.get_model_audit_store", return_value=audit_store),
    )


def _enter_db_patches(stack: ExitStack):
    """Enter DB patches; return (mock_get, mock_intent)."""
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
    mock_get.return_value = _FakeTaskPacket()
    mock_intent.return_value = _FakeIntent()
    return mock_get, mock_intent


def _enter_runner_patch(stack: ExitStack, result: AgentResult | None = None):
    """Patch PrimaryAgentRunner.run to return a canned AgentResult."""
    mock_run = stack.enter_context(
        patch(
            f"{_PA}.PrimaryAgentRunner.run",
            new_callable=AsyncMock,
        ),
    )
    mock_run.return_value = result or _make_agent_result()
    return mock_run


# ---------------------------------------------------------------------------
# A1: Agent calls route through AgentRunner (which uses gateway)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_uses_agent_runner():
    """implement() delegates to PrimaryAgentRunner.run()."""
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_db_patches(stack)
        mock_run = _enter_runner_patch(stack)

        result = await implement(session, TASK_ID, "/repo")

    mock_run.assert_called_once()
    assert result.taskpacket_id == TASK_ID
    assert result.agent_summary == "- src/widget.py: added widget"


@pytest.mark.asyncio
async def test_implement_passes_context_to_runner():
    """implement() builds AgentContext with overlays, repo_tier, complexity."""
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_db_patches(stack)
        mock_run = _enter_runner_patch(stack)

        await implement(
            session,
            TASK_ID,
            "/repo",
            overlays=["security"],
            repo_tier="execute",
            complexity="high",
        )

    ctx = mock_run.call_args[0][0]  # First positional arg = AgentContext
    assert ctx.overlays == ["security"]
    assert ctx.repo_tier == "execute"
    assert ctx.complexity == "high"
    assert ctx.extra["repo_path"] == "/repo"


@pytest.mark.asyncio
async def test_implement_with_explicit_role_config():
    """When role_config is provided, AgentConfig uses its values."""
    from src.agent.developer_role import DeveloperRoleConfig

    session = AsyncMock()
    explicit_config = DeveloperRoleConfig(model="custom-model", max_turns=5)

    with ExitStack() as stack:
        _enter_db_patches(stack)
        _enter_runner_patch(stack)

        # Patch _make_developer_config to verify it receives the role_config
        with patch(f"{_PA}._make_developer_config") as mock_make_config:
            mock_make_config.return_value = MagicMock()
            await implement(
                session,
                TASK_ID,
                "/repo",
                role_config=explicit_config,
            )

        mock_make_config.assert_called_once_with(explicit_config)


# ---------------------------------------------------------------------------
# A1 (framework level): Gateway routing verified through framework
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_routes_through_gateway_via_framework():
    """When using the framework, select_model is called by AgentRunner."""
    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_db_patches(stack)
        # Enable the feature flag so the runner actually calls the LLM path
        stack.enter_context(
            patch(
                f"{_FW}.settings",
                agent_llm_enabled={"developer": True},
            ),
        )
        # Mock the agentic LLM call (SDK) to return a result
        stack.enter_context(
            patch(
                f"{_FW}.AgentRunner._call_llm_agentic",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    content="- src/widget.py: added widget",
                    tokens_in=100,
                    tokens_out=50,
                    model="claude-sonnet-4-6",
                    stop_reason="end_turn",
                ),
            ),
        )

        result = await implement(session, TASK_ID, "/repo")

    router.select_model.assert_called_once()
    assert result.taskpacket_id == TASK_ID


# ---------------------------------------------------------------------------
# A2: Budget check (now handled gracefully by framework fallback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_budget_exceeded_uses_fallback():
    """When budget is exceeded, framework falls back gracefully."""
    session = AsyncMock()
    fallback_result = _make_agent_result(raw_output="")
    fallback_result.used_fallback = True
    fallback_result.model_used = "fallback"

    with ExitStack() as stack:
        _enter_db_patches(stack)
        mock_run = _enter_runner_patch(stack, result=fallback_result)

        result = await implement(session, TASK_ID, "/repo")

    # Agent ran (via fallback) and returned evidence
    assert result.taskpacket_id == TASK_ID
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_handle_loopback_budget_exceeded_uses_fallback():
    """handle_loopback() also falls back gracefully on budget exceeded."""
    session = AsyncMock()
    fallback_result = _make_agent_result(raw_output="")
    fallback_result.used_fallback = True

    vr = VerificationResult(
        passed=False,
        checks=[
            CheckResult(name="ruff", passed=False, details="lint fail"),
        ],
    )

    with ExitStack() as stack:
        _enter_db_patches(stack)
        _enter_runner_patch(stack, result=fallback_result)

        result = await handle_loopback(session, TASK_ID, "/repo", vr)

    assert result.taskpacket_id == TASK_ID


# ---------------------------------------------------------------------------
# A3: Spend is recorded (via framework audit)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_records_spend_via_framework():
    """After LLM call, the framework records spend."""
    provider = _make_provider(cost=0.003)
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_db_patches(stack)
        stack.enter_context(
            patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
        )
        stack.enter_context(
            patch(
                f"{_FW}.AgentRunner._call_llm_agentic",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    content="- src/widget.py: added widget",
                    tokens_in=100,
                    tokens_out=50,
                    model="claude-sonnet-4-6",
                    stop_reason="end_turn",
                ),
            ),
        )

        await implement(session, TASK_ID, "/repo")

    enforcer.record_spend.assert_called_once()
    call_kwargs = enforcer.record_spend.call_args
    assert call_kwargs.kwargs["task_id"] == str(TASK_ID)
    assert call_kwargs.kwargs["step"] == "primary_agent"
    assert call_kwargs.kwargs["cost"] > 0


# ---------------------------------------------------------------------------
# A4: Audit records are created (via framework)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_creates_audit_record_via_framework():
    """After LLM call, the framework creates an audit record."""
    from src.admin.model_gateway import ModelCallAudit

    provider = _make_provider()
    router, enforcer, audit_store = _mock_gateway(provider=provider)
    session = AsyncMock()

    with ExitStack() as stack:
        _enter_gateway_patches(stack, router, enforcer, audit_store)
        _enter_db_patches(stack)
        stack.enter_context(
            patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
        )
        stack.enter_context(
            patch(
                f"{_FW}.AgentRunner._call_llm_agentic",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    content="done",
                    tokens_in=100,
                    tokens_out=50,
                    model="claude-sonnet-4-6",
                    stop_reason="end_turn",
                ),
            ),
        )

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
async def test_handle_loopback_creates_audit_record_via_framework():
    """handle_loopback() also creates an audit record via the framework."""
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
        _enter_db_patches(stack)
        stack.enter_context(
            patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
        )
        stack.enter_context(
            patch(
                f"{_FW}.AgentRunner._call_llm_agentic",
                new_callable=AsyncMock,
                return_value=MagicMock(
                    content="done",
                    tokens_in=100,
                    tokens_out=50,
                    model="claude-sonnet-4-6",
                    stop_reason="end_turn",
                ),
            ),
        )

        await handle_loopback(session, TASK_ID, "/repo", vr)

    audit_store.record.assert_called_once()


# ---------------------------------------------------------------------------
# A5: Fallback activates on provider failure (via framework)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_falls_back_on_no_provider_via_framework():
    """When all providers fail, the framework uses fallback."""
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
        _enter_db_patches(stack)
        stack.enter_context(
            patch(f"{_FW}.settings", agent_llm_enabled={"developer": True}),
        )

        # Framework falls back gracefully instead of raising
        result = await implement(session, TASK_ID, "/repo")

    # Evidence bundle is returned (with empty summary from fallback)
    assert result.taskpacket_id == TASK_ID
    assert result.agent_summary == ""


# ---------------------------------------------------------------------------
# Evidence bundle construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_implement_builds_evidence_bundle():
    """implement() constructs EvidenceBundle from AgentResult."""
    session = AsyncMock()
    agent_result = _make_agent_result(
        raw_output="- src/widget.py: added widget\n- tests/test_widget.py: added tests",
    )

    with ExitStack() as stack:
        _enter_db_patches(stack)
        _enter_runner_patch(stack, result=agent_result)

        evidence = await implement(session, TASK_ID, "/repo")

    assert evidence.taskpacket_id == TASK_ID
    assert evidence.intent_version == 1
    assert evidence.files_changed == ["src/widget.py", "tests/test_widget.py"]
    assert "added widget" in evidence.agent_summary


@pytest.mark.asyncio
async def test_handle_loopback_builds_evidence_bundle():
    """handle_loopback() constructs EvidenceBundle with loopback context."""
    session = AsyncMock()

    vr = VerificationResult(
        passed=False,
        checks=[
            CheckResult(name="ruff", passed=False, details="lint fail"),
        ],
    )

    with ExitStack() as stack:
        mock_get, _ = _enter_db_patches(stack)
        mock_get.return_value = _FakeTaskPacket(loopback_count=2)
        _enter_runner_patch(stack)

        evidence = await handle_loopback(session, TASK_ID, "/repo", vr)

    assert evidence.taskpacket_id == TASK_ID
    assert evidence.loopback_attempt == 2


@pytest.mark.asyncio
async def test_handle_loopback_passes_failure_context():
    """handle_loopback() includes verification failures in user prompt."""
    session = AsyncMock()

    vr = VerificationResult(
        passed=False,
        checks=[
            CheckResult(name="ruff", passed=False, details="lint fail"),
            CheckResult(name="pytest", passed=True, details="all passed"),
        ],
    )

    with ExitStack() as stack:
        _enter_db_patches(stack)
        mock_run = _enter_runner_patch(stack)

        await handle_loopback(session, TASK_ID, "/repo", vr)

    ctx = mock_run.call_args[0][0]
    user_prompt = ctx.extra["user_prompt"]
    assert "ruff" in user_prompt
    assert "FAILED" in user_prompt
    assert "loopback attempt" in user_prompt


# ---------------------------------------------------------------------------
# Config construction
# ---------------------------------------------------------------------------


def test_make_developer_config_defaults():
    """_make_developer_config() with no role_config uses settings."""
    from src.agent.primary_agent import _make_developer_config

    config = _make_developer_config()
    assert config.agent_name == "developer"
    assert config.pipeline_step == "primary_agent"
    assert "Read" in config.tool_allowlist
    assert "Write" in config.tool_allowlist


def test_make_developer_config_with_role_config():
    """_make_developer_config() with role_config uses its values."""
    from src.agent.developer_role import DeveloperRoleConfig
    from src.agent.primary_agent import _make_developer_config

    role = DeveloperRoleConfig(model="custom", max_turns=10, max_budget_usd=2.0)
    config = _make_developer_config(role)
    assert config.max_turns == 10
    assert config.max_budget_usd == 2.0
