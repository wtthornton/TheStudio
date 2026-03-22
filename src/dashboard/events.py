"""SSE event streaming for dashboard — real-time pipeline events via NATS JetStream."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

import nats
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, DeliverPolicy

from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

STREAM_NAME = "THESTUDIO_PIPELINE"
SUBJECT_PATTERN = "pipeline.>"
# Epic 38.25: also subscribe to GitHub bridge events on same stream
GITHUB_SUBJECT_PATTERN = "github.event.>"
_HEARTBEAT_INTERVAL_S = 15
_MAX_REPLAY_GAP = 1000

# All subjects carried on the THESTUDIO_PIPELINE stream
_STREAM_SUBJECTS = ["pipeline.>", "github.event.>"]


async def ensure_stream(js: JetStreamContext) -> None:
    """Create or verify the THESTUDIO_PIPELINE JetStream stream.

    Epic 38.25: stream carries both pipeline.> and github.event.> subjects
    so webhook bridge events flow through the same SSE connection.

    If the stream already exists (legacy single-subject config), we attempt
    to add the github.event.> subject filter. Failures are non-fatal — the
    stream remains usable for pipeline.> events; github events will be
    silently dropped until the stream is updated.
    """
    try:
        existing_name = await js.find_stream_name_by_subject("pipeline.>")
        # Stream exists — check if github.event.> is already included
        try:
            info = await js.stream_info(existing_name)
            current_subjects = list(info.config.subjects or [])
            if "github.event.>" not in current_subjects:
                new_subjects = current_subjects + ["github.event.>"]
                await js.add_stream(name=existing_name, subjects=new_subjects)
                logger.info(
                    "Updated stream %s to include github.event.> subjects",
                    existing_name,
                )
        except Exception:
            # Non-fatal: stream update failed, pipeline.> still works
            logger.debug(
                "Could not add github.event.> to stream — GitHub events may not flow via SSE",
                exc_info=True,
            )
    except Exception:
        # Stream does not exist — create it with both subject filters
        await js.add_stream(
            name=STREAM_NAME,
            subjects=_STREAM_SUBJECTS,
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


def _parse_last_event_id(raw: str | None) -> int | None:
    """Parse Last-Event-ID header into a stream sequence number, or None."""
    if not raw:
        return None
    try:
        seq = int(raw.strip())
        return seq if seq > 0 else None
    except (ValueError, TypeError):
        return None


async def _get_stream_last_seq(js: JetStreamContext) -> int:
    """Return the last sequence number in the pipeline stream, or 0."""
    try:
        info = await js.stream_info(STREAM_NAME)
        return info.state.last_seq
    except Exception:
        return 0


async def _nats_event_generator(
    last_event_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from NATS JetStream pipeline messages.

    If *last_event_id* is set the subscription resumes from that stream
    sequence.  When the gap between the requested sequence and the current
    stream head exceeds _MAX_REPLAY_GAP a ``system.full_state`` marker is
    emitted and the subscription starts from the latest message instead.
    """
    nc = None
    sub = None

    try:
        nc = await nats.connect(settings.nats_url)
        js = nc.jetstream()
        await ensure_stream(js)

        # Determine subscription start position
        config: ConsumerConfig | None = None
        if last_event_id is not None:
            current_last = await _get_stream_last_seq(js)
            gap = current_last - last_event_id

            if gap > _MAX_REPLAY_GAP:
                # Gap too large — skip replay, notify client
                logger.info(
                    "SSE reconnect gap %d exceeds max %d, sending full_state",
                    gap,
                    _MAX_REPLAY_GAP,
                )
                yield _format_sse(
                    "system.full_state",
                    {"reason": "gap_exceeded", "missed": gap},
                    current_last,
                )
                # Start from latest
                config = ConsumerConfig(
                    deliver_policy=DeliverPolicy.LAST,
                )
            else:
                # Replay from the message after the last one the client saw
                resume_seq = last_event_id + 1
                logger.info(
                    "SSE reconnect: replaying from seq %d (gap=%d)",
                    resume_seq,
                    gap,
                )
                config = ConsumerConfig(
                    deliver_policy=DeliverPolicy.BY_START_SEQUENCE,
                    opt_start_seq=resume_seq,
                )

        # Push-based subscription: messages arrive via asyncio iterator.
        # Epic 38.25: subscribe to ">" (all subjects in stream) so both
        # pipeline.> and github.event.> messages are delivered.
        sub = await js.subscribe(
            ">",
            stream=STREAM_NAME,
            ordered_consumer=True,
            config=config,
        )
        logger.info(
            "SSE client connected, subscribed to all subjects in stream %s",
            STREAM_NAME,
        )

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

                # Use NATS stream sequence as SSE event ID for reconnection
                meta = msg.metadata
                event_id = meta.sequence.stream if meta else 0
                yield _format_sse(event_type, event_data, event_id)
            except TimeoutError:
                yield _format_heartbeat()
            except Exception:
                logger.exception("Error processing NATS message")
                yield _format_heartbeat()
    except Exception:
        logger.exception("Failed to connect to NATS for SSE stream")
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


def _verify_token(token: str | None) -> None:
    """Raise 401 if dashboard_token is configured and the supplied token does not match."""
    required = settings.dashboard_token
    if not required:
        # No token configured — dev mode, allow all
        return
    if not token or token != required:
        raise HTTPException(status_code=401, detail="Invalid or missing dashboard token")


@router.get("/events/stream")
async def event_stream(
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    token: str | None = Query(None),
) -> StreamingResponse:
    """SSE endpoint streaming pipeline events from NATS JetStream.

    Supports reconnection via the standard ``Last-Event-ID`` header.
    Requires ``?token=`` query param when ``dashboard_token`` is set.
    """
    _verify_token(token)
    parsed_id = _parse_last_event_id(last_event_id)
    return StreamingResponse(
        _nats_event_generator(last_event_id=parsed_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
