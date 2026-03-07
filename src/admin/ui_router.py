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

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.admin.audit import AuditEventType, AuditLogFilter, get_audit_service
from src.admin.compliance_scorecard import get_scorecard_service
from src.admin.experts import get_expert_service
from src.admin.metrics import get_metrics_service
from src.admin.model_gateway import get_model_router
from src.admin.operational_targets import get_targets_service
from src.admin.success_gate import get_success_gate_service
from src.admin.tool_catalog import DEFAULT_PROFILES, get_tool_catalog
from src.admin.rbac import ROLE_PERMISSIONS, Permission, Role, get_rbac_service
from src.admin.router import (
    get_health_service,
    get_repo_repository,
    get_workflow_console_service,
    get_workflow_metrics_service,
)
from src.db.connection import get_async_session

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ui_router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])


@dataclass
class FlashMessage:
    """A flash message to display in the UI."""

    text: str
    level: str = "success"  # success, error, warning


async def _resolve_role(user_id: str | None) -> Role | None:
    """Resolve user role from database."""
    if not user_id:
        return None
    try:
        service = get_rbac_service()
        async with get_async_session() as session:
            return await service.get_user_role(session, user_id)
    except Exception:
        logger.debug("Could not resolve role for %s", user_id)
        return None


def _has_permission(role: Role | None, permission: Permission) -> bool:
    """Check if role has permission."""
    if role is None:
        return False
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def _base_context(request: Request, role: Role | None = None) -> dict[str, Any]:
    """Build base template context with user info and navigation state."""
    user_id = request.headers.get("X-User-ID")
    return {
        "request": request,
        "current_user_id": user_id,
        "current_user_role": role,
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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "dashboard"
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@ui_router.get("/repos", response_class=HTMLResponse)
async def ui_repos(request: Request) -> Response:
    """Render the Repo Management list page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "repos"
    return templates.TemplateResponse(request, "repos.html", ctx)


@ui_router.get("/repos/{repo_id}", response_class=HTMLResponse)
async def ui_repo_detail(request: Request, repo_id: str) -> Response:
    """Render the Repo Detail page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "repos"
    ctx["repo_id"] = repo_id
    return templates.TemplateResponse(request, "repo_detail.html", ctx)


@ui_router.get("/workflows", response_class=HTMLResponse)
async def ui_workflows(request: Request) -> Response:
    """Render the Workflow Console list page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "workflows"
    return templates.TemplateResponse(request, "workflows.html", ctx)


@ui_router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
async def ui_workflow_detail(request: Request, workflow_id: str) -> Response:
    """Render the Workflow Detail page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "workflows"
    ctx["workflow_id"] = workflow_id
    return templates.TemplateResponse(request, "workflow_detail.html", ctx)


@ui_router.get("/audit", response_class=HTMLResponse)
async def ui_audit(request: Request) -> Response:
    """Render the Audit Log page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
    ctx["active_page"] = "audit"
    return templates.TemplateResponse(request, "audit.html", ctx)


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
        repos_list.append({
            "repo_id": str(repo_metric.repo_id),
            "full_name": repo_metric.repo_name,
            "tier": repo_metric.tier,
            "health": "OK" if not repo_metric.has_elevated_failure_rate else "DEGRADED",
            "queue_depth": repo_metric.queue_depth,
            "running": repo_metric.counts.running,
            "stuck": repo_metric.counts.stuck,
            "pass_rate_24h": round(repo_metric.pass_rate_24h * 100, 1),
        })

    hot_alerts = []
    for alert in metrics_data.alerts:
        hot_alerts.append({
            "repo": alert.repo_name,
            "message": alert.message,
        })

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
        repos.append({
            "id": str(row.id),
            "owner": row.owner,
            "repo": row.repo,
            "tier": row.tier.value if hasattr(row.tier, "value") else str(row.tier),
            "status": (
                row.status.value
                if hasattr(row, "status") and row.status and hasattr(row.status, "value")
                else "active"
            ),
            "health": health,
            "installation_id": row.installation_id,
        })

    ctx = {"request": request, "repos": repos}
    return templates.TemplateResponse(request, "partials/repos_list.html", ctx)


@ui_router.get("/partials/repo/{repo_id}", response_class=HTMLResponse)
async def partial_repo_detail(request: Request, repo_id: str) -> Response:
    """Render repo detail partial."""
    repo_repo = get_repo_repository()
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)

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
        "repo": row.repo,
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
        },
    }

    ctx = {
        "request": request,
        "repo": repo_data,
        "current_user_id": user_id,
        "can_update_profile": _has_permission(role, Permission.UPDATE_REPO_PROFILE),
        "can_change_tier": _has_permission(role, Permission.CHANGE_REPO_TIER),
        "can_pause": _has_permission(role, Permission.PAUSE_REPO),
        "can_toggle_writes": _has_permission(role, Permission.TOGGLE_WRITES),
        "can_delete": _has_permission(role, Permission.REGISTER_REPO),
    }
    return templates.TemplateResponse(request, "partials/repo_detail_content.html", ctx)


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
        workflows.append({
            "id": str(wf.workflow_id),
            "repo_id": wf.repo_id,
            "repo_name": getattr(wf, "repo_name", wf.repo_id),
            "status": wf.status.value,
            "current_step": getattr(wf, "current_step", None),
            "attempt_count": getattr(wf, "attempt_count", 1),
        })

    ctx = {"request": request, "workflows": workflows}
    return templates.TemplateResponse(request, "partials/workflows_list.html", ctx)


@ui_router.get("/partials/workflow/{workflow_id}", response_class=HTMLResponse)
async def partial_workflow_detail(request: Request, workflow_id: str) -> Response:
    """Render workflow detail partial."""
    console_svc = get_workflow_console_service()
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)

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
        step_status = (
            step.status.value if hasattr(step.status, "value") else str(step.status)
        )
        evidence_str = None
        if step.evidence:
            evidence_str = (
                "\n".join(step.evidence)
                if isinstance(step.evidence, list)
                else str(step.evidence)
            )
        timeline.append({
            "name": step.step,
            "status": step_status,
            "timestamp": str(step.started_at or ""),
            "failure_reason": step.failure_reason,
            "evidence": evidence_str,
        })

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
        "current_user_id": user_id,
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
        entries.append({
            "timestamp": str(row.timestamp),
            "actor": row.actor,
            "event_type": (
                row.event_type.value
                if hasattr(row.event_type, "value")
                else str(row.event_type)
            ),
            "target_id": str(row.target_id) if row.target_id else None,
            "details": row.details,
        })

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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    svc = get_expert_service()
    detail = svc.get_expert(expert_id)

    if detail is None:
        ctx = _base_context(request, role)
        ctx["active_page"] = "experts"
        ctx["detail"] = "Expert not found"
        return templates.TemplateResponse(request, "error.html", ctx)

    ctx = _base_context(request, role)
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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
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
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
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


# --- Compliance Scorecard Routes (Story 7.12) ---


@ui_router.get("/compliance", response_class=HTMLResponse)
async def compliance_page(request: Request) -> Response:
    """Render Compliance Scorecard page."""
    user_id = request.headers.get("X-User-ID")
    role = await _resolve_role(user_id)
    ctx = _base_context(request, role)
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
