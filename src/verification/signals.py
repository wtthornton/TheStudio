"""JetStream signal emission for verification events.

Publishes verification_passed / verification_failed / verification_exhausted
to NATS JetStream for consumption by downstream components.
"""

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import nats
from nats.js import JetStreamContext

from src.dashboard.events_publisher import get_pipeline_jetstream
from src.settings import settings
from src.verification.runners.base import CheckResult

logger = logging.getLogger(__name__)

STREAM_NAME = "THESTUDIO_VERIFICATION"
SUBJECT_PREFIX = "thestudio.verification"

_js: JetStreamContext | None = None


async def get_jetstream() -> JetStreamContext:
    """Get or create a JetStream context (singleton)."""
    global _js
    if _js is None:
        nc = await nats.connect(settings.nats_url)
        _js = nc.jetstream()
        # Ensure stream exists
        try:
            await _js.find_stream_name_by_subject(f"{SUBJECT_PREFIX}.*")
        except Exception:
            await _js.add_stream(
                name=STREAM_NAME,
                subjects=[f"{SUBJECT_PREFIX}.*"],
            )
    return _js


def _build_payload(
    event: str,
    taskpacket_id: UUID,
    correlation_id: UUID,
    loopback_count: int,
    checks: list[CheckResult],
) -> bytes:
    """Build JSON payload for a verification signal."""
    return json.dumps({
        "event": event,
        "taskpacket_id": str(taskpacket_id),
        "correlation_id": str(correlation_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "loopback_count": loopback_count,
        "checks": [
            {
                "name": c.name,
                "result": "passed" if c.passed else "failed",
                "details": c.details,
                "duration_ms": c.duration_ms,
            }
            for c in checks
        ],
    }).encode()


async def _emit_pipeline_gate(
    passed: bool,
    taskpacket_id: UUID,
    correlation_id: UUID,
    stage: str = "verify",
) -> None:
    """Fire-and-forget gate event to THESTUDIO_PIPELINE stream."""
    try:
        js = await get_pipeline_jetstream()
        result = "pass" if passed else "fail"
        payload = json.dumps({
            "type": f"pipeline.gate.{result}",
            "data": {
                "stage": stage,
                "taskpacket_id": str(taskpacket_id),
                "correlation_id": str(correlation_id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }).encode()
        await js.publish(f"pipeline.gate.{result}", payload)
        logger.debug("Emitted pipeline.gate.%s for verify task=%s", result, taskpacket_id)
    except Exception:
        logger.debug("Failed to emit pipeline gate event for verify", exc_info=True)


async def emit_verification_passed(
    taskpacket_id: UUID,
    correlation_id: UUID,
    loopback_count: int,
    checks: list[CheckResult],
) -> None:
    """Emit verification_passed signal to JetStream."""
    js = await get_jetstream()
    payload = _build_payload(
        "verification_passed", taskpacket_id, correlation_id, loopback_count, checks
    )
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted verification_passed for %s", taskpacket_id)
    await _emit_pipeline_gate(True, taskpacket_id, correlation_id)


async def emit_verification_failed(
    taskpacket_id: UUID,
    correlation_id: UUID,
    loopback_count: int,
    checks: list[CheckResult],
) -> None:
    """Emit verification_failed signal to JetStream."""
    js = await get_jetstream()
    payload = _build_payload(
        "verification_failed", taskpacket_id, correlation_id, loopback_count, checks
    )
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted verification_failed for %s (loopback=%d)", taskpacket_id, loopback_count)
    await _emit_pipeline_gate(False, taskpacket_id, correlation_id)


async def emit_verification_exhausted(
    taskpacket_id: UUID,
    correlation_id: UUID,
    loopback_count: int,
    checks: list[CheckResult],
) -> None:
    """Emit verification_exhausted signal to JetStream."""
    js = await get_jetstream()
    payload = _build_payload(
        "verification_exhausted", taskpacket_id, correlation_id, loopback_count, checks
    )
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted verification_exhausted for %s", taskpacket_id)
    await _emit_pipeline_gate(False, taskpacket_id, correlation_id)
