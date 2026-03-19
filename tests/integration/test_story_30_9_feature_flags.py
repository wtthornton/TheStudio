"""Story 30.9: Enable Projects v2 + Meridian Portfolio — Integration Tests.

Verifies that when feature flags are activated with valid configuration,
the Projects v2 sync and Meridian Portfolio review paths work end-to-end.

These tests mock the external GitHub GraphQL API but exercise the full
internal code path: settings → activity → client → mapping → output.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Projects v2: Flag activation path
# ---------------------------------------------------------------------------


class TestProjectsV2FlagActivation:
    """Verify Projects v2 sync works when flags are properly configured."""

    @pytest.mark.asyncio
    async def test_full_sync_path_with_flags_enabled(self) -> None:
        """When projects_v2_enabled=True with valid owner/number/token,
        status sync completes successfully through the full code path."""
        from src.workflow.activities import (
            ProjectStatusInput,
            update_project_status_activity,
        )

        params = ProjectStatusInput(
            taskpacket_id="tp-story-30-9",
            taskpacket_status="PUBLISHED",
            project_item_id="PVTI_integration_test",
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "thestudio-org"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "ghp_test_token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced is True
        assert result.error == ""
        mock_client.set_status.assert_called_once_with(
            "thestudio-org", 1, "PVTI_integration_test", "Done"
        )

    @pytest.mark.asyncio
    async def test_all_status_transitions_map_correctly(self) -> None:
        """Every TaskPacket status maps to a valid Projects v2 status."""
        from src.github.projects_mapping import map_status

        expected_mappings = {
            "RECEIVED": "Queued",
            "ENRICHED": "Queued",
            "INTENT_BUILT": "In Progress",
            "IN_PROGRESS": "In Progress",
            "VERIFICATION_PASSED": "In Progress",
            "AWAITING_APPROVAL": "In Review",
            "CLARIFICATION_REQUESTED": "Blocked",
            "HUMAN_REVIEW_REQUIRED": "Blocked",
            "PUBLISHED": "Done",
            "FAILED": "Done",
            "REJECTED": "Done",
        }

        for tp_status, expected_v2_status in expected_mappings.items():
            result = map_status(tp_status)
            assert result == expected_v2_status, (
                f"map_status('{tp_status}') returned '{result}', expected '{expected_v2_status}'"
            )

    @pytest.mark.asyncio
    async def test_received_sets_both_status_and_tier(self) -> None:
        """RECEIVED status sets both Queued status and automation tier."""
        from src.workflow.activities import (
            ProjectStatusInput,
            update_project_status_activity,
        )

        params = ProjectStatusInput(
            taskpacket_id="tp-tier-test",
            taskpacket_status="RECEIVED",
            repo_tier="suggest",
            project_item_id="PVTI_tier_test",
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "thestudio-org"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "ghp_test_token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced is True
        mock_client.set_status.assert_called_once()
        mock_client.set_automation_tier.assert_called_once_with(
            "thestudio-org", 1, "PVTI_tier_test", "Suggest"
        )

    @pytest.mark.asyncio
    async def test_enriched_sets_risk_tier(self) -> None:
        """ENRICHED status triggers risk tier field update."""
        from src.workflow.activities import (
            ProjectStatusInput,
            update_project_status_activity,
        )

        params = ProjectStatusInput(
            taskpacket_id="tp-risk-test",
            taskpacket_status="ENRICHED",
            complexity_index="high",
            project_item_id="PVTI_risk_test",
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "thestudio-org"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "ghp_test_token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced is True
        mock_client.set_risk_tier.assert_called_once_with(
            "thestudio-org", 1, "PVTI_risk_test", "High"
        )

    @pytest.mark.asyncio
    async def test_sync_failure_is_best_effort(self) -> None:
        """API failure doesn't raise — returns graceful error."""
        from src.workflow.activities import (
            ProjectStatusInput,
            update_project_status_activity,
        )

        params = ProjectStatusInput(
            taskpacket_id="tp-fail-test",
            taskpacket_status="PUBLISHED",
            project_item_id="PVTI_fail_test",
        )

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = "thestudio-org"
            mock_settings.projects_v2_number = 1
            mock_settings.projects_v2_token = "ghp_test_token"
            mock_settings.github_app_id = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.set_status = AsyncMock(side_effect=RuntimeError("GitHub API 502"))

            with patch(
                "src.github.projects_client.ProjectsV2Client",
                return_value=mock_client,
            ):
                result = await update_project_status_activity(params)

        assert result.synced is False
        assert result.error == "sync_exception"

    def test_pipeline_input_propagates_projects_v2_fields(self) -> None:
        """PipelineInput carries projects_v2 config to workflow."""
        from src.workflow.pipeline import PipelineInput

        inp = PipelineInput(
            taskpacket_id="tp-pipe",
            correlation_id="corr-pipe",
            projects_v2_enabled=True,
            project_item_id="PVTI_pipe",
        )
        assert inp.projects_v2_enabled is True
        assert inp.project_item_id == "PVTI_pipe"


# ---------------------------------------------------------------------------
# Meridian Portfolio: Flag activation path
# ---------------------------------------------------------------------------


class TestMeridianPortfolioFlagActivation:
    """Verify Meridian Portfolio review works when flags are configured."""

    @pytest.mark.asyncio
    async def test_portfolio_review_activity_with_mock_snapshot(self) -> None:
        """Full portfolio review path: collect → evaluate → persist."""
        from src.meridian.portfolio_config import (
            HealthStatus,
            PortfolioReviewOutput,
        )
        from src.meridian.portfolio_workflow import (
            PortfolioReviewInput,
            portfolio_review_activity,
        )

        params = PortfolioReviewInput(
            owner="thestudio-org",
            project_number=1,
            token="ghp_test_token",
        )

        # Mock the collector to return a synthetic snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.items = []
        mock_snapshot.items_by_status = {"Queued": [], "In Progress": [], "Done": []}
        mock_snapshot.items_by_repo = {}

        # Mock the agent runner to return a healthy review
        mock_review = PortfolioReviewOutput(
            overall_health=HealthStatus.HEALTHY,
            flags=[],
            recommendations=["All systems operating normally"],
            metrics={"blocked_ratio": 0.0, "failure_rate": 0.0},
            reviewed_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.parsed_output = mock_review
        mock_result.raw_output = ""

        collect_path = "src.meridian.portfolio_collector.collect_portfolio"
        persist_path = "src.meridian.portfolio_workflow._persist_review"

        with (
            patch(collect_path, new_callable=AsyncMock, return_value=mock_snapshot) as mock_collect,
            patch("src.agent.framework.AgentRunner") as mock_runner_cls,
            patch(persist_path, new_callable=AsyncMock, return_value=True),
            patch("src.settings.settings") as mock_settings,
        ):
            mock_settings.meridian_thresholds = {
                "blocked_ratio": 0.20,
                "high_risk_concurrent": 3,
                "review_stale_hours": 48,
                "repo_concentration": 0.50,
                "failure_rate": 0.30,
                "queued_stale_days": 7,
            }
            mock_settings.meridian_portfolio_github_issue = False

            mock_runner = AsyncMock()
            mock_runner.run.return_value = mock_result
            mock_runner_cls.return_value = mock_runner

            result = await portfolio_review_activity(params)

        assert result.overall_health == "healthy"
        assert result.persisted is True
        assert result.error == ""
        mock_collect.assert_called_once_with(
            owner="thestudio-org",
            project_number=1,
            token="ghp_test_token",
        )

    @pytest.mark.asyncio
    async def test_portfolio_review_with_github_issue_posting(self) -> None:
        """When meridian_portfolio_github_issue=True, issue is posted."""
        from src.meridian.portfolio_config import (
            HealthStatus,
            PortfolioReviewOutput,
        )
        from src.meridian.portfolio_workflow import (
            PortfolioReviewInput,
            portfolio_review_activity,
        )

        params = PortfolioReviewInput(
            owner="thestudio-org",
            project_number=1,
            token="ghp_test_token",
        )

        mock_snapshot = MagicMock()
        mock_snapshot.items = []
        mock_snapshot.items_by_status = {}
        mock_snapshot.items_by_repo = {}

        mock_review = PortfolioReviewOutput(
            overall_health=HealthStatus.WARNING,
            flags=[],
            recommendations=["Review blocked items"],
            metrics={"blocked_ratio": 0.25},
            reviewed_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.parsed_output = mock_review
        mock_result.raw_output = ""

        collect_path = "src.meridian.portfolio_collector.collect_portfolio"
        persist_path = "src.meridian.portfolio_workflow._persist_review"
        post_path = "src.meridian.portfolio_workflow._post_github_issue"

        with (
            patch(collect_path, new_callable=AsyncMock, return_value=mock_snapshot),
            patch("src.agent.framework.AgentRunner") as mock_runner_cls,
            patch(persist_path, new_callable=AsyncMock, return_value=True),
            patch(post_path, new_callable=AsyncMock, return_value=True) as mock_post,
            patch("src.settings.settings") as mock_settings,
        ):
            mock_settings.meridian_thresholds = {
                "blocked_ratio": 0.20,
                "high_risk_concurrent": 3,
                "review_stale_hours": 48,
                "repo_concentration": 0.50,
                "failure_rate": 0.30,
                "queued_stale_days": 7,
            }
            mock_settings.meridian_portfolio_github_issue = True

            mock_runner = AsyncMock()
            mock_runner.run.return_value = mock_result
            mock_runner_cls.return_value = mock_runner

            result = await portfolio_review_activity(params)

        assert result.overall_health == "warning"
        assert result.github_issue_posted is True
        mock_post.assert_called_once()

    def test_portfolio_health_thresholds_configurable(self) -> None:
        """Meridian thresholds can be overridden via settings."""
        from src.settings import Settings

        custom = Settings(
            encryption_key="hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=",
            meridian_thresholds={
                "blocked_ratio": 0.10,
                "high_risk_concurrent": 2,
                "review_stale_hours": 24,
                "repo_concentration": 0.40,
                "failure_rate": 0.20,
                "queued_stale_days": 3,
            },
        )
        assert custom.meridian_thresholds["blocked_ratio"] == 0.10
        assert custom.meridian_thresholds["queued_stale_days"] == 3

    def test_health_report_markdown_format(self) -> None:
        """format_health_report_markdown produces valid markdown."""
        from src.meridian.portfolio_config import (
            HealthFlag,
            HealthStatus,
            PortfolioReviewOutput,
            format_health_report_markdown,
        )

        review = PortfolioReviewOutput(
            overall_health=HealthStatus.WARNING,
            flags=[
                HealthFlag(
                    category="throughput",
                    severity="high",
                    description="Blocked items >20%",
                    affected_items=["org/repo#1"],
                ),
            ],
            recommendations=["Clear blocked items"],
            metrics={"blocked_ratio": 0.25, "failure_rate": 0.05},
            reviewed_at=datetime(2026, 3, 19, 9, 0, tzinfo=UTC),
        )

        md = format_health_report_markdown(review)
        assert "WARNING" in md.upper() or "warning" in md.lower() or "Warning" in md
        assert "throughput" in md.lower() or "Throughput" in md
        assert "Blocked" in md or "blocked" in md


# ---------------------------------------------------------------------------
# Compliance checker: Projects v2 integration
# ---------------------------------------------------------------------------


class TestComplianceProjectsV2Activation:
    """Verify compliance checker gives real results when Projects v2 is configured."""

    @pytest.mark.asyncio
    async def test_enabled_but_not_configured_fails(self) -> None:
        """Compliance fails when enabled but owner/number missing.

        When a Projects v2 client IS provided (not None), the checker
        proceeds to validate config — enabled + missing owner triggers failure.
        """
        from src.compliance.checker import ComplianceChecker
        from src.compliance.models import ComplianceCheck

        check = ComplianceCheck.PROJECTS_V2

        checker = ComplianceChecker.__new__(ComplianceChecker)
        checker._check_results = []
        # Provide a mock client so the checker doesn't short-circuit
        checker._projects_v2_client = AsyncMock()

        with patch("src.settings.settings") as mock_settings:
            mock_settings.projects_v2_enabled = True
            mock_settings.projects_v2_owner = ""
            mock_settings.projects_v2_number = 0

            await checker._check_projects_v2(check)

        assert len(checker._check_results) == 1
        assert not checker._check_results[0].passed
        assert "not configured" in checker._check_results[0].failure_reason

    @pytest.mark.asyncio
    async def test_no_client_passes_with_waiver_note(self) -> None:
        """When no Projects v2 client is provided, checker passes with note."""
        from src.compliance.checker import ComplianceChecker
        from src.compliance.models import ComplianceCheck

        check = ComplianceCheck.PROJECTS_V2

        checker = ComplianceChecker.__new__(ComplianceChecker)
        checker._check_results = []
        checker._projects_v2_client = None

        await checker._check_projects_v2(check)

        assert len(checker._check_results) == 1
        assert checker._check_results[0].passed
        assert "not configured" in checker._check_results[0].details["note"]


# ---------------------------------------------------------------------------
# Admin UI: Portfolio health page
# ---------------------------------------------------------------------------


class TestAdminPortfolioHealthActivation:
    """Verify Admin UI portfolio health page serves real data."""

    def test_portfolio_health_route_registered(self) -> None:
        """The /admin/ui/portfolio-health route is registered."""
        from src.admin.ui_router import ui_router

        routes = [r.path for r in ui_router.routes if hasattr(r, "path")]
        assert any("portfolio-health" in r for r in routes), (
            f"No portfolio-health route found in: {routes}"
        )

    def test_portfolio_health_partial_route_registered(self) -> None:
        """The /admin/ui/partials/portfolio-health route is registered."""
        from src.admin.ui_router import ui_router

        routes = [r.path for r in ui_router.routes if hasattr(r, "path")]
        assert any("partials/portfolio-health" in r for r in routes), (
            f"No partials/portfolio-health route found in: {routes}"
        )

    def test_portfolio_review_db_model_exists(self) -> None:
        """PortfolioReviewRow ORM model is defined for persistence."""
        from src.db.models import PortfolioReviewRow

        assert hasattr(PortfolioReviewRow, "reviewed_at")
        assert hasattr(PortfolioReviewRow, "overall_health")
        assert hasattr(PortfolioReviewRow, "flags")
        assert hasattr(PortfolioReviewRow, "metrics")
        assert hasattr(PortfolioReviewRow, "recommendations")


# ---------------------------------------------------------------------------
# Feature flag settings validation
# ---------------------------------------------------------------------------


class TestFeatureFlagSettings:
    """Verify feature flag settings load correctly."""

    def test_projects_v2_flags_default_off(self) -> None:
        """Projects v2 is off by default."""
        from src.settings import Settings

        s = Settings(encryption_key="hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=")
        assert s.projects_v2_enabled is False
        assert s.projects_v2_owner == ""
        assert s.projects_v2_number == 0

    def test_meridian_portfolio_flags_default_off(self) -> None:
        """Meridian portfolio is off by default."""
        from src.settings import Settings

        s = Settings(encryption_key="hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=")
        assert s.meridian_portfolio_enabled is False
        assert s.meridian_portfolio_github_issue is False
        assert s.meridian_portfolio_repo == ""

    def test_projects_v2_flags_enable_via_env(self, monkeypatch) -> None:
        """Projects v2 can be enabled via environment variables."""
        monkeypatch.setenv("THESTUDIO_PROJECTS_V2_ENABLED", "true")
        monkeypatch.setenv("THESTUDIO_PROJECTS_V2_OWNER", "test-org")
        monkeypatch.setenv("THESTUDIO_PROJECTS_V2_NUMBER", "42")
        monkeypatch.setenv("THESTUDIO_PROJECTS_V2_TOKEN", "ghp_xxx")
        enc_key = "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac="
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", enc_key)

        from src.settings import Settings

        s = Settings()
        assert s.projects_v2_enabled is True
        assert s.projects_v2_owner == "test-org"
        assert s.projects_v2_number == 42
        assert s.projects_v2_token == "ghp_xxx"

    def test_meridian_portfolio_flags_enable_via_env(self, monkeypatch) -> None:
        """Meridian portfolio can be enabled via environment variables."""
        monkeypatch.setenv("THESTUDIO_MERIDIAN_PORTFOLIO_ENABLED", "true")
        monkeypatch.setenv("THESTUDIO_MERIDIAN_PORTFOLIO_GITHUB_ISSUE", "true")
        monkeypatch.setenv("THESTUDIO_MERIDIAN_PORTFOLIO_REPO", "test-org/test-repo")
        enc_key = "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac="
        monkeypatch.setenv("THESTUDIO_ENCRYPTION_KEY", enc_key)

        from src.settings import Settings

        s = Settings()
        assert s.meridian_portfolio_enabled is True
        assert s.meridian_portfolio_github_issue is True
        assert s.meridian_portfolio_repo == "test-org/test-repo"

    def test_meridian_thresholds_defaults(self) -> None:
        """Default thresholds match AC 19 specification."""
        from src.settings import Settings

        s = Settings(encryption_key="hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=")
        t = s.meridian_thresholds
        assert t["blocked_ratio"] == 0.20
        assert t["high_risk_concurrent"] == 3
        assert t["review_stale_hours"] == 48
        assert t["repo_concentration"] == 0.50
        assert t["failure_rate"] == 0.30
        assert t["queued_stale_days"] == 7
