"""GitHub API client for Publisher operations.

Uses httpx with GitHub App installation tokens for authenticated API calls.
Handles branch creation, PR creation, comments, and labels.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Async GitHub API client using installation tokens."""

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

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make a GitHub API request with error handling."""
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of a repository."""
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        return data["default_branch"]  # type: ignore[no-any-return]

    async def get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        """Get the SHA of a branch tip."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        return data["object"]["sha"]  # type: ignore[no-any-return]

    async def create_branch(
        self, owner: str, repo: str, branch_name: str, from_sha: str
    ) -> None:
        """Create a new branch from a SHA."""
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
        )
        logger.info("Created branch %s on %s/%s", branch_name, owner, repo)

    async def find_pr_by_head(
        self, owner: str, repo: str, head_branch: str
    ) -> dict[str, Any] | None:
        """Find an existing PR by head branch (for idempotency)."""
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/pulls",
            params={"head": f"{owner}:{head_branch}", "state": "open"},
        )
        resp.raise_for_status()
        prs = resp.json()
        if prs:
            return prs[0]  # type: ignore[no-any-return]
        return None

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool = True,
    ) -> dict[str, Any]:
        """Create a draft pull request."""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
                "draft": draft,
            },
        )

    async def add_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        """Add a comment to a pull request."""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )

    async def add_labels(
        self, owner: str, repo: str, pr_number: int, labels: list[str]
    ) -> list[dict[str, Any]]:
        """Add labels to a pull request."""
        return await self._request(  # type: ignore[return-value]
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/labels",
            json={"labels": labels},
        )

    async def remove_label(
        self, owner: str, repo: str, pr_number: int, label: str
    ) -> None:
        """Remove a label from a pull request (ignores 404)."""
        resp = await self._client.delete(
            f"/repos/{owner}/{repo}/issues/{pr_number}/labels/{label}"
        )
        if resp.status_code != 404:
            resp.raise_for_status()

    async def update_comment(
        self, owner: str, repo: str, comment_id: int, body: str
    ) -> dict[str, Any]:
        """Update an existing comment."""
        return await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
            json={"body": body},
        )

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> dict[str, Any] | None:
        """Get file content and SHA from a repo. Returns None if file doesn't exist."""
        params = {}
        if ref:
            params["ref"] = ref
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/contents/{path}", params=params
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
        """Create or update a file via the GitHub Contents API.

        Args:
            owner: Repo owner.
            repo: Repo name.
            path: File path in the repo.
            content_b64: Base64-encoded file content.
            message: Commit message.
            branch: Target branch.
            sha: Current file SHA (required for updates, omit for creates).
        """
        payload: dict[str, Any] = {
            "message": message,
            "content": content_b64,
            "branch": branch,
        }
        if sha is not None:
            payload["sha"] = sha
        return await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/contents/{path}",
            json=payload,
        )

    async def mark_ready_for_review(
        self, owner: str, repo: str, pr_number: int
    ) -> None:
        """Mark a draft PR as ready for review using the GraphQL API.

        The REST API does not support this operation — GraphQL is required.
        """
        # First get the PR node_id via REST
        pr_data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        node_id = pr_data["node_id"]

        # Use GraphQL mutation to mark ready
        mutation = """
            mutation($pullRequestId: ID!) {
                markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
                    pullRequest { number }
                }
            }
        """
        resp = await self._client.post(
            "https://api.github.com/graphql",
            json={"query": mutation, "variables": {"pullRequestId": node_id}},
        )
        resp.raise_for_status()
        logger.info(
            "Marked PR #%d as ready for review on %s/%s", pr_number, owner, repo
        )

    async def enable_auto_merge(
        self, owner: str, repo: str, pr_number: int, merge_method: str = "SQUASH"
    ) -> None:
        """Enable auto-merge on a PR using the GitHub GraphQL API.

        Requires the repository to have "Allow auto-merge" enabled in settings
        and the GitHub App to have ``contents: write`` permission.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            merge_method: One of MERGE, SQUASH, REBASE (GraphQL enum values).
                         Also accepts lowercase; will be uppercased automatically.
        """
        # Get the PR node_id via REST
        pr_data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        node_id = pr_data["node_id"]

        # Map common lowercase values to GraphQL enum
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
        resp = await self._client.post(
            "https://api.github.com/graphql",
            json={
                "query": mutation,
                "variables": {
                    "pullRequestId": node_id,
                    "mergeMethod": method_upper,
                },
            },
        )
        resp.raise_for_status()

        # Check for GraphQL-level errors
        data = resp.json()
        if "errors" in data:
            error_msgs = [e.get("message", "") for e in data["errors"]]
            raise RuntimeError(
                f"GraphQL errors enabling auto-merge on PR #{pr_number}: {error_msgs}"
            )

        logger.info(
            "Enabled auto-merge (%s) on PR #%d for %s/%s",
            method_upper, pr_number, owner, repo,
        )
