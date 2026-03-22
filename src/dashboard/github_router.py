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
from src.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

GITHUB_API_BASE = "https://api.github.com"
_CACHE_TTL_SECONDS = 300  # 5 minutes

# In-memory TTL cache: key -> (expires_at, response_data)
_cache: dict[str, tuple[float, "GitHubIssueListResponse"]] = {}


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
        description="Issues to import (1–50 per request)",
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
