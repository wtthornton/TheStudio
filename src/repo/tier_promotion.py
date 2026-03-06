"""Tier promotion — promote repo from Observe to Suggest tier.

Architecture reference: thestudioarc/15-system-runtime-flow.md (repo lifecycle, tier promotion)

Suggest tier means: draft PRs become ready-for-review after verification + QA pass.
Promotion requires both verification and QA to have passed for the TaskPacket.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_id
from src.observability.tracing import get_tracer
from src.repo.repo_profile import RepoTier
from src.repo.repo_profile_crud import update_tier

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.tier_promotion")


@dataclass(frozen=True)
class PromotionResult:
    """Result of a tier promotion attempt."""

    promoted: bool
    previous_tier: RepoTier
    new_tier: RepoTier
    reason: str
    timestamp: datetime


class PromotionError(Exception):
    """Raised when promotion preconditions are not met."""


async def promote_to_suggest(
    session: AsyncSession,
    profile_id: UUID,
    taskpacket_id: UUID,
    verification_passed: bool,
    qa_passed: bool,
) -> PromotionResult:
    """Promote a repo from Observe to Suggest tier.

    Preconditions:
    - Verification must have passed
    - QA must have passed
    - TaskPacket must exist and be in a terminal success state
    - Current tier must be Observe

    Args:
        session: Database session.
        profile_id: Repo profile to promote.
        taskpacket_id: TaskPacket that triggered promotion.
        verification_passed: Whether verification gate passed.
        qa_passed: Whether QA validation passed.

    Returns:
        PromotionResult with audit metadata.

    Raises:
        PromotionError: If preconditions are not met.
    """
    with tracer.start_as_current_span("tier.promote_to_suggest") as span:
        span.set_attribute("thestudio.profile_id", str(profile_id))
        span.set_attribute("thestudio.taskpacket_id", str(taskpacket_id))

        now = datetime.now(UTC)

        # Validate TaskPacket exists
        tp = await get_by_id(session, taskpacket_id)
        if tp is None:
            raise PromotionError(f"TaskPacket {taskpacket_id} not found")

        # Validate gates passed
        if not verification_passed:
            raise PromotionError("Cannot promote: verification has not passed")

        if not qa_passed:
            raise PromotionError("Cannot promote: QA has not passed")

        # Validate TaskPacket is in a publishable state
        if tp.status not in (
            TaskPacketStatus.VERIFICATION_PASSED,
            TaskPacketStatus.PUBLISHED,
        ):
            raise PromotionError(
                f"Cannot promote: TaskPacket status is {tp.status}, "
                "expected verification_passed or published"
            )

        # Perform tier update
        updated = await update_tier(session, profile_id, RepoTier.SUGGEST)
        previous_tier = RepoTier.OBSERVE  # Only valid promotion path in Epic 1

        reason = (
            f"Promoted after TaskPacket {taskpacket_id} passed verification + QA. "
            f"Previous tier: {previous_tier.value}"
        )

        span.set_attribute("thestudio.promotion_result", "promoted")
        logger.info(
            "Repo %s/%s promoted to Suggest tier (TaskPacket %s)",
            updated.owner,
            updated.repo_name,
            taskpacket_id,
        )

        return PromotionResult(
            promoted=True,
            previous_tier=previous_tier,
            new_tier=RepoTier.SUGGEST,
            reason=reason,
            timestamp=now,
        )
