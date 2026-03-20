"""Tests for dashboard SSE event streaming (B-0.2a, B-0.2b)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dashboard.events import (
    STREAM_NAME,
    SUBJECT_PATTERN,
    _format_heartbeat,
    _format_sse,
    _nats_event_generator,
    ensure_stream,
)


def test_sse_event_format():
    """SSE events have correct format with id, event, data fields."""
    result = _format_sse("pipeline.stage.enter", {"stage": "intake"}, 1)
    assert "id: 1\n" in result
    assert "event: pipeline.stage.enter\n" in result
    assert 'data: {"stage": "intake"}\n' in result
    assert result.endswith("\n\n")


def test_sse_heartbeat_format():
    """Heartbeat events are SSE comments."""
    hb = _format_heartbeat()
    assert hb.startswith(": heartbeat")
    assert hb.endswith("\n\n")


def test_sse_endpoint_registered():
    """SSE endpoint is registered at /api/v1/dashboard/events/stream."""
    from src.app import app

    routes = [r.path for r in app.routes]  # type: ignore[union-attr]
    assert any("events/stream" in r for r in routes)


@pytest.mark.asyncio
async def test_event_stream_returns_streaming_response():
    """event_stream() returns a StreamingResponse with correct media type."""
    from src.dashboard.events import event_stream

    resp = await event_stream()
    assert resp.media_type == "text/event-stream"
    assert resp.headers.get("Cache-Control") == "no-cache"


def test_stream_name_and_subject():
    """Stream config constants are correct."""
    assert STREAM_NAME == "THESTUDIO_PIPELINE"
    assert SUBJECT_PATTERN == "pipeline.>"


@pytest.mark.asyncio
async def test_ensure_stream_creates_when_missing():
    """ensure_stream creates stream when find_stream_name_by_subject raises."""
    js = AsyncMock()
    js.find_stream_name_by_subject.side_effect = Exception("not found")
    await ensure_stream(js)
    js.add_stream.assert_awaited_once_with(
        name=STREAM_NAME,
        subjects=["pipeline.>"],
    )


@pytest.mark.asyncio
async def test_ensure_stream_skips_when_exists():
    """ensure_stream does nothing when stream already exists."""
    js = AsyncMock()
    js.find_stream_name_by_subject.return_value = STREAM_NAME
    await ensure_stream(js)
    js.add_stream.assert_not_awaited()


@pytest.mark.asyncio
async def test_nats_generator_yields_events_from_messages():
    """Generator yields SSE events from NATS messages."""
    payload = {
        "type": "pipeline.stage.enter",
        "data": {"stage": "intake", "task_id": "t-001"},
    }
    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode()
    mock_msg.subject = "pipeline.stage.enter"

    mock_sub = AsyncMock()
    call_count = 0

    async def _next_msg(timeout=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_msg
        raise asyncio.CancelledError()

    mock_sub.next_msg = _next_msg
    mock_sub.unsubscribe = AsyncMock()

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        events = []
        gen = _nats_event_generator()
        try:
            async for event in gen:
                events.append(event)
        except asyncio.CancelledError:
            pass

    assert len(events) >= 1
    assert "pipeline.stage.enter" in events[0]
    assert "intake" in events[0]
    assert "id: 1" in events[0]


@pytest.mark.asyncio
async def test_nats_generator_heartbeat_on_timeout():
    """Generator yields heartbeat when no NATS message within timeout."""
    mock_sub = AsyncMock()
    call_count = 0

    async def _next_msg(timeout=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError()
        raise asyncio.CancelledError()

    mock_sub.next_msg = _next_msg
    mock_sub.unsubscribe = AsyncMock()

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        events = []
        gen = _nats_event_generator()
        try:
            async for event in gen:
                events.append(event)
        except asyncio.CancelledError:
            pass

    assert len(events) >= 1
    assert events[0].startswith(": heartbeat")


@pytest.mark.asyncio
async def test_nats_generator_cleanup_on_disconnect():
    """Generator cleans up NATS resources on client disconnect."""
    mock_sub = AsyncMock()
    mock_sub.next_msg = AsyncMock(side_effect=asyncio.CancelledError())
    mock_sub.unsubscribe = AsyncMock()

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True
    mock_nc.drain = AsyncMock()

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        gen = _nats_event_generator()
        try:
            async for _ in gen:
                pass
        except asyncio.CancelledError:
            pass

    mock_sub.unsubscribe.assert_awaited_once()
    mock_nc.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_nats_generator_error_event_on_connection_failure():
    """Generator yields error event when NATS connection fails."""
    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(side_effect=ConnectionRefusedError())

        events = []
        async for event in _nats_event_generator():
            events.append(event)

    assert len(events) == 1
    assert "system.error" in events[0]
    assert "NATS connection failed" in events[0]
