"""Approval Review Context — aggregated evidence for human reviewers.

Epic 24 Story 24.1: Pydantic model that collects all information a reviewer
needs to make an informed approval decision: TaskPacket summary, intent spec,
QA results, verification results, evidence highlights, and diff summary.

The reviewer sees everything in one place instead of reconstructing context
from scattered sources.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskPacketSummary(BaseModel):
    """Minimal TaskPacket info for the review view."""

    taskpacket_id: UUID
    repo: str = ""
    status: str = ""
    repo_tier: str = "observe"
    issue_title: str = ""
    issue_number: int = 0
    created_at: datetime | None = None


class IntentSummary(BaseModel):
    """Intent spec summary for review."""

    goal: str = ""
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    version: int = 1


class VerificationCheckResult(BaseModel):
    """Single verification check result."""

    name: str
    passed: bool
    detail: str = ""


class VerificationSummary(BaseModel):
    """Verification gate results summary."""

    passed: bool = False
    checks: list[VerificationCheckResult] = Field(default_factory=list)
    loopback_count: int = 0


class QASummary(BaseModel):
    """QA agent results summary."""

    passed: bool = False
    defect_count: int = 0
    defect_categories: list[str] = Field(default_factory=list)
    loopback_count: int = 0


class EvidenceHighlights(BaseModel):
    """Key evidence data for reviewer consumption."""

    files_changed: list[str] = Field(default_factory=list)
    total_lines_added: int = 0
    total_lines_removed: int = 0
    agent_summary: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0


class DiffSummary(BaseModel):
    """High-level diff statistics."""

    files_added: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    files_removed: list[str] = Field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0


class ReviewContext(BaseModel):
    """Complete review context for a TaskPacket awaiting approval.

    Aggregates all information a reviewer needs to approve or reject:
    - What the task is (TaskPacket + Intent)
    - What the agent did (Evidence + Diff)
    - Whether it passed checks (Verification + QA)
    - Trust level (repo tier)
    """

    taskpacket: TaskPacketSummary
    intent: IntentSummary = Field(default_factory=IntentSummary)
    verification: VerificationSummary = Field(default_factory=VerificationSummary)
    qa: QASummary = Field(default_factory=QASummary)
    evidence: EvidenceHighlights = Field(default_factory=EvidenceHighlights)
    diff: DiffSummary = Field(default_factory=DiffSummary)
    pr_url: str = ""
    pr_number: int = 0

    def to_system_prompt(self) -> str:
        """Format review context as a system prompt for the chat LLM.

        The LLM uses this to answer reviewer questions about the changes.
        """
        criteria_list = "\n".join(
            f"  - {c}" for c in self.intent.acceptance_criteria
        ) or "  (none specified)"

        files_list = "\n".join(
            f"  - {f}" for f in self.evidence.files_changed
        ) or "  (no files changed)"

        checks_list = "\n".join(
            f"  - {c.name}: {'PASS' if c.passed else 'FAIL'} {c.detail}"
            for c in self.verification.checks
        ) or "  (no checks recorded)"

        return f"""You are a review assistant for TheStudio. You help human reviewers
understand proposed code changes. You answer questions about the changes
based ONLY on the evidence provided below. You do not make claims beyond
what the evidence shows. You cannot approve, reject, or modify the changes.

## Task
- TaskPacket: {self.taskpacket.taskpacket_id}
- Repo: {self.taskpacket.repo}
- Tier: {self.taskpacket.repo_tier}
- Issue: {self.taskpacket.issue_title}

## Intent
Goal: {self.intent.goal}
Acceptance Criteria:
{criteria_list}

## What Changed
{files_list}
Agent Summary: {self.evidence.agent_summary}

## Verification
Passed: {self.verification.passed}
{checks_list}

## QA
Passed: {self.qa.passed}
Defects: {self.qa.defect_count}

## PR
URL: {self.pr_url}
"""


async def build_review_context(
    taskpacket_id: UUID,
    *,
    session: Any = None,
) -> ReviewContext | None:
    """Assemble a ReviewContext from the database.

    Returns None if the TaskPacket doesn't exist or isn't in
    AWAITING_APPROVAL status.

    Args:
        taskpacket_id: UUID of the TaskPacket to build context for.
        session: AsyncSession (optional, for production use).
    """
    if session is None:
        logger.warning(
            "build_review_context called without session",
            extra={"taskpacket_id": str(taskpacket_id)},
        )
        return None

    try:
        from src.models.taskpacket import TaskPacketStatus
        from src.models.taskpacket_crud import get_by_id

        taskpacket = await get_by_id(session, taskpacket_id)
        if taskpacket is None:
            return None

        if taskpacket.status != TaskPacketStatus.AWAITING_APPROVAL:
            return None

        return ReviewContext(
            taskpacket=TaskPacketSummary(
                taskpacket_id=taskpacket.id,
                repo=taskpacket.repo,
                status=taskpacket.status.value,
                issue_title=getattr(taskpacket, "issue_title", ""),
                created_at=taskpacket.created_at,
            ),
        )
    except Exception:
        logger.exception(
            "Failed to build review context",
            extra={"taskpacket_id": str(taskpacket_id)},
        )
        return None
