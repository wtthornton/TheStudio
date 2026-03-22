"""Tests for src/dashboard/budget_checker.py.

Covers:
- _check_budget_thresholds: below cap, above cap with/without pause flag,
  approach with/without downgrade flag, debounce (_downgrade_activated) flag.
- _pause_all_active_workflows: empty result, populated result, Temporal failure.
- _on_message: bare-payload JSON, typed-envelope JSON, invalid JSON (ack-always).
- _downgrade_activated module-level flag reset on start_budget_checker().
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import src.dashboard.budget_checker as bc_mod
from src.dashboard.budget_checker import (
    _check_budget_thresholds,
    _on_message,
    _pause_all_active_workflows,
)

from tests.dashboard.conftest import MockNatsMessage


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_config(
    *,
    weekly_budget_cap: float | None = 100.0,
    pause_on_budget_exceeded: bool = True,
    model_downgrade_on_approach: bool = True,
    downgrade_threshold_percent: float = 80.0,
) -> MagicMock:
    """Build a minimal budget-config mock."""
    cfg = MagicMock()
    cfg.weekly_budget_cap = weekly_budget_cap
    cfg.pause_on_budget_exceeded = pause_on_budget_exceeded
    cfg.model_downgrade_on_approach = model_downgrade_on_approach
    cfg.downgrade_threshold_percent = downgrade_threshold_percent
    return cfg


def _make_spend_report(total_cost: float = 0.0) -> MagicMock:
    report = MagicMock()
    report.total_cost = total_cost
    return report


def _make_async_session_cm(session: Any | None = None) -> MagicMock:
    """Return a sync callable that produces an async context manager."""
    sess = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=sess)
    cm.__aexit__ = AsyncMock(return_value=False)

    def _factory() -> Any:
        return cm

    return _factory, sess


# ---------------------------------------------------------------------------
# _check_budget_thresholds — below cap
# ---------------------------------------------------------------------------


class TestCheckBudgetThresholdsNoop:
    """No actions taken when spend is comfortably below all thresholds."""

    @pytest.mark.asyncio
    async def test_below_cap_no_pause_no_downgrade(self) -> None:
        cfg = _make_config(weekly_budget_cap=100.0, downgrade_threshold_percent=80.0)
        report = _make_spend_report(total_cost=50.0)  # 50% of cap

        session_factory, session = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-1"})

        mock_pause.assert_not_called()
        mock_down.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_budget_cap_skips_both_actions(self) -> None:
        """weekly_budget_cap=None → neither action fires."""
        cfg = _make_config(weekly_budget_cap=None)
        report = _make_spend_report(total_cost=9999.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-2"})

        mock_pause.assert_not_called()
        mock_down.assert_not_called()


# ---------------------------------------------------------------------------
# _check_budget_thresholds — above cap
# ---------------------------------------------------------------------------


class TestCheckBudgetThresholdsAboveCap:
    """Actions when weekly spend equals or exceeds weekly_budget_cap."""

    @pytest.mark.asyncio
    async def test_above_cap_with_pause_enabled(self) -> None:
        cfg = _make_config(
            weekly_budget_cap=100.0,
            pause_on_budget_exceeded=True,
            model_downgrade_on_approach=False,
        )
        report = _make_spend_report(total_cost=101.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-3"})

        mock_pause.assert_awaited_once()
        mock_down.assert_not_called()

    @pytest.mark.asyncio
    async def test_at_exact_cap_triggers_pause(self) -> None:
        """Spend exactly equal to cap triggers pause (>= semantics)."""
        cfg = _make_config(weekly_budget_cap=100.0, pause_on_budget_exceeded=True)
        report = _make_spend_report(total_cost=100.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()),
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-exact"})

        mock_pause.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_above_cap_with_pause_disabled(self) -> None:
        """pause_on_budget_exceeded=False → no pause even when cap breached."""
        cfg = _make_config(
            weekly_budget_cap=100.0,
            pause_on_budget_exceeded=False,
            model_downgrade_on_approach=False,
        )
        report = _make_spend_report(total_cost=200.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-4"})

        mock_pause.assert_not_called()
        mock_down.assert_not_called()


# ---------------------------------------------------------------------------
# _check_budget_thresholds — downgrade approach
# ---------------------------------------------------------------------------


class TestCheckBudgetThresholdsApproach:
    """Cost-optimization routing when spend reaches downgrade_threshold_percent."""

    @pytest.mark.asyncio
    async def test_approach_with_downgrade_enabled(self) -> None:
        """80% threshold hit with model_downgrade_on_approach=True → enable routing."""
        cfg = _make_config(
            weekly_budget_cap=100.0,
            pause_on_budget_exceeded=False,
            model_downgrade_on_approach=True,
            downgrade_threshold_percent=80.0,
        )
        report = _make_spend_report(total_cost=80.0)  # exactly 80%

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()) as mock_pause,
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-5"})

        mock_pause.assert_not_called()
        mock_down.assert_awaited_once()
        assert bc_mod._downgrade_activated is True

    @pytest.mark.asyncio
    async def test_approach_with_downgrade_disabled(self) -> None:
        """model_downgrade_on_approach=False → routing not enabled."""
        cfg = _make_config(
            weekly_budget_cap=100.0,
            model_downgrade_on_approach=False,
            downgrade_threshold_percent=80.0,
        )
        report = _make_spend_report(total_cost=90.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()),
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            bc_mod._downgrade_activated = False
            await _check_budget_thresholds({"task_id": "t-6"})

        mock_down.assert_not_called()

    @pytest.mark.asyncio
    async def test_debounce_flag_prevents_second_downgrade(self) -> None:
        """_downgrade_activated=True prevents redundant enable call."""
        cfg = _make_config(
            weekly_budget_cap=100.0,
            pause_on_budget_exceeded=False,
            model_downgrade_on_approach=True,
            downgrade_threshold_percent=80.0,
        )
        report = _make_spend_report(total_cost=90.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()),
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()) as mock_down,
        ):
            # Simulate that downgrade was already activated in this process lifetime.
            bc_mod._downgrade_activated = True
            await _check_budget_thresholds({"task_id": "t-7"})

        mock_down.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_task_id_defaults_to_unknown(self) -> None:
        """payload without task_id still runs without error."""
        cfg = _make_config(weekly_budget_cap=100.0, pause_on_budget_exceeded=False)
        report = _make_spend_report(total_cost=0.0)

        session_factory, _ = _make_async_session_cm()

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.dashboard.models.budget_config.get_budget_config",
                AsyncMock(return_value=cfg),
            ),
            patch("src.admin.model_spend.get_spend_report", return_value=report),
            patch.object(bc_mod, "_pause_all_active_workflows", AsyncMock()),
            patch.object(bc_mod, "_enable_cost_optimization_routing", AsyncMock()),
        ):
            bc_mod._downgrade_activated = False
            # No task_id key in payload
            await _check_budget_thresholds({})


# ---------------------------------------------------------------------------
# _pause_all_active_workflows
# ---------------------------------------------------------------------------


class TestPauseAllActiveWorkflows:
    """Tests for _pause_all_active_workflows."""

    @pytest.mark.asyncio
    async def test_empty_result_returns_early(self) -> None:
        """No task IDs in DB → no Temporal calls attempted."""
        # Build a session whose fetchall returns empty list.
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        session_factory, _ = _make_async_session_cm(session)

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.ingress.workflow_trigger.get_temporal_client",
                AsyncMock(),
            ) as mock_get_client,
        ):
            await _pause_all_active_workflows()

        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_populated_result_sends_signals(self) -> None:
        """Two active tasks → pause_task signal sent to each workflow handle."""
        task_id1 = uuid4()
        task_id2 = uuid4()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(task_id1,), (task_id2,)]
        session.execute = AsyncMock(return_value=result_mock)

        session_factory, _ = _make_async_session_cm(session)

        handle_mock = AsyncMock()
        handle_mock.signal = AsyncMock()
        client_mock = AsyncMock()
        client_mock.get_workflow_handle = MagicMock(return_value=handle_mock)

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.ingress.workflow_trigger.get_temporal_client",
                AsyncMock(return_value=client_mock),
            ),
        ):
            await _pause_all_active_workflows()

        assert client_mock.get_workflow_handle.call_count == 2
        assert handle_mock.signal.await_count == 2

    @pytest.mark.asyncio
    async def test_single_signal_failure_does_not_stop_others(self) -> None:
        """If one signal raises, remaining tasks are still attempted."""
        task_id1 = uuid4()
        task_id2 = uuid4()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(task_id1,), (task_id2,)]
        session.execute = AsyncMock(return_value=result_mock)

        session_factory, _ = _make_async_session_cm(session)

        call_count = 0

        async def _flaky_signal(*_args: Any, **_kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("workflow not found")

        handle_mock = AsyncMock()
        handle_mock.signal = _flaky_signal
        client_mock = AsyncMock()
        client_mock.get_workflow_handle = MagicMock(return_value=handle_mock)

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.ingress.workflow_trigger.get_temporal_client",
                AsyncMock(return_value=client_mock),
            ),
        ):
            # Should not raise
            await _pause_all_active_workflows()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_temporal_client_failure_logs_and_returns(self) -> None:
        """Temporal client unavailable → function returns without raising."""
        task_id = uuid4()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [(task_id,)]
        session.execute = AsyncMock(return_value=result_mock)

        session_factory, _ = _make_async_session_cm(session)

        async def _fail() -> None:
            raise ConnectionError("NATS not available")

        with (
            patch("src.db.connection.get_async_session", session_factory),
            patch(
                "src.ingress.workflow_trigger.get_temporal_client",
                _fail,
            ),
        ):
            # Must not raise
            await _pause_all_active_workflows()


# ---------------------------------------------------------------------------
# _on_message — JSON parsing + ack-always
# ---------------------------------------------------------------------------


class TestOnMessage:
    """Tests for _on_message NATS handler."""

    @pytest.mark.asyncio
    async def test_bare_payload_dispatches_to_check(self) -> None:
        """Bare JSON object (no envelope) is passed directly to _check_budget_thresholds."""
        payload = {"task_id": "t-bare", "cost": 1.5}
        msg = MockNatsMessage(payload)

        with patch.object(
            bc_mod, "_check_budget_thresholds", AsyncMock()
        ) as mock_check:
            await _on_message(msg)

        mock_check.assert_awaited_once_with(payload)
        assert msg.ack_called == 1

    @pytest.mark.asyncio
    async def test_typed_envelope_extracts_data_field(self) -> None:
        """Envelope format {"type": "...", "data": {...}} → data dict dispatched."""
        data = {"task_id": "t-env", "cost": 2.0}
        envelope = {"type": "pipeline.cost_update", "data": data}
        msg = MockNatsMessage(envelope)

        with patch.object(
            bc_mod, "_check_budget_thresholds", AsyncMock()
        ) as mock_check:
            await _on_message(msg)

        mock_check.assert_awaited_once_with(data)
        assert msg.ack_called == 1

    @pytest.mark.asyncio
    async def test_invalid_json_still_acks(self) -> None:
        """Malformed JSON → exception caught, message still acked."""
        msg = MockNatsMessage(b"this is not json!!!")

        with patch.object(bc_mod, "_check_budget_thresholds", AsyncMock()) as mock_check:
            await _on_message(msg)

        mock_check.assert_not_called()
        assert msg.ack_called == 1

    @pytest.mark.asyncio
    async def test_check_raises_still_acks(self) -> None:
        """Exception from _check_budget_thresholds → message is still acked."""
        payload = {"task_id": "t-err"}
        msg = MockNatsMessage(payload)

        with patch.object(
            bc_mod,
            "_check_budget_thresholds",
            AsyncMock(side_effect=RuntimeError("db error")),
        ):
            await _on_message(msg)

        assert msg.ack_called == 1

    @pytest.mark.asyncio
    async def test_empty_payload_envelope_fallback(self) -> None:
        """Empty JSON object {} → dispatched as-is (no data key → falls back to envelope)."""
        msg = MockNatsMessage({})

        with patch.object(
            bc_mod, "_check_budget_thresholds", AsyncMock()
        ) as mock_check:
            await _on_message(msg)

        mock_check.assert_awaited_once_with({})
        assert msg.ack_called == 1


# ---------------------------------------------------------------------------
# _downgrade_activated module-level flag reset
# ---------------------------------------------------------------------------


class TestDowngradeActivatedFlagReset:
    """start_budget_checker resets the module-level _downgrade_activated flag."""

    @pytest.mark.asyncio
    async def test_start_budget_checker_resets_flag(self) -> None:
        """Starting the checker clears _downgrade_activated from a previous run."""
        # Pre-set the flag as if downgrade was triggered in a prior run.
        bc_mod._downgrade_activated = True

        # Patch nats.connect so we don't hit real NATS; cancel immediately.
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nc.jetstream.return_value = mock_js
        mock_js.find_stream_name_by_subject = AsyncMock()
        mock_js.subscribe = AsyncMock()

        with patch("nats.connect", AsyncMock(return_value=mock_nc)):
            task = await bc_mod.start_budget_checker(nats_url="nats://localhost:4222")
            # Cancel immediately — we only care about the reset, not the loop.
            task.cancel()
            try:
                await task
            except BaseException:
                pass

        # Flag must be False right after start_budget_checker() is called.
        assert bc_mod._downgrade_activated is False

    def test_flag_is_module_level_bool(self) -> None:
        """Sanity check: _downgrade_activated is a plain module-level bool."""
        assert isinstance(bc_mod._downgrade_activated, bool)
