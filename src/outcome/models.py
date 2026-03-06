"""Outcome signal models — consumed signals and quarantined events.

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


class QuarantinedSignal(BaseModel):
    """A signal that failed validation and was quarantined for review."""

    raw_payload: dict[str, Any]
    reason: QuarantineReason
    timestamp: datetime
