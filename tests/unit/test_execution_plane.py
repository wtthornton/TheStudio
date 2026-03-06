"""Tests for Story 3.2: Compliance Checker — Execution Plane Health.

Validates:
- Workspace health checking (exists, accessible)
- Worker health checking (Temporal workers)
- Verification runner health (ruff, pytest availability)
- Publisher idempotency guard
- Credential scope checking
"""

import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.compliance.execution_plane import (
    EXPECTED_SCOPES_BY_TIER,
    CredentialScopeChecker,
    ExecutionPlaneChecker,
    PublisherIdempotencyChecker,
)


class TestExecutionPlaneChecker:
    """Tests for ExecutionPlaneChecker."""

    @pytest.mark.asyncio
    async def test_workspace_exists_and_accessible(self) -> None:
        """Workspace exists and is accessible -> healthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            assert health.workspace.healthy is True
            assert health.workspace.exists is True
            assert health.workspace.accessible is True

    @pytest.mark.asyncio
    async def test_workspace_does_not_exist(self) -> None:
        """Workspace does not exist -> unhealthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            # Don't create the workspace directory

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            assert health.workspace.healthy is False
            assert health.workspace.exists is False
            assert "does not exist" in (health.workspace.reason or "")

    @pytest.mark.asyncio
    async def test_workers_healthy_without_temporal_client(self) -> None:
        """No Temporal client -> assume workers healthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            checker = ExecutionPlaneChecker(
                workspace_root=tmpdir,
                temporal_client=None,
            )
            health = await checker.check_health(repo_id)

            assert health.workers.healthy is True
            assert health.workers.worker_count >= 1

    @pytest.mark.asyncio
    async def test_verification_runner_tools_available(self) -> None:
        """ruff and pytest available -> healthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            # These should be available in test environment
            assert health.verification_runner.ruff_available is True
            assert health.verification_runner.pytest_available is True
            assert health.verification_runner.healthy is True

    @pytest.mark.asyncio
    async def test_overall_health_requires_all_components(self) -> None:
        """Overall health requires workspace, workers, and verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            # All components should be healthy
            assert health.workspace.healthy is True
            assert health.workers.healthy is True
            assert health.verification_runner.healthy is True
            assert health.healthy is True

    @pytest.mark.asyncio
    async def test_overall_unhealthy_if_workspace_unhealthy(self) -> None:
        """Overall unhealthy if workspace is unhealthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            # Don't create workspace

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            assert health.workspace.healthy is False
            assert health.healthy is False
            assert health.reason is not None
            assert "Workspace" in health.reason

    @pytest.mark.asyncio
    async def test_to_dict_returns_complete_structure(self) -> None:
        """to_dict returns all health information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            health = await checker.check_health(repo_id)

            health_dict = health.to_dict()

            assert "healthy" in health_dict
            assert "workspace" in health_dict
            assert "workers" in health_dict
            assert "verification_runner" in health_dict


class TestPublisherIdempotencyChecker:
    """Tests for PublisherIdempotencyChecker."""

    @pytest.mark.asyncio
    async def test_healthy_without_lookup_function(self) -> None:
        """No lookup function -> assume healthy."""
        checker = PublisherIdempotencyChecker(taskpacket_lookup=None)
        health = await checker.check_health(uuid4())

        assert health.healthy is True
        assert health.lookup_operational is True

    @pytest.mark.asyncio
    async def test_healthy_with_working_lookup(self) -> None:
        """Working lookup function -> healthy."""

        async def mock_lookup(key: str) -> None:
            return None

        checker = PublisherIdempotencyChecker(taskpacket_lookup=mock_lookup)
        health = await checker.check_health(uuid4())

        assert health.healthy is True
        assert health.lookup_operational is True
        assert health.test_key_result == "not_found"

    @pytest.mark.asyncio
    async def test_unhealthy_with_failing_lookup(self) -> None:
        """Failing lookup function -> unhealthy."""

        async def failing_lookup(key: str) -> None:
            raise ConnectionError("Database unavailable")

        checker = PublisherIdempotencyChecker(taskpacket_lookup=failing_lookup)
        health = await checker.check_health(uuid4())

        assert health.healthy is False
        assert health.lookup_operational is False
        assert "failed" in (health.reason or "").lower()


class TestCredentialScopeChecker:
    """Tests for CredentialScopeChecker."""

    @pytest.mark.asyncio
    async def test_healthy_without_scope_fetcher(self) -> None:
        """No scope fetcher -> assume correct scopes."""
        checker = CredentialScopeChecker(token_scope_fetcher=None)
        health = await checker.check_scopes(uuid4(), "execute")

        assert health.healthy is True
        assert len(health.missing_scopes) == 0

    @pytest.mark.asyncio
    async def test_healthy_with_correct_scopes(self) -> None:
        """Correct scopes -> healthy."""
        expected = set(EXPECTED_SCOPES_BY_TIER["execute"])

        async def mock_fetcher(repo_id: Any) -> list[str]:
            return list(expected)

        checker = CredentialScopeChecker(token_scope_fetcher=mock_fetcher)
        health = await checker.check_scopes(uuid4(), "execute")

        assert health.healthy is True
        assert len(health.missing_scopes) == 0

    @pytest.mark.asyncio
    async def test_unhealthy_with_missing_scopes(self) -> None:
        """Missing required scopes -> unhealthy."""

        async def mock_fetcher(repo_id: Any) -> list[str]:
            return ["repo"]  # Missing "workflow" and "write:packages"

        checker = CredentialScopeChecker(token_scope_fetcher=mock_fetcher)
        health = await checker.check_scopes(uuid4(), "execute")

        assert health.healthy is False
        assert len(health.missing_scopes) > 0
        assert "Missing required scopes" in (health.reason or "")

    @pytest.mark.asyncio
    async def test_healthy_with_excess_scopes(self) -> None:
        """Excess scopes (but all required present) -> healthy."""
        expected = set(EXPECTED_SCOPES_BY_TIER["execute"])
        actual = expected | {"admin:org", "delete_repo"}  # Extra scopes

        async def mock_fetcher(repo_id: Any) -> list[str]:
            return list(actual)

        checker = CredentialScopeChecker(token_scope_fetcher=mock_fetcher)
        health = await checker.check_scopes(uuid4(), "execute")

        assert health.healthy is True
        assert len(health.excess_scopes) > 0

    @pytest.mark.asyncio
    async def test_unhealthy_with_failing_fetcher(self) -> None:
        """Failing scope fetcher -> unhealthy."""

        async def failing_fetcher(repo_id: Any) -> list[str]:
            raise ConnectionError("GitHub API unavailable")

        checker = CredentialScopeChecker(token_scope_fetcher=failing_fetcher)
        health = await checker.check_scopes(uuid4(), "execute")

        assert health.healthy is False
        assert "Failed to fetch" in (health.reason or "")

    @pytest.mark.asyncio
    async def test_different_tiers_have_different_expected_scopes(self) -> None:
        """Different tiers require different scopes."""
        checker = CredentialScopeChecker(token_scope_fetcher=None)

        observe_health = await checker.check_scopes(uuid4(), "observe")
        execute_health = await checker.check_scopes(uuid4(), "execute")

        # Execute tier should require more scopes than observe
        assert len(execute_health.expected_scopes) >= len(observe_health.expected_scopes)


class TestComplianceCheckerWithExecutionPlane:
    """Integration tests for compliance checker with execution plane checks."""

    @pytest.mark.asyncio
    async def test_execution_plane_checks_included(self) -> None:
        """Execution plane checks are included when enabled."""
        from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
        from src.compliance.models import REQUIRED_LABELS, ComplianceCheck

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_id = uuid4()
            workspace = Path(tmpdir) / str(repo_id)
            workspace.mkdir()

            execution_plane_checker = ExecutionPlaneChecker(workspace_root=tmpdir)
            checker = ComplianceChecker(
                execution_plane_checker=execution_plane_checker,
            )

            repo_info = GitHubRepoInfo(
                owner="test",
                repo="repo",
                default_branch="main",
                rulesets=[{"name": "ci", "rules": [{"type": "required_status_checks"}]}],
                branch_protection={
                    "required_pull_request_reviews": {"required_approving_review_count": 1}
                },
                labels=REQUIRED_LABELS.copy(),
                codeowners_exists=True,
                codeowners_paths=[],
            )

            result = await checker.check_compliance(
                repo_id=repo_id,
                repo_info=repo_info,
                triggered_by="test",
                projects_v2_waived=True,
                check_execution_plane=True,
            )

            # Should have execution plane checks
            check_names = [c.check for c in result.checks]
            assert ComplianceCheck.EXECUTION_PLANE_HEALTH in check_names
            assert ComplianceCheck.PUBLISHER_IDEMPOTENCY in check_names
            assert ComplianceCheck.CREDENTIALS_SCOPED in check_names

    @pytest.mark.asyncio
    async def test_execution_plane_checks_excluded(self) -> None:
        """Execution plane checks are excluded when disabled."""
        from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
        from src.compliance.models import REQUIRED_LABELS, ComplianceCheck

        checker = ComplianceChecker()

        repo_info = GitHubRepoInfo(
            owner="test",
            repo="repo",
            default_branch="main",
            rulesets=[{"name": "ci", "rules": [{"type": "required_status_checks"}]}],
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },
            labels=REQUIRED_LABELS.copy(),
            codeowners_exists=True,
            codeowners_paths=[],
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        # Should NOT have execution plane checks
        check_names = [c.check for c in result.checks]
        assert ComplianceCheck.EXECUTION_PLANE_HEALTH not in check_names
        assert ComplianceCheck.PUBLISHER_IDEMPOTENCY not in check_names
        assert ComplianceCheck.CREDENTIALS_SCOPED not in check_names
