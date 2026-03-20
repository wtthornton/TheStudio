"""SSE event streaming for dashboard — real-time pipeline events via NATS JetStream."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

import nats
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from nats.js import JetStreamContext

from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

STREAM_NAME = "THESTUDIO_PIPELINE"
SUBJECT_PATTERN = "pipeline.>"
_HEARTBEAT_INTERVAL_S = 15


async def ensure_stream(js: JetStreamContext) -> None:
    """Create THESTUDIO_PIPELINE JetStream stream if it does not exist."""
    try:
        await js.find_stream_name_by_subject("pipeline.>")
    except Exception:
        await js.add_stream(
            name=STREAM_NAME,
            subjects=["pipeline.>"],
        )
        logger.info("Created JetStream stream %s", STREAM_NAME)


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


async def _nats_event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events from NATS JetStream pipeline messages."""
    event_id = 0
    nc = None
    sub = None

    try:
        nc = await nats.connect(settings.nats_url)
        js = nc.jetstream()
        await ensure_stream(js)

        # Push-based subscription: messages arrive via asyncio iterator
        sub = await js.subscribe(
            SUBJECT_PATTERN,
            stream=STREAM_NAME,
            ordered_consumer=True,
        )
        logger.info("SSE client connected, subscribed to %s", SUBJECT_PATTERN)

        while True:
            try:
                msg = await asyncio.wait_for(
                    sub.next_msg(),
                    timeout=_HEARTBEAT_INTERVAL_S,
                )
                await msg.ack()
                payload = json.loads(msg.data.decode())
                event_type = payload.get("type", msg.subject)
                event_data = payload.get("data", payload)
                event_id += 1
                yield _format_sse(event_type, event_data, event_id)
            except TimeoutError:
                yield _format_heartbeat()
            except Exception:
                logger.exception("Error processing NATS message")
                yield _format_heartbeat()
    except Exception:
        logger.exception("Failed to connect to NATS for SSE stream")
        # Yield an error event so the client knows
        yield _format_sse("system.error", {"message": "NATS connection failed"}, 1)
    finally:
        if sub:
            try:
                await sub.unsubscribe()
            except Exception:
                logger.debug("Error unsubscribing", exc_info=True)
        if nc and nc.is_connected:
            try:
                await nc.drain()
            except Exception:
                logger.debug("Error draining NATS connection", exc_info=True)
        logger.info("SSE client disconnected, cleaned up NATS resources")


@router.get("/events/stream")
async def event_stream() -> StreamingResponse:
    """SSE endpoint streaming pipeline events from NATS JetStream."""
    return StreamingResponse(
        _nats_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
