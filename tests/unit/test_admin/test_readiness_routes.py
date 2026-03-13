"""Unit tests for readiness admin API routes (Story 16.7)."""

from __future__ import annotations

import pytest

from src.admin.readiness_routes import (
    clear_metrics,
    get_metrics,
    record_gate_result,
)
from src.readiness.calibrator import ReadinessCalibrator, set_calibrator


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset metrics and calibrator state for each test."""
    clear_metrics()
    calibrator = ReadinessCalibrator()
    set_calibrator(calibrator)
    yield
    clear_metrics()
    set_calibrator(None)


class TestRecordGateResult:
    """Tests for the metrics recording function."""

    def test_records_pass(self):
        record_gate_result("org/repo", "pass", 0.85, [])
        metrics = get_metrics("org/repo")
        assert metrics.total_evaluations == 1
        assert metrics.pass_count == 1
        assert metrics.hold_count == 0

    def test_records_hold_with_missing_dims(self):
        record_gate_result("org/repo", "hold", 0.35, ["acceptance_criteria", "goal_clarity"])
        metrics = get_metrics("org/repo")
        assert metrics.hold_count == 1
        assert len(metrics.top_missing_dimensions) == 2

    def test_records_escalate(self):
        record_gate_result("org/repo", "escalate", 0.2, ["goal_clarity"])
        metrics = get_metrics("org/repo")
        assert metrics.escalate_count == 1

    def test_average_score_calculated(self):
        record_gate_result("org/repo", "pass", 0.8, [])
        record_gate_result("org/repo", "hold", 0.4, [])
        metrics = get_metrics("org/repo")
        assert metrics.average_score == pytest.approx(0.6, abs=0.01)

    def test_aggregate_across_repos(self):
        record_gate_result("org/a", "pass", 0.9, [])
        record_gate_result("org/b", "hold", 0.3, ["goal_clarity"])
        metrics = get_metrics()  # no repo_id = aggregate
        assert metrics.total_evaluations == 2
        assert metrics.pass_count == 1
        assert metrics.hold_count == 1

    def test_unknown_repo_returns_empty(self):
        metrics = get_metrics("org/nonexistent")
        assert metrics.total_evaluations == 0


class TestClearMetrics:
    """Tests for clear_metrics()."""

    def test_clears_all_data(self):
        record_gate_result("org/repo", "pass", 0.8, [])
        clear_metrics()
        metrics = get_metrics("org/repo")
        assert metrics.total_evaluations == 0
