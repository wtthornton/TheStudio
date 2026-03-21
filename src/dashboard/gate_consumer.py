"""NATS JetStream consumer — writes GateEvidence rows from verification/QA signals.

Subscribes to ``thestudio.verification.>`` and ``thestudio.qa.>`` on their
respective JetStream streams and persists gate results to the
``gate_evidence`` table for dashboard consumption (S2.B2b).

Started from ``src/app.py`` lifespan alongside the existing signal consumer.
"""

import asyncio
import json
import logging
from typing import Any

import nats

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task[None] | None = None


async def _persist_gate_evidence(payload: dict[str, Any]) -> None:
    """Write a single GateEvidence row from a decoded NATS message."""
    from src.dashboard.gates import GateEvidenceRow
    from src.db.connection import get_async_session

    task_id = payload.get("task_id") or payload.get("taskpacket_id")
    if not task_id:
        logger.debug("Gate message missing task_id, skipping: %s", payload)
        return

    stage = payload.get("stage", "unknown")
    result = payload.get("result", payload.get("outcome", "unknown"))
    checks = payload.get("checks")
    defect_category = payload.get("defect_category")
    evidence_artifact = payload.get("evidence") or payload.get("evidence_artifact")

    async with get_async_session() as session:
        row = GateEvidenceRow(
            task_id=task_id,
            stage=stage,
            result=result,
            checks=checks,
            defect_category=defect_category,
            evidence_artifact=evidence_artifact,
        )
        session.add(row)
        await session.commit()
        logger.debug(
            "Persisted gate_evidence: task=%s stage=%s result=%s",
            task_id,
            stage,
            result,
        )


async def _on_message(msg: Any) -> None:
    """Process a single NATS message from verification or QA streams."""
    try:
        payload = json.loads(msg.data)
        # Support nested data envelope ({"type": "...", "data": {...}})
        data = payload.get("data", payload)
        await _persist_gate_evidence(data)
        await msg.ack()
    except Exception:
        logger.exception("Failed to process gate evidence message")
        await msg.ack()  # Ack to avoid redelivery loop


async def start_gate_consumer(
    nats_url: str = "nats://localhost:4222",
) -> asyncio.Task[None]:
    """Start consuming verification + QA signals and writing GateEvidence rows.

    Creates durable subscriptions for:
    - ``thestudio.verification.>``
    - ``thestudio.qa.>``

    Returns the asyncio task running the consumer loop.
    """

    async def _run() -> None:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()

        # Ensure streams exist (they may already be created by the outcome consumer)
        for stream_name, subjects in [
            ("THESTUDIO_VERIFICATION", ["thestudio.verification.>"]),
            ("THESTUDIO_QA", ["thestudio.qa.>"]),
        ]:
            try:
                await js.find_stream_name_by_subject(subjects[0])
            except Exception:
                try:
                    await js.add_stream(name=stream_name, subjects=subjects)
                    logger.info("Created JetStream stream %s", stream_name)
                except Exception:
                    logger.debug(
                        "Could not create stream %s (may already exist)",
                        stream_name,
                        exc_info=True,
                    )

        await js.subscribe(
            "thestudio.verification.>",
            durable="dashboard-gate-verification",
            cb=_on_message,
        )
        await js.subscribe(
            "thestudio.qa.>",
            durable="dashboard-gate-qa",
            cb=_on_message,
        )

        logger.info("Gate evidence consumer started: verification + QA streams")

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await nc.drain()
            logger.info("Gate evidence consumer stopped gracefully")

    global _consumer_task
    _consumer_task = asyncio.create_task(_run())
    return _consumer_task


async def stop_gate_consumer() -> None:
    """Stop the gate evidence consumer."""
    global _consumer_task
    if _consumer_task is not None:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
