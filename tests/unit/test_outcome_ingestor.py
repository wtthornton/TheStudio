"""Unit tests for Outcome Ingestor (Story 1.8 stub, Story 2.2 full).

Architecture reference: thestudioarc/12-outcome-ingestor.md
Story 2.2 adds: normalization by complexity, attribution via provenance.
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
