"""Outcome signal models — consumed signals, quarantined events, and reputation indicators.

Architecture reference: thestudioarc/12-outcome-ingestor.md
"""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SignalEvent(enum.StrEnum):
    """Valid signal event types consumed by the Outcome Ingestor."""

    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_EXHAUSTED = "verification_exhausted"
    QA_PASSED = "qa_passed"
    QA_DEFECT = "qa_defect"
    QA_REWORK = "qa_rework"


class OutcomeType(enum.StrEnum):
    """Outcome types for reputation indicators."""

    SUCCESS = "success"
    FAILURE = "failure"
    LOOPBACK = "loopback"


class DefectCategory(enum.StrEnum):
    """Defect categories from QA signals (per 14-qa-quality-layer.md)."""

    INTENT_GAP = "intent_gap"
    IMPLEMENTATION_BUG = "implementation_bug"
    REGRESSION = "regression"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    PARTNER_MISMATCH = "partner_mismatch"
    OPERABILITY = "operability"


class DefectSeverity(enum.StrEnum):
    """Defect severity levels."""

    S0 = "s0"  # Critical
    S1 = "s1"  # High
    S2 = "s2"  # Medium
    S3 = "s3"  # Low


class OutcomeSignal(BaseModel):
    """A consumed and validated signal persisted for analytics."""

    event: SignalEvent
    taskpacket_id: UUID
    correlation_id: UUID
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class QuarantineReason(enum.StrEnum):
    """Reasons a signal may be quarantined."""

    MISSING_CORRELATION_ID = "missing_correlation_id"
    UNKNOWN_TASKPACKET = "unknown_taskpacket"
    INVALID_EVENT = "invalid_event"
    INVALID_CATEGORY_SEVERITY = "invalid_category_severity"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"


class QuarantinedSignal(BaseModel):
    """A signal that failed validation and was quarantined for review."""

    raw_payload: dict[str, Any]
    reason: QuarantineReason
    timestamp: datetime


class ReputationIndicator(BaseModel):
    """Indicator produced for the Reputation Engine.

    Contains normalized outcome data for expert reputation updates.
    Per thestudioarc/06-reputation-engine.md and 12-outcome-ingestor.md.
    """

    expert_id: UUID
    expert_version: int
    context_key: str  # Format: "{repo}:{risk_class}:{complexity_band}"
    outcome_type: OutcomeType
    defect_category: DefectCategory | None = None
    defect_severity: DefectSeverity | None = None
    normalized_weight: float  # Complexity-adjusted impact (-1.0 to 1.0)
    raw_weight: float  # Pre-normalization weight
    complexity_band: str  # "low", "medium", "high"
    provenance_complete: bool  # Whether full provenance was available
    taskpacket_id: UUID
    correlation_id: UUID
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "expert_id": str(self.expert_id),
            "expert_version": self.expert_version,
            "context_key": self.context_key,
            "outcome_type": self.outcome_type.value,
            "defect_category": self.defect_category.value if self.defect_category else None,
            "defect_severity": self.defect_severity.value if self.defect_severity else None,
            "normalized_weight": self.normalized_weight,
            "raw_weight": self.raw_weight,
            "complexity_band": self.complexity_band,
            "provenance_complete": self.provenance_complete,
            "taskpacket_id": str(self.taskpacket_id),
            "correlation_id": str(self.correlation_id),
            "timestamp": self.timestamp.isoformat(),
        }
