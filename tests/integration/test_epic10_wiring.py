"""Integration tests for Epic 10 wiring — merge_mode in publisher, record_timing in workflow.

Sprint 2: Verify that the integration points are connected end-to-end.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.admin.merge_mode import MergeMode, set_merge_mode
from src.admin.merge_mode import clear as clear_merge
from src.admin.operational_targets import (
    OperationalTargetsService,
    clear_timing_events,
)
from src.publisher.publisher import _should_mark_ready
from src.repo.repo_profile import RepoTier


@pytest.fixture(autouse=True)
def _reset():
    clear_merge()
    clear_timing_events()
    yield
    clear_merge()
    clear_timing_events()


class TestMergeModeInPublisher:
    """Verify publisher reads get_merge_mode() and applies it."""

    def test_draft_only_never_marks_ready(self):
        assert _should_mark_ready(
            RepoTier.SUGGEST, True, True, MergeMode.DRAFT_ONLY
        ) is False

    def test_require_review_marks_ready_in_suggest(self):
        assert _should_mark_ready(
            RepoTier.SUGGEST, True, True, MergeMode.REQUIRE_REVIEW
        ) is True

    def test_require_review_not_ready_in_observe(self):
        assert _should_mark_ready(
            RepoTier.OBSERVE, True, True, MergeMode.REQUIRE_REVIEW
        ) is False

    def test_auto_merge_marks_ready_in_suggest(self):
        assert _should_mark_ready(
            RepoTier.SUGGEST, True, True, MergeMode.AUTO_MERGE
        ) is True

    def test_require_review_not_ready_without_qa(self):
        assert _should_mark_ready(
            RepoTier.SUGGEST, True, False, MergeMode.REQUIRE_REVIEW
        ) is False

    def test_default_merge_mode_preserves_legacy_behavior(self):
        """Without merge_mode arg, _should_mark_ready uses tier-only logic."""
        assert _should_mark_ready(RepoTier.SUGGEST, True, True) is True
        assert _should_mark_ready(RepoTier.OBSERVE, True, True) is False

    @pytest.mark.asyncio
    async def test_publish_reads_merge_mode(self):
        """Full publish() reads get_merge_mode() for the repo."""
        from src.publisher.publisher import publish

        tp_id = uuid4()
        mock_session = AsyncMock()
        mock_github = AsyncMock()

        # Mock TaskPacket
        mock_tp = MagicMock()
        mock_tp.repo = "owner/repo"
        mock_tp.correlation_id = uuid4()

        # Mock intent
        mock_intent = MagicMock()
        mock_intent.version = 1
        mock_intent.goal = "Test goal"

        # Mock verification
        mock_verification = MagicMock()
        mock_verification.passed = True

        # Mock evidence
        mock_evidence = MagicMock()

        # No existing PR — will create new one
        mock_github.find_pr_by_head = AsyncMock(return_value=None)
        mock_github.get_default_branch = AsyncMock(return_value="main")
        mock_github.get_branch_sha = AsyncMock(return_value="abc123")
        mock_github.create_branch = AsyncMock()
        mock_github.create_pull_request = AsyncMock(return_value={
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        })
        mock_github.add_comment = AsyncMock(return_value={"id": 100})
        mock_github.add_labels = AsyncMock()
        mock_github.remove_label = AsyncMock()
        mock_github.mark_ready_for_review = AsyncMock()

        # Set merge mode to REQUIRE_REVIEW
        set_merge_mode("owner/repo", MergeMode.REQUIRE_REVIEW)

        with (
            patch("src.publisher.publisher.get_by_id", AsyncMock(return_value=mock_tp)),
            patch(
                "src.publisher.publisher.get_latest_for_taskpacket",
                AsyncMock(return_value=mock_intent),
            ),
            patch("src.publisher.publisher.update_status", AsyncMock()),
            patch("src.publisher.publisher.format_evidence_comment", return_value="evidence"),
        ):
            result = await publish(
                session=mock_session,
                taskpacket_id=tp_id,
                evidence=mock_evidence,
                verification=mock_verification,
                github=mock_github,
                repo_tier=RepoTier.SUGGEST,
                qa_passed=True,
            )

        # With REQUIRE_REVIEW + Suggest + V+QA passed → should mark ready
        assert result.marked_ready is True
        mock_github.mark_ready_for_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_draft_only_blocks_ready(self):
        """Publish with DRAFT_ONLY merge mode does NOT mark ready."""
        from src.publisher.publisher import publish

        tp_id = uuid4()
        mock_session = AsyncMock()
        mock_github = AsyncMock()

        mock_tp = MagicMock()
        mock_tp.repo = "owner/repo"
        mock_tp.correlation_id = uuid4()

        mock_intent = MagicMock()
        mock_intent.version = 1
        mock_intent.goal = "Test goal"

        mock_verification = MagicMock()
        mock_verification.passed = True

        mock_github.find_pr_by_head = AsyncMock(return_value=None)
        mock_github.get_default_branch = AsyncMock(return_value="main")
        mock_github.get_branch_sha = AsyncMock(return_value="abc123")
        mock_github.create_branch = AsyncMock()
        mock_github.create_pull_request = AsyncMock(return_value={
            "number": 43,
            "html_url": "https://github.com/owner/repo/pull/43",
        })
        mock_github.add_comment = AsyncMock(return_value={"id": 101})
        mock_github.add_labels = AsyncMock()
        mock_github.remove_label = AsyncMock()
        mock_github.mark_ready_for_review = AsyncMock()

        # DRAFT_ONLY (default)
        clear_merge()

        with (
            patch("src.publisher.publisher.get_by_id", AsyncMock(return_value=mock_tp)),
            patch(
                "src.publisher.publisher.get_latest_for_taskpacket",
                AsyncMock(return_value=mock_intent),
            ),
            patch("src.publisher.publisher.update_status", AsyncMock()),
            patch("src.publisher.publisher.format_evidence_comment", return_value="evidence"),
        ):
            result = await publish(
                session=mock_session,
                taskpacket_id=tp_id,
                evidence=MagicMock(),
                verification=mock_verification,
                github=mock_github,
                repo_tier=RepoTier.SUGGEST,
                qa_passed=True,
            )

        assert result.marked_ready is False
        mock_github.mark_ready_for_review.assert_not_called()


class TestRecordTimingInWorkflow:
    """Verify publish_activity calls record_timing."""

    @pytest.mark.asyncio
    async def test_publish_activity_records_timing(self):
        from src.workflow.activities import PublishInput, publish_activity

        params = PublishInput(
            taskpacket_id="tp-123",
            repo_tier="suggest",
            qa_passed=True,
        )
        await publish_activity(params)

        svc = OperationalTargetsService()
        lead_times = svc._get_lead_times(None, 28)
        assert len(lead_times) >= 1

    @pytest.mark.asyncio
    async def test_publish_activity_records_merge_ready_when_qa_passed(self):
        from src.workflow.activities import PublishInput, publish_activity

        params = PublishInput(
            taskpacket_id="tp-456",
            repo_tier="suggest",
            qa_passed=True,
        )
        await publish_activity(params)

        svc = OperationalTargetsService()
        cycle_times = svc._get_cycle_times(None, 28)
        # With qa_passed=True, merge_ready_at is set → cycle time computed
        assert len(cycle_times) >= 1

    @pytest.mark.asyncio
    async def test_publish_activity_no_merge_ready_without_qa(self):
        from src.workflow.activities import PublishInput, publish_activity

        params = PublishInput(
            taskpacket_id="tp-789",
            repo_tier="observe",
            qa_passed=False,
        )
        await publish_activity(params)

        svc = OperationalTargetsService()
        cycle_times = svc._get_cycle_times(None, 28)
        # Without qa_passed, merge_ready_at is None → no cycle time
        assert len(cycle_times) == 0
