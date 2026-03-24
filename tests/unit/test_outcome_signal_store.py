"""Unit tests for OutcomeSignalRow persistence (Epic 39 Story 39.0c).

Covers:
- save_signal() persists an OutcomeSignal as an OutcomeSignalRow
- list_signals() queries with filters
- signal_row_to_outcome_signal() round-trip conversion
- ingestor db_session path calls save_signal without breaking on failure
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.outcome.ingestor import clear, ingest_signal
from src.outcome.models import OutcomeSignal, SignalEvent
from src.outcome.signal_store import (
    OutcomeSignalRow,
    list_signals,
    save_signal,
    signal_row_to_outcome_signal,
)


def _make_signal(
    event: SignalEvent = SignalEvent.VERIFICATION_PASSED,
) -> OutcomeSignal:
    return OutcomeSignal(
        event=event,
        taskpacket_id=uuid4(),
        correlation_id=uuid4(),
        timestamp=datetime.now(UTC),
        payload={"event": event.value, "source": "test"},
    )


def _make_row(signal: OutcomeSignal) -> OutcomeSignalRow:
    row = OutcomeSignalRow()
    row.id = uuid4()
    row.task_id = signal.taskpacket_id
    row.correlation_id = signal.correlation_id
    row.signal_type = signal.event.value
    row.payload = signal.payload
    row.signal_at = signal.timestamp
    row.created_at = datetime.now(UTC)
    return row


class TestSaveSignal:
    """save_signal() adds row to session and commits."""

    @pytest.mark.asyncio
    async def test_save_signal_adds_and_commits(self) -> None:
        signal = _make_signal()
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        row = await save_signal(session, signal)

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert row.signal_type == signal.event.value
        assert row.task_id == signal.taskpacket_id
        assert row.correlation_id == signal.correlation_id
        assert row.payload == signal.payload
        assert row.signal_at == signal.timestamp

    @pytest.mark.asyncio
    async def test_save_signal_all_event_types(self) -> None:
        for event in SignalEvent:
            signal = _make_signal(event)
            session = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.refresh = AsyncMock()

            row = await save_signal(session, signal)
            assert row.signal_type == event.value


class TestListSignals:
    """list_signals() queries with optional filters."""

    @pytest.mark.asyncio
    async def test_list_signals_no_filter(self) -> None:
        signal = _make_signal()
        row = _make_row(signal)

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        session.execute = AsyncMock(return_value=mock_result)

        rows = await list_signals(session)
        assert len(rows) == 1
        assert rows[0].signal_type == signal.event.value

    @pytest.mark.asyncio
    async def test_list_signals_task_id_filter(self) -> None:
        signal = _make_signal()
        row = _make_row(signal)

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        session.execute = AsyncMock(return_value=mock_result)

        rows = await list_signals(session, task_id=signal.taskpacket_id)
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_list_signals_signal_type_filter(self) -> None:
        signal = _make_signal(SignalEvent.QA_DEFECT)
        row = _make_row(signal)

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        session.execute = AsyncMock(return_value=mock_result)

        rows = await list_signals(session, signal_type=SignalEvent.QA_DEFECT)
        assert len(rows) == 1
        assert rows[0].signal_type == "qa_defect"

    @pytest.mark.asyncio
    async def test_list_signals_empty(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        rows = await list_signals(session)
        assert rows == []


class TestSignalRowToOutcomeSignal:
    """signal_row_to_outcome_signal() round-trips correctly."""

    def test_round_trip_known_signal(self) -> None:
        signal = _make_signal(SignalEvent.QA_PASSED)
        row = _make_row(signal)

        result = signal_row_to_outcome_signal(row)
        assert result.event == SignalEvent.QA_PASSED
        assert result.taskpacket_id == signal.taskpacket_id
        assert result.correlation_id == signal.correlation_id
        assert result.timestamp == signal.timestamp
        assert result.payload == signal.payload

    def test_null_task_id_falls_back_to_zero_uuid(self) -> None:
        signal = _make_signal()
        row = _make_row(signal)
        row.task_id = None
        row.correlation_id = None

        result = signal_row_to_outcome_signal(row)
        assert result.taskpacket_id == UUID(int=0)
        assert result.correlation_id == UUID(int=0)


class TestIngestorDbSessionPath:
    """ingestor.ingest_signal() calls save_signal when db_session provided."""

    @pytest.fixture(autouse=True)
    def _clean(self) -> None:
        clear()

    @pytest.mark.asyncio
    async def test_ingestor_calls_save_signal_on_success(self) -> None:
        """When db_session is provided, save_signal is called for valid signals."""
        payload = {
            "event": "verification_passed",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        session = AsyncMock()

        with patch("src.outcome.signal_store.save_signal", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = MagicMock(spec=OutcomeSignalRow)
            result = await ingest_signal(payload, db_session=session)

        mock_save.assert_awaited_once()
        call_signal = mock_save.call_args[0][1]
        assert call_signal.event == SignalEvent.VERIFICATION_PASSED

    @pytest.mark.asyncio
    async def test_ingestor_skips_save_signal_when_no_session(self) -> None:
        """When db_session is None, save_signal is NOT called."""
        payload = {
            "event": "qa_passed",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        with patch("src.outcome.signal_store.save_signal", new_callable=AsyncMock) as mock_save:
            await ingest_signal(payload, db_session=None)

        mock_save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ingestor_continues_on_db_failure(self) -> None:
        """DB persistence failure does NOT abort signal ingestion."""
        payload = {
            "event": "verification_passed",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        session = AsyncMock()

        with patch(
            "src.outcome.signal_store.save_signal",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            result = await ingest_signal(payload, db_session=session)

        # Signal still ingested in-memory despite DB failure
        from src.outcome.ingestor import get_signals
        assert isinstance(result, OutcomeSignal)
        assert len(get_signals()) == 1
