"""Compliance API router — endpoints for tier promotion and compliance checks.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Execute Tier Compliance Gate, Repo Registration Lifecycle)

Story 4.1: Updated to use database-backed repository.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.promotion import (
    PromotionBlockReason,
    PromotionService,
)
from src.repo.repo_profile import RepoProfileCreate, RepoStatus, RepoTier

if TYPE_CHECKING:
    from src.repo.repo_profile import RepoProfileRow
    from src.repo.repository import RepoRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["compliance"])


def _get_repo_repository() -> RepoRepository:
    """Lazy import of RepoRepository to avoid database connection at import time."""
    from src.repo.repository import RepoRepository
    return RepoRepository()


async def get_db_session() -> Any:
    """Get database session with lazy import."""
    from src.db.connection import get_session
    async for session in get_session():
        yield session


# Repository instance (lazy initialization)
_repo_repository: RepoRepository | None = None


def get_repo_repository() -> RepoRepository:
    """Get or create repository instance."""
    global _repo_repository
    if _repo_repository is None:
        _repo_repository = _get_repo_repository()
    return _repo_repository


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
    webhook_secret: str = ""


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
    status: RepoStatus
    installation_id: int
    full_name: str
    writes_enabled: bool = True


class RepoListResponse(BaseModel):
    """Response from listing repos."""

    repos: list[RepoInfo]
    total: int
    by_tier: dict[str, int]


def _create_github_repo_info(row: RepoProfileRow) -> GitHubRepoInfo:
    """Create GitHubRepoInfo from repo profile for compliance checking.

    Note: This creates a minimal GitHubRepoInfo. In production, you would
    fetch actual GitHub metadata via the API. For compliance checking,
    the real data comes from GitHub API calls.
    """
    return GitHubRepoInfo(
        owner=row.owner,
        repo=row.repo_name,
        default_branch=row.default_branch,
        rulesets=[],
        branch_protection=None,
        labels=[],
        codeowners_exists=False,
        codeowners_paths=[],
    )


# Service instances (can be overridden for testing)
_promotion_service: PromotionService | None = None
_compliance_checker: ComplianceChecker | None = None


def get_compliance_checker() -> ComplianceChecker:
    """Get or create compliance checker."""
    global _compliance_checker
    if _compliance_checker is None:
        _compliance_checker = ComplianceChecker()
    return _compliance_checker


def set_compliance_checker(checker: ComplianceChecker | None) -> None:
    """Set compliance checker (for testing)."""
    global _compliance_checker
    _compliance_checker = checker


# Legacy in-memory registry for backward compatibility during migration
# These will be removed once all tests are migrated to use database
_repos: dict[UUID, dict[str, Any]] = {}
_use_in_memory: bool = False


def set_use_in_memory(use: bool) -> None:
    """Set whether to use in-memory registry (for testing)."""
    global _use_in_memory
    _use_in_memory = use


def register_repo(
    repo_id: UUID,
    owner: str,
    repo: str,
    tier: RepoTier = RepoTier.OBSERVE,
    repo_info: GitHubRepoInfo | None = None,
    installation_id: int = 0,
) -> dict[str, Any]:
    """Register a repo (in-memory stub for testing)."""
    full_name = f"{owner}/{repo}"
    _repos[repo_id] = {
        "id": repo_id,
        "owner": owner,
        "repo": repo,
        "full_name": full_name,
        "tier": tier,
        "status": RepoStatus.ACTIVE,
        "installation_id": installation_id,
        "writes_enabled": True,
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
    """Get repo by ID (in-memory stub for testing)."""
    return _repos.get(repo_id)


def update_repo_tier(repo_id: UUID, tier: RepoTier) -> None:
    """Update repo tier (in-memory stub for testing)."""
    if repo_id in _repos:
        _repos[repo_id]["tier"] = tier


def clear() -> None:
    """Clear all repos (for testing)."""
    _repos.clear()


def list_repos() -> list[dict[str, Any]]:
    """List all registered repos (in-memory stub for testing)."""
    return list(_repos.values())


def get_repo_by_full_name(full_name: str) -> dict[str, Any] | None:
    """Get repo by full name (in-memory stub for testing)."""
    for repo in _repos.values():
        if repo["full_name"] == full_name:
            return repo
    return None


def count_repos_by_tier() -> dict[str, int]:
    """Count repos by tier (in-memory stub for testing)."""
    counts: dict[str, int] = {}
    for repo in _repos.values():
        tier_value = repo["tier"].value
        counts[tier_value] = counts.get(tier_value, 0) + 1
    return counts


def get_promotion_service() -> PromotionService:
    """Get or create promotion service (uses in-memory tier updater)."""
    global _promotion_service
    if _promotion_service is None:
        _promotion_service = PromotionService(
            compliance_checker=get_compliance_checker(),
            repo_profile_updater=update_repo_tier,
        )
    return _promotion_service


def set_promotion_service(service: PromotionService | None) -> None:
    """Set promotion service (for testing)."""
    global _promotion_service
    _promotion_service = service


@router.post("/{repo_id}/promote", response_model=PromotionResponse)
async def promote_repo(
    repo_id: UUID,
    request: PromotionRequest,
    session: Any = Depends(get_db_session),
) -> PromotionResponse:
    """Promote a repo to a target tier.

    The promotion is gated on compliance check results for Execute tier.
    """
    if _use_in_memory:
        repo_data = get_repo(repo_id)
        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = repo_data["repo_info"]
        current_tier = repo_data["tier"]
        owner = repo_data["owner"]
        repo_name = repo_data["repo"]
    else:
        repo_repository = get_repo_repository()
        repo = await repo_repository.get(session, repo_id)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = _create_github_repo_info(repo)
        current_tier = repo.tier
        owner = repo.owner
        repo_name = repo.repo_name

    service = get_promotion_service()

    result = await service.request_promotion(
        repo_id=repo_id,
        target_tier=request.target_tier,
        triggered_by=request.triggered_by,
        repo_info=repo_info,
        current_tier=current_tier,
    )

    if not _use_in_memory and result.success:
        repo_repository = get_repo_repository()
        await repo_repository.update_tier(session, repo_id, result.to_tier)
        await session.commit()

    if result.success:
        message = (
            f"Promoted {owner}/{repo_name} from "
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
async def demote_repo(
    repo_id: UUID,
    request: DemotionRequest,
    session: Any = Depends(get_db_session),
) -> DemotionResponse:
    """Demote a repo to a lower tier."""
    if _use_in_memory:
        repo_data = get_repo(repo_id)
        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        current_tier = repo_data["tier"]
        owner = repo_data["owner"]
        repo_name = repo_data["repo"]
    else:
        repo_repository = get_repo_repository()
        repo = await repo_repository.get(session, repo_id)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        current_tier = repo.tier
        owner = repo.owner
        repo_name = repo.repo_name

    service = get_promotion_service()

    result = await service.demote_tier(
        repo_id=repo_id,
        target_tier=request.target_tier,
        reason=request.reason,
        triggered_by=request.triggered_by,
        current_tier=current_tier,
    )

    if not _use_in_memory and result.success:
        repo_repository = get_repo_repository()
        await repo_repository.update_tier(session, repo_id, result.to_tier)
        await session.commit()

    if result.success:
        message = (
            f"Demoted {owner}/{repo_name} from "
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
async def check_compliance(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> ComplianceCheckResponse:
    """Run compliance check for a repo."""
    if _use_in_memory:
        repo_data = get_repo(repo_id)
        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = repo_data["repo_info"]
    else:
        repo_repository = get_repo_repository()
        repo = await repo_repository.get(session, repo_id)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = _create_github_repo_info(repo)

    checker = get_compliance_checker()

    result = await checker.check_compliance(
        repo_id=repo_id,
        repo_info=repo_info,
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
async def check_eligibility(
    repo_id: UUID,
    target_tier: RepoTier,
    session: Any = Depends(get_db_session),
) -> EligibilityResponse:
    """Check if a repo is eligible for promotion to a target tier."""
    if _use_in_memory:
        repo_data = get_repo(repo_id)
        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = repo_data["repo_info"]
        current_tier = repo_data["tier"]
    else:
        repo_repository = get_repo_repository()
        repo = await repo_repository.get(session, repo_id)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        repo_info = _create_github_repo_info(repo)
        current_tier = repo.tier

    service = get_promotion_service()

    result = await service.check_promotion_eligibility(
        repo_id=repo_id,
        target_tier=target_tier,
        repo_info=repo_info,
        current_tier=current_tier,
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
async def register_new_repo(
    request: RepoRegistrationRequest,
    session: Any = Depends(get_db_session),
) -> RepoRegistrationResponse:
    """Register a new repository.

    New repos start at Observe tier. Promotion to Execute requires compliance check.
    """
    full_name = f"{request.owner}/{request.repo}"

    if _use_in_memory:
        existing = get_repo_by_full_name(full_name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Repository {full_name} is already registered",
            )

        from uuid import uuid4
        repo_id = uuid4()
        repo_info_obj = GitHubRepoInfo(
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
            repo_info=repo_info_obj,
            installation_id=request.installation_id,
        )
    else:
        from src.repo.repository import RepoDuplicateError
        repo_repository = get_repo_repository()
        try:
            create_data = RepoProfileCreate(
                owner=request.owner,
                repo_name=request.repo,
                installation_id=request.installation_id,
                default_branch=request.default_branch,
                webhook_secret=request.webhook_secret or "placeholder",
            )
            repo = await repo_repository.create(session, create_data)
            await session.commit()
            repo_id = repo.id
        except RepoDuplicateError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Repository {full_name} is already registered",
            ) from err

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
async def list_registered_repos(
    session: Any = Depends(get_db_session),
) -> RepoListResponse:
    """List all registered repositories."""
    if _use_in_memory:
        repos_data = list_repos()
        by_tier = count_repos_by_tier()
        return RepoListResponse(
            repos=[
                RepoInfo(
                    id=r["id"],
                    owner=r["owner"],
                    repo=r["repo"],
                    tier=r["tier"],
                    status=r.get("status", RepoStatus.ACTIVE),
                    installation_id=r["installation_id"],
                    full_name=r["full_name"],
                    writes_enabled=r.get("writes_enabled", True),
                )
                for r in repos_data
            ],
            total=len(repos_data),
            by_tier=by_tier,
        )

    repo_repository = get_repo_repository()
    repos = await repo_repository.list_all(session)
    by_tier = await repo_repository.count_by_tier(session)

    return RepoListResponse(
        repos=[
            RepoInfo(
                id=r.id,
                owner=r.owner,
                repo=r.repo_name,
                tier=r.tier,
                status=r.status,
                installation_id=r.installation_id,
                full_name=r.full_name,
                writes_enabled=r.writes_enabled,
            )
            for r in repos
        ],
        total=len(repos),
        by_tier=by_tier,
    )


@router.get("/{repo_id}", response_model=RepoInfo)
async def get_repo_info(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> RepoInfo:
    """Get information about a specific repository."""
    if _use_in_memory:
        repo_data = get_repo(repo_id)
        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        return RepoInfo(
            id=repo_data["id"],
            owner=repo_data["owner"],
            repo=repo_data["repo"],
            tier=repo_data["tier"],
            status=repo_data.get("status", RepoStatus.ACTIVE),
            installation_id=repo_data["installation_id"],
            full_name=repo_data["full_name"],
            writes_enabled=repo_data.get("writes_enabled", True),
        )

    repo_repository = get_repo_repository()
    repo = await repo_repository.get(session, repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    return RepoInfo(
        id=repo.id,
        owner=repo.owner,
        repo=repo.repo_name,
        tier=repo.tier,
        status=repo.status,
        installation_id=repo.installation_id,
        full_name=repo.full_name,
        writes_enabled=repo.writes_enabled,
    )


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_repo(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> None:
    """Soft-delete a repository.

    The repo is marked as deleted but retained for audit trail.
    """
    if _use_in_memory:
        if repo_id not in _repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        del _repos[repo_id]
        return

    from src.repo.repository import RepoNotFoundError
    repo_repository = get_repo_repository()
    try:
        await repo_repository.soft_delete(session, repo_id)
        await session.commit()
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err


@router.post("/{repo_id}/pause", status_code=status.HTTP_200_OK)
async def pause_repo(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> dict[str, str]:
    """Pause a repository (stop accepting new tasks)."""
    if _use_in_memory:
        if repo_id not in _repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        _repos[repo_id]["status"] = RepoStatus.PAUSED
        return {"message": f"Repository {repo_id} paused"}

    from src.repo.repository import RepoNotFoundError
    repo_repository = get_repo_repository()
    try:
        repo = await repo_repository.update_status(session, repo_id, RepoStatus.PAUSED)
        await session.commit()
        return {"message": f"Repository {repo.full_name} paused"}
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err


@router.post("/{repo_id}/resume", status_code=status.HTTP_200_OK)
async def resume_repo(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> dict[str, str]:
    """Resume a paused repository."""
    if _use_in_memory:
        if repo_id not in _repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        _repos[repo_id]["status"] = RepoStatus.ACTIVE
        return {"message": f"Repository {repo_id} resumed"}

    from src.repo.repository import RepoNotFoundError
    repo_repository = get_repo_repository()
    try:
        repo = await repo_repository.update_status(session, repo_id, RepoStatus.ACTIVE)
        await session.commit()
        return {"message": f"Repository {repo.full_name} resumed"}
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err


@router.post("/{repo_id}/disable-writes", status_code=status.HTTP_200_OK)
async def disable_writes(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> dict[str, str]:
    """Disable writes for a repository (Publisher freeze)."""
    if _use_in_memory:
        if repo_id not in _repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        _repos[repo_id]["writes_enabled"] = False
        return {"message": f"Writes disabled for repository {repo_id}"}

    from src.repo.repository import RepoNotFoundError
    repo_repository = get_repo_repository()
    try:
        repo = await repo_repository.set_writes_enabled(session, repo_id, enabled=False)
        await session.commit()
        return {"message": f"Writes disabled for repository {repo.full_name}"}
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err


@router.post("/{repo_id}/enable-writes", status_code=status.HTTP_200_OK)
async def enable_writes(
    repo_id: UUID,
    session: Any = Depends(get_db_session),
) -> dict[str, str]:
    """Enable writes for a repository (clear Publisher freeze)."""
    if _use_in_memory:
        if repo_id not in _repos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        _repos[repo_id]["writes_enabled"] = True
        return {"message": f"Writes enabled for repository {repo_id}"}

    from src.repo.repository import RepoNotFoundError
    repo_repository = get_repo_repository()
    try:
        repo = await repo_repository.set_writes_enabled(session, repo_id, enabled=True)
        await session.commit()
        return {"message": f"Writes enabled for repository {repo.full_name}"}
    except RepoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        ) from err
