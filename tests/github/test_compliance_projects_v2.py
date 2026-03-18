"""Tests for Projects v2 compliance check (Epic 29 AC 8-9)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.models import ComplianceCheck


def _repo_info() -> GitHubRepoInfo:
    return GitHubRepoInfo(
        owner="myorg",
        repo="myrepo",
        default_branch="main",
        rulesets=[{
            "id": 1,
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
            "rules": [{"type": "required_status_checks"}],
        }],
        branch_protection={
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
            },
        },
        labels=[
            "agent:in-progress", "agent:done", "agent:human-review",
            "tier:observe", "tier:suggest",
        ],
        codeowners_exists=True,
        codeowners_paths=["src/"],
    )


class TestProjectsV2Waived:
    """Waived check passes immediately."""

    @pytest.mark.asyncio
    async def test_waived_passes(self) -> None:
        checker = ComplianceChecker()
        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=_repo_info(),
            triggered_by="test",
            projects_v2_waived=True,
            check_execution_plane=False,
        )
        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed


class TestProjectsV2NoClient:
    """No client = stub pass (backwards compatibility)."""

    @pytest.mark.asyncio
    async def test_no_client_passes_with_note(self) -> None:
        checker = ComplianceChecker(projects_v2_client=None)
        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=_repo_info(),
            triggered_by="test",
            check_execution_plane=False,
        )
        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed
        assert "not configured" in (projects_check.details or {}).get("note", "")


class TestProjectsV2Disabled:
    """Feature flag off = pass with note."""

    @pytest.mark.asyncio
    async def test_disabled_passes(self) -> None:
        mock_client = AsyncMock()
        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = False
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed


class TestProjectsV2NotConfigured:
    """Enabled but missing owner/number = fail."""

    @pytest.mark.asyncio
    async def test_missing_owner_fails(self) -> None:
        mock_client = AsyncMock()
        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = ""
            mock_settings.projects_v2_number = 0
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert not projects_check.passed
        assert "not configured" in projects_check.failure_reason


class TestProjectsV2FieldValidation:
    """AC 8: Validates required fields exist."""

    @pytest.mark.asyncio
    async def test_all_fields_present_passes(self) -> None:
        mock_client = AsyncMock()
        mock_client.get_configured_fields = AsyncMock(return_value={
            "Status", "Automation Tier", "Risk Tier", "Priority", "Owner", "Repo",
        })
        mock_client.get_project_items = AsyncMock(return_value=[{"id": "item1"}])

        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed
        assert projects_check.details["has_synced_items"] is True

    @pytest.mark.asyncio
    async def test_missing_fields_fails(self) -> None:
        mock_client = AsyncMock()
        mock_client.get_configured_fields = AsyncMock(return_value={
            "Status", "Priority",  # Missing 4 required fields
        })

        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert not projects_check.passed
        assert "missing required fields" in projects_check.failure_reason

    @pytest.mark.asyncio
    async def test_no_synced_items_still_passes(self) -> None:
        """All fields present but no items — passes (project is configured)."""
        mock_client = AsyncMock()
        mock_client.get_configured_fields = AsyncMock(return_value={
            "Status", "Automation Tier", "Risk Tier", "Priority", "Owner", "Repo",
        })
        mock_client.get_project_items = AsyncMock(return_value=[])

        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed
        assert projects_check.details["has_synced_items"] is False


class TestProjectsV2APIError:
    """Graceful handling of API errors."""

    @pytest.mark.asyncio
    async def test_api_error_fails_check(self) -> None:
        mock_client = AsyncMock()
        mock_client.get_configured_fields = AsyncMock(
            side_effect=RuntimeError("API unavailable")
        )

        checker = ComplianceChecker(projects_v2_client=mock_client)

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=_repo_info(),
                triggered_by="test",
                check_execution_plane=False,
            )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert not projects_check.passed
        assert "API unavailable" in projects_check.failure_reason
