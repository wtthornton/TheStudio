"""JetStream consumer — subscribes to verification + QA signal streams.

Creates durable subscriptions for:
- THESTUDIO_VERIFICATION (subject: thestudio.verification.*)
- THESTUDIO_QA (subject: thestudio.qa.*)

Messages are decoded and passed to ingest_signal() for processing.

Architecture reference: thestudioarc/12-outcome-ingestor.md
"""

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task[None] | None = None


async def _process_message(data: bytes) -> None:
    """Decode and pass to ingest_signal."""
    from src.outcome.ingestor import ingest_signal

    payload = json.loads(data)
    await ingest_signal(payload)


async def start_signal_consumer(
    nats_url: str = "nats://localhost:4222",
) -> asyncio.Task[None]:
    """Start consuming from verification + QA JetStream streams.

    Creates durable subscriptions for:
    - THESTUDIO_VERIFICATION (subject: thestudio.verification.*)
    - THESTUDIO_QA (subject: thestudio.qa.*)

    Args:
        nats_url: NATS server URL to connect to.

    Returns:
        The asyncio task running the consumer loop.
    """
    import nats

    async def _run() -> None:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()

        async def _on_verification(msg: Any) -> None:
            try:
                await _process_message(msg.data)
                await msg.ack()
            except Exception:
                logger.exception("Failed to process verification signal")
                await msg.ack()  # Ack on quarantine too

        async def _on_qa(msg: Any) -> None:
            try:
                await _process_message(msg.data)
                await msg.ack()
            except Exception:
                logger.exception("Failed to process QA signal")
                await msg.ack()

        await js.subscribe(
            "thestudio.verification.*",
            durable="thestudio-verification-consumer",
            cb=_on_verification,
        )
        await js.subscribe(
            "thestudio.qa.*",
            durable="thestudio-qa-consumer",
            cb=_on_qa,
        )

        logger.info("Signal consumer started: verification + QA streams")

        # Keep running until cancelled
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await nc.drain()
            logger.info("Signal consumer stopped gracefully")

    global _consumer_task
    _consumer_task = asyncio.create_task(_run())
    return _consumer_task


async def stop_signal_consumer() -> None:
    """Stop the signal consumer."""
    global _consumer_task
    if _consumer_task is not None:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
