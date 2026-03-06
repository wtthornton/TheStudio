"""Replay mechanism — replays quarantined events after correction.

Architecture reference: thestudioarc/12-outcome-ingestor.md lines 97-100

Replay and correction:
- quarantined events can be corrected by an operator (or automated fix) and replayed
- replay must be deterministic: same ordered events produce same aggregates

Replay maintains determinism by:
1. Using the corrected_payload if available, otherwise the original event_payload
2. Processing events in order (caller provides ordered list)
3. Linking replayed signals to the original quarantine_id for audit
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.outcome.models import OutcomeSignal, QuarantinedEvent, ReplayResult
from src.outcome.quarantine import QuarantineStore, get_quarantine_store

logger = logging.getLogger(__name__)


# Type alias for the ingest function signature
IngestFn = Callable[[dict[str, Any]], Any]


class ReplayError(Exception):
    """Error during replay processing."""


async def replay_quarantined(
    quarantine_id: UUID,
    ingest_fn: IngestFn,
    quarantine_store: QuarantineStore | None = None,
) -> ReplayResult:
    """Replay a single quarantined event.

    Uses the corrected_payload if available, otherwise the original event_payload.
    Marks the event as replayed on success.

    Args:
        quarantine_id: The UUID of the quarantined event to replay.
        ingest_fn: Async callable that processes the payload (e.g., ingest_signal).
        quarantine_store: Optional quarantine store (uses global if not provided).

    Returns:
        ReplayResult with success status and the resulting signal if successful.
    """
    store = quarantine_store or get_quarantine_store()
    now = datetime.now(UTC)

    event = store.get_quarantined(quarantine_id)
    if event is None:
        return ReplayResult(
            quarantine_id=quarantine_id,
            success=False,
            error=f"Quarantine event {quarantine_id} not found",
            replayed_at=now,
        )

    if event.replayed_at is not None:
        return ReplayResult(
            quarantine_id=quarantine_id,
            success=False,
            error=f"Quarantine event {quarantine_id} already replayed at {event.replayed_at}",
            replayed_at=now,
        )

    # Use corrected payload if available
    payload = event.corrected_payload or event.event_payload

    try:
        result = await ingest_fn(payload)

        # Check if result is a valid signal (not quarantined again)
        if isinstance(result, OutcomeSignal):
            store.mark_replayed(quarantine_id)
            logger.info(
                "Successfully replayed quarantine_id %s -> signal %s",
                quarantine_id, result.event,
            )
            return ReplayResult(
                quarantine_id=quarantine_id,
                success=True,
                signal=result,
                replayed_at=now,
            )
        else:
            # Result is a QuarantinedSignal — replay failed
            logger.warning(
                "Replay of quarantine_id %s produced another quarantine: %s",
                quarantine_id, result.reason if hasattr(result, "reason") else "unknown",
            )
            return ReplayResult(
                quarantine_id=quarantine_id,
                success=False,
                error="Replay produced another quarantine event",
                replayed_at=now,
            )
    except Exception as e:
        logger.error("Replay of quarantine_id %s failed: %s", quarantine_id, e)
        return ReplayResult(
            quarantine_id=quarantine_id,
            success=False,
            error=str(e),
            replayed_at=now,
        )


async def replay_batch(
    quarantine_ids: list[UUID],
    ingest_fn: IngestFn,
    quarantine_store: QuarantineStore | None = None,
) -> list[ReplayResult]:
    """Replay multiple quarantined events in order.

    Processes events sequentially to maintain determinism.
    The order of quarantine_ids determines the processing order.

    Args:
        quarantine_ids: List of quarantine_ids to replay, in order.
        ingest_fn: Async callable that processes the payload.
        quarantine_store: Optional quarantine store (uses global if not provided).

    Returns:
        List of ReplayResult for each event, in the same order as input.
    """
    store = quarantine_store or get_quarantine_store()
    results: list[ReplayResult] = []

    for qid in quarantine_ids:
        result = await replay_quarantined(qid, ingest_fn, store)
        results.append(result)

    return results


def replay_deterministic(
    events: list[QuarantinedEvent],
    ingest_fn: Callable[[dict[str, Any]], OutcomeSignal],
) -> list[OutcomeSignal]:
    """Replay a batch of events deterministically (synchronous version).

    Given the same ordered event list, produces the same output signals.
    This is used for backfill and audit verification.

    Args:
        events: Ordered list of QuarantinedEvent to replay.
        ingest_fn: Synchronous callable that processes the payload.

    Returns:
        List of OutcomeSignal produced (in order).
    """
    signals: list[OutcomeSignal] = []

    for event in events:
        payload = event.corrected_payload or event.event_payload
        try:
            signal = ingest_fn(payload)
            if isinstance(signal, OutcomeSignal):
                signals.append(signal)
        except Exception as e:
            logger.error(
                "Deterministic replay of quarantine_id %s failed: %s",
                event.quarantine_id, e,
            )
            # Continue processing — deterministic replay should not stop on errors

    return signals


async def verify_replay_determinism(
    quarantine_store: QuarantineStore,
    ingest_fn: IngestFn,
    repo_id: str | None = None,
) -> tuple[bool, list[str]]:
    """Verify that replay is deterministic for a set of events.

    Replays all corrected events twice and compares results.

    Args:
        quarantine_store: The quarantine store to verify.
        ingest_fn: Async callable that processes the payload.
        repo_id: Optional filter by repo_id.

    Returns:
        Tuple of (is_deterministic, list of discrepancies).
    """
    # Get all corrected but not yet replayed events
    events = quarantine_store.list_quarantined(
        repo_id=repo_id,
        include_replayed=False,
    )
    corrected = [e for e in events if e.corrected_at is not None]

    if not corrected:
        return (True, [])

    discrepancies: list[str] = []

    for event in corrected:
        payload = event.corrected_payload or event.event_payload

        # Run ingest twice
        try:
            result1 = await ingest_fn(payload)
            result2 = await ingest_fn(payload)

            # Compare results (basic equality check)
            if isinstance(result1, OutcomeSignal) and isinstance(result2, OutcomeSignal):
                if (
                    result1.event != result2.event
                    or result1.taskpacket_id != result2.taskpacket_id
                    or result1.correlation_id != result2.correlation_id
                ):
                    discrepancies.append(
                        f"quarantine_id={event.quarantine_id}: results differ"
                    )
            elif type(result1) is not type(result2):
                discrepancies.append(
                    f"quarantine_id={event.quarantine_id}: result types differ"
                )
        except Exception as e:
            discrepancies.append(f"quarantine_id={event.quarantine_id}: error - {e}")

    return (len(discrepancies) == 0, discrepancies)
