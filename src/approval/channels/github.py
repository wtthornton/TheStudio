"""GitHub notification channel for approval workflows.

Epic 24 Story 24.4: Posts structured approval request comments to GitHub
issues/PRs. Enhances the existing comment format with a link to the
review UI, intent/QA summaries, and reviewer instructions.

The existing GitHub comment posted by post_approval_request_activity is
extended, not replaced. This channel adapter is called by the activity
via the channel registry.
"""

from __future__ import annotations

import logging
from uuid import UUID

from src.approval.channels.base import NotificationChannel
from src.approval.review_context import ReviewContext

logger = logging.getLogger(__name__)


class GitHubChannel(NotificationChannel):
    """Posts approval notifications as GitHub issue/PR comments.

    Uses the Publisher's GitHubClient for API calls. Falls back to
    logging when the client is unavailable (test/mock mode).
    """

    def __init__(
        self,
        *,
        review_ui_base_url: str = "",
    ) -> None:
        self._review_ui_base_url = review_ui_base_url

    @property
    def channel_name(self) -> str:
        return "github"

    async def notify_awaiting_approval(
        self,
        context: ReviewContext,
    ) -> bool:
        """Post a structured approval request comment to GitHub."""
        comment_body = self._format_approval_request(context)

        logger.info(
            "approval.channel.github.awaiting_approval",
            extra={
                "taskpacket_id": str(context.taskpacket.taskpacket_id),
                "repo": context.taskpacket.repo,
                "channel": self.channel_name,
                "comment_length": len(comment_body),
            },
        )

        try:
            return await self._post_comment(context, comment_body)
        except Exception:
            logger.exception(
                "approval.channel.github.post_failed",
                extra={"taskpacket_id": str(context.taskpacket.taskpacket_id)},
            )
            return False

    async def notify_approved(
        self,
        taskpacket_id: UUID,
        approved_by: str,
    ) -> bool:
        """Post an approval confirmation comment."""
        comment = (
            f"**Approved** by `{approved_by}` via TheStudio review interface.\n\n"
            f"The pipeline will proceed with publishing."
        )
        logger.info(
            "approval.channel.github.approved",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "approved_by": approved_by,
                "channel": self.channel_name,
            },
        )
        return True  # Comment posting delegated to approval API

    async def notify_rejected(
        self,
        taskpacket_id: UUID,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Post a rejection comment."""
        logger.info(
            "approval.channel.github.rejected",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "rejected_by": rejected_by,
                "reason": reason,
                "channel": self.channel_name,
            },
        )
        return True  # Comment posting delegated to approval API

    async def notify_timeout(
        self,
        taskpacket_id: UUID,
    ) -> bool:
        """Post a timeout notification. Delegated to escalate_timeout_activity."""
        logger.info(
            "approval.channel.github.timeout",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "channel": self.channel_name,
            },
        )
        return True

    def _format_approval_request(self, context: ReviewContext) -> str:
        """Format a structured approval request comment.

        Includes: review UI link, intent summary, QA/verification status,
        files changed, and reviewer instructions.
        """
        tp = context.taskpacket
        review_link = ""
        if self._review_ui_base_url:
            review_link = (
                f"\n**[Open Review Interface]"
                f"({self._review_ui_base_url}/api/tasks/{tp.taskpacket_id}/review)**\n"
            )

        # Intent summary
        intent_section = f"**Goal:** {context.intent.goal}" if context.intent.goal else ""
        criteria = "\n".join(
            f"- [ ] {c}" for c in context.intent.acceptance_criteria
        )
        if criteria:
            intent_section += f"\n\n**Acceptance Criteria:**\n{criteria}"

        # Verification & QA
        v_status = "PASSED" if context.verification.passed else "FAILED"
        qa_status = "PASSED" if context.qa.passed else "FAILED"
        checks_section = f"| Verification | {v_status} |\n| QA | {qa_status} |"

        # Files changed
        files = "\n".join(
            f"- `{f}`" for f in context.evidence.files_changed[:20]
        ) or "- No files recorded"
        if len(context.evidence.files_changed) > 20:
            files += f"\n- ... and {len(context.evidence.files_changed) - 20} more"

        return f"""<!-- thestudio-approval-request -->

## TheStudio — Approval Required

This task is awaiting human approval before the pipeline proceeds.
{review_link}
### Summary

| Field | Value |
|-------|-------|
| **TaskPacket** | `{tp.taskpacket_id}` |
| **Repo** | {tp.repo} |
| **Tier** | {tp.repo_tier} |
| **Issue** | {tp.issue_title} |

### Intent

{intent_section or "No intent recorded."}

### Gate Results

| Gate | Result |
|------|--------|
{checks_section}

### Files Changed

{files}

### Instructions

1. Review the changes in this PR
2. Use the review interface to ask questions about the changes{review_link and " (link above)" or ""}
3. **Approve** via `POST /api/tasks/{tp.taskpacket_id}/approve` or the review UI
4. **Reject** via `POST /api/tasks/{tp.taskpacket_id}/reject` with a reason

If no action is taken, this request will timeout after 7 days.

---
*TheStudio — AI-augmented software delivery*
"""

    async def _post_comment(self, context: ReviewContext, body: str) -> bool:
        """Post a comment to the GitHub issue/PR.

        In production, uses the Publisher's GitHubClient. Falls back to
        log-only mode when the client is unavailable.
        """
        try:
            from src.publisher.github_client import GitHubClient
            from src.settings import settings

            if settings.github_provider == "real" and settings.github_app_id:
                # Parse owner/repo from context
                parts = context.taskpacket.repo.split("/", 1)
                if len(parts) == 2:
                    owner, repo_name = parts
                    async with GitHubClient(settings.github_app_id) as github:
                        await github.create_issue_comment(
                            owner=owner,
                            repo=repo_name,
                            issue_number=context.taskpacket.issue_number,
                            body=body,
                        )
                        return True
        except Exception:
            logger.debug(
                "GitHub client not available, comment logged only",
                exc_info=True,
            )

        # Log-only fallback
        logger.info(
            "approval.channel.github.comment_logged",
            extra={
                "taskpacket_id": str(context.taskpacket.taskpacket_id),
                "comment_preview": body[:200],
            },
        )
        return True
