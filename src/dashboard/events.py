"""SSE event streaming for dashboard — real-time pipeline events."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Hardcoded test events for PoC (B-0.2a), replaced by NATS in B-0.2b
_TEST_EVENTS: list[dict] = [
    {
        "type": "pipeline.stage.enter",
        "data": {"stage": "intake", "task_id": "test-001"},
    },
    {
        "type": "pipeline.stage.exit",
        "data": {"stage": "intake", "task_id": "test-001", "duration_ms": 120},
    },
    {
        "type": "pipeline.stage.enter",
        "data": {"stage": "context", "task_id": "test-001"},
    },
]

_HEARTBEAT_INTERVAL_S = 15
_TEST_EVENT_INTERVAL_S = 5


def _format_sse(event_type: str, data: dict, event_id: int) -> str:
    """Format a server-sent event per SSE spec."""
    lines = [
        f"id: {event_id}",
        f"event: {event_type}",
        f"data: {json.dumps(data)}",
        "",
        "",
    ]
    return "\n".join(lines)


def _format_heartbeat() -> str:
    """Format an SSE comment as heartbeat."""
    return f": heartbeat {int(time.time())}\n\n"


async def _event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events: hardcoded test events then heartbeats."""
    event_id = 0

    # Emit test events
    for evt in _TEST_EVENTS:
        event_id += 1
        yield _format_sse(evt["type"], evt["data"], event_id)
        await asyncio.sleep(_TEST_EVENT_INTERVAL_S)

    # Then heartbeat indefinitely
    while True:
        yield _format_heartbeat()
        await asyncio.sleep(_HEARTBEAT_INTERVAL_S)


@router.get("/events/stream")
async def event_stream() -> StreamingResponse:
    """SSE endpoint streaming pipeline events."""
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
