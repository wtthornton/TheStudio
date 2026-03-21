"""Fire-and-forget NATS publish helper for pipeline activity events.

Publishes ``pipeline.activity`` events to the THESTUDIO_PIPELINE
JetStream stream for dashboard Activity Stream consumption (S3.B1a/B1b).

Supported activity types:
- file_read, file_edit, search, test_run, shell, reasoning, llm_call
"""

import json
import logging
from datetime import UTC, datetime

from src.dashboard.events_publisher import get_pipeline_jetstream

logger = logging.getLogger(__name__)


async def emit_activity(
    task_id: str,
    stage: str,
    activity_type: str,
    content: str,
    *,
    subphase: str = "",
    detail: str = "",
    metadata: dict | None = None,
    correlation_id: str = "",
) -> None:
    """Emit a pipeline.activity event (fire-and-forget).

    Args:
        task_id: ID of the TaskPacket this activity belongs to.
        stage: Current pipeline stage (e.g. "implement", "verify").
        activity_type: One of file_read, file_edit, search, test_run,
            shell, reasoning, llm_call.
        content: Human-readable summary of the activity.
        subphase: Optional sub-phase grouping (e.g. "CONTEXT GATHERING").
        detail: Optional extended detail (diff preview, error trace, etc.).
        metadata: Optional structured metadata (JSONB).
        correlation_id: Request correlation ID for tracing.

    Failures are logged but never raised -- callers must not be blocked.
    """
    try:
        js = await get_pipeline_jetstream()
        payload = json.dumps(
            {
                "type": "pipeline.activity",
                "data": {
                    "task_id": task_id,
                    "stage": stage,
                    "activity_type": activity_type,
                    "content": content,
                    "subphase": subphase,
                    "detail": detail,
                    "metadata": metadata,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        ).encode()
        await js.publish("pipeline.activity", payload)
        logger.debug(
            "Emitted activity task=%s stage=%s type=%s",
            task_id,
            stage,
            activity_type,
        )
    except Exception:
        logger.debug(
            "Failed to emit activity for task=%s type=%s",
            task_id,
            activity_type,
            exc_info=True,
        )
