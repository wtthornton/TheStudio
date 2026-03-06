"""Unit tests for Suggest Tier Promotion (Story 1.10).

Tests promotion preconditions, tier gate in Publisher, and tier label reconciliation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.taskpacket import TaskPacketRead, TaskPacketStatus
from src.publisher.publisher import (
    LABEL_TIER_OBSERVE,
    LABEL_TIER_SUGGEST,
    _should_mark_ready,
)
from src.repo.repo_profile import RepoTier
from src.repo.tier_promotion import PromotionError, promote_to_suggest

# --- Fixtures ---


def _make_taskpacket(**overrides: object) -> TaskPacketRead:
    defaults = {
        "id": uuid4(),
        "repo": "acme/widgets",
        "issue_id": 42,
        "delivery_id": "abc123",
        "correlation_id": uuid4(),
        "status": TaskPacketStatus.VERIFICATION_PASSED,
        "scope": {"type": "feature"},
        "risk_flags": {},
        "complexity_index": "low",
        "context_packs": [],
        "intent_spec_id": uuid4(),
        "intent_version": 1,
        "loopback_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return TaskPacketRead(**defaults)  # type: ignore[arg-type]


# --- Promotion Preconditions ---


class TestPromotionPreconditions:
    @pytest.mark.asyncio
    async def test_promotes_when_v_and_qa_passed(self) -> None:
        tp = _make_taskpacket(status=TaskPacketStatus.VERIFICATION_PASSED)
        profile_id = uuid4()
        mock_profile = MagicMock(owner="acme", repo_name="widgets")

        with (
            patch("src.repo.tier_promotion.get_by_id", return_value=tp),
            patch("src.repo.tier_promotion.update_tier", return_value=mock_profile),
        ):
            result = await promote_to_suggest(
                AsyncMock(), profile_id, tp.id,
                verification_passed=True, qa_passed=True,
            )

        assert result.promoted is True
        assert result.new_tier == RepoTier.SUGGEST
        assert result.previous_tier == RepoTier.OBSERVE

    @pytest.mark.asyncio
    async def test_rejects_when_verification_not_passed(self) -> None:
        tp = _make_taskpacket()
        with patch("src.repo.tier_promotion.get_by_id", return_value=tp):
            with pytest.raises(PromotionError, match="verification has not passed"):
                await promote_to_suggest(
                    AsyncMock(), uuid4(), tp.id,
                    verification_passed=False, qa_passed=True,
                )

    @pytest.mark.asyncio
    async def test_rejects_when_qa_not_passed(self) -> None:
        tp = _make_taskpacket()
        with patch("src.repo.tier_promotion.get_by_id", return_value=tp):
            with pytest.raises(PromotionError, match="QA has not passed"):
                await promote_to_suggest(
                    AsyncMock(), uuid4(), tp.id,
                    verification_passed=True, qa_passed=False,
                )

    @pytest.mark.asyncio
    async def test_rejects_when_taskpacket_not_found(self) -> None:
        with patch("src.repo.tier_promotion.get_by_id", return_value=None):
            with pytest.raises(PromotionError, match="not found"):
                await promote_to_suggest(
                    AsyncMock(), uuid4(), uuid4(),
                    verification_passed=True, qa_passed=True,
                )

    @pytest.mark.asyncio
    async def test_rejects_wrong_taskpacket_status(self) -> None:
        tp = _make_taskpacket(status=TaskPacketStatus.IN_PROGRESS)
        with patch("src.repo.tier_promotion.get_by_id", return_value=tp):
            with pytest.raises(PromotionError, match="TaskPacket status"):
                await promote_to_suggest(
                    AsyncMock(), uuid4(), tp.id,
                    verification_passed=True, qa_passed=True,
                )

    @pytest.mark.asyncio
    async def test_accepts_published_status(self) -> None:
        tp = _make_taskpacket(status=TaskPacketStatus.PUBLISHED)
        mock_profile = MagicMock(owner="acme", repo_name="widgets")

        with (
            patch("src.repo.tier_promotion.get_by_id", return_value=tp),
            patch("src.repo.tier_promotion.update_tier", return_value=mock_profile),
        ):
            result = await promote_to_suggest(
                AsyncMock(), uuid4(), tp.id,
                verification_passed=True, qa_passed=True,
            )
        assert result.promoted is True


class TestPromotionResult:
    @pytest.mark.asyncio
    async def test_result_has_audit_metadata(self) -> None:
        tp = _make_taskpacket(status=TaskPacketStatus.VERIFICATION_PASSED)
        mock_profile = MagicMock(owner="acme", repo_name="widgets")

        with (
            patch("src.repo.tier_promotion.get_by_id", return_value=tp),
            patch("src.repo.tier_promotion.update_tier", return_value=mock_profile),
        ):
            result = await promote_to_suggest(
                AsyncMock(), uuid4(), tp.id,
                verification_passed=True, qa_passed=True,
            )

        assert isinstance(result.timestamp, datetime)
        assert "Promoted after" in result.reason
        assert str(tp.id) in result.reason


# --- Tier Gate in Publisher ---


class TestShouldMarkReady:
    def test_suggest_tier_with_both_passed(self) -> None:
        assert _should_mark_ready(RepoTier.SUGGEST, True, True) is True

    def test_suggest_tier_without_qa(self) -> None:
        assert _should_mark_ready(RepoTier.SUGGEST, True, False) is False

    def test_suggest_tier_without_verification(self) -> None:
        assert _should_mark_ready(RepoTier.SUGGEST, False, True) is False

    def test_observe_tier_never_ready(self) -> None:
        assert _should_mark_ready(RepoTier.OBSERVE, True, True) is False

    def test_observe_tier_with_both_passed(self) -> None:
        assert _should_mark_ready(RepoTier.OBSERVE, True, True) is False


# --- Tier Label Reconciliation ---


class TestTierLabelReconciliation:
    @pytest.mark.asyncio
    async def test_suggest_tier_adds_suggest_label(self) -> None:
        from src.publisher.publisher import _reconcile_tier_labels

        mock_github = AsyncMock()
        await _reconcile_tier_labels(mock_github, "acme", "widgets", 1, RepoTier.SUGGEST)

        # Should remove observe label and add suggest label
        mock_github.remove_label.assert_called_once_with("acme", "widgets", 1, LABEL_TIER_OBSERVE)
        mock_github.add_labels.assert_called_once_with(
            "acme", "widgets", 1, [LABEL_TIER_SUGGEST]
        )

    @pytest.mark.asyncio
    async def test_observe_tier_adds_observe_label(self) -> None:
        from src.publisher.publisher import _reconcile_tier_labels

        mock_github = AsyncMock()
        await _reconcile_tier_labels(mock_github, "acme", "widgets", 1, RepoTier.OBSERVE)

        mock_github.remove_label.assert_called_once_with("acme", "widgets", 1, LABEL_TIER_SUGGEST)
        mock_github.add_labels.assert_called_once_with(
            "acme", "widgets", 1, [LABEL_TIER_OBSERVE]
        )


# --- Publisher Tier-Aware Behavior ---


class TestPublishWithTier:
    @pytest.mark.asyncio
    async def test_observe_tier_stays_draft(self) -> None:
        """Observe tier: PR stays as draft regardless of V+QA status."""
        from src.agent.evidence import EvidenceBundle
        from src.intent.intent_spec import IntentSpecRead
        from src.publisher.publisher import publish
        from src.verification.gate import VerificationResult
        from src.verification.runners.base import CheckResult

        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Test goal", constraints=[], acceptance_criteria=["test"],
            non_goals=[], created_at=datetime.now(UTC),
        )
        evidence = EvidenceBundle(taskpacket_id=tp_id, intent_version=1, files_changed=["a.py"])
        verification = VerificationResult(
            passed=True, checks=[CheckResult(name="ruff", passed=True)]
        )

        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = None
        mock_github.get_default_branch.return_value = "main"
        mock_github.get_branch_sha.return_value = "sha"
        mock_github.create_pull_request.return_value = {
            "number": 1, "html_url": "https://github.com/acme/widgets/pull/1",
        }
        mock_github.add_comment.return_value = {"id": 1}
        mock_github.add_labels.return_value = []
        mock_github.remove_label.return_value = None

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            result = await publish(
                AsyncMock(), tp_id, evidence, verification, mock_github,
                repo_tier=RepoTier.OBSERVE, qa_passed=True,
            )

        assert result.marked_ready is False
        mock_github.mark_ready_for_review.assert_not_called()

    @pytest.mark.asyncio
    async def test_suggest_tier_marks_ready(self) -> None:
        """Suggest tier: PR marked ready-for-review when V+QA passed."""
        from src.agent.evidence import EvidenceBundle
        from src.intent.intent_spec import IntentSpecRead
        from src.publisher.publisher import publish
        from src.verification.gate import VerificationResult
        from src.verification.runners.base import CheckResult

        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Test goal", constraints=[], acceptance_criteria=["test"],
            non_goals=[], created_at=datetime.now(UTC),
        )
        evidence = EvidenceBundle(taskpacket_id=tp_id, intent_version=1, files_changed=["a.py"])
        verification = VerificationResult(
            passed=True, checks=[CheckResult(name="ruff", passed=True)]
        )

        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = None
        mock_github.get_default_branch.return_value = "main"
        mock_github.get_branch_sha.return_value = "sha"
        mock_github.create_pull_request.return_value = {
            "number": 1, "html_url": "https://github.com/acme/widgets/pull/1",
        }
        mock_github.add_comment.return_value = {"id": 1}
        mock_github.add_labels.return_value = []
        mock_github.remove_label.return_value = None

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            result = await publish(
                AsyncMock(), tp_id, evidence, verification, mock_github,
                repo_tier=RepoTier.SUGGEST, qa_passed=True,
            )

        assert result.marked_ready is True
        mock_github.mark_ready_for_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_suggest_tier_stays_draft_without_qa(self) -> None:
        """Suggest tier: PR stays draft if QA did not pass."""
        from src.agent.evidence import EvidenceBundle
        from src.intent.intent_spec import IntentSpecRead
        from src.publisher.publisher import publish
        from src.verification.gate import VerificationResult
        from src.verification.runners.base import CheckResult

        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id)
        intent = IntentSpecRead(
            id=uuid4(), taskpacket_id=tp_id, version=1,
            goal="Test goal", constraints=[], acceptance_criteria=["test"],
            non_goals=[], created_at=datetime.now(UTC),
        )
        evidence = EvidenceBundle(taskpacket_id=tp_id, intent_version=1, files_changed=["a.py"])
        verification = VerificationResult(
            passed=True, checks=[CheckResult(name="ruff", passed=True)]
        )

        mock_github = AsyncMock()
        mock_github.find_pr_by_head.return_value = None
        mock_github.get_default_branch.return_value = "main"
        mock_github.get_branch_sha.return_value = "sha"
        mock_github.create_pull_request.return_value = {
            "number": 1, "html_url": "https://github.com/acme/widgets/pull/1",
        }
        mock_github.add_comment.return_value = {"id": 1}
        mock_github.add_labels.return_value = []
        mock_github.remove_label.return_value = None

        with (
            patch("src.publisher.publisher.get_by_id", return_value=tp),
            patch("src.publisher.publisher.get_latest_for_taskpacket", return_value=intent),
            patch("src.publisher.publisher.update_status", return_value=tp),
        ):
            result = await publish(
                AsyncMock(), tp_id, evidence, verification, mock_github,
                repo_tier=RepoTier.SUGGEST, qa_passed=False,
            )

        assert result.marked_ready is False
        mock_github.mark_ready_for_review.assert_not_called()
