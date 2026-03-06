"""Compliance API router — endpoints for tier promotion and compliance checks.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Execute Tier Compliance Gate, Repo Registration Lifecycle)
"""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.promotion import (
    PromotionBlockReason,
    PromotionService,
)
from src.repo.repo_profile import RepoTier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["compliance"])


class PromotionRequest(BaseModel):
    """Request to promote a repo to a target tier."""

    target_tier: RepoTier
    triggered_by: str = "api"


class PromotionResponse(BaseModel):
    """Response from a promotion request."""

    success: bool
    repo_id: UUID
    from_tier: RepoTier
    to_tier: RepoTier
    compliance_score: float | None = None
    block_reason: PromotionBlockReason | None = None
    block_details: str | None = None
    message: str


class DemotionRequest(BaseModel):
    """Request to demote a repo to a lower tier."""

    target_tier: RepoTier
    reason: str
    triggered_by: str = "api"


class DemotionResponse(BaseModel):
    """Response from a demotion request."""

    success: bool
    repo_id: UUID
    from_tier: RepoTier
    to_tier: RepoTier
    reason: str
    message: str


class ComplianceCheckResponse(BaseModel):
    """Response from a compliance check."""

    repo_id: UUID
    overall_passed: bool
    score: float = Field(ge=0.0, le=100.0)
    checks: list[dict[str, Any]]
    triggered_by: str


class EligibilityResponse(BaseModel):
    """Response from an eligibility check."""

    repo_id: UUID
    target_tier: RepoTier
    eligible: bool
    block_reason: PromotionBlockReason | None = None
    block_details: str | None = None
    compliance_score: float | None = None


class RepoRegistrationRequest(BaseModel):
    """Request to register a new repository."""

    owner: str
    repo: str
    installation_id: int
    default_branch: str = "main"


class RepoRegistrationResponse(BaseModel):
    """Response from repo registration."""

    id: UUID
    owner: str
    repo: str
    tier: RepoTier
    installation_id: int
    message: str


class RepoInfo(BaseModel):
    """Information about a registered repository."""

    id: UUID
    owner: str
    repo: str
    tier: RepoTier
    installation_id: int
    full_name: str


class RepoListResponse(BaseModel):
    """Response from listing repos."""

    repos: list[RepoInfo]
    total: int
    by_tier: dict[str, int]


# In-memory repo registry for testing (will be replaced with database)
_repos: dict[UUID, dict[str, Any]] = {}


def register_repo(
    repo_id: UUID,
    owner: str,
    repo: str,
    tier: RepoTier = RepoTier.OBSERVE,
    repo_info: GitHubRepoInfo | None = None,
    installation_id: int = 0,
) -> dict[str, Any]:
    """Register a repo (in-memory stub)."""
    full_name = f"{owner}/{repo}"
    _repos[repo_id] = {
        "id": repo_id,
        "owner": owner,
        "repo": repo,
        "full_name": full_name,
        "tier": tier,
        "installation_id": installation_id,
        "repo_info": repo_info or GitHubRepoInfo(
            owner=owner,
            repo=repo,
            default_branch="main",
            rulesets=[],
            branch_protection=None,
            labels=[],
            codeowners_exists=False,
            codeowners_paths=[],
        ),
    }
    return _repos[repo_id]


def get_repo(repo_id: UUID) -> dict[str, Any] | None:
    """Get repo by ID (in-memory stub)."""
    return _repos.get(repo_id)


def update_repo_tier(repo_id: UUID, tier: RepoTier) -> None:
    """Update repo tier (in-memory stub)."""
    if repo_id in _repos:
        _repos[repo_id]["tier"] = tier


def clear() -> None:
    """Clear all repos (for testing)."""
    _repos.clear()


def list_repos() -> list[dict[str, Any]]:
    """List all registered repos."""
    return list(_repos.values())


def get_repo_by_full_name(full_name: str) -> dict[str, Any] | None:
    """Get repo by full name (owner/repo)."""
    for repo in _repos.values():
        if repo["full_name"] == full_name:
            return repo
    return None


def count_repos_by_tier() -> dict[str, int]:
    """Count repos by tier."""
    counts: dict[str, int] = {}
    for repo in _repos.values():
        tier_value = repo["tier"].value
        counts[tier_value] = counts.get(tier_value, 0) + 1
    return counts


# Service instances (can be overridden for testing)
_promotion_service: PromotionService | None = None
_compliance_checker: ComplianceChecker | None = None


def get_promotion_service() -> PromotionService:
    """Get or create promotion service."""
    global _promotion_service
    if _promotion_service is None:
        _promotion_service = PromotionService(
            compliance_checker=get_compliance_checker(),
            repo_profile_updater=update_repo_tier,
        )
    return _promotion_service


def get_compliance_checker() -> ComplianceChecker:
    """Get or create compliance checker."""
    global _compliance_checker
    if _compliance_checker is None:
        _compliance_checker = ComplianceChecker()
    return _compliance_checker


def set_promotion_service(service: PromotionService | None) -> None:
    """Set promotion service (for testing)."""
    global _promotion_service
    _promotion_service = service


def set_compliance_checker(checker: ComplianceChecker | None) -> None:
    """Set compliance checker (for testing)."""
    global _compliance_checker
    _compliance_checker = checker


@router.post("/{repo_id}/promote", response_model=PromotionResponse)
async def promote_repo(repo_id: UUID, request: PromotionRequest) -> PromotionResponse:
    """Promote a repo to a target tier.

    The promotion is gated on compliance check results for Execute tier.
    """
    repo = get_repo(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    service = get_promotion_service()

    result = await service.request_promotion(
        repo_id=repo_id,
        target_tier=request.target_tier,
        triggered_by=request.triggered_by,
        repo_info=repo["repo_info"],
        current_tier=repo["tier"],
    )

    if result.success:
        message = (
            f"Promoted {repo['owner']}/{repo['repo']} from "
            f"{result.from_tier.value} to {result.to_tier.value}"
        )
    else:
        message = f"Promotion blocked: {result.block_details}"

    return PromotionResponse(
        success=result.success,
        repo_id=repo_id,
        from_tier=result.from_tier,
        to_tier=result.to_tier,
        compliance_score=result.compliance_score,
        block_reason=result.block_reason,
        block_details=result.block_details,
        message=message,
    )


@router.post("/{repo_id}/demote", response_model=DemotionResponse)
async def demote_repo(repo_id: UUID, request: DemotionRequest) -> DemotionResponse:
    """Demote a repo to a lower tier."""
    repo = get_repo(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    service = get_promotion_service()

    result = await service.demote_tier(
        repo_id=repo_id,
        target_tier=request.target_tier,
        reason=request.reason,
        triggered_by=request.triggered_by,
        current_tier=repo["tier"],
    )

    if result.success:
        message = (
            f"Demoted {repo['owner']}/{repo['repo']} from "
            f"{result.from_tier.value} to {result.to_tier.value}"
        )
    else:
        message = f"Demotion failed: {result.reason}"

    return DemotionResponse(
        success=result.success,
        repo_id=repo_id,
        from_tier=result.from_tier,
        to_tier=result.to_tier,
        reason=result.reason,
        message=message,
    )


@router.get("/{repo_id}/compliance", response_model=ComplianceCheckResponse)
async def check_compliance(repo_id: UUID) -> ComplianceCheckResponse:
    """Run compliance check for a repo."""
    repo = get_repo(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    checker = get_compliance_checker()

    result = await checker.check_compliance(
        repo_id=repo_id,
        repo_info=repo["repo_info"],
        triggered_by="api",
        check_execution_plane=True,
    )

    return ComplianceCheckResponse(
        repo_id=repo_id,
        overall_passed=result.overall_passed,
        score=result.score,
        checks=[
            {
                "check": c.check.value,
                "passed": c.passed,
                "failure_reason": c.failure_reason,
                "remediation_hint": c.remediation_hint,
            }
            for c in result.checks
        ],
        triggered_by=result.triggered_by,
    )


@router.get("/{repo_id}/eligibility/{target_tier}", response_model=EligibilityResponse)
async def check_eligibility(repo_id: UUID, target_tier: RepoTier) -> EligibilityResponse:
    """Check if a repo is eligible for promotion to a target tier."""
    repo = get_repo(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    service = get_promotion_service()

    result = await service.check_promotion_eligibility(
        repo_id=repo_id,
        target_tier=target_tier,
        repo_info=repo["repo_info"],
        current_tier=repo["tier"],
    )

    return EligibilityResponse(
        repo_id=repo_id,
        target_tier=target_tier,
        eligible=result.eligible,
        block_reason=result.block_reason,
        block_details=result.block_details,
        compliance_score=(
            result.compliance_result.score if result.compliance_result else None
        ),
    )


@router.post("/register", response_model=RepoRegistrationResponse)
async def register_new_repo(request: RepoRegistrationRequest) -> RepoRegistrationResponse:
    """Register a new repository.

    New repos start at Observe tier. Promotion to Execute requires compliance check.
    """
    full_name = f"{request.owner}/{request.repo}"

    # Check if repo already registered
    existing = get_repo_by_full_name(full_name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository {full_name} is already registered",
        )

    repo_id = uuid4()
    repo_info = GitHubRepoInfo(
        owner=request.owner,
        repo=request.repo,
        default_branch=request.default_branch,
        rulesets=[],
        branch_protection=None,
        labels=[],
        codeowners_exists=False,
        codeowners_paths=[],
    )

    register_repo(
        repo_id=repo_id,
        owner=request.owner,
        repo=request.repo,
        tier=RepoTier.OBSERVE,
        repo_info=repo_info,
        installation_id=request.installation_id,
    )

    logger.info(
        "Registered repo %s with ID %s at Observe tier",
        full_name,
        repo_id,
    )

    return RepoRegistrationResponse(
        id=repo_id,
        owner=request.owner,
        repo=request.repo,
        tier=RepoTier.OBSERVE,
        installation_id=request.installation_id,
        message=f"Registered {full_name} at Observe tier",
    )


@router.get("", response_model=RepoListResponse)
async def list_registered_repos() -> RepoListResponse:
    """List all registered repositories."""
    repos = list_repos()
    by_tier = count_repos_by_tier()

    return RepoListResponse(
        repos=[
            RepoInfo(
                id=r["id"],
                owner=r["owner"],
                repo=r["repo"],
                tier=r["tier"],
                installation_id=r["installation_id"],
                full_name=r["full_name"],
            )
            for r in repos
        ],
        total=len(repos),
        by_tier=by_tier,
    )


@router.get("/{repo_id}", response_model=RepoInfo)
async def get_repo_info(repo_id: UUID) -> RepoInfo:
    """Get information about a specific repository."""
    repo = get_repo(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    return RepoInfo(
        id=repo["id"],
        owner=repo["owner"],
        repo=repo["repo"],
        tier=repo["tier"],
        installation_id=repo["installation_id"],
        full_name=repo["full_name"],
    )
