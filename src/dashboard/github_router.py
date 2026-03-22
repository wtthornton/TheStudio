"""GitHub Issues API router — browse and import repo issues into the pipeline.

Epic 38, Story 38.1: GET /api/v1/dashboard/github/issues
Epic 38, Story 38.2: POST /api/v1/dashboard/github/import
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.models.taskpacket import TaskPacketCreate, TaskPacketStatus
from src.models.taskpacket_crud import create as create_taskpacket
from src.models.taskpacket_crud import get_by_repo_and_issue
from src.repo.repository import RepoRepository
from src.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

GITHUB_API_BASE = "https://api.github.com"
_CACHE_TTL_SECONDS = 300  # 5 minutes

# In-memory TTL cache: key -> (expires_at, response_data)
_cache: dict[str, tuple[float, GitHubIssueListResponse]] = {}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class GitHubIssue(BaseModel):
    """A GitHub issue returned from the REST API."""

    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    labels: list[str] = Field(default_factory=list)
    html_url: str
    user_login: str | None = None
    created_at: str
    updated_at: str
    comments: int = 0


class GitHubIssueListResponse(BaseModel):
    """Paginated list of GitHub issues (pull requests excluded)."""

    issues: list[GitHubIssue]
    total_count: int
    page: int
    per_page: int
    has_next: bool


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_key(
    repo: str,
    state: str,
    labels: str,
    search: str,
    page: int,
    per_page: int,
) -> str:
    """Build a deterministic cache key from query parameters."""
    return f"{repo}|{state}|{labels}|{search}|{page}|{per_page}"


def _cache_get(key: str) -> GitHubIssueListResponse | None:
    """Return cached response if still fresh, otherwise None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, data = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None
    return data


def _cache_set(key: str, data: GitHubIssueListResponse) -> None:
    """Store response in cache with TTL."""
    _cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, data)


def _cache_clear() -> None:
    """Clear all cache entries (used in tests)."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_issue(raw: dict[str, Any]) -> GitHubIssue:
    """Convert a raw GitHub API issue dict to a GitHubIssue model."""
    user_login: str | None = None
    if raw.get("user"):
        user_login = raw["user"].get("login")

    return GitHubIssue(
        id=raw["id"],
        number=raw["number"],
        title=raw["title"],
        body=raw.get("body"),
        state=raw["state"],
        labels=[lbl["name"] for lbl in raw.get("labels", [])],
        html_url=raw["html_url"],
        user_login=user_login,
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
        comments=raw.get("comments", 0),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/github/issues", response_model=GitHubIssueListResponse)
async def list_github_issues(
    repo: str = Query(..., description="Repository in 'owner/repo' format"),
    state: str = Query("open", description="Issue state: open, closed, or all"),
    labels: str = Query("", description="Comma-separated label names to filter by"),
    search: str = Query("", description="Search term to filter issue titles (client-side)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
) -> GitHubIssueListResponse:
    """List GitHub issues for a repository, excluding pull requests.

    Results are cached per unique combination of query parameters for 5 minutes.
    Uses ``THESTUDIO_INTAKE_POLL_TOKEN`` for GitHub API authentication.

    Pull requests are filtered out server-side (GitHub's issues endpoint returns
    both issues and PRs; we exclude any item that has a ``pull_request`` key).

    The ``search`` parameter filters issue titles client-side (case-insensitive).
    """
    # Validate repo format
    if "/" not in repo or repo.count("/") != 1:
        raise HTTPException(
            status_code=400,
            detail="repo must be in 'owner/repo' format",
        )

    token = settings.intake_poll_token
    if not token:
        raise HTTPException(
            status_code=503,
            detail="GitHub API token not configured (THESTUDIO_INTAKE_POLL_TOKEN)",
        )

    cache_key = _cache_key(repo, state, labels, search, page, per_page)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("GitHub issues cache hit for %s page=%d", repo, page)
        return cached

    owner, repo_name = repo.split("/", 1)

    params: dict[str, Any] = {
        "state": state,
        "per_page": per_page,
        "page": page,
    }
    if labels:
        params["labels"] = labels

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/issues",
                params=params,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="GitHub API request timed out") from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"GitHub API request failed: {exc}"
        ) from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=502, detail="GitHub API authentication failed")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Repository '{repo}' not found")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: HTTP {response.status_code}",
        )

    raw_issues: list[dict[str, Any]] = response.json()

    # Filter out pull requests; optionally apply title search
    issues: list[GitHubIssue] = []
    search_lower = search.lower() if search else ""
    for raw in raw_issues:
        if "pull_request" in raw:
            continue
        if search_lower and search_lower not in raw.get("title", "").lower():
            continue
        issues.append(_parse_issue(raw))

    result = GitHubIssueListResponse(
        issues=issues,
        total_count=len(issues),
        page=page,
        per_page=per_page,
        # has_next is a hint: if the raw page was full, there may be more
        has_next=len(raw_issues) == per_page,
    )

    _cache_set(cache_key, result)
    logger.info(
        "GitHub issues fetched for %s page=%d issues=%d",
        repo,
        page,
        len(issues),
    )
    return result


# ---------------------------------------------------------------------------
# Import request / response models (Story 38.2)
# ---------------------------------------------------------------------------


class ImportIssueItem(BaseModel):
    """A single GitHub issue to import into the pipeline."""

    number: int = Field(..., ge=1, description="GitHub issue number")
    title: str = Field(..., min_length=1, description="Issue title")
    body: str | None = Field(None, description="Issue body (Markdown)")
    labels: list[str] = Field(default_factory=list, description="Label names")


class ImportRequest(BaseModel):
    """Request body for batch-importing GitHub issues as TaskPackets."""

    repo: str = Field(..., description="Repository in 'owner/repo' format")
    issues: list[ImportIssueItem] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Issues to import (1-50 per request)",
    )
    triage_override: bool | None = Field(
        None,
        description=(
            "Override triage mode for this import. "
            "True=TRIAGE, False=RECEIVED+workflow, None=use server setting"
        ),
    )


class ImportIssueResult(BaseModel):
    """Per-issue result from a batch import."""

    number: int
    status: str  # "created" | "duplicate" | "error"
    task_id: str | None = None
    workflow_started: bool = False
    error: str | None = None


class ImportResponse(BaseModel):
    """Response from POST /github/import."""

    repo: str
    created: int
    duplicates: int
    errors: int
    results: list[ImportIssueResult]


# ---------------------------------------------------------------------------
# Import endpoint (Story 38.2)
# ---------------------------------------------------------------------------


@router.post("/github/import", response_model=ImportResponse)
async def import_github_issues(
    body: ImportRequest,
    session: AsyncSession = Depends(get_session),
) -> ImportResponse:
    """Batch-import selected GitHub issues as TaskPackets.

    For each issue:
    * If a TaskPacket already exists for ``(repo, issue_number)`` the entry is
      marked **duplicate** and skipped (no change to the existing record).
    * Otherwise a new TaskPacket is created with ``source_name="dashboard_import"``.

    Triage behaviour follows ``triage_override`` when provided; otherwise it
    respects the server-level ``THESTUDIO_TRIAGE_MODE_ENABLED`` setting:
    * **Triage mode on** → status = TRIAGE (held for human review)
    * **Triage mode off** → status = RECEIVED + Temporal workflow started

    At most 50 issues may be imported per request.
    """
    if "/" not in body.repo or body.repo.count("/") != 1:
        raise HTTPException(
            status_code=400,
            detail="repo must be in 'owner/repo' format",
        )

    use_triage: bool = (
        body.triage_override
        if body.triage_override is not None
        else settings.triage_mode_enabled
    )

    results: list[ImportIssueResult] = []
    created = duplicates = errors = 0

    for issue in body.issues:
        # Deduplicate: check if any TaskPacket for this repo+issue already exists
        existing = await get_by_repo_and_issue(session, body.repo, issue.number)
        if existing is not None:
            duplicates += 1
            results.append(
                ImportIssueResult(
                    number=issue.number,
                    status="duplicate",
                    task_id=str(existing.id),
                )
            )
            logger.debug(
                "GitHub import: issue #%d already in pipeline as task %s",
                issue.number,
                existing.id,
            )
            continue

        # Build a stable delivery_id for dedupe at the DB level
        delivery_id = f"dashboard_import-{body.repo}-{issue.number}"
        task_data = TaskPacketCreate(
            repo=body.repo,
            issue_id=issue.number,
            delivery_id=delivery_id,
            source_name="dashboard_import",
            issue_title=issue.title,
            issue_body=issue.body,
        )

        try:
            initial_status = (
                TaskPacketStatus.TRIAGE if use_triage else TaskPacketStatus.RECEIVED
            )
            taskpacket = await create_taskpacket(session, task_data, initial_status=initial_status)

            workflow_started = False
            if not use_triage:
                try:
                    from src.ingress.workflow_trigger import start_workflow

                    await start_workflow(
                        taskpacket.id,
                        taskpacket.correlation_id,
                        repo=body.repo,
                        issue_title=issue.title,
                        issue_body=issue.body or "",
                        labels=issue.labels,
                    )
                    workflow_started = True
                except Exception:
                    logger.exception(
                        "GitHub import: failed to start workflow for issue #%d (task %s)",
                        issue.number,
                        taskpacket.id,
                    )

            created += 1
            results.append(
                ImportIssueResult(
                    number=issue.number,
                    status="created",
                    task_id=str(taskpacket.id),
                    workflow_started=workflow_started,
                )
            )
            logger.info(
                "GitHub import: issue #%d imported as task %s (triage=%s, workflow=%s)",
                issue.number,
                taskpacket.id,
                use_triage,
                workflow_started,
            )

        except Exception as exc:
            errors += 1
            logger.exception(
                "GitHub import: failed to create TaskPacket for issue #%d: %s",
                issue.number,
                exc,
            )
            results.append(
                ImportIssueResult(
                    number=issue.number,
                    status="error",
                    error=str(exc),
                )
            )

    return ImportResponse(
        repo=body.repo,
        created=created,
        duplicates=duplicates,
        errors=errors,
        results=results,
    )


# ---------------------------------------------------------------------------
# Registered repos endpoint (Story 38.3 — Import Modal repo selector)
# ---------------------------------------------------------------------------


class DashboardRepo(BaseModel):
    """A repository registered in the admin panel."""

    full_name: str
    owner: str
    name: str


class DashboardRepoListResponse(BaseModel):
    """List of registered repos for the import modal repo selector."""

    repos: list[DashboardRepo]
    total: int


@router.get("/github/repos", response_model=DashboardRepoListResponse)
async def list_dashboard_repos(
    session: AsyncSession = Depends(get_session),
) -> DashboardRepoListResponse:
    """Return all repositories registered in the admin panel.

    Used by the Import Modal frontend (Story 38.3) to populate the repo
    selector dropdown.  Returns an empty list when no repos are registered
    (e.g. in development) so the frontend can gracefully fall back to a
    manual text input.
    """
    repo_repository = RepoRepository()
    repos = await repo_repository.list_all(session)
    return DashboardRepoListResponse(
        repos=[
            DashboardRepo(
                full_name=f"{r.owner}/{r.repo_name}",
                owner=r.owner,
                name=r.repo_name,
            )
            for r in repos
        ],
        total=len(repos),
    )


# ---------------------------------------------------------------------------
# Projects v2 sync config endpoints (Story 38.16)
# ---------------------------------------------------------------------------


class ProjectsSyncConfig(BaseModel):
    """Configuration for GitHub Projects v2 sync (Epic 38.16)."""

    enabled: bool = Field(description="Whether Projects v2 sync is active")
    owner: str = Field(description="GitHub org or user owning the project")
    project_number: int = Field(ge=0, description="GitHub Projects v2 number")
    auto_add: bool = Field(description="Auto-add new TaskPackets to the project board")
    auto_close: bool = Field(description="Close GitHub issues when pipeline completes")
    respect_manual_overrides: bool = Field(
        description="Skip sync if user manually changed the field on the board"
    )


class ProjectsSyncStatus(BaseModel):
    """Current status returned alongside config."""

    token_configured: bool
    last_sync_error: str | None = None


class ProjectsSyncConfigResponse(BaseModel):
    """Response model for GET /github/projects/config."""

    config: ProjectsSyncConfig
    status: ProjectsSyncStatus


@router.get("/github/projects/config", response_model=ProjectsSyncConfigResponse)
async def get_projects_sync_config() -> ProjectsSyncConfigResponse:
    """Return the current GitHub Projects v2 sync configuration.

    Story 38.16: Exposes projects_v2_* settings as a readable API so the
    frontend config UI can show the current state without restarting the server.
    """
    config = ProjectsSyncConfig(
        enabled=settings.projects_v2_enabled,
        owner=settings.projects_v2_owner,
        project_number=settings.projects_v2_number,
        auto_add=settings.projects_sync_auto_add,
        auto_close=settings.projects_sync_auto_close,
        respect_manual_overrides=settings.projects_sync_respect_manual_overrides,
    )
    status = ProjectsSyncStatus(
        token_configured=bool(settings.projects_v2_token or settings.github_app_id),
    )
    return ProjectsSyncConfigResponse(config=config, status=status)


@router.put("/github/projects/config", response_model=ProjectsSyncConfigResponse)
async def update_projects_sync_config(
    body: ProjectsSyncConfig,
) -> ProjectsSyncConfigResponse:
    """Update the GitHub Projects v2 sync configuration.

    Story 38.16: Writes updated sync behavior flags to the in-process settings
    object. Changes apply immediately to all subsequent sync operations without
    a server restart.

    Note: ``owner``, ``project_number``, and the token are managed via
    environment variables (THESTUDIO_PROJECTS_V2_*). This endpoint updates the
    runtime sync behaviour flags only.
    """
    settings.projects_v2_enabled = body.enabled
    settings.projects_sync_auto_add = body.auto_add
    settings.projects_sync_auto_close = body.auto_close
    settings.projects_sync_respect_manual_overrides = body.respect_manual_overrides

    logger.info(
        "projects_sync_config.updated",
        extra={
            "enabled": body.enabled,
            "auto_add": body.auto_add,
            "auto_close": body.auto_close,
        },
    )

    return await get_projects_sync_config()


# ---------------------------------------------------------------------------
# Force sync endpoint (Story 38.17)
# ---------------------------------------------------------------------------


class ForceSyncResponse(BaseModel):
    """Response from POST /github/projects/sync."""

    triggered: bool
    active_tasks_found: int
    errors: list[str] = Field(default_factory=list)
    message: str


async def _get_issue_node_id(
    token: str,
    owner: str,
    repo_name: str,
    issue_number: int,
) -> str | None:
    """Fetch the GitHub node ID for a repo issue via the REST API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            resp = await http_client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/issues/{issue_number}",
                headers=headers,
            )
        if resp.status_code == 200:
            return resp.json().get("node_id")
    except Exception:
        pass
    return None


@router.post("/github/projects/sync", response_model=ForceSyncResponse)
async def force_projects_sync(
    session: AsyncSession = Depends(get_session),
) -> ForceSyncResponse:
    """Force a full re-sync of all active TaskPackets to the GitHub project board.

    Story 38.17: Re-pushes Status, Trust Tier, and Complexity fields for every
    non-terminal TaskPacket to the configured GitHub Projects v2 board.

    For each active task the endpoint:
    1. Resolves the GitHub issue node ID via the REST API.
    2. Adds the item to the project (idempotent — already-added items are returned).
    3. Sets Status, Automation Tier, and Complexity fields.

    This is a best-effort operation. Individual item failures are collected and
    returned in the ``errors`` list; partial success is still reported as
    triggered=True.

    Returns 503 if Projects v2 sync is not configured.
    """
    if not settings.projects_v2_enabled:
        raise HTTPException(status_code=503, detail="Projects v2 sync is not enabled")
    if not settings.projects_v2_owner or not settings.projects_v2_number:
        raise HTTPException(status_code=503, detail="Projects v2 owner/number not configured")

    token = settings.projects_v2_token or settings.github_app_id
    if not token:
        raise HTTPException(status_code=503, detail="Projects v2 token not configured")

    from src.models.taskpacket_crud import list_active

    active_tasks = await list_active(session)
    errors: list[str] = []
    synced = 0

    from src.github.projects_client import ProjectsV2Client
    from src.github.projects_mapping import map_complexity, map_status, map_tier

    try:
        async with ProjectsV2Client(token) as client:
            await client.ensure_cost_and_complexity_fields(
                settings.projects_v2_owner,
                settings.projects_v2_number,
            )
            project = await client.find_project(
                settings.projects_v2_owner,
                settings.projects_v2_number,
            )

            for task in active_tasks:
                try:
                    # Resolve GitHub issue node ID via REST API
                    if "/" not in (task.repo or ""):
                        errors.append(f"task {task.id}: invalid repo format")
                        continue
                    repo_owner, repo_name = task.repo.split("/", 1)
                    node_id = await _get_issue_node_id(token, repo_owner, repo_name, task.issue_id)
                    if not node_id:
                        errors.append(f"task {task.id}: could not resolve issue node_id")
                        continue

                    # Add to project (idempotent)
                    item_id = await client.add_item(project.project_id, node_id)

                    task_status = task.status.value if hasattr(task.status, "value") else str(task.status)
                    status_value = map_status(task_status)
                    if status_value and "Status" in project.fields:
                        await client.set_field_value(
                            project.project_id, item_id, project.fields["Status"], status_value,
                        )

                    if task.task_trust_tier:
                        tier_raw = task.task_trust_tier.value if hasattr(task.task_trust_tier, "value") else str(task.task_trust_tier)
                        tier_value = map_tier(tier_raw)
                        if tier_value and "Automation Tier" in project.fields:
                            await client.set_field_value(
                                project.project_id, item_id,
                                project.fields["Automation Tier"], tier_value,
                            )

                    if task.complexity_index and isinstance(task.complexity_index, dict):
                        ci_val = task.complexity_index.get("level", "")
                        complexity_value = map_complexity(ci_val) if ci_val else None
                        if complexity_value and "Complexity" in project.fields:
                            await client.set_field_value(
                                project.project_id, item_id,
                                project.fields["Complexity"], complexity_value,
                            )

                    synced += 1

                except Exception as exc:
                    errors.append(f"task {task.id}: {exc}")
                    logger.warning(
                        "force_sync.task_error",
                        extra={"task_id": str(task.id), "error": str(exc)},
                    )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Projects v2 API error: {exc}") from exc

    logger.info(
        "projects_sync.force_sync_complete",
        extra={
            "active_tasks": len(active_tasks),
            "synced": synced,
            "errors": len(errors),
        },
    )

    return ForceSyncResponse(
        triggered=True,
        active_tasks_found=len(active_tasks),
        errors=errors,
        message=(
            f"Sync complete: {synced} of {len(active_tasks)} tasks synced, "
            f"{len(errors)} failed."
        ),
    )
