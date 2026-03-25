"""Admin UI router — serves Jinja2 templates for the Admin Console.

Story 4.10: UI Foundation — Layout, Templates, Static Assets.
Stories 4.11-4.15: Dashboard, Repos, Workflows, Audit, RBAC views.
Architecture reference: thestudioarc/23-admin-control-ui.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from src.admin.audit import AuditEventType, AuditLogFilter, get_audit_service
from src.admin.compliance_scorecard import get_scorecard_service
from src.admin.experts import get_expert_service
from src.admin.merge_mode import MergeMode, get_merge_mode, set_merge_mode
from src.admin.metrics import get_metrics_service
from src.admin.model_gateway import get_model_router
from src.admin.model_spend import get_budget_utilization, get_spend_report
from src.admin.operational_targets import get_targets_service
from src.admin.rbac import ROLE_PERMISSIONS, Permission, Role, get_rbac_service
from src.admin.router import (
    get_health_service,
    get_repo_repository,
    get_workflow_console_service,
    get_workflow_metrics_service,
)
from src.admin.settings_service import (
    RESTART_REQUIRED_KEYS,
    get_settings_service,
)
from src.admin.success_gate import get_success_gate_service
from src.admin.tool_catalog import DEFAULT_PROFILES, get_tool_catalog
from src.compliance.plane_registry import PlaneStatus, get_plane_registry
from src.compliance.promotion import get_transitions
from src.db.connection import get_async_session
from sqlalchemy import func, select

from src.models.taskpacket import TaskPacketRow, TaskPacketStatus
from src.outcome.dead_letter import get_dead_letter_store
from src.outcome.models import QuarantineReason
from src.outcome.quarantine import get_quarantine_store

# Terminal statuses for TaskPacket queue counts
_PANEL_TERMINAL_STATUSES = {
    TaskPacketStatus.PUBLISHED,
    TaskPacketStatus.REJECTED,
    TaskPacketStatus.FAILED,
}

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _require_ui_auth(request: Request) -> None:
    """Router-level dependency that enforces authentication on all UI routes.

    Reads X-User-ID header, resolves role from DB, and stores both in
    request.state for downstream use by _base_context.
    In dev mode (llm_provider=mock), auto-authenticates as local admin.
    """
    from src.admin.rbac import DEV_MODE_USER_ID

    user_id = request.headers.get("X-User-ID")
    if not user_id:
        from src.settings import settings

        if settings.llm_provider == "mock":
            user_id = DEV_MODE_USER_ID
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )
    request.state.user_id = user_id
    request.state.user_role = await _resolve_role(user_id)


ui_router = APIRouter(
    prefix="/admin/ui",
    tags=["admin-ui"],
    dependencies=[Depends(_require_ui_auth)],
)


@dataclass
class FlashMessage:
    """A flash message to display in the UI."""

    text: str
    level: str = "success"  # success, error, warning


async def _resolve_role(user_id: str | None) -> Role | None:
    """Resolve user role from database.

    In dev mode, auto-provisions the dev admin user with ADMIN role.
    """
    if not user_id:
        return None
    try:
        from src.admin.rbac import DEV_MODE_USER_ID, UserRoleCreate

        service = get_rbac_service()
        async with get_async_session() as session:
            role = await service.get_user_role(session, user_id)
            if role is None and user_id == DEV_MODE_USER_ID:
                from src.settings import settings

                if settings.llm_provider == "mock":
                    logger.info("Dev mode: auto-provisioning admin role for %s", user_id)
                    await service.create_user_role(
                        session,
                        UserRoleCreate(user_id=user_id, role=Role.ADMIN),
                        created_by="dev-mode-auto",
                    )
                    await session.commit()
                    return Role.ADMIN
            return role
    except Exception:
        logger.debug("Could not resolve role for %s", user_id, exc_info=True)
        return None


def _has_permission(role: Role | None, permission: Permission) -> bool:
    """Check if role has permission."""
    if role is None:
        return False
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def _base_context(request: Request) -> dict[str, Any]:
    """Build base template context with user info and navigation state.

    Uses request.state populated by _require_ui_auth dependency.
    """
    return {
        "request": request,
        "current_user_id": request.state.user_id,
        "current_user_role": request.state.user_role,
        "flash_messages": [],
        "active_page": "",
    }


# --- Full Page Routes ---


@ui_router.get("/", response_class=RedirectResponse)
async def ui_root() -> RedirectResponse:
    """Redirect /admin/ui/ to dashboard."""
    return RedirectResponse(url="/admin/ui/dashboard", status_code=302)


@ui_router.get("/dashboard", response_class=HTMLResponse)
async def ui_dashboard(request: Request) -> Response:
    """Render the Fleet Dashboard page."""
    ctx = _base_context(request)
    ctx["active_page"] = "dashboard"
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@ui_router.get("/repos", response_class=HTMLResponse)
async def ui_repos(request: Request) -> Response:
    """Render the Repo Management list page."""
    ctx = _base_context(request)
    ctx["active_page"] = "repos"
    return templates.TemplateResponse(request, "repos.html", ctx)


@ui_router.get("/repos/{repo_id}", response_class=HTMLResponse)
async def ui_repo_detail(request: Request, repo_id: str) -> Response:
    """Render the Repo Detail page."""
    ctx = _base_context(request)
    ctx["active_page"] = "repos"
    ctx["repo_id"] = repo_id
    return templates.TemplateResponse(request, "repo_detail.html", ctx)


@ui_router.get("/workflows", response_class=HTMLResponse)
async def ui_workflows(request: Request) -> Response:
    """Render the Workflow Console list page."""
    ctx = _base_context(request)
    ctx["active_page"] = "workflows"
    return templates.TemplateResponse(request, "workflows.html", ctx)


@ui_router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
async def ui_workflow_detail(request: Request, workflow_id: str) -> Response:
    """Render the Workflow Detail page."""
    ctx = _base_context(request)
    ctx["active_page"] = "workflows"
    ctx["workflow_id"] = workflow_id
    return templates.TemplateResponse(request, "workflow_detail.html", ctx)


@ui_router.get("/audit", response_class=HTMLResponse)
async def ui_audit(request: Request) -> Response:
    """Render the Audit Log page."""
    ctx = _base_context(request)
    ctx["active_page"] = "audit"
    return templates.TemplateResponse(request, "audit.html", ctx)


# --- Detail Panel Routes (Epic 75.2) ---


@ui_router.get("/panel/demo", response_class=HTMLResponse)
async def panel_demo(request: Request) -> Response:
    """Demo endpoint for detail panel infrastructure (Epic 75.2).

    Returns a simple HTML fragment to verify panel HTMX loading works.
    Specific panel routes (repo, workflow) are added in Stories 75.3–75.4.
    """
    return HTMLResponse(
        content=(
            '<div data-panel-title="Panel Demo" class="space-y-3">'
            '<p class="text-gray-700">Detail panel infrastructure is operational.</p>'
            '<p class="text-xs text-gray-400">'
            "Stories 75.3–75.4 add repo and workflow panel routes."
            "</p>"
            "</div>"
        )
    )


# --- Partial (HTMX fragment) Routes ---


@ui_router.get("/partials/dashboard", response_class=HTMLResponse)
async def partial_dashboard(request: Request) -> Response:
    """Render dashboard content partial (called by HTMX polling)."""
    health_svc = get_health_service()
    metrics_svc = get_workflow_metrics_service()

    health_data = await health_svc.check_all()
    async with get_async_session() as session:
        metrics_data = await metrics_svc.get_metrics(session)

    services = [
        health_data.temporal,
        health_data.jetstream,
        health_data.postgres,
        health_data.router,
    ]

    repos_list = []
    for repo_metric in metrics_data.repos:
        repos_list.append(
            {
                "repo_id": str(repo_metric.repo_id),
                "full_name": repo_metric.repo_name,
                "tier": repo_metric.tier,
                "health": "OK" if not repo_metric.has_elevated_failure_rate else "DEGRADED",
                "queue_depth": repo_metric.queue_depth,
                "running": repo_metric.counts.running,
                "stuck": repo_metric.counts.stuck,
                "pass_rate_24h": round(repo_metric.pass_rate_24h * 100, 1),
            }
        )

    hot_alerts = []
    for alert in metrics_data.alerts:
        hot_alerts.append(
            {
                "repo": alert.repo_name,
                "message": alert.message,
            }
        )

    ctx = {
        "request": request,
        "health": {
            "services": [
                {
                    "name": s.name,
                    "status": s.status.value if hasattr(s.status, "value") else s.status,
                    "latency_ms": s.latency_ms,
                    "error": s.error,
                }
                for s in services
            ],
        },
        "metrics": {
            "aggregate": {
                "running": metrics_data.aggregate.running,
                "stuck": metrics_data.aggregate.stuck,
                "failed": metrics_data.aggregate.failed,
                "queue_depth": metrics_data.queue_depth,
            },
            "repos": repos_list,
            "hot_alerts": hot_alerts,
        },
    }
    return templates.TemplateResponse(request, "partials/dashboard_content.html", ctx)


@ui_router.get("/partials/repos", response_class=HTMLResponse)
async def partial_repos(request: Request) -> Response:
    """Render repos list partial."""
    repo_repo = get_repo_repository()

    try:
        async with get_async_session() as session:
            rows = await repo_repo.list_all(session)
    except Exception:
        logger.exception("Failed to list repos")
        rows = []

    repos = []
    for row in rows:
        health = "healthy"
        if hasattr(row, "status") and row.status and row.status.value == "paused":
            health = "degraded"
        elif hasattr(row, "status") and row.status and row.status.value == "writes_disabled":
            health = "degraded"
        repos.append(
            {
                "id": str(row.id),
                "owner": row.owner,
                "repo": row.repo_name,
                "tier": row.tier.value if hasattr(row.tier, "value") else str(row.tier),
                "status": (
                    row.status.value
                    if hasattr(row, "status") and row.status and hasattr(row.status, "value")
                    else "active"
                ),
                "health": health,
                "installation_id": row.installation_id,
            }
        )

    ctx = {"request": request, "repos": repos}
    return templates.TemplateResponse(request, "partials/repos_list.html", ctx)


@ui_router.get("/partials/repo/{repo_id}", response_class=HTMLResponse)
async def partial_repo_detail(request: Request, repo_id: str) -> Response:
    """Render repo detail partial."""
    repo_repo = get_repo_repository()
    role = request.state.user_role

    try:
        async with get_async_session() as session:
            row = await repo_repo.get(session, UUID(repo_id))
    except Exception:
        return HTMLResponse(
            '<div class="text-center py-12 text-red-500 text-sm">Repo not found</div>'
        )

    if row is None:
        return HTMLResponse(
            '<div class="text-center py-12 text-red-500 text-sm">Repo not found</div>'
        )

    health = "healthy"
    if row.status.value == "paused":
        health = "degraded"

    repo_data = {
        "id": str(row.id),
        "owner": row.owner,
        "repo": row.repo_name,
        "tier": row.tier.value,
        "status": row.status.value,
        "health": health,
        "installation_id": row.installation_id,
        "default_branch": getattr(row, "default_branch", "main"),
        "created_at": str(getattr(row, "created_at", "")),
        "writes_enabled": row.status.value != "writes_disabled",
        "profile": {
            "language": getattr(row, "language", ""),
            "build_commands": getattr(row, "build_commands", ""),
            "required_checks": ", ".join(getattr(row, "required_checks", []) or []),
            "risk_paths": ", ".join(getattr(row, "risk_paths", []) or []),
            "poll_enabled": row.poll_enabled,
            "poll_interval_minutes": row.poll_interval_minutes or 10,
        },
    }

    ctx = {
        "request": request,
        "repo": repo_data,
        "current_user_id": request.state.user_id,
        "can_update_profile": _has_permission(role, Permission.UPDATE_REPO_PROFILE),
        "can_change_tier": _has_permission(role, Permission.CHANGE_REPO_TIER),
        "can_pause": _has_permission(role, Permission.PAUSE_REPO),
        "can_toggle_writes": _has_permission(role, Permission.TOGGLE_WRITES),
        "can_delete": _has_permission(role, Permission.REGISTER_REPO),
    }
    return templates.TemplateResponse(request, "partials/repo_detail_content.html", ctx)


@ui_router.get("/panel/repos/{repo_id}", response_class=HTMLResponse)
async def panel_repo_detail(request: Request, repo_id: str) -> Response:
    """Render repo detail sliding panel partial (Epic 75.3).

    Returns a compact panel view with config, trust tier, queue stats,
    and quick-action buttons. Served into #detail-panel-body via HTMX.
    """
    repo_repo = get_repo_repository()
    role = request.state.user_role

    try:
        async with get_async_session() as session:
            row = await repo_repo.get(session, UUID(repo_id))
    except Exception:
        return HTMLResponse(
            '<div class="p-4 text-red-500 text-sm">Repo not found</div>'
        )

    if row is None:
        return HTMLResponse(
            '<div class="p-4 text-red-500 text-sm">Repo not found</div>'
        )

    full_name = f"{row.owner}/{row.repo_name}"
    health = "degraded" if row.status.value == "paused" else "healthy"

    # Queue stats: count TaskPackets by terminal / non-terminal status
    active_count = 0
    completed_count = 0
    failed_count = 0
    try:
        async with get_async_session() as session:
            active_result = await session.execute(
                select(func.count(TaskPacketRow.id)).where(
                    TaskPacketRow.repo == full_name,
                    TaskPacketRow.status.notin_(
                        [s.value for s in _PANEL_TERMINAL_STATUSES]
                    ),
                )
            )
            active_count = active_result.scalar_one() or 0

            completed_result = await session.execute(
                select(func.count(TaskPacketRow.id)).where(
                    TaskPacketRow.repo == full_name,
                    TaskPacketRow.status == TaskPacketStatus.PUBLISHED.value,
                )
            )
            completed_count = completed_result.scalar_one() or 0

            failed_result = await session.execute(
                select(func.count(TaskPacketRow.id)).where(
                    TaskPacketRow.repo == full_name,
                    TaskPacketRow.status == TaskPacketStatus.FAILED.value,
                )
            )
            failed_count = failed_result.scalar_one() or 0
    except Exception:
        logger.debug("Could not fetch queue counts for repo %s", repo_id, exc_info=True)

    repo_data = {
        "id": str(row.id),
        "owner": row.owner,
        "repo": row.repo_name,
        "tier": row.tier.value,
        "status": row.status.value,
        "health": health,
        "installation_id": row.installation_id,
        "default_branch": getattr(row, "default_branch", "main"),
        "profile": {
            "language": getattr(row, "language", ""),
        },
    }

    ctx = {
        "request": request,
        "repo": repo_data,
        "queue": {
            "active": active_count,
            "completed": completed_count,
            "failed": failed_count,
        },
        "current_user_id": request.state.user_id,
        "can_change_tier": _has_permission(role, Permission.CHANGE_REPO_TIER),
        "can_pause": _has_permission(role, Permission.PAUSE_REPO),
    }
    return templates.TemplateResponse(request, "partials/repo_detail.html", ctx)


@ui_router.get("/panel/workflows/{workflow_id}", response_class=HTMLResponse)
async def panel_workflow_detail(request: Request, workflow_id: str) -> Response:
    """Render workflow detail sliding panel partial (Epic 75.4).

    Returns a compact panel view with status timeline, step outputs, logs,
    and quick-action buttons. Served into #detail-panel-body via HTMX.
    """
    console_svc = get_workflow_console_service()
    role = request.state.user_role

    try:
        wf = await console_svc.get_workflow_detail(workflow_id)
    except Exception:
        return HTMLResponse(
            '<div class="p-4 text-red-500 text-sm">Workflow not found</div>'
        )

    if wf is None:
        return HTMLResponse(
            '<div class="p-4 text-red-500 text-sm">Workflow not found</div>'
        )

    timeline = []
    for step in getattr(wf, "timeline", []) or []:
        step_status = step.status.value if hasattr(step.status, "value") else str(step.status)
        evidence_str = None
        if step.evidence:
            evidence_str = (
                "\n".join(step.evidence) if isinstance(step.evidence, list) else str(step.evidence)
            )
        timeline.append(
            {
                "name": step.step,
                "status": step_status,
                "timestamp": str(step.started_at or ""),
                "failure_reason": step.failure_reason,
                "evidence": evidence_str,
            }
        )

    retry_info = None
    if wf.retry_info:
        retry_info = {
            "next_retry_time": str(wf.retry_info.next_retry_time or "—"),
            "time_in_current_step": f"{wf.retry_info.time_in_current_step_ms}ms",
            "attempt_count_for_step": wf.retry_info.attempt_count_for_step,
        }

    escalation = None
    if wf.escalation_info and (wf.escalation_info.trigger or wf.escalation_info.human_wait_state):
        escalation = {
            "trigger": wf.escalation_info.trigger or "—",
            "owner": wf.escalation_info.owner or "—",
            "human_wait_state": wf.escalation_info.human_wait_state,
        }

    workflow_data = {
        "id": str(wf.workflow_id),
        "repo_id": str(wf.repo_id) if wf.repo_id else None,
        "repo_name": getattr(wf, "repo_name", str(wf.repo_id) if wf.repo_id else ""),
        "status": wf.status.value,
        "current_step": getattr(wf, "current_step", None),
        "attempt_count": getattr(wf, "attempt_count", 1),
        "complexity": getattr(wf, "complexity", None),
        "issue_ref": getattr(wf, "issue_ref", None),
        "timeline": timeline,
        "retry_info": retry_info,
        "escalation": escalation,
    }

    ctx = {
        "request": request,
        "workflow": workflow_data,
        "current_user_id": request.state.user_id,
        "can_rerun": _has_permission(role, Permission.RERUN_VERIFICATION),
        "can_escalate": _has_permission(role, Permission.ESCALATE_WORKFLOW),
    }
    return templates.TemplateResponse(request, "partials/workflow_detail.html", ctx)


@ui_router.get("/partials/workflows", response_class=HTMLResponse)
async def partial_workflows(
    request: Request,
    status: str | None = Query(None),
    repo_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Response:
    """Render workflows list partial."""
    console_svc = get_workflow_console_service()

    wf_status = None
    if status:
        try:
            from src.admin.workflow_console import WorkflowStatus

            wf_status = WorkflowStatus(status)
        except ValueError:
            pass

    repo_uuid = UUID(repo_id) if repo_id else None

    try:
        async with get_async_session() as session:
            workflows_response = await console_svc.list_workflows(
                session,
                repo_id=repo_uuid,
                status_filter=wf_status,
            )
        workflows_data = workflows_response.workflows
    except Exception:
        logger.exception("Failed to list workflows")
        workflows_data = []

    workflows = []
    for wf in workflows_data:
        workflows.append(
            {
                "id": str(wf.workflow_id),
                "repo_id": wf.repo_id,
                "repo_name": getattr(wf, "repo_name", wf.repo_id),
                "status": wf.status.value,
                "current_step": getattr(wf, "current_step", None),
                "attempt_count": getattr(wf, "attempt_count", 1),
            }
        )

    ctx = {"request": request, "workflows": workflows}
    return templates.TemplateResponse(request, "partials/workflows_list.html", ctx)


@ui_router.get("/partials/workflow/{workflow_id}", response_class=HTMLResponse)
async def partial_workflow_detail(request: Request, workflow_id: str) -> Response:
    """Render workflow detail partial."""
    console_svc = get_workflow_console_service()
    role = request.state.user_role

    try:
        wf = await console_svc.get_workflow_detail(workflow_id)
    except Exception:
        return HTMLResponse(
            '<div class="text-center py-12 text-red-500 text-sm">Workflow not found</div>'
        )

    if wf is None:
        return HTMLResponse(
            '<div class="text-center py-12 text-red-500 text-sm">Workflow not found</div>'
        )

    timeline = []
    for step in getattr(wf, "timeline", []) or []:
        step_status = step.status.value if hasattr(step.status, "value") else str(step.status)
        evidence_str = None
        if step.evidence:
            evidence_str = (
                "\n".join(step.evidence) if isinstance(step.evidence, list) else str(step.evidence)
            )
        timeline.append(
            {
                "name": step.step,
                "status": step_status,
                "timestamp": str(step.started_at or ""),
                "failure_reason": step.failure_reason,
                "evidence": evidence_str,
            }
        )

    retry_info = None
    if wf.retry_info:
        retry_info = {
            "next_retry_time": str(wf.retry_info.next_retry_time or "-"),
            "time_in_current_step": f"{wf.retry_info.time_in_current_step_ms}ms",
            "attempt_count_for_step": wf.retry_info.attempt_count_for_step,
        }

    escalation = None
    if wf.escalation_info and (wf.escalation_info.trigger or wf.escalation_info.human_wait_state):
        escalation = {
            "trigger": wf.escalation_info.trigger or "-",
            "owner": wf.escalation_info.owner or "-",
            "human_wait_state": wf.escalation_info.human_wait_state,
        }

    workflow_data = {
        "id": str(wf.workflow_id),
        "repo_id": wf.repo_id,
        "repo_name": getattr(wf, "repo_name", wf.repo_id),
        "status": wf.status.value,
        "current_step": getattr(wf, "current_step", None),
        "attempt_count": getattr(wf, "attempt_count", 1),
        "complexity": getattr(wf, "complexity", None),
        "issue_ref": getattr(wf, "issue_ref", None),
        "timeline": timeline,
        "retry_info": retry_info,
        "escalation": escalation,
    }

    ctx = {
        "request": request,
        "workflow": workflow_data,
        "current_user_id": request.state.user_id,
        "can_rerun": _has_permission(role, Permission.RERUN_VERIFICATION),
        "can_send_to_agent": _has_permission(role, Permission.SEND_TO_AGENT),
        "can_escalate": _has_permission(role, Permission.ESCALATE_WORKFLOW),
    }
    return templates.TemplateResponse(request, "partials/workflow_detail_content.html", ctx)


@ui_router.get("/partials/audit", response_class=HTMLResponse)
async def partial_audit(
    request: Request,
    event_type: str | None = Query(None),
    actor: str | None = Query(None),
    target_id: str | None = Query(None),
    hours: int = Query(24, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Response:
    """Render audit log partial."""
    audit_svc = get_audit_service()

    audit_event_type = None
    if event_type:
        try:
            audit_event_type = AuditEventType(event_type)
        except ValueError:
            pass

    log_filter = AuditLogFilter(
        event_type=audit_event_type,
        actor=actor,
        target_id=target_id,
        hours=hours,
        limit=limit + 1,  # Fetch one extra to detect "has more"
        offset=offset,
    )

    try:
        async with get_async_session() as session:
            result = await audit_svc.query(session, log_filter)
            rows = result.entries
    except Exception:
        logger.exception("Failed to query audit log")
        rows = []

    has_more = len(rows) > limit
    entries_to_show = rows[:limit]

    entries = []
    for row in entries_to_show:
        entries.append(
            {
                "timestamp": str(row.timestamp),
                "actor": row.actor,
                "event_type": (
                    row.event_type.value
                    if hasattr(row.event_type, "value")
                    else str(row.event_type)
                ),
                "target_id": str(row.target_id) if row.target_id else None,
                "details": row.details,
            }
        )

    ctx = {
        "request": request,
        "entries": entries,
        "has_more": has_more,
        "offset": offset,
        "limit": limit,
    }
    return templates.TemplateResponse(request, "partials/audit_list.html", ctx)


# --- Metrics Page Routes (Story 5.7) ---


@ui_router.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request) -> Response:
    """Render Metrics & Trends page."""
    ctx = _base_context(request)
    ctx["active_page"] = "metrics"
    return templates.TemplateResponse(request, "metrics.html", ctx)


@ui_router.get("/partials/metrics", response_class=HTMLResponse)
async def metrics_partial(
    request: Request,
    repo: str | None = Query(None),
) -> Response:
    """Render metrics dashboard partial."""
    svc = get_metrics_service()
    repo_filter = repo if repo else None

    single_pass = svc.get_single_pass(repo_filter=repo_filter)
    loopbacks = svc.get_loopbacks(repo_filter=repo_filter)
    reopen = svc.get_reopen(repo_filter=repo_filter)

    gate_svc = get_success_gate_service()
    success_gate = gate_svc.check(repo_filter=repo_filter)

    ctx = {
        "request": request,
        "single_pass": single_pass,
        "loopbacks": loopbacks,
        "reopen": reopen,
        "success_gate": success_gate,
    }
    return templates.TemplateResponse(request, "partials/metrics_content.html", ctx)


# --- Expert Performance Routes (Story 5.8) ---


@ui_router.get("/experts", response_class=HTMLResponse)
async def experts_page(request: Request) -> Response:
    """Render Expert Performance page."""
    ctx = _base_context(request)
    ctx["active_page"] = "experts"
    return templates.TemplateResponse(request, "experts.html", ctx)


@ui_router.get("/partials/experts", response_class=HTMLResponse)
async def experts_partial(
    request: Request,
    repo: str | None = Query(None),
    tier: str | None = Query(None),
) -> Response:
    """Render expert list partial."""
    svc = get_expert_service()
    repo_filter = repo if repo else None
    tier_filter = tier if tier else None
    experts = svc.list_experts(repo_filter=repo_filter, tier_filter=tier_filter)

    ctx = {
        "request": request,
        "experts": [e.to_dict() for e in experts],
    }
    return templates.TemplateResponse(request, "partials/experts_list.html", ctx)


@ui_router.get("/experts/{expert_id}", response_class=HTMLResponse)
async def expert_detail_page(request: Request, expert_id: str) -> Response:
    """Render expert detail page."""
    svc = get_expert_service()
    detail = svc.get_expert(expert_id)

    if detail is None:
        ctx = _base_context(request)
        ctx["active_page"] = "experts"
        ctx["detail"] = "Expert not found"
        return templates.TemplateResponse(request, "error.html", ctx)

    ctx = _base_context(request)
    ctx["active_page"] = "experts"
    ctx["expert"] = detail.to_dict()
    return templates.TemplateResponse(request, "expert_detail.html", ctx)


@ui_router.get("/partials/expert/{expert_id}", response_class=HTMLResponse)
async def expert_detail_partial(request: Request, expert_id: str) -> Response:
    """Render expert detail partial."""
    svc = get_expert_service()
    detail = svc.get_expert(expert_id)

    if detail is None:
        return HTMLResponse("<p class='text-gray-400 text-sm'>Expert not found.</p>")

    ctx = {
        "request": request,
        "expert": detail.to_dict(),
    }
    return templates.TemplateResponse(request, "partials/expert_detail_content.html", ctx)


# --- Tool Hub Routes (Story 7.10) ---


@ui_router.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request) -> Response:
    """Render Tool Hub page."""
    ctx = _base_context(request)
    ctx["active_page"] = "tools"
    return templates.TemplateResponse(request, "tools.html", ctx)


@ui_router.get("/partials/tools", response_class=HTMLResponse)
async def tools_partial(request: Request) -> Response:
    """Render tool catalog partial."""
    catalog = get_tool_catalog()
    suites = catalog.list_suites()

    ctx = {
        "request": request,
        "suites": [s.to_dict() for s in suites],
        "profiles": [p.to_dict() for p in DEFAULT_PROFILES],
    }
    return templates.TemplateResponse(request, "partials/tools_content.html", ctx)


# --- Model Gateway Routes (Story 7.11) ---


@ui_router.get("/models", response_class=HTMLResponse)
async def models_page(request: Request) -> Response:
    """Render Model Gateway page."""
    ctx = _base_context(request)
    ctx["active_page"] = "models"
    return templates.TemplateResponse(request, "models.html", ctx)


@ui_router.get("/partials/models", response_class=HTMLResponse)
async def models_partial(request: Request) -> Response:
    """Render model gateway partial."""
    router = get_model_router()

    ctx = {
        "request": request,
        "providers": [p.to_dict() for p in router.providers],
        "rules": [r.to_dict() for r in router.rules],
    }
    return templates.TemplateResponse(request, "partials/models_content.html", ctx)


@ui_router.get("/partials/model-spend", response_class=HTMLResponse)
async def model_spend_partial(
    request: Request,
    window: int = Query(24, ge=1, le=720),
) -> Response:
    """Render model spend dashboard partial."""
    report = get_spend_report(window_hours=window)
    ctx = {"request": request, "report": report.to_dict()}
    return templates.TemplateResponse(request, "partials/model_spend_content.html", ctx)


# --- Cost Dashboard Routes (Story 32.13) ---


@ui_router.get("/cost-dashboard", response_class=HTMLResponse)
async def cost_dashboard_page(request: Request) -> Response:
    """Render Cost Dashboard page."""
    ctx = _base_context(request)
    ctx["active_page"] = "cost-dashboard"
    return templates.TemplateResponse(request, "cost_dashboard.html", ctx)


@ui_router.get("/partials/cost-dashboard", response_class=HTMLResponse)
async def cost_dashboard_partial(
    request: Request,
    window: int = Query(24, ge=1, le=720),
) -> Response:
    """Render cost dashboard partial with all breakdowns."""
    report = get_spend_report(window_hours=window)
    ctx = {"request": request, "report": report.to_dict()}
    return templates.TemplateResponse(request, "partials/cost_dashboard_content.html", ctx)


@ui_router.get("/partials/budget-utilization", response_class=HTMLResponse)
async def budget_utilization_partial(
    request: Request,
    window: int = Query(24, ge=1, le=720),
) -> Response:
    """Render budget utilization widget partial."""
    utilization = get_budget_utilization(window_hours=window)
    ctx = {"request": request, "utilization": [u.to_dict() for u in utilization]}
    return templates.TemplateResponse(request, "partials/budget_utilization_content.html", ctx)


# --- Compliance Scorecard Routes (Story 7.12) ---


@ui_router.get("/compliance", response_class=HTMLResponse)
async def compliance_page(request: Request) -> Response:
    """Render Compliance Scorecard page."""
    ctx = _base_context(request)
    ctx["active_page"] = "compliance"
    return templates.TemplateResponse(request, "compliance.html", ctx)


@ui_router.get("/partials/compliance", response_class=HTMLResponse)
async def compliance_partial(
    request: Request,
    repo_id: str = Query("default"),
) -> Response:
    """Render compliance scorecard partial."""
    svc = get_scorecard_service()
    scorecard = svc.evaluate(repo_id)

    ctx = {
        "request": request,
        "scorecard": scorecard.to_dict(),
    }
    return templates.TemplateResponse(request, "partials/compliance_content.html", ctx)


# --- Operational Targets Partial (Story 7.13) ---


@ui_router.get("/partials/targets", response_class=HTMLResponse)
async def targets_partial(
    request: Request,
    repo: str | None = Query(None),
) -> Response:
    """Render operational targets partial (lead time, cycle time, reopen target)."""
    svc = get_targets_service()

    lead_time = svc.get_lead_time(repo_filter=repo)
    cycle_time = svc.get_cycle_time(repo_filter=repo)
    reopen_target = svc.get_reopen_target(repo_filter=repo)

    ctx = {
        "request": request,
        "lead_time": lead_time,
        "cycle_time": cycle_time,
        "reopen_target": reopen_target,
    }
    return templates.TemplateResponse(request, "partials/targets_content.html", ctx)


# --- Quarantine Operations Routes (Epic 10, AC1) ---


@ui_router.get("/quarantine", response_class=HTMLResponse)
async def quarantine_page(request: Request) -> Response:
    """Render Quarantine Operations page."""
    ctx = _base_context(request)
    ctx["active_page"] = "quarantine"
    return templates.TemplateResponse(request, "quarantine.html", ctx)


@ui_router.get("/partials/quarantine", response_class=HTMLResponse)
async def quarantine_partial(
    request: Request,
    reason: str | None = Query(None),
    repo: str | None = Query(None),
) -> Response:
    """Render quarantine list partial."""
    store = get_quarantine_store()

    q_reason = None
    if reason:
        try:
            q_reason = QuarantineReason(reason)
        except ValueError:
            pass

    events = store.list_quarantined(
        repo_id=repo if repo else None,
        reason=q_reason,
        include_replayed=True,
    )

    ctx = {
        "request": request,
        "events": [e.to_dict() for e in events],
        "reasons": [r.value for r in QuarantineReason],
        "reason_filter": reason or "",
        "repo_filter": repo or "",
    }
    return templates.TemplateResponse(request, "partials/quarantine_content.html", ctx)


@ui_router.get("/partials/quarantine/{quarantine_id}", response_class=HTMLResponse)
async def quarantine_detail_partial(request: Request, quarantine_id: str) -> Response:
    """Render quarantine event detail partial."""
    store = get_quarantine_store()
    event = store.get_quarantined(UUID(quarantine_id))

    if event is None:
        return HTMLResponse('<div class="text-red-500 text-sm p-4">Event not found.</div>')

    ctx = {"request": request, "evt": event.to_dict()}
    return templates.TemplateResponse(request, "partials/quarantine_detail.html", ctx)


@ui_router.post("/partials/quarantine/{quarantine_id}/replay", response_class=HTMLResponse)
async def quarantine_replay(request: Request, quarantine_id: str) -> Response:
    """Mark quarantined event as replayed."""
    store = get_quarantine_store()
    store.mark_replayed(UUID(quarantine_id))

    event = store.get_quarantined(UUID(quarantine_id))
    if event is None:
        return HTMLResponse('<div class="text-red-500 text-sm p-4">Event not found.</div>')

    ctx = {"request": request, "evt": event.to_dict()}
    return templates.TemplateResponse(request, "partials/quarantine_detail.html", ctx)


@ui_router.delete("/partials/quarantine/{quarantine_id}", response_class=HTMLResponse)
async def quarantine_delete(request: Request, quarantine_id: str) -> Response:
    """Delete quarantined event."""
    store = get_quarantine_store()
    store.delete(UUID(quarantine_id))
    return HTMLResponse('<div class="text-green-600 text-sm p-4">Event deleted.</div>')


# --- Dead-Letter Operations Routes (Epic 10, AC2) ---


@ui_router.get("/dead-letters", response_class=HTMLResponse)
async def dead_letters_page(request: Request) -> Response:
    """Render Dead-Letter Queue page."""
    ctx = _base_context(request)
    ctx["active_page"] = "dead-letters"
    return templates.TemplateResponse(request, "dead_letters.html", ctx)


@ui_router.get("/partials/dead-letters", response_class=HTMLResponse)
async def dead_letters_partial(request: Request) -> Response:
    """Render dead-letter list partial."""
    store = get_dead_letter_store()
    events = store.list_dead_letters()

    ctx = {
        "request": request,
        "events": [e.to_dict() for e in events],
    }
    return templates.TemplateResponse(request, "partials/dead_letters_content.html", ctx)


@ui_router.get("/partials/dead-letter/{event_id}", response_class=HTMLResponse)
async def dead_letter_detail_partial(request: Request, event_id: str) -> Response:
    """Render dead-letter event detail partial."""
    store = get_dead_letter_store()
    event = store.get_dead_letter(UUID(event_id))

    if event is None:
        return HTMLResponse('<div class="text-red-500 text-sm p-4">Event not found.</div>')

    ctx = {"request": request, "evt": event.to_dict()}
    return templates.TemplateResponse(request, "partials/dead_letter_detail.html", ctx)


@ui_router.delete("/partials/dead-letter/{event_id}", response_class=HTMLResponse)
async def dead_letter_delete(request: Request, event_id: str) -> Response:
    """Delete dead-letter event."""
    store = get_dead_letter_store()
    store.delete(UUID(event_id))
    return HTMLResponse('<div class="text-green-600 text-sm p-4">Event deleted.</div>')


# --- Merge Mode Routes (Epic 10, AC3) ---


@ui_router.get("/partials/merge-mode/{repo_id}", response_class=HTMLResponse)
async def merge_mode_partial(request: Request, repo_id: str) -> Response:
    """Render merge mode control for a repo."""
    mode = get_merge_mode(repo_id)
    modes = [m.value for m in MergeMode]
    mode_labels = {
        MergeMode.DRAFT_ONLY.value: "Draft Only",
        MergeMode.REQUIRE_REVIEW.value: "Require Review",
        MergeMode.AUTO_MERGE.value: "Auto Merge",
    }
    safe_repo_id = escape(repo_id)
    safe_mode_value = escape(mode.value)
    return HTMLResponse(
        f'<div class="flex items-center gap-2">'
        f'<label class="text-xs font-medium text-gray-500">Merge Mode:</label>'
        f'<select hx-post="/admin/ui/partials/merge-mode/{safe_repo_id}" '
        f'hx-target="closest div" hx-swap="outerHTML" name="mode" '
        f'class="border border-gray-300 rounded px-2 py-1 text-sm">'
        + "".join(
            f'<option value="{escape(m)}" {"selected" if m == mode.value else ""}>'
            f"{escape(mode_labels[m])}</option>"
            for m in modes
        )
        + f"</select>"
        f'<span class="text-xs text-gray-400">({safe_mode_value})</span>'
        f"</div>"
    )


@ui_router.post("/partials/merge-mode/{repo_id}", response_class=HTMLResponse)
async def merge_mode_update(request: Request, repo_id: str) -> Response:
    """Update merge mode for a repo."""
    form = await request.form()
    mode_str = str(form.get("mode", MergeMode.DRAFT_ONLY.value))
    try:
        mode = MergeMode(mode_str)
    except ValueError:
        mode = MergeMode.DRAFT_ONLY
    set_merge_mode(repo_id, mode)

    # Re-render the control with updated value
    modes = [m.value for m in MergeMode]
    mode_labels = {
        MergeMode.DRAFT_ONLY.value: "Draft Only",
        MergeMode.REQUIRE_REVIEW.value: "Require Review",
        MergeMode.AUTO_MERGE.value: "Auto Merge",
    }
    safe_repo_id = escape(repo_id)
    return HTMLResponse(
        f'<div class="flex items-center gap-2">'
        f'<label class="text-xs font-medium text-gray-500">Merge Mode:</label>'
        f'<select hx-post="/admin/ui/partials/merge-mode/{safe_repo_id}" '
        f'hx-target="closest div" hx-swap="outerHTML" name="mode" '
        f'class="border border-gray-300 rounded px-2 py-1 text-sm">'
        + "".join(
            f'<option value="{escape(m)}" {"selected" if m == mode.value else ""}>'
            f"{escape(mode_labels[m])}</option>"
            for m in modes
        )
        + "</select>"
        '<span class="text-xs text-green-600 text-xs">Updated</span>'
        "</div>"
    )


# --- Execution Plane Routes (Epic 10, AC6) ---


@ui_router.get("/planes", response_class=HTMLResponse)
async def planes_page(request: Request) -> Response:
    """Render Execution Planes page."""
    ctx = _base_context(request)
    ctx["active_page"] = "planes"
    return templates.TemplateResponse(request, "planes.html", ctx)


@ui_router.get("/partials/planes", response_class=HTMLResponse)
async def planes_partial(request: Request) -> Response:
    """Render execution planes partial."""
    registry = get_plane_registry()
    planes = registry.list_planes()
    health = registry.get_health_summary()

    ctx = {
        "request": request,
        "planes": [p.to_dict() for p in planes],
        "health": [h.to_dict() for h in health],
        "total_repos": registry.total_repo_count(),
    }
    return templates.TemplateResponse(request, "partials/planes_content.html", ctx)


@ui_router.post("/partials/planes/register", response_class=HTMLResponse)
async def plane_register(request: Request) -> Response:
    """Register a new execution plane."""
    form = await request.form()
    name = str(form.get("name", ""))
    region = str(form.get("region", "default"))

    if name:
        registry = get_plane_registry()
        registry.register(name=name, region=region)

    return await _render_planes_list(request)


@ui_router.post("/partials/planes/{plane_id}/pause", response_class=HTMLResponse)
async def plane_pause(request: Request, plane_id: str) -> Response:
    """Pause an execution plane."""
    registry = get_plane_registry()
    registry.set_status(UUID(plane_id), PlaneStatus.PAUSED)
    return await _render_planes_list(request)


@ui_router.post("/partials/planes/{plane_id}/resume", response_class=HTMLResponse)
async def plane_resume(request: Request, plane_id: str) -> Response:
    """Resume a paused execution plane."""
    registry = get_plane_registry()
    registry.set_status(UUID(plane_id), PlaneStatus.ACTIVE)
    return await _render_planes_list(request)


async def _render_planes_list(request: Request) -> Response:
    """Helper to re-render planes list after mutation."""
    registry = get_plane_registry()
    planes = registry.list_planes()
    health = registry.get_health_summary()
    ctx = {
        "request": request,
        "planes": [p.to_dict() for p in planes],
        "health": [h.to_dict() for h in health],
        "total_repos": registry.total_repo_count(),
    }
    return templates.TemplateResponse(request, "partials/planes_content.html", ctx)


# --- Promotion History Route (Epic 10, AC7) ---


@ui_router.get("/partials/promotion-history/{repo_id}", response_class=HTMLResponse)
async def promotion_history_partial(request: Request, repo_id: str) -> Response:
    """Render promotion history for a repo."""
    transitions = get_transitions(UUID(repo_id))
    items = [t.to_dict() for t in transitions]

    if not items:
        return HTMLResponse('<div class="text-gray-400 text-sm py-2">No promotion history.</div>')

    rows = []
    for t in items:
        score_str = f"{t['compliance_score']:.0f}" if t.get("compliance_score") is not None else "-"
        remediation_count = len(t.get("remediation_items", []))
        from_tier = escape(str(t.get("from_tier", "")))
        to_tier = escape(str(t.get("to_tier", "")))
        triggered_by = escape(str(t.get("triggered_by", "")))
        reason = escape(str(t.get("reason", "")))
        transitioned_at = escape(str(t.get("transitioned_at") or "")[:19])
        rows.append(
            f'<tr class="hover:bg-gray-50">'
            f'<td class="py-2 pr-4 text-xs">{transitioned_at}</td>'
            f'<td class="py-2 pr-4">{from_tier} &rarr; {to_tier}</td>'
            f'<td class="py-2 pr-4">{triggered_by}</td>'
            f'<td class="py-2 pr-4">{score_str}</td>'
            f'<td class="py-2 pr-4 text-gray-500">{reason}</td>'
            f'<td class="py-2">{remediation_count} item(s)</td>'
            f"</tr>"
        )

    return HTMLResponse(
        '<table class="w-full text-sm">'
        '<thead><tr class="border-b border-gray-200 text-left'
        ' text-xs text-gray-500 uppercase tracking-wide">'
        '<th class="pb-2 pr-4">Date</th>'
        '<th class="pb-2 pr-4">Transition</th>'
        '<th class="pb-2 pr-4">Triggered By</th>'
        '<th class="pb-2 pr-4">Score</th>'
        '<th class="pb-2 pr-4">Reason</th>'
        '<th class="pb-2">Remediation</th>'
        "</tr></thead>"
        f'<tbody class="divide-y divide-gray-100">{"".join(rows)}</tbody>'
        "</table>"
    )


# --- Settings UI Routes (Epic 12) ---


@ui_router.get("/settings", response_class=HTMLResponse)
async def ui_settings(request: Request) -> Response:
    """Render the Settings page (admin-only)."""
    role = request.state.user_role
    if role != Role.ADMIN:
        return RedirectResponse(url="/admin/ui/dashboard", status_code=302)
    ctx = _base_context(request)
    ctx["active_page"] = "settings"
    return templates.TemplateResponse(request, "settings.html", ctx)


@ui_router.get("/partials/settings", response_class=HTMLResponse)
async def partial_settings(request: Request) -> Response:
    """Render the settings content partial with 5 card containers."""
    ctx = {"request": request}
    return templates.TemplateResponse(request, "partials/settings_content.html", ctx)


@ui_router.get("/partials/settings/api-keys", response_class=HTMLResponse)
async def partial_settings_api_keys(request: Request) -> Response:
    """Render the API Keys card partial."""
    from src.admin.persistence.pg_settings import SettingCategory

    svc = get_settings_service()
    async with get_async_session() as session:
        values = await svc.list_by_category(session, SettingCategory.API_KEYS)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
    }
    return templates.TemplateResponse(request, "partials/settings_api_keys.html", ctx)


@ui_router.post("/partials/settings/api-keys", response_class=HTMLResponse)
async def partial_settings_api_keys_update(request: Request) -> Response:
    """Update an API key and re-render the card."""
    from src.admin.audit import AuditEventType, get_audit_service
    from src.admin.persistence.pg_settings import SettingCategory

    form = await request.form()
    key = str(form.get("key", ""))
    value = str(form.get("value", ""))
    user_id = request.state.user_id

    svc = get_settings_service()
    audit_svc = get_audit_service()
    flash = None

    async with get_async_session() as session:
        try:
            old_sv = await svc.get(session, key)
            old_display = old_sv.display_value if old_sv else None
            sv = await svc.set(session, key, value, user_id)
            await audit_svc.log_event(
                session,
                user_id,
                AuditEventType.SETTINGS_CHANGED,
                key,
                {"action": "update", "old_value": old_display, "new_value": sv.display_value},
            )
            await session.commit()
            flash = f"Updated {key} successfully"
        except ValueError as e:
            flash = str(e)

        values = await svc.list_by_category(session, SettingCategory.API_KEYS)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
        "flash": flash,
    }
    return templates.TemplateResponse(request, "partials/settings_api_keys.html", ctx)


@ui_router.get("/partials/settings/api-keys/reveal/{key}", response_class=HTMLResponse)
async def partial_settings_api_keys_reveal(request: Request, key: str) -> Response:
    """Reveal an unmasked API key value (admin only, logged)."""
    role = request.state.user_role
    if role != Role.ADMIN:
        denied = '<span class="text-red-500 text-sm">Access denied</span>'
        return HTMLResponse(denied, status_code=403)

    svc = get_settings_service()
    async with get_async_session() as session:
        sv = await svc.get(session, key, unmask=True)

    if sv is None:
        return HTMLResponse('<span class="text-gray-400 text-sm">Not configured</span>')

    logger.info("Settings reveal: user=%s key=%s", request.state.user_id, key)
    return HTMLResponse(
        f'<code class="text-sm text-gray-600 bg-gray-50 px-2 py-1 rounded">'
        f'{escape(sv.value)}</code>'
    )


@ui_router.get("/partials/settings/infrastructure", response_class=HTMLResponse)
async def partial_settings_infrastructure(request: Request) -> Response:
    """Render the Infrastructure card partial."""
    from src.admin.persistence.pg_settings import SettingCategory

    svc = get_settings_service()
    async with get_async_session() as session:
        values = await svc.list_by_category(session, SettingCategory.INFRASTRUCTURE)

    # Check if any infra settings have DB overrides (restart-required)
    restart_required = any(v.source == "db" and v.key in RESTART_REQUIRED_KEYS for v in values)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
        "restart_required": restart_required,
        "restart_required_keys": RESTART_REQUIRED_KEYS,
    }
    return templates.TemplateResponse(request, "partials/settings_infrastructure.html", ctx)


@ui_router.post("/partials/settings/infrastructure", response_class=HTMLResponse)
async def partial_settings_infrastructure_update(request: Request) -> Response:
    """Update an infrastructure setting and re-render."""
    from src.admin.audit import AuditEventType, get_audit_service
    from src.admin.persistence.pg_settings import SettingCategory

    form = await request.form()
    key = str(form.get("key", ""))
    value = str(form.get("value", ""))
    user_id = request.state.user_id

    svc = get_settings_service()
    audit_svc = get_audit_service()
    flash = None
    error = None

    async with get_async_session() as session:
        try:
            old_sv = await svc.get(session, key)
            old_display = old_sv.display_value if old_sv else None
            sv = await svc.set(session, key, value, user_id)
            await audit_svc.log_event(
                session,
                user_id,
                AuditEventType.SETTINGS_CHANGED,
                key,
                {"action": "update", "old_value": old_display, "new_value": sv.display_value},
            )
            await session.commit()
            flash = f"Updated {key} successfully"
        except ValueError as e:
            error = str(e)

        values = await svc.list_by_category(session, SettingCategory.INFRASTRUCTURE)

    restart_required = any(v.source == "db" and v.key in RESTART_REQUIRED_KEYS for v in values)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
        "restart_required": restart_required,
        "restart_required_keys": RESTART_REQUIRED_KEYS,
        "flash": flash,
        "error": error,
    }
    return templates.TemplateResponse(request, "partials/settings_infrastructure.html", ctx)


@ui_router.get("/partials/settings/feature-flags", response_class=HTMLResponse)
async def partial_settings_feature_flags(request: Request) -> Response:
    """Render the Feature Flags card partial."""
    from src.admin.persistence.pg_settings import SettingCategory

    svc = get_settings_service()
    async with get_async_session() as session:
        values = await svc.list_by_category(session, SettingCategory.FEATURE_FLAGS)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
    }
    return templates.TemplateResponse(request, "partials/settings_feature_flags.html", ctx)


@ui_router.post("/partials/settings/feature-flags", response_class=HTMLResponse)
async def partial_settings_feature_flags_update(request: Request) -> Response:
    """Toggle a feature flag and re-render."""
    from src.admin.audit import AuditEventType, get_audit_service
    from src.admin.persistence.pg_settings import SettingCategory

    form = await request.form()
    key = str(form.get("key", ""))
    value = str(form.get("value", ""))
    user_id = request.state.user_id

    svc = get_settings_service()
    audit_svc = get_audit_service()
    flash = None

    async with get_async_session() as session:
        try:
            old_sv = await svc.get(session, key)
            old_display = old_sv.display_value if old_sv else None
            sv = await svc.set(session, key, value, user_id)
            await audit_svc.log_event(
                session,
                user_id,
                AuditEventType.SETTINGS_CHANGED,
                key,
                {"action": "update", "old_value": old_display, "new_value": sv.display_value},
            )
            await session.commit()
            flash = f"Updated {key} to {value}"
        except ValueError as e:
            flash = str(e)

        values = await svc.list_by_category(session, SettingCategory.FEATURE_FLAGS)

    ctx = {
        "request": request,
        "settings": [v.to_dict() for v in values],
        "flash": flash,
    }
    return templates.TemplateResponse(request, "partials/settings_feature_flags.html", ctx)


@ui_router.get("/partials/settings/agent-config", response_class=HTMLResponse)
async def partial_settings_agent_config(request: Request) -> Response:
    """Render the Agent Config card partial."""
    from src.admin.persistence.pg_settings import SettingCategory

    svc = get_settings_service()
    model_router = get_model_router()

    async with get_async_session() as session:
        values = await svc.list_by_category(session, SettingCategory.AGENT_CONFIG)

    current_values = {v.key: v.value for v in values}
    sources = {v.key: v.source for v in values}

    # Get available model IDs from ModelRouter
    available_models = sorted({p.model_id for p in model_router.providers})
    if not available_models:
        available_models = ["claude-haiku-3-5", "claude-sonnet-4-5", "claude-opus-4-6"]

    ctx = {
        "request": request,
        "current_values": current_values,
        "sources": sources,
        "available_models": available_models,
    }
    return templates.TemplateResponse(request, "partials/settings_agent_config.html", ctx)


@ui_router.post("/partials/settings/agent-config", response_class=HTMLResponse)
async def partial_settings_agent_config_update(request: Request) -> Response:
    """Update agent config settings and re-render."""
    from src.admin.audit import AuditEventType, get_audit_service
    from src.admin.persistence.pg_settings import SettingCategory

    form = await request.form()
    user_id = request.state.user_id

    svc = get_settings_service()
    audit_svc = get_audit_service()
    flash = None
    error = None

    agent_keys = ["agent_model", "agent_max_turns", "agent_max_budget_usd", "agent_max_loopbacks"]

    async with get_async_session() as session:
        for key in agent_keys:
            value = form.get(key)
            if value is None:
                continue
            value = str(value)
            try:
                old_sv = await svc.get(session, key)
                old_display = old_sv.display_value if old_sv else None
                sv = await svc.set(session, key, value, user_id)
                await audit_svc.log_event(
                    session,
                    user_id,
                    AuditEventType.SETTINGS_CHANGED,
                    key,
                    {"action": "update", "old_value": old_display, "new_value": sv.display_value},
                )
            except ValueError as e:
                error = str(e)
                break

        if not error:
            await session.commit()
            flash = "Agent configuration updated"

        values = await svc.list_by_category(session, SettingCategory.AGENT_CONFIG)

    current_values = {v.key: v.value for v in values}
    sources = {v.key: v.source for v in values}

    model_router = get_model_router()
    available_models = sorted({p.model_id for p in model_router.providers})
    if not available_models:
        available_models = ["claude-haiku-3-5", "claude-sonnet-4-5", "claude-opus-4-6"]

    ctx = {
        "request": request,
        "current_values": current_values,
        "sources": sources,
        "available_models": available_models,
        "flash": flash,
        "error": error,
    }
    return templates.TemplateResponse(request, "partials/settings_agent_config.html", ctx)


@ui_router.get("/partials/settings/budget-controls", response_class=HTMLResponse)
async def partial_settings_budget_controls(request: Request) -> Response:
    """Render the Budget Controls card partial (Story 32.7)."""
    svc = get_settings_service()

    async with get_async_session() as session:
        sv = await svc.get(session, "cost_optimization_budget_tiers")
        routing_sv = await svc.get(session, "cost_optimization_routing_enabled")

    import json as _json

    if sv:
        try:
            budget_tiers = _json.loads(sv.value) if isinstance(sv.value, str) else sv.value
        except (ValueError, TypeError):
            budget_tiers = {"observe": 2.00, "suggest": 5.00, "execute": 8.00}
        source = sv.source
    else:
        budget_tiers = {"observe": 2.00, "suggest": 5.00, "execute": 8.00}
        source = "env"

    routing_enabled = False
    if routing_sv:
        routing_enabled = routing_sv.value in ("True", "true", "1", True)

    ctx = {
        "request": request,
        "budget_tiers": budget_tiers,
        "source": source,
        "routing_enabled": routing_enabled,
    }
    return templates.TemplateResponse(request, "partials/settings_budget_controls.html", ctx)


@ui_router.post("/partials/settings/budget-controls", response_class=HTMLResponse)
async def partial_settings_budget_controls_update(request: Request) -> Response:
    """Update budget tier caps and re-render (Story 32.7)."""
    import json as _json

    from src.admin.audit import AuditEventType, get_audit_service

    form = await request.form()
    user_id = request.state.user_id

    svc = get_settings_service()
    audit_svc = get_audit_service()
    flash = None
    error = None

    tiers = {}
    for tier in ("observe", "suggest", "execute"):
        raw = form.get(tier, "")
        try:
            val = float(raw)  # type: ignore[arg-type]
            if val < 0.50 or val > 50.00:
                error = f"{tier.title()} tier must be between $0.50 and $50.00"
                break
            tiers[tier] = val
        except (ValueError, TypeError):
            error = f"Invalid value for {tier} tier"
            break

    if not error:
        value_json = _json.dumps(tiers)
        async with get_async_session() as session:
            try:
                old_sv = await svc.get(session, "cost_optimization_budget_tiers")
                old_display = old_sv.display_value if old_sv else None
                await svc.set(session, "cost_optimization_budget_tiers", value_json, user_id)
                await audit_svc.log_event(
                    session,
                    user_id,
                    AuditEventType.SETTINGS_CHANGED,
                    "cost_optimization_budget_tiers",
                    {"action": "update", "old_value": old_display, "new_value": value_json},
                )
                await session.commit()
                flash = f"Budget caps updated: observe=${tiers['observe']:.2f}, suggest=${tiers['suggest']:.2f}, execute=${tiers['execute']:.2f}"
            except ValueError as e:
                error = str(e)

    # Re-fetch for render
    async with get_async_session() as session:
        sv = await svc.get(session, "cost_optimization_budget_tiers")
        routing_sv = await svc.get(session, "cost_optimization_routing_enabled")

    if sv:
        try:
            budget_tiers = _json.loads(sv.value) if isinstance(sv.value, str) else sv.value
        except (ValueError, TypeError):
            budget_tiers = tiers or {"observe": 2.00, "suggest": 5.00, "execute": 8.00}
        source = sv.source
    else:
        budget_tiers = tiers or {"observe": 2.00, "suggest": 5.00, "execute": 8.00}
        source = "env"

    routing_enabled = False
    if routing_sv:
        routing_enabled = routing_sv.value in ("True", "true", "1", True)

    ctx = {
        "request": request,
        "budget_tiers": budget_tiers,
        "source": source,
        "routing_enabled": routing_enabled,
        "flash": flash,
        "error": error,
    }
    return templates.TemplateResponse(request, "partials/settings_budget_controls.html", ctx)


@ui_router.get("/partials/settings/secrets", response_class=HTMLResponse)
async def partial_settings_secrets(request: Request) -> Response:
    """Render the Secrets card partial."""
    svc = get_settings_service()

    async with get_async_session() as session:
        enc_sv = await svc.get(session, "encryption_key")
        wh_sv = await svc.get(session, "webhook_secret")

    ctx = {
        "request": request,
        "encryption_key_set": enc_sv is not None and bool(enc_sv.value),
        "webhook_secret_set": wh_sv is not None and bool(wh_sv.value),
    }
    return templates.TemplateResponse(request, "partials/settings_secrets.html", ctx)


@ui_router.post("/partials/settings/secrets/rotate-key", response_class=HTMLResponse)
async def partial_settings_secrets_rotate_key(request: Request) -> Response:
    """Rotate the encryption key (requires typing ROTATE to confirm)."""
    from src.admin.audit import AuditEventType, get_audit_service
    from src.admin.settings_crypto import generate_fernet_key

    form = await request.form()
    confirmation = str(form.get("confirmation", ""))
    user_id = request.state.user_id

    error = None
    flash = None

    if confirmation != "ROTATE":
        error = 'Type "ROTATE" to confirm key rotation'
    else:
        svc = get_settings_service()
        audit_svc = get_audit_service()
        new_key = generate_fernet_key()

        async with get_async_session() as session:
            try:
                count = await svc.rotate_encryption_key(session, new_key, user_id)
                # Store the new key
                await svc.set(session, "encryption_key", new_key, user_id)
                await audit_svc.log_event(
                    session,
                    user_id,
                    AuditEventType.SETTINGS_CHANGED,
                    "encryption_key",
                    {"action": "rotate", "secrets_reencrypted": count},
                )
                await session.commit()
                flash = f"Encryption key rotated. {count} secrets re-encrypted."
            except Exception as e:
                logger.exception("Key rotation failed")
                error = f"Key rotation failed: {e}"

    svc = get_settings_service()
    async with get_async_session() as session:
        enc_sv = await svc.get(session, "encryption_key")
        wh_sv = await svc.get(session, "webhook_secret")

    ctx = {
        "request": request,
        "encryption_key_set": enc_sv is not None and bool(enc_sv.value),
        "webhook_secret_set": wh_sv is not None and bool(wh_sv.value),
        "flash": flash,
        "error": error,
    }
    return templates.TemplateResponse(request, "partials/settings_secrets.html", ctx)


@ui_router.post("/partials/settings/secrets/regenerate-webhook", response_class=HTMLResponse)
async def partial_settings_secrets_regenerate_webhook(request: Request) -> Response:
    """Regenerate the webhook secret."""
    from src.admin.audit import AuditEventType, get_audit_service

    user_id = request.state.user_id
    svc = get_settings_service()
    audit_svc = get_audit_service()

    async with get_async_session() as session:
        new_secret = await svc.regenerate_webhook_secret(session, user_id)
        await audit_svc.log_event(
            session,
            user_id,
            AuditEventType.SETTINGS_CHANGED,
            "webhook_secret",
            {"action": "regenerate"},
        )
        await session.commit()

        enc_sv = await svc.get(session, "encryption_key")

    ctx = {
        "request": request,
        "encryption_key_set": enc_sv is not None and bool(enc_sv.value),
        "webhook_secret_set": True,
        "new_webhook_secret": new_secret,
        "flash": "Webhook secret regenerated",
    }
    return templates.TemplateResponse(request, "partials/settings_secrets.html", ctx)


# --- Portfolio Health Dashboard (Epic 29 Sprint 2, Story 29.8) ---


@ui_router.get("/portfolio-health", response_class=HTMLResponse)
async def portfolio_health_page(request: Request) -> Response:
    """Render the Meridian portfolio health dashboard page."""
    ctx = _base_context(request)
    ctx["active_page"] = "portfolio-health"
    return templates.TemplateResponse(request, "portfolio_health.html", ctx)


@ui_router.get("/partials/portfolio-health", response_class=HTMLResponse)
async def portfolio_health_partial(request: Request) -> Response:
    """Render portfolio health partial with latest review data."""
    reviews = await _get_recent_portfolio_reviews(limit=7)

    latest = reviews[0] if reviews else None
    trend = [
        {
            "reviewed_at": r["reviewed_at"],
            "overall_health": r["overall_health"],
            "flag_count": len(r.get("flags", [])),
        }
        for r in reviews
    ]

    ctx = {
        "request": request,
        "latest": latest,
        "trend": trend,
        "has_data": latest is not None,
    }
    return templates.TemplateResponse(
        request, "partials/portfolio_health_content.html", ctx
    )


async def _get_recent_portfolio_reviews(limit: int = 7) -> list[dict]:
    """Fetch recent portfolio reviews from the database."""
    try:
        from sqlalchemy import select

        from src.db.models import PortfolioReviewRow

        async with get_async_session() as session:
            stmt = (
                select(PortfolioReviewRow)
                .order_by(PortfolioReviewRow.reviewed_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "reviewed_at": row.reviewed_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "overall_health": row.overall_health,
                    "flags": row.flags or [],
                    "metrics": row.metrics or {},
                    "recommendations": row.recommendations or [],
                }
                for row in rows
            ]
    except Exception:
        logger.debug("Could not fetch portfolio reviews", exc_info=True)
        return []
