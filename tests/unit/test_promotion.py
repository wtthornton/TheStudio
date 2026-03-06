"""Tests for Story 3.3: Execute Tier Promotion Gate.

Validates:
- Promotion eligibility checking (valid paths, compliance gate)
- Promotion execution with audit trail
- Demotion support
- tier_changed signal emission
"""

import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.execution_plane import ExecutionPlaneChecker
from src.compliance.models import REQUIRED_LABELS
from src.compliance.promotion import (
    VALID_DEMOTIONS,
    VALID_PROMOTIONS,
    PromotionBlockReason,
    PromotionService,
    TierTransition,
    clear,
    get_latest_transition,
    get_transitions,
    store_transition,
)
from src.repo.repo_profile import RepoTier


@pytest.fixture(autouse=True)
def clear_state() -> None:
    """Clear tier transitions before each test."""
    clear()


def make_compliant_repo_info() -> GitHubRepoInfo:
    """Create GitHubRepoInfo that passes all compliance checks."""
    return GitHubRepoInfo(
        owner="test-org",
        repo="test-repo",
        default_branch="main",
        rulesets=[{"name": "ci", "rules": [{"type": "required_status_checks"}]}],
        branch_protection={
            "required_pull_request_reviews": {"required_approving_review_count": 1}
        },
        labels=REQUIRED_LABELS.copy(),
        codeowners_exists=True,
        codeowners_paths=[],
    )


def make_non_compliant_repo_info() -> GitHubRepoInfo:
    """Create GitHubRepoInfo that fails compliance checks."""
    return GitHubRepoInfo(
        owner="test-org",
        repo="test-repo",
        default_branch="main",
        rulesets=[],  # Missing rulesets
        branch_protection=None,  # Missing branch protection
        labels=[],  # Missing labels
        codeowners_exists=False,
        codeowners_paths=[],
    )


class TestPromotionPaths:
    """Tests for valid promotion/demotion paths."""

    def test_observe_can_promote_to_suggest(self) -> None:
        """Observe tier can promote to Suggest."""
        assert RepoTier.SUGGEST in VALID_PROMOTIONS[RepoTier.OBSERVE]

    def test_suggest_can_promote_to_execute(self) -> None:
        """Suggest tier can promote to Execute."""
        assert RepoTier.EXECUTE in VALID_PROMOTIONS[RepoTier.SUGGEST]

    def test_execute_cannot_promote(self) -> None:
        """Execute tier has no further promotions."""
        assert VALID_PROMOTIONS[RepoTier.EXECUTE] == []

    def test_execute_can_demote_to_suggest(self) -> None:
        """Execute tier can demote to Suggest."""
        assert RepoTier.SUGGEST in VALID_DEMOTIONS[RepoTier.EXECUTE]

    def test_execute_can_demote_to_observe(self) -> None:
        """Execute tier can demote to Observe."""
        assert RepoTier.OBSERVE in VALID_DEMOTIONS[RepoTier.EXECUTE]

    def test_observe_cannot_demote(self) -> None:
        """Observe tier has no demotions."""
        assert VALID_DEMOTIONS[RepoTier.OBSERVE] == []


class TestPromotionEligibility:
    """Tests for promotion eligibility checking."""

    @pytest.mark.asyncio
    async def test_already_at_tier_not_eligible(self) -> None:
        """Cannot promote to current tier."""
        service = PromotionService()
        repo_info = make_compliant_repo_info()

        result = await service.check_promotion_eligibility(
            repo_id=uuid4(),
            target_tier=RepoTier.SUGGEST,
            repo_info=repo_info,
            current_tier=RepoTier.SUGGEST,
        )

        assert result.eligible is False
        assert result.block_reason == PromotionBlockReason.ALREADY_AT_TIER

    @pytest.mark.asyncio
    async def test_invalid_promotion_path_not_eligible(self) -> None:
        """Cannot promote via invalid path (Observe -> Execute)."""
        service = PromotionService()
        repo_info = make_compliant_repo_info()

        result = await service.check_promotion_eligibility(
            repo_id=uuid4(),
            target_tier=RepoTier.EXECUTE,
            repo_info=repo_info,
            current_tier=RepoTier.OBSERVE,  # Cannot skip Suggest
        )

        assert result.eligible is False
        assert result.block_reason == PromotionBlockReason.INVALID_CURRENT_TIER

    @pytest.mark.asyncio
    async def test_active_workflows_blocks_promotion(self) -> None:
        """Active workflows block promotion."""

        async def has_active_workflows(repo_id: Any) -> bool:
            return True

        service = PromotionService(active_workflow_checker=has_active_workflows)
        repo_info = make_compliant_repo_info()

        result = await service.check_promotion_eligibility(
            repo_id=uuid4(),
            target_tier=RepoTier.SUGGEST,
            repo_info=repo_info,
            current_tier=RepoTier.OBSERVE,
        )

        assert result.eligible is False
        assert result.block_reason == PromotionBlockReason.ACTIVE_WORKFLOWS

    @pytest.mark.asyncio
    async def test_compliance_failure_blocks_execute_promotion(self) -> None:
        """Failed compliance check blocks Execute promotion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(compliance_checker=compliance_checker)

            repo_info = make_non_compliant_repo_info()

            result = await service.check_promotion_eligibility(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.eligible is False
            assert result.block_reason == PromotionBlockReason.COMPLIANCE_FAILED
            assert result.compliance_result is not None
            assert result.compliance_result.overall_passed is False

    @pytest.mark.asyncio
    async def test_compliant_repo_eligible_for_execute(self) -> None:
        """Compliant repo is eligible for Execute promotion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(compliance_checker=compliance_checker)

            repo_info = make_compliant_repo_info()

            result = await service.check_promotion_eligibility(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.eligible is True
            assert result.compliance_result is not None
            assert result.compliance_result.overall_passed is True

    @pytest.mark.asyncio
    async def test_suggest_promotion_does_not_require_compliance(self) -> None:
        """Suggest promotion doesn't require compliance check."""
        service = PromotionService()
        repo_info = make_non_compliant_repo_info()  # Would fail compliance

        result = await service.check_promotion_eligibility(
            repo_id=uuid4(),
            target_tier=RepoTier.SUGGEST,
            repo_info=repo_info,
            current_tier=RepoTier.OBSERVE,
        )

        # Still eligible - Suggest doesn't require compliance
        assert result.eligible is True
        assert result.compliance_result is None


class TestPromotionExecution:
    """Tests for promotion execution."""

    @pytest.mark.asyncio
    async def test_successful_promotion_records_transition(self) -> None:
        """Successful promotion records a tier transition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(compliance_checker=compliance_checker)

            repo_info = make_compliant_repo_info()

            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.success is True
            assert result.from_tier == RepoTier.SUGGEST
            assert result.to_tier == RepoTier.EXECUTE

            # Check transition was recorded
            transitions = get_transitions(repo_id)
            assert len(transitions) == 1
            assert transitions[0].from_tier == RepoTier.SUGGEST
            assert transitions[0].to_tier == RepoTier.EXECUTE
            assert transitions[0].triggered_by == "admin"

    @pytest.mark.asyncio
    async def test_failed_promotion_does_not_record_transition(self) -> None:
        """Failed promotion does not record a tier transition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(compliance_checker=compliance_checker)

            repo_info = make_non_compliant_repo_info()

            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.success is False
            assert result.block_reason == PromotionBlockReason.COMPLIANCE_FAILED

            # Check no transition was recorded
            transitions = get_transitions(repo_id)
            assert len(transitions) == 0

    @pytest.mark.asyncio
    async def test_promotion_emits_tier_changed_signal(self) -> None:
        """Successful promotion emits tier_changed signal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            emitted_signals: list[dict[str, Any]] = []

            async def capture_signal(signal: dict[str, Any]) -> None:
                emitted_signals.append(signal)

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                signal_emitter=capture_signal,
            )

            repo_info = make_compliant_repo_info()

            await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert len(emitted_signals) == 1
            assert emitted_signals[0]["event"] == "tier_changed"
            assert emitted_signals[0]["from_tier"] == "suggest"
            assert emitted_signals[0]["to_tier"] == "execute"


class TestDemotion:
    """Tests for tier demotion."""

    @pytest.mark.asyncio
    async def test_valid_demotion_succeeds(self) -> None:
        """Valid demotion path succeeds."""
        service = PromotionService()

        result = await service.demote_tier(
            repo_id=uuid4(),
            target_tier=RepoTier.SUGGEST,
            reason="Compliance violation detected",
            triggered_by="compliance_monitor",
            current_tier=RepoTier.EXECUTE,
        )

        assert result.success is True
        assert result.from_tier == RepoTier.EXECUTE
        assert result.to_tier == RepoTier.SUGGEST
        assert "Compliance violation" in result.reason

    @pytest.mark.asyncio
    async def test_invalid_demotion_fails(self) -> None:
        """Invalid demotion path fails."""
        service = PromotionService()

        result = await service.demote_tier(
            repo_id=uuid4(),
            target_tier=RepoTier.EXECUTE,  # Can't demote TO Execute
            reason="Test",
            triggered_by="test",
            current_tier=RepoTier.OBSERVE,
        )

        assert result.success is False
        assert "Invalid demotion path" in result.reason

    @pytest.mark.asyncio
    async def test_demotion_records_transition(self) -> None:
        """Demotion records a tier transition."""
        repo_id = uuid4()
        service = PromotionService()

        await service.demote_tier(
            repo_id=repo_id,
            target_tier=RepoTier.OBSERVE,
            reason="Security incident",
            triggered_by="security_team",
            current_tier=RepoTier.EXECUTE,
        )

        transitions = get_transitions(repo_id)
        assert len(transitions) == 1
        assert transitions[0].from_tier == RepoTier.EXECUTE
        assert transitions[0].to_tier == RepoTier.OBSERVE
        assert "Security incident" in transitions[0].reason

    @pytest.mark.asyncio
    async def test_demotion_emits_tier_changed_signal(self) -> None:
        """Demotion emits tier_changed signal."""
        emitted_signals: list[dict[str, Any]] = []

        async def capture_signal(signal: dict[str, Any]) -> None:
            emitted_signals.append(signal)

        service = PromotionService(signal_emitter=capture_signal)

        await service.demote_tier(
            repo_id=uuid4(),
            target_tier=RepoTier.SUGGEST,
            reason="Compliance drift",
            triggered_by="compliance_monitor",
            current_tier=RepoTier.EXECUTE,
        )

        assert len(emitted_signals) == 1
        assert emitted_signals[0]["event"] == "tier_changed"
        assert emitted_signals[0]["from_tier"] == "execute"
        assert emitted_signals[0]["to_tier"] == "suggest"


class TestTransitionStorage:
    """Tests for tier transition storage (in-memory stub)."""

    def test_store_and_retrieve_transition(self) -> None:
        """Can store and retrieve transitions."""
        repo_id = uuid4()
        transition = TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.OBSERVE,
            to_tier=RepoTier.SUGGEST,
            triggered_by="test",
            reason="Test transition",
        )

        store_transition(transition)

        retrieved = get_latest_transition(repo_id)
        assert retrieved is not None
        assert retrieved.repo_id == repo_id
        assert retrieved.from_tier == RepoTier.OBSERVE
        assert retrieved.to_tier == RepoTier.SUGGEST

    def test_get_all_transitions(self) -> None:
        """Can retrieve all transitions for a repo."""
        repo_id = uuid4()

        for tier in [RepoTier.SUGGEST, RepoTier.EXECUTE]:
            transition = TierTransition(
                repo_id=repo_id,
                from_tier=RepoTier.OBSERVE if tier == RepoTier.SUGGEST else RepoTier.SUGGEST,
                to_tier=tier,
                triggered_by="test",
                reason=f"Transition to {tier.value}",
            )
            store_transition(transition)

        transitions = get_transitions(repo_id)
        assert len(transitions) == 2

    def test_get_latest_returns_none_for_unknown_repo(self) -> None:
        """get_latest_transition returns None for unknown repo."""
        result = get_latest_transition(uuid4())
        assert result is None
