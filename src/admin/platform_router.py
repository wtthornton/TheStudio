"""Platform Maturity API router — Tool Hub, Model Gateway, Compliance, Targets.

Story 7.3: Tool Hub API & Audit
Story 7.6: Model Gateway API & Audit
Story 7.8: Compliance Scorecard API & Promotion Gate
Story 7.9: Operational Targets API
Architecture reference: thestudioarc/25-tool-hub-mcp-toolkit.md,
    thestudioarc/26-model-runtime-and-routing.md,
    thestudioarc/23-admin-control-ui.md
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin.compliance_scorecard import RepoComplianceData, get_scorecard_service
from src.admin.model_gateway import (
    BudgetSpec,
    get_budget_enforcer,
    get_model_audit_store,
    get_model_router,
)
from src.admin.operational_targets import get_targets_service
from src.admin.rbac import Permission, get_current_user_id, require_permission
from src.admin.tool_catalog import get_tool_catalog, get_tool_policy_engine

logger = logging.getLogger(__name__)
platform_router = APIRouter(prefix="/admin", tags=["platform"])


# ============================================================
# Tool Hub API (Story 7.3)
# ============================================================


@platform_router.get(
    "/tools/catalog",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def list_tool_catalog(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """List all tool suites in the catalog."""
    catalog = get_tool_catalog()
    suites = catalog.list_suites()
    return {
        "suites": [s.to_dict() for s in suites],
        "total": len(suites),
    }


@platform_router.get(
    "/tools/catalog/{suite_name}",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def get_tool_suite(
    suite_name: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Get details of a specific tool suite."""
    catalog = get_tool_catalog()
    try:
        suite = catalog.get_suite(suite_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Suite '{suite_name}' not found") from exc
    return suite.to_dict()


@platform_router.post(
    "/tools/catalog/{suite_name}/promote",
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def promote_tool_suite(
    suite_name: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Promote a tool suite to the next approval status."""
    catalog = get_tool_catalog()
    try:
        suite = catalog.promote_suite(suite_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    logger.info("Tool suite promoted: %s -> %s by %s", suite_name, suite.approval_status.value, user_id)
    return suite.to_dict()


@platform_router.get(
    "/tools/profiles",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def list_tool_profiles(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """List default tool profiles."""
    from src.admin.tool_catalog import DEFAULT_PROFILES
    return {
        "profiles": [p.to_dict() for p in DEFAULT_PROFILES],
        "total": len(DEFAULT_PROFILES),
    }


class CheckAccessRequest(BaseModel):
    """Request body for checking tool access by role and overlays."""

    role: str
    overlays: list[str] = Field(default_factory=list)
    repo_tier: str = "suggest"
    suite_name: str
    tool_name: str


@platform_router.post(
    "/tools/check-access",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def check_tool_access(
    request: CheckAccessRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Check if a tool call is allowed by policy."""
    engine = get_tool_policy_engine()
    decision = engine.check_access(
        role=request.role,
        overlays=request.overlays,
        repo_tier=request.repo_tier,
        suite_name=request.suite_name,
        tool_name=request.tool_name,
    )
    return decision.to_dict()


# ============================================================
# Model Gateway API (Story 7.6)
# ============================================================


class RouteRequest(BaseModel):
    """Request body for simulating a model routing decision."""

    step: str
    role: str = ""
    overlays: list[str] = Field(default_factory=list)
    repo_tier: str = ""
    complexity: str = ""


@platform_router.post(
    "/models/route",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def route_model(
    request: RouteRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Simulate a model routing decision."""
    router = get_model_router()
    try:
        provider = router.select_model(
            step=request.step,
            role=request.role,
            overlays=request.overlays,
            repo_tier=request.repo_tier,
            complexity=request.complexity,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {
        "selected": provider.to_dict(),
        "resolved_class": provider.model_class.value,
        "step": request.step,
    }


@platform_router.get(
    "/models/providers",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def list_providers(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """List all model provider configurations."""
    router = get_model_router()
    providers = router.providers
    return {
        "providers": [p.to_dict() for p in providers],
        "total": len(providers),
    }


@platform_router.patch(
    "/models/providers/{provider_id}",
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def update_provider(
    provider_id: str,
    enabled: bool = Query(...),
    user_id: Annotated[str, Depends(get_current_user_id)] = "",
) -> dict[str, Any]:
    """Enable or disable a model provider."""
    router = get_model_router()
    try:
        provider = router.set_provider_enabled(provider_id, enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found") from exc
    logger.info("Provider %s set enabled=%s by %s", provider_id, enabled, user_id)
    return provider.to_dict()


@platform_router.get(
    "/models/audit",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def query_model_audit(
    user_id: Annotated[str, Depends(get_current_user_id)],
    task_id: str | None = Query(None),
    step: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Query model call audit records."""
    store = get_model_audit_store()
    records = store.query(task_id=task_id, step=step, provider=provider, limit=limit)
    return {
        "records": [r.to_dict() for r in records],
        "total": len(records),
    }


class SetBudgetRequest(BaseModel):
    """Request body for setting model spend budget on a repo."""

    per_task_max_spend: float = Field(1.0, gt=0)
    per_step_token_cap: int = Field(50_000, gt=0)
    conservative_mode: bool = False


@platform_router.post(
    "/models/budget/{repo_id}",
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def set_repo_budget(
    repo_id: str,
    request: SetBudgetRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Set model budget for a repo."""
    enforcer = get_budget_enforcer()
    budget = BudgetSpec(
        per_task_max_spend=request.per_task_max_spend,
        per_step_token_cap=request.per_step_token_cap,
        conservative_mode=request.conservative_mode,
    )
    enforcer.set_budget(repo_id, budget)
    logger.info("Budget set for repo %s by %s: %s", repo_id, user_id, budget.to_dict())
    return {"repo_id": repo_id, "budget": budget.to_dict()}


# ============================================================
# Compliance Scorecard API (Story 7.8)
# ============================================================


@platform_router.get(
    "/repos/{repo_id}/compliance",
    dependencies=[Depends(require_permission(Permission.VIEW_REPOS))],
)
async def get_compliance_scorecard(
    repo_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Run and return compliance scorecard for a repo."""
    service = get_scorecard_service()
    scorecard = service.evaluate(repo_id)
    return scorecard.to_dict()


class EvaluateComplianceRequest(BaseModel):
    """Explicit compliance data for evaluation (for testing/override)."""
    branch_protection_enabled: bool = False
    required_reviewers_configured: bool = False
    standard_labels_present: bool = False
    projects_v2_configured: bool = False
    evidence_format_valid: bool = False
    idempotency_guard_active: bool = False
    execution_plane_healthy: bool = False
    execute_tier_policy_passed: bool = False


@platform_router.post(
    "/repos/{repo_id}/compliance/evaluate",
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def evaluate_compliance(
    repo_id: str,
    request: EvaluateComplianceRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, Any]:
    """Evaluate compliance with explicit data (admin override)."""
    service = get_scorecard_service()
    data = RepoComplianceData(
        branch_protection_enabled=request.branch_protection_enabled,
        required_reviewers_configured=request.required_reviewers_configured,
        standard_labels_present=request.standard_labels_present,
        projects_v2_configured=request.projects_v2_configured,
        evidence_format_valid=request.evidence_format_valid,
        idempotency_guard_active=request.idempotency_guard_active,
        execution_plane_healthy=request.execution_plane_healthy,
        execute_tier_policy_passed=request.execute_tier_policy_passed,
    )
    scorecard = service.evaluate(repo_id, data)
    return scorecard.to_dict()


# ============================================================
# Operational Targets API (Story 7.9)
# ============================================================


@platform_router.get(
    "/metrics/lead-time",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def get_lead_time(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: str | None = Query(None),
) -> dict[str, Any]:
    """Get lead time metrics (intake to PR opened)."""
    service = get_targets_service()
    result = service.get_lead_time(repo_filter=repo)
    return result.to_dict()


@platform_router.get(
    "/metrics/cycle-time",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def get_cycle_time(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: str | None = Query(None),
) -> dict[str, Any]:
    """Get cycle time metrics (PR opened to merge-ready)."""
    service = get_targets_service()
    result = service.get_cycle_time(repo_filter=repo)
    return result.to_dict()


@platform_router.get(
    "/metrics/reopen-target",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def get_reopen_target(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: str | None = Query(None),
) -> dict[str, Any]:
    """Get reopen rate vs <5% target."""
    service = get_targets_service()
    result = service.get_reopen_target(repo_filter=repo)
    if not result.met and not result.insufficient_data:
        logger.warning(
            "Reopen target NOT MET: rate=%.3f target=%.3f samples=%d",
            result.current_rate,
            result.target,
            result.sample_count,
        )
    return result.to_dict()


# ============================================================
# Expert Management API (Epic 26, Story 26.5)
# ============================================================


class ExpertSummary(BaseModel):
    """Response model for expert list endpoint."""

    id: str
    name: str
    expert_class: str
    capability_tags: list[str]
    trust_tier: str
    lifecycle_state: str
    current_version: int
    source_path: str | None = None
    version_hash: str | None = None
    updated_at: str


class ExpertReloadResponse(BaseModel):
    """Response model for expert reload endpoint."""

    created: list[str]
    updated: list[str]
    unchanged: list[str]
    deactivated: list[str]
    errors: list[str]
    scan_errors: list[dict[str, str]]


@platform_router.post(
    "/experts/reload",
    dependencies=[Depends(require_permission(Permission.CHANGE_REPO_TIER))],
)
async def reload_experts(
    user_id: Annotated[str, Depends(get_current_user_id)],
    deactivate_removed: bool = Query(False),
) -> ExpertReloadResponse:
    """Re-scan expert directories and sync changes to the database."""
    from src.db.connection import get_async_session
    from src.experts.config import get_experts_base_path
    from src.experts.registrar import sync_experts
    from src.experts.scanner import scan_expert_directories

    experts_path = get_experts_base_path()
    if not experts_path.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Experts directory not found: {experts_path}",
        )

    scan_result = scan_expert_directories(experts_path)
    scan_errors = [
        {"directory": str(e.directory), "error": e.error}
        for e in scan_result.errors
    ]

    async with get_async_session() as session:
        sync_result = await sync_experts(
            session, scan_result.experts, deactivate_removed
        )

    logger.info(
        "Expert reload by %s: created=%d updated=%d unchanged=%d",
        user_id,
        len(sync_result.created),
        len(sync_result.updated),
        len(sync_result.unchanged),
    )

    return ExpertReloadResponse(
        created=sync_result.created,
        updated=sync_result.updated,
        unchanged=sync_result.unchanged,
        deactivated=sync_result.deactivated,
        errors=sync_result.errors,
        scan_errors=scan_errors,
    )


@platform_router.get(
    "/experts/registry",
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def list_experts_registry(
    user_id: Annotated[str, Depends(get_current_user_id)],
    expert_class: str | None = Query(None, alias="class"),
) -> dict[str, Any]:
    """List all registered experts with source and version metadata."""
    from src.db.connection import get_async_session
    from src.experts.expert import ExpertClass as ExpertClassEnum
    from src.experts.expert_crud import get_expert_versions, search_experts

    ec_filter = None
    if expert_class:
        try:
            ec_filter = ExpertClassEnum(expert_class)
        except ValueError as err:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid expert class: {expert_class}",
            ) from err

    async with get_async_session() as session:
        experts = await search_experts(
            session,
            expert_class=ec_filter,
            include_deprecated=True,
        )
        summaries = []
        for expert in experts:
            versions = await get_expert_versions(session, expert.id)
            source_path = None
            version_hash = None
            if versions:
                latest = max(versions, key=lambda v: v.version)
                source_path = latest.definition.get("_source_path")
                version_hash = latest.definition.get("_version_hash")

            summaries.append(
                ExpertSummary(
                    id=str(expert.id),
                    name=expert.name,
                    expert_class=expert.expert_class.value,
                    capability_tags=expert.capability_tags,
                    trust_tier=expert.trust_tier.value,
                    lifecycle_state=expert.lifecycle_state.value,
                    current_version=expert.current_version,
                    source_path=source_path,
                    version_hash=version_hash,
                    updated_at=expert.updated_at.isoformat(),
                )
            )

    return {
        "experts": [s.model_dump() for s in summaries],
        "total": len(summaries),
    }
