"""Outcome Ingestor Stub — consumes verification + QA signals, persists for analytics.

Stub implementation: in-memory storage. No JetStream consumer wiring.
Real consumer and DB persistence are Phase 2.

Architecture reference: thestudioarc/12-outcome-ingestor.md
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_OUTCOME_INGEST,
)
from src.observability.tracing import get_tracer
from src.outcome.models import (
    OutcomeSignal,
    QuarantinedSignal,
    QuarantineReason,
    SignalEvent,
)

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.outcome")


# In-memory stores (stub — replaced by DB in Phase 2)
_signals: list[OutcomeSignal] = []
_quarantined: list[QuarantinedSignal] = []


def get_signals() -> list[OutcomeSignal]:
    """Return all persisted signals (for analytics queries)."""
    return list(_signals)


def get_quarantined() -> list[QuarantinedSignal]:
    """Return all quarantined signals (for operator review)."""
    return list(_quarantined)


def clear() -> None:
    """Clear all stores (for testing)."""
    _signals.clear()
    _quarantined.clear()


async def ingest_signal(
    raw_payload: dict[str, Any],
    taskpacket_exists_fn: Any = None,
) -> OutcomeSignal | QuarantinedSignal:
    """Ingest a signal payload from JetStream.

    Validates the payload, correlates to a TaskPacket, and persists.
    Invalid signals are quarantined, not dropped.

    Args:
        raw_payload: The raw JSON payload from JetStream.
        taskpacket_exists_fn: Async callable(UUID) -> bool that checks
            whether a TaskPacket exists. If None, existence is assumed.

    Returns:
        OutcomeSignal if valid, QuarantinedSignal if quarantined.
    """
    with tracer.start_as_current_span(SPAN_OUTCOME_INGEST) as span:
        now = datetime.now(UTC)

        # Validate correlation_id present
        correlation_id_str = raw_payload.get("correlation_id")
        if not correlation_id_str:
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: missing correlation_id")
            return quarantined

        # Parse correlation_id
        try:
            correlation_id = UUID(str(correlation_id_str))
        except ValueError:
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.MISSING_CORRELATION_ID,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid correlation_id format")
            return quarantined

        span.set_attribute(ATTR_CORRELATION_ID, str(correlation_id))

        # Validate event type
        event_str = raw_payload.get("event", "")
        try:
            event = SignalEvent(event_str)
        except ValueError:
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.INVALID_EVENT,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid event type '%s'", event_str)
            return quarantined

        # Parse taskpacket_id
        taskpacket_id_str = raw_payload.get("taskpacket_id")
        if not taskpacket_id_str:
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: missing taskpacket_id")
            return quarantined

        try:
            taskpacket_id = UUID(str(taskpacket_id_str))
        except ValueError:
            quarantined = QuarantinedSignal(
                raw_payload=raw_payload,
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                timestamp=now,
            )
            _quarantined.append(quarantined)
            logger.warning("Quarantined signal: invalid taskpacket_id format")
            return quarantined

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))

        # Verify TaskPacket exists (if checker provided)
        if taskpacket_exists_fn is not None:
            exists = await taskpacket_exists_fn(taskpacket_id)
            if not exists:
                quarantined = QuarantinedSignal(
                    raw_payload=raw_payload,
                    reason=QuarantineReason.UNKNOWN_TASKPACKET,
                    timestamp=now,
                )
                _quarantined.append(quarantined)
                logger.warning(
                    "Quarantined signal: unknown TaskPacket %s", taskpacket_id,
                )
                return quarantined

        # Parse timestamp from payload or use now
        timestamp_str = raw_payload.get("timestamp")
        if timestamp_str:
            try:
                signal_ts = datetime.fromisoformat(str(timestamp_str))
            except ValueError:
                signal_ts = now
        else:
            signal_ts = now

        # Idempotency: check for duplicate (same event + taskpacket + timestamp)
        for existing in _signals:
            if (
                existing.event == event
                and existing.taskpacket_id == taskpacket_id
                and existing.timestamp == signal_ts
            ):
                logger.info(
                    "Duplicate signal ignored: %s for %s", event, taskpacket_id,
                )
                return existing

        # Persist signal
        signal = OutcomeSignal(
            event=event,
            taskpacket_id=taskpacket_id,
            correlation_id=correlation_id,
            timestamp=signal_ts,
            payload=raw_payload,
        )
        _signals.append(signal)

        logger.info(
            "Ingested signal %s for TaskPacket %s (correlation=%s)",
            event,
            taskpacket_id,
            correlation_id,
        )

        return signal
