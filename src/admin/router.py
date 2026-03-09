"""Admin API router for fleet management and operational visibility.

Story 4.2+: Admin UI backend APIs.
Story 4.8: RBAC — Role Definitions, API Enforcement.
Story 4.9: Audit Log — Schema, Logging, Query API.
Architecture reference: thestudioarc/23-admin-control-ui.md
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.audit import (
    AuditEventType,
    AuditLogFilter,
    get_audit_service,
)
from src.admin.experts import get_expert_service
from src.admin.health import HealthService
from src.admin.metrics import get_metrics_service
from src.admin.rbac import Permission, get_current_user_id, require_permission
from src.admin.success_gate import get_success_gate_service
from src.admin.workflow_console import (
    UnsafeRerunError,
    WorkflowConsoleService,
    WorkflowNotFoundError,
    WorkflowStatus,
)
from src.admin.workflow_metrics import WorkflowMetricsService
from src.db.connection import get_session
from src.repo.repo_profile import (
    RepoProfileCreate,
    RepoProfileUpdate,
    RepoStatus,
    RepoTier,
)
from src.repo.repository import RepoDuplicateError, RepoNotFoundError, RepoRepository
from src.settings import settings as _settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Service instances (lazy initialization)
_health_service: HealthService | None = None
_workflow_metrics_service: WorkflowMetricsService | None = None


def get_health_service() -> HealthService:
    """Get or create health service instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


def set_health_service(service: HealthService | None) -> None:
    """Set health service (for testing)."""
    global _health_service
    _health_service = service


def get_workflow_metrics_service() -> WorkflowMetricsService:
    """Get or create workflow metrics service instance."""
    global _workflow_metrics_service
    if _workflow_metrics_service is None:
        _workflow_metrics_service = WorkflowMetricsService()
    return _workflow_metrics_service


def set_workflow_metrics_service(service: WorkflowMetricsService | None) -> None:
    """Set workflow metrics service (for testing)."""
    global _workflow_metrics_service
    _workflow_metrics_service = service


# Repo repository instance (lazy initialization)
_repo_repository: RepoRepository | None = None


def get_repo_repository() -> RepoRepository:
    """Get or create repo repository instance."""
    global _repo_repository
    if _repo_repository is None:
        _repo_repository = RepoRepository()
    return _repo_repository


def set_repo_repository(repo: RepoRepository | None) -> None:
    """Set repo repository (for testing)."""
    global _repo_repository
    _repo_repository = repo


# Workflow console service instance (lazy initialization)
_workflow_console_service: WorkflowConsoleService | None = None


def get_workflow_console_service() -> WorkflowConsoleService:
    """Get or create workflow console service instance."""
    global _workflow_console_service
    if _workflow_console_service is None:
        _workflow_console_service = WorkflowConsoleService()
    return _workflow_console_service


def set_workflow_console_service(service: WorkflowConsoleService | None) -> None:
    """Set workflow console service (for testing)."""
    global _workflow_console_service
    _workflow_console_service = service


class ServiceHealthResponse(BaseModel):
    """Health status for a single service."""

    name: str
    status: str
    latency_ms: float | None = None
    details: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """System health response."""

    temporal: ServiceHealthResponse
    jetstream: ServiceHealthResponse
    postgres: ServiceHealthResponse
    router: ServiceHealthResponse
    checked_at: datetime
    overall_status: str


@router.get(
    "/health",
    response_model=HealthResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_HEALTH))],
)
async def get_system_health() -> HealthResponse:
    """Get system health status.

    Checks health of: Temporal, JetStream, Postgres, Router.
    Each service returns OK, DEGRADED, or DOWN.

    Returns:
        HealthResponse with status of all services and overall status.
    """
    service = get_health_service()
    health = await service.check_all()

    return HealthResponse(
        temporal=ServiceHealthResponse(
            name=health.temporal.name,
            status=health.temporal.status.value,
            latency_ms=health.temporal.latency_ms,
            details=health.temporal.details or None,
            error=health.temporal.error,
        ),
        jetstream=ServiceHealthResponse(
            name=health.jetstream.name,
            status=health.jetstream.status.value,
            latency_ms=health.jetstream.latency_ms,
            details=health.jetstream.details or None,
            error=health.jetstream.error,
        ),
        postgres=ServiceHealthResponse(
            name=health.postgres.name,
            status=health.postgres.status.value,
            latency_ms=health.postgres.latency_ms,
            details=health.postgres.details or None,
            error=health.postgres.error,
        ),
        router=ServiceHealthResponse(
            name=health.router.name,
            status=health.router.status.value,
            latency_ms=health.router.latency_ms,
            details=health.router.details or None,
            error=health.router.error,
        ),
        checked_at=health.checked_at,
        overall_status=health.overall_status.value,
    )


class WorkflowCountsResponse(BaseModel):
    """Aggregate workflow counts."""

    running: int
    stuck: int
    failed: int
    completed: int


class HotAlertResponse(BaseModel):
    """Alert for operational issues."""

    alert_type: str
    severity: str
    repo_name: str
    message: str
    workflow_ids: list[str]
    details: dict[str, Any]


class RepoMetricsResponse(BaseModel):
    """Per-repo workflow metrics."""

    repo_id: str
    repo_name: str
    tier: str
    running: int
    stuck: int
    failed: int
    completed: int
    queue_depth: int
    pass_rate_24h: float
    has_elevated_failure_rate: bool
    stuck_workflow_ids: list[str]


class WorkflowMetricsResponse(BaseModel):
    """Full workflow metrics response."""

    aggregate: WorkflowCountsResponse
    queue_depth: int
    pass_rate_24h: float
    repos: list[RepoMetricsResponse]
    alerts: list[HotAlertResponse]
    checked_at: datetime
    stuck_threshold_hours: int


# --- Repo Management Models (Story 4.4) ---


class RepoListItem(BaseModel):
    """Repository info for list endpoint."""

    id: UUID
    owner: str
    repo: str
    tier: RepoTier
    status: RepoStatus
    installation_id: int
    health: str = "unknown"


class RepoListResponse(BaseModel):
    """Response from GET /admin/repos."""

    repos: list[RepoListItem]
    total: int


class RepoRegisterRequest(BaseModel):
    """Request to register a new repository."""

    owner: str = Field(..., min_length=1, max_length=255)
    repo: str = Field(..., min_length=1, max_length=255)
    installation_id: int
    default_branch: str = "main"


class RepoRegisterResponse(BaseModel):
    """Response from POST /admin/repos."""

    id: UUID
    owner: str
    repo: str
    tier: RepoTier
    installation_id: int
    message: str


class RepoProfileResponse(BaseModel):
    """Full repo profile for detail endpoint."""

    id: UUID
    owner: str
    repo: str
    tier: RepoTier
    status: RepoStatus
    installation_id: int
    default_branch: str
    required_checks: list[str]
    tool_allowlist: list[str]
    writes_enabled: bool
    created_at: datetime
    updated_at: datetime
    health: str = "unknown"


class RepoProfileUpdateRequest(BaseModel):
    """Request to update repo profile."""

    default_branch: str | None = None
    required_checks: list[str] | None = None
    tool_allowlist: list[str] | None = None


class RepoProfileUpdateResponse(BaseModel):
    """Response from PATCH /admin/repos/{id}/profile."""

    id: UUID
    owner: str
    repo: str
    updated_fields: list[str]
    message: str


# --- Repo Management Models (Story 4.5) ---


class RepoTierChangeRequest(BaseModel):
    """Request to change repository tier."""

    tier: RepoTier


class RepoTierChangeResponse(BaseModel):
    """Response from PATCH /admin/repos/{id}/tier."""

    id: UUID
    owner: str
    repo: str
    from_tier: RepoTier
    to_tier: RepoTier
    message: str


class RepoStatusChangeResponse(BaseModel):
    """Response from pause/resume endpoints."""

    id: UUID
    owner: str
    repo: str
    status: RepoStatus
    message: str


class RepoWritesChangeRequest(BaseModel):
    """Request to toggle writes enabled."""

    enabled: bool


class RepoWritesChangeResponse(BaseModel):
    """Response from POST /admin/repos/{id}/writes."""

    id: UUID
    owner: str
    repo: str
    writes_enabled: bool
    message: str


# --- Workflow Console Models (Story 4.6) ---


class TimelineEntryResponse(BaseModel):
    """Single step in workflow timeline."""

    step: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    failure_reason: str | None = None
    evidence: list[str] = Field(default_factory=list)
    attempt_count: int = 1


class RetryInfoResponse(BaseModel):
    """Retry information for a workflow."""

    next_retry_time: datetime | None = None
    time_in_current_step_ms: int = 0
    attempt_count_for_step: int = 1
    max_attempts: int = 3


class EscalationInfoResponse(BaseModel):
    """Escalation information for a workflow."""

    trigger: str | None = None
    owner: str | None = None
    human_wait_state: bool = False
    escalated_at: datetime | None = None


class WorkflowListItemResponse(BaseModel):
    """Workflow item for list response."""

    workflow_id: str
    repo_id: UUID | None = None
    repo_name: str
    status: str
    current_step: str
    issue_ref: str | None = None
    started_at: datetime
    attempt_count: int = 1
    complexity: str = "medium"


class WorkflowListResponse(BaseModel):
    """Response from GET /admin/workflows."""

    workflows: list[WorkflowListItemResponse]
    total: int
    filtered_by: dict[str, Any]


class WorkflowDetailResponse(BaseModel):
    """Full workflow detail with timeline."""

    workflow_id: str
    task_packet_id: str | None = None
    repo_id: UUID | None = None
    repo_name: str
    issue_ref: str | None = None
    status: str
    current_step: str
    attempt_count: int
    complexity: str
    started_at: datetime
    completed_at: datetime | None = None
    timeline: list[TimelineEntryResponse]
    retry_info: RetryInfoResponse
    escalation_info: EscalationInfoResponse


# --- Workflow Safe Rerun Models (Story 4.7) ---


class RerunVerificationRequest(BaseModel):
    """Request to rerun verification for a workflow."""

    reason: str = Field(
        ..., min_length=1, max_length=500, description="Reason for rerun"
    )
    actor: str = Field(
        ..., min_length=1, max_length=255, description="User initiating the rerun"
    )


class RerunVerificationResponse(BaseModel):
    """Response from POST /admin/workflows/{id}/rerun-verification."""

    workflow_id: str
    task_packet_id: str | None = None
    previous_step: str
    rerun_from_step: str
    idempotency_preserved: bool
    message: str


class SendToAgentRequest(BaseModel):
    """Request to send workflow back to agent for fix."""

    reason: str = Field(
        ..., min_length=1, max_length=500, description="Reason for sending back"
    )
    actor: str = Field(
        ..., min_length=1, max_length=255, description="User initiating the action"
    )
    reset_workspace: bool = Field(
        default=False, description="Whether to reset workspace before rerun"
    )


class SendToAgentResponse(BaseModel):
    """Response from POST /admin/workflows/{id}/send-to-agent."""

    workflow_id: str
    task_packet_id: str | None = None
    sent_to_step: str
    workspace_reset: bool
    idempotency_preserved: bool
    message: str


class EscalateRequest(BaseModel):
    """Request to escalate workflow to human."""

    reason: str = Field(
        ..., min_length=1, max_length=500, description="Reason for escalation"
    )
    actor: str = Field(
        ..., min_length=1, max_length=255, description="User initiating escalation"
    )
    owner: str | None = Field(
        default=None,
        max_length=255,
        description="Optional owner to assign escalation to",
    )


class EscalateResponse(BaseModel):
    """Response from POST /admin/workflows/{id}/escalate."""

    workflow_id: str
    task_packet_id: str | None = None
    escalated_at: datetime
    trigger: str
    owner: str | None
    message: str


# --- Audit Log Models (Story 4.9) ---


class AuditLogEntryResponse(BaseModel):
    """Single audit log entry in response."""

    id: UUID
    timestamp: datetime
    actor: str
    event_type: str
    target_id: str
    details: dict[str, Any]


class AuditLogListResponse(BaseModel):
    """Response from GET /admin/audit."""

    entries: list[AuditLogEntryResponse]
    total: int
    filtered_by: dict[str, Any]


@router.get(
    "/workflows/metrics",
    response_model=WorkflowMetricsResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def get_workflow_metrics(
    session: Annotated[AsyncSession, Depends(get_session)],
    repo_id: Annotated[UUID | None, Query(description="Filter by repo ID")] = None,
) -> WorkflowMetricsResponse:
    """Get workflow metrics for the Fleet Dashboard.

    Returns aggregate workflow metrics including:
    - Running, stuck, failed, completed workflow counts
    - Queue depth from Temporal task queue
    - 24h pass rate (workflows completing on first attempt)
    - Per-repo breakdown with tier and health info
    - Hot alerts for repos with elevated failures or stuck workflows

    Args:
        repo_id: Optional repo ID to filter metrics for a single repo.

    Returns:
        WorkflowMetricsResponse with aggregate and per-repo metrics.
    """
    service = get_workflow_metrics_service()
    metrics = await service.get_metrics(session, repo_id)

    return WorkflowMetricsResponse(
        aggregate=WorkflowCountsResponse(
            running=metrics.aggregate.running,
            stuck=metrics.aggregate.stuck,
            failed=metrics.aggregate.failed,
            completed=metrics.aggregate.completed,
        ),
        queue_depth=metrics.queue_depth,
        pass_rate_24h=round(metrics.pass_rate_24h * 100, 1),
        repos=[
            RepoMetricsResponse(
                repo_id=str(repo.repo_id),
                repo_name=repo.repo_name,
                tier=repo.tier,
                running=repo.counts.running,
                stuck=repo.counts.stuck,
                failed=repo.counts.failed,
                completed=repo.counts.completed,
                queue_depth=repo.queue_depth,
                pass_rate_24h=round(repo.pass_rate_24h * 100, 1),
                has_elevated_failure_rate=repo.has_elevated_failure_rate,
                stuck_workflow_ids=repo.stuck_workflow_ids,
            )
            for repo in metrics.repos
        ],
        alerts=[
            HotAlertResponse(
                alert_type=alert.alert_type,
                severity=alert.severity,
                repo_name=alert.repo_name,
                message=alert.message,
                workflow_ids=alert.workflow_ids,
                details=alert.details,
            )
            for alert in metrics.alerts
        ],
        checked_at=metrics.checked_at,
        stuck_threshold_hours=metrics.stuck_threshold_hours,
    )


# --- Repo Management Endpoints (Story 4.4) ---


async def _emit_repo_audit_event(
    session: AsyncSession,
    event_type: AuditEventType,
    repo_id: UUID,
    actor: str,
    details: dict[str, Any],
) -> None:
    """Emit repository audit event to audit log.

    Args:
        session: Database session for audit logging.
        event_type: Type of audit event.
        repo_id: Repository UUID.
        actor: User who performed the action.
        details: Additional event details.
    """
    service = get_audit_service()
    await service.log_repo_event(
        session=session,
        event_type=event_type,
        repo_id=repo_id,
        actor=actor,
        details=details,
    )


@router.get(
    "/repos",
    response_model=RepoListResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_REPOS))],
)
async def list_repos(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoListResponse:
    """List all registered repositories.

    Returns all repos with: id, owner, repo, tier, status, installation_id, health.

    Returns:
        RepoListResponse with list of repos and total count.
    """
    repo_repository = get_repo_repository()
    repos = await repo_repository.list_all(session)

    return RepoListResponse(
        repos=[
            RepoListItem(
                id=repo.id,
                owner=repo.owner,
                repo=repo.repo_name,
                tier=repo.tier,
                status=repo.status,
                installation_id=repo.installation_id,
                health="ok" if repo.status == RepoStatus.ACTIVE else "degraded",
            )
            for repo in repos
        ],
        total=len(repos),
    )


@router.post(
    "/repos",
    response_model=RepoRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.REGISTER_REPO))],
)
async def register_repo(
    request: RepoRegisterRequest,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoRegisterResponse:
    """Register a new repository.

    New repos start at Observe tier. Emits repo_registered audit event.

    Args:
        request: Registration data (owner, repo, installation_id, default_branch).
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoRegisterResponse with new repo ID and details.

    Raises:
        HTTPException 409: If repository is already registered.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    create_data = RepoProfileCreate(
        owner=request.owner,
        repo_name=request.repo,
        installation_id=request.installation_id,
        default_branch=request.default_branch,
        webhook_secret=_settings.webhook_secret,
        tier=RepoTier.OBSERVE,
    )

    try:
        repo = await repo_repository.create(session, create_data)
    except RepoDuplicateError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository {request.owner}/{request.repo} is already registered",
        ) from err

    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_REGISTERED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
            "tier": repo.tier.value,
            "installation_id": repo.installation_id,
        },
    )

    await session.commit()

    return RepoRegisterResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        tier=repo.tier,
        installation_id=repo.installation_id,
        message=f"Registered {repo.full_name} at Observe tier",
    )


@router.get(
    "/repos/{repo_id}",
    response_model=RepoProfileResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_REPOS))],
)
async def get_repo_detail(
    repo_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoProfileResponse:
    """Get repository detail with full Repo Profile.

    Args:
        repo_id: Repository UUID.

    Returns:
        RepoProfileResponse with full repo profile.

    Raises:
        HTTPException 404: If repository not found.
    """
    repo_repository = get_repo_repository()
    repo = await repo_repository.get(session, repo_id)

    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    return RepoProfileResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        tier=repo.tier,
        status=repo.status,
        installation_id=repo.installation_id,
        default_branch=repo.default_branch,
        required_checks=repo.required_checks,
        tool_allowlist=repo.tool_allowlist,
        writes_enabled=repo.writes_enabled,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        health="ok" if repo.status == RepoStatus.ACTIVE else "degraded",
    )


@router.patch(
    "/repos/{repo_id}/profile",
    response_model=RepoProfileUpdateResponse,
    dependencies=[Depends(require_permission(Permission.UPDATE_REPO_PROFILE))],
)
async def update_repo_profile(
    repo_id: UUID,
    request: RepoProfileUpdateRequest,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoProfileUpdateResponse:
    """Update repository profile.

    Updates Repo Profile fields (default_branch, required_checks, tool_allowlist).
    Emits repo_profile_updated audit event.

    Args:
        repo_id: Repository UUID.
        request: Fields to update (all optional).
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoProfileUpdateResponse with updated repo info.

    Raises:
        HTTPException 404: If repository not found.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    update_data = RepoProfileUpdate(
        default_branch=request.default_branch,
        required_checks=request.required_checks,
        tool_allowlist=request.tool_allowlist,
    )

    updated_fields: list[str] = []
    if request.default_branch is not None:
        updated_fields.append("default_branch")
    if request.required_checks is not None:
        updated_fields.append("required_checks")
    if request.tool_allowlist is not None:
        updated_fields.append("tool_allowlist")

    try:
        repo = await repo_repository.update_profile(session, repo_id, update_data)
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err

    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_PROFILE_UPDATED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
            "updated_fields": updated_fields,
        },
    )

    await session.commit()

    return RepoProfileUpdateResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        updated_fields=updated_fields,
        message=f"Updated profile for {repo.full_name}",
    )


# --- Repo Management Endpoints (Story 4.5) ---


@router.patch(
    "/repos/{repo_id}/tier",
    response_model=RepoTierChangeResponse,
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def change_repo_tier(
    repo_id: UUID,
    request: RepoTierChangeRequest,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoTierChangeResponse:
    """Change repository tier (admin override).

    Directly sets tier without compliance checks. Use /repos/{id}/promote
    for gated tier promotion with compliance validation.

    Emits repo_tier_changed audit event.

    Args:
        repo_id: Repository UUID.
        request: New tier value.
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoTierChangeResponse with old and new tier.

    Raises:
        HTTPException 404: If repository not found.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    repo = await repo_repository.get(session, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    from_tier = repo.tier

    try:
        repo = await repo_repository.update_tier(session, repo_id, request.tier)
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err

    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_TIER_CHANGED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
            "from_tier": from_tier.value,
            "to_tier": repo.tier.value,
        },
    )

    await session.commit()

    return RepoTierChangeResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        from_tier=from_tier,
        to_tier=repo.tier,
        message=f"Changed tier for {repo.full_name}: {from_tier.value} → {repo.tier.value}",
    )


@router.post(
    "/repos/{repo_id}/pause",
    response_model=RepoStatusChangeResponse,
    dependencies=[Depends(require_permission(Permission.PAUSE_REPO))],
)
async def pause_repo(
    repo_id: UUID,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoStatusChangeResponse:
    """Pause a repository (stop accepting new tasks).

    Emits repo_paused audit event.

    Args:
        repo_id: Repository UUID.
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoStatusChangeResponse with new status.

    Raises:
        HTTPException 404: If repository not found.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    try:
        repo = await repo_repository.update_status(session, repo_id, RepoStatus.PAUSED)
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err

    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_PAUSED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
        },
    )

    await session.commit()

    return RepoStatusChangeResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        status=repo.status,
        message=f"Paused {repo.full_name}",
    )


@router.post(
    "/repos/{repo_id}/resume",
    response_model=RepoStatusChangeResponse,
    dependencies=[Depends(require_permission(Permission.RESUME_REPO))],
)
async def resume_repo(
    repo_id: UUID,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoStatusChangeResponse:
    """Resume a paused repository.

    Emits repo_resumed audit event.

    Args:
        repo_id: Repository UUID.
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoStatusChangeResponse with new status.

    Raises:
        HTTPException 404: If repository not found.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    try:
        repo = await repo_repository.update_status(session, repo_id, RepoStatus.ACTIVE)
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err

    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_RESUMED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
        },
    )

    await session.commit()

    return RepoStatusChangeResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        status=repo.status,
        message=f"Resumed {repo.full_name}",
    )


@router.post(
    "/repos/{repo_id}/writes",
    response_model=RepoWritesChangeResponse,
    dependencies=[Depends(require_permission(Permission.TOGGLE_WRITES))],
)
async def toggle_repo_writes(
    repo_id: UUID,
    request: RepoWritesChangeRequest,
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RepoWritesChangeResponse:
    """Toggle writes enabled for a repository (Publisher freeze).

    Emits repo_writes_toggled audit event.

    Args:
        repo_id: Repository UUID.
        request: Whether writes should be enabled.
        http_request: FastAPI request for extracting actor.

    Returns:
        RepoWritesChangeResponse with new writes_enabled state.

    Raises:
        HTTPException 404: If repository not found.
    """
    actor = get_current_user_id(http_request)
    repo_repository = get_repo_repository()

    try:
        repo = await repo_repository.set_writes_enabled(
            session, repo_id, enabled=request.enabled
        )
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err

    action = "enabled" if request.enabled else "disabled"
    await _emit_repo_audit_event(
        session=session,
        event_type=AuditEventType.REPO_WRITES_TOGGLED,
        repo_id=repo.id,
        actor=actor,
        details={
            "owner": repo.owner,
            "repo": repo.repo_name,
            "writes_enabled": repo.writes_enabled,
        },
    )

    await session.commit()

    return RepoWritesChangeResponse(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        writes_enabled=repo.writes_enabled,
        message=f"Writes {action} for {repo.full_name}",
    )


# --- Workflow Console Endpoints (Story 4.6) ---


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_WORKFLOWS))],
)
async def list_workflows(
    session: Annotated[AsyncSession, Depends(get_session)],
    repo_id: Annotated[UUID | None, Query(description="Filter by repo ID")] = None,
    status_filter: Annotated[
        WorkflowStatus | None, Query(alias="status", description="Filter by status")
    ] = None,
    age_hours: Annotated[
        int | None, Query(description="Filter workflows older than N hours", ge=1)
    ] = None,
) -> WorkflowListResponse:
    """List workflows with optional filters.

    Returns workflows filtered by repo, status, and/or age.
    Status options: running, stuck, paused, completed, failed, cancelled, terminated.

    Args:
        repo_id: Optional repo ID to filter workflows.
        status_filter: Optional status filter.
        age_hours: Optional minimum age filter (workflows older than N hours).

    Returns:
        WorkflowListResponse with filtered workflow list.
    """
    service = get_workflow_console_service()
    result = await service.list_workflows(
        session,
        repo_id=repo_id,
        status_filter=status_filter,
        age_hours=age_hours,
    )

    return WorkflowListResponse(
        workflows=[
            WorkflowListItemResponse(
                workflow_id=wf.workflow_id,
                repo_id=wf.repo_id,
                repo_name=wf.repo_name,
                status=wf.status.value,
                current_step=wf.current_step,
                issue_ref=wf.issue_ref,
                started_at=wf.started_at,
                attempt_count=wf.attempt_count,
                complexity=wf.complexity,
            )
            for wf in result.workflows
        ],
        total=result.total,
        filtered_by=result.filtered_by,
    )


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowDetailResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_WORKFLOWS))],
)
async def get_workflow_detail(
    workflow_id: str,
) -> WorkflowDetailResponse:
    """Get workflow detail with timeline.

    Returns full workflow information including:
    - TaskPacket ID and issue reference
    - Status and current step
    - Attempt count and complexity
    - Timeline with step-by-step execution history
    - Retry info: next_retry_time, time_in_current_step, attempt_count
    - Escalation info: trigger, owner, human_wait_state

    Args:
        workflow_id: Temporal workflow ID.

    Returns:
        WorkflowDetailResponse with full workflow detail.

    Raises:
        HTTPException 404: If workflow not found.
    """
    service = get_workflow_console_service()
    detail = await service.get_workflow_detail(workflow_id)

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowDetailResponse(
        workflow_id=detail.workflow_id,
        task_packet_id=detail.task_packet_id,
        repo_id=detail.repo_id,
        repo_name=detail.repo_name,
        issue_ref=detail.issue_ref,
        status=detail.status.value,
        current_step=detail.current_step,
        attempt_count=detail.attempt_count,
        complexity=detail.complexity,
        started_at=detail.started_at,
        completed_at=detail.completed_at,
        timeline=[
            TimelineEntryResponse(
                step=entry.step,
                status=entry.status.value,
                started_at=entry.started_at,
                completed_at=entry.completed_at,
                duration_ms=entry.duration_ms,
                failure_reason=entry.failure_reason,
                evidence=entry.evidence,
                attempt_count=entry.attempt_count,
            )
            for entry in detail.timeline
        ],
        retry_info=RetryInfoResponse(
            next_retry_time=detail.retry_info.next_retry_time,
            time_in_current_step_ms=detail.retry_info.time_in_current_step_ms,
            attempt_count_for_step=detail.retry_info.attempt_count_for_step,
            max_attempts=detail.retry_info.max_attempts,
        ),
        escalation_info=EscalationInfoResponse(
            trigger=detail.escalation_info.trigger,
            owner=detail.escalation_info.owner,
            human_wait_state=detail.escalation_info.human_wait_state,
            escalated_at=detail.escalation_info.escalated_at,
        ),
    )


# --- Workflow Safe Rerun Endpoints (Story 4.7) ---


async def _emit_workflow_audit_event(
    session: AsyncSession,
    event_type: AuditEventType,
    workflow_id: str,
    actor: str,
    details: dict[str, Any],
) -> None:
    """Emit workflow audit event to audit log.

    Args:
        session: Database session for audit logging.
        event_type: Type of audit event.
        workflow_id: Temporal workflow ID.
        actor: User who performed the action.
        details: Additional event details.
    """
    service = get_audit_service()
    await service.log_workflow_event(
        session=session,
        event_type=event_type,
        workflow_id=workflow_id,
        actor=actor,
        details=details,
    )


@router.post(
    "/workflows/{workflow_id}/rerun-verification",
    response_model=RerunVerificationResponse,
    dependencies=[Depends(require_permission(Permission.RERUN_VERIFICATION))],
)
async def rerun_verification(
    workflow_id: str,
    request: RerunVerificationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RerunVerificationResponse:
    """Rerun verification for a workflow.

    Triggers verification rerun from current state while preserving
    idempotency keys and attempt counters. This is a safe operation
    for workflows stuck in verification.

    Emits workflow_verification_rerun audit event.

    Args:
        workflow_id: Temporal workflow ID.
        request: Rerun request with reason and actor.
        session: Database session for audit logging.

    Returns:
        RerunVerificationResponse with rerun details.

    Raises:
        HTTPException 404: If workflow not found.
        HTTPException 400: If rerun would be unsafe.
    """
    service = get_workflow_console_service()

    try:
        result = await service.rerun_verification(
            workflow_id=workflow_id,
            reason=request.reason,
            actor=request.actor,
        )
    except WorkflowNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        ) from err
    except UnsafeRerunError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsafe rerun blocked: {err.reason}",
        ) from err

    await _emit_workflow_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_VERIFICATION_RERUN,
        workflow_id=workflow_id,
        actor=request.actor,
        details={
            "reason": request.reason,
            "previous_step": result.previous_step,
            "rerun_from_step": result.rerun_from_step,
        },
    )

    await session.commit()

    return RerunVerificationResponse(
        workflow_id=result.workflow_id,
        task_packet_id=result.task_packet_id,
        previous_step=result.previous_step,
        rerun_from_step=result.rerun_from_step,
        idempotency_preserved=result.idempotency_preserved,
        message=f"Verification rerun initiated for {workflow_id}",
    )


@router.post(
    "/workflows/{workflow_id}/send-to-agent",
    response_model=SendToAgentResponse,
    dependencies=[Depends(require_permission(Permission.SEND_TO_AGENT))],
)
async def send_to_agent(
    workflow_id: str,
    request: SendToAgentRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SendToAgentResponse:
    """Send workflow back to Primary Agent for fix.

    Resets the workflow to the implementation step so the agent can
    attempt a fix. Optionally resets the workspace for a clean slate.

    Emits workflow_sent_to_agent audit event.

    Args:
        workflow_id: Temporal workflow ID.
        request: Request with reason, actor, and reset option.
        session: Database session for audit logging.

    Returns:
        SendToAgentResponse with details.

    Raises:
        HTTPException 404: If workflow not found.
        HTTPException 400: If rerun would be unsafe.
    """
    service = get_workflow_console_service()

    try:
        result = await service.send_to_agent(
            workflow_id=workflow_id,
            reason=request.reason,
            actor=request.actor,
            reset_workspace=request.reset_workspace,
        )
    except WorkflowNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        ) from err
    except UnsafeRerunError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsafe rerun blocked: {err.reason}",
        ) from err

    await _emit_workflow_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_SENT_TO_AGENT,
        workflow_id=workflow_id,
        actor=request.actor,
        details={
            "reason": request.reason,
            "sent_to_step": result.sent_to_step,
            "workspace_reset": result.workspace_reset,
        },
    )

    await session.commit()

    return SendToAgentResponse(
        workflow_id=result.workflow_id,
        task_packet_id=result.task_packet_id,
        sent_to_step=result.sent_to_step,
        workspace_reset=result.workspace_reset,
        idempotency_preserved=result.idempotency_preserved,
        message=f"Workflow {workflow_id} sent back to agent",
    )


@router.post(
    "/workflows/{workflow_id}/escalate",
    response_model=EscalateResponse,
    dependencies=[Depends(require_permission(Permission.ESCALATE_WORKFLOW))],
)
async def escalate_workflow(
    workflow_id: str,
    request: EscalateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscalateResponse:
    """Escalate workflow for human intervention.

    Marks the workflow as requiring human review. The workflow will
    enter a human wait state until manually resolved.

    Emits workflow_escalated audit event.

    Args:
        workflow_id: Temporal workflow ID.
        request: Escalation request with reason, actor, and optional owner.
        session: Database session for audit logging.

    Returns:
        EscalateResponse with escalation details.

    Raises:
        HTTPException 404: If workflow not found.
    """
    service = get_workflow_console_service()

    try:
        result = await service.escalate(
            workflow_id=workflow_id,
            reason=request.reason,
            actor=request.actor,
            owner=request.owner,
        )
    except WorkflowNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        ) from err

    await _emit_workflow_audit_event(
        session=session,
        event_type=AuditEventType.WORKFLOW_ESCALATED,
        workflow_id=workflow_id,
        actor=request.actor,
        details={
            "reason": request.reason,
            "owner": result.owner,
        },
    )

    await session.commit()

    return EscalateResponse(
        workflow_id=result.workflow_id,
        task_packet_id=result.task_packet_id,
        escalated_at=result.escalated_at,
        trigger=result.trigger,
        owner=result.owner,
        message=f"Workflow {workflow_id} escalated for human review",
    )


# --- Audit Log Endpoints (Story 4.9) ---


@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT))],
)
async def list_audit_log(
    session: Annotated[AsyncSession, Depends(get_session)],
    event_type: Annotated[
        AuditEventType | None, Query(description="Filter by event type")
    ] = None,
    actor: Annotated[str | None, Query(description="Filter by actor")] = None,
    target_id: Annotated[str | None, Query(description="Filter by target ID")] = None,
    hours: Annotated[
        int | None, Query(description="Filter to last N hours", ge=1, le=720)
    ] = None,
    limit: Annotated[int, Query(description="Max entries to return", ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(description="Offset for pagination", ge=0)] = 0,
) -> AuditLogListResponse:
    """Query audit log with optional filters.

    Returns audit log entries filtered by event_type, actor, target_id,
    and time window. Entries are sorted by timestamp descending (most recent first).

    Args:
        event_type: Optional event type filter.
        actor: Optional actor (user) filter.
        target_id: Optional target ID filter (repo ID or workflow ID).
        hours: Optional time filter (entries from last N hours).
        limit: Maximum entries to return (default 100, max 1000).
        offset: Pagination offset.

    Returns:
        AuditLogListResponse with filtered entries and total count.
    """
    service = get_audit_service()

    filters = AuditLogFilter(
        event_type=event_type,
        actor=actor,
        target_id=target_id,
        hours=hours,
        limit=limit,
        offset=offset,
    )

    result = await service.query(session, filters)

    return AuditLogListResponse(
        entries=[
            AuditLogEntryResponse(
                id=entry.id,
                timestamp=entry.timestamp,
                actor=entry.actor,
                event_type=entry.event_type.value,
                target_id=entry.target_id,
                details=entry.details,
            )
            for entry in result.entries
        ],
        total=result.total,
        filtered_by=result.filtered_by,
    )


# ---------------------------------------------------------------------------
# Metrics API — Story 5.4, 5.5
# ---------------------------------------------------------------------------


@router.get("/metrics/single-pass")
async def get_single_pass_metrics(
    request: Request,
    repo: str | None = Query(None, description="Filter by repo ID"),
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get single-pass success rate (7d and 30d windows, per-repo)."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_metrics_service()
    return svc.get_single_pass(repo_filter=repo).to_dict()


@router.get("/metrics/loopbacks")
async def get_loopback_metrics(
    request: Request,
    repo: str | None = Query(None, description="Filter by repo ID"),
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get verification loopback breakdown by category."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_metrics_service()
    return svc.get_loopbacks(repo_filter=repo).to_dict()


@router.get("/metrics/reopen")
async def get_reopen_metrics(
    request: Request,
    repo: str | None = Query(None, description="Filter by repo ID"),
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get reopen rate with attribution breakdown."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_metrics_service()
    return svc.get_reopen(repo_filter=repo).to_dict()


@router.get("/metrics/success-gate")
async def get_success_gate(
    request: Request,
    repo: str | None = Query(None, description="Filter by repo ID"),
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Check single-pass success gate status."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_success_gate_service()
    result = svc.check(repo_filter=repo)

    # Emit alert signal if gate fails
    if not result.met and not result.insufficient_data:
        _emit_success_gate_signal(result)

    return result.to_dict()


def _emit_success_gate_signal(result: Any) -> None:
    """Log success_gate_failed alert."""
    logger.warning(
        "Success gate FAILED: rate=%.1f%% threshold=%.1f%%",
        result.current_rate * 100,
        result.threshold * 100,
    )


# ---------------------------------------------------------------------------
# Expert Performance API — Story 5.6
# ---------------------------------------------------------------------------


@router.get("/experts")
async def list_experts(
    request: Request,
    repo: str | None = Query(None, description="Filter by repo ID"),
    tier: str | None = Query(None, description="Filter by trust tier"),
    _user_id: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """List experts with summary metrics."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_expert_service()
    return [e.to_dict() for e in svc.list_experts(repo_filter=repo, tier_filter=tier)]


@router.get("/experts/{expert_id}")
async def get_expert_detail(
    request: Request,
    expert_id: str,
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get expert detail with per-repo breakdown."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_expert_service()
    detail = svc.get_expert(expert_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Expert not found")
    return detail.to_dict()


@router.get("/experts/{expert_id}/drift")
async def get_expert_drift(
    request: Request,
    expert_id: str,
    _user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get drift data for an expert."""
    require_permission(request, Permission.VIEW_METRICS)
    svc = get_expert_service()
    drift = svc.get_expert_drift(expert_id)
    if drift is None:
        raise HTTPException(status_code=404, detail="Expert not found")
    return drift.to_dict()
