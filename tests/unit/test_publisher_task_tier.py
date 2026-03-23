"""Unit tests for Publisher task-level trust tier wiring (Epic 42, Story 42.5).

Tests cover:
(a) task_trust_tier=execute + repo Execute + all gates = auto-merge enabled
(b) task_trust_tier=execute + repo Suggest = no auto-merge (ceiling enforcement)
(c) task_trust_tier=None = fallback to repo_tier
(d) safety bound violation at publish time = auto-merge blocked, marked_ready=True
(e) dry_run rule = SUGGEST behavior with EXECUTE audit trail in EvaluationResult
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.admin.merge_mode import MergeMode
from src.dashboard.models.trust_config import AssignedTier, SafeBoundsRead
from src.dashboard.trust_engine import EvaluationResult, _cap_tier
from src.models.taskpacket import TaskTrustTier
from src.publisher.publisher import (
    _check_safety_bounds_at_publish,
    _compute_effective_tier,
    _should_enable_auto_merge,
    _should_mark_ready,
)
from src.repo.repo_profile import RepoTier

from datetime import datetime, UTC


# ---------------------------------------------------------------------------
# _compute_effective_tier (Story 42.1)
# ---------------------------------------------------------------------------


class TestComputeEffectiveTier:
    def test_task_execute_repo_execute_returns_execute(self) -> None:
        """Task EXECUTE + repo EXECUTE → effective EXECUTE."""
        result = _compute_effective_tier(RepoTier.EXECUTE, TaskTrustTier.EXECUTE)
        assert result == RepoTier.EXECUTE

    def test_task_execute_repo_suggest_returns_suggest(self) -> None:
        """Repo SUGGEST is the ceiling — task EXECUTE is downgraded."""
        result = _compute_effective_tier(RepoTier.SUGGEST, TaskTrustTier.EXECUTE)
        assert result == RepoTier.SUGGEST

    def test_task_observe_repo_execute_returns_observe(self) -> None:
        """Task OBSERVE is more restrictive than repo EXECUTE."""
        result = _compute_effective_tier(RepoTier.EXECUTE, TaskTrustTier.OBSERVE)
        assert result == RepoTier.OBSERVE

    def test_task_suggest_repo_execute_returns_suggest(self) -> None:
        result = _compute_effective_tier(RepoTier.EXECUTE, TaskTrustTier.SUGGEST)
        assert result == RepoTier.SUGGEST

    def test_task_none_falls_back_to_repo_tier(self) -> None:
        """When task_trust_tier is None, repo_tier is used unchanged."""
        result = _compute_effective_tier(RepoTier.EXECUTE, None)
        assert result == RepoTier.EXECUTE

    def test_task_none_observe_falls_back_to_observe(self) -> None:
        result = _compute_effective_tier(RepoTier.OBSERVE, None)
        assert result == RepoTier.OBSERVE

    def test_task_none_suggest_falls_back_to_suggest(self) -> None:
        result = _compute_effective_tier(RepoTier.SUGGEST, None)
        assert result == RepoTier.SUGGEST

    def test_same_tier_returns_same(self) -> None:
        for tier in [RepoTier.OBSERVE, RepoTier.SUGGEST, RepoTier.EXECUTE]:
            task_tier = TaskTrustTier(tier.value)
            result = _compute_effective_tier(tier, task_tier)
            assert result == tier


# ---------------------------------------------------------------------------
# Effective tier drives auto-merge decisions (Story 42.1)
# ---------------------------------------------------------------------------


class TestEffectiveTierAutoMergeBehavior:
    def test_effective_execute_enables_auto_merge(self) -> None:
        """task=EXECUTE, repo=EXECUTE → effective=EXECUTE → auto-merge allowed."""
        effective = _compute_effective_tier(RepoTier.EXECUTE, TaskTrustTier.EXECUTE)
        result = _should_enable_auto_merge(
            effective, True, True, MergeMode.AUTO_MERGE, True
        )
        assert result is True

    def test_ceiling_repo_suggest_blocks_auto_merge(self) -> None:
        """task=EXECUTE, repo=SUGGEST → effective=SUGGEST → no auto-merge."""
        effective = _compute_effective_tier(RepoTier.SUGGEST, TaskTrustTier.EXECUTE)
        result = _should_enable_auto_merge(
            effective, True, True, MergeMode.AUTO_MERGE, True
        )
        assert result is False

    def test_ceiling_repo_suggest_still_marks_ready(self) -> None:
        """Suggest behavior: PR marked ready-for-review even without auto-merge."""
        effective = _compute_effective_tier(RepoTier.SUGGEST, TaskTrustTier.EXECUTE)
        result = _should_mark_ready(effective, True, True, MergeMode.AUTO_MERGE)
        assert result is True

    def test_null_task_tier_fallback_execute_enables_auto_merge(self) -> None:
        """task=None falls back to repo_tier=EXECUTE → auto-merge allowed."""
        effective = _compute_effective_tier(RepoTier.EXECUTE, None)
        result = _should_enable_auto_merge(
            effective, True, True, MergeMode.AUTO_MERGE, True
        )
        assert result is True

    def test_null_task_tier_fallback_suggest_blocks_auto_merge(self) -> None:
        """task=None falls back to repo_tier=SUGGEST → no auto-merge."""
        effective = _compute_effective_tier(RepoTier.SUGGEST, None)
        result = _should_enable_auto_merge(
            effective, True, True, MergeMode.AUTO_MERGE, True
        )
        assert result is False


# ---------------------------------------------------------------------------
# Safety bounds re-check at publish time (Story 42.2)
# ---------------------------------------------------------------------------


def _make_bounds(**overrides) -> SafeBoundsRead:
    """Factory for SafeBoundsRead with permissive defaults."""
    defaults = dict(
        max_auto_merge_lines=500,
        max_auto_merge_cost=10_000,
        max_loopbacks=3,
        mandatory_review_patterns=[],
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SafeBoundsRead(**defaults)


def _make_packet(**overrides) -> MagicMock:
    """Factory for a minimal TaskPacketRow mock."""
    packet = MagicMock()
    packet.loopback_count = 0
    packet.estimated_cost = 100
    packet.scope = {"diff_lines": 50}
    packet.repo = "org/repo"
    for k, v in overrides.items():
        setattr(packet, k, v)
    return packet


@pytest.mark.asyncio
async def test_safety_bounds_pass_when_within_limits() -> None:
    """All metrics within limits → safe=True, empty reasons."""
    session = AsyncMock()
    packet = _make_packet()
    bounds = _make_bounds()

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is True
    assert reasons == []


@pytest.mark.asyncio
async def test_safety_bounds_loopback_violation_blocks() -> None:
    """loopback_count > max_loopbacks → safe=False."""
    session = AsyncMock()
    packet = _make_packet(loopback_count=10)
    bounds = _make_bounds(max_loopbacks=3)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is False
    assert any("loopback_count=10" in r for r in reasons)


@pytest.mark.asyncio
async def test_safety_bounds_cost_violation_blocks() -> None:
    """estimated_cost > max_auto_merge_cost → safe=False."""
    session = AsyncMock()
    packet = _make_packet(estimated_cost=50_000)
    bounds = _make_bounds(max_auto_merge_cost=10_000)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is False
    assert any("estimated_cost=50000" in r for r in reasons)


@pytest.mark.asyncio
async def test_safety_bounds_diff_lines_violation_blocks() -> None:
    """diff_lines > max_auto_merge_lines → safe=False."""
    session = AsyncMock()
    packet = _make_packet(scope={"diff_lines": 1000})
    bounds = _make_bounds(max_auto_merge_lines=500)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is False
    assert any("diff_lines=1000" in r for r in reasons)


@pytest.mark.asyncio
async def test_safety_bounds_mandatory_review_pattern_blocks() -> None:
    """Repo matching mandatory_review_patterns → safe=False."""
    session = AsyncMock()
    packet = _make_packet(repo="org/critical-repo")
    bounds = _make_bounds(mandatory_review_patterns=["org/critical-*"])

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is False
    assert any("mandatory-review" in r for r in reasons)


@pytest.mark.asyncio
async def test_safety_bounds_none_limits_always_pass() -> None:
    """None limits → no check performed → safe=True even with high values."""
    session = AsyncMock()
    packet = _make_packet(loopback_count=9999, estimated_cost=9_999_999)
    bounds = _make_bounds(
        max_loopbacks=None,
        max_auto_merge_cost=None,
        max_auto_merge_lines=None,
    )

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "src.publisher.publisher.get_safety_bounds",
            AsyncMock(return_value=bounds),
        )
        safe, reasons = await _check_safety_bounds_at_publish(
            session, packet, uuid4()
        )

    assert safe is True
    assert reasons == []


# ---------------------------------------------------------------------------
# Dry-run EvaluationResult (Story 42.4 / AC6)
# ---------------------------------------------------------------------------


class TestDryRunEvaluationResult:
    def test_dry_run_result_has_dry_run_true(self) -> None:
        """EvaluationResult with dry_run=True records the flag."""
        result = EvaluationResult(
            AssignedTier.SUGGEST,
            raw_tier=AssignedTier.EXECUTE,
            matched_rule_id=uuid4(),
            dry_run=True,
            reason="dry_run active — effective tier downgraded to SUGGEST",
        )
        assert result.dry_run is True
        assert result.tier == AssignedTier.SUGGEST
        assert result.raw_tier == AssignedTier.EXECUTE

    def test_dry_run_result_defaults_false(self) -> None:
        """EvaluationResult defaults to dry_run=False."""
        result = EvaluationResult(AssignedTier.EXECUTE)
        assert result.dry_run is False

    def test_repr_includes_dry_run(self) -> None:
        result = EvaluationResult(AssignedTier.SUGGEST, dry_run=True)
        assert "dry_run=True" in repr(result)


# ---------------------------------------------------------------------------
# _cap_tier helper (used by _compute_effective_tier)
# ---------------------------------------------------------------------------


class TestCapTier:
    def test_observe_cap_observe_stays_observe(self) -> None:
        assert _cap_tier(AssignedTier.OBSERVE, AssignedTier.OBSERVE) == AssignedTier.OBSERVE

    def test_execute_capped_by_suggest(self) -> None:
        assert _cap_tier(AssignedTier.EXECUTE, AssignedTier.SUGGEST) == AssignedTier.SUGGEST

    def test_suggest_capped_by_observe(self) -> None:
        assert _cap_tier(AssignedTier.SUGGEST, AssignedTier.OBSERVE) == AssignedTier.OBSERVE

    def test_observe_not_raised_by_execute_ceiling(self) -> None:
        assert _cap_tier(AssignedTier.OBSERVE, AssignedTier.EXECUTE) == AssignedTier.OBSERVE
