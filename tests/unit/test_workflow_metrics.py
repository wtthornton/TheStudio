"""Tests for Story 4.3: Fleet Dashboard API — Workflow Metrics.

Tests the WorkflowMetricsService for querying Temporal workflow metrics.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.admin.workflow_metrics import (
    DEFAULT_ALERT_FAILURE_RATE_THRESHOLD,
    DEFAULT_STUCK_THRESHOLD_HOURS,
    HotAlert,
    RepoWorkflowMetrics,
    WorkflowCounts,
    WorkflowMetricsResponse,
    WorkflowMetricsService,
)


class TestWorkflowCounts:
    """Tests for WorkflowCounts dataclass."""

    def test_default_values(self) -> None:
        """WorkflowCounts has zero defaults."""
        counts = WorkflowCounts()

        assert counts.running == 0
        assert counts.stuck == 0
        assert counts.failed == 0
        assert counts.completed == 0


class TestRepoWorkflowMetrics:
    """Tests for RepoWorkflowMetrics dataclass."""

    def test_to_dict(self) -> None:
        """to_dict returns expected format."""
        repo_id = uuid4()
        metrics = RepoWorkflowMetrics(
            repo_id=repo_id,
            repo_name="owner/repo",
            tier="execute",
            counts=WorkflowCounts(running=5, stuck=1, failed=2, completed=10),
            queue_depth=3,
            pass_rate_24h=0.833,
            has_elevated_failure_rate=False,
            stuck_workflow_ids=["wf-123"],
        )

        result = metrics.to_dict()

        assert result["repo_id"] == str(repo_id)
        assert result["repo_name"] == "owner/repo"
        assert result["tier"] == "execute"
        assert result["running"] == 5
        assert result["stuck"] == 1
        assert result["failed"] == 2
        assert result["completed"] == 10
        assert result["queue_depth"] == 3
        assert result["pass_rate_24h"] == 83.3
        assert result["has_elevated_failure_rate"] is False
        assert result["stuck_workflow_ids"] == ["wf-123"]


class TestHotAlert:
    """Tests for HotAlert dataclass."""

    def test_to_dict(self) -> None:
        """to_dict returns expected format."""
        alert = HotAlert(
            alert_type="stuck_workflows",
            severity="warning",
            repo_name="owner/repo",
            message="2 workflows stuck > 2h",
            workflow_ids=["wf-1", "wf-2"],
            details={"threshold_hours": 2},
        )

        result = alert.to_dict()

        assert result["alert_type"] == "stuck_workflows"
        assert result["severity"] == "warning"
        assert result["repo_name"] == "owner/repo"
        assert result["message"] == "2 workflows stuck > 2h"
        assert result["workflow_ids"] == ["wf-1", "wf-2"]
        assert result["details"] == {"threshold_hours": 2}


class TestWorkflowMetricsResponse:
    """Tests for WorkflowMetricsResponse dataclass."""

    def test_to_dict(self) -> None:
        """to_dict returns full response format."""
        now = datetime.now(UTC)
        response = WorkflowMetricsResponse(
            aggregate=WorkflowCounts(running=10, stuck=2, failed=3, completed=50),
            queue_depth=15,
            pass_rate_24h=0.85,
            repos=[],
            alerts=[],
            checked_at=now,
            stuck_threshold_hours=2,
        )

        result = response.to_dict()

        assert result["aggregate"]["running"] == 10
        assert result["aggregate"]["stuck"] == 2
        assert result["aggregate"]["failed"] == 3
        assert result["aggregate"]["completed"] == 50
        assert result["queue_depth"] == 15
        assert result["pass_rate_24h"] == 85.0
        assert result["repos"] == []
        assert result["alerts"] == []
        assert result["checked_at"] == now.isoformat()
        assert result["stuck_threshold_hours"] == 2


class TestWorkflowMetricsService:
    """Tests for WorkflowMetricsService."""

    @pytest.fixture
    def service(self) -> WorkflowMetricsService:
        """Create a WorkflowMetricsService with default settings."""
        return WorkflowMetricsService(
            temporal_host="localhost:7233",
            namespace="test-namespace",
            task_queue="test-queue",
        )

    def test_default_thresholds(self, service: WorkflowMetricsService) -> None:
        """Service uses default threshold values."""
        assert service._stuck_threshold_hours == DEFAULT_STUCK_THRESHOLD_HOURS
        assert service._failure_rate_threshold == DEFAULT_ALERT_FAILURE_RATE_THRESHOLD

    def test_custom_thresholds(self) -> None:
        """Service accepts custom threshold values."""
        service = WorkflowMetricsService(
            stuck_threshold_hours=4,
            failure_rate_threshold=0.5,
        )

        assert service._stuck_threshold_hours == 4
        assert service._failure_rate_threshold == 0.5

    def test_matches_repo_with_slash(self, service: WorkflowMetricsService) -> None:
        """_matches_repo handles repo names with slashes."""
        wf = MagicMock()
        wf.id = "workflow-owner-repo-123"

        result = service._matches_repo(wf, "owner/repo")

        assert result is True

    def test_matches_repo_no_match(self, service: WorkflowMetricsService) -> None:
        """_matches_repo returns False when no match."""
        wf = MagicMock()
        wf.id = "workflow-other-project-123"

        result = service._matches_repo(wf, "owner/repo")

        assert result is False

    def test_generate_repo_alerts_stuck_workflows(
        self, service: WorkflowMetricsService
    ) -> None:
        """_generate_repo_alerts creates alert for stuck workflows."""
        repo_metric = RepoWorkflowMetrics(
            repo_id=uuid4(),
            repo_name="owner/repo",
            tier="execute",
            stuck_workflow_ids=["wf-1", "wf-2"],
        )

        alerts = service._generate_repo_alerts(repo_metric)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "stuck_workflows"
        assert alerts[0].severity == "warning"
        assert "2 workflow(s) stuck" in alerts[0].message

    def test_generate_repo_alerts_elevated_failure_rate(
        self, service: WorkflowMetricsService
    ) -> None:
        """_generate_repo_alerts creates alert for elevated failure rate."""
        repo_metric = RepoWorkflowMetrics(
            repo_id=uuid4(),
            repo_name="owner/repo",
            tier="suggest",
            counts=WorkflowCounts(completed=5, failed=5),
            pass_rate_24h=0.5,
            has_elevated_failure_rate=True,
        )

        alerts = service._generate_repo_alerts(repo_metric)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "elevated_failure_rate"
        assert alerts[0].severity == "warning"
        assert "50%" in alerts[0].message

    def test_generate_repo_alerts_multiple(
        self, service: WorkflowMetricsService
    ) -> None:
        """_generate_repo_alerts can generate multiple alerts."""
        repo_metric = RepoWorkflowMetrics(
            repo_id=uuid4(),
            repo_name="owner/repo",
            tier="execute",
            counts=WorkflowCounts(completed=3, failed=7),
            pass_rate_24h=0.3,
            has_elevated_failure_rate=True,
            stuck_workflow_ids=["wf-1"],
        )

        alerts = service._generate_repo_alerts(repo_metric)

        assert len(alerts) == 2
        alert_types = {a.alert_type for a in alerts}
        assert "stuck_workflows" in alert_types
        assert "elevated_failure_rate" in alert_types

    def test_generate_repo_alerts_no_issues(
        self, service: WorkflowMetricsService
    ) -> None:
        """_generate_repo_alerts returns empty list when no issues."""
        repo_metric = RepoWorkflowMetrics(
            repo_id=uuid4(),
            repo_name="owner/repo",
            tier="observe",
            counts=WorkflowCounts(completed=10, failed=0),
            pass_rate_24h=1.0,
            has_elevated_failure_rate=False,
            stuck_workflow_ids=[],
        )

        alerts = service._generate_repo_alerts(repo_metric)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_list_workflows_handles_exception(
        self, service: WorkflowMetricsService
    ) -> None:
        """_list_workflows handles exceptions gracefully."""
        mock_client = MagicMock()

        async def raise_error(_query: str):
            raise RuntimeError("Connection failed")
            yield  # Make it an async generator

        mock_client.list_workflows = raise_error

        from temporalio.client import WorkflowExecutionStatus

        result = await service._list_workflows(
            mock_client, WorkflowExecutionStatus.RUNNING
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_queue_depth_handles_exception(
        self, service: WorkflowMetricsService
    ) -> None:
        """_get_queue_depth returns 0 on exception."""
        mock_client = AsyncMock()
        mock_client.get_worker_task_reachability.side_effect = RuntimeError("Failed")

        result = await service._get_queue_depth(mock_client)

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_metrics_empty_repos(
        self, service: WorkflowMetricsService
    ) -> None:
        """get_metrics handles case with no repos."""
        mock_session = AsyncMock()

        with patch.object(service, "_get_client") as mock_get_client, patch.object(
            service, "_get_repos"
        ) as mock_get_repos, patch.object(
            service, "_get_queue_depth"
        ) as mock_queue_depth:
            mock_get_client.return_value = AsyncMock()
            mock_get_repos.return_value = []
            mock_queue_depth.return_value = 0

            result = await service.get_metrics(mock_session)

        assert result.aggregate.running == 0
        assert result.aggregate.stuck == 0
        assert result.aggregate.failed == 0
        assert result.aggregate.completed == 0
        assert result.repos == []
        assert result.alerts == []

    @pytest.mark.asyncio
    async def test_get_metrics_with_repo_filter(
        self, service: WorkflowMetricsService
    ) -> None:
        """get_metrics filters by repo_id when provided."""
        mock_session = AsyncMock()
        repo_id = uuid4()

        with patch.object(service, "_get_client") as mock_get_client, patch.object(
            service, "_get_repos"
        ) as mock_get_repos, patch.object(
            service, "_get_repo_metrics"
        ) as mock_repo_metrics, patch.object(
            service, "_get_queue_depth"
        ) as mock_queue_depth:
            mock_get_client.return_value = AsyncMock()
            mock_get_repos.return_value = [
                {"id": repo_id, "full_name": "owner/repo", "tier": "execute"}
            ]
            mock_repo_metrics.return_value = RepoWorkflowMetrics(
                repo_id=repo_id,
                repo_name="owner/repo",
                tier="execute",
            )
            mock_queue_depth.return_value = 5

            result = await service.get_metrics(mock_session, repo_id)

        mock_get_repos.assert_called_once_with(mock_session, repo_id)
        assert len(result.repos) == 1
        assert result.repos[0].repo_id == repo_id

    @pytest.mark.asyncio
    async def test_close(self, service: WorkflowMetricsService) -> None:
        """close cleans up Temporal client."""
        mock_client = AsyncMock()
        service._client = mock_client

        await service.close()

        mock_client.close.assert_called_once()
        assert service._client is None


class TestWorkflowMetricsIntegration:
    """Integration-style tests for workflow metrics calculation."""

    @pytest.mark.asyncio
    async def test_stuck_workflow_detection(self) -> None:
        """Workflows older than threshold are marked stuck."""
        service = WorkflowMetricsService(stuck_threshold_hours=2)
        mock_client = MagicMock()

        now = datetime.now(UTC)
        old_wf = MagicMock()
        old_wf.id = "wf-owner-repo-old"
        old_wf.start_time = now - timedelta(hours=3)

        recent_wf = MagicMock()
        recent_wf.id = "wf-owner-repo-recent"
        recent_wf.start_time = now - timedelta(minutes=30)

        repo_info = {
            "id": uuid4(),
            "full_name": "owner/repo",
            "tier": "execute",
        }

        async def mock_list_workflows(query: str):
            if "RUNNING" in query:
                for wf in [old_wf, recent_wf]:
                    yield wf
            else:
                return

        mock_client.list_workflows = mock_list_workflows

        result = await service._get_repo_metrics(
            mock_client,
            repo_info,
            stuck_threshold=timedelta(hours=2),
            checked_at=now,
        )

        assert result.counts.running == 2
        assert result.counts.stuck == 1
        assert "wf-owner-repo-old" in result.stuck_workflow_ids
        assert "wf-owner-repo-recent" not in result.stuck_workflow_ids

    @pytest.mark.asyncio
    async def test_pass_rate_calculation(self) -> None:
        """24h pass rate is calculated correctly."""
        service = WorkflowMetricsService()
        mock_client = MagicMock()

        now = datetime.now(UTC)

        completed_wfs = [
            MagicMock(id=f"wf-owner-repo-completed-{i}")
            for i in range(8)
        ]
        failed_wfs = [
            MagicMock(id=f"wf-owner-repo-failed-{i}")
            for i in range(2)
        ]

        repo_info = {
            "id": uuid4(),
            "full_name": "owner/repo",
            "tier": "execute",
        }

        async def mock_list_workflows(query: str):
            if "COMPLETED" in query:
                for wf in completed_wfs:
                    yield wf
            elif "FAILED" in query:
                for wf in failed_wfs:
                    yield wf
            else:
                return

        mock_client.list_workflows = mock_list_workflows

        result = await service._get_repo_metrics(
            mock_client,
            repo_info,
            stuck_threshold=timedelta(hours=2),
            checked_at=now,
        )

        assert result.counts.completed == 8
        assert result.counts.failed == 2
        assert result.pass_rate_24h == pytest.approx(0.8, rel=0.01)

    @pytest.mark.asyncio
    async def test_elevated_failure_rate_threshold(self) -> None:
        """Elevated failure rate flag is set correctly."""
        service = WorkflowMetricsService(failure_rate_threshold=0.3)
        mock_client = MagicMock()

        now = datetime.now(UTC)

        completed_wfs = [MagicMock(id=f"wf-owner-repo-c-{i}") for i in range(5)]
        failed_wfs = [MagicMock(id=f"wf-owner-repo-f-{i}") for i in range(5)]

        repo_info = {
            "id": uuid4(),
            "full_name": "owner/repo",
            "tier": "execute",
        }

        async def mock_list_workflows(query: str):
            if "COMPLETED" in query:
                for wf in completed_wfs:
                    yield wf
            elif "FAILED" in query:
                for wf in failed_wfs:
                    yield wf
            else:
                return

        mock_client.list_workflows = mock_list_workflows

        result = await service._get_repo_metrics(
            mock_client,
            repo_info,
            stuck_threshold=timedelta(hours=2),
            checked_at=now,
        )

        assert result.has_elevated_failure_rate is True
