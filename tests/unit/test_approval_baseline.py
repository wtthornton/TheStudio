"""Tests for approval flow baseline metrics (Epic 24 prep).

Validates that approval event recording and baseline computation work
correctly, providing the metrics Meridian requires before Epic 24 starts.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.admin.operational_targets import (
    ApprovalBaselineMetrics,
    ApprovalEvent,
    clear_approval_events,
    get_targets_service,
    record_approval_event,
)


@pytest.fixture(autouse=True)
def _clean_events():
    """Clear approval events before each test."""
    clear_approval_events()
    yield
    clear_approval_events()


class TestApprovalEvent:
    def test_latency_calculation(self):
        event = ApprovalEvent(
            taskpacket_id="tp-001",
            repo_tier="suggest",
            awaiting_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
            resolved_at=datetime(2026, 3, 17, 12, 30, tzinfo=UTC),
            outcome="approved",
        )
        assert event.latency_hours == pytest.approx(2.5)

    def test_latency_none_when_unresolved(self):
        event = ApprovalEvent(
            taskpacket_id="tp-002",
            repo_tier="suggest",
            awaiting_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
        )
        assert event.latency_hours is None

    def test_timeout_event(self):
        event = ApprovalEvent(
            taskpacket_id="tp-003",
            repo_tier="execute",
            awaiting_at=datetime(2026, 3, 10, 0, 0, tzinfo=UTC),
            resolved_at=datetime(2026, 3, 17, 0, 0, tzinfo=UTC),
            outcome="timeout",
        )
        assert event.latency_hours == pytest.approx(168.0)  # 7 days


class TestApprovalBaseline:
    def _record_events(self):
        """Record a mix of approval events for baseline testing."""
        now = datetime.now(UTC)

        # 3 approvals with varying latency
        for i, hours in enumerate([1.0, 2.0, 4.0]):
            record_approval_event(
                ApprovalEvent(
                    taskpacket_id=f"tp-approve-{i}",
                    repo_tier="suggest",
                    awaiting_at=now - timedelta(hours=hours + 1),
                    resolved_at=now - timedelta(hours=1),
                    outcome="approved",
                    approved_by="reviewer",
                )
            )

        # 1 rejection
        record_approval_event(
            ApprovalEvent(
                taskpacket_id="tp-reject-0",
                repo_tier="suggest",
                awaiting_at=now - timedelta(hours=3),
                resolved_at=now - timedelta(hours=2),
                outcome="rejected",
                rejected_by="reviewer",
                rejection_reason="Needs tests",
            )
        )

        # 1 timeout
        record_approval_event(
            ApprovalEvent(
                taskpacket_id="tp-timeout-0",
                repo_tier="execute",
                awaiting_at=now - timedelta(days=8),
                resolved_at=now - timedelta(days=1),
                outcome="timeout",
            )
        )

    def test_baseline_with_events(self):
        self._record_events()
        svc = get_targets_service()
        baseline = svc.get_approval_baseline(min_samples=1)

        assert baseline.total_approvals == 3
        assert baseline.total_rejections == 1
        assert baseline.total_timeouts == 1
        assert baseline.sample_count == 5
        assert baseline.timeout_rate == pytest.approx(0.2)
        assert baseline.median_latency_hours > 0
        assert not baseline.insufficient_data

    def test_baseline_insufficient_data(self):
        # Only 1 event, need 10 minimum
        record_approval_event(
            ApprovalEvent(
                taskpacket_id="tp-001",
                repo_tier="suggest",
                awaiting_at=datetime.now(UTC) - timedelta(hours=2),
                resolved_at=datetime.now(UTC),
                outcome="approved",
            )
        )
        svc = get_targets_service()
        baseline = svc.get_approval_baseline()

        assert baseline.insufficient_data is True
        assert baseline.sample_count == 1

    def test_baseline_empty(self):
        svc = get_targets_service()
        baseline = svc.get_approval_baseline()

        assert baseline.sample_count == 0
        assert baseline.insufficient_data is True
        assert baseline.timeout_rate == 0.0

    def test_to_dict(self):
        self._record_events()
        svc = get_targets_service()
        baseline = svc.get_approval_baseline(min_samples=1)
        d = baseline.to_dict()

        assert "total_approvals" in d
        assert "timeout_rate" in d
        assert "median_latency_hours" in d
        assert isinstance(d["timeout_rate"], float)

    def test_window_filtering(self):
        """Events outside the window are excluded."""
        now = datetime.now(UTC)
        # Old event (60 days ago)
        record_approval_event(
            ApprovalEvent(
                taskpacket_id="tp-old",
                repo_tier="suggest",
                awaiting_at=now - timedelta(days=60),
                resolved_at=now - timedelta(days=59),
                outcome="approved",
            )
        )
        # Recent event
        record_approval_event(
            ApprovalEvent(
                taskpacket_id="tp-recent",
                repo_tier="suggest",
                awaiting_at=now - timedelta(hours=2),
                resolved_at=now,
                outcome="approved",
            )
        )

        svc = get_targets_service()
        baseline = svc.get_approval_baseline(window_days=28, min_samples=1)
        assert baseline.sample_count == 1  # Only the recent one
