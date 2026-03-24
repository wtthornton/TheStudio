"""Unit tests for cost recording (43.10) and activity heartbeat (43.11).

Story 43.12 — Validates:
- ModelCallAudit recorded after Ralph run with correct fields (provider, step, role,
  tokens, cost, latency)
- Cost estimate: tokens_in * $3/Mtok + tokens_out * $15/Mtok
- BudgetEnforcer.record_spend() called post-run with task_id, step, cost, tokens
- PipelineBudget.consume() checked pre-launch; BudgetExceededError on exhaustion
  → agent.run() must NOT be called
- Post-run BudgetExceededError from record_spend is logged but not re-raised;
  EvidenceBundle is still returned
- _implement_ralph_with_heartbeat emits temporal_activity.heartbeat() at least once
  per run with "ralph_running elapsed=…s timeout=…s" message format
- Timeout: agent.cancel() called + TimeoutError("wall-clock timeout") raised when
  elapsed_s >= timeout_s
- Cancellation: agent.cancel() called + asyncio.CancelledError re-raised on activity
  cancellation
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.admin.model_gateway import BudgetExceededError, ModelCallAudit
from src.agent.evidence import EvidenceBundle
from src.workflow.activities import ImplementInput

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _taskpacket(loopback_count: int = 0, tp_id: UUID | None = None) -> MagicMock:
    tp = MagicMock()
    tp.id = tp_id or uuid4()
    tp.correlation_id = uuid4()
    tp.loopback_count = loopback_count
    tp.repo = "owner/repo"
    tp.issue_id = 42
    tp.task_trust_tier = None
    tp.complexity_index = None
    tp.risk_flags = {}
    return tp


def _intent(version: int = 1) -> MagicMock:
    m = MagicMock()
    m.id = uuid4()
    m.taskpacket_id = uuid4()
    m.version = version
    m.goal = "Add rate limiting"
    m.constraints = []
    m.acceptance_criteria = []
    m.non_goals = []
    m.source = "auto"
    return m


def _ralph_result(
    tokens_in: int = 100,
    tokens_out: int = 200,
    duration: float = 5.0,
) -> MagicMock:
    """Minimal TaskResult mock with token counts, status, and output."""
    from ralph_sdk.status import RalphLoopStatus, RalphStatus, WorkType

    r = MagicMock()
    r.output = "- src/api.py: added rate limiter"
    r.error = ""
    r.loop_count = 2
    r.duration_seconds = duration
    r.tokens_in = tokens_in
    r.tokens_out = tokens_out
    r.status = RalphStatus(
        progress_summary="Completed",
        exit_signal=True,
        status=RalphLoopStatus.COMPLETED,
        work_type=WorkType.IMPLEMENTATION,
    )
    return r


def _evidence(taskpacket_id: UUID | None = None) -> EvidenceBundle:
    return EvidenceBundle(
        taskpacket_id=taskpacket_id or uuid4(),
        intent_version=1,
        files_changed=["src/api.py"],
        agent_summary="Completed",
    )


def _impl_input(taskpacket_id: str | None = None) -> ImplementInput:
    return ImplementInput(
        taskpacket_id=taskpacket_id or str(uuid4()),
        repo_path="/tmp/test-repo",
        loopback_attempt=0,
        repo_tier="observe",
        repo="owner/repo",
        issue_title="Add rate limiting",
        issue_body="Add rate limiting to the API",
        intent_goal="Add rate limiting",
        acceptance_criteria=[],
        plan_steps=[],
        qa_feedback="",
    )


def _default_settings() -> MagicMock:
    s = MagicMock()
    s.agent_model = "claude-sonnet-4-5"
    s.agent_max_turns = 30
    s.agent_max_budget_usd = 5.0
    s.ralph_state_backend = "null"
    s.ralph_session_ttl_seconds = 7200
    return s


def _make_mock_agent(run_result: MagicMock) -> MagicMock:
    agent = MagicMock()
    agent.run = AsyncMock(return_value=run_result)
    agent.ralph_dir = MagicMock()
    return agent


def _make_task_input() -> MagicMock:
    ti = MagicMock()
    ti.prompt = "Implement the goal"
    ti.agent_instructions = None
    return ti


def _make_bridge_outputs() -> tuple[MagicMock, MagicMock]:
    """Return (packet_input, intent_input) mocks."""
    packet_input = MagicMock()
    packet_input.intent = MagicMock()
    intent_input = MagicMock()
    return packet_input, intent_input


# ---------------------------------------------------------------------------
# Cost recording tests — _implement_ralph in src/agent/primary_agent.py
# ---------------------------------------------------------------------------


class TestCostRecording:
    """Verify ModelCallAudit + BudgetEnforcer.record_spend() after a Ralph run."""

    @pytest.mark.asyncio
    async def test_model_call_audit_recorded_with_correct_fields(self) -> None:
        """ModelCallAudit recorded with provider='claude_code', correct step/role/tokens."""
        tp = _taskpacket()
        intent = _intent(version=3)
        run_result = _ralph_result(tokens_in=500, tokens_out=300, duration=7.5)

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()
        mock_agent = _make_mock_agent(run_result)
        mock_store = MagicMock()
        mock_enforcer = MagicMock()
        settings = _default_settings()

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store", return_value=mock_store),
            patch("src.agent.primary_agent.get_budget_enforcer", return_value=mock_enforcer),
        ):
            from src.agent.primary_agent import _implement_ralph

            await _implement_ralph(tp, intent, repo_path="/tmp/repo")

        mock_store.record.assert_called_once()
        audit: ModelCallAudit = mock_store.record.call_args[0][0]
        assert isinstance(audit, ModelCallAudit)
        assert audit.tokens_in == 500
        assert audit.tokens_out == 300
        assert audit.provider == "claude_code"
        assert audit.step == "primary_agent_ralph"
        assert audit.role == "developer"
        assert audit.model == "claude-sonnet-4-5"
        assert abs(audit.latency_ms - 7500.0) < 1.0

    @pytest.mark.asyncio
    async def test_cost_calculation_from_token_counts(self) -> None:
        """Cost estimate = tokens_in * $3/Mtok + tokens_out * $15/Mtok."""
        tp = _taskpacket()
        intent = _intent()
        # 1000 tokens each → $0.003 + $0.015 = $0.018
        run_result = _ralph_result(tokens_in=1000, tokens_out=1000)

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()
        mock_agent = _make_mock_agent(run_result)
        mock_store = MagicMock()
        mock_enforcer = MagicMock()
        settings = _default_settings()

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store", return_value=mock_store),
            patch("src.agent.primary_agent.get_budget_enforcer", return_value=mock_enforcer),
        ):
            from src.agent.primary_agent import _implement_ralph

            await _implement_ralph(tp, intent, repo_path="/tmp/repo")

        audit: ModelCallAudit = mock_store.record.call_args[0][0]
        expected_cost = (1000 * 0.003 / 1000) + (1000 * 0.015 / 1000)  # 0.018
        assert abs(audit.cost - expected_cost) < 1e-9

    @pytest.mark.asyncio
    async def test_budget_enforcer_record_spend_called_with_correct_args(self) -> None:
        """BudgetEnforcer.record_spend() called with step, cost, and total tokens."""
        tp = _taskpacket()
        intent = _intent()
        run_result = _ralph_result(tokens_in=200, tokens_out=400)

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()
        mock_agent = _make_mock_agent(run_result)
        mock_store = MagicMock()
        mock_enforcer = MagicMock()
        settings = _default_settings()

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store", return_value=mock_store),
            patch("src.agent.primary_agent.get_budget_enforcer", return_value=mock_enforcer),
        ):
            from src.agent.primary_agent import _implement_ralph

            await _implement_ralph(tp, intent, repo_path="/tmp/repo")

        mock_enforcer.record_spend.assert_called_once()
        kw = mock_enforcer.record_spend.call_args.kwargs
        assert kw["step"] == "primary_agent_ralph"
        assert kw["tokens"] == 600  # 200 + 400
        expected_cost = (200 * 0.003 / 1000) + (400 * 0.015 / 1000)
        assert abs(kw["cost"] - expected_cost) < 1e-9

    @pytest.mark.asyncio
    async def test_pipeline_budget_exhausted_pre_launch_raises_budget_exceeded(self) -> None:
        """PipelineBudget.consume() → False raises BudgetExceededError before agent.run()."""
        tp = _taskpacket()
        intent = _intent()
        run_result = _ralph_result()

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()
        mock_agent = _make_mock_agent(run_result)
        settings = _default_settings()

        pipeline_budget = MagicMock()
        pipeline_budget.consume.return_value = False
        pipeline_budget.used = 4.99
        pipeline_budget.max_total_usd = 5.0

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store"),
            patch("src.agent.primary_agent.get_budget_enforcer"),
        ):
            from src.agent.primary_agent import _implement_ralph

            with pytest.raises(BudgetExceededError):
                await _implement_ralph(
                    tp, intent, repo_path="/tmp/repo",
                    pipeline_budget=pipeline_budget,
                )

        # Agent must NOT have run when budget is exhausted pre-launch
        mock_agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_budget_consume_called_before_agent_run(self) -> None:
        """PipelineBudget.consume() must be invoked before agent.run() (pre-launch check)."""
        tp = _taskpacket()
        intent = _intent()
        run_result = _ralph_result()

        call_order: list[str] = []
        settings = _default_settings()
        pipeline_budget = MagicMock()

        def consume_side_effect(amount: float) -> bool:
            call_order.append("consume")
            return True

        async def run_side_effect() -> MagicMock:
            call_order.append("run")
            return run_result

        pipeline_budget.consume.side_effect = consume_side_effect

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=run_side_effect)
        mock_agent.ralph_dir = MagicMock()

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store"),
            patch("src.agent.primary_agent.get_budget_enforcer"),
        ):
            from src.agent.primary_agent import _implement_ralph

            await _implement_ralph(
                tp, intent, repo_path="/tmp/repo",
                pipeline_budget=pipeline_budget,
            )

        assert "consume" in call_order, "pipeline_budget.consume() was not called"
        assert "run" in call_order, "agent.run() was not called"
        assert call_order.index("consume") < call_order.index("run"), (
            "consume() must be called before agent.run()"
        )

    @pytest.mark.asyncio
    async def test_post_run_budget_exceeded_logged_not_reraised(self) -> None:
        """BudgetExceededError from record_spend after run → logged, EvidenceBundle returned."""
        tp = _taskpacket()
        intent = _intent()
        run_result = _ralph_result()

        packet_input, intent_input = _make_bridge_outputs()
        task_input = _make_task_input()
        mock_agent = _make_mock_agent(run_result)
        mock_store = MagicMock()
        mock_enforcer = MagicMock()
        mock_enforcer.record_spend.side_effect = BudgetExceededError(
            task_id=str(tp.id),
            current_spend=5.1,
            limit=5.0,
            step="primary_agent_ralph",
        )
        settings = _default_settings()

        with (
            patch("src.agent.ralph_bridge.taskpacket_to_ralph_input", return_value=(packet_input, intent_input)),
            patch("src.agent.ralph_bridge.build_ralph_config"),
            patch("ralph_sdk.NullStateBackend"),
            patch("ralph_sdk.converters.from_task_packet", return_value=task_input),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("src.agent.primary_agent.settings", settings),
            patch("src.agent.primary_agent.get_model_audit_store", return_value=mock_store),
            patch("src.agent.primary_agent.get_budget_enforcer", return_value=mock_enforcer),
        ):
            from src.agent.primary_agent import _implement_ralph

            # Must NOT raise — post-run BudgetExceededError is a warning, not an abort
            bundle = await _implement_ralph(tp, intent, repo_path="/tmp/repo")

        assert isinstance(bundle, EvidenceBundle)
        mock_store.record.assert_called_once()  # audit was still recorded


# ---------------------------------------------------------------------------
# Activity heartbeat tests — _implement_ralph_with_heartbeat
# ---------------------------------------------------------------------------


class TestActivityHeartbeat:
    """Verify Temporal heartbeat emission and agent cancellation paths."""

    def _make_session_factory(self) -> tuple:
        """Return (async_ctx_manager_factory, mock_session)."""
        mock_session = AsyncMock()

        @asynccontextmanager
        async def factory():
            yield mock_session

        return factory, mock_session

    @pytest.mark.asyncio
    async def test_heartbeat_emitted_during_successful_run(self) -> None:
        """temporal_activity.heartbeat() called at least once with 'ralph_running' message."""
        tp = _taskpacket()
        intent = _intent()
        evidence = _evidence(tp.id)
        task_id_str = str(tp.id)

        heartbeat_messages: list[str] = []

        def capture_heartbeat(msg: str) -> None:
            heartbeat_messages.append(msg)

        session_factory, _ = self._make_session_factory()

        with (
            patch("temporalio.activity.heartbeat", side_effect=capture_heartbeat),
            patch("src.agent.primary_agent._implement_ralph", new_callable=AsyncMock, return_value=evidence),
            patch("src.db.connection.get_async_session", session_factory),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.intent.intent_crud.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.settings.settings") as mock_settings,
        ):
            mock_settings.ralph_timeout_minutes = 30

            from src.workflow.activities import _implement_ralph_with_heartbeat

            params = _impl_input(taskpacket_id=task_id_str)
            result = await _implement_ralph_with_heartbeat(params, "observe")

        assert len(heartbeat_messages) >= 1, "temporal_activity.heartbeat() must be called at least once"
        assert result.taskpacket_id == task_id_str

    @pytest.mark.asyncio
    async def test_heartbeat_message_format(self) -> None:
        """Heartbeat message contains 'ralph_running', 'elapsed=', and 'timeout=' tokens."""
        tp = _taskpacket()
        intent = _intent()
        evidence = _evidence(tp.id)
        task_id_str = str(tp.id)

        heartbeat_messages: list[str] = []

        def capture_heartbeat(msg: str) -> None:
            heartbeat_messages.append(msg)

        session_factory, _ = self._make_session_factory()

        with (
            patch("temporalio.activity.heartbeat", side_effect=capture_heartbeat),
            patch("src.agent.primary_agent._implement_ralph", new_callable=AsyncMock, return_value=evidence),
            patch("src.db.connection.get_async_session", session_factory),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.intent.intent_crud.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.settings.settings") as mock_settings,
        ):
            mock_settings.ralph_timeout_minutes = 30

            from src.workflow.activities import _implement_ralph_with_heartbeat

            params = _impl_input(taskpacket_id=task_id_str)
            await _implement_ralph_with_heartbeat(params, "observe")

        assert heartbeat_messages, "At least one heartbeat must be emitted"
        msg = heartbeat_messages[0]
        assert "ralph_running" in msg
        assert "elapsed=" in msg
        assert "timeout=" in msg

    @pytest.mark.asyncio
    async def test_timeout_calls_agent_cancel_and_raises_timeout_error(self) -> None:
        """Wall-clock timeout: agent.cancel() called + TimeoutError('wall-clock timeout') raised."""
        tp = _taskpacket()
        intent = _intent()
        task_id_str = str(tp.id)

        mock_agent = MagicMock()
        mock_agent.cancel = MagicMock()

        # Event to synchronize: heartbeat loop waits until agent_holder is populated
        agent_appended = asyncio.Event()

        async def slow_ralph(
            *,
            taskpacket: object = None,
            intent: object = None,
            repo_path: str = "",
            loopback_context: str = "",
            agent_holder: list | None = None,
            **_kw: object,
        ) -> EvidenceBundle:
            if agent_holder is not None:
                agent_holder.append(mock_agent)
                agent_appended.set()
            # Block until cancelled
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise
            return _evidence(tp.id)

        wait_call_count = 0

        async def mock_wait(tasks: set, timeout: float | None = None) -> tuple:
            nonlocal wait_call_count
            wait_call_count += 1
            if wait_call_count == 1:
                # First call: yield to the event loop so slow_ralph can populate agent_holder
                await agent_appended.wait()
            # Simulate: task still running after the poll interval elapsed
            return (set(), set())

        session_factory, _ = self._make_session_factory()

        with (
            patch("temporalio.activity.heartbeat"),
            patch("src.agent.primary_agent._implement_ralph", side_effect=slow_ralph),
            patch("src.db.connection.get_async_session", session_factory),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.intent.intent_crud.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.settings.settings") as mock_settings,
            patch("asyncio.wait", mock_wait),
            patch("asyncio.sleep", new_callable=AsyncMock),   # Make 10s grace period instant
            patch("asyncio.gather", new_callable=AsyncMock),  # Make post-cancel gather instant
        ):
            # ralph_timeout_minutes=-5 → timeout_s = 0
            # After first non-done wait: elapsed_s=30 >= 0 → triggers timeout path
            mock_settings.ralph_timeout_minutes = -5

            from src.workflow.activities import _implement_ralph_with_heartbeat

            params = _impl_input(taskpacket_id=task_id_str)

            with pytest.raises(TimeoutError, match="wall-clock timeout"):
                await _implement_ralph_with_heartbeat(params, "observe")

        mock_agent.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancelled_error_calls_agent_cancel_and_reraises(self) -> None:
        """asyncio.CancelledError: agent.cancel() called + CancelledError re-raised."""
        tp = _taskpacket()
        intent = _intent()
        task_id_str = str(tp.id)

        mock_agent = MagicMock()
        mock_agent.cancel = MagicMock()

        agent_appended = asyncio.Event()

        async def slow_ralph(
            *,
            taskpacket: object = None,
            intent: object = None,
            repo_path: str = "",
            loopback_context: str = "",
            agent_holder: list | None = None,
            **_kw: object,
        ) -> EvidenceBundle:
            if agent_holder is not None:
                agent_holder.append(mock_agent)
                agent_appended.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise
            return _evidence(tp.id)

        async def mock_wait_raises(tasks: set, timeout: float | None = None) -> tuple:
            # Yield to let slow_ralph start and populate agent_holder
            await agent_appended.wait()
            raise asyncio.CancelledError("Temporal cancelled the activity")

        session_factory, _ = self._make_session_factory()

        with (
            patch("temporalio.activity.heartbeat"),
            patch("src.agent.primary_agent._implement_ralph", side_effect=slow_ralph),
            patch("src.db.connection.get_async_session", session_factory),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.intent.intent_crud.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.settings.settings") as mock_settings,
            patch("asyncio.wait", mock_wait_raises),
            patch("asyncio.gather", new_callable=AsyncMock),
        ):
            mock_settings.ralph_timeout_minutes = 30

            from src.workflow.activities import _implement_ralph_with_heartbeat

            params = _impl_input(taskpacket_id=task_id_str)

            with pytest.raises(asyncio.CancelledError):
                await _implement_ralph_with_heartbeat(params, "observe")

        mock_agent.cancel.assert_called_once()
