"""Tests for src.dashboard.events_publisher — fire-and-forget NATS stage events."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dashboard.events_publisher import (
    emit_cost_update,
    emit_stage_enter,
    emit_stage_exit,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module-level JetStream singleton between tests."""
    import src.dashboard.events_publisher as mod
    mod._js = None
    yield
    mod._js = None


def _make_mock_js():
    js = AsyncMock()
    js.find_stream_name_by_subject = AsyncMock(return_value="THESTUDIO_PIPELINE")
    js.publish = AsyncMock()
    return js


@pytest.mark.asyncio
async def test_emit_stage_enter_publishes():
    mock_js = _make_mock_js()
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_stage_enter("intake", "task-123", correlation_id="corr-1")

    mock_js.publish.assert_called_once()
    subject, payload_bytes = mock_js.publish.call_args.args
    assert subject == "pipeline.stage.enter"
    payload = json.loads(payload_bytes)
    assert payload["type"] == "pipeline.stage.enter"
    assert payload["data"]["stage"] == "intake"
    assert payload["data"]["taskpacket_id"] == "task-123"
    assert payload["data"]["correlation_id"] == "corr-1"
    assert "timestamp" in payload["data"]


@pytest.mark.asyncio
async def test_emit_stage_exit_publishes():
    mock_js = _make_mock_js()
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_stage_exit("context", "task-456", success=True)

    mock_js.publish.assert_called_once()
    subject, payload_bytes = mock_js.publish.call_args.args
    assert subject == "pipeline.stage.exit"
    payload = json.loads(payload_bytes)
    assert payload["type"] == "pipeline.stage.exit"
    assert payload["data"]["stage"] == "context"
    assert payload["data"]["taskpacket_id"] == "task-456"
    assert payload["data"]["success"] is True


@pytest.mark.asyncio
async def test_emit_stage_exit_failure():
    mock_js = _make_mock_js()
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_stage_exit("intent", "task-789", success=False)

    payload = json.loads(mock_js.publish.call_args.args[1])
    assert payload["data"]["success"] is False


@pytest.mark.asyncio
async def test_emit_stage_enter_swallows_nats_error():
    """Fire-and-forget must not raise even if NATS is down."""
    mock_js = _make_mock_js()
    mock_js.publish.side_effect = Exception("NATS connection refused")
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        # Should not raise
        await emit_stage_enter("intake", "task-err")


@pytest.mark.asyncio
async def test_emit_stage_exit_swallows_nats_error():
    """Fire-and-forget must not raise even if NATS is down."""
    mock_js = _make_mock_js()
    mock_js.publish.side_effect = Exception("NATS connection refused")
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_stage_exit("context", "task-err", success=True)


@pytest.mark.asyncio
async def test_get_pipeline_jetstream_creates_stream():
    """Singleton creates stream on first call if not found."""
    import src.dashboard.events_publisher as mod

    mock_nc = AsyncMock()
    mock_js = AsyncMock()
    # jetstream() is a sync method that returns a JetStreamContext
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_js.find_stream_name_by_subject.side_effect = Exception("not found")
    mock_js.add_stream = AsyncMock()

    with patch("src.dashboard.events_publisher.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)
        js = await mod.get_pipeline_jetstream()

    assert js is mock_js
    mock_js.add_stream.assert_called_once_with(
        name="THESTUDIO_PIPELINE",
        subjects=["pipeline.>"],
    )


@pytest.mark.asyncio
async def test_emit_cost_update_publishes():
    mock_js = _make_mock_js()
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_cost_update(
            task_id="task-100",
            cost_delta=0.0025,
            total_cost=0.015,
            model="claude-3-5-sonnet",
            stage="intent",
            correlation_id="corr-9",
        )

    mock_js.publish.assert_called_once()
    subject, payload_bytes = mock_js.publish.call_args.args
    assert subject == "pipeline.cost_update"
    payload = json.loads(payload_bytes)
    assert payload["type"] == "pipeline.cost_update"
    assert payload["data"]["task_id"] == "task-100"
    assert payload["data"]["cost_delta"] == 0.0025
    assert payload["data"]["total_cost"] == 0.015
    assert payload["data"]["model"] == "claude-3-5-sonnet"
    assert payload["data"]["stage"] == "intent"
    assert payload["data"]["correlation_id"] == "corr-9"
    assert "timestamp" in payload["data"]


@pytest.mark.asyncio
async def test_emit_cost_update_swallows_nats_error():
    """Fire-and-forget must not raise even if NATS is down."""
    mock_js = _make_mock_js()
    mock_js.publish.side_effect = Exception("NATS connection refused")
    with patch("src.dashboard.events_publisher.get_pipeline_jetstream", return_value=mock_js):
        await emit_cost_update(
            task_id="task-err",
            cost_delta=0.01,
            total_cost=0.05,
            model="test-model",
            stage="verify",
        )
