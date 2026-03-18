"""Tests for Projects v2 status sync activity (Epic 29 AC 5-7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.workflow.activities import (
    ProjectStatusInput,
    update_project_status_activity,
)


class TestProjectStatusDisabled:
    """AC 7: Feature flag controls sync."""

    @pytest.mark.asyncio
    async def test_disabled_returns_not_synced(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="PUBLISHED",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = False
            result = await update_project_status_activity(params)

        assert not result.synced
        assert result.error == "projects_v2_disabled"


class TestProjectStatusNotConfigured:
    """AC 7: Graceful handling when not configured."""

    @pytest.mark.asyncio
    async def test_no_owner_returns_not_synced(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="PUBLISHED",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = ""
            mock_settings.projects_v2_number = 0
            result = await update_project_status_activity(params)

        assert not result.synced
        assert result.error == "projects_v2_not_configured"


class TestProjectStatusNoItemId:
    """Sync requires an item_id to update."""

    @pytest.mark.asyncio
    async def test_no_item_id_returns_not_synced(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="PUBLISHED",
            project_item_id="",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)

                result = await update_project_status_activity(params)

        assert not result.synced
        assert result.error == "no_item_id"


class TestProjectStatusSyncSuccess:
    """AC 5-6: Successful status sync."""

    @pytest.mark.asyncio
    async def test_published_syncs_done(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="PUBLISHED",
            project_item_id="PVTI_456",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced
        mock_client.set_status.assert_called_once_with(
            "myorg", 1, "PVTI_456", "Done"
        )

    @pytest.mark.asyncio
    async def test_received_sets_tier(self) -> None:
        """AC 3: Automation Tier set on RECEIVED."""
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="RECEIVED",
            repo_tier="execute",
            project_item_id="PVTI_456",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced
        mock_client.set_status.assert_called_once()
        mock_client.set_automation_tier.assert_called_once_with(
            "myorg", 1, "PVTI_456", "Execute"
        )

    @pytest.mark.asyncio
    async def test_enriched_sets_risk_tier(self) -> None:
        """AC 4: Risk Tier set on ENRICHED."""
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="ENRICHED",
            complexity_index="high",
            project_item_id="PVTI_456",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced
        mock_client.set_risk_tier.assert_called_once_with(
            "myorg", 1, "PVTI_456", "High"
        )


class TestProjectStatusSyncFailure:
    """AC 5: Sync failures don't block pipeline."""

    @pytest.mark.asyncio
    async def test_exception_returns_gracefully(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="PUBLISHED",
            project_item_id="PVTI_456",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.set_status = AsyncMock(side_effect=RuntimeError("API down"))

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert not result.synced
        assert result.error == "sync_exception"

    @pytest.mark.asyncio
    async def test_unmapped_status(self) -> None:
        params = ProjectStatusInput(
            taskpacket_id="tp-001",
            taskpacket_status="NONEXISTENT",
            project_item_id="PVTI_456",
        )
        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "myorg"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "test-token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert not result.synced
        assert "unmapped_status" in result.error


class TestPipelineProjectsV2Integration:
    """Pipeline-level tests for Projects v2 sync points."""

    def test_pipeline_input_has_projects_v2_fields(self) -> None:
        from src.workflow.pipeline import PipelineInput

        inp = PipelineInput(
            taskpacket_id="tp-001",
            correlation_id="corr-001",
            projects_v2_enabled=True,
            project_item_id="PVTI_456",
        )
        assert inp.projects_v2_enabled is True
        assert inp.project_item_id == "PVTI_456"

    def test_projects_v2_sync_step_policy_exists(self) -> None:
        from src.workflow.pipeline import STEP_POLICIES, WorkflowStep

        assert WorkflowStep.PROJECTS_V2_SYNC in STEP_POLICIES
        policy = STEP_POLICIES[WorkflowStep.PROJECTS_V2_SYNC]
        assert policy.timeout.total_seconds() == 30
        assert policy.max_retries == 2
