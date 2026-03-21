"""Tests for dashboard SSE event streaming (B-0.2a, B-0.2b, B-0.3)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.dashboard.events import (
    STREAM_NAME,
    SUBJECT_PATTERN,
    _format_heartbeat,
    _format_sse,
    _nats_event_generator,
    _parse_last_event_id,
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

    resp = await event_stream(last_event_id=None, token=None)
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


def _make_mock_msg(payload: dict, subject: str, stream_seq: int = 1) -> AsyncMock:
    """Create a mock NATS JetStream message with metadata."""
    mock_msg = AsyncMock()
    mock_msg.data = json.dumps(payload).encode()
    mock_msg.subject = subject
    seq_pair = MagicMock()
    seq_pair.stream = stream_seq
    seq_pair.consumer = stream_seq
    meta = MagicMock()
    meta.sequence = seq_pair
    mock_msg.metadata = meta
    return mock_msg


@pytest.mark.asyncio
async def test_nats_generator_yields_events_from_messages():
    """Generator yields SSE events from NATS messages."""
    payload = {
        "type": "pipeline.stage.enter",
        "data": {"stage": "intake", "task_id": "t-001"},
    }
    mock_msg = _make_mock_msg(payload, "pipeline.stage.enter", stream_seq=42)

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
    # SSE event ID should be the NATS stream sequence
    assert "id: 42" in events[0]


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


# --- B-0.3: Last-Event-ID reconnection ---


class TestParseLastEventId:
    """Tests for _parse_last_event_id helper."""

    def test_none(self):
        assert _parse_last_event_id(None) is None

    def test_empty(self):
        assert _parse_last_event_id("") is None

    def test_valid_int(self):
        assert _parse_last_event_id("42") == 42

    def test_with_whitespace(self):
        assert _parse_last_event_id("  100  ") == 100

    def test_zero(self):
        assert _parse_last_event_id("0") is None

    def test_negative(self):
        assert _parse_last_event_id("-5") is None

    def test_non_numeric(self):
        assert _parse_last_event_id("abc") is None


@pytest.mark.asyncio
async def test_reconnect_replays_from_last_event_id():
    """Reconnect with Last-Event-ID subscribes with BY_START_SEQUENCE."""
    from nats.js.api import DeliverPolicy

    payload = {
        "type": "pipeline.stage.enter",
        "data": {"stage": "context"},
    }
    mock_msg = _make_mock_msg(payload, "pipeline.stage.enter", stream_seq=55)

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

    # Stream info says last_seq is 60, client says 50 → gap=10, within limit
    stream_state = MagicMock()
    stream_state.last_seq = 60
    stream_info = MagicMock()
    stream_info.state = stream_state

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME
    mock_js.stream_info.return_value = stream_info

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        events = []
        gen = _nats_event_generator(last_event_id=50)
        try:
            async for event in gen:
                events.append(event)
        except asyncio.CancelledError:
            pass

    # Should have subscribed with BY_START_SEQUENCE config
    call_args = mock_js.subscribe.call_args
    config = call_args.kwargs.get("config")
    assert config is not None
    assert config.deliver_policy == DeliverPolicy.BY_START_SEQUENCE
    assert config.opt_start_seq == 51  # last_event_id + 1

    # Should have received the event
    assert len(events) >= 1
    assert "context" in events[0]


@pytest.mark.asyncio
async def test_reconnect_full_state_on_large_gap():
    """Gap > _MAX_REPLAY_GAP sends system.full_state and starts from LAST."""
    from nats.js.api import DeliverPolicy

    # No real messages needed — we just check the full_state event
    mock_sub = AsyncMock()
    mock_sub.next_msg = AsyncMock(side_effect=asyncio.CancelledError())
    mock_sub.unsubscribe = AsyncMock()

    stream_state = MagicMock()
    stream_state.last_seq = 5000
    stream_info = MagicMock()
    stream_info.state = stream_state

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME
    mock_js.stream_info.return_value = stream_info

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        events = []
        # last_event_id=100, current=5000 → gap=4900 > 1000
        gen = _nats_event_generator(last_event_id=100)
        try:
            async for event in gen:
                events.append(event)
        except asyncio.CancelledError:
            pass

    # First event should be system.full_state
    assert len(events) >= 1
    assert "system.full_state" in events[0]
    assert "gap_exceeded" in events[0]

    # Subscription should use LAST deliver policy
    call_args = mock_js.subscribe.call_args
    config = call_args.kwargs.get("config")
    assert config is not None
    assert config.deliver_policy == DeliverPolicy.LAST


@pytest.mark.asyncio
async def test_reconnect_no_header_subscribes_normally():
    """No Last-Event-ID → no config passed (default ordered consumer)."""
    mock_sub = AsyncMock()
    mock_sub.next_msg = AsyncMock(side_effect=asyncio.CancelledError())
    mock_sub.unsubscribe = AsyncMock()

    mock_js = AsyncMock()
    mock_js.subscribe.return_value = mock_sub
    mock_js.find_stream_name_by_subject.return_value = STREAM_NAME

    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    mock_nc.is_connected = True

    with patch("src.dashboard.events.nats") as mock_nats:
        mock_nats.connect = AsyncMock(return_value=mock_nc)

        gen = _nats_event_generator(last_event_id=None)
        try:
            async for _ in gen:
                pass
        except asyncio.CancelledError:
            pass

    call_args = mock_js.subscribe.call_args
    config = call_args.kwargs.get("config")
    assert config is None


@pytest.mark.asyncio
async def test_event_stream_passes_last_event_id():
    """event_stream endpoint parses Last-Event-ID header."""
    from src.dashboard.events import event_stream

    resp = await event_stream(last_event_id="42", token=None)
    assert resp.media_type == "text/event-stream"


# --- B-0.7: Auth token on SSE endpoint ---


class TestSSEAuth:
    """Tests for ?token= query param authentication on the SSE endpoint."""

    @pytest.mark.asyncio
    async def test_no_token_required_when_dashboard_token_empty(self):
        """No auth needed when dashboard_token is not configured."""
        from src.dashboard.events import event_stream

        resp = await event_stream(last_event_id=None, token=None)
        assert resp.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_401_without_token_when_configured(self):
        """Returns 401 when dashboard_token is set but no token provided."""
        from src.dashboard.events import event_stream

        with patch("src.dashboard.events.settings") as mock_settings:
            mock_settings.dashboard_token = "secret-token-123"
            mock_settings.nats_url = "nats://localhost:4222"
            with pytest.raises(HTTPException) as exc_info:
                await event_stream(last_event_id=None, token=None)
            assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_401_with_wrong_token(self):
        """Returns 401 when token does not match dashboard_token."""
        from src.dashboard.events import event_stream

        with patch("src.dashboard.events.settings") as mock_settings:
            mock_settings.dashboard_token = "secret-token-123"
            mock_settings.nats_url = "nats://localhost:4222"
            with pytest.raises(HTTPException) as exc_info:
                await event_stream(last_event_id=None, token="wrong-token")
            assert exc_info.value.status_code == 401  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_200_with_valid_token(self):
        """Returns streaming response when valid token provided."""
        from src.dashboard.events import event_stream

        with patch("src.dashboard.events.settings") as mock_settings:
            mock_settings.dashboard_token = "secret-token-123"
            mock_settings.nats_url = "nats://localhost:4222"
            resp = await event_stream(last_event_id=None, token="secret-token-123")
            assert resp.media_type == "text/event-stream"
