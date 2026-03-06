"""Publisher — creates draft PRs on GitHub with evidence comments and lifecycle labels.

Single writer to GitHub. Idempotency key = TaskPacket ID + intent version.
Observe tier: draft PRs only. Suggest tier: ready-for-review after V+QA pass.

Architecture reference: Epic 0 Story 0.7, Epic 1 Story 1.10 (tier promotion)
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.evidence import EvidenceBundle
from src.intent.intent_crud import get_latest_for_taskpacket
from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id, update_status
from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_TASKPACKET_ID,
    SPAN_PUBLISHER_PUBLISH,
)
from src.observability.tracing import get_tracer
from src.publisher.evidence_comment import (
    EVIDENCE_COMMENT_MARKER,
    format_evidence_comment,
)
from src.publisher.github_client import GitHubClient
from src.repo.repo_profile import RepoTier
from src.verification.gate import VerificationResult

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.publisher")

LABEL_IN_PROGRESS = "agent:in-progress"
LABEL_DONE = "agent:done"
LABEL_TIER_OBSERVE = "tier:observe"
LABEL_TIER_SUGGEST = "tier:suggest"

# Map tier to its label for reconciliation
TIER_LABELS: dict[RepoTier, str] = {
    RepoTier.OBSERVE: LABEL_TIER_OBSERVE,
    RepoTier.SUGGEST: LABEL_TIER_SUGGEST,
}
ALL_TIER_LABELS = frozenset(TIER_LABELS.values())


@dataclass
class PublishResult:
    """Result of a publish operation."""

    pr_number: int
    pr_url: str
    created: bool  # True if new PR, False if updated existing
    comment_id: int
    marked_ready: bool = False  # True if PR was marked ready-for-review


def _branch_name(taskpacket_id: UUID, intent_version: int) -> str:
    """Deterministic branch name from idempotency key."""
    short_id = str(taskpacket_id)[:8]
    return f"thestudio/{short_id}/v{intent_version}"


def _pr_title(goal: str) -> str:
    """Build PR title from intent goal, truncated to 72 chars."""
    prefix = "[TheStudio] "
    max_goal_len = 72 - len(prefix)
    truncated = goal[:max_goal_len] if len(goal) > max_goal_len else goal
    return f"{prefix}{truncated}"


async def _reconcile_tier_labels(
    github: GitHubClient,
    owner: str,
    repo_name: str,
    pr_number: int,
    tier: RepoTier,
) -> None:
    """Reconcile tier labels on a PR — add correct tier, remove stale ones."""
    correct_label = TIER_LABELS.get(tier)
    if correct_label is None:
        return

    # Remove all tier labels that aren't the correct one
    for label in ALL_TIER_LABELS:
        if label != correct_label:
            await github.remove_label(owner, repo_name, pr_number, label)

    # Add the correct tier label
    await github.add_labels(owner, repo_name, pr_number, [correct_label])


async def publish(
    session: AsyncSession,
    taskpacket_id: UUID,
    evidence: EvidenceBundle,
    verification: VerificationResult,
    github: GitHubClient,
    repo_tier: RepoTier = RepoTier.OBSERVE,
    qa_passed: bool = False,
) -> PublishResult:
    """Publish a draft PR with evidence comment and lifecycle labels.

    Idempotency: If a PR already exists for this TaskPacket + intent version
    (same branch name), updates the existing PR's evidence comment instead
    of creating a duplicate.

    Tier behavior:
    - Observe: creates draft PR (existing behavior)
    - Suggest: creates draft PR, then marks ready-for-review after V+QA pass

    Transitions TaskPacket status: verification_passed -> published.

    Args:
        session: Database session.
        taskpacket_id: TaskPacket being published.
        evidence: Evidence bundle from Primary Agent.
        verification: Verification result (must be passed).
        github: Authenticated GitHub API client.
        repo_tier: Current repo tier (controls ready-for-review behavior).
        qa_passed: Whether QA validation passed.

    Returns:
        PublishResult with PR details.

    Raises:
        ValueError: If TaskPacket not found or verification not passed.
    """
    with tracer.start_as_current_span(SPAN_PUBLISHER_PUBLISH) as span:
        # Load TaskPacket
        taskpacket = await get_by_id(session, taskpacket_id)
        if taskpacket is None:
            raise ValueError(f"TaskPacket {taskpacket_id} not found")

        span.set_attribute(ATTR_TASKPACKET_ID, str(taskpacket_id))
        span.set_attribute(ATTR_CORRELATION_ID, str(taskpacket.correlation_id))

        if not verification.passed:
            raise ValueError("Cannot publish: verification has not passed")

        # Load intent for evidence comment
        intent = await get_latest_for_taskpacket(session, taskpacket_id)
        if intent is None:
            raise ValueError(f"No IntentSpec found for TaskPacket {taskpacket_id}")

        owner, repo_name = taskpacket.repo.split("/", 1)
        branch = _branch_name(taskpacket_id, intent.version)

        # Idempotency check — look for existing PR with same branch
        existing_pr = await github.find_pr_by_head(owner, repo_name, branch)

        marked_ready = False

        if existing_pr is not None:
            # Update existing PR's evidence comment
            pr_number = existing_pr["number"]
            pr_url = existing_pr["html_url"]
            comment_id = await _update_evidence_comment(
                github, owner, repo_name, pr_number, evidence, intent, verification
            )
            span.set_attribute("thestudio.publish_action", "updated")
            logger.info("Updated existing PR #%d for TaskPacket %s", pr_number, taskpacket_id)

            # Suggest tier: mark ready-for-review if V+QA passed
            if _should_mark_ready(repo_tier, verification.passed, qa_passed):
                await github.mark_ready_for_review(owner, repo_name, pr_number)
                marked_ready = True

            # Reconcile tier labels
            await _reconcile_tier_labels(github, owner, repo_name, pr_number, repo_tier)

            await update_status(session, taskpacket_id, TaskPacketStatus.PUBLISHED)
            return PublishResult(
                pr_number=pr_number,
                pr_url=pr_url,
                created=False,
                comment_id=comment_id,
                marked_ready=marked_ready,
            )

        # Create new branch and PR
        default_branch = await github.get_default_branch(owner, repo_name)
        base_sha = await github.get_branch_sha(owner, repo_name, default_branch)
        await github.create_branch(owner, repo_name, branch, base_sha)

        # Create draft PR
        comment_body = format_evidence_comment(evidence, intent, verification)
        pr_data = await github.create_pull_request(
            owner=owner,
            repo=repo_name,
            title=_pr_title(intent.goal),
            body=f"Implements: {intent.goal}\n\nTaskPacket: `{taskpacket_id}`",
            head_branch=branch,
            base_branch=default_branch,
            draft=True,
        )
        pr_number = pr_data["number"]
        pr_url = pr_data["html_url"]

        # Add evidence comment
        comment_data = await github.add_comment(owner, repo_name, pr_number, comment_body)
        comment_id = comment_data["id"]

        # Apply lifecycle labels: start with in-progress, then done
        await github.add_labels(owner, repo_name, pr_number, [LABEL_IN_PROGRESS])
        await github.remove_label(owner, repo_name, pr_number, LABEL_IN_PROGRESS)
        await github.add_labels(owner, repo_name, pr_number, [LABEL_DONE])

        # Reconcile tier labels
        await _reconcile_tier_labels(github, owner, repo_name, pr_number, repo_tier)

        # Suggest tier: mark ready-for-review if V+QA passed
        if _should_mark_ready(repo_tier, verification.passed, qa_passed):
            await github.mark_ready_for_review(owner, repo_name, pr_number)
            marked_ready = True

        # Transition status
        await update_status(session, taskpacket_id, TaskPacketStatus.PUBLISHED)

        span.set_attribute("thestudio.publish_action", "created")
        span.set_attribute("thestudio.pr_number", pr_number)
        span.set_attribute("thestudio.marked_ready", marked_ready)
        logger.info(
            "Published %s PR #%d for TaskPacket %s: %s",
            "ready-for-review" if marked_ready else "draft",
            pr_number,
            taskpacket_id,
            pr_url,
        )

        return PublishResult(
            pr_number=pr_number,
            pr_url=pr_url,
            created=True,
            comment_id=comment_id,
            marked_ready=marked_ready,
        )


def _should_mark_ready(
    repo_tier: RepoTier, verification_passed: bool, qa_passed: bool
) -> bool:
    """Determine if a PR should be marked ready-for-review.

    Only in Suggest tier, and only when both verification and QA have passed.
    Observe tier always stays as draft. Execute tier is Phase 2.
    """
    return (
        repo_tier == RepoTier.SUGGEST
        and verification_passed
        and qa_passed
    )


async def _update_evidence_comment(
    github: GitHubClient,
    owner: str,
    repo_name: str,
    pr_number: int,
    evidence: EvidenceBundle,
    intent: IntentSpecRead,
    verification: VerificationResult,
) -> int:
    """Find and update the existing evidence comment, or create a new one."""

    comment_body = format_evidence_comment(evidence, intent, verification)

    # Search existing comments for our marker
    resp = await github._client.get(
        f"/repos/{owner}/{repo_name}/issues/{pr_number}/comments"
    )
    resp.raise_for_status()
    comments = resp.json()

    for comment in comments:
        if EVIDENCE_COMMENT_MARKER in comment.get("body", ""):
            await github.update_comment(owner, repo_name, comment["id"], comment_body)
            return comment["id"]  # type: ignore[no-any-return]

    # No existing evidence comment — create new
    comment_data = await github.add_comment(owner, repo_name, pr_number, comment_body)
    return comment_data["id"]  # type: ignore[no-any-return]
