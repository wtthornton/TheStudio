"""Tests for src/dashboard/notification_generator.py.

Covers:
- _safe_task_id: valid UUID, None/missing, invalid string.
- _notification_for_gate_fail: with checks, without checks, task_id aliases.
- _notification_for_cost_update: zero delta → None, positive delta, all fields.
- _notification_for_steering_action: minimal, with from/to stage, with reason.
- _notification_for_trust_tier: basic, with matched_rule_id, with safety_capped.
- _on_message: known subject dispatch, unknown subject skip, invalid JSON ack-always,
  typed-envelope unwrap, builder returns None (no persist).
- _BUILDERS dict: keys and callable values.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.dashboard.notification_generator import (
    _BUILDERS,
    _notification_for_cost_update,
    _notification_for_gate_fail,
    _notification_for_steering_action,
    _notification_for_trust_tier,
    _on_message,
    _safe_task_id,
)
from tests.dashboard.conftest import MockNatsMessage


# ---------------------------------------------------------------------------
# _safe_task_id
# ---------------------------------------------------------------------------


def test_safe_task_id_valid_uuid_string() -> None:
    uid = uuid4()
    result = _safe_task_id(str(uid))
    assert result == uid


def test_safe_task_id_uuid_object() -> None:
    uid = uuid4()
    result = _safe_task_id(uid)
    assert result == uid


def test_safe_task_id_none_returns_none() -> None:
    assert _safe_task_id(None) is None


def test_safe_task_id_empty_string_returns_none() -> None:
    assert _safe_task_id("") is None


def test_safe_task_id_invalid_string_returns_none() -> None:
    assert _safe_task_id("not-a-uuid") is None


def test_safe_task_id_integer_returns_none() -> None:
    # Integers are truthy but not valid UUIDs unless they match the format.
    assert _safe_task_id(99999) is None


# ---------------------------------------------------------------------------
# _notification_for_gate_fail
# ---------------------------------------------------------------------------


def test_gate_fail_basic() -> None:
    uid = uuid4()
    result = _notification_for_gate_fail({"task_id": str(uid), "stage": "verify"})
    assert result is not None
    assert result["type"] == "gate_fail"
    assert result["title"] == "Gate failed: verify"
    assert result["task_id"] == uid
    assert "verify" in result["message"]


def test_gate_fail_with_checks() -> None:
    checks = [{"name": "ruff", "passed": False}]
    result = _notification_for_gate_fail({"stage": "verify", "checks": checks})
    assert result is not None
    assert "Checks:" in result["message"]
    assert "ruff" in result["message"]


def test_gate_fail_without_checks() -> None:
    result = _notification_for_gate_fail({"stage": "qa"})
    assert result is not None
    assert "Checks:" not in result["message"]
    assert "qa" in result["message"]


def test_gate_fail_taskpacket_id_alias() -> None:
    """task_id can also come via the ``taskpacket_id`` key."""
    uid = uuid4()
    result = _notification_for_gate_fail({"taskpacket_id": str(uid), "stage": "verify"})
    assert result is not None
    assert result["task_id"] == uid


def test_gate_fail_no_task_id() -> None:
    result = _notification_for_gate_fail({"stage": "verify"})
    assert result is not None
    assert result["task_id"] is None


def test_gate_fail_title_truncated_to_500() -> None:
    long_stage = "x" * 600
    result = _notification_for_gate_fail({"stage": long_stage})
    assert result is not None
    assert len(result["title"]) <= 500


# ---------------------------------------------------------------------------
# _notification_for_cost_update
# ---------------------------------------------------------------------------


def test_cost_update_zero_delta_returns_none() -> None:
    result = _notification_for_cost_update({"task_id": str(uuid4()), "delta": 0.0, "total": 5.0})
    assert result is None


def test_cost_update_missing_delta_returns_none() -> None:
    result = _notification_for_cost_update({"task_id": str(uuid4()), "total": 5.0})
    assert result is None


def test_cost_update_positive_delta() -> None:
    uid = uuid4()
    result = _notification_for_cost_update(
        {"task_id": str(uid), "delta": 0.05, "total": 1.23, "stage": "implement"}
    )
    assert result is not None
    assert result["type"] == "cost_update"
    assert result["task_id"] == uid
    assert "1.2300" in result["title"]
    assert "0.0500" in result["message"]
    assert "implement" in result["message"]


def test_cost_update_default_stage() -> None:
    result = _notification_for_cost_update({"delta": 0.01})
    assert result is not None
    assert "unknown" in result["message"]


def test_cost_update_title_truncated_to_500() -> None:
    # Force a float that can't exceed 500 chars in title naturally — just verify the slice.
    result = _notification_for_cost_update({"delta": 0.01, "total": 999999.99999})
    assert result is not None
    assert len(result["title"]) <= 500


# ---------------------------------------------------------------------------
# _notification_for_steering_action
# ---------------------------------------------------------------------------


def test_steering_action_minimal() -> None:
    uid = uuid4()
    result = _notification_for_steering_action(
        {"task_id": str(uid), "action": "pause", "actor": "alice"}
    )
    assert result is not None
    assert result["type"] == "steering_action"
    assert result["task_id"] == uid
    assert "pause" in result["title"]
    assert "alice" in result["message"]


def test_steering_action_with_from_to_stage() -> None:
    result = _notification_for_steering_action(
        {
            "action": "redirect",
            "actor": "bob",
            "from_stage": "implement",
            "to_stage": "verify",
        }
    )
    assert result is not None
    assert "From stage: implement." in result["message"]
    assert "To stage: verify." in result["message"]


def test_steering_action_with_reason() -> None:
    result = _notification_for_steering_action(
        {"action": "abort", "actor": "system", "reason": "cost overrun"}
    )
    assert result is not None
    assert "cost overrun" in result["message"]


def test_steering_action_defaults() -> None:
    """Missing action/actor fallback to 'unknown' / 'system'."""
    result = _notification_for_steering_action({})
    assert result is not None
    assert "unknown" in result["title"]
    assert "system" in result["message"]


def test_steering_action_title_truncated_to_500() -> None:
    result = _notification_for_steering_action({"action": "a" * 600})
    assert result is not None
    assert len(result["title"]) <= 500


# ---------------------------------------------------------------------------
# _notification_for_trust_tier
# ---------------------------------------------------------------------------


def test_trust_tier_basic() -> None:
    uid = uuid4()
    result = _notification_for_trust_tier({"task_id": str(uid), "tier": "suggest"})
    assert result is not None
    assert result["type"] == "trust_tier_assigned"
    assert result["task_id"] == uid
    assert "suggest" in result["title"]
    assert "suggest" in result["message"]


def test_trust_tier_with_matched_rule() -> None:
    result = _notification_for_trust_tier(
        {"tier": "execute", "matched_rule_id": "rule-42"}
    )
    assert result is not None
    assert "rule-42" in result["message"]


def test_trust_tier_safety_capped() -> None:
    result = _notification_for_trust_tier(
        {"tier": "observe", "safety_capped": True}
    )
    assert result is not None
    assert "Safety bounds override applied." in result["message"]


def test_trust_tier_no_safety_cap() -> None:
    result = _notification_for_trust_tier({"tier": "suggest", "safety_capped": False})
    assert result is not None
    assert "Safety bounds" not in result["message"]


def test_trust_tier_defaults() -> None:
    result = _notification_for_trust_tier({})
    assert result is not None
    assert "unknown" in result["title"]


def test_trust_tier_title_truncated_to_500() -> None:
    result = _notification_for_trust_tier({"tier": "t" * 600})
    assert result is not None
    assert len(result["title"]) <= 500


# ---------------------------------------------------------------------------
# _BUILDERS dict
# ---------------------------------------------------------------------------


def test_builders_keys() -> None:
    expected = {
        "pipeline.gate.fail",
        "pipeline.cost_update",
        "pipeline.steering.action",
        "pipeline.trust_tier.assigned",
    }
    assert set(_BUILDERS.keys()) == expected


def test_builders_are_callable() -> None:
    for key, fn in _BUILDERS.items():
        assert callable(fn), f"_BUILDERS[{key!r}] is not callable"


def test_builders_map_to_correct_functions() -> None:
    assert _BUILDERS["pipeline.gate.fail"] is _notification_for_gate_fail
    assert _BUILDERS["pipeline.cost_update"] is _notification_for_cost_update
    assert _BUILDERS["pipeline.steering.action"] is _notification_for_steering_action
    assert _BUILDERS["pipeline.trust_tier.assigned"] is _notification_for_trust_tier


# ---------------------------------------------------------------------------
# _on_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_message_dispatches_gate_fail() -> None:
    """A gate.fail message is dispatched to the correct builder and persisted."""
    uid = uuid4()
    msg = MockNatsMessage(
        {
            "type": "pipeline.gate.fail",
            "data": {"task_id": str(uid), "stage": "verify"},
        }
    )
    msg.subject = "pipeline.gate.fail"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_awaited_once()
    kwargs = mock_persist.call_args[0][0]
    assert kwargs["type"] == "gate_fail"
    assert kwargs["task_id"] == uid


@pytest.mark.asyncio
async def test_on_message_dispatches_cost_update() -> None:
    uid = uuid4()
    msg = MockNatsMessage(
        {"type": "pipeline.cost_update", "data": {"task_id": str(uid), "delta": 0.1, "total": 0.5}}
    )
    msg.subject = "pipeline.cost_update"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_awaited_once()
    kwargs = mock_persist.call_args[0][0]
    assert kwargs["type"] == "cost_update"


@pytest.mark.asyncio
async def test_on_message_dispatches_steering_action() -> None:
    msg = MockNatsMessage(
        {
            "type": "pipeline.steering.action",
            "data": {"action": "pause", "actor": "operator"},
        }
    )
    msg.subject = "pipeline.steering.action"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_message_dispatches_trust_tier() -> None:
    msg = MockNatsMessage(
        {
            "type": "pipeline.trust_tier.assigned",
            "data": {"tier": "observe"},
        }
    )
    msg.subject = "pipeline.trust_tier.assigned"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_message_subject_fallback() -> None:
    """When the envelope has no ``type`` field, fall back to msg.subject."""
    uid = uuid4()
    # Bare payload (no "type" wrapper) — builder derived from msg.subject.
    msg = MockNatsMessage({"task_id": str(uid), "stage": "verify"})
    msg.subject = "pipeline.gate.fail"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_message_unknown_subject_skips_persist() -> None:
    """Unknown subjects are ack'd but do NOT call _persist_notification."""
    msg = MockNatsMessage({"event": "something_else"})
    msg.subject = "pipeline.unknown.subject"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_invalid_json_acks_always() -> None:
    """Invalid JSON must still ack to prevent infinite redelivery."""
    msg = MockNatsMessage(b"not valid json {{")
    msg.subject = "pipeline.gate.fail"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_zero_delta_cost_update_no_persist() -> None:
    """_notification_for_cost_update returns None for zero delta — no persist call."""
    msg = MockNatsMessage(
        {"type": "pipeline.cost_update", "data": {"delta": 0.0, "total": 5.0}}
    )
    msg.subject = "pipeline.cost_update"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        new=AsyncMock(),
    ) as mock_persist:
        await _on_message(msg)

    assert msg.ack_called == 1
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_persist_exception_still_acks() -> None:
    """If _persist_notification raises, message is still ack'd (fire-and-forget)."""
    msg = MockNatsMessage(
        {"type": "pipeline.gate.fail", "data": {"stage": "verify"}}
    )
    msg.subject = "pipeline.gate.fail"

    with patch(
        "src.dashboard.notification_generator._persist_notification",
        side_effect=RuntimeError("DB down"),
    ):
        await _on_message(msg)

    assert msg.ack_called == 1
