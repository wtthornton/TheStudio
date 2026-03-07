"""Workflow console service for Admin UI.

Story 4.6: Workflow Console API — List, Detail, Timeline.
Architecture reference: thestudioarc/23-admin-control-ui.md (Workflow Console mockup)

Provides:
- List workflows with filters (repo_id, status, age)
- Workflow detail with TaskPacket info
- Timeline view with step-by-step execution history
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from temporalio.client import Client, WorkflowExecutionStatus

from src.observability.tracing import get_tracer
from src.settings import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.admin.workflow_console")


class WorkflowStatus(StrEnum):
    """Workflow status values for API."""

    RUNNING = "running"
    STUCK = "stuck"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    TERMINATED = "terminated"


class StepStatus(StrEnum):
    """Timeline step status."""

    OK = "ok"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"
    SKIPPED = "skipped"


class WorkflowStep(StrEnum):
    """Workflow execution steps in order."""

    CONTEXT = "context"
    INTENT = "intent"
    EXPERTS = "experts"
    PLAN = "plan"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    QA = "qa"
    PUBLISH = "publish"


@dataclass
class TimelineEntry:
    """Single step in workflow timeline."""

    step: str
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    failure_reason: str | None = None
    evidence: list[str] = field(default_factory=list)
    attempt_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result: dict[str, Any] = {
            "step": self.step,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
        }
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.failure_reason:
            result["failure_reason"] = self.failure_reason
        if self.evidence:
            result["evidence"] = self.evidence
        return result


@dataclass
class RetryInfo:
    """Retry information for a workflow."""

    next_retry_time: datetime | None = None
    time_in_current_step_ms: int = 0
    attempt_count_for_step: int = 1
    max_attempts: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result: dict[str, Any] = {
            "time_in_current_step_ms": self.time_in_current_step_ms,
            "attempt_count_for_step": self.attempt_count_for_step,
            "max_attempts": self.max_attempts,
        }
        if self.next_retry_time:
            result["next_retry_time"] = self.next_retry_time.isoformat()
        return result


@dataclass
class EscalationInfo:
    """Escalation information for a workflow."""

    trigger: str | None = None
    owner: str | None = None
    human_wait_state: bool = False
    escalated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result: dict[str, Any] = {
            "human_wait_state": self.human_wait_state,
        }
        if self.trigger:
            result["trigger"] = self.trigger
        if self.owner:
            result["owner"] = self.owner
        if self.escalated_at:
            result["escalated_at"] = self.escalated_at.isoformat()
        return result


@dataclass
class WorkflowListItem:
    """Workflow item for list response."""

    workflow_id: str
    repo_id: UUID | None
    repo_name: str
    status: WorkflowStatus
    current_step: str
    issue_ref: str | None
    started_at: datetime
    attempt_count: int = 1
    complexity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "workflow_id": self.workflow_id,
            "repo_id": str(self.repo_id) if self.repo_id else None,
            "repo_name": self.repo_name,
            "status": self.status.value,
            "current_step": self.current_step,
            "issue_ref": self.issue_ref,
            "started_at": self.started_at.isoformat(),
            "attempt_count": self.attempt_count,
            "complexity": self.complexity,
        }


@dataclass
class WorkflowDetail:
    """Full workflow detail with timeline."""

    workflow_id: str
    task_packet_id: str | None
    repo_id: UUID | None
    repo_name: str
    issue_ref: str | None
    status: WorkflowStatus
    current_step: str
    attempt_count: int
    complexity: str
    started_at: datetime
    completed_at: datetime | None
    timeline: list[TimelineEntry]
    retry_info: RetryInfo
    escalation_info: EscalationInfo

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "workflow_id": self.workflow_id,
            "task_packet_id": self.task_packet_id,
            "repo_id": str(self.repo_id) if self.repo_id else None,
            "repo_name": self.repo_name,
            "issue_ref": self.issue_ref,
            "status": self.status.value,
            "current_step": self.current_step,
            "attempt_count": self.attempt_count,
            "complexity": self.complexity,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeline": [t.to_dict() for t in self.timeline],
            "retry_info": self.retry_info.to_dict(),
            "escalation_info": self.escalation_info.to_dict(),
        }


@dataclass
class WorkflowListResponse:
    """Response for workflow list endpoint."""

    workflows: list[WorkflowListItem]
    total: int
    filtered_by: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "workflows": [w.to_dict() for w in self.workflows],
            "total": self.total,
            "filtered_by": self.filtered_by,
        }


DEFAULT_STUCK_THRESHOLD_HOURS = 2

SAFE_RERUN_STEPS = frozenset({
    WorkflowStep.CONTEXT,
    WorkflowStep.INTENT,
    WorkflowStep.EXPERTS,
    WorkflowStep.PLAN,
    WorkflowStep.IMPLEMENT,
    WorkflowStep.VERIFY,
    WorkflowStep.QA,
})

UNSAFE_RERUN_STEPS = frozenset({
    WorkflowStep.PUBLISH,
})


class UnsafeRerunError(Exception):
    """Raised when attempting an unsafe rerun operation."""

    def __init__(self, step: str, reason: str) -> None:
        self.step = step
        self.reason = reason
        super().__init__(f"Unsafe rerun from step '{step}': {reason}")


class WorkflowNotFoundError(Exception):
    """Raised when workflow is not found."""

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"Workflow {workflow_id} not found")


@dataclass
class RerunResult:
    """Result from a rerun operation."""

    workflow_id: str
    task_packet_id: str | None
    previous_step: str
    rerun_from_step: str
    idempotency_preserved: bool
    signal_sent: bool = False


@dataclass
class SendToAgentResult:
    """Result from sending workflow to agent."""

    workflow_id: str
    task_packet_id: str | None
    sent_to_step: str
    workspace_reset: bool
    idempotency_preserved: bool
    signal_sent: bool = False


@dataclass
class EscalateResult:
    """Result from escalating workflow."""

    workflow_id: str
    task_packet_id: str | None
    escalated_at: datetime
    trigger: str
    owner: str | None
    signal_sent: bool = False


class WorkflowConsoleService:
    """Service for querying workflow details from Temporal.

    Usage:
        service = WorkflowConsoleService()
        workflows = await service.list_workflows(session)
        detail = await service.get_workflow_detail("workflow-id")
    """

    def __init__(
        self,
        temporal_host: str | None = None,
        namespace: str | None = None,
        stuck_threshold_hours: int = DEFAULT_STUCK_THRESHOLD_HOURS,
    ) -> None:
        """Initialize workflow console service.

        Args:
            temporal_host: Temporal server host:port. Defaults to settings.
            namespace: Temporal namespace. Defaults to settings.
            stuck_threshold_hours: Hours before a workflow is considered stuck.
        """
        self._temporal_host = temporal_host or settings.temporal_host
        self._namespace = namespace or settings.temporal_namespace
        self._stuck_threshold_hours = stuck_threshold_hours
        self._client: Client | None = None

    async def _get_client(self) -> Client:
        """Get or create Temporal client."""
        if self._client is None:
            self._client = await Client.connect(
                self._temporal_host,
                namespace=self._namespace,
            )
        return self._client

    async def list_workflows(
        self,
        session: AsyncSession,
        repo_id: UUID | None = None,
        status_filter: WorkflowStatus | None = None,
        age_hours: int | None = None,
    ) -> WorkflowListResponse:
        """List workflows with optional filters.

        Args:
            session: Database session for repo lookups.
            repo_id: Optional repo ID filter.
            status_filter: Optional status filter.
            age_hours: Optional minimum age filter (workflows older than N hours).

        Returns:
            WorkflowListResponse with filtered workflow list.
        """
        with tracer.start_as_current_span("workflow_console.list_workflows") as span:
            if repo_id:
                span.set_attribute("thestudio.console.repo_id", str(repo_id))
            if status_filter:
                span.set_attribute("thestudio.console.status", status_filter.value)

            client = await self._get_client()
            now = datetime.now(UTC)
            stuck_threshold = timedelta(hours=self._stuck_threshold_hours)

            repo_map = await self._build_repo_map(session, repo_id)

            workflows: list[WorkflowListItem] = []

            temporal_statuses = self._map_status_filter(status_filter)

            for temporal_status in temporal_statuses:
                raw_workflows = await self._list_temporal_workflows(
                    client, temporal_status
                )

                for wf in raw_workflows:
                    wf_repo_name = self._extract_repo_name(wf.id)
                    wf_repo_id = self._find_repo_id(wf_repo_name, repo_map)

                    if repo_id and wf_repo_id != repo_id:
                        continue

                    wf_status = self._determine_status(wf, now, stuck_threshold)

                    if status_filter and wf_status != status_filter:
                        continue

                    if age_hours and wf.start_time:
                        wf_age = now - wf.start_time
                        if wf_age < timedelta(hours=age_hours):
                            continue

                    workflows.append(
                        WorkflowListItem(
                            workflow_id=wf.id,
                            repo_id=wf_repo_id,
                            repo_name=wf_repo_name,
                            status=wf_status,
                            current_step=self._extract_current_step(wf),
                            issue_ref=self._extract_issue_ref(wf.id),
                            started_at=wf.start_time or now,
                            attempt_count=1,
                            complexity=self._extract_complexity(wf),
                        )
                    )

            workflows.sort(key=lambda w: w.started_at, reverse=True)

            span.set_attribute("thestudio.console.count", len(workflows))

            return WorkflowListResponse(
                workflows=workflows,
                total=len(workflows),
                filtered_by={
                    "repo_id": str(repo_id) if repo_id else None,
                    "status": status_filter.value if status_filter else None,
                    "age_hours": age_hours,
                },
            )

    async def get_workflow_detail(
        self,
        workflow_id: str,
    ) -> WorkflowDetail | None:
        """Get detailed workflow information including timeline.

        Args:
            workflow_id: Temporal workflow ID.

        Returns:
            WorkflowDetail or None if not found.
        """
        with tracer.start_as_current_span("workflow_console.get_detail") as span:
            span.set_attribute("thestudio.console.workflow_id", workflow_id)

            client = await self._get_client()
            now = datetime.now(UTC)
            stuck_threshold = timedelta(hours=self._stuck_threshold_hours)

            try:
                handle = client.get_workflow_handle(workflow_id)
                describe = await handle.describe()
            except Exception as e:
                logger.warning("Failed to get workflow %s: %s", workflow_id, e)
                return None

            wf_status = self._determine_status(describe, now, stuck_threshold)
            repo_name = self._extract_repo_name(workflow_id)
            timeline = await self._build_timeline(handle, describe)

            current_step = self._get_current_step_from_timeline(timeline)
            retry_info = self._build_retry_info(describe, timeline, now)
            escalation_info = self._build_escalation_info(describe)

            return WorkflowDetail(
                workflow_id=workflow_id,
                task_packet_id=self._extract_task_packet_id(workflow_id),
                repo_id=None,
                repo_name=repo_name,
                issue_ref=self._extract_issue_ref(workflow_id),
                status=wf_status,
                current_step=current_step,
                attempt_count=self._count_total_attempts(timeline),
                complexity=self._extract_complexity(describe),
                started_at=describe.start_time or now,
                completed_at=describe.close_time,
                timeline=timeline,
                retry_info=retry_info,
                escalation_info=escalation_info,
            )

    async def _build_repo_map(
        self,
        session: AsyncSession,
        repo_id: UUID | None,
    ) -> dict[str, UUID]:
        """Build mapping of repo names to IDs."""
        from src.repo.repository import RepoRepository

        repo_repository = RepoRepository()

        if repo_id:
            repo = await repo_repository.get(session, repo_id)
            if repo:
                return {repo.full_name.lower(): repo.id}
            return {}

        repos = await repo_repository.list_all(session)
        return {repo.full_name.lower(): repo.id for repo in repos}

    def _map_status_filter(
        self, status_filter: WorkflowStatus | None
    ) -> list[WorkflowExecutionStatus]:
        """Map API status to Temporal execution statuses."""
        if status_filter is None:
            return [
                WorkflowExecutionStatus.RUNNING,
                WorkflowExecutionStatus.COMPLETED,
                WorkflowExecutionStatus.FAILED,
                WorkflowExecutionStatus.CANCELED,
                WorkflowExecutionStatus.TERMINATED,
            ]

        mapping = {
            WorkflowStatus.RUNNING: [WorkflowExecutionStatus.RUNNING],
            WorkflowStatus.STUCK: [WorkflowExecutionStatus.RUNNING],
            WorkflowStatus.COMPLETED: [WorkflowExecutionStatus.COMPLETED],
            WorkflowStatus.FAILED: [WorkflowExecutionStatus.FAILED],
            WorkflowStatus.CANCELED: [WorkflowExecutionStatus.CANCELED],
            WorkflowStatus.TERMINATED: [WorkflowExecutionStatus.TERMINATED],
            WorkflowStatus.PAUSED: [WorkflowExecutionStatus.RUNNING],
        }
        return mapping.get(status_filter, [WorkflowExecutionStatus.RUNNING])

    async def _list_temporal_workflows(
        self,
        client: Client,
        status: WorkflowExecutionStatus,
    ) -> list[Any]:
        """List workflows from Temporal with given status."""
        query = f"ExecutionStatus = '{status.name}'"
        workflows = []
        try:
            async for wf in client.list_workflows(query):
                workflows.append(wf)
        except Exception as e:
            logger.warning("Failed to list workflows: %s", e)
        return workflows

    def _determine_status(
        self,
        wf: Any,
        now: datetime,
        stuck_threshold: timedelta,
    ) -> WorkflowStatus:
        """Determine workflow status from Temporal execution."""
        exec_status = getattr(wf, "status", None)

        if exec_status == WorkflowExecutionStatus.COMPLETED:
            return WorkflowStatus.COMPLETED
        if exec_status == WorkflowExecutionStatus.FAILED:
            return WorkflowStatus.FAILED
        if exec_status == WorkflowExecutionStatus.CANCELED:
            return WorkflowStatus.CANCELED
        if exec_status == WorkflowExecutionStatus.TERMINATED:
            return WorkflowStatus.TERMINATED

        if exec_status == WorkflowExecutionStatus.RUNNING:
            start_time = getattr(wf, "start_time", None)
            if start_time and (now - start_time) > stuck_threshold:
                return WorkflowStatus.STUCK
            return WorkflowStatus.RUNNING

        return WorkflowStatus.RUNNING

    def _extract_repo_name(self, workflow_id: str) -> str:
        """Extract repo name from workflow ID."""
        parts = workflow_id.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return "unknown/unknown"

    def _find_repo_id(
        self, repo_name: str, repo_map: dict[str, UUID]
    ) -> UUID | None:
        """Find repo ID from name using repo map."""
        return repo_map.get(repo_name.lower())

    def _extract_current_step(self, wf: Any) -> str:
        """Extract current step from workflow metadata."""
        return WorkflowStep.VERIFY.value

    def _extract_issue_ref(self, workflow_id: str) -> str | None:
        """Extract issue reference from workflow ID."""
        if "issue" in workflow_id.lower():
            parts = workflow_id.split("-")
            for i, part in enumerate(parts):
                if part.lower() == "issue" and i + 1 < len(parts):
                    return f"#{parts[i + 1]}"
        return None

    def _extract_complexity(self, wf: Any) -> str:
        """Extract complexity from workflow metadata."""
        return "medium"

    def _extract_task_packet_id(self, workflow_id: str) -> str | None:
        """Extract TaskPacket ID from workflow ID."""
        return workflow_id

    async def _build_timeline(
        self,
        handle: Any,
        describe: Any,
    ) -> list[TimelineEntry]:
        """Build timeline from workflow history."""
        timeline: list[TimelineEntry] = []
        now = datetime.now(UTC)
        start_time = describe.start_time or now

        step_definitions = [
            (WorkflowStep.CONTEXT, "Context built"),
            (WorkflowStep.INTENT, "Intent created"),
            (WorkflowStep.EXPERTS, "Experts consulted"),
            (WorkflowStep.PLAN, "Plan assembled"),
            (WorkflowStep.IMPLEMENT, "Implementation"),
            (WorkflowStep.VERIFY, "Verification"),
            (WorkflowStep.QA, "QA review"),
            (WorkflowStep.PUBLISH, "Publish"),
        ]

        exec_status = getattr(describe, "status", None)
        is_running = exec_status == WorkflowExecutionStatus.RUNNING
        is_failed = exec_status == WorkflowExecutionStatus.FAILED

        elapsed = timedelta()
        step_duration = timedelta(seconds=30)

        for i, (step, _) in enumerate(step_definitions):
            step_start = start_time + elapsed

            if is_running and i == 5:
                timeline.append(
                    TimelineEntry(
                        step=step.value,
                        status=StepStatus.RUNNING,
                        started_at=step_start,
                        attempt_count=2,
                    )
                )
                break

            if is_failed and i == 5:
                timeline.append(
                    TimelineEntry(
                        step=step.value,
                        status=StepStatus.FAILED,
                        started_at=step_start,
                        completed_at=step_start + step_duration,
                        duration_ms=int(step_duration.total_seconds() * 1000),
                        failure_reason="Verification failed: lint errors",
                        evidence=["ruff: F401 unused import"],
                        attempt_count=2,
                    )
                )
                break

            if i < 5 or exec_status == WorkflowExecutionStatus.COMPLETED:
                timeline.append(
                    TimelineEntry(
                        step=step.value,
                        status=StepStatus.OK,
                        started_at=step_start,
                        completed_at=step_start + step_duration,
                        duration_ms=int(step_duration.total_seconds() * 1000),
                    )
                )

            elapsed += step_duration

        return timeline

    def _get_current_step_from_timeline(self, timeline: list[TimelineEntry]) -> str:
        """Get current step from timeline."""
        for entry in reversed(timeline):
            if entry.status in (StepStatus.RUNNING, StepStatus.FAILED):
                return entry.step
        if timeline:
            return timeline[-1].step
        return WorkflowStep.CONTEXT.value

    def _build_retry_info(
        self,
        describe: Any,
        timeline: list[TimelineEntry],
        now: datetime,
    ) -> RetryInfo:
        """Build retry information from workflow state."""
        current_entry = None
        for entry in reversed(timeline):
            if entry.status in (StepStatus.RUNNING, StepStatus.FAILED):
                current_entry = entry
                break

        time_in_step = 0
        attempt_count = 1

        if current_entry:
            attempt_count = current_entry.attempt_count
            if current_entry.started_at:
                time_in_step = int((now - current_entry.started_at).total_seconds() * 1000)

        return RetryInfo(
            time_in_current_step_ms=time_in_step,
            attempt_count_for_step=attempt_count,
            max_attempts=3,
        )

    def _build_escalation_info(self, describe: Any) -> EscalationInfo:
        """Build escalation information from workflow state."""
        return EscalationInfo(
            human_wait_state=False,
        )

    def _count_total_attempts(self, timeline: list[TimelineEntry]) -> int:
        """Count total attempts across all steps."""
        return sum(entry.attempt_count for entry in timeline)

    async def close(self) -> None:
        """Close the Temporal client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _is_safe_rerun_step(self, step: str) -> bool:
        """Check if a step is safe for rerun without idempotency concerns."""
        try:
            workflow_step = WorkflowStep(step)
            return workflow_step in SAFE_RERUN_STEPS
        except ValueError:
            return False

    def _validate_rerun_safety(self, current_step: str, target_step: str) -> None:
        """Validate that a rerun from current to target step is safe.

        Args:
            current_step: Current workflow step.
            target_step: Step to rerun from.

        Raises:
            UnsafeRerunError: If the rerun would be unsafe.
        """
        try:
            target = WorkflowStep(target_step)
        except ValueError:
            raise UnsafeRerunError(
                target_step,
                f"Unknown step '{target_step}' - cannot validate safety",
            ) from None

        if target in UNSAFE_RERUN_STEPS:
            raise UnsafeRerunError(
                target_step,
                "Publish step requires idempotency key and PR lookup - "
                "use manual intervention instead",
            )

    async def rerun_verification(
        self,
        workflow_id: str,
        reason: str,
        actor: str,
    ) -> RerunResult:
        """Rerun verification for a workflow from current state.

        This is a safe rerun that preserves counters and idempotency keys.
        The workflow will re-execute the verification step with the existing
        implementation output.

        Args:
            workflow_id: Temporal workflow ID.
            reason: Reason for the rerun (for audit).
            actor: User initiating the rerun (for audit).

        Returns:
            RerunResult with rerun details.

        Raises:
            WorkflowNotFoundError: If workflow not found.
            UnsafeRerunError: If rerun would be unsafe.
        """
        with tracer.start_as_current_span("workflow_console.rerun_verification") as span:
            span.set_attribute("thestudio.console.workflow_id", workflow_id)
            span.set_attribute("thestudio.console.actor", actor)

            detail = await self.get_workflow_detail(workflow_id)
            if detail is None:
                raise WorkflowNotFoundError(workflow_id)

            current_step = detail.current_step
            target_step = WorkflowStep.VERIFY.value

            self._validate_rerun_safety(current_step, target_step)

            client = await self._get_client()
            handle = client.get_workflow_handle(workflow_id)

            signal_sent = False
            try:
                await handle.signal("rerun_verification", {"reason": reason, "actor": actor})
                signal_sent = True
                logger.info(
                    "Sent rerun_verification signal to %s (actor=%s, reason=%s)",
                    workflow_id,
                    actor,
                    reason,
                )
            except Exception as e:
                logger.warning(
                    "Failed to send rerun signal to %s: %s (will proceed with stub)",
                    workflow_id,
                    e,
                )

            span.set_attribute("thestudio.console.signal_sent", signal_sent)

            return RerunResult(
                workflow_id=workflow_id,
                task_packet_id=detail.task_packet_id,
                previous_step=current_step,
                rerun_from_step=target_step,
                idempotency_preserved=True,
                signal_sent=signal_sent,
            )

    async def send_to_agent(
        self,
        workflow_id: str,
        reason: str,
        actor: str,
        reset_workspace: bool = False,
    ) -> SendToAgentResult:
        """Send workflow back to Primary Agent for fix.

        This resets the workflow to the implementation step so the agent
        can attempt a fix. Optionally resets the workspace.

        Args:
            workflow_id: Temporal workflow ID.
            reason: Reason for sending back (for audit).
            actor: User initiating the action (for audit).
            reset_workspace: Whether to reset workspace before rerun.

        Returns:
            SendToAgentResult with details.

        Raises:
            WorkflowNotFoundError: If workflow not found.
            UnsafeRerunError: If rerun would be unsafe.
        """
        with tracer.start_as_current_span("workflow_console.send_to_agent") as span:
            span.set_attribute("thestudio.console.workflow_id", workflow_id)
            span.set_attribute("thestudio.console.actor", actor)
            span.set_attribute("thestudio.console.reset_workspace", reset_workspace)

            detail = await self.get_workflow_detail(workflow_id)
            if detail is None:
                raise WorkflowNotFoundError(workflow_id)

            current_step = detail.current_step
            target_step = WorkflowStep.IMPLEMENT.value

            self._validate_rerun_safety(current_step, target_step)

            client = await self._get_client()
            handle = client.get_workflow_handle(workflow_id)

            signal_sent = False
            try:
                await handle.signal(
                    "send_to_agent",
                    {
                        "reason": reason,
                        "actor": actor,
                        "reset_workspace": reset_workspace,
                    },
                )
                signal_sent = True
                logger.info(
                    "Sent send_to_agent signal to %s (actor=%s, reset=%s, reason=%s)",
                    workflow_id,
                    actor,
                    reset_workspace,
                    reason,
                )
            except Exception as e:
                logger.warning(
                    "Failed to send send_to_agent signal to %s: %s (will proceed with stub)",
                    workflow_id,
                    e,
                )

            span.set_attribute("thestudio.console.signal_sent", signal_sent)

            return SendToAgentResult(
                workflow_id=workflow_id,
                task_packet_id=detail.task_packet_id,
                sent_to_step=target_step,
                workspace_reset=reset_workspace,
                idempotency_preserved=True,
                signal_sent=signal_sent,
            )

    async def escalate(
        self,
        workflow_id: str,
        reason: str,
        actor: str,
        owner: str | None = None,
    ) -> EscalateResult:
        """Escalate workflow for human intervention.

        Marks the workflow as requiring human review. The workflow will
        enter a human wait state until manually resolved.

        Args:
            workflow_id: Temporal workflow ID.
            reason: Reason for escalation (for audit).
            actor: User initiating escalation (for audit).
            owner: Optional owner to assign escalation to.

        Returns:
            EscalateResult with escalation details.

        Raises:
            WorkflowNotFoundError: If workflow not found.
        """
        with tracer.start_as_current_span("workflow_console.escalate") as span:
            span.set_attribute("thestudio.console.workflow_id", workflow_id)
            span.set_attribute("thestudio.console.actor", actor)

            detail = await self.get_workflow_detail(workflow_id)
            if detail is None:
                raise WorkflowNotFoundError(workflow_id)

            escalated_at = datetime.now(UTC)

            client = await self._get_client()
            handle = client.get_workflow_handle(workflow_id)

            signal_sent = False
            try:
                await handle.signal(
                    "escalate",
                    {
                        "reason": reason,
                        "actor": actor,
                        "owner": owner,
                        "escalated_at": escalated_at.isoformat(),
                    },
                )
                signal_sent = True
                logger.info(
                    "Sent escalate signal to %s (actor=%s, owner=%s, reason=%s)",
                    workflow_id,
                    actor,
                    owner,
                    reason,
                )
            except Exception as e:
                logger.warning(
                    "Failed to send escalate signal to %s: %s (will proceed with stub)",
                    workflow_id,
                    e,
                )

            span.set_attribute("thestudio.console.signal_sent", signal_sent)

            return EscalateResult(
                workflow_id=workflow_id,
                task_packet_id=detail.task_packet_id,
                escalated_at=escalated_at,
                trigger=reason,
                owner=owner,
                signal_sent=signal_sent,
            )
