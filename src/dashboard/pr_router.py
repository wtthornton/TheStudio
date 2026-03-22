"""PR action API — approve/merge and request changes on TaskPacket pull requests.

Epic 38, Story 38.9: POST /api/v1/dashboard/tasks/{task_id}/pr/approve
Epic 38, Story 38.10: POST /api/v1/dashboard/tasks/{task_id}/pr/request-changes

Each endpoint fetches the TaskPacket, extracts the PR number and repo, then
calls the GitHub REST API to perform the requested action.

Error codes:
  404 — TaskPacket not found
  409 — Task has no associated PR (pr_number is None)
  502 — GitHub API error (network, auth, rate limit, or unexpected status)
  504 — GitHub API request timed out
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.models.taskpacket_crud import get_by_id
from src.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pr"])

GITHUB_API_BASE = "https://api.github.com"


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class PRApproveResponse(BaseModel):
    """Response returned after a successful PR merge."""

    task_id: UUID
    pr_number: int
    merged: bool
    sha: str | None = None
    message: str = "Pull request merged successfully"


class PRRequestChangesRequest(BaseModel):
    """Request body for requesting changes on a PR."""

    body: str = Field(
        ...,
        min_length=1,
        max_length=65535,
        description="Review comment body explaining the requested changes",
    )


class PRRequestChangesResponse(BaseModel):
    """Response returned after posting a request-changes review."""

    task_id: UUID
    pr_number: int
    review_id: int | None = None
    message: str = "Review submitted: changes requested"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _github_headers(token: str) -> dict[str, str]:
    """Build standard GitHub API request headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _require_task_with_pr(session: AsyncSession, task_id: UUID) -> tuple[str, int]:
    """Fetch the TaskPacket and return (repo, pr_number).

    Raises:
        HTTPException 404 — task not found
        HTTPException 409 — task exists but has no PR number
    """
    task = await get_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.pr_number is None:
        raise HTTPException(
            status_code=409,
            detail=f"Task {task_id} has no associated pull request",
        )
    return task.repo, task.pr_number


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/tasks/{task_id}/pr/approve",
    response_model=PRApproveResponse,
    status_code=200,
)
async def approve_pr(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PRApproveResponse:
    """Approve and merge the pull request associated with a TaskPacket.

    Calls the GitHub merge API (``PUT /repos/{owner}/{repo}/pulls/{pr}/merge``).
    The merge is performed as a squash merge with the default commit message.

    Raises:
        404 — task not found
        409 — task has no associated PR
        502 — GitHub API error (auth, rate limit, unexpected status)
        504 — GitHub API request timed out
    """
    token = settings.intake_poll_token
    if not token:
        raise HTTPException(
            status_code=503,
            detail="GitHub API token not configured (THESTUDIO_INTAKE_POLL_TOKEN)",
        )

    repo, pr_number = await _require_task_with_pr(session, task_id)

    if "/" not in repo:
        raise HTTPException(
            status_code=422,
            detail=f"Task repo '{repo}' is not in 'owner/repo' format",
        )
    owner, repo_name = repo.split("/", 1)

    merge_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/pulls/{pr_number}/merge"
    payload = {"merge_method": "squash"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                merge_url,
                json=payload,
                headers=_github_headers(token),
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="GitHub API request timed out") from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API request failed: {exc}",
        ) from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=502, detail="GitHub API authentication failed")
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Pull request #{pr_number} not found on GitHub",
        )
    if response.status_code == 405:
        raise HTTPException(
            status_code=409,
            detail=f"Pull request #{pr_number} is not mergeable",
        )
    if response.status_code == 409:
        raise HTTPException(
            status_code=409,
            detail=f"Pull request #{pr_number} merge conflict — resolve conflicts before merging",
        )
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: HTTP {response.status_code}",
        )

    data = response.json()
    sha: str | None = data.get("sha")
    message: str = data.get("message", "Pull request merged successfully")

    logger.info(
        "PR #%d merged for task %s repo=%s sha=%s",
        pr_number,
        task_id,
        repo,
        sha,
    )

    return PRApproveResponse(
        task_id=task_id,
        pr_number=pr_number,
        merged=True,
        sha=sha,
        message=message,
    )
