"""TaskPacket model — the durable work record for a single work item.

Created by Ingress (Story 0.1), enriched by Context Manager (Story 0.3).
Every downstream component reads from and/or updates the TaskPacket.
Supports multi-source intake via source_name column (Epic 27).
"""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PrMergeStatus(enum.StrEnum):
    """Merge status of the pull request associated with a TaskPacket.

    Updated by the Epic 38 webhook bridge (Story 38.24) or a polling activity.
    Nullable — only set after a PR is created (PUBLISHED status).
    """

    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


class TaskTrustTier(enum.StrEnum):
    """Pipeline-level trust tier assigned to a TaskPacket.

    Controls the automation contract for downstream actions:
      * OBSERVE  — read-only; all actions require human approval
      * SUGGEST  — agent proposes; human confirms before execution
      * EXECUTE  — agent executes autonomously within safety bounds

    Assigned by the trust rule engine (src/dashboard/trust_engine.py).
    Distinct from the expert reputation tiers in src/reputation/tiers.py.
    """

    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


class TaskPacketStatus(enum.StrEnum):
    """Valid status values for a TaskPacket."""

    TRIAGE = "triage"
    RECEIVED = "received"
    ENRICHED = "enriched"
    CLARIFICATION_REQUESTED = "clarification_requested"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    INTENT_BUILT = "intent_built"
    IN_PROGRESS = "in_progress"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_APPROVAL_EXPIRED = "awaiting_approval_expired"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"
    # Steering states (Epic 37 — Slice 1)
    PAUSED = "paused"   # Pipeline held between activities; resumes on resume_task signal
    ABORTED = "aborted"  # Forcefully terminated by operator; terminal, stores reason


# Allowed status transitions. Key = current status, value = set of valid next statuses.
ALLOWED_TRANSITIONS: dict[TaskPacketStatus, set[TaskPacketStatus]] = {
    TaskPacketStatus.TRIAGE: {
        TaskPacketStatus.RECEIVED,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.RECEIVED: {
        TaskPacketStatus.ENRICHED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.ENRICHED: {
        TaskPacketStatus.CLARIFICATION_REQUESTED,
        TaskPacketStatus.HUMAN_REVIEW_REQUIRED,
        TaskPacketStatus.INTENT_BUILT,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.CLARIFICATION_REQUESTED: {
        TaskPacketStatus.ENRICHED,  # re-evaluation after update
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.HUMAN_REVIEW_REQUIRED: {
        TaskPacketStatus.ENRICHED,  # re-evaluation after update
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.INTENT_BUILT: {
        TaskPacketStatus.IN_PROGRESS,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.IN_PROGRESS: {
        TaskPacketStatus.VERIFICATION_PASSED,
        TaskPacketStatus.VERIFICATION_FAILED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.VERIFICATION_PASSED: {
        TaskPacketStatus.AWAITING_APPROVAL,
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.AWAITING_APPROVAL: {
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.AWAITING_APPROVAL_EXPIRED,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.AWAITING_APPROVAL_EXPIRED: {
        TaskPacketStatus.FAILED,
        TaskPacketStatus.ABORTED,
    },
    TaskPacketStatus.REJECTED: {TaskPacketStatus.FAILED},
    TaskPacketStatus.VERIFICATION_FAILED: {
        TaskPacketStatus.IN_PROGRESS,  # loopback
        TaskPacketStatus.FAILED,
        TaskPacketStatus.PAUSED,
        TaskPacketStatus.ABORTED,
    },
    # Steering states (Epic 37 — Slice 1)
    # PAUSED can resume back to any active pipeline stage, or be aborted.
    TaskPacketStatus.PAUSED: {
        TaskPacketStatus.RECEIVED,
        TaskPacketStatus.ENRICHED,
        TaskPacketStatus.INTENT_BUILT,
        TaskPacketStatus.IN_PROGRESS,
        TaskPacketStatus.VERIFICATION_PASSED,
        TaskPacketStatus.AWAITING_APPROVAL,
        TaskPacketStatus.ABORTED,
        TaskPacketStatus.FAILED,
    },
    # ABORTED is a terminal state — no outgoing transitions.
    TaskPacketStatus.ABORTED: set(),
    TaskPacketStatus.PUBLISHED: set(),
    TaskPacketStatus.FAILED: set(),
}


class TaskPacketRow(Base):
    """SQLAlchemy ORM model for the taskpacket table."""

    __tablename__ = "taskpacket"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_id: Mapped[int] = mapped_column(nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    # Source that created this TaskPacket (Epic 27 — multi-source intake)
    # "github" for the default GitHub webhook, or the source config name
    # (e.g. "jira", "linear", "slack") for generic webhook sources.
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="github", server_default="github"
    )
    status: Mapped[TaskPacketStatus] = mapped_column(
        Enum(
            TaskPacketStatus,
            name="taskpacket_status",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TaskPacketStatus.RECEIVED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    # Set on transition to terminal status: PUBLISHED, REJECTED, FAILED, ABORTED (Epic 39.0a)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Enrichment fields (Story 0.3 — Context Manager, upgraded in Story 2.1)
    scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_flags: Mapped[dict[str, bool] | None] = mapped_column(JSON, nullable=True)
    # Complexity Index v1: JSONB with score, band, and dimensions
    # See docs/architecture/complexity-index-v1.md
    complexity_index: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    context_packs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Intent fields (Story 0.4 — Intent Builder)
    intent_spec_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    intent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Readiness gate fields (Epic 16 — Story 16.5)
    readiness_evaluation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    readiness_hold_comment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    readiness_score: Mapped[float | None] = mapped_column(nullable=True)
    readiness_miss: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Stage timing fields (Epic 35 S1.B1 — Pipeline Visibility)
    # JSONB dict mapping stage name to {"start": iso_ts, "end": iso_ts|null}
    # Null for historical records that predate this migration.
    stage_timings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Triage fields (Epic 36 — Planning Experience)
    issue_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issue_body: Mapped[str | None] = mapped_column(String(65535), nullable=True)
    triage_enrichment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Routing review fields (Epic 36 — Story 36.14c)
    # Full ConsultPlan stored as JSONB so the dashboard can render routing decisions.
    routing_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Published PR fields — persisted by Publisher after PR creation
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # PR merge status: open/merged/closed. Set by webhook bridge (Epic 38.24) or polling.
    # Nullable — only populated after PR creation. (Epic 39.0b)
    pr_merge_status: Mapped[PrMergeStatus | None] = mapped_column(
        Enum(
            PrMergeStatus,
            name="pr_merge_status_enum",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
        default=None,
    )

    # Trust tier (Epic 37 — Slice 3: Trust Tier Configuration)
    # Nullable: set by trust rule engine before first pipeline activity.
    # Allowed values: observe / suggest / execute  (TaskTrustTier enum).
    task_trust_tier: Mapped[TaskTrustTier | None] = mapped_column(
        Enum(
            TaskTrustTier,
            name="task_trust_tier_enum",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
        default=None,
    )

    # Execute tier fields (Epic 42 — Slice 1)
    # UUID of the trust-tier rule that matched this packet (or None if default tier used).
    matched_rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, default=None
    )
    # Set to True by the Publisher when auto-merge is successfully enabled on the PR.
    auto_merged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Verification fields (Story 0.6 — Verification Gate)
    loopback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("delivery_id", "repo", name="ix_taskpacket_delivery_repo"),
        {"comment": "TaskPacket — durable work record"},
    )


class TaskPacketCreate(BaseModel):
    """Pydantic model for TaskPacket creation input."""

    repo: str
    issue_id: int
    delivery_id: str
    correlation_id: UUID = Field(default_factory=uuid4)
    source_name: str = "github"
    issue_title: str | None = None
    issue_body: str | None = None
    triage_enrichment: dict[str, Any] | None = None


class TaskPacketRead(BaseModel):
    """Pydantic model for TaskPacket read output."""

    model_config = {"from_attributes": True}

    id: UUID
    repo: str
    issue_id: int
    delivery_id: str
    correlation_id: UUID
    source_name: str = "github"
    status: TaskPacketStatus
    scope: dict[str, Any] | None = None
    risk_flags: dict[str, bool] | None = None
    # Complexity Index v1: dict with score, band, and dimensions
    complexity_index: dict[str, Any] | None = None
    context_packs: list[dict[str, Any]] | None = None
    intent_spec_id: UUID | None = None
    intent_version: int | None = None
    readiness_evaluation_count: int = 0
    readiness_hold_comment_id: str | None = None
    readiness_score: float | None = None
    readiness_miss: bool = False
    stage_timings: dict[str, Any] | None = None
    issue_title: str | None = None
    issue_body: str | None = None
    triage_enrichment: dict[str, Any] | None = None
    rejection_reason: str | None = None
    routing_result: dict[str, Any] | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    # PR merge status (Epic 39.0b)
    pr_merge_status: PrMergeStatus | None = None
    loopback_count: int = 0
    # Trust tier assigned by the rule engine (Epic 37 — Slice 3)
    task_trust_tier: TaskTrustTier | None = None
    # Execute tier fields (Epic 42 — Slice 1)
    matched_rule_id: UUID | None = None
    auto_merged: bool = False
    created_at: datetime
    updated_at: datetime
    # Set when TaskPacket reaches terminal status (Epic 39.0a)
    completed_at: datetime | None = None
