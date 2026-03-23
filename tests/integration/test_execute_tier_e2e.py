"""Integration tests: end-to-end auto-merge with task-level trust tier (Epic 42, Story 42.6).

Tests the full publish() flow with mocked GitHub client, mocked DB, and mocked
safety bounds.  Covers:
- task_trust_tier=EXECUTE + repo=EXECUTE + all gates → auto_merge_enabled=True
- task_trust_tier=EXECUTE + repo=SUGGEST → ceiling enforced, no auto-merge
- Safety bound violation (loopback > max) → auto-merge blocked, marked_ready=True
- task_trust_tier=None → fallback to repo_tier
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.admin.merge_mode import MergeMode
from src.dashboard.models.trust_config import SafeBoundsRead
from src.models.taskpacket import TaskPacketStatus, TaskTrustTier
from src.publisher.publisher import publish
from src.repo.repo_profile import RepoTier
from src.verification.gate import VerificationResult

from datetime import datetime, UTC

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_safe_bounds(**overrides) -> SafeBoundsRead:
    defaults = dict(
        max_auto_merge_lines=1000,
        max_auto_merge_cost=100_000,
        max_loopbacks=5,
        mandatory_review_patterns=[],
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SafeBoundsRead(**defaults)


def _make_taskpacket(
    *,
    task_trust_tier: TaskTrustTier | None = TaskTrustTier.EXECUTE,
    loopback_count: int = 0,
    estimated_cost: int = 500,
    repo: str = "test-org/test-repo",
    scope: dict | None = None,
) -> MagicMock:
    """Build a minimal TaskPacketRow-like mock."""
    tp = MagicMock()
    tp.id = uuid4()
    tp.repo = repo
    tp.correlation_id = uuid4()
    tp.task_trust_tier = task_trust_tier
    tp.loopback_count = loopback_count
    tp.estimated_cost = estimated_cost
    tp.scope = scope or {"diff_lines": 100}
    tp.matched_rule_id = uuid4()
    tp.pr_number = None
    tp.pr_url = None
    tp.auto_merged = False
    return tp


def _make_intent() -> MagicMock:
    intent = MagicMock()
    intent.version = 1
    intent.goal = "Add a feature"
    return intent


def _make_github_client(*, pr_exists: bool = False) -> AsyncMock:
    """Return an AsyncMock GitHub client that fakes out all needed methods."""
    github = AsyncMock()
    if pr_exists:
        github.find_pr_by_head.return_value = {
            "number": 42,
            "html_url": "https://github.com/test-org/test-repo/pull/42",
        }
    else:
        github.find_pr_by_head.return_value = None
    github.get_default_branch.return_value = "main"
    github.get_branch_sha.return_value = "abc123"
    github.create_branch.return_value = None
    github.create_pull_request.return_value = {
        "number": 99,
        "html_url": "https://github.com/test-org/test-repo/pull/99",
    }
    github.add_comment.return_value = {"id": 1001}
    github.add_labels.return_value = None
    github.remove_label.return_value = None
    github.mark_ready_for_review.return_value = None
    github.enable_auto_merge.return_value = None
    # For evidence comment update path
    github._client = AsyncMock()
    github._client.get.return_value = AsyncMock(
        json=MagicMock(return_value=[]),
        raise_for_status=MagicMock(),
    )
    return github


def _make_verification(passed: bool = True) -> VerificationResult:
    return MagicMock(spec=VerificationResult, passed=passed)


# ---------------------------------------------------------------------------
# Shared patch targets
# ---------------------------------------------------------------------------

_PATCHES = {
    "get_by_id": "src.publisher.publisher.get_by_id",
    "get_latest": "src.publisher.publisher.get_latest_for_taskpacket",
    "update_status": "src.publisher.publisher.update_status",
    "get_merge_mode": "src.publisher.publisher.get_merge_mode",
    "get_safety_bounds": "src.publisher.publisher.get_safety_bounds",
    "format_evidence_comment": "src.publisher.publisher.format_evidence_comment",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_execute_tier_task_and_repo_enables_auto_merge() -> None:
    """task=EXECUTE + repo=EXECUTE + all gates → auto_merge_enabled=True."""
    taskpacket_id = uuid4()
    tp = _make_taskpacket(task_trust_tier=TaskTrustTier.EXECUTE)
    tp.id = taskpacket_id
    session = AsyncMock()
    session.get.return_value = tp  # for auto_merged flag write-back

    github = _make_github_client()
    verification = _make_verification(passed=True)
    bounds = _make_safe_bounds()

    with (
        patch(_PATCHES["get_by_id"], new=AsyncMock(return_value=tp)),
        patch(_PATCHES["get_latest"], new=AsyncMock(return_value=_make_intent())),
        patch(_PATCHES["update_status"], new=AsyncMock()),
        patch(_PATCHES["get_merge_mode"], return_value=MergeMode.AUTO_MERGE),
        patch(_PATCHES["get_safety_bounds"], new=AsyncMock(return_value=bounds)),
        patch(_PATCHES["format_evidence_comment"], return_value="# Evidence"),
    ):
        result = await publish(
            session=session,
            taskpacket_id=taskpacket_id,
            evidence=MagicMock(),
            verification=verification,
            github=github,
            repo_tier=RepoTier.EXECUTE,
            qa_passed=True,
            approval_received=True,
        )

    assert result.auto_merge_enabled is True
    assert result.marked_ready is True
    github.enable_auto_merge.assert_awaited_once()


async def test_ceiling_repo_suggest_blocks_auto_merge() -> None:
    """task=EXECUTE + repo=SUGGEST → ceiling enforces SUGGEST, no auto-merge."""
    taskpacket_id = uuid4()
    tp = _make_taskpacket(task_trust_tier=TaskTrustTier.EXECUTE)
    tp.id = taskpacket_id
    session = AsyncMock()
    session.get.return_value = tp

    github = _make_github_client()
    verification = _make_verification(passed=True)
    bounds = _make_safe_bounds()

    with (
        patch(_PATCHES["get_by_id"], new=AsyncMock(return_value=tp)),
        patch(_PATCHES["get_latest"], new=AsyncMock(return_value=_make_intent())),
        patch(_PATCHES["update_status"], new=AsyncMock()),
        patch(_PATCHES["get_merge_mode"], return_value=MergeMode.AUTO_MERGE),
        patch(_PATCHES["get_safety_bounds"], new=AsyncMock(return_value=bounds)),
        patch(_PATCHES["format_evidence_comment"], return_value="# Evidence"),
    ):
        result = await publish(
            session=session,
            taskpacket_id=taskpacket_id,
            evidence=MagicMock(),
            verification=verification,
            github=github,
            repo_tier=RepoTier.SUGGEST,  # SUGGEST ceiling
            qa_passed=True,
            approval_received=True,
        )

    assert result.auto_merge_enabled is False
    assert result.marked_ready is True  # SUGGEST still marks ready
    github.enable_auto_merge.assert_not_awaited()


async def test_safety_bound_loopback_blocks_auto_merge_not_mark_ready() -> None:
    """loopback_count > max_loopbacks → auto-merge blocked but PR still marked ready."""
    taskpacket_id = uuid4()
    tp = _make_taskpacket(task_trust_tier=TaskTrustTier.EXECUTE, loopback_count=10)
    tp.id = taskpacket_id
    session = AsyncMock()
    session.get.return_value = tp

    github = _make_github_client()
    verification = _make_verification(passed=True)
    bounds = _make_safe_bounds(max_loopbacks=3)

    with (
        patch(_PATCHES["get_by_id"], new=AsyncMock(return_value=tp)),
        patch(_PATCHES["get_latest"], new=AsyncMock(return_value=_make_intent())),
        patch(_PATCHES["update_status"], new=AsyncMock()),
        patch(_PATCHES["get_merge_mode"], return_value=MergeMode.AUTO_MERGE),
        patch(_PATCHES["get_safety_bounds"], new=AsyncMock(return_value=bounds)),
        patch(_PATCHES["format_evidence_comment"], return_value="# Evidence"),
    ):
        result = await publish(
            session=session,
            taskpacket_id=taskpacket_id,
            evidence=MagicMock(),
            verification=verification,
            github=github,
            repo_tier=RepoTier.EXECUTE,
            qa_passed=True,
            approval_received=True,
        )

    assert result.auto_merge_enabled is False  # safety bound blocked
    assert result.marked_ready is True  # still marked ready (SUGGEST behavior)
    github.enable_auto_merge.assert_not_awaited()


async def test_null_task_tier_falls_back_to_repo_tier_execute() -> None:
    """task_trust_tier=None → falls back to repo_tier=EXECUTE → auto-merge enabled."""
    taskpacket_id = uuid4()
    tp = _make_taskpacket(task_trust_tier=None)  # legacy packet
    tp.id = taskpacket_id
    session = AsyncMock()
    session.get.return_value = tp

    github = _make_github_client()
    verification = _make_verification(passed=True)
    bounds = _make_safe_bounds()

    with (
        patch(_PATCHES["get_by_id"], new=AsyncMock(return_value=tp)),
        patch(_PATCHES["get_latest"], new=AsyncMock(return_value=_make_intent())),
        patch(_PATCHES["update_status"], new=AsyncMock()),
        patch(_PATCHES["get_merge_mode"], return_value=MergeMode.AUTO_MERGE),
        patch(_PATCHES["get_safety_bounds"], new=AsyncMock(return_value=bounds)),
        patch(_PATCHES["format_evidence_comment"], return_value="# Evidence"),
    ):
        result = await publish(
            session=session,
            taskpacket_id=taskpacket_id,
            evidence=MagicMock(),
            verification=verification,
            github=github,
            repo_tier=RepoTier.EXECUTE,
            qa_passed=True,
            approval_received=True,
        )

    assert result.auto_merge_enabled is True


async def test_null_task_tier_falls_back_to_repo_tier_suggest() -> None:
    """task_trust_tier=None → falls back to repo_tier=SUGGEST → no auto-merge."""
    taskpacket_id = uuid4()
    tp = _make_taskpacket(task_trust_tier=None)
    tp.id = taskpacket_id
    session = AsyncMock()
    session.get.return_value = tp

    github = _make_github_client()
    verification = _make_verification(passed=True)
    bounds = _make_safe_bounds()

    with (
        patch(_PATCHES["get_by_id"], new=AsyncMock(return_value=tp)),
        patch(_PATCHES["get_latest"], new=AsyncMock(return_value=_make_intent())),
        patch(_PATCHES["update_status"], new=AsyncMock()),
        patch(_PATCHES["get_merge_mode"], return_value=MergeMode.AUTO_MERGE),
        patch(_PATCHES["get_safety_bounds"], new=AsyncMock(return_value=bounds)),
        patch(_PATCHES["format_evidence_comment"], return_value="# Evidence"),
    ):
        result = await publish(
            session=session,
            taskpacket_id=taskpacket_id,
            evidence=MagicMock(),
            verification=verification,
            github=github,
            repo_tier=RepoTier.SUGGEST,
            qa_passed=True,
            approval_received=True,
        )

    assert result.auto_merge_enabled is False
    assert result.marked_ready is True
