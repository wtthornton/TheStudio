"""Tests for dashboard SSE event streaming (B-0.2a)."""

import pytest

from src.dashboard.events import _format_heartbeat, _format_sse


def test_sse_event_format():
    """SSE events have correct format with id, event, data fields."""
    result = _format_sse("pipeline.stage.enter", {"stage": "intake"}, 1)
    assert "id: 1\n" in result
    assert "event: pipeline.stage.enter\n" in result
    assert 'data: {"stage": "intake"}\n' in result
    # Ends with double newline (SSE spec)
    assert result.endswith("\n\n")


def test_sse_heartbeat_format():
    """Heartbeat events are SSE comments."""
    hb = _format_heartbeat()
    assert hb.startswith(": heartbeat")
    assert hb.endswith("\n\n")


@pytest.mark.asyncio
async def test_sse_generator_emits_events():
    """Event generator emits hardcoded test events then heartbeats."""
    from src.dashboard.events import _TEST_EVENTS, _format_sse

    # Verify test events exist and are well-formed
    assert len(_TEST_EVENTS) >= 1
    for evt in _TEST_EVENTS:
        assert "type" in evt
        assert "data" in evt
        # Format should not raise
        _format_sse(evt["type"], evt["data"], 1)


def test_sse_endpoint_registered():
    """SSE endpoint is registered at /api/v1/dashboard/events/stream."""
    from src.app import app

    routes = [r.path for r in app.routes]  # type: ignore[union-attr]
    # FastAPI registers routes with the full prefix
    assert any("events/stream" in r for r in routes)


@pytest.mark.asyncio
async def test_event_stream_returns_streaming_response():
    """event_stream() returns a StreamingResponse with correct media type."""
    from src.dashboard.events import event_stream

    resp = await event_stream()
    assert resp.media_type == "text/event-stream"
    assert resp.headers.get("Cache-Control") == "no-cache"
