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
    # Epic 42 — Execute tier post-merge monitoring
    MERGE_SUCCEEDED = "merge_succeeded"
    MERGE_REVERTED = "merge_reverted"
    POST_MERGE_ISSUE = "post_merge_issue"


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
    """Reasons a signal may be quarantined.

    Per thestudioarc/12-outcome-ingestor.md lines 83-93:
    - missing_correlation_id: no correlation_id in payload
    - unknown_taskpacket: taskpacket_id not found in database
    - unknown_repo: repo_id not found in database
    - invalid_event: event type not in SignalEvent enum
    - invalid_category_severity: invalid defect_category or defect_severity value
    - idempotency_conflict: duplicate event with conflicting payload
    """

    MISSING_CORRELATION_ID = "missing_correlation_id"
    UNKNOWN_TASKPACKET = "unknown_taskpacket"
    UNKNOWN_REPO = "unknown_repo"
    INVALID_EVENT = "invalid_event"
    INVALID_CATEGORY_SEVERITY = "invalid_category_severity"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"


class QuarantinedEvent(BaseModel):
    """A signal that failed validation and was quarantined for operator review.

    Per thestudioarc/12-outcome-ingestor.md lines 83-105:
    Quarantined events can be corrected and replayed.
    """

    quarantine_id: UUID
    event_payload: dict[str, Any]
    reason: QuarantineReason
    repo_id: str | None = None
    category: str | None = None
    created_at: datetime
    corrected_at: datetime | None = None
    corrected_payload: dict[str, Any] | None = None
    replayed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "quarantine_id": str(self.quarantine_id),
            "event_payload": self.event_payload,
            "reason": self.reason.value,
            "repo_id": self.repo_id,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "corrected_at": self.corrected_at.isoformat() if self.corrected_at else None,
            "corrected_payload": self.corrected_payload,
            "replayed_at": self.replayed_at.isoformat() if self.replayed_at else None,
        }


class QuarantinedSignal(BaseModel):
    """Legacy model — use QuarantinedEvent for new code."""

    raw_payload: dict[str, Any]
    reason: QuarantineReason
    timestamp: datetime


class DeadLetterEvent(BaseModel):
    """An event that failed parsing/validation after max attempts.

    Per thestudioarc/12-outcome-ingestor.md lines 94-96:
    Events moved to dead-letter preserve raw payload and failure reason.
    """

    id: UUID
    raw_payload: bytes
    failure_reason: str
    attempt_count: int
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "raw_payload": self.raw_payload.decode("utf-8", errors="replace"),
            "failure_reason": self.failure_reason,
            "attempt_count": self.attempt_count,
            "created_at": self.created_at.isoformat(),
        }


class ReplayResult(BaseModel):
    """Result of replaying a quarantined event."""

    quarantine_id: UUID
    success: bool
    signal: OutcomeSignal | None = None
    error: str | None = None
    replayed_at: datetime


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
