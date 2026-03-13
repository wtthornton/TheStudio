"""Compliance models — data structures for compliance checking results.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Repo Compliance Scorecard, Execute Tier Compliance Gate)
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ComplianceCheck(enum.StrEnum):
    """Individual compliance checks that must pass for Execute tier.

    Per thestudioarc/23-admin-control-ui.md:
    - rulesets_configured: At least one ruleset with required status checks
    - required_reviewers: Required reviewer rules for sensitive paths
    - branch_protection: Default branch has protection enabled
    - labels_exist: Standard agent labels exist
    - projects_v2: Projects v2 integration configured (or waived)
    - execution_plane_health: Workspace, workers, verification runner OK
    - publisher_idempotency: Publisher idempotency guard operational
    - credentials_scoped: Credentials scoped correctly for tier
    """

    RULESETS_CONFIGURED = "rulesets_configured"
    REQUIRED_REVIEWERS = "required_reviewers"
    BRANCH_PROTECTION = "branch_protection"
    LABELS_EXIST = "labels_exist"
    PROJECTS_V2 = "projects_v2"
    EXECUTION_PLANE_HEALTH = "execution_plane_health"
    PUBLISHER_IDEMPOTENCY = "publisher_idempotency"
    CREDENTIALS_SCOPED = "credentials_scoped"
    ADVERSARIAL_CONTENT = "adversarial_content"
    EXECUTE_TIER_POLICY = "execute_tier_policy"


class ComplianceCheckResult(BaseModel):
    """Result of a single compliance check."""

    check: ComplianceCheck
    passed: bool
    failure_reason: str | None = None
    remediation_hint: str | None = None
    details: dict[str, object] | None = None


class ComplianceResult(BaseModel):
    """Result of full compliance check for a repo."""

    model_config = {"from_attributes": True}

    id: UUID = Field(default_factory=uuid4)
    repo_id: UUID
    overall_passed: bool
    score: float = Field(ge=0.0, le=100.0)
    checks: list[ComplianceCheckResult]
    checked_at: datetime
    triggered_by: str


class ComplianceResultRow(Base):
    """SQLAlchemy ORM model for the compliance_results table."""

    __tablename__ = "compliance_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    repo_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    overall_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    checks: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = ({"comment": "Compliance check results — persisted for audit trail"},)


REMEDIATION_HINTS: dict[ComplianceCheck, str] = {
    ComplianceCheck.RULESETS_CONFIGURED: (
        "Create a ruleset in GitHub Settings > Rules > Rulesets with required status "
        "checks for CI (e.g., test, lint). See GitHub docs on repository rulesets."
    ),
    ComplianceCheck.REQUIRED_REVIEWERS: (
        "Add CODEOWNERS file or required reviewer rule for sensitive paths "
        "(auth/**, billing/**, exports/**, infra/**). "
        "See GitHub docs on code owners and required reviewers."
    ),
    ComplianceCheck.BRANCH_PROTECTION: (
        "Enable branch protection on the default branch: require pull request reviews, "
        "dismiss stale reviews, require status checks. "
        "See GitHub Settings > Branches > Branch protection rules."
    ),
    ComplianceCheck.LABELS_EXIST: (
        "Create the following labels in GitHub: agent:in-progress, agent:queued, "
        "agent:done, agent:blocked. These are used by the Publisher for lifecycle tracking."
    ),
    ComplianceCheck.PROJECTS_V2: (
        "Configure Projects v2 integration for the repository, or set "
        "projects_v2_waived: true in the Repo Profile if not using Projects."
    ),
    ComplianceCheck.EXECUTION_PLANE_HEALTH: (
        "Verify the execution plane is deployed and healthy: workspace directory "
        "exists, workers are registered in Temporal, verification runner can invoke "
        "ruff/pytest. Check execution plane logs for errors."
    ),
    ComplianceCheck.PUBLISHER_IDEMPOTENCY: (
        "Verify the Publisher idempotency guard is operational. The TaskPacket "
        "lookup-before-create mechanism should prevent duplicate PRs. "
        "Check Publisher service health and database connectivity."
    ),
    ComplianceCheck.CREDENTIALS_SCOPED: (
        "Review GitHub token scope for this repo. Execute tier requires specific "
        "permissions (repo, workflow). Ensure the token is not over-permissioned "
        "and is scoped to this repository only."
    ),
    ComplianceCheck.ADVERSARIAL_CONTENT: (
        "Review issue content for suspicious patterns such as prompt injection, "
        "credential exposure, or tool manipulation commands."
    ),
    ComplianceCheck.EXECUTE_TIER_POLICY: (
        "Execute tier requires: (1) MergeMode.AUTO_MERGE explicitly configured in repo settings, "
        "(2) human approval wait states operational (Epic 21), "
        "(3) required reviewer rules must be mandatory-fail "
        "(not warn-and-pass) for all sensitive paths. "
        "Verify repo merge mode, Temporal workflow configuration, and CODEOWNERS coverage."
    ),
}


REQUIRED_LABELS = [
    "agent:in-progress",
    "agent:queued",
    "agent:done",
    "agent:blocked",
    "tier:execute",
]


SENSITIVE_PATHS = [
    "auth/**",
    "billing/**",
    "exports/**",
    "infra/**",
]
