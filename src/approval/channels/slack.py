"""Slack notification channel for approval workflows.

Epic 24 Story 24.5: Posts structured Block Kit messages to Slack via
incoming webhook. Includes approve/reject action buttons that call
back to TheStudio's approval API endpoints.

Optional — only active when THESTUDIO_SLACK_APPROVAL_WEBHOOK_URL is set.
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from src.approval.channels.base import NotificationChannel
from src.approval.review_context import ReviewContext

logger = logging.getLogger(__name__)


class SlackChannel(NotificationChannel):
    """Posts approval notifications to Slack via incoming webhook.

    Uses Slack Block Kit for structured messages with action buttons.
    Approve/reject buttons trigger callbacks to the TheStudio API.
    """

    def __init__(
        self,
        *,
        webhook_url: str,
        api_base_url: str = "",
    ) -> None:
        if not webhook_url:
            raise ValueError("Slack webhook URL is required")
        self._webhook_url = webhook_url
        self._api_base_url = api_base_url

    @property
    def channel_name(self) -> str:
        return "slack"

    async def notify_awaiting_approval(
        self,
        context: ReviewContext,
    ) -> bool:
        """Post a Block Kit message with approval actions to Slack."""
        blocks = self._build_approval_blocks(context)
        text = (
            f"TheStudio — Approval required for "
            f"{context.taskpacket.repo}: {context.taskpacket.issue_title}"
        )

        logger.info(
            "approval.channel.slack.awaiting_approval",
            extra={
                "taskpacket_id": str(context.taskpacket.taskpacket_id),
                "repo": context.taskpacket.repo,
                "channel": self.channel_name,
            },
        )

        return await self._post_webhook({"text": text, "blocks": blocks})

    async def notify_approved(
        self,
        taskpacket_id: UUID,
        approved_by: str,
    ) -> bool:
        """Post approval confirmation to Slack."""
        payload = {
            "text": f"Approved by {approved_by}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":white_check_mark: *Approved* by `{approved_by}`\n"
                            f"TaskPacket: `{taskpacket_id}`"
                        ),
                    },
                },
            ],
        }

        logger.info(
            "approval.channel.slack.approved",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "approved_by": approved_by,
                "channel": self.channel_name,
            },
        )
        return await self._post_webhook(payload)

    async def notify_rejected(
        self,
        taskpacket_id: UUID,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Post rejection notification to Slack."""
        payload = {
            "text": f"Rejected by {rejected_by}: {reason}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":x: *Rejected* by `{rejected_by}`\n"
                            f"TaskPacket: `{taskpacket_id}`\n"
                            f"Reason: {reason}"
                        ),
                    },
                },
            ],
        }

        logger.info(
            "approval.channel.slack.rejected",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "rejected_by": rejected_by,
                "reason": reason,
                "channel": self.channel_name,
            },
        )
        return await self._post_webhook(payload)

    async def notify_timeout(
        self,
        taskpacket_id: UUID,
    ) -> bool:
        """Post timeout warning to Slack."""
        payload = {
            "text": f"Approval timed out for {taskpacket_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":warning: *Approval Timed Out*\n"
                            f"TaskPacket: `{taskpacket_id}`\n"
                            f"The 7-day approval window has expired."
                        ),
                    },
                },
            ],
        }

        logger.info(
            "approval.channel.slack.timeout",
            extra={
                "taskpacket_id": str(taskpacket_id),
                "channel": self.channel_name,
            },
        )
        return await self._post_webhook(payload)

    def _build_approval_blocks(self, context: ReviewContext) -> list[dict]:
        """Build Slack Block Kit blocks for the approval request."""
        tp = context.taskpacket
        v_status = "PASSED" if context.verification.passed else "FAILED"
        qa_status = "PASSED" if context.qa.passed else "FAILED"

        files_text = "\n".join(
            f"• `{f}`" for f in context.evidence.files_changed[:10]
        ) or "No files recorded"
        if len(context.evidence.files_changed) > 10:
            files_text += f"\n• ... and {len(context.evidence.files_changed) - 10} more"

        criteria_text = "\n".join(
            f"• {c}" for c in context.intent.acceptance_criteria[:5]
        ) or "None specified"

        blocks: list[dict] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "TheStudio — Approval Required",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repo:*\n{tp.repo}"},
                    {"type": "mrkdwn", "text": f"*Tier:*\n{tp.repo_tier}"},
                    {"type": "mrkdwn", "text": f"*Issue:*\n{tp.issue_title}"},
                    {"type": "mrkdwn", "text": f"*TaskPacket:*\n`{tp.taskpacket_id}`"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Goal:* {context.intent.goal or 'Not specified'}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Acceptance Criteria:*\n{criteria_text}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Verification:* {v_status}"},
                    {"type": "mrkdwn", "text": f"*QA:* {qa_status}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Files Changed:*\n{files_text}",
                },
            },
        ]

        # Add PR link if available
        if context.pr_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*PR:* <{context.pr_url}|View Pull Request>",
                },
            })

        # Add action buttons
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": f"approve_{tp.taskpacket_id}",
                    "value": str(tp.taskpacket_id),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "action_id": f"reject_{tp.taskpacket_id}",
                    "value": str(tp.taskpacket_id),
                },
            ],
        })

        return blocks

    async def _post_webhook(self, payload: dict) -> bool:
        """Post a JSON payload to the Slack incoming webhook.

        Uses httpx for async HTTP. Falls back to logging on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._webhook_url,
                    json=payload,
                )
                if resp.status_code == 200:
                    return True

                logger.warning(
                    "approval.channel.slack.webhook_error",
                    extra={
                        "status_code": resp.status_code,
                        "response": resp.text[:200],
                    },
                )
                return False

        except Exception:
            logger.exception("approval.channel.slack.post_failed")
            return False
