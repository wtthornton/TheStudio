"""Rule health tracking and auto-deactivation for Execute-tier trust rules.

When an auto-merged PR is reverted, this module:
1. Updates the matched rule's merge_count / revert_count.
2. Checks if the rule's success rate has dropped below the configured threshold
   (default 90%) with a minimum sample size of 20 auto-merges.
3. If the threshold is breached, sets ``active = False`` and records a
   human-readable ``deactivation_reason``.
4. Generates a dashboard notification so the operator is aware.

The threshold and minimum sample size are intentionally conservative:
- Minimum 20 samples prevents false positives on low-traffic rules.
- 90% success rate gives a 1-in-10 tolerance for reverts — beyond this,
  the rule is deactivated to prevent further automated damage.

Epic 42 Story 42.11.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.models.trust_config import TrustTierRuleRow

logger = logging.getLogger(__name__)

# Thresholds — configurable via environment for testing
_DEFAULT_MIN_SAMPLES = 20
_DEFAULT_SUCCESS_RATE_THRESHOLD = 0.90  # 90%


async def update_rule_success_metrics(
    session: AsyncSession,
    rule_id: UUID,
    outcome: str,
    taskpacket_id: UUID,
    *,
    min_samples: int = _DEFAULT_MIN_SAMPLES,
    success_rate_threshold: float = _DEFAULT_SUCCESS_RATE_THRESHOLD,
) -> dict[str, Any]:
    """Update success metrics for a trust-tier rule and trigger deactivation if needed.

    Called by ``monitor_post_merge_activity`` after each merge outcome is
    determined.  Operates within the caller's transaction — the caller must
    ``commit()`` after this returns.

    Args:
        session: Active async DB session.
        rule_id: UUID of the matched trust-tier rule.
        outcome: "succeeded" | "reverted" | "issue_detected"
        taskpacket_id: UUID of the TaskPacket (for logging).
        min_samples: Minimum auto-merges before the threshold activates.
        success_rate_threshold: Float 0-1; deactivate when rate < threshold.

    Returns:
        Dict with keys: merge_count, revert_count, success_rate,
        deactivated (bool), deactivation_reason (str | None).
    """
    row = await session.get(TrustTierRuleRow, rule_id)
    if row is None:
        logger.warning(
            "rule_health.rule_not_found rule_id=%s taskpacket_id=%s",
            rule_id,
            taskpacket_id,
        )
        return {
            "merge_count": 0,
            "revert_count": 0,
            "success_rate": None,
            "deactivated": False,
            "deactivation_reason": None,
        }

    # Update counters
    if outcome == "reverted":
        row.revert_count = (getattr(row, "revert_count", 0) or 0) + 1
        row.merge_count = (getattr(row, "merge_count", 0) or 0) + 1
    elif outcome == "succeeded":
        row.merge_count = (getattr(row, "merge_count", 0) or 0) + 1
    # issue_detected does not increment merge_count (PR is not necessarily reverted)

    row.updated_at = datetime.now(tz=UTC)

    merge_count: int = getattr(row, "merge_count", 0) or 0
    revert_count: int = getattr(row, "revert_count", 0) or 0
    success_rate: float | None = None
    deactivated = False
    deactivation_reason: str | None = None

    # Only evaluate threshold when minimum samples are met
    if merge_count >= min_samples:
        success_rate = (merge_count - revert_count) / merge_count
        threshold_pct = int(success_rate_threshold * 100)
        rate_pct = round(success_rate * 100, 1)

        logger.info(
            "rule_health.check rule_id=%s merge_count=%d revert_count=%d "
            "success_rate=%.1f%% threshold=%d%%",
            rule_id,
            merge_count,
            revert_count,
            rate_pct,
            threshold_pct,
        )

        if success_rate < success_rate_threshold and row.active:
            # Deactivate the rule
            row.active = False
            reason = (
                f"auto: success rate {rate_pct}% below threshold {threshold_pct}% "
                f"({merge_count - revert_count}/{merge_count} merges succeeded)"
            )
            row.deactivation_reason = reason
            deactivated = True
            deactivation_reason = reason

            logger.warning(
                "rule_health.rule_deactivated rule_id=%s reason=%r",
                rule_id,
                reason,
            )

            # Generate a dashboard notification
            await _notify_rule_deactivated(session, rule_id, reason)
    else:
        logger.debug(
            "rule_health.insufficient_samples rule_id=%s merge_count=%d min=%d",
            rule_id,
            merge_count,
            min_samples,
        )

    await session.flush()

    return {
        "merge_count": merge_count,
        "revert_count": revert_count,
        "success_rate": success_rate,
        "deactivated": deactivated,
        "deactivation_reason": deactivation_reason,
    }


def compute_success_rate(merge_count: int, revert_count: int) -> float | None:
    """Compute success rate as a float (0-1), or None when merge_count is 0.

    Used by the dashboard API to display per-rule health metrics.
    """
    if merge_count == 0:
        return None
    return (merge_count - revert_count) / merge_count


async def get_rule_health_summary(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Return a summary of rule health for all Execute-tier trust rules.

    Used by the dashboard API endpoint ``GET /auto-merge/rule-health``.
    Returns a list of dicts, one per Execute-tier rule, with:
    - rule_id, priority, description, active, dry_run
    - merge_count, revert_count, success_rate (float | None)
    - deactivation_reason (str | None)
    - sample_warning: True when merge_count < 20 (insufficient data)

    Epic 42 Story 42.12.
    """
    stmt = select(TrustTierRuleRow).where(
        TrustTierRuleRow.assigned_tier == "execute"
    ).order_by(TrustTierRuleRow.priority.asc())
    result = await session.execute(stmt)
    rows = result.scalars().all()

    summary = []
    for row in rows:
        merge_count: int = getattr(row, "merge_count", 0) or 0
        revert_count: int = getattr(row, "revert_count", 0) or 0
        success_rate = compute_success_rate(merge_count, revert_count)
        summary.append({
            "rule_id": str(row.id),
            "priority": row.priority,
            "description": row.description,
            "active": row.active,
            "dry_run": getattr(row, "dry_run", False),
            "merge_count": merge_count,
            "revert_count": revert_count,
            "success_rate": round(success_rate * 100, 1) if success_rate is not None else None,
            "deactivation_reason": getattr(row, "deactivation_reason", None),
            "sample_warning": merge_count < _DEFAULT_MIN_SAMPLES,
        })

    return summary


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _notify_rule_deactivated(
    session: AsyncSession,
    rule_id: UUID,
    reason: str,
) -> None:
    """Generate a dashboard notification when a rule is auto-deactivated."""
    try:
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.dashboard.models.notification import NotificationRow, NotificationType

        notification = NotificationRow(
            id=uuid4(),
            type=NotificationType.TRUST_TIER_ASSIGNED,
            title="Trust-Tier Rule Auto-Deactivated",
            message=(
                f"Rule {rule_id} was automatically deactivated. "
                f"Reason: {reason}. "
                "Review the rule in the Trust Configuration dashboard before re-activating."
            ),
            task_id=None,
            read=False,
            created_at=datetime.now(tz=UTC),
        )
        session.add(notification)
        await session.flush()

        logger.info(
            "rule_health.notification_created rule_id=%s", rule_id
        )
    except Exception:
        logger.warning(
            "rule_health.notification_failed rule_id=%s",
            rule_id,
            exc_info=True,
        )
