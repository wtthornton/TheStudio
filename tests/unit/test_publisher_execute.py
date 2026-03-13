"""Unit tests for Execute tier Publisher behavior (Epic 22).

Tests _should_mark_ready() with Execute tier, _should_enable_auto_merge(),
_try_enable_auto_merge(), tier label reconciliation, and PublishResult fields.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.admin.merge_mode import MergeMode
from src.publisher.publisher import (
    LABEL_TIER_EXECUTE,
    LABEL_TIER_OBSERVE,
    LABEL_TIER_SUGGEST,
    TIER_LABELS,
    PublishResult,
    _should_enable_auto_merge,
    _should_mark_ready,
    _try_enable_auto_merge,
)
from src.repo.repo_profile import RepoTier


# --- _should_mark_ready with Execute tier ---


class TestShouldMarkReadyExecute:
    def test_execute_with_auto_merge_marks_ready(self) -> None:
        assert _should_mark_ready(
            RepoTier.EXECUTE, True, True, MergeMode.AUTO_MERGE
        ) is True

    def test_execute_with_require_review_marks_ready(self) -> None:
        assert _should_mark_ready(
            RepoTier.EXECUTE, True, True, MergeMode.REQUIRE_REVIEW
        ) is True

    def test_execute_with_draft_only_stays_draft(self) -> None:
        assert _should_mark_ready(
            RepoTier.EXECUTE, True, True, MergeMode.DRAFT_ONLY
        ) is False

    def test_execute_without_qa_stays_draft(self) -> None:
        assert _should_mark_ready(
            RepoTier.EXECUTE, True, False, MergeMode.AUTO_MERGE
        ) is False

    def test_execute_without_verification_stays_draft(self) -> None:
        assert _should_mark_ready(
            RepoTier.EXECUTE, False, True, MergeMode.AUTO_MERGE
        ) is False

    def test_observe_still_stays_draft(self) -> None:
        assert _should_mark_ready(
            RepoTier.OBSERVE, True, True, MergeMode.AUTO_MERGE
        ) is False

    def test_suggest_still_marks_ready(self) -> None:
        assert _should_mark_ready(
            RepoTier.SUGGEST, True, True, MergeMode.AUTO_MERGE
        ) is True


# --- _should_enable_auto_merge ---


class TestShouldEnableAutoMerge:
    def test_all_conditions_met(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, True, MergeMode.AUTO_MERGE, True
        ) is True

    def test_missing_approval(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, True, MergeMode.AUTO_MERGE, False
        ) is False

    def test_wrong_merge_mode(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, True, MergeMode.REQUIRE_REVIEW, True
        ) is False

    def test_wrong_tier_suggest(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.SUGGEST, True, True, MergeMode.AUTO_MERGE, True
        ) is False

    def test_wrong_tier_observe(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.OBSERVE, True, True, MergeMode.AUTO_MERGE, True
        ) is False

    def test_verification_failed(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, False, True, MergeMode.AUTO_MERGE, True
        ) is False

    def test_qa_failed(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, False, MergeMode.AUTO_MERGE, True
        ) is False

    def test_draft_only_mode(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, True, MergeMode.DRAFT_ONLY, True
        ) is False

    def test_no_merge_mode(self) -> None:
        assert _should_enable_auto_merge(
            RepoTier.EXECUTE, True, True, None, True
        ) is False


# --- _try_enable_auto_merge ---


class TestTryEnableAutoMerge:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        mock_github = AsyncMock()
        result = await _try_enable_auto_merge(
            mock_github, "acme", "widgets", 99, "squash"
        )
        assert result is True
        mock_github.enable_auto_merge.assert_called_once_with(
            "acme", "widgets", 99, "squash"
        )

    @pytest.mark.asyncio
    async def test_failure_returns_false(self) -> None:
        mock_github = AsyncMock()
        mock_github.enable_auto_merge.side_effect = RuntimeError("not enabled")
        result = await _try_enable_auto_merge(
            mock_github, "acme", "widgets", 99, "squash"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_custom_merge_method(self) -> None:
        mock_github = AsyncMock()
        result = await _try_enable_auto_merge(
            mock_github, "acme", "widgets", 99, "rebase"
        )
        assert result is True
        mock_github.enable_auto_merge.assert_called_once_with(
            "acme", "widgets", 99, "rebase"
        )


# --- TIER_LABELS includes Execute ---


class TestTierLabels:
    def test_execute_label_exists(self) -> None:
        assert RepoTier.EXECUTE in TIER_LABELS
        assert TIER_LABELS[RepoTier.EXECUTE] == "tier:execute"

    def test_all_tiers_have_labels(self) -> None:
        for tier in RepoTier:
            assert tier in TIER_LABELS

    def test_label_constants(self) -> None:
        assert LABEL_TIER_OBSERVE == "tier:observe"
        assert LABEL_TIER_SUGGEST == "tier:suggest"
        assert LABEL_TIER_EXECUTE == "tier:execute"


# --- PublishResult has auto_merge_enabled ---


class TestPublishResultAutoMerge:
    def test_default_false(self) -> None:
        result = PublishResult(
            pr_number=1, pr_url="url", created=True, comment_id=1
        )
        assert result.auto_merge_enabled is False

    def test_explicit_true(self) -> None:
        result = PublishResult(
            pr_number=1, pr_url="url", created=True, comment_id=1,
            auto_merge_enabled=True,
        )
        assert result.auto_merge_enabled is True


# --- Full publish() integration with Execute tier ---


class TestPublishExecuteTier:
    """Tests publish() with Execute tier (mocked GitHub)."""

    def _mock_github(self) -> AsyncMock:
        mock = AsyncMock()
        mock.find_pr_by_head.return_value = None
        mock.get_default_branch.return_value = "main"
        mock.get_branch_sha.return_value = "abc123sha"
        mock.create_pull_request.return_value = {
            "number": 99,
            "html_url": "https://github.com/acme/widgets/pull/99",
        }
        mock.add_comment.return_value = {"id": 555}
        mock.add_labels.return_value = []
        mock.remove_label.return_value = None
        return mock

    def _patches(self, tp, intent):
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            with (
                patch("src.publisher.publisher.get_by_id", return_value=tp),
                patch(
                    "src.publisher.publisher.get_latest_for_taskpacket",
                    return_value=intent,
                ),
                patch("src.publisher.publisher.update_status", return_value=tp),
                patch(
                    "src.publisher.publisher.get_merge_mode",
                    return_value=MergeMode.AUTO_MERGE,
                ),
            ):
                yield

        return _ctx()

    @pytest.mark.asyncio
    async def test_execute_auto_merge_all_gates_pass(self) -> None:
        """Execute + AUTO_MERGE + approval → auto-merge enabled."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

        tp_id = uuid4()
        tp = TaskPacketRead(
            id=tp_id, repo="acme/widgets", issue_id=42,
            delivery_id="abc", correlation_id=uuid4(),
            status=TaskPacketStatus.VERIFICATION_PASSED,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        from src.intent.intent_spec import IntentSpecRead

        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Add feature", constraints=[], acceptance_criteria=[],
            non_goals=[], created_at=datetime.now(UTC),
        )

        mock_github = self._mock_github()

        with self._patches(tp, intent):
            from src.publisher.publisher import publish

            result = await publish(
                AsyncMock(), tp_id,
                _make_evidence(tp_id), _make_verification(),
                mock_github,
                repo_tier=RepoTier.EXECUTE,
                qa_passed=True,
                approval_received=True,
            )

        assert result.marked_ready is True
        assert result.auto_merge_enabled is True
        mock_github.enable_auto_merge.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_approval_no_auto_merge(self) -> None:
        """Execute + AUTO_MERGE but no approval → ready-for-review, no auto-merge."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

        tp_id = uuid4()
        tp = TaskPacketRead(
            id=tp_id, repo="acme/widgets", issue_id=42,
            delivery_id="abc", correlation_id=uuid4(),
            status=TaskPacketStatus.VERIFICATION_PASSED,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        from src.intent.intent_spec import IntentSpecRead

        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Add feature", constraints=[], acceptance_criteria=[],
            non_goals=[], created_at=datetime.now(UTC),
        )

        mock_github = self._mock_github()

        with self._patches(tp, intent):
            from src.publisher.publisher import publish

            result = await publish(
                AsyncMock(), tp_id,
                _make_evidence(tp_id), _make_verification(),
                mock_github,
                repo_tier=RepoTier.EXECUTE,
                qa_passed=True,
                approval_received=False,
            )

        assert result.marked_ready is True
        assert result.auto_merge_enabled is False
        mock_github.enable_auto_merge.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_require_review_no_auto_merge(self) -> None:
        """Execute + REQUIRE_REVIEW → ready-for-review, no auto-merge."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

        tp_id = uuid4()
        tp = TaskPacketRead(
            id=tp_id, repo="acme/widgets", issue_id=42,
            delivery_id="abc", correlation_id=uuid4(),
            status=TaskPacketStatus.VERIFICATION_PASSED,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        from src.intent.intent_spec import IntentSpecRead

        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Add feature", constraints=[], acceptance_criteria=[],
            non_goals=[], created_at=datetime.now(UTC),
        )

        mock_github = self._mock_github()

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch(
                "src.publisher.publisher.get_latest_for_taskpacket",
                return_value=intent,
            ),
            patch("src.publisher.publisher.update_status", return_value=tp),
            patch(
                "src.publisher.publisher.get_merge_mode",
                return_value=MergeMode.REQUIRE_REVIEW,
            ),
        ):
            from src.publisher.publisher import publish

            result = await publish(
                AsyncMock(), tp_id,
                _make_evidence(tp_id), _make_verification(),
                mock_github,
                repo_tier=RepoTier.EXECUTE,
                qa_passed=True,
                approval_received=True,
            )

        assert result.marked_ready is True
        assert result.auto_merge_enabled is False

    @pytest.mark.asyncio
    async def test_execute_auto_merge_failure_degrades_gracefully(self) -> None:
        """Execute + AUTO_MERGE + approval but GitHub rejects → still publishes."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

        tp_id = uuid4()
        tp = TaskPacketRead(
            id=tp_id, repo="acme/widgets", issue_id=42,
            delivery_id="abc", correlation_id=uuid4(),
            status=TaskPacketStatus.VERIFICATION_PASSED,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        from src.intent.intent_spec import IntentSpecRead

        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Add feature", constraints=[], acceptance_criteria=[],
            non_goals=[], created_at=datetime.now(UTC),
        )

        mock_github = self._mock_github()
        mock_github.enable_auto_merge.side_effect = RuntimeError("not enabled")

        with self._patches(tp, intent):
            from src.publisher.publisher import publish

            result = await publish(
                AsyncMock(), tp_id,
                _make_evidence(tp_id), _make_verification(),
                mock_github,
                repo_tier=RepoTier.EXECUTE,
                qa_passed=True,
                approval_received=True,
            )

        assert result.created is True
        assert result.marked_ready is True
        assert result.auto_merge_enabled is False


# --- Helpers ---


def _make_evidence(tp_id=None):
    from uuid import uuid4

    from src.agent.evidence import EvidenceBundle

    return EvidenceBundle(
        taskpacket_id=tp_id or uuid4(),
        intent_version=1,
        files_changed=["src/main.py"],
        agent_summary="Change",
    )


def _make_verification(passed=True):
    from src.verification.gate import VerificationResult
    from src.verification.runners.base import CheckResult

    return VerificationResult(
        passed=passed,
        checks=[CheckResult(name="ruff", passed=True, details="clean")],
    )
