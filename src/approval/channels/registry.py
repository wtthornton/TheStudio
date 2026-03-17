"""Channel registry — resolves configured notification channels.

Epic 24 Story 24.4: Returns the list of active notification channels
based on application settings. Used by post_approval_request_activity
to fan out notifications.
"""

from __future__ import annotations

import logging

from src.approval.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


def get_configured_channels() -> list[NotificationChannel]:
    """Return the list of notification channels enabled in settings.

    Always includes GitHub. Includes Slack if configured.
    """
    channels: list[NotificationChannel] = []

    # GitHub is always available
    from src.approval.channels.github import GitHubChannel

    channels.append(GitHubChannel())

    # Slack is optional — only if configured
    try:
        from src.settings import settings

        slack_webhook = getattr(settings, "slack_approval_webhook_url", "")
        if slack_webhook:
            from src.approval.channels.slack import SlackChannel

            channels.append(SlackChannel(webhook_url=slack_webhook))
    except Exception:
        logger.debug("Slack channel not configured", exc_info=True)

    return channels
