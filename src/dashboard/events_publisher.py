"""Fire-and-forget NATS publish helper for pipeline stage events.

Publishes pipeline.stage.enter / pipeline.stage.exit events to the
THESTUDIO_PIPELINE JetStream stream for dashboard consumption.
"""

import json
import logging
from datetime import UTC, datetime

import nats
from nats.js import JetStreamContext

from src.settings import settings

logger = logging.getLogger(__name__)

STREAM_NAME = "THESTUDIO_PIPELINE"
SUBJECT_PREFIX = "pipeline.stage"

_js: JetStreamContext | None = None


async def get_pipeline_jetstream() -> JetStreamContext:
    """Get or create a JetStream context for the pipeline stream (singleton)."""
    global _js
    if _js is None:
        nc = await nats.connect(settings.nats_url)
        _js = nc.jetstream()
        try:
            await _js.find_stream_name_by_subject("pipeline.>")
        except Exception:
            await _js.add_stream(
                name=STREAM_NAME,
                subjects=["pipeline.>"],
            )
            logger.info("Created JetStream stream %s", STREAM_NAME)
    return _js


async def emit_stage_enter(
    stage: str,
    taskpacket_id: str,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.stage.enter event (fire-and-forget).

    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps({
            "type": "pipeline.stage.enter",
            "data": {
                "stage": stage,
                "taskpacket_id": taskpacket_id,
                "correlation_id": correlation_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }).encode()
        await js.publish(f"{SUBJECT_PREFIX}.enter", payload)
        logger.debug("Emitted stage.enter for %s task=%s", stage, taskpacket_id)
    except Exception:
        logger.debug("Failed to emit stage.enter for %s", stage, exc_info=True)


async def emit_stage_exit(
    stage: str,
    taskpacket_id: str,
    *,
    correlation_id: str = "",
    success: bool = True,
) -> None:
    """Emit a pipeline.stage.exit event (fire-and-forget).

    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps({
            "type": "pipeline.stage.exit",
            "data": {
                "stage": stage,
                "taskpacket_id": taskpacket_id,
                "correlation_id": correlation_id,
                "success": success,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }).encode()
        await js.publish(f"{SUBJECT_PREFIX}.exit", payload)
        logger.debug("Emitted stage.exit for %s task=%s success=%s", stage, taskpacket_id, success)
    except Exception:
        logger.debug("Failed to emit stage.exit for %s", stage, exc_info=True)


async def emit_cost_update(
    task_id: str,
    cost_delta: float,
    total_cost: float,
    model: str,
    stage: str,
    *,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.cost_update event (fire-and-forget).

    Published on each model call so the dashboard can track running costs.
    Failures are logged but never raised — callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps({
            "type": "pipeline.cost_update",
            "data": {
                "task_id": task_id,
                "cost_delta": round(cost_delta, 6),
                "total_cost": round(total_cost, 6),
                "model": model,
                "stage": stage,
                "correlation_id": correlation_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }).encode()
        await js.publish("pipeline.cost_update", payload)
        logger.debug(
            "Emitted cost_update task=%s delta=%.4f total=%.4f stage=%s",
            task_id, cost_delta, total_cost, stage,
        )
    except Exception:
        logger.debug("Failed to emit cost_update for task=%s", task_id, exc_info=True)
