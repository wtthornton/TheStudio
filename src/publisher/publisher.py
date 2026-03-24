"""Publisher — creates draft PRs on GitHub with evidence comments and lifecycle labels.

Single writer to GitHub. Idempotency key = TaskPacket ID + intent version.
Observe tier: draft PRs only. Suggest tier: ready-for-review after V+QA pass.
Execute tier: ready-for-review + auto-merge after V+QA+approval pass.

Architecture reference: Epic 0 Story 0.7, Epic 1 Story 1.10 (tier promotion),
Epic 22 (Execute tier end-to-end)
"""

import fnmatch
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.merge_mode import MergeMode, get_merge_mode
from src.agent.evidence import EvidenceBundle
from src.intent.intent_crud import get_latest_for_taskpacket
from src.intent.intent_spec import IntentSpecRead
from src.dashboard.models.trust_config import AssignedTier, SafeBoundsRead, get_safety_bounds
from src.dashboard.trust_engine import _cap_tier
from src.models.taskpacket import PrMergeStatus, TaskPacketStatus, TaskTrustTier
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
LABEL_TIER_EXECUTE = "tier:execute"

# Map tier to its label for reconciliation
TIER_LABELS: dict[RepoTier, str] = {
    RepoTier.OBSERVE: LABEL_TIER_OBSERVE,
    RepoTier.SUGGEST: LABEL_TIER_SUGGEST,
    RepoTier.EXECUTE: LABEL_TIER_EXECUTE,
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
    auto_merge_enabled: bool = False  # True if auto-merge was enabled (Execute tier)


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


async def _check_safety_bounds_at_publish(
    session: AsyncSession,
    packet: object,
    correlation_id: UUID,
) -> tuple[bool, list[str]]:
    """Pre-publish safety bound re-check.

    Verifies the TaskPacket's metrics against the current safety bounds at
    publish time.  This catches cases where bounds were tightened after the
    trust tier was assigned, or where packet metrics changed during the
    pipeline (e.g., loopback_count increased).

    Returns:
        (safe, reasons) — safe is True when all bounds are satisfied.
        reasons contains human-readable descriptions of each violation.
    """
    bounds: SafeBoundsRead = await get_safety_bounds(session)
    reasons: list[str] = []

    # 1. Loopback count
    loopback_count = getattr(packet, "loopback_count", 0)
    if bounds.max_loopbacks is not None and loopback_count > bounds.max_loopbacks:
        reasons.append(
            f"loopback_count={loopback_count} > max_loopbacks={bounds.max_loopbacks}"
        )

    # 2. Estimated cost (field may not exist on older TaskPackets)
    estimated_cost = getattr(packet, "estimated_cost", None)
    if (
        estimated_cost is not None
        and bounds.max_auto_merge_cost is not None
        and estimated_cost > bounds.max_auto_merge_cost
    ):
        reasons.append(
            f"estimated_cost={estimated_cost} > max_auto_merge_cost={bounds.max_auto_merge_cost}"
        )

    # 3. Diff lines from scope
    scope = getattr(packet, "scope", None)
    diff_lines: int | None = None
    if isinstance(scope, dict):
        raw_dl = scope.get("diff_lines") or scope.get("changed_lines")
        if raw_dl is not None:
            try:
                diff_lines = int(raw_dl)
            except (TypeError, ValueError):
                pass
    if (
        diff_lines is not None
        and bounds.max_auto_merge_lines is not None
        and diff_lines > bounds.max_auto_merge_lines
    ):
        reasons.append(
            f"diff_lines={diff_lines} > max_auto_merge_lines={bounds.max_auto_merge_lines}"
        )

    # 4. Mandatory review patterns
    repo = getattr(packet, "repo", "")
    for pattern in bounds.mandatory_review_patterns:
        if fnmatch.fnmatch(repo, pattern):
            reasons.append(
                f"repo '{repo}' matches mandatory-review pattern '{pattern}'"
            )
            break

    safe = len(reasons) == 0
    if not safe:
        logger.info(
            "Safety bound violations at publish time: %s (correlation_id=%s)",
            "; ".join(reasons),
            correlation_id,
        )
    return safe, reasons


def _compute_effective_tier(
    repo_tier: RepoTier,
    task_trust_tier: TaskTrustTier | None,
) -> RepoTier:
    """Compute the effective tier for publish-time decisions.

    The effective tier is the minimum (most restrictive) of the repo-level
    tier and the task-level tier.  When task_trust_tier is None (legacy
    packets that predate the trust rule engine), falls back to repo_tier.

    Uses _cap_tier from the trust engine, bridging via AssignedTier which
    shares the same string values as both RepoTier and TaskTrustTier.
    """
    if task_trust_tier is None:
        return repo_tier

    # Bridge to AssignedTier for the cap calculation
    task_at = AssignedTier(task_trust_tier.value)
    repo_at = AssignedTier(repo_tier.value)

    capped = _cap_tier(task_at, repo_at)

    # Convert back to RepoTier
    return RepoTier(capped.value)


async def publish(
    session: AsyncSession,
    taskpacket_id: UUID,
    evidence: EvidenceBundle,
    verification: VerificationResult,
    github: GitHubClient,
    repo_tier: RepoTier = RepoTier.OBSERVE,
    qa_passed: bool = False,
    approval_received: bool = False,
    merge_method: str = "squash",
) -> PublishResult:
    """Publish a draft PR with evidence comment and lifecycle labels.

    Idempotency: If a PR already exists for this TaskPacket + intent version
    (same branch name), updates the existing PR's evidence comment instead
    of creating a duplicate.

    Tier behavior:
    - Observe: creates draft PR (existing behavior)
    - Suggest: creates draft PR, then marks ready-for-review after V+QA pass
    - Execute: marks ready-for-review + enables auto-merge after V+QA+approval

    Transitions TaskPacket status: verification_passed -> published.

    Args:
        session: Database session.
        taskpacket_id: TaskPacket being published.
        evidence: Evidence bundle from Primary Agent.
        verification: Verification result (must be passed).
        github: Authenticated GitHub API client.
        repo_tier: Current repo tier (controls ready-for-review behavior).
        qa_passed: Whether QA validation passed.
        approval_received: Whether human approval was received (Epic 21).
        merge_method: Merge method for auto-merge (squash, merge, rebase).

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

        # Compute effective tier: min(task_trust_tier, repo_tier)
        task_tier = getattr(taskpacket, "task_trust_tier", None)
        effective_tier = _compute_effective_tier(repo_tier, task_tier)
        logger.debug(
            "Publisher tier resolution: task_trust_tier=%s, repo_tier=%s, effective=%s "
            "(correlation_id=%s)",
            task_tier,
            repo_tier,
            effective_tier,
            taskpacket.correlation_id,
        )

        # Load intent for evidence comment
        intent = await get_latest_for_taskpacket(session, taskpacket_id)
        if intent is None:
            raise ValueError(f"No IntentSpec found for TaskPacket {taskpacket_id}")

        owner, repo_name = taskpacket.repo.split("/", 1)
        branch = _branch_name(taskpacket_id, intent.version)
        merge_mode = get_merge_mode(taskpacket.repo)

        # Idempotency check — look for existing PR with same branch
        existing_pr = await github.find_pr_by_head(owner, repo_name, branch)

        marked_ready = False
        auto_merge_enabled = False

        # Pre-publish safety bounds re-check (Epic 42 — Story 42.2)
        safety_ok, safety_reasons = await _check_safety_bounds_at_publish(
            session, taskpacket, taskpacket.correlation_id,
        )

        if existing_pr is not None:
            # Update existing PR's evidence comment
            pr_number = existing_pr["number"]
            pr_url = existing_pr["html_url"]
            comment_id = await _update_evidence_comment(
                github, owner, repo_name, pr_number, evidence, intent, verification
            )
            span.set_attribute("thestudio.publish_action", "updated")
            logger.info("Updated existing PR #%d for TaskPacket %s", pr_number, taskpacket_id)

            # Suggest/Execute tier: mark ready-for-review if V+QA passed
            if _should_mark_ready(effective_tier, verification.passed, qa_passed, merge_mode):
                await github.mark_ready_for_review(owner, repo_name, pr_number)
                marked_ready = True

            # Execute tier: enable auto-merge if all gates passed
            # Safety bounds violation blocks auto-merge but not mark-ready
            if not safety_ok:
                logger.warning(
                    "Safety bounds violated — auto-merge blocked for TaskPacket %s: %s "
                    "(correlation_id=%s)",
                    taskpacket_id,
                    "; ".join(safety_reasons),
                    taskpacket.correlation_id,
                )
            elif _should_enable_auto_merge(
                effective_tier, verification.passed, qa_passed, merge_mode, approval_received
            ):
                auto_merge_enabled = await _try_enable_auto_merge(
                    github, owner, repo_name, pr_number, merge_method
                )

            # Persist auto_merged flag (Epic 42 — Story 42.3d)
            if auto_merge_enabled:
                from src.models.taskpacket import TaskPacketRow

                tp_row = await session.get(TaskPacketRow, taskpacket_id)
                if tp_row is not None:
                    tp_row.auto_merged = True

            # Reconcile tier labels
            await _reconcile_tier_labels(github, owner, repo_name, pr_number, effective_tier)

            await update_status(session, taskpacket_id, TaskPacketStatus.PUBLISHED)
            return PublishResult(
                pr_number=pr_number,
                pr_url=pr_url,
                created=False,
                comment_id=comment_id,
                marked_ready=marked_ready,
                auto_merge_enabled=auto_merge_enabled,
            )

        # Create new branch and PR (branch may already exist from implement step)
        default_branch = await github.get_default_branch(owner, repo_name)
        try:
            base_sha = await github.get_branch_sha(owner, repo_name, default_branch)
            await github.create_branch(owner, repo_name, branch, base_sha)
        except Exception as exc:
            if "Reference already exists" not in str(exc):
                raise
            logger.info("Branch %s already exists (created by implement step)", branch)

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
        await _reconcile_tier_labels(github, owner, repo_name, pr_number, effective_tier)

        # Suggest/Execute tier: mark ready-for-review if V+QA passed
        if _should_mark_ready(effective_tier, verification.passed, qa_passed, merge_mode):
            await github.mark_ready_for_review(owner, repo_name, pr_number)
            marked_ready = True

        # Execute tier: enable auto-merge if all gates passed
        # Safety bounds violation blocks auto-merge but not mark-ready
        if not safety_ok:
            logger.warning(
                "Safety bounds violated — auto-merge blocked for TaskPacket %s: %s "
                "(correlation_id=%s)",
                taskpacket_id,
                "; ".join(safety_reasons),
                taskpacket.correlation_id,
            )
        elif _should_enable_auto_merge(
            effective_tier, verification.passed, qa_passed, merge_mode, approval_received
        ):
            auto_merge_enabled = await _try_enable_auto_merge(
                github, owner, repo_name, pr_number, merge_method
            )

        # Persist PR metadata on TaskPacket
        from src.models.taskpacket import TaskPacketRow

        tp_row = await session.get(TaskPacketRow, taskpacket_id)
        if tp_row is not None:
            tp_row.pr_number = pr_number
            tp_row.pr_url = pr_url
            # Epic 39.0b: initialise merge status to OPEN on PR creation
            tp_row.pr_merge_status = PrMergeStatus.OPEN
            # Persist auto_merged flag (Epic 42 — Story 42.3d)
            if auto_merge_enabled:
                tp_row.auto_merged = True

        # Transition status
        await update_status(session, taskpacket_id, TaskPacketStatus.PUBLISHED)

        span.set_attribute("thestudio.publish_action", "created")
        span.set_attribute("thestudio.pr_number", pr_number)
        span.set_attribute("thestudio.marked_ready", marked_ready)
        span.set_attribute("thestudio.auto_merge_enabled", auto_merge_enabled)
        span.set_attribute("thestudio.merge_method", merge_method)
        span.set_attribute("thestudio.execute_tier_active", effective_tier == RepoTier.EXECUTE)
        logger.info(
            "Published %s PR #%d for TaskPacket %s: %s",
            "auto-merge" if auto_merge_enabled
            else ("ready-for-review" if marked_ready else "draft"),
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
            auto_merge_enabled=auto_merge_enabled,
        )


LABEL_HUMAN_REVIEW = "agent:human-review"

APPROVAL_COMMENT_MARKER = "<!-- thestudio-approval-request -->"

ESCALATION_COMMENT_MARKER = "<!-- thestudio-approval-timeout -->"


async def post_approval_request(
    github: GitHubClient,
    owner: str,
    repo_name: str,
    issue_number: int,
    taskpacket_id: UUID,
    intent_summary: str,
    qa_passed: bool,
) -> int:
    """Post a comment requesting human approval before publish.

    Idempotent: if a comment with APPROVAL_COMMENT_MARKER already exists,
    it is updated instead of duplicated.

    Returns the comment ID.
    """
    qa_status = "PASSED" if qa_passed else "FAILED"
    body = f"""{APPROVAL_COMMENT_MARKER}

## Approval Required

This task has passed QA and is ready for human approval before publishing.

| Field | Value |
|-------|-------|
| **TaskPacket ID** | `{taskpacket_id}` |
| **Intent** | {intent_summary} |
| **QA Result** | {qa_status} |

### How to Approve

Use the approval API endpoint:

```
POST /api/tasks/{taskpacket_id}/approve
{{"approved_by": "your-email@example.com"}}
```

**Timeout:** This task will expire after **7 days** if not approved.

---
*Generated by TheStudio — awaiting human approval*
"""

    # Idempotent: search for existing approval comment
    resp = await github._client.get(
        f"/repos/{owner}/{repo_name}/issues/{issue_number}/comments"
    )
    resp.raise_for_status()
    comments = resp.json()

    for comment in comments:
        if APPROVAL_COMMENT_MARKER in comment.get("body", ""):
            await github.update_comment(owner, repo_name, comment["id"], body)
            logger.info(
                "Updated approval request comment on %s/%s#%d for TaskPacket %s",
                owner, repo_name, issue_number, taskpacket_id,
            )
            return comment["id"]  # type: ignore[no-any-return]

    comment_data = await github.add_comment(owner, repo_name, issue_number, body)
    logger.info(
        "Posted approval request comment on %s/%s#%d for TaskPacket %s",
        owner, repo_name, issue_number, taskpacket_id,
    )
    return comment_data["id"]  # type: ignore[no-any-return]


async def escalate_approval_timeout(
    github: GitHubClient,
    owner: str,
    repo_name: str,
    issue_number: int,
    taskpacket_id: UUID,
) -> None:
    """Escalate a task that timed out waiting for approval.

    Applies the ``agent:human-review`` label and posts an escalation comment.
    Idempotent: duplicate calls do not create duplicate labels or comments.
    """
    body = f"""{ESCALATION_COMMENT_MARKER}

## Approval Expired

Approval wait expired after **7 days** for TaskPacket `{taskpacket_id}`.
This task has been paused and will not be published.

**Manual action required** to proceed.

---
*Generated by TheStudio — approval timeout escalation*
"""

    # Apply label (idempotent — GitHub ignores duplicates)
    await github.add_labels(owner, repo_name, issue_number, [LABEL_HUMAN_REVIEW])

    # Post escalation comment (idempotent — check for existing)
    resp = await github._client.get(
        f"/repos/{owner}/{repo_name}/issues/{issue_number}/comments"
    )
    resp.raise_for_status()
    comments = resp.json()

    for comment in comments:
        if ESCALATION_COMMENT_MARKER in comment.get("body", ""):
            await github.update_comment(owner, repo_name, comment["id"], body)
            logger.info(
                "Updated escalation comment on %s/%s#%d for TaskPacket %s",
                owner, repo_name, issue_number, taskpacket_id,
            )
            return

    await github.add_comment(owner, repo_name, issue_number, body)
    logger.info(
        "Posted escalation comment on %s/%s#%d for TaskPacket %s",
        owner, repo_name, issue_number, taskpacket_id,
    )


def _should_mark_ready(
    repo_tier: RepoTier,
    verification_passed: bool,
    qa_passed: bool,
    merge_mode: MergeMode | None = None,
) -> bool:
    """Determine if a PR should be marked ready-for-review.

    When merge_mode is provided, it overrides tier-based behavior:
    - DRAFT_ONLY: never mark ready (always stays draft)
    - REQUIRE_REVIEW: mark ready when V+QA pass in Suggest/Execute tier
    - AUTO_MERGE: mark ready when V+QA pass in Suggest/Execute tier

    When merge_mode is None (legacy callers), uses tier-only logic.
    Observe tier always stays as draft regardless of merge mode.
    """
    if merge_mode == MergeMode.DRAFT_ONLY:
        return False
    return (
        repo_tier in (RepoTier.SUGGEST, RepoTier.EXECUTE)
        and verification_passed
        and qa_passed
    )


def _should_enable_auto_merge(
    repo_tier: RepoTier,
    verification_passed: bool,
    qa_passed: bool,
    merge_mode: MergeMode | None = None,
    approval_received: bool = False,
) -> bool:
    """Determine if auto-merge should be enabled on a PR.

    Auto-merge requires ALL of:
    - Execute tier
    - MergeMode.AUTO_MERGE explicitly configured
    - Verification passed
    - QA passed
    - Human approval received (Epic 21)
    """
    return (
        repo_tier == RepoTier.EXECUTE
        and merge_mode == MergeMode.AUTO_MERGE
        and verification_passed
        and qa_passed
        and approval_received
    )


async def _try_enable_auto_merge(
    github: GitHubClient,
    owner: str,
    repo_name: str,
    pr_number: int,
    merge_method: str = "squash",
) -> bool:
    """Attempt to enable auto-merge on a PR. Returns True on success.

    Degrades gracefully: if auto-merge is not available on the repo
    (e.g., not enabled in GitHub settings), logs a warning and returns False.
    """
    try:
        await github.enable_auto_merge(owner, repo_name, pr_number, merge_method)
        logger.info(
            "Enabled auto-merge (%s) on PR #%d for %s/%s",
            merge_method, pr_number, owner, repo_name,
        )
        return True
    except Exception:
        logger.warning(
            "Failed to enable auto-merge on PR #%d for %s/%s — "
            "repo may not have auto-merge enabled in GitHub settings",
            pr_number, owner, repo_name,
            exc_info=True,
        )
        return False


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
