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
                "Authorization": f"Bearer {self._token}",
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
        """Remove a label from a PR (ignores 404 — label may not exist)."""
        resp = await self._client.request(
            "DELETE", f"/repos/{owner}/{repo}/issues/{pr_number}/labels/{label}",
        )
        if resp.status_code != 404:
            resp.raise_for_status()

    async def update_comment(
        self, owner: str, repo: str, comment_id: int, body: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
            json={"body": body},
        )


    async def find_pr_by_head(
        self, owner: str, repo: str, head_branch: str
    ) -> dict[str, Any] | None:
        """Find an existing PR by head branch (for idempotency)."""
        resp = await self._client.request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={"head": f"{owner}:{head_branch}", "state": "open"},
        )
        resp.raise_for_status()
        prs = resp.json()
        if prs:
            return prs[0]  # type: ignore[no-any-return]
        return None

    async def mark_ready_for_review(
        self, owner: str, repo: str, pr_number: int
    ) -> None:
        """Mark a draft PR as ready for review using the GraphQL API."""
        pr_data = await self._request_json("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        node_id = pr_data["node_id"]
        mutation = """
            mutation($pullRequestId: ID!) {
                markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
                    pullRequest { number }
                }
            }
        """
        resp = await self._client.request(
            "POST",
            "https://api.github.com/graphql",
            json={"query": mutation, "variables": {"pullRequestId": node_id}},
        )
        resp.raise_for_status()

    async def enable_auto_merge(
        self, owner: str, repo: str, pr_number: int, merge_method: str = "SQUASH"
    ) -> None:
        """Enable auto-merge on a PR using the GitHub GraphQL API."""
        pr_data = await self._request_json("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        node_id = pr_data["node_id"]
        method_upper = merge_method.upper()
        mutation = """
            mutation($pullRequestId: ID!, $mergeMethod: PullRequestMergeMethod!) {
                enablePullRequestAutoMerge(input: {
                    pullRequestId: $pullRequestId,
                    mergeMethod: $mergeMethod
                }) {
                    pullRequest { number autoMergeRequest { enabledAt } }
                }
            }
        """
        resp = await self._client.request(
            "POST",
            "https://api.github.com/graphql",
            json={
                "query": mutation,
                "variables": {"pullRequestId": node_id, "mergeMethod": method_upper},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            error_msgs = [e.get("message", "") for e in data["errors"]]
            raise RuntimeError(f"GraphQL errors enabling auto-merge: {error_msgs}")

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> dict[str, Any] | None:
        """Get file content and SHA from a repo. Returns None if file doesn't exist."""
        params = {}
        if ref:
            params["ref"] = ref
        resp = await self._client.request(
            "GET", f"/repos/{owner}/{repo}/contents/{path}", params=params
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content_b64: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a file via the GitHub Contents API."""
        payload: dict[str, Any] = {
            "message": message,
            "content": content_b64,
            "branch": branch,
        }
        if sha is not None:
            payload["sha"] = sha
        return await self._request_json(
            "PUT",
            f"/repos/{owner}/{repo}/contents/{path}",
            json=payload,
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
