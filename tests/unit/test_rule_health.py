"""Unit tests for rule health tracking and auto-deactivation (Epic 42 Story 42.13).

Covers:
(d) Rule auto-deactivation at threshold
(e) Rule stays active at exactly threshold (90%)
(f) Insufficient samples warning
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.dashboard.rule_health import (
    _DEFAULT_SUCCESS_RATE_THRESHOLD,
    compute_success_rate,
    update_rule_success_metrics,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule_row(
    rule_id: UUID | None = None,
    merge_count: int = 0,
    revert_count: int = 0,
    active: bool = True,
    assigned_tier: str = "execute",
) -> MagicMock:
    """Return a mock TrustTierRuleRow with the given metrics."""
    from src.dashboard.models.trust_config import TrustTierRuleRow

    row = MagicMock(spec=TrustTierRuleRow)
    row.id = rule_id or uuid4()
    row.merge_count = merge_count
    row.revert_count = revert_count
    row.active = active
    row.assigned_tier = assigned_tier
    row.deactivation_reason = None
    row.updated_at = datetime.now(UTC)
    return row


def _make_session(rule_row: Any) -> AsyncMock:
    """Return a mock AsyncSession that returns the given rule_row on get()."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=rule_row)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# compute_success_rate
# ---------------------------------------------------------------------------


def test_compute_success_rate_zero_merges():
    """Returns None when there are no merges (avoids division by zero)."""
    assert compute_success_rate(0, 0) is None


def test_compute_success_rate_all_success():
    """100% success rate when no reverts."""
    assert compute_success_rate(20, 0) == 1.0


def test_compute_success_rate_mixed():
    """18/20 = 90% success rate."""
    rate = compute_success_rate(20, 2)
    assert abs(rate - 0.90) < 1e-9


def test_compute_success_rate_below_threshold():
    """18/21 ≈ 85.7% — below the 90% threshold."""
    rate = compute_success_rate(21, 3)
    assert rate is not None
    assert rate < _DEFAULT_SUCCESS_RATE_THRESHOLD


# ---------------------------------------------------------------------------
# update_rule_success_metrics — below sample threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_no_deactivation_below_min_samples():
    """Rule stays active when merge_count < 20 regardless of revert rate."""
    rule_id = uuid4()
    row = _make_rule_row(rule_id, merge_count=5, revert_count=4, active=True)
    session = _make_session(row)

    result = await update_rule_success_metrics(
        session, rule_id, "reverted", uuid4(), min_samples=20
    )

    assert result["deactivated"] is False
    assert row.active is True  # unchanged


@pytest.mark.asyncio
async def test_update_increments_merge_count_on_success():
    """merge_count is incremented on 'succeeded' outcome."""
    rule_id = uuid4()
    row = _make_rule_row(rule_id, merge_count=10, revert_count=0)
    session = _make_session(row)

    await update_rule_success_metrics(session, rule_id, "succeeded", uuid4())

    assert row.merge_count == 11
    assert row.revert_count == 0


@pytest.mark.asyncio
async def test_update_increments_both_counts_on_revert():
    """Both merge_count and revert_count are incremented on 'reverted' outcome."""
    rule_id = uuid4()
    row = _make_rule_row(rule_id, merge_count=10, revert_count=1)
    session = _make_session(row)

    await update_rule_success_metrics(session, rule_id, "reverted", uuid4())

    assert row.merge_count == 11
    assert row.revert_count == 2


# ---------------------------------------------------------------------------
# update_rule_success_metrics — threshold evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_stays_active_at_exactly_threshold():
    """Rule stays active when success rate is exactly 90% (18/20).

    AC4: threshold is strict — exactly at threshold means active stays True.
    """
    rule_id = uuid4()
    # After this success, merge_count=20, revert_count=2 → 18/20 = 90% exactly
    row = _make_rule_row(rule_id, merge_count=19, revert_count=2, active=True)
    session = _make_session(row)

    result = await update_rule_success_metrics(
        session,
        rule_id,
        "succeeded",
        uuid4(),
        min_samples=20,
        success_rate_threshold=0.90,
    )

    # merge_count becomes 20, revert_count stays 2 → 90% exactly → stays active
    assert result["deactivated"] is False
    assert row.active is True


@pytest.mark.asyncio
async def test_rule_deactivated_below_threshold():
    """Rule is deactivated when success rate drops below 90% with >= 20 samples.

    AC4: Process 21 outcomes (18 success, 3 reverts = 85.7%) → rule deactivated.
    """
    rule_id = uuid4()
    # Currently at 20 merges, 2 reverts (90% = threshold, stays active).
    # Trigger one more revert to push to 21 merges, 3 reverts (85.7%).
    row = _make_rule_row(rule_id, merge_count=20, revert_count=2, active=True)
    session = _make_session(row)

    # Patch the notification to avoid DB dependency
    with patch(
        "src.dashboard.rule_health._notify_rule_deactivated",
        new_callable=AsyncMock,
    ):
        result = await update_rule_success_metrics(
            session,
            rule_id,
            "reverted",
            uuid4(),
            min_samples=20,
            success_rate_threshold=0.90,
        )

    assert result["deactivated"] is True
    assert row.active is False
    assert row.deactivation_reason is not None
    assert "85.7" in row.deactivation_reason or "auto:" in row.deactivation_reason


@pytest.mark.asyncio
async def test_rule_not_deactivated_twice():
    """Auto-deactivation only runs once — already-inactive rule is not modified."""
    rule_id = uuid4()
    row = _make_rule_row(
        rule_id,
        merge_count=20,
        revert_count=5,
        active=False,  # Already deactivated
    )
    row.deactivation_reason = "auto: already deactivated"
    session = _make_session(row)

    with patch(
        "src.dashboard.rule_health._notify_rule_deactivated",
        new_callable=AsyncMock,
    ) as mock_notify:
        result = await update_rule_success_metrics(
            session, rule_id, "reverted", uuid4()
        )

    # Notification should NOT be sent again
    mock_notify.assert_not_called()
    assert result["deactivated"] is False


@pytest.mark.asyncio
async def test_rule_not_found_returns_safe_defaults():
    """Missing rule returns safe defaults without raising."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)  # Rule not found

    result = await update_rule_success_metrics(
        session, uuid4(), "reverted", uuid4()
    )

    assert result["deactivated"] is False
    assert result["merge_count"] == 0


# ---------------------------------------------------------------------------
# get_rule_health_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rule_health_summary_returns_execute_rules():
    """Health summary includes only Execute-tier rules with correct metrics."""
    from src.dashboard.models.trust_config import TrustTierRuleRow
    from src.dashboard.rule_health import get_rule_health_summary

    row1 = MagicMock(spec=TrustTierRuleRow)
    row1.id = uuid4()
    row1.priority = 10
    row1.description = "Execute safe tasks"
    row1.active = True
    row1.assigned_tier = "execute"
    row1.merge_count = 25
    row1.revert_count = 1
    row1.deactivation_reason = None
    row1.dry_run = False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    summary = await get_rule_health_summary(session)

    assert len(summary) == 1
    assert summary[0]["rule_id"] == str(row1.id)
    assert summary[0]["merge_count"] == 25
    assert summary[0]["revert_count"] == 1
    # (25 - 1) / 25 = 0.96 → 96.0%
    assert abs(summary[0]["success_rate"] - 96.0) < 0.1
    assert summary[0]["sample_warning"] is False  # 25 >= 20


@pytest.mark.asyncio
async def test_get_rule_health_summary_sample_warning_for_low_count():
    """Sample warning is True when merge_count < 20."""
    from src.dashboard.models.trust_config import TrustTierRuleRow
    from src.dashboard.rule_health import get_rule_health_summary

    row = MagicMock(spec=TrustTierRuleRow)
    row.id = uuid4()
    row.priority = 5
    row.description = "New rule"
    row.active = True
    row.assigned_tier = "execute"
    row.merge_count = 3
    row.revert_count = 0
    row.deactivation_reason = None
    row.dry_run = False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    summary = await get_rule_health_summary(session)

    assert summary[0]["sample_warning"] is True
    assert summary[0]["success_rate"] is not None  # Still computed even with low count


@pytest.mark.asyncio
async def test_get_rule_health_summary_zero_merges():
    """success_rate is None when merge_count is 0."""
    from src.dashboard.models.trust_config import TrustTierRuleRow
    from src.dashboard.rule_health import get_rule_health_summary

    row = MagicMock(spec=TrustTierRuleRow)
    row.id = uuid4()
    row.priority = 1
    row.description = "Unused rule"
    row.active = True
    row.assigned_tier = "execute"
    row.merge_count = 0
    row.revert_count = 0
    row.deactivation_reason = None
    row.dry_run = False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    summary = await get_rule_health_summary(session)

    assert summary[0]["success_rate"] is None
    assert summary[0]["sample_warning"] is True
