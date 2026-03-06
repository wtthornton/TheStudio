"""Unit tests for Reopen Event Handling (Story 2.4).

Architecture reference: thestudioarc/12-outcome-ingestor.md lines 110-127
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.outcome.reopen import (
    RECENT_REOPEN_DAYS,
    ReopenClassification,
    ReopenEvent,
    ReopenEventProcessor,
    ReopenSource,
    clear,
    get_reopen_events,
    get_reopen_indicators,
    get_reopen_outcomes,
)


@pytest.fixture(autouse=True)
def _clean_stores() -> None:
    """Clear stores before each test."""
    clear()


def _make_reopen_event(
    source: ReopenSource = ReopenSource.ISSUE_REOPENED,
    repo_id: str = "owner/repo",
    days_since_merge: float | None = 3.0,
    labels: list[str] | None = None,
    ac_failing: list[str] | None = None,
    has_compliance_bypass: bool = False,
    original_taskpacket_id: UUID | None = None,
) -> ReopenEvent:
    """Create a test ReopenEvent."""
    now = datetime.now(UTC)
    merge_ts = None
    if days_since_merge is not None:
        merge_ts = now - timedelta(days=days_since_merge)

    return ReopenEvent(
        source=source,
        repo_id=repo_id,
        issue_number=123,
        pr_number=456,
        original_pr_number=456,
        original_taskpacket_id=original_taskpacket_id,
        timestamp=now,
        labels=labels or [],
        title="Test issue",
        body="Test body",
        original_merge_timestamp=merge_ts,
        has_compliance_bypass=has_compliance_bypass,
        ac_failing=ac_failing or [],
    )


class TestReopenClassificationIntentGap:
    """Test intent_gap classification."""

    @pytest.mark.asyncio
    async def test_recent_reopen_with_ac_failing(self) -> None:
        """Reopen within 7 days with AC failing -> intent_gap."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            days_since_merge=3.0,
            ac_failing=["User can login", "Password reset works"],
        )

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.INTENT_GAP
        assert "AC failing" in outcome.reason


class TestReopenClassificationImplementationBug:
    """Test implementation_bug classification."""

    @pytest.mark.asyncio
    async def test_recent_reopen_without_ac_failing(self) -> None:
        """Reopen within 7 days without AC failing -> implementation_bug."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            days_since_merge=5.0,
            ac_failing=[],
        )

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.IMPLEMENTATION_BUG
        assert "new failure mode" in outcome.reason.lower()


class TestReopenClassificationRegression:
    """Test regression classification."""

    @pytest.mark.asyncio
    async def test_late_reopen(self) -> None:
        """Reopen after 7 days -> regression."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(days_since_merge=10.0)

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.REGRESSION
        assert "after" in outcome.reason.lower()

    @pytest.mark.asyncio
    async def test_rollback_pr(self) -> None:
        """Rollback PR -> regression."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            source=ReopenSource.ROLLBACK_PR,
            days_since_merge=2.0,  # Even if recent
        )

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.REGRESSION
        assert "rollback" in outcome.reason.lower()

    @pytest.mark.asyncio
    async def test_regression_issue_label(self) -> None:
        """New issue with regression label -> regression."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            source=ReopenSource.REGRESSION_ISSUE,
            labels=["bug", "Regression", "priority:high"],
            days_since_merge=3.0,
        )

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.REGRESSION
        assert "regression" in outcome.reason.lower()


class TestReopenClassificationGovernanceFailure:
    """Test governance_failure classification."""

    @pytest.mark.asyncio
    async def test_compliance_bypass(self) -> None:
        """Reopen with compliance bypass -> governance_failure."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            days_since_merge=3.0,
            has_compliance_bypass=True,
        )

        outcome = await processor.process_reopen(event)

        assert outcome.classification == ReopenClassification.GOVERNANCE_FAILURE
        assert "compliance" in outcome.reason.lower() or "bypass" in outcome.reason.lower()

    @pytest.mark.asyncio
    async def test_governance_failure_overrides_other_classifications(self) -> None:
        """Governance failure takes precedence over other classifications."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(
            source=ReopenSource.ROLLBACK_PR,  # Would normally be regression
            has_compliance_bypass=True,
        )

        outcome = await processor.process_reopen(event)

        # Governance failure takes precedence
        assert outcome.classification == ReopenClassification.GOVERNANCE_FAILURE


class TestTaskPacketLinking:
    """Test TaskPacket linking from reopen events."""

    @pytest.mark.asyncio
    async def test_links_to_provided_taskpacket(self) -> None:
        """Uses provided taskpacket_id when available."""
        tp_id = uuid4()
        processor = ReopenEventProcessor()
        event = _make_reopen_event(original_taskpacket_id=tp_id)

        outcome = await processor.process_reopen(event)

        assert outcome.taskpacket_id == tp_id

    @pytest.mark.asyncio
    async def test_looks_up_taskpacket_by_pr(self) -> None:
        """Looks up taskpacket by PR number when not provided."""
        tp_id = uuid4()

        class MockTaskPacket:
            def __init__(self) -> None:
                self.id = tp_id

        async def get_tp_by_pr(repo: str, pr_num: int) -> MockTaskPacket:
            return MockTaskPacket()

        processor = ReopenEventProcessor(get_taskpacket_by_pr_fn=get_tp_by_pr)
        event = _make_reopen_event(original_taskpacket_id=None)

        outcome = await processor.process_reopen(event)

        assert outcome.taskpacket_id == tp_id


class TestMetricUpdates:
    """Test reopen metric updates."""

    @pytest.mark.asyncio
    async def test_increments_total_reopens(self) -> None:
        """Total reopens metric increments per event."""
        processor = ReopenEventProcessor()

        await processor.process_reopen(_make_reopen_event(repo_id="repo1"))
        await processor.process_reopen(_make_reopen_event(repo_id="repo1"))

        metrics = processor.get_metrics_by_repo("repo1")
        assert metrics["total_reopens"] == 2

    @pytest.mark.asyncio
    async def test_increments_classification_counts(self) -> None:
        """Classification counts increment correctly."""
        processor = ReopenEventProcessor()

        # Intent gap
        await processor.process_reopen(_make_reopen_event(
            repo_id="repo1",
            days_since_merge=3.0,
            ac_failing=["AC1"],
        ))

        # Regression
        await processor.process_reopen(_make_reopen_event(
            repo_id="repo1",
            days_since_merge=10.0,
        ))

        metrics = processor.get_metrics_by_repo("repo1")
        assert metrics["intent_gap_count"] == 1
        assert metrics["regression_count"] == 1

    @pytest.mark.asyncio
    async def test_separate_metrics_per_repo(self) -> None:
        """Metrics are tracked separately per repo."""
        processor = ReopenEventProcessor()

        await processor.process_reopen(_make_reopen_event(repo_id="repo1"))
        await processor.process_reopen(_make_reopen_event(repo_id="repo2"))
        await processor.process_reopen(_make_reopen_event(repo_id="repo1"))

        assert processor.get_reopen_rate("repo1") == 2
        assert processor.get_reopen_rate("repo2") == 1


class TestIndicatorProduction:
    """Test ReputationIndicator production for reopen events."""

    @pytest.mark.asyncio
    async def test_indicator_produced_with_taskpacket(self) -> None:
        """Indicator produced when TaskPacket is linked."""
        tp_id = uuid4()
        processor = ReopenEventProcessor()
        event = _make_reopen_event(original_taskpacket_id=tp_id)

        outcome = await processor.process_reopen(event)

        assert outcome.indicator_produced is True
        indicators = get_reopen_indicators()
        assert len(indicators) == 1
        assert indicators[0].taskpacket_id == tp_id

    @pytest.mark.asyncio
    async def test_no_indicator_without_taskpacket(self) -> None:
        """No indicator produced without TaskPacket linkage."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event(original_taskpacket_id=None)

        outcome = await processor.process_reopen(event)

        assert outcome.indicator_produced is False
        assert len(get_reopen_indicators()) == 0

    @pytest.mark.asyncio
    async def test_intent_gap_does_not_penalize_experts(self) -> None:
        """Intent gap reopens have zero weight (don't penalize experts)."""
        tp_id = uuid4()
        expert_id = uuid4()

        class MockProvenance:
            experts_consulted = [{"id": str(expert_id), "version": 1}]

        async def get_prov(_id: UUID) -> MockProvenance:
            return MockProvenance()

        processor = ReopenEventProcessor(get_provenance_fn=get_prov)
        event = _make_reopen_event(
            original_taskpacket_id=tp_id,
            days_since_merge=3.0,
            ac_failing=["AC1"],
        )

        await processor.process_reopen(event)

        indicators = get_reopen_indicators()
        # Intent gap produces indicator but with zero weight (no expert penalty)
        assert len(indicators) == 1
        assert indicators[0].normalized_weight == 0.0

    @pytest.mark.asyncio
    async def test_regression_penalizes_experts(self) -> None:
        """Regression reopens penalize experts with negative weight."""
        tp_id = uuid4()
        expert_id = uuid4()

        class MockProvenance:
            experts_consulted = [{"id": str(expert_id), "version": 1}]

        async def get_prov(_id: UUID) -> MockProvenance:
            return MockProvenance()

        processor = ReopenEventProcessor(get_provenance_fn=get_prov)
        event = _make_reopen_event(
            original_taskpacket_id=tp_id,
            days_since_merge=10.0,  # Late -> regression
        )

        await processor.process_reopen(event)

        indicators = get_reopen_indicators()
        assert len(indicators) == 1
        assert indicators[0].normalized_weight < 0
        assert indicators[0].expert_id == expert_id


class TestEventPersistence:
    """Test event and outcome persistence."""

    @pytest.mark.asyncio
    async def test_events_persisted(self) -> None:
        """Reopen events are persisted."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event()

        await processor.process_reopen(event)

        events = get_reopen_events()
        assert len(events) == 1
        assert events[0].event_id == event.event_id

    @pytest.mark.asyncio
    async def test_outcomes_persisted(self) -> None:
        """Reopen outcomes are persisted."""
        processor = ReopenEventProcessor()
        event = _make_reopen_event()

        outcome = await processor.process_reopen(event)

        outcomes = get_reopen_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0].event_id == event.event_id
        assert outcomes[0].classification == outcome.classification
