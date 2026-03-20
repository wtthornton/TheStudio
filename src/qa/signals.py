"""JetStream signal emission for QA events.

Publishes qa_passed / qa_defect / qa_rework to NATS JetStream.
Follows the same pattern as verification/signals.py.

Architecture reference: thestudioarc/14-qa-quality-layer.md
"""

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import nats
from nats.js import JetStreamContext

from src.dashboard.events_publisher import get_pipeline_jetstream
from src.qa.defect import QADefect
from src.settings import settings

logger = logging.getLogger(__name__)

STREAM_NAME = "THESTUDIO_QA"
SUBJECT_PREFIX = "thestudio.qa"

_js: JetStreamContext | None = None


async def get_jetstream() -> JetStreamContext:
    """Get or create a JetStream context for QA signals."""
    global _js
    if _js is None:
        nc = await nats.connect(settings.nats_url)
        _js = nc.jetstream()
        try:
            await _js.find_stream_name_by_subject(f"{SUBJECT_PREFIX}.*")
        except Exception:
            await _js.add_stream(
                name=STREAM_NAME,
                subjects=[f"{SUBJECT_PREFIX}.*"],
            )
    return _js


def _build_qa_payload(
    event: str,
    taskpacket_id: UUID,
    correlation_id: UUID,
    defects: list[QADefect] | None = None,
) -> bytes:
    """Build JSON payload for a QA signal."""
    payload: dict[str, object] = {
        "event": event,
        "taskpacket_id": str(taskpacket_id),
        "correlation_id": str(correlation_id),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if defects:
        payload["defects"] = [
            {
                "category": d.category.value,
                "severity": d.severity.value,
                "description": d.description,
                "acceptance_criterion": d.acceptance_criterion,
            }
            for d in defects
        ]
    return json.dumps(payload).encode()


async def _emit_pipeline_gate(
    passed: bool,
    taskpacket_id: UUID,
    correlation_id: UUID,
    stage: str = "qa",
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
        logger.debug("Emitted pipeline.gate.%s for qa task=%s", result, taskpacket_id)
    except Exception:
        logger.debug("Failed to emit pipeline gate event for qa", exc_info=True)


async def emit_qa_passed(
    taskpacket_id: UUID,
    correlation_id: UUID,
) -> None:
    """Emit qa_passed signal to JetStream."""
    js = await get_jetstream()
    payload = _build_qa_payload("qa_passed", taskpacket_id, correlation_id)
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted qa_passed for %s", taskpacket_id)
    await _emit_pipeline_gate(True, taskpacket_id, correlation_id)


async def emit_qa_defect(
    taskpacket_id: UUID,
    correlation_id: UUID,
    defects: list[QADefect],
) -> None:
    """Emit qa_defect signal to JetStream."""
    js = await get_jetstream()
    payload = _build_qa_payload("qa_defect", taskpacket_id, correlation_id, defects)
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted qa_defect for %s (%d defects)", taskpacket_id, len(defects))
    await _emit_pipeline_gate(False, taskpacket_id, correlation_id)


async def emit_qa_rework(
    taskpacket_id: UUID,
    correlation_id: UUID,
    defects: list[QADefect],
) -> None:
    """Emit qa_rework signal to JetStream."""
    js = await get_jetstream()
    payload = _build_qa_payload("qa_rework", taskpacket_id, correlation_id, defects)
    subject = f"{SUBJECT_PREFIX}.{taskpacket_id}"
    await js.publish(subject, payload)
    logger.info("Emitted qa_rework for %s (%d defects)", taskpacket_id, len(defects))
    await _emit_pipeline_gate(False, taskpacket_id, correlation_id)
