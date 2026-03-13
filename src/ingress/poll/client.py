"""GitHub API poll client for fetching repository issues.

Epic 17 — Poll for Issues as Backup to Webhooks.
Fetches issues with conditional requests, PR filtering, and rate-limit awareness.
"""

import logging
import re
from typing import Any

import httpx

from src.ingress.poll.models import PollConfig, PollResult, RateLimitError

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
RATE_LIMIT_EARLY_RETURN = 50


def _parse_link_header(link_header: str | None) -> dict[str, str]:
    """Parse Link header into rel -> url mapping."""
    if not link_header:
        return {}
    result: dict[str, str] = {}
    for part in link_header.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', part.strip())
        if match:
            result[match.group(2)] = match.group(1)
    return result


def _filter_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out PRs — only return issues (no pull_request key)."""
    return [item for item in items if "pull_request" not in item]


async def fetch_issues(config: PollConfig) -> PollResult:
    """Fetch issues from GitHub API with conditional requests and pagination.

    Uses GET /repos/{owner}/{repo}/issues with since, sort=updated, state=open.
    Filters out PRs. Supports If-None-Match / If-Modified-Since. Paginates via Link.
    On 304, returns empty issues (no rate limit spend). On 403/429, raises RateLimitError.

    Args:
        config: Poll configuration (owner, repo, token, optional since/etag/last_modified).

    Returns:
        PollResult with issues, etag, last_modified, rate_limit_remaining.

    Raises:
        RateLimitError: On 403 or 429 with retry_after if present.
        httpx.HTTPStatusError: On other HTTP errors.
    """
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {config.token}",
    }
    if config.etag:
        headers["If-None-Match"] = config.etag
    elif config.last_modified:
        headers["If-Modified-Since"] = config.last_modified

    params: dict[str, str] = {
        "sort": "updated",
        "state": "open",
        "per_page": "100",
    }
    if config.since:
        params["since"] = config.since

    url = f"{GITHUB_API_BASE}/repos/{config.owner}/{config.repo}/issues"
    all_issues: list[dict[str, Any]] = []
    etag: str | None = None
    last_modified: str | None = None
    rate_limit_remaining = 5000

    async with httpx.AsyncClient(timeout=30.0) as client:
        next_url: str | None = url

        while next_url:
            resp = await client.get(
                next_url,
                headers=headers,
                params=params if next_url == url else None,
            )

            rate_limit_remaining = int(resp.headers.get("x-ratelimit-remaining", 0))
            if resp.headers.get("etag"):
                etag = resp.headers["etag"].strip()
            if resp.headers.get("last-modified"):
                last_modified = resp.headers["last-modified"]

            if resp.status_code == 304:
                return PollResult(
                    issues=[],
                    etag=config.etag,
                    last_modified=config.last_modified,
                    rate_limit_remaining=rate_limit_remaining,
                )

            if resp.status_code in (403, 429):
                retry_after: int | None = None
                if "retry-after" in resp.headers:
                    try:
                        retry_after = int(resp.headers["retry-after"])
                    except ValueError:
                        retry_after = 60
                raise RateLimitError(
                    f"GitHub API rate limit: {resp.status_code}",
                    retry_after=retry_after,
                )

            resp.raise_for_status()
            items = resp.json()
            issues = _filter_issues(items)
            all_issues.extend(issues)

            if rate_limit_remaining < RATE_LIMIT_EARLY_RETURN:
                logger.warning(
                    "poll.rate_limit_low repo=%s/%s remaining=%d",
                    config.owner,
                    config.repo,
                    rate_limit_remaining,
                )
                break

            link_header = resp.headers.get("link")
            links = _parse_link_header(link_header)
            next_rel = links.get("next")
            if next_rel:
                next_url = next_rel
                headers = {
                    k: v
                    for k, v in headers.items()
                    if k.lower() not in ("if-none-match", "if-modified-since")
                }
                params = {}
            else:
                next_url = None

    return PollResult(
        issues=all_issues,
        etag=etag,
        last_modified=last_modified,
        rate_limit_remaining=rate_limit_remaining,
    )
