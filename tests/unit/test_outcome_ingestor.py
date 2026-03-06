"""Unit tests for Outcome Ingestor Stub (Story 1.8).

Architecture reference: thestudioarc/12-outcome-ingestor.md
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.outcome.ingestor import (
    clear,
    get_quarantined,
    get_signals,
    ingest_signal,
)
from src.outcome.models import (
    OutcomeSignal,
    QuarantinedSignal,
    QuarantineReason,
    SignalEvent,
)


@pytest.fixture(autouse=True)
def _clean_stores() -> None:
    """Clear in-memory stores before each test."""
    clear()


def _make_payload(
    event: str = "verification_passed",
    taskpacket_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, object]:
    return {
        "event": event,
        "taskpacket_id": taskpacket_id or str(uuid4()),
        "correlation_id": correlation_id or str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
    }


class TestIngestVerificationPassed:
    """Ingest verification_passed signal."""

    @pytest.mark.asyncio
    async def test_ingest_verification_passed(self) -> None:
        payload = _make_payload("verification_passed")
        result = await ingest_signal(payload)

        assert isinstance(result, OutcomeSignal)
        assert result.event == SignalEvent.VERIFICATION_PASSED
        assert len(get_signals()) == 1


class TestIngestQAPassed:
    """Ingest qa_passed signal."""

    @pytest.mark.asyncio
    async def test_ingest_qa_passed(self) -> None:
        payload = _make_payload("qa_passed")
        result = await ingest_signal(payload)

        assert isinstance(result, OutcomeSignal)
        assert result.event == SignalEvent.QA_PASSED
        assert len(get_signals()) == 1


class TestCorrelateByCorrelationId:
    """Signals correlated to TaskPacket by correlation_id."""

    @pytest.mark.asyncio
    async def test_correlation_id_preserved(self) -> None:
        corr_id = uuid4()
        tp_id = uuid4()
        payload = _make_payload(
            correlation_id=str(corr_id), taskpacket_id=str(tp_id),
        )
        result = await ingest_signal(payload)

        assert isinstance(result, OutcomeSignal)
        assert result.correlation_id == corr_id
        assert result.taskpacket_id == tp_id


class TestQuarantineMissingCorrelationId:
    """Quarantine signals with missing correlation_id."""

    @pytest.mark.asyncio
    async def test_missing_correlation_id_quarantined(self) -> None:
        payload = {
            "event": "verification_passed",
            "taskpacket_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        result = await ingest_signal(payload)

        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.MISSING_CORRELATION_ID
        assert len(get_quarantined()) == 1
        assert len(get_signals()) == 0


class TestQuarantineUnknownTaskPacket:
    """Quarantine signals referencing unknown TaskPacket."""

    @pytest.mark.asyncio
    async def test_unknown_taskpacket_quarantined(self) -> None:
        payload = _make_payload()

        async def tp_not_found(_id: object) -> bool:
            return False

        result = await ingest_signal(payload, taskpacket_exists_fn=tp_not_found)

        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.UNKNOWN_TASKPACKET
        assert len(get_quarantined()) == 1
        assert len(get_signals()) == 0


class TestQuarantineInvalidEvent:
    """Quarantine signals with invalid event type."""

    @pytest.mark.asyncio
    async def test_invalid_event_quarantined(self) -> None:
        payload = _make_payload("not_a_real_event")
        result = await ingest_signal(payload)

        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.INVALID_EVENT
        assert len(get_quarantined()) == 1


class TestPersistForAnalytics:
    """Signals persisted for analytics queries."""

    @pytest.mark.asyncio
    async def test_multiple_signals_persisted(self) -> None:
        await ingest_signal(_make_payload("verification_passed"))
        await ingest_signal(_make_payload("qa_passed"))
        await ingest_signal(_make_payload("qa_defect"))

        signals = get_signals()
        assert len(signals) == 3
        events = {s.event for s in signals}
        assert events == {
            SignalEvent.VERIFICATION_PASSED,
            SignalEvent.QA_PASSED,
            SignalEvent.QA_DEFECT,
        }


class TestIdempotentHandling:
    """Duplicate signals handled idempotently."""

    @pytest.mark.asyncio
    async def test_duplicate_signal_not_persisted_twice(self) -> None:
        payload = _make_payload("verification_passed")
        result1 = await ingest_signal(payload)
        result2 = await ingest_signal(payload)

        assert isinstance(result1, OutcomeSignal)
        assert isinstance(result2, OutcomeSignal)
        # Same signal — only stored once
        assert len(get_signals()) == 1
