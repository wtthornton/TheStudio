"""Tests for Story 3.4: First Repo Promotion to Execute.

Validates the promotion workflow through direct function calls.
API endpoint testing would require database setup which is out of scope.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.execution_plane import ExecutionPlaneChecker
from src.compliance.models import REQUIRED_LABELS
from src.compliance.promotion import PromotionService
from src.compliance.promotion import clear as clear_transitions
from src.compliance.router import (
    clear,
    count_repos_by_tier,
    get_repo,
    get_repo_by_full_name,
    list_repos,
    register_repo,
    update_repo_tier,
)
from src.repo.repo_profile import RepoTier


@pytest.fixture(autouse=True)
def clear_state() -> None:
    """Clear repo registry and transitions before each test."""
    clear()
    clear_transitions()


def make_compliant_repo_info(
    owner: str = "test-org", repo: str = "test-repo"
) -> GitHubRepoInfo:
    """Create GitHubRepoInfo that passes all compliance checks."""
    return GitHubRepoInfo(
        owner=owner,
        repo=repo,
        default_branch="main",
        rulesets=[{"name": "ci", "rules": [{"type": "required_status_checks"}]}],
        branch_protection={
            "required_pull_request_reviews": {"required_approving_review_count": 1}
        },
        labels=REQUIRED_LABELS.copy(),
        codeowners_exists=True,
        codeowners_paths=[],
    )


def make_non_compliant_repo_info(
    owner: str = "test-org", repo: str = "test-repo"
) -> GitHubRepoInfo:
    """Create GitHubRepoInfo that fails compliance checks."""
    return GitHubRepoInfo(
        owner=owner,
        repo=repo,
        default_branch="main",
        rulesets=[],
        branch_protection=None,
        labels=[],
        codeowners_exists=False,
        codeowners_paths=[],
    )


class TestRepoRegistry:
    """Tests for in-memory repo registry."""

    def test_register_and_get_repo(self) -> None:
        """Can register and retrieve a repo."""
        repo_id = uuid4()
        register_repo(repo_id, "test-org", "test-repo")

        repo = get_repo(repo_id)
        assert repo is not None
        assert repo["owner"] == "test-org"
        assert repo["repo"] == "test-repo"
        assert repo["tier"] == RepoTier.OBSERVE

    def test_register_repo_with_custom_tier(self) -> None:
        """Can register repo with custom tier."""
        repo_id = uuid4()
        register_repo(repo_id, "test-org", "test-repo", RepoTier.SUGGEST)

        repo = get_repo(repo_id)
        assert repo is not None
        assert repo["tier"] == RepoTier.SUGGEST

    def test_update_repo_tier(self) -> None:
        """Can update repo tier."""
        repo_id = uuid4()
        register_repo(repo_id, "test-org", "test-repo", RepoTier.OBSERVE)

        update_repo_tier(repo_id, RepoTier.SUGGEST)

        repo = get_repo(repo_id)
        assert repo is not None
        assert repo["tier"] == RepoTier.SUGGEST

    def test_get_nonexistent_repo_returns_none(self) -> None:
        """Getting non-existent repo returns None."""
        repo = get_repo(uuid4())
        assert repo is None


class TestPromotionWorkflow:
    """Tests for promotion workflow (via PromotionService)."""

    @pytest.mark.asyncio
    async def test_observe_to_suggest_promotion(self) -> None:
        """Observe -> Suggest promotion succeeds without compliance check."""
        repo_id = uuid4()
        register_repo(repo_id, "test-org", "test-repo", RepoTier.OBSERVE)
        repo_info = make_non_compliant_repo_info()  # Would fail compliance

        service = PromotionService(repo_profile_updater=update_repo_tier)

        result = await service.request_promotion(
            repo_id=repo_id,
            target_tier=RepoTier.SUGGEST,
            triggered_by="admin",
            repo_info=repo_info,
            current_tier=RepoTier.OBSERVE,
        )

        assert result.success is True
        assert result.from_tier == RepoTier.OBSERVE
        assert result.to_tier == RepoTier.SUGGEST

    @pytest.mark.asyncio
    async def test_suggest_to_execute_with_compliant_repo(self) -> None:
        """Suggest -> Execute promotion succeeds with compliant repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            register_repo(repo_id, "test-org", "test-repo", RepoTier.SUGGEST)
            repo_info = make_compliant_repo_info()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                repo_profile_updater=update_repo_tier,
            )

            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.success is True
            assert result.compliance_score == 100.0

    @pytest.mark.asyncio
    async def test_suggest_to_execute_with_non_compliant_repo(self) -> None:
        """Suggest -> Execute promotion fails with non-compliant repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            register_repo(repo_id, "test-org", "test-repo", RepoTier.SUGGEST)
            repo_info = make_non_compliant_repo_info()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                repo_profile_updater=update_repo_tier,
            )

            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )

            assert result.success is False
            assert result.block_reason is not None


class TestDemotionWorkflow:
    """Tests for demotion workflow."""

    @pytest.mark.asyncio
    async def test_execute_to_suggest_demotion(self) -> None:
        """Execute -> Suggest demotion succeeds."""
        repo_id = uuid4()
        register_repo(repo_id, "test-org", "test-repo", RepoTier.EXECUTE)

        service = PromotionService(repo_profile_updater=update_repo_tier)

        result = await service.demote_tier(
            repo_id=repo_id,
            target_tier=RepoTier.SUGGEST,
            reason="Compliance violation",
            triggered_by="compliance_monitor",
            current_tier=RepoTier.EXECUTE,
        )

        assert result.success is True
        assert result.from_tier == RepoTier.EXECUTE
        assert result.to_tier == RepoTier.SUGGEST


class TestFirstRepoPromotion:
    """Integration test: First repo promotion to Execute tier."""

    @pytest.mark.asyncio
    async def test_full_promotion_flow(self) -> None:
        """Test complete promotion flow: Observe -> Suggest -> Execute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            # Register repo at Observe tier
            repo_info = make_compliant_repo_info("thestudio", "demo-repo")
            register_repo(
                repo_id, "thestudio", "demo-repo", RepoTier.OBSERVE, repo_info
            )

            # Set up service
            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                repo_profile_updater=update_repo_tier,
            )

            # Step 1: Observe -> Suggest
            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.SUGGEST,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.OBSERVE,
            )
            assert result.success is True
            assert result.to_tier == RepoTier.SUGGEST

            # Update in-memory tier
            update_repo_tier(repo_id, RepoTier.SUGGEST)
            repo = get_repo(repo_id)
            assert repo is not None
            assert repo["tier"] == RepoTier.SUGGEST

            # Step 2: Check eligibility for Execute
            eligibility = await service.check_promotion_eligibility(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )
            assert eligibility.eligible is True

            # Step 3: Suggest -> Execute
            result = await service.request_promotion(
                repo_id=repo_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )
            assert result.success is True
            assert result.compliance_score == 100.0

            # Final verification
            update_repo_tier(repo_id, RepoTier.EXECUTE)
            repo = get_repo(repo_id)
            assert repo is not None
            assert repo["tier"] == RepoTier.EXECUTE


class TestMultiRepoRegistration:
    """Tests for Story 3.5: Multi-Repo Registration."""

    def test_register_multiple_repos(self) -> None:
        """Can register 3+ repos."""
        repo1_id = uuid4()
        repo2_id = uuid4()
        repo3_id = uuid4()

        register_repo(repo1_id, "org1", "repo1", installation_id=1001)
        register_repo(repo2_id, "org1", "repo2", installation_id=1001)
        register_repo(repo3_id, "org2", "repo3", installation_id=2001)

        repos = list_repos()
        assert len(repos) == 3

    def test_repos_have_separate_tiers(self) -> None:
        """Each repo maintains its own tier."""
        repo1_id = uuid4()
        repo2_id = uuid4()
        repo3_id = uuid4()

        register_repo(repo1_id, "org", "repo1", RepoTier.OBSERVE)
        register_repo(repo2_id, "org", "repo2", RepoTier.SUGGEST)
        register_repo(repo3_id, "org", "repo3", RepoTier.EXECUTE)

        assert get_repo(repo1_id)["tier"] == RepoTier.OBSERVE
        assert get_repo(repo2_id)["tier"] == RepoTier.SUGGEST
        assert get_repo(repo3_id)["tier"] == RepoTier.EXECUTE

    def test_count_repos_by_tier(self) -> None:
        """Count repos grouped by tier."""
        register_repo(uuid4(), "org", "observe1", RepoTier.OBSERVE)
        register_repo(uuid4(), "org", "observe2", RepoTier.OBSERVE)
        register_repo(uuid4(), "org", "suggest1", RepoTier.SUGGEST)
        register_repo(uuid4(), "org", "execute1", RepoTier.EXECUTE)

        counts = count_repos_by_tier()
        assert counts["observe"] == 2
        assert counts["suggest"] == 1
        assert counts["execute"] == 1

    def test_get_repo_by_full_name(self) -> None:
        """Can retrieve repo by full name."""
        repo_id = uuid4()
        register_repo(repo_id, "thestudio", "demo-repo")

        repo = get_repo_by_full_name("thestudio/demo-repo")
        assert repo is not None
        assert repo["id"] == repo_id

    def test_repos_have_installation_id(self) -> None:
        """Each repo stores its installation ID for credential scoping."""
        repo_id = uuid4()
        register_repo(repo_id, "org", "repo", installation_id=12345)

        repo = get_repo(repo_id)
        assert repo is not None
        assert repo["installation_id"] == 12345


class TestMultiRepoTierPromotion:
    """Tests for Story 3.6: Multi-Repo Tier Promotion."""

    @pytest.mark.asyncio
    async def test_promote_multiple_repos_independently(self) -> None:
        """Multiple repos can be promoted independently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo1_id = uuid4()
            repo2_id = uuid4()
            repo3_id = uuid4()

            # Create workspaces for each repo
            for repo_id in [repo1_id, repo2_id, repo3_id]:
                workspace = Path(tmpdir) / str(repo_id)
                workspace.mkdir()

            # Register all repos with compliant info
            repo_info = make_compliant_repo_info()
            register_repo(repo1_id, "org", "repo1", RepoTier.OBSERVE, repo_info)
            register_repo(repo2_id, "org", "repo2", RepoTier.OBSERVE, repo_info)
            register_repo(repo3_id, "org", "repo3", RepoTier.OBSERVE, repo_info)

            # Set up service
            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                repo_profile_updater=update_repo_tier,
            )

            # Promote repo1 to Suggest
            result1 = await service.request_promotion(
                repo_id=repo1_id,
                target_tier=RepoTier.SUGGEST,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.OBSERVE,
            )
            assert result1.success is True
            update_repo_tier(repo1_id, RepoTier.SUGGEST)

            # Promote repo2 to Suggest then Execute
            result2a = await service.request_promotion(
                repo_id=repo2_id,
                target_tier=RepoTier.SUGGEST,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.OBSERVE,
            )
            assert result2a.success is True
            update_repo_tier(repo2_id, RepoTier.SUGGEST)

            result2b = await service.request_promotion(
                repo_id=repo2_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=repo_info,
                current_tier=RepoTier.SUGGEST,
            )
            assert result2b.success is True
            update_repo_tier(repo2_id, RepoTier.EXECUTE)

            # repo3 stays at Observe

            # Verify final tier states
            assert get_repo(repo1_id)["tier"] == RepoTier.SUGGEST
            assert get_repo(repo2_id)["tier"] == RepoTier.EXECUTE
            assert get_repo(repo3_id)["tier"] == RepoTier.OBSERVE

            # Verify tier counts
            counts = count_repos_by_tier()
            assert counts["observe"] == 1
            assert counts["suggest"] == 1
            assert counts["execute"] == 1

    @pytest.mark.asyncio
    async def test_non_compliant_repos_cannot_reach_execute(self) -> None:
        """Non-compliant repos are blocked from Execute tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo1_id = uuid4()
            repo2_id = uuid4()

            for repo_id in [repo1_id, repo2_id]:
                workspace = Path(tmpdir) / str(repo_id)
                workspace.mkdir()

            compliant_info = make_compliant_repo_info("org", "repo1")
            non_compliant_info = make_non_compliant_repo_info("org", "repo2")

            register_repo(repo1_id, "org", "repo1", RepoTier.SUGGEST, compliant_info)
            register_repo(
                repo2_id, "org", "repo2", RepoTier.SUGGEST, non_compliant_info
            )

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            compliance_checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )
            service = PromotionService(
                compliance_checker=compliance_checker,
                repo_profile_updater=update_repo_tier,
            )

            # Compliant repo can promote to Execute
            result1 = await service.request_promotion(
                repo_id=repo1_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=compliant_info,
                current_tier=RepoTier.SUGGEST,
            )
            assert result1.success is True

            # Non-compliant repo is blocked
            result2 = await service.request_promotion(
                repo_id=repo2_id,
                target_tier=RepoTier.EXECUTE,
                triggered_by="admin",
                repo_info=non_compliant_info,
                current_tier=RepoTier.SUGGEST,
            )
            assert result2.success is False
            assert result2.block_reason is not None

    @pytest.mark.asyncio
    async def test_demote_one_repo_others_unaffected(self) -> None:
        """Demoting one repo doesn't affect others."""
        repo1_id = uuid4()
        repo2_id = uuid4()

        register_repo(repo1_id, "org", "repo1", RepoTier.EXECUTE)
        register_repo(repo2_id, "org", "repo2", RepoTier.EXECUTE)

        service = PromotionService(repo_profile_updater=update_repo_tier)

        # Demote repo1
        result = await service.demote_tier(
            repo_id=repo1_id,
            target_tier=RepoTier.SUGGEST,
            reason="Compliance violation",
            triggered_by="monitor",
            current_tier=RepoTier.EXECUTE,
        )
        assert result.success is True
        update_repo_tier(repo1_id, RepoTier.SUGGEST)

        # repo1 is now Suggest, repo2 remains Execute
        assert get_repo(repo1_id)["tier"] == RepoTier.SUGGEST
        assert get_repo(repo2_id)["tier"] == RepoTier.EXECUTE


class TestComplianceCheck:
    """Tests for compliance check via ComplianceChecker."""

    @pytest.mark.asyncio
    async def test_compliance_check_compliant_repo(self) -> None:
        """Compliant repo passes all checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            repo_info = make_compliant_repo_info()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )

            result = await checker.check_compliance(
                repo_id=repo_id,
                repo_info=repo_info,
                triggered_by="api",
                check_execution_plane=True,
            )

            assert result.overall_passed is True
            assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_compliance_check_non_compliant_repo(self) -> None:
        """Non-compliant repo fails some checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            repo_info = make_non_compliant_repo_info()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )

            result = await checker.check_compliance(
                repo_id=repo_id,
                repo_info=repo_info,
                triggered_by="api",
                check_execution_plane=True,
            )

            assert result.overall_passed is False
            assert result.score < 100.0

            # Verify failed checks have remediation hints
            failed_checks = [c for c in result.checks if not c.passed]
            for check in failed_checks:
                assert check.remediation_hint is not None
