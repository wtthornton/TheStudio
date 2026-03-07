"""Workflow metrics service for Admin UI Fleet Dashboard.

Story 4.3: Fleet Dashboard API — Workflow Metrics.
Architecture reference: thestudioarc/23-admin-control-ui.md (Fleet Dashboard mockup)

Provides:
- Aggregate workflow metrics (running, stuck, failed, queue_depth)
- Per-repo workflow metrics
- 24h pass rate calculation
- Hot alerts (elevated failure rates, stuck workflows)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from temporalio.client import Client, WorkflowExecutionStatus

from src.observability.tracing import get_tracer
from src.settings import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.admin.workflow_metrics")

DEFAULT_STUCK_THRESHOLD_HOURS = 2
DEFAULT_ALERT_FAILURE_RATE_THRESHOLD = 0.3


@dataclass
class WorkflowCounts:
    """Aggregate workflow counts."""

    running: int = 0
    stuck: int = 0
    failed: int = 0
    completed: int = 0


@dataclass
class RepoWorkflowMetrics:
    """Per-repo workflow metrics."""

    repo_id: UUID
    repo_name: str
    tier: str
    counts: WorkflowCounts = field(default_factory=WorkflowCounts)
    queue_depth: int = 0
    pass_rate_24h: float = 0.0
    has_elevated_failure_rate: bool = False
    stuck_workflow_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "repo_id": str(self.repo_id),
            "repo_name": self.repo_name,
            "tier": self.tier,
            "running": self.counts.running,
            "stuck": self.counts.stuck,
            "failed": self.counts.failed,
            "completed": self.counts.completed,
            "queue_depth": self.queue_depth,
            "pass_rate_24h": round(self.pass_rate_24h * 100, 1),
            "has_elevated_failure_rate": self.has_elevated_failure_rate,
            "stuck_workflow_ids": self.stuck_workflow_ids,
        }


@dataclass
class HotAlert:
    """Alert for operational issues requiring attention."""

    alert_type: str
    severity: str
    repo_name: str
    message: str
    workflow_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "repo_name": self.repo_name,
            "message": self.message,
            "workflow_ids": self.workflow_ids,
            "details": self.details,
        }


@dataclass
class WorkflowMetricsResponse:
    """Full workflow metrics response."""

    aggregate: WorkflowCounts
    queue_depth: int
    pass_rate_24h: float
    repos: list[RepoWorkflowMetrics]
    alerts: list[HotAlert]
    checked_at: datetime
    stuck_threshold_hours: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "aggregate": {
                "running": self.aggregate.running,
                "stuck": self.aggregate.stuck,
                "failed": self.aggregate.failed,
                "completed": self.aggregate.completed,
            },
            "queue_depth": self.queue_depth,
            "pass_rate_24h": round(self.pass_rate_24h * 100, 1),
            "repos": [r.to_dict() for r in self.repos],
            "alerts": [a.to_dict() for a in self.alerts],
            "checked_at": self.checked_at.isoformat(),
            "stuck_threshold_hours": self.stuck_threshold_hours,
        }


class WorkflowMetricsService:
    """Service for querying workflow metrics from Temporal.

    Usage:
        service = WorkflowMetricsService()
        metrics = await service.get_metrics(session)
    """

    def __init__(
        self,
        temporal_host: str | None = None,
        namespace: str | None = None,
        task_queue: str | None = None,
        stuck_threshold_hours: int = DEFAULT_STUCK_THRESHOLD_HOURS,
        failure_rate_threshold: float = DEFAULT_ALERT_FAILURE_RATE_THRESHOLD,
    ) -> None:
        """Initialize workflow metrics service.

        Args:
            temporal_host: Temporal server host:port. Defaults to settings.
            namespace: Temporal namespace. Defaults to settings.
            task_queue: Task queue name. Defaults to settings.
            stuck_threshold_hours: Hours before a workflow is considered stuck.
            failure_rate_threshold: Failure rate above which to trigger alert.
        """
        self._temporal_host = temporal_host or settings.temporal_host
        self._namespace = namespace or settings.temporal_namespace
        self._task_queue = task_queue or settings.temporal_task_queue
        self._stuck_threshold_hours = stuck_threshold_hours
        self._failure_rate_threshold = failure_rate_threshold
        self._client: Client | None = None

    async def _get_client(self) -> Client:
        """Get or create Temporal client."""
        if self._client is None:
            self._client = await Client.connect(
                self._temporal_host,
                namespace=self._namespace,
            )
        return self._client

    async def get_metrics(
        self,
        session: AsyncSession,
        repo_id: UUID | None = None,
    ) -> WorkflowMetricsResponse:
        """Get workflow metrics, optionally filtered by repo.

        Args:
            session: Database session for repo lookups.
            repo_id: Optional repo ID to filter metrics.

        Returns:
            WorkflowMetricsResponse with aggregate and per-repo metrics.
        """
        with tracer.start_as_current_span("workflow_metrics.get_metrics") as span:
            if repo_id:
                span.set_attribute("thestudio.metrics.repo_id", str(repo_id))

            client = await self._get_client()
            checked_at = datetime.now(UTC)
            stuck_threshold = timedelta(hours=self._stuck_threshold_hours)

            repos_data = await self._get_repos(session, repo_id)

            aggregate = WorkflowCounts()
            repo_metrics: list[RepoWorkflowMetrics] = []
            alerts: list[HotAlert] = []

            for repo_info in repos_data:
                repo_metric = await self._get_repo_metrics(
                    client,
                    repo_info,
                    stuck_threshold,
                    checked_at,
                )
                repo_metrics.append(repo_metric)

                aggregate.running += repo_metric.counts.running
                aggregate.stuck += repo_metric.counts.stuck
                aggregate.failed += repo_metric.counts.failed
                aggregate.completed += repo_metric.counts.completed

                repo_alerts = self._generate_repo_alerts(repo_metric)
                alerts.extend(repo_alerts)

            queue_depth = await self._get_queue_depth(client)

            total_workflows = aggregate.completed + aggregate.failed
            pass_rate = (
                aggregate.completed / total_workflows if total_workflows > 0 else 0.0
            )

            span.set_attribute("thestudio.metrics.running", aggregate.running)
            span.set_attribute("thestudio.metrics.stuck", aggregate.stuck)
            span.set_attribute("thestudio.metrics.alerts", len(alerts))

            return WorkflowMetricsResponse(
                aggregate=aggregate,
                queue_depth=queue_depth,
                pass_rate_24h=pass_rate,
                repos=repo_metrics,
                alerts=alerts,
                checked_at=checked_at,
                stuck_threshold_hours=self._stuck_threshold_hours,
            )

    async def _get_repos(
        self,
        session: AsyncSession,
        repo_id: UUID | None,
    ) -> list[dict[str, Any]]:
        """Get repo information from database."""
        from src.repo.repository import RepoRepository

        repo_repository = RepoRepository()

        if repo_id is not None:
            repo = await repo_repository.get(session, repo_id)
            if repo is None:
                return []
            return [
                {
                    "id": repo.id,
                    "full_name": repo.full_name,
                    "tier": repo.tier.value,
                }
            ]

        repos = await repo_repository.list_all(session)
        return [
            {
                "id": repo.id,
                "full_name": repo.full_name,
                "tier": repo.tier.value,
            }
            for repo in repos
        ]

    async def _get_repo_metrics(
        self,
        client: Client,
        repo_info: dict[str, Any],
        stuck_threshold: timedelta,
        checked_at: datetime,
    ) -> RepoWorkflowMetrics:
        """Get metrics for a single repo."""
        repo_name = repo_info["full_name"]
        counts = WorkflowCounts()
        stuck_workflow_ids: list[str] = []
        completed_24h = 0
        failed_24h = 0

        cutoff_24h = checked_at - timedelta(hours=24)
        stuck_cutoff = checked_at - stuck_threshold

        running_workflows = await self._list_workflows(
            client,
            status=WorkflowExecutionStatus.RUNNING,
        )

        for wf in running_workflows:
            if not self._matches_repo(wf, repo_name):
                continue

            counts.running += 1

            if wf.start_time and wf.start_time < stuck_cutoff:
                counts.stuck += 1
                stuck_workflow_ids.append(wf.id)

        completed_workflows = await self._list_workflows(
            client,
            status=WorkflowExecutionStatus.COMPLETED,
            start_time_after=cutoff_24h,
        )

        for wf in completed_workflows:
            if self._matches_repo(wf, repo_name):
                counts.completed += 1
                completed_24h += 1

        failed_workflows = await self._list_workflows(
            client,
            status=WorkflowExecutionStatus.FAILED,
            start_time_after=cutoff_24h,
        )

        for wf in failed_workflows:
            if self._matches_repo(wf, repo_name):
                counts.failed += 1
                failed_24h += 1

        total_24h = completed_24h + failed_24h
        pass_rate_24h = completed_24h / total_24h if total_24h > 0 else 0.0

        has_elevated_failure_rate = (
            total_24h >= 3 and (1 - pass_rate_24h) > self._failure_rate_threshold
        )

        return RepoWorkflowMetrics(
            repo_id=repo_info["id"],
            repo_name=repo_name,
            tier=repo_info["tier"],
            counts=counts,
            queue_depth=0,
            pass_rate_24h=pass_rate_24h,
            has_elevated_failure_rate=has_elevated_failure_rate,
            stuck_workflow_ids=stuck_workflow_ids,
        )

    async def _list_workflows(
        self,
        client: Client,
        status: WorkflowExecutionStatus,
        start_time_after: datetime | None = None,
    ) -> list[Any]:
        """List workflows with given status."""
        query_parts = [f"ExecutionStatus = '{status.name}'"]

        if start_time_after:
            timestamp = start_time_after.strftime("%Y-%m-%dT%H:%M:%SZ")
            query_parts.append(f"StartTime >= '{timestamp}'")

        query = " AND ".join(query_parts)

        workflows = []
        try:
            async for wf in client.list_workflows(query):
                workflows.append(wf)
        except Exception as e:
            logger.warning("Failed to list workflows: %s", e)

        return workflows

    def _matches_repo(self, workflow: Any, repo_name: str) -> bool:
        """Check if workflow belongs to repo.

        Workflow IDs are expected to contain the repo name or
        be prefixed with repo-related information.
        """
        wf_id = workflow.id
        normalized_repo = repo_name.replace("/", "-").lower()
        normalized_id = wf_id.lower()

        return normalized_repo in normalized_id or repo_name.lower() in normalized_id

    async def _get_queue_depth(self, client: Client) -> int:
        """Get task queue depth from Temporal."""
        try:
            queue_info = await client.get_worker_task_reachability(
                build_ids=[],
                task_queues=[self._task_queue],
            )
            _ = queue_info
            return 0
        except Exception as e:
            logger.warning("Failed to get queue depth: %s", e)
            return 0

    def _generate_repo_alerts(
        self,
        repo_metric: RepoWorkflowMetrics,
    ) -> list[HotAlert]:
        """Generate alerts for a repo based on its metrics."""
        alerts: list[HotAlert] = []

        if repo_metric.stuck_workflow_ids:
            alerts.append(
                HotAlert(
                    alert_type="stuck_workflows",
                    severity="warning",
                    repo_name=repo_metric.repo_name,
                    message=(
                        f"{len(repo_metric.stuck_workflow_ids)} workflow(s) stuck "
                        f"> {self._stuck_threshold_hours}h"
                    ),
                    workflow_ids=repo_metric.stuck_workflow_ids,
                    details={"threshold_hours": self._stuck_threshold_hours},
                )
            )

        if repo_metric.has_elevated_failure_rate:
            failure_rate = 1 - repo_metric.pass_rate_24h
            alerts.append(
                HotAlert(
                    alert_type="elevated_failure_rate",
                    severity="warning",
                    repo_name=repo_metric.repo_name,
                    message=(
                        f"Failure rate {failure_rate:.0%} exceeds threshold "
                        f"({self._failure_rate_threshold:.0%})"
                    ),
                    details={
                        "failure_rate": round(failure_rate * 100, 1),
                        "threshold": round(self._failure_rate_threshold * 100, 1),
                        "failed_count": repo_metric.counts.failed,
                        "total_count": (
                            repo_metric.counts.completed + repo_metric.counts.failed
                        ),
                    },
                )
            )

        return alerts

    async def close(self) -> None:
        """Close the Temporal client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
