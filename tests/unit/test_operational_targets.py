"""Tests for Operational Targets — lead time, cycle time, reopen target (Story 7.9)."""

from unittest.mock import patch

import pytest

from src.admin.metrics import ReopenMetrics
from src.admin.operational_targets import (
    CycleTimeMetrics,
    LeadTimeMetrics,
    OperationalTargetsService,
    ReopenTargetMetrics,
    _compute_percentiles,
    clear_timing_events,
)


@pytest.fixture(autouse=True)
def _reset_timing():
    """Ensure no timing events leak from other tests."""
    clear_timing_events()
    yield
    clear_timing_events()


class TestPercentiles:
    def test_empty_list(self):
        p50, p95, p99 = _compute_percentiles([])
        assert p50 == 0.0
        assert p95 == 0.0

    def test_single_value(self):
        p50, p95, p99 = _compute_percentiles([5.0])
        assert p50 == 5.0
        assert p99 == 5.0

    def test_known_distribution(self):
        values = list(range(1, 101))  # 1..100
        p50, p95, p99 = _compute_percentiles(values)
        assert p50 == 51  # 50th percentile
        assert p95 == 96  # 95th percentile
        assert p99 == 100  # 99th percentile


class TestLeadTimeMetrics:
    def test_to_dict(self):
        m = LeadTimeMetrics(p50=1.5, p95=4.0, p99=8.0, sample_count=50)
        d = m.to_dict()
        assert d["p50_hours"] == 1.5
        assert d["p95_hours"] == 4.0
        assert d["sample_count"] == 50
        assert d["insufficient_data"] is False


class TestCycleTimeMetrics:
    def test_to_dict(self):
        m = CycleTimeMetrics(p50=0.5, p95=2.0, p99=5.0, sample_count=30)
        d = m.to_dict()
        assert d["p50_hours"] == 0.5
        assert d["insufficient_data"] is False


class TestReopenTargetMetrics:
    def test_to_dict_met(self):
        m = ReopenTargetMetrics(current_rate=0.03, met=True, sample_count=100)
        d = m.to_dict()
        assert d["met"] is True
        assert d["target"] == 0.05

    def test_to_dict_not_met(self):
        m = ReopenTargetMetrics(current_rate=0.08, met=False, sample_count=100)
        d = m.to_dict()
        assert d["met"] is False


class TestOperationalTargetsService:
    def test_lead_time_sufficient_data(self):
        lead_times = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        svc = OperationalTargetsService(lead_times=lead_times)
        result = svc.get_lead_time()
        assert result.insufficient_data is False
        assert result.sample_count == 12
        assert result.p50 > 0

    def test_lead_time_insufficient_data(self):
        svc = OperationalTargetsService(lead_times=[1.0, 2.0])
        result = svc.get_lead_time()
        assert result.insufficient_data is True
        assert result.sample_count == 2

    def test_lead_time_empty(self):
        svc = OperationalTargetsService()
        result = svc.get_lead_time()
        assert result.insufficient_data is True
        assert result.p50 == 0.0

    def test_cycle_time_sufficient_data(self):
        cycle_times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
        svc = OperationalTargetsService(cycle_times=cycle_times)
        result = svc.get_cycle_time()
        assert result.insufficient_data is False
        assert result.sample_count == 11

    def test_cycle_time_insufficient_data(self):
        svc = OperationalTargetsService(cycle_times=[1.0])
        result = svc.get_cycle_time()
        assert result.insufficient_data is True

    @patch("src.admin.operational_targets.get_metrics_service")
    def test_reopen_target_met(self, mock_metrics):
        mock_metrics.return_value.get_reopen.return_value = ReopenMetrics(
            total_merged=100, total_reopened=3, reopen_rate=0.03,
        )
        svc = OperationalTargetsService()
        result = svc.get_reopen_target()
        assert result.met is True
        assert result.current_rate == 0.03

    @patch("src.admin.operational_targets.get_metrics_service")
    def test_reopen_target_not_met(self, mock_metrics):
        mock_metrics.return_value.get_reopen.return_value = ReopenMetrics(
            total_merged=100, total_reopened=8, reopen_rate=0.08,
        )
        svc = OperationalTargetsService()
        result = svc.get_reopen_target()
        assert result.met is False
        assert result.current_rate == 0.08

    @patch("src.admin.operational_targets.get_metrics_service")
    def test_reopen_target_insufficient_data(self, mock_metrics):
        mock_metrics.return_value.get_reopen.return_value = ReopenMetrics(
            total_merged=5, total_reopened=1, reopen_rate=0.20,
        )
        svc = OperationalTargetsService()
        result = svc.get_reopen_target()
        assert result.insufficient_data is True
        assert result.met is True  # Insufficient data -> met=True

    @patch("src.admin.operational_targets.get_metrics_service")
    def test_reopen_target_no_data(self, mock_metrics):
        mock_metrics.return_value.get_reopen.return_value = ReopenMetrics()
        svc = OperationalTargetsService()
        result = svc.get_reopen_target()
        assert result.insufficient_data is True
        assert result.sample_count == 0
