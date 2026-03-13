"""Unit tests for ReadinessCalibrator (Story 16.6)."""

from __future__ import annotations

import pytest

from src.readiness.calibrator import (
    DEFAULT_DIMENSION_WEIGHTS,
    MAX_WEIGHT_ADJUSTMENT,
    MIN_CALIBRATION_SAMPLES,
    ReadinessCalibrator,
)


@pytest.fixture
def calibrator():
    c = ReadinessCalibrator()
    yield c
    c.clear()


class TestRecordReadinessMiss:
    """Tests for record_readiness_miss()."""

    def test_records_a_miss(self, calibrator: ReadinessCalibrator):
        record = calibrator.record_readiness_miss(
            taskpacket_id="tp-1",
            repo_id="org/repo",
            readiness_score=0.55,
            defect_category="intent_gap",
        )
        assert record.taskpacket_id == "tp-1"
        assert record.repo_id == "org/repo"
        assert record.readiness_score == 0.55
        assert record.defect_category == "intent_gap"

    def test_miss_records_accumulate(self, calibrator: ReadinessCalibrator):
        for i in range(5):
            calibrator.record_readiness_miss(
                taskpacket_id=f"tp-{i}",
                repo_id="org/repo",
                readiness_score=0.45,
                defect_category="intent_gap",
            )
        assert len(calibrator.get_miss_records()) == 5

    def test_filter_by_repo(self, calibrator: ReadinessCalibrator):
        calibrator.record_readiness_miss("tp-1", "org/a", 0.5, "intent_gap")
        calibrator.record_readiness_miss("tp-2", "org/b", 0.5, "intent_gap")
        assert len(calibrator.get_miss_records("org/a")) == 1
        assert len(calibrator.get_miss_records("org/b")) == 1

    def test_missing_dimensions_stored(self, calibrator: ReadinessCalibrator):
        record = calibrator.record_readiness_miss(
            taskpacket_id="tp-1",
            repo_id="org/repo",
            readiness_score=0.4,
            defect_category="intent_gap",
            missing_dimensions=["acceptance_criteria", "scope_boundaries"],
        )
        assert record.missing_dimensions == ["acceptance_criteria", "scope_boundaries"]


class TestCalibrate:
    """Tests for calibrate()."""

    def test_skips_with_insufficient_samples(self, calibrator: ReadinessCalibrator):
        for i in range(5):
            calibrator.record_readiness_miss(f"tp-{i}", "org/repo", 0.5, "intent_gap")

        result = calibrator.calibrate()
        assert result.skipped_reason is not None
        assert "5/20" in result.skipped_reason
        assert result.samples_analyzed == 5

    def test_calibrates_with_enough_samples(self, calibrator: ReadinessCalibrator):
        for i in range(MIN_CALIBRATION_SAMPLES):
            calibrator.record_readiness_miss(
                taskpacket_id=f"tp-{i}",
                repo_id="org/repo",
                readiness_score=0.45,
                defect_category="intent_gap",
                missing_dimensions=["acceptance_criteria"],
            )

        result = calibrator.calibrate()
        assert result.skipped_reason is None
        assert result.samples_analyzed == MIN_CALIBRATION_SAMPLES
        assert "acceptance_criteria" in result.adjustments_made
        assert result.new_weights != result.previous_weights

    def test_weight_adjustment_capped(self, calibrator: ReadinessCalibrator):
        for i in range(50):
            calibrator.record_readiness_miss(
                taskpacket_id=f"tp-{i}",
                repo_id="org/repo",
                readiness_score=0.3,
                defect_category="intent_gap",
                missing_dimensions=["goal_clarity"],
            )

        result = calibrator.calibrate()
        for adj in result.adjustments_made.values():
            assert adj <= MAX_WEIGHT_ADJUSTMENT

    def test_weights_normalized_to_one(self, calibrator: ReadinessCalibrator):
        for i in range(MIN_CALIBRATION_SAMPLES):
            calibrator.record_readiness_miss(
                taskpacket_id=f"tp-{i}",
                repo_id="org/repo",
                readiness_score=0.4,
                defect_category="intent_gap",
                missing_dimensions=["acceptance_criteria", "goal_clarity"],
            )

        result = calibrator.calibrate()
        total = sum(result.new_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_per_repo_calibration(self, calibrator: ReadinessCalibrator):
        for i in range(MIN_CALIBRATION_SAMPLES):
            calibrator.record_readiness_miss(
                taskpacket_id=f"tp-{i}",
                repo_id="org/repo-a",
                readiness_score=0.5,
                defect_category="intent_gap",
                missing_dimensions=["scope_boundaries"],
            )

        result = calibrator.calibrate("org/repo-a")
        assert result.repo_id == "org/repo-a"
        assert result.skipped_reason is None

        # Other repo has no data
        result_b = calibrator.calibrate("org/repo-b")
        assert result_b.skipped_reason is not None

    def test_calibration_history_tracked(self, calibrator: ReadinessCalibrator):
        calibrator.calibrate()  # Will be skipped (no data)
        assert len(calibrator.get_calibration_history()) == 1


class TestGetWeights:
    """Tests for weight retrieval."""

    def test_default_weights_returned(self, calibrator: ReadinessCalibrator):
        weights = calibrator.get_weights()
        assert weights == DEFAULT_DIMENSION_WEIGHTS

    def test_unknown_repo_returns_defaults(self, calibrator: ReadinessCalibrator):
        weights = calibrator.get_weights("org/unknown")
        assert weights == DEFAULT_DIMENSION_WEIGHTS


class TestClear:
    """Tests for clear()."""

    def test_clear_resets_all_state(self, calibrator: ReadinessCalibrator):
        calibrator.record_readiness_miss("tp-1", "org/repo", 0.5, "intent_gap")
        calibrator.clear()
        assert len(calibrator.get_miss_records()) == 0
        assert len(calibrator.get_calibration_history()) == 0
