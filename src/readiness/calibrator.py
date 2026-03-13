"""Readiness gate calibrator — learns from outcome signals to improve gate accuracy.

Records misses (issues that passed the gate but later received intent_gap defects)
and adjusts dimension weights to reduce future misses.

Story 16.6: Outcome signal feedback — intent_gap to readiness calibration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Weight adjustment cap per calibration cycle
MAX_WEIGHT_ADJUSTMENT = 0.10

# Minimum samples required before calibration can adjust weights
MIN_CALIBRATION_SAMPLES = 20

# Default dimension weights (baseline from scorer)
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "goal_clarity": 0.25,
    "acceptance_criteria": 0.25,
    "scope_boundaries": 0.15,
    "risk_coverage": 0.15,
    "reproduction_context": 0.10,
    "dependency_awareness": 0.10,
}


@dataclass
class CalibrationRecord:
    """A single readiness miss record for calibration."""

    taskpacket_id: str
    repo_id: str
    readiness_score: float
    defect_category: str
    missing_dimensions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class CalibrationResult:
    """Result of a calibration cycle."""

    samples_analyzed: int
    adjustments_made: dict[str, float] = field(default_factory=dict)
    previous_weights: dict[str, float] = field(default_factory=dict)
    new_weights: dict[str, float] = field(default_factory=dict)
    repo_id: str | None = None
    skipped_reason: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ReadinessCalibrator:
    """Calibrates readiness gate weights based on outcome signals.

    Records misses when gate-passed issues later receive intent_gap defects.
    On calibration, analyzes miss patterns and adjusts dimension weights
    by up to +/-10% per cycle.
    """

    def __init__(self) -> None:
        self._miss_records: list[CalibrationRecord] = []
        self._weights: dict[str, dict[str, float]] = {}  # repo_id -> weights
        self._calibration_history: list[CalibrationResult] = []

    def get_weights(self, repo_id: str | None = None) -> dict[str, float]:
        """Get current dimension weights for a repo (or global defaults)."""
        if repo_id and repo_id in self._weights:
            return dict(self._weights[repo_id])
        return dict(DEFAULT_DIMENSION_WEIGHTS)

    def get_miss_records(self, repo_id: str | None = None) -> list[CalibrationRecord]:
        """Get miss records, optionally filtered by repo."""
        if repo_id:
            return [r for r in self._miss_records if r.repo_id == repo_id]
        return list(self._miss_records)

    def get_calibration_history(self) -> list[CalibrationResult]:
        """Get history of calibration results."""
        return list(self._calibration_history)

    def record_readiness_miss(
        self,
        taskpacket_id: str,
        repo_id: str,
        readiness_score: float,
        defect_category: str,
        missing_dimensions: list[str] | None = None,
    ) -> CalibrationRecord:
        """Record a readiness miss — an issue that passed the gate but had an intent_gap.

        Args:
            taskpacket_id: The TaskPacket that had the miss.
            repo_id: Repository identifier.
            readiness_score: The score the issue received when it passed.
            defect_category: The defect category (should be "intent_gap").
            missing_dimensions: Dimensions that were scored low but still passed.

        Returns:
            The recorded CalibrationRecord.
        """
        record = CalibrationRecord(
            taskpacket_id=taskpacket_id,
            repo_id=repo_id,
            readiness_score=readiness_score,
            defect_category=defect_category,
            missing_dimensions=missing_dimensions or [],
        )
        self._miss_records.append(record)
        logger.info(
            "readiness.calibrator.miss_recorded",
            extra={
                "taskpacket_id": taskpacket_id,
                "repo_id": repo_id,
                "readiness_score": readiness_score,
                "defect_category": defect_category,
            },
        )
        return record

    def calibrate(self, repo_id: str | None = None) -> CalibrationResult:
        """Analyze miss data and adjust dimension weights.

        Requires minimum 20 samples. Adjustments are capped at +/-10% per cycle.
        Per-repo calibration is preferred; global aggregates across all repos.

        Args:
            repo_id: If provided, calibrate for a specific repo. Otherwise global.

        Returns:
            CalibrationResult with adjustments made (or skipped_reason).
        """
        records = self.get_miss_records(repo_id)
        sample_count = len(records)

        if sample_count < MIN_CALIBRATION_SAMPLES:
            result = CalibrationResult(
                samples_analyzed=sample_count,
                repo_id=repo_id,
                skipped_reason=(
                    f"Insufficient samples: {sample_count}/{MIN_CALIBRATION_SAMPLES} required"
                ),
            )
            self._calibration_history.append(result)
            logger.info(
                "readiness.calibrator.skipped",
                extra={"repo_id": repo_id, "samples": sample_count},
            )
            return result

        # Count how often each dimension appears in misses
        dimension_miss_counts: dict[str, int] = {}
        for record in records:
            for dim in record.missing_dimensions:
                dimension_miss_counts[dim] = dimension_miss_counts.get(dim, 0) + 1

        # Current weights
        current_weights = self.get_weights(repo_id)
        previous_weights = dict(current_weights)
        new_weights = dict(current_weights)
        adjustments: dict[str, float] = {}

        # Adjust weights: increase weight for dimensions that appear in misses
        for dim, miss_count in dimension_miss_counts.items():
            if dim not in new_weights:
                continue

            # Proportional adjustment: more misses = larger increase (capped)
            miss_rate = miss_count / sample_count
            adjustment = min(miss_rate * 0.2, MAX_WEIGHT_ADJUSTMENT)

            new_weights[dim] = min(new_weights[dim] + adjustment, 1.0)
            adjustments[dim] = round(adjustment, 4)

        # Normalize weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: round(v / total, 4) for k, v in new_weights.items()}

        # Store updated weights
        weight_key = repo_id or "__global__"
        self._weights[weight_key] = new_weights

        result = CalibrationResult(
            samples_analyzed=sample_count,
            adjustments_made=adjustments,
            previous_weights=previous_weights,
            new_weights=new_weights,
            repo_id=repo_id,
        )
        self._calibration_history.append(result)

        logger.info(
            "readiness.calibrator.calibrated",
            extra={
                "repo_id": repo_id,
                "samples": sample_count,
                "adjustments": adjustments,
            },
        )
        return result

    def clear(self) -> None:
        """Clear all records and weights (for testing)."""
        self._miss_records.clear()
        self._weights.clear()
        self._calibration_history.clear()


# Module-level singleton
_calibrator: ReadinessCalibrator | None = None


def get_calibrator() -> ReadinessCalibrator:
    """Get or create the module-level calibrator instance."""
    global _calibrator
    if _calibrator is None:
        _calibrator = ReadinessCalibrator()
    return _calibrator


def set_calibrator(calibrator: ReadinessCalibrator | None) -> None:
    """Set the module-level calibrator (for testing)."""
    global _calibrator
    _calibrator = calibrator
