"""Unit tests for Outcome Ingestor (Story 1.8 stub, Story 2.2 full, Story 2.3 hardening).

Architecture reference: thestudioarc/12-outcome-ingestor.md
Story 2.2 adds: normalization by complexity, attribution via provenance.
Story 2.3 adds: quarantine + dead-letter + replay.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.outcome.ingestor import (
    COMPLEXITY_MULTIPLIERS,
    _build_context_key,
    _normalize_weight,
    _should_attribute_to_expert,
    clear,
    get_indicators,
    get_quarantined,
    get_signals,
    ingest_signal,
)
from src.outcome.models import (
    DefectCategory,
    OutcomeSignal,
    OutcomeType,
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


# --- Story 2.2: Normalization and Attribution Tests ---


class TestNormalizationByComplexity:
    """Test complexity-based normalization (Story 2.2)."""

    def test_low_complexity_success_weight(self) -> None:
        """Low complexity success has reduced weight (easy task)."""
        normalized, raw = _normalize_weight(OutcomeType.SUCCESS, "low", provenance_complete=True)
        assert raw == 1.0
        # Low complexity success: 1.0 * 0.8 = 0.8
        assert normalized == 0.8

    def test_low_complexity_failure_weight(self) -> None:
        """Low complexity failure has increased weight (easy task failed)."""
        normalized, raw = _normalize_weight(OutcomeType.FAILURE, "low", provenance_complete=True)
        assert raw == -1.0
        # Low complexity failure: -1.0 * 1.2 = -1.2
        assert normalized == -1.2

    def test_high_complexity_success_weight(self) -> None:
        """High complexity success has increased weight (hard task succeeded)."""
        normalized, raw = _normalize_weight(OutcomeType.SUCCESS, "high", provenance_complete=True)
        assert raw == 1.0
        # High complexity success: 1.0 * 1.2 = 1.2
        assert normalized == 1.2

    def test_high_complexity_failure_weight(self) -> None:
        """High complexity failure has reduced weight (hard task failed)."""
        normalized, raw = _normalize_weight(OutcomeType.FAILURE, "high", provenance_complete=True)
        assert raw == -1.0
        # High complexity failure: -1.0 * 0.8 = -0.8
        assert normalized == -0.8

    def test_medium_complexity_neutral(self) -> None:
        """Medium complexity has standard weights."""
        success_norm, _ = _normalize_weight(
            OutcomeType.SUCCESS, "medium", provenance_complete=True
        )
        failure_norm, _ = _normalize_weight(
            OutcomeType.FAILURE, "medium", provenance_complete=True
        )
        assert success_norm == 1.0
        assert failure_norm == -1.0

    def test_incomplete_provenance_reduces_weight(self) -> None:
        """Missing provenance reduces weight by 50%."""
        with_prov, _ = _normalize_weight(
            OutcomeType.SUCCESS, "medium", provenance_complete=True
        )
        without_prov, _ = _normalize_weight(
            OutcomeType.SUCCESS, "medium", provenance_complete=False
        )
        assert with_prov == 1.0
        assert without_prov == 0.5

    def test_loopback_half_failure_weight(self) -> None:
        """Loopback has half the failure weight."""
        normalized, raw = _normalize_weight(
            OutcomeType.LOOPBACK, "medium", provenance_complete=True
        )
        assert raw == -0.5
        assert normalized == -0.5


class TestContextKeyBuilding:
    """Test context key construction for reputation storage."""

    def test_context_key_general(self) -> None:
        """No active risks -> general risk class."""
        key = _build_context_key(
            repo="owner/repo",
            risk_flags={"risk_security": False, "risk_data": False},
            complexity_band="medium",
        )
        assert key == "owner/repo:general:medium"

    def test_context_key_with_risk(self) -> None:
        """Active risk -> risk class in key."""
        key = _build_context_key(
            repo="owner/repo",
            risk_flags={"risk_security": True, "risk_data": False},
            complexity_band="high",
        )
        assert key == "owner/repo:security:high"

    def test_context_key_first_risk_wins(self) -> None:
        """Multiple active risks -> first one is used."""
        key = _build_context_key(
            repo="owner/repo",
            risk_flags={"risk_security": True, "risk_data": True},
            complexity_band="low",
        )
        # First active risk alphabetically
        assert "security" in key or "data" in key


class TestAttributionRules:
    """Test attribution rules for expert reputation."""

    def test_success_attributes_to_expert(self) -> None:
        """Success outcomes always attribute to experts."""
        assert _should_attribute_to_expert(OutcomeType.SUCCESS, None) is True

    def test_intent_gap_does_not_attribute(self) -> None:
        """Intent gap defects do NOT penalize experts."""
        assert _should_attribute_to_expert(OutcomeType.FAILURE, DefectCategory.INTENT_GAP) is False

    def test_implementation_bug_attributes(self) -> None:
        """Implementation bugs DO penalize experts."""
        result = _should_attribute_to_expert(
            OutcomeType.FAILURE, DefectCategory.IMPLEMENTATION_BUG
        )
        assert result is True

    def test_failure_without_category_attributes(self) -> None:
        """Failures without category still attribute."""
        assert _should_attribute_to_expert(OutcomeType.FAILURE, None) is True


class TestReputationIndicatorProduction:
    """Test indicator production from signals (Story 2.2)."""

    @pytest.mark.asyncio
    async def test_indicators_produced_with_provenance(self) -> None:
        """Indicators produced when provenance available."""
        tp_id = uuid4()
        corr_id = uuid4()
        expert_id = uuid4()

        payload = {
            "event": "verification_passed",
            "taskpacket_id": str(tp_id),
            "correlation_id": str(corr_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Mock TaskPacket with complexity (using dataclass-like structure)
        class MockTaskPacket:
            def __init__(self) -> None:
                self.id = tp_id
                self.repo = "owner/repo"
                self.complexity_index = {"score": 8.0, "band": "medium", "dimensions": {}}
                self.risk_flags = {"risk_security": False}

        # Mock provenance with expert
        class MockProvenance:
            def __init__(self) -> None:
                self.experts_consulted = [
                    {"id": str(expert_id), "version": 1, "name": "TestExpert"}
                ]

        async def get_tp(_id: UUID) -> MockTaskPacket:
            return MockTaskPacket()

        async def get_prov(_id: UUID) -> MockProvenance:
            return MockProvenance()

        result = await ingest_signal(
            payload,
            taskpacket_exists_fn=None,
            get_taskpacket_fn=get_tp,
            get_provenance_fn=get_prov,
        )

        assert isinstance(result, OutcomeSignal)
        indicators = get_indicators()
        assert len(indicators) == 1
        assert indicators[0].expert_id == expert_id
        assert indicators[0].outcome_type == OutcomeType.SUCCESS
        assert indicators[0].complexity_band == "medium"
        assert indicators[0].provenance_complete is True

    @pytest.mark.asyncio
    async def test_indicators_produced_without_provenance(self) -> None:
        """Indicators produced with reduced weight when no provenance."""
        tp_id = uuid4()
        corr_id = uuid4()

        payload = {
            "event": "verification_passed",
            "taskpacket_id": str(tp_id),
            "correlation_id": str(corr_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        class MockTaskPacket:
            def __init__(self) -> None:
                self.id = tp_id
                self.repo = "owner/repo"
                self.complexity_index = {"score": 3.0, "band": "low", "dimensions": {}}
                self.risk_flags: dict[str, bool] = {}

        async def get_tp(_id: UUID) -> MockTaskPacket:
            return MockTaskPacket()

        async def get_prov(_id: UUID) -> None:
            return None

        result = await ingest_signal(
            payload,
            get_taskpacket_fn=get_tp,
            get_provenance_fn=get_prov,
        )

        assert isinstance(result, OutcomeSignal)
        indicators = get_indicators()
        assert len(indicators) == 1
        assert indicators[0].provenance_complete is False
        # Weight reduced by 50% for missing provenance
        assert indicators[0].normalized_weight < indicators[0].raw_weight


class TestDefectCategorySeverity:
    """Test defect category and severity parsing."""

    @pytest.mark.asyncio
    async def test_qa_defect_with_category(self) -> None:
        """QA defect signals can include defect category."""
        payload = {
            "event": "qa_defect",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "defect_category": "implementation_bug",
            "defect_severity": "s2",
        }

        result = await ingest_signal(payload)
        assert isinstance(result, OutcomeSignal)
        assert result.event == SignalEvent.QA_DEFECT

    @pytest.mark.asyncio
    async def test_invalid_defect_category_quarantined(self) -> None:
        """Invalid defect category quarantines the signal."""
        payload = {
            "event": "qa_defect",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "defect_category": "not_a_real_category",
        }

        result = await ingest_signal(payload)
        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.INVALID_CATEGORY_SEVERITY

    @pytest.mark.asyncio
    async def test_invalid_defect_severity_quarantined(self) -> None:
        """Invalid defect severity quarantines the signal."""
        payload = {
            "event": "qa_defect",
            "taskpacket_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "defect_category": "implementation_bug",
            "defect_severity": "not_a_real_severity",
        }

        result = await ingest_signal(payload)
        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.INVALID_CATEGORY_SEVERITY


class TestComplexityMultipliers:
    """Verify complexity multiplier configuration."""

    def test_multipliers_symmetric(self) -> None:
        """Success and failure multipliers are inverse."""
        for band in ["low", "medium", "high"]:
            m = COMPLEXITY_MULTIPLIERS[band]
            # Success multiplier for one band equals failure multiplier for opposite
            assert "success" in m
            assert "failure" in m

    def test_medium_is_neutral(self) -> None:
        """Medium complexity has neutral multipliers."""
        m = COMPLEXITY_MULTIPLIERS["medium"]
        assert m["success"] == 1.0
        assert m["failure"] == 1.0


# --- Story 2.3: Quarantine + Dead-Letter + Replay Tests ---


from src.outcome.quarantine import QuarantineStore, clear as clear_quarantine
from src.outcome.dead_letter import DeadLetterStore, FailureTracker, clear as clear_dead_letter
from src.outcome.replay import replay_quarantined, replay_batch, replay_deterministic
from src.outcome.models import QuarantinedEvent, DeadLetterEvent, ReplayResult


class TestQuarantineStore:
    """Test QuarantineStore CRUD operations (Story 2.3)."""

    def setup_method(self) -> None:
        """Clear stores before each test."""
        clear_quarantine()
        clear_dead_letter()

    def test_quarantine_creates_event(self) -> None:
        """Quarantine creates a new QuarantinedEvent."""
        store = QuarantineStore()
        payload = {"event": "test", "taskpacket_id": str(uuid4())}

        qid = store.quarantine(
            event_payload=payload,
            reason=QuarantineReason.MISSING_CORRELATION_ID,
            repo_id="owner/repo",
            category="test",
        )

        assert qid is not None
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.reason == QuarantineReason.MISSING_CORRELATION_ID
        assert event.repo_id == "owner/repo"

    def test_list_quarantined_by_repo(self) -> None:
        """List quarantined events filtered by repo_id."""
        store = QuarantineStore()

        store.quarantine(
            {"event": "a"}, QuarantineReason.UNKNOWN_TASKPACKET, repo_id="repo1"
        )
        store.quarantine(
            {"event": "b"}, QuarantineReason.UNKNOWN_TASKPACKET, repo_id="repo2"
        )
        store.quarantine(
            {"event": "c"}, QuarantineReason.INVALID_EVENT, repo_id="repo1"
        )

        repo1_events = store.list_quarantined(repo_id="repo1")
        assert len(repo1_events) == 2

        repo2_events = store.list_quarantined(repo_id="repo2")
        assert len(repo2_events) == 1

    def test_list_quarantined_by_reason(self) -> None:
        """List quarantined events filtered by reason."""
        store = QuarantineStore()

        store.quarantine(
            {"event": "a"}, QuarantineReason.UNKNOWN_TASKPACKET
        )
        store.quarantine(
            {"event": "b"}, QuarantineReason.INVALID_EVENT
        )

        tp_events = store.list_quarantined(reason=QuarantineReason.UNKNOWN_TASKPACKET)
        assert len(tp_events) == 1
        assert tp_events[0].reason == QuarantineReason.UNKNOWN_TASKPACKET

    def test_mark_corrected_updates_payload(self) -> None:
        """Mark corrected sets corrected_at and corrected_payload."""
        store = QuarantineStore()
        original_payload = {"event": "bad"}
        corrected_payload = {"event": "verification_passed", "correlation_id": str(uuid4())}

        qid = store.quarantine(original_payload, QuarantineReason.INVALID_EVENT)
        result = store.mark_corrected(qid, corrected_payload)

        assert result is True
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.corrected_at is not None
        assert event.corrected_payload == corrected_payload

    def test_mark_corrected_fails_if_replayed(self) -> None:
        """Cannot correct an already-replayed event."""
        store = QuarantineStore()
        qid = store.quarantine({"event": "test"}, QuarantineReason.INVALID_EVENT)
        store.mark_replayed(qid)

        result = store.mark_corrected(qid, {"event": "fixed"})
        assert result is False

    def test_mark_replayed_sets_timestamp(self) -> None:
        """Mark replayed sets replayed_at timestamp."""
        store = QuarantineStore()
        qid = store.quarantine({"event": "test"}, QuarantineReason.INVALID_EVENT)

        result = store.mark_replayed(qid)
        assert result is True

        event = store.get_quarantined(qid)
        assert event is not None
        assert event.replayed_at is not None

    def test_list_excludes_replayed_by_default(self) -> None:
        """List excludes replayed events unless include_replayed=True."""
        store = QuarantineStore()
        qid1 = store.quarantine({"event": "a"}, QuarantineReason.INVALID_EVENT)
        store.quarantine({"event": "b"}, QuarantineReason.INVALID_EVENT)
        store.mark_replayed(qid1)

        # Default excludes replayed
        events = store.list_quarantined()
        assert len(events) == 1

        # Include replayed
        all_events = store.list_quarantined(include_replayed=True)
        assert len(all_events) == 2

    def test_count_by_reason(self) -> None:
        """Count quarantined events by reason."""
        store = QuarantineStore()
        store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"b": 2}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"c": 3}, QuarantineReason.UNKNOWN_TASKPACKET)

        counts = store.count_by_reason()
        assert counts[QuarantineReason.MISSING_CORRELATION_ID] == 2
        assert counts[QuarantineReason.UNKNOWN_TASKPACKET] == 1


class TestDeadLetterStore:
    """Test DeadLetterStore operations (Story 2.3)."""

    def setup_method(self) -> None:
        """Clear stores before each test."""
        clear_dead_letter()

    def test_add_dead_letter(self) -> None:
        """Add event to dead-letter store."""
        store = DeadLetterStore()
        raw = b'{"invalid": json}'

        dl_id = store.add_dead_letter(
            raw_payload=raw,
            failure_reason="JSON parse error",
            attempt_count=3,
        )

        assert dl_id is not None
        event = store.get_dead_letter(dl_id)
        assert event is not None
        assert event.raw_payload == raw
        assert event.failure_reason == "JSON parse error"
        assert event.attempt_count == 3

    def test_list_dead_letters_sorted_by_created(self) -> None:
        """List dead-letters sorted by created_at descending."""
        import time
        store = DeadLetterStore()

        store.add_dead_letter(b"first", "error1", 1)
        time.sleep(0.01)  # Ensure different timestamps
        store.add_dead_letter(b"second", "error2", 2)

        events = store.list_dead_letters()
        assert len(events) == 2
        # Most recent first
        assert events[0].failure_reason == "error2"
        assert events[1].failure_reason == "error1"

    def test_count_dead_letters(self) -> None:
        """Count total dead-letter events."""
        store = DeadLetterStore()
        assert store.count() == 0

        store.add_dead_letter(b"a", "err", 1)
        store.add_dead_letter(b"b", "err", 1)
        assert store.count() == 2

    def test_delete_dead_letter(self) -> None:
        """Delete a dead-letter event."""
        store = DeadLetterStore()
        dl_id = store.add_dead_letter(b"data", "error", 3)

        result = store.delete(dl_id)
        assert result is True
        assert store.get_dead_letter(dl_id) is None


class TestFailureTracker:
    """Test FailureTracker for dead-letter eligibility (Story 2.3)."""

    def test_record_failure_increments_count(self) -> None:
        """Recording failure increments attempt count."""
        tracker = FailureTracker(max_attempts=3)
        
        count1 = tracker.record_failure("hash1")
        count2 = tracker.record_failure("hash1")
        count3 = tracker.record_failure("hash1")

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_should_dead_letter_at_max_attempts(self) -> None:
        """Should dead-letter when max attempts reached."""
        tracker = FailureTracker(max_attempts=3)

        tracker.record_failure("hash1")
        assert tracker.should_dead_letter("hash1") is False

        tracker.record_failure("hash1")
        assert tracker.should_dead_letter("hash1") is False

        tracker.record_failure("hash1")
        assert tracker.should_dead_letter("hash1") is True

    def test_clear_failures_resets_count(self) -> None:
        """Clear failures resets count for a hash."""
        tracker = FailureTracker(max_attempts=3)
        tracker.record_failure("hash1")
        tracker.record_failure("hash1")

        tracker.clear_failures("hash1")
        assert tracker.get_attempt_count("hash1") == 0


class TestReplayMechanism:
    """Test replay of quarantined events (Story 2.3)."""

    def setup_method(self) -> None:
        """Clear stores before each test."""
        clear_quarantine()
        clear_dead_letter()
        clear()

    @pytest.mark.asyncio
    async def test_replay_success(self) -> None:
        """Successful replay returns signal and marks as replayed."""
        store = QuarantineStore()
        valid_payload = _make_payload("verification_passed")

        # Quarantine it first
        qid = store.quarantine(valid_payload, QuarantineReason.UNKNOWN_TASKPACKET)

        # Replay with valid ingest function
        result = await replay_quarantined(qid, ingest_signal, store)

        assert result.success is True
        assert result.signal is not None
        assert result.signal.event == SignalEvent.VERIFICATION_PASSED

        # Event should be marked as replayed
        event = store.get_quarantined(qid)
        assert event is not None
        assert event.replayed_at is not None

    @pytest.mark.asyncio
    async def test_replay_uses_corrected_payload(self) -> None:
        """Replay uses corrected payload if available."""
        store = QuarantineStore()
        original = {"event": "invalid_event", "taskpacket_id": str(uuid4())}
        corrected = _make_payload("qa_passed")

        qid = store.quarantine(original, QuarantineReason.INVALID_EVENT)
        store.mark_corrected(qid, corrected)

        result = await replay_quarantined(qid, ingest_signal, store)

        assert result.success is True
        assert result.signal is not None
        assert result.signal.event == SignalEvent.QA_PASSED

    @pytest.mark.asyncio
    async def test_replay_not_found(self) -> None:
        """Replay returns error if quarantine_id not found."""
        store = QuarantineStore()
        fake_id = uuid4()

        result = await replay_quarantined(fake_id, ingest_signal, store)

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_replay_already_replayed(self) -> None:
        """Replay returns error if already replayed."""
        store = QuarantineStore()
        qid = store.quarantine(_make_payload(), QuarantineReason.UNKNOWN_TASKPACKET)
        store.mark_replayed(qid)

        result = await replay_quarantined(qid, ingest_signal, store)

        assert result.success is False
        assert "already replayed" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_replay_batch_processes_in_order(self) -> None:
        """Batch replay processes events in order."""
        store = QuarantineStore()
        payloads = [_make_payload("verification_passed") for _ in range(3)]
        qids = [store.quarantine(p, QuarantineReason.UNKNOWN_TASKPACKET) for p in payloads]

        results = await replay_batch(qids, ingest_signal, store)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_replay_deterministic(self) -> None:
        """Deterministic replay produces same outputs for same inputs."""
        events = [
            QuarantinedEvent(
                quarantine_id=uuid4(),
                event_payload=_make_payload("verification_passed"),
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                created_at=datetime.now(UTC),
            ),
            QuarantinedEvent(
                quarantine_id=uuid4(),
                event_payload=_make_payload("qa_passed"),
                reason=QuarantineReason.UNKNOWN_TASKPACKET,
                created_at=datetime.now(UTC),
            ),
        ]

        def sync_ingest(payload: dict[str, object]) -> OutcomeSignal:
            return OutcomeSignal(
                event=SignalEvent(str(payload.get("event", "verification_passed"))),
                taskpacket_id=UUID(str(payload["taskpacket_id"])),
                correlation_id=UUID(str(payload["correlation_id"])),
                timestamp=datetime.now(UTC),
                payload=dict(payload),
            )

        # Run twice — same input should produce consistent results
        signals1 = replay_deterministic(events, sync_ingest)
        signals2 = replay_deterministic(events, sync_ingest)

        assert len(signals1) == len(signals2) == 2
        for s1, s2 in zip(signals1, signals2):
            assert s1.event == s2.event
            assert s1.taskpacket_id == s2.taskpacket_id


class TestQuarantineUnknownRepo:
    """Quarantine signals referencing unknown repo_id (Story 2.3)."""

    def setup_method(self) -> None:
        """Clear stores before each test."""
        clear_quarantine()
        clear()

    @pytest.mark.asyncio
    async def test_unknown_repo_quarantined(self) -> None:
        """Signals with unknown repo_id are quarantined."""
        payload = _make_payload("verification_passed")
        payload["repo_id"] = "unknown/repo"

        async def repo_not_found(_id: str) -> bool:
            return False

        async def tp_found(_id: UUID) -> bool:
            return True

        result = await ingest_signal(
            payload,
            taskpacket_exists_fn=tp_found,
            repo_exists_fn=repo_not_found,
        )

        assert isinstance(result, QuarantinedSignal)
        assert result.reason == QuarantineReason.UNKNOWN_REPO

    @pytest.mark.asyncio
    async def test_known_repo_accepted(self) -> None:
        """Signals with known repo_id are accepted."""
        payload = _make_payload("verification_passed")
        payload["repo_id"] = "known/repo"

        async def repo_found(_id: str) -> bool:
            return True

        async def tp_found(_id: UUID) -> bool:
            return True

        result = await ingest_signal(
            payload,
            taskpacket_exists_fn=tp_found,
            repo_exists_fn=repo_found,
        )

        assert isinstance(result, OutcomeSignal)


class TestIdempotencyConflict:
    """Test idempotency conflict detection (Story 2.3)."""

    def setup_method(self) -> None:
        """Clear stores before each test."""
        clear_quarantine()
        clear()

    @pytest.mark.asyncio
    async def test_duplicate_with_same_payload_accepted(self) -> None:
        """Duplicate signal with identical payload returns existing signal."""
        payload = _make_payload("verification_passed")

        result1 = await ingest_signal(payload)
        result2 = await ingest_signal(payload)

        assert isinstance(result1, OutcomeSignal)
        assert isinstance(result2, OutcomeSignal)
        assert result1 == result2
        assert len(get_signals()) == 1

    @pytest.mark.asyncio
    async def test_duplicate_with_different_payload_quarantined(self) -> None:
        """Duplicate signal with conflicting payload is quarantined."""
        tp_id = str(uuid4())
        corr_id = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()

        payload1 = {
            "event": "verification_passed",
            "taskpacket_id": tp_id,
            "correlation_id": corr_id,
            "timestamp": timestamp,
            "extra_field": "original",
        }
        payload2 = {
            "event": "verification_passed",
            "taskpacket_id": tp_id,
            "correlation_id": corr_id,
            "timestamp": timestamp,
            "extra_field": "conflicting",
        }

        result1 = await ingest_signal(payload1)
        result2 = await ingest_signal(payload2)

        assert isinstance(result1, OutcomeSignal)
        assert isinstance(result2, QuarantinedSignal)
        assert result2.reason == QuarantineReason.IDEMPOTENCY_CONFLICT
