"""Abstract base class for notification channels.

Epic 24 Story 24.4: Defines the NotificationChannel interface that all
channel adapters must implement. Each method handles a specific approval
lifecycle event.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from src.approval.review_context import ReviewContext

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base for approval notification channels.

    Implementations: GitHubChannel, SlackChannel.
    Each method is async and should be idempotent.
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Identifier for this channel (e.g. 'github', 'slack')."""

    @abstractmethod
    async def notify_awaiting_approval(
        self,
        context: ReviewContext,
    ) -> bool:
        """Notify that a task is awaiting human approval.

        Args:
            context: Full review context for the TaskPacket.

        Returns:
            True if notification was delivered successfully.
        """

    @abstractmethod
    async def notify_approved(
        self,
        taskpacket_id: UUID,
        approved_by: str,
    ) -> bool:
        """Notify that a task was approved.

        Args:
            taskpacket_id: UUID of the approved TaskPacket.
            approved_by: Identifier of the approver.

        Returns:
            True if notification was delivered successfully.
        """

    @abstractmethod
    async def notify_rejected(
        self,
        taskpacket_id: UUID,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Notify that a task was rejected.

        Args:
            taskpacket_id: UUID of the rejected TaskPacket.
            rejected_by: Identifier of the rejector.
            reason: Rejection reason for audit trail.

        Returns:
            True if notification was delivered successfully.
        """

    @abstractmethod
    async def notify_timeout(
        self,
        taskpacket_id: UUID,
    ) -> bool:
        """Notify that an approval request timed out.

        Args:
            taskpacket_id: UUID of the timed-out TaskPacket.

        Returns:
            True if notification was delivered successfully.
        """
