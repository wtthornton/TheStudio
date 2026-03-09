"""Unit tests for Epic 10 additions to src/admin/operational_targets.py.

Tests TimingEvent properties, record_timing, and _get_lead_times window filtering.
Core OperationalTargetsService percentile logic is tested in test_operational_targets.py.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.admin.operational_targets import (
    OperationalTargetsService,
    TimingEvent,
    _compute_percentiles,
    clear_timing_events,
    record_timing,
)


@pytest.fixture(autouse=True)
def _reset_state():
    clear_timing_events()
    yield
    clear_timing_events()


class TestTimingEvent:
    def test_lead_time_hours(self):
        t0 = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
        t1 = datetime(2025, 1, 1, 2, 30, tzinfo=UTC)  # 2.5 hours later
        evt = TimingEvent(repo_id="repo", intake_created_at=t0, pr_opened_at=t1)
        assert evt.lead_time_hours == pytest.approx(2.5)

    def test_lead_time_none_when_no_pr(self):
        evt = TimingEvent(repo_id="repo", intake_created_at=datetime.now(UTC))
        assert evt.lead_time_hours is None

    def test_cycle_time_hours(self):
        t0 = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
        t1 = datetime(2025, 1, 1, 1, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 4, 0, tzinfo=UTC)  # 3 hours after PR opened
        evt = TimingEvent(repo_id="repo", intake_created_at=t0, pr_opened_at=t1, merge_ready_at=t2)
        assert evt.cycle_time_hours == pytest.approx(3.0)

    def test_cycle_time_none_when_no_pr(self):
        evt = TimingEvent(
            repo_id="repo",
            intake_created_at=datetime.now(UTC),
            merge_ready_at=datetime.now(UTC),
        )
        assert evt.cycle_time_hours is None

    def test_cycle_time_none_when_no_merge_ready(self):
        evt = TimingEvent(
            repo_id="repo",
            intake_created_at=datetime.now(UTC),
            pr_opened_at=datetime.now(UTC),
        )
        assert evt.cycle_time_hours is None


class TestRecordTiming:
    def test_record_stores_event(self):
        evt = TimingEvent(
            repo_id="repo",
            intake_created_at=datetime.now(UTC),
            pr_opened_at=datetime.now(UTC),
        )
        record_timing(evt)
        svc = OperationalTargetsService()
        lead_times = svc._get_lead_times(None, 28)
        assert len(lead_times) >= 1

    def test_record_multiple(self):
        now = datetime.now(UTC)
        for i in range(5):
            evt = TimingEvent(
                repo_id="repo",
                intake_created_at=now - timedelta(hours=i + 1),
                pr_opened_at=now,
            )
            record_timing(evt)
        svc = OperationalTargetsService()
        lead_times = svc._get_lead_times(None, 28)
        assert len(lead_times) == 5


class TestGetLeadTimesWindowFiltering:
    def test_filters_old_events(self):
        now = datetime.now(UTC)
        old = now - timedelta(days=35)

        record_timing(TimingEvent(
            repo_id="repo",
            intake_created_at=now - timedelta(hours=1),
            pr_opened_at=now,
        ))
        record_timing(TimingEvent(
            repo_id="repo",
            intake_created_at=old,
            pr_opened_at=old + timedelta(hours=2),
        ))

        svc = OperationalTargetsService()
        lead_times = svc._get_lead_times(None, 28)
        assert len(lead_times) == 1

    def test_filters_by_repo(self):
        now = datetime.now(UTC)
        record_timing(TimingEvent(
            repo_id="repo-a",
            intake_created_at=now - timedelta(hours=1),
            pr_opened_at=now,
        ))
        record_timing(TimingEvent(
            repo_id="repo-b",
            intake_created_at=now - timedelta(hours=2),
            pr_opened_at=now,
        ))

        svc = OperationalTargetsService()
        lead_times = svc._get_lead_times("repo-a", 28)
        assert len(lead_times) == 1

    def test_falls_back_to_injected(self):
        svc = OperationalTargetsService(lead_times=[1.0, 2.0, 3.0])
        lead_times = svc._get_lead_times(None, 28)
        assert lead_times == [1.0, 2.0, 3.0]

    def test_prefers_timing_events_over_injected(self):
        now = datetime.now(UTC)
        record_timing(TimingEvent(
            repo_id="repo",
            intake_created_at=now - timedelta(hours=5),
            pr_opened_at=now,
        ))
        svc = OperationalTargetsService(lead_times=[99.0])
        lead_times = svc._get_lead_times(None, 28)
        assert len(lead_times) == 1
        assert lead_times[0] != 99.0  # Should use real timing events


class TestGetCycleTimesWindowFiltering:
    def test_filters_and_computes(self):
        now = datetime.now(UTC)
        record_timing(TimingEvent(
            repo_id="repo",
            intake_created_at=now - timedelta(hours=5),
            pr_opened_at=now - timedelta(hours=3),
            merge_ready_at=now,
        ))
        svc = OperationalTargetsService()
        cycle_times = svc._get_cycle_times(None, 28)
        assert len(cycle_times) == 1
        assert cycle_times[0] == pytest.approx(3.0)

    def test_skips_events_without_merge_ready(self):
        now = datetime.now(UTC)
        record_timing(TimingEvent(
            repo_id="repo",
            intake_created_at=now - timedelta(hours=5),
            pr_opened_at=now,
        ))
        svc = OperationalTargetsService()
        cycle_times = svc._get_cycle_times(None, 28)
        assert len(cycle_times) == 0


class TestComputePercentiles:
    def test_empty(self):
        assert _compute_percentiles([]) == (0.0, 0.0, 0.0)

    def test_single_value(self):
        p50, p95, p99 = _compute_percentiles([5.0])
        assert p50 == 5.0
        assert p95 == 5.0
        assert p99 == 5.0

    def test_ordered_values(self):
        values = list(range(1, 101))  # 1 to 100
        p50, p95, p99 = _compute_percentiles(values)
        assert p50 == 51  # index 50 of 100
        assert p95 == 96  # index 95 of 100
        assert p99 == 100  # index 99 of 100


class TestLeadTimeMetricsFromTimingEvents:
    def test_insufficient_data(self):
        now = datetime.now(UTC)
        for i in range(3):
            record_timing(TimingEvent(
                repo_id="repo",
                intake_created_at=now - timedelta(hours=i + 1),
                pr_opened_at=now,
            ))
        svc = OperationalTargetsService()
        result = svc.get_lead_time(min_samples=10)
        assert result.insufficient_data is True
        assert result.sample_count == 3

    def test_sufficient_data(self):
        now = datetime.now(UTC)
        for i in range(15):
            record_timing(TimingEvent(
                repo_id="repo",
                intake_created_at=now - timedelta(hours=i + 1),
                pr_opened_at=now,
            ))
        svc = OperationalTargetsService()
        result = svc.get_lead_time(min_samples=10)
        assert result.insufficient_data is False
        assert result.sample_count == 15
        assert result.p50 > 0
