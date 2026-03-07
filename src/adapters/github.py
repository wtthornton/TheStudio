"""GitHub REST API adapter with retry logic and error classification.

Story 8.6: GitHub REST API Adapter
Feature flag: THESTUDIO_GITHUB_PROVIDER ("mock" or "real")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.settings import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    """Classified GitHub API error."""

    def __init__(self, status_code: int, error_class: str, message: str) -> None:
        self.status_code = status_code
        self.error_class = error_class
        super().__init__(f"GitHub API {error_class} ({status_code}): {message}")


def _classify_error(status_code: int) -> str:
    """Classify HTTP status codes into error categories."""
    if status_code == 401 or status_code == 403:
        return "auth"
    if status_code == 404:
        return "not_found"
    if status_code == 422:
        return "validation"
    if status_code == 429:
        return "rate_limit"
    if status_code >= 500:
        return "server"
    return "unknown"


class ResilientGitHubClient:
    """GitHub API client with retry logic and error classification.

    Wraps httpx with exponential backoff retries for transient errors
    (rate limits and server errors). Auth and validation errors fail immediately.
    """

    RETRYABLE_CLASSES = {"rate_limit", "server"}
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

    def __init__(self, installation_token: str) -> None:
        self._token = installation_token
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"token {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ResilientGitHubClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def _request_with_retry(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Make a request with retry logic for transient errors."""
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES + 1):
            resp = await self._client.request(method, path, **kwargs)

            if resp.is_success:
                return resp

            error_class = _classify_error(resp.status_code)

            if error_class not in self.RETRYABLE_CLASSES or attempt == self.MAX_RETRIES:
                try:
                    detail = resp.json().get("message", resp.text)
                except Exception:
                    detail = resp.text
                raise GitHubAPIError(resp.status_code, error_class, detail)

            delay = self.BASE_DELAY * (2 ** attempt)
            logger.warning(
                "GitHub API %s (attempt %d/%d), retrying in %.1fs: %s %s",
                error_class, attempt + 1, self.MAX_RETRIES + 1, delay, method, path,
            )
            await asyncio.sleep(delay)

        raise last_error or GitHubAPIError(500, "server", "Max retries exceeded")

    async def _request_json(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        resp = await self._request_with_retry(method, path, **kwargs)
        return resp.json()  # type: ignore[no-any-return]

    async def get_default_branch(self, owner: str, repo: str) -> str:
        data = await self._request_json("GET", f"/repos/{owner}/{repo}")
        return data["default_branch"]  # type: ignore[no-any-return]

    async def get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        data = await self._request_json(
            "GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}",
        )
        return data["object"]["sha"]  # type: ignore[no-any-return]

    async def create_branch(
        self, owner: str, repo: str, branch_name: str, from_sha: str,
    ) -> None:
        await self._request_json(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
        )

    async def create_pull_request(
        self, owner: str, repo: str, title: str, body: str,
        head_branch: str, base_branch: str, draft: bool = True,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title, "body": body,
                "head": head_branch, "base": base_branch, "draft": draft,
            },
        )

    async def add_comment(
        self, owner: str, repo: str, pr_number: int, body: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )

    async def add_labels(
        self, owner: str, repo: str, pr_number: int, labels: list[str],
    ) -> list[dict[str, Any]]:
        return await self._request_json(  # type: ignore[return-value]
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/labels",
            json={"labels": labels},
        )

    async def remove_label(
        self, owner: str, repo: str, pr_number: int, label: str,
    ) -> None:
        resp = await self._request_with_retry(
            "DELETE", f"/repos/{owner}/{repo}/issues/{pr_number}/labels/{label}",
        )

    async def update_comment(
        self, owner: str, repo: str, comment_id: int, body: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
            json={"body": body},
        )


def get_github_client(installation_token: str) -> ResilientGitHubClient:
    """Return the configured GitHub client.

    When THESTUDIO_GITHUB_PROVIDER is "real", returns ResilientGitHubClient.
    When "mock" (default), callers should use the original GitHubClient
    from src.publisher.github_client which has no retry logic.
    """
    from src.publisher.github_client import GitHubClient

    if settings.github_provider == "real":
        return ResilientGitHubClient(installation_token)
    return GitHubClient(installation_token)  # type: ignore[return-value]
