"""Unit tests for src/outcome/replay.py — replay mechanism for quarantined events.

Covers: replay_quarantined, replay_batch, replay_deterministic, verify_replay_determinism.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.outcome.models import (
    OutcomeSignal,
    QuarantinedEvent,
    QuarantineReason,
    ReplayResult,
    SignalEvent,
)
from src.outcome.quarantine import QuarantineStore, clear as clear_quarantine
from src.outcome.replay import (
    ReplayError,
    replay_batch,
    replay_deterministic,
    replay_quarantined,
    verify_replay_determinism,
)


@pytest.fixture(autouse=True)
def _clean_quarantine():
    """Clear in-memory quarantine store before each test."""
    clear_quarantine()


def _make_signal(**overrides) -> OutcomeSignal:
    """Build a minimal OutcomeSignal for test assertions."""
    defaults = {
        "event": SignalEvent.VERIFICATION_PASSED,
        "taskpacket_id": uuid4(),
        "correlation_id": uuid4(),
        "timestamp": datetime.now(UTC),
        "payload": {},
    }
    defaults.update(overrides)
    return OutcomeSignal(**defaults)


def _make_quarantined_event(**overrides) -> QuarantinedEvent:
    """Build a QuarantinedEvent for deterministic-replay tests."""
    defaults = {
        "quarantine_id": uuid4(),
        "event_payload": {"event": "verification_passed", "taskpacket_id": str(uuid4())},
        "reason": QuarantineReason.UNKNOWN_TASKPACKET,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return QuarantinedEvent(**defaults)


# ---------------------------------------------------------------------------
# replay_quarantined
# ---------------------------------------------------------------------------


class TestReplayQuarantinedSuccess:
    """Successful replay returns signal and marks event replayed."""

    async def test_success_with_original_payload(self):
        store = QuarantineStore()
        payload = {"event": "verification_passed", "taskpacket_id": str(uuid4())}
        qid = store.quarantine(payload, QuarantineReason.UNKNOWN_TASKPACKET)

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is True
        assert result.signal is signal
        assert result.quarantine_id == qid
        assert result.replayed_at is not None
        ingest_fn.assert_awaited_once_with(payload)

        # Event marked replayed in store
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.replayed_at is not None

    async def test_success_uses_corrected_payload(self):
        store = QuarantineStore()
        original = {"event": "bad"}
        corrected = {"event": "verification_passed", "correlation_id": str(uuid4())}

        qid = store.quarantine(original, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, corrected)

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is True
        # Must use corrected payload, not original
        ingest_fn.assert_awaited_once_with(corrected)


class TestReplayQuarantinedNotFound:
    """Replay of missing quarantine_id returns failure."""

    async def test_not_found(self):
        store = QuarantineStore()
        fake_id = uuid4()
        ingest_fn = AsyncMock()

        result = await replay_quarantined(fake_id, ingest_fn, quarantine_store=store)

        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.quarantine_id == fake_id
        ingest_fn.assert_not_awaited()


class TestReplayQuarantinedAlreadyReplayed:
    """Replay of already-replayed event returns failure."""

    async def test_already_replayed(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_replayed(qid)

        ingest_fn = AsyncMock()
        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is False
        assert "already replayed" in result.error.lower()
        ingest_fn.assert_not_awaited()


class TestReplayQuarantinedProducesAnotherQuarantine:
    """Replay that produces a non-OutcomeSignal result is treated as failure."""

    async def test_result_not_outcome_signal(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        # Ingest returns something that is NOT an OutcomeSignal (e.g. QuarantinedSignal)
        non_signal = MagicMock()
        non_signal.reason = "still_invalid"
        ingest_fn = AsyncMock(return_value=non_signal)

        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is False
        assert "another quarantine" in result.error.lower()

        # Event should NOT be marked replayed
        event = store.get_quarantined(qid)
        assert event.replayed_at is None

    async def test_result_not_outcome_signal_without_reason_attr(self):
        """Non-signal result without a 'reason' attr still handles gracefully."""
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        plain_obj = object()  # no .reason attribute
        ingest_fn = AsyncMock(return_value=plain_obj)

        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is False
        assert "another quarantine" in result.error.lower()


class TestReplayQuarantinedIngestException:
    """Replay handles exceptions from ingest_fn gracefully."""

    async def test_ingest_raises(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        ingest_fn = AsyncMock(side_effect=ValueError("parse error"))

        result = await replay_quarantined(qid, ingest_fn, quarantine_store=store)

        assert result.success is False
        assert "parse error" in result.error
        assert result.quarantine_id == qid


class TestReplayQuarantinedUsesGlobalStore:
    """replay_quarantined falls back to get_quarantine_store() when no store given."""

    async def test_uses_global_store(self):
        # Put an event in the global store
        from src.outcome.quarantine import get_quarantine_store

        store = get_quarantine_store()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        # Don't pass quarantine_store — should use global
        result = await replay_quarantined(qid, ingest_fn)

        assert result.success is True


# ---------------------------------------------------------------------------
# replay_batch
# ---------------------------------------------------------------------------


class TestReplayBatch:
    """Batch replay processes events sequentially and returns ordered results."""

    async def test_batch_all_succeed(self):
        store = QuarantineStore()
        qids = [
            store.quarantine({"event": "a"}, QuarantineReason.INVALID_EVENT)
            for _ in range(3)
        ]

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        results = await replay_batch(qids, ingest_fn, quarantine_store=store)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.quarantine_id for r in results] == qids

    async def test_batch_mixed_results(self):
        store = QuarantineStore()
        qid_good = store.quarantine({"event": "ok"}, QuarantineReason.INVALID_EVENT)
        qid_bad = uuid4()  # not in store — will fail

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        results = await replay_batch([qid_good, qid_bad], ingest_fn, quarantine_store=store)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    async def test_batch_empty_list(self):
        store = QuarantineStore()
        ingest_fn = AsyncMock()

        results = await replay_batch([], ingest_fn, quarantine_store=store)

        assert results == []
        ingest_fn.assert_not_awaited()

    async def test_batch_uses_global_store(self):
        """replay_batch falls back to get_quarantine_store() when no store given."""
        from src.outcome.quarantine import get_quarantine_store

        store = get_quarantine_store()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        results = await replay_batch([qid], ingest_fn)
        assert len(results) == 1
        assert results[0].success is True


# ---------------------------------------------------------------------------
# replay_deterministic
# ---------------------------------------------------------------------------


class TestReplayDeterministic:
    """Synchronous deterministic replay for backfill / audit."""

    def test_produces_signals_in_order(self):
        tp1, tp2 = uuid4(), uuid4()
        events = [
            _make_quarantined_event(event_payload={"tp": str(tp1)}),
            _make_quarantined_event(event_payload={"tp": str(tp2)}),
        ]

        def sync_ingest(payload):
            return _make_signal(taskpacket_id=uuid4())

        signals = replay_deterministic(events, sync_ingest)
        assert len(signals) == 2

    def test_uses_corrected_payload_when_available(self):
        corrected = {"corrected": True}
        event = _make_quarantined_event(
            event_payload={"original": True},
            corrected_payload=corrected,
        )

        captured = []

        def sync_ingest(payload):
            captured.append(payload)
            return _make_signal()

        replay_deterministic([event], sync_ingest)
        assert captured == [corrected]

    def test_uses_original_payload_when_no_correction(self):
        original = {"original": True}
        event = _make_quarantined_event(event_payload=original, corrected_payload=None)

        captured = []

        def sync_ingest(payload):
            captured.append(payload)
            return _make_signal()

        replay_deterministic([event], sync_ingest)
        assert captured == [original]

    def test_skips_non_outcome_signal_results(self):
        event = _make_quarantined_event()

        def sync_ingest(payload):
            return "not a signal"

        signals = replay_deterministic([event], sync_ingest)
        assert signals == []

    def test_continues_on_exception(self):
        events = [
            _make_quarantined_event(),
            _make_quarantined_event(),
        ]

        call_count = 0

        def sync_ingest(payload):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            return _make_signal()

        signals = replay_deterministic(events, sync_ingest)
        # First event errored, second succeeded
        assert len(signals) == 1
        assert call_count == 2

    def test_empty_events_returns_empty(self):
        signals = replay_deterministic([], lambda p: _make_signal())
        assert signals == []


# ---------------------------------------------------------------------------
# verify_replay_determinism
# ---------------------------------------------------------------------------


class TestVerifyReplayDeterminism:
    """Verify determinism by replaying corrected events twice."""

    async def test_deterministic_returns_true(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        # Ingest returns the same OutcomeSignal each time
        stable_signal = _make_signal()
        ingest_fn = AsyncMock(return_value=stable_signal)

        is_det, discrepancies = await verify_replay_determinism(store, ingest_fn)

        assert is_det is True
        assert discrepancies == []
        assert ingest_fn.await_count == 2  # called twice for one event

    async def test_non_deterministic_returns_discrepancy(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        # Ingest returns different signals each call
        call_count = 0

        async def unstable_ingest(payload):
            nonlocal call_count
            call_count += 1
            return _make_signal(
                event=SignalEvent.VERIFICATION_PASSED if call_count == 1 else SignalEvent.QA_PASSED,
            )

        is_det, discrepancies = await verify_replay_determinism(store, unstable_ingest)

        assert is_det is False
        assert len(discrepancies) == 1
        assert str(qid) in discrepancies[0]

    async def test_type_mismatch_returns_discrepancy(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        call_count = 0

        async def mixed_ingest(payload):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_signal()
            return "not a signal"

        is_det, discrepancies = await verify_replay_determinism(store, mixed_ingest)

        assert is_det is False
        assert len(discrepancies) == 1
        assert "types differ" in discrepancies[0]

    async def test_ingest_exception_returns_discrepancy(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        ingest_fn = AsyncMock(side_effect=RuntimeError("boom"))

        is_det, discrepancies = await verify_replay_determinism(store, ingest_fn)

        assert is_det is False
        assert len(discrepancies) == 1
        assert "error" in discrepancies[0].lower()

    async def test_no_corrected_events_returns_true(self):
        store = QuarantineStore()
        # Quarantine without correcting
        store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)

        ingest_fn = AsyncMock()

        is_det, discrepancies = await verify_replay_determinism(store, ingest_fn)

        assert is_det is True
        assert discrepancies == []
        ingest_fn.assert_not_awaited()

    async def test_empty_store_returns_true(self):
        store = QuarantineStore()
        ingest_fn = AsyncMock()

        is_det, discrepancies = await verify_replay_determinism(store, ingest_fn)

        assert is_det is True
        assert discrepancies == []

    async def test_filters_by_repo_id(self):
        store = QuarantineStore()

        # Two events in different repos, both corrected
        qid1 = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT, repo_id="repo1")
        store.mark_corrected(qid1, {"event": "fixed"})

        qid2 = store.quarantine({"event": "y"}, QuarantineReason.INVALID_EVENT, repo_id="repo2")
        store.mark_corrected(qid2, {"event": "fixed"})

        signal = _make_signal()
        ingest_fn = AsyncMock(return_value=signal)

        is_det, discrepancies = await verify_replay_determinism(
            store, ingest_fn, repo_id="repo1"
        )

        assert is_det is True
        # Only 1 event (repo1), called twice = 2 awaits
        assert ingest_fn.await_count == 2

    async def test_skips_already_replayed_events(self):
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "fixed"})
        store.mark_replayed(qid)

        ingest_fn = AsyncMock()

        is_det, discrepancies = await verify_replay_determinism(store, ingest_fn)

        assert is_det is True
        ingest_fn.assert_not_awaited()

    async def test_taskpacket_id_difference_detected(self):
        """Differing taskpacket_id across two runs is a discrepancy."""
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        call_count = 0

        async def varying_ingest(payload):
            nonlocal call_count
            call_count += 1
            return _make_signal(taskpacket_id=uuid4())  # different each time

        is_det, discrepancies = await verify_replay_determinism(store, varying_ingest)

        assert is_det is False
        assert len(discrepancies) == 1

    async def test_correlation_id_difference_detected(self):
        """Differing correlation_id across two runs is a discrepancy."""
        store = QuarantineStore()
        qid = store.quarantine({"event": "x"}, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, {"event": "verification_passed"})

        tp_id = uuid4()
        call_count = 0

        async def varying_ingest(payload):
            nonlocal call_count
            call_count += 1
            return _make_signal(
                taskpacket_id=tp_id,
                correlation_id=uuid4(),  # different each time
            )

        is_det, discrepancies = await verify_replay_determinism(store, varying_ingest)

        assert is_det is False
        assert len(discrepancies) == 1


# ---------------------------------------------------------------------------
# ReplayError
# ---------------------------------------------------------------------------


class TestReplayError:
    """ReplayError is a proper Exception subclass."""

    def test_is_exception(self):
        err = ReplayError("something broke")
        assert isinstance(err, Exception)
        assert str(err) == "something broke"
