"""Real GitHub provider integration tests — Story 30.6.

Validates that ResilientGitHubClient operations work against a real
GitHub test repository. Tests run in order and clean up after themselves.

Requires:
  - THESTUDIO_GITHUB_TOKEN env var (PAT or installation token)
  - THESTUDIO_GITHUB_TEST_REPO env var (e.g. "owner/thestudio-test-target")

Run with: pytest -m integration tests/integration/test_real_github.py -v
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from src.adapters.github import GitHubAPIError, ResilientGitHubClient

pytestmark = pytest.mark.integration

_TOKEN = os.environ.get("THESTUDIO_GITHUB_TOKEN", "")
_REPO = os.environ.get("THESTUDIO_GITHUB_TEST_REPO", "")

requires_github = pytest.mark.skipif(
    not _TOKEN or not _REPO,
    reason="THESTUDIO_GITHUB_TOKEN and THESTUDIO_GITHUB_TEST_REPO not set",
)


def _parse_repo() -> tuple[str, str]:
    """Split 'owner/repo' into (owner, repo)."""
    parts = _REPO.split("/", 1)
    if len(parts) != 2:
        pytest.skip(f"Invalid THESTUDIO_GITHUB_TEST_REPO format: {_REPO!r}")
    return parts[0], parts[1]


@pytest.fixture
async def client():
    """Create a real GitHub client."""
    async with ResilientGitHubClient(_TOKEN) as c:
        yield c


@requires_github
class TestRealGitHub:
    """Tests against a real GitHub repository — ordered, with cleanup."""

    async def test_get_default_branch(self, client: ResilientGitHubClient) -> None:
        """Verify we can fetch the default branch name."""
        owner, repo = _parse_repo()
        branch = await client.get_default_branch(owner, repo)
        assert isinstance(branch, str)
        assert len(branch) > 0

    async def test_get_branch_sha(self, client: ResilientGitHubClient) -> None:
        """Verify we can get the SHA of the default branch."""
        owner, repo = _parse_repo()
        default = await client.get_default_branch(owner, repo)
        sha = await client.get_branch_sha(owner, repo, default)
        assert isinstance(sha, str)
        assert len(sha) == 40  # full SHA

    async def test_create_branch_and_pr_lifecycle(
        self, client: ResilientGitHubClient
    ) -> None:
        """Full lifecycle: create branch, create PR, add comment, add/remove labels."""
        owner, repo = _parse_repo()
        branch_name = f"thestudio-test/{uuid4().hex[:8]}"
        pr_number = None

        try:
            # Get base SHA
            default = await client.get_default_branch(owner, repo)
            sha = await client.get_branch_sha(owner, repo, default)

            # Create branch
            await client.create_branch(owner, repo, branch_name, sha)

            # Create draft PR
            pr_data = await client.create_pull_request(
                owner, repo,
                title=f"[Test] Integration smoke test {branch_name}",
                body="Automated integration test — will be closed and cleaned up.",
                head_branch=branch_name,
                base_branch=default,
                draft=True,
            )
            pr_number = pr_data["number"]
            assert pr_number > 0
            assert pr_data["draft"] is True

            # Add evidence comment
            comment = await client.add_comment(
                owner, repo, pr_number,
                body="<!-- thestudio-evidence -->\nTest evidence comment.",
            )
            comment_id = comment["id"]
            assert comment_id > 0

            # Update comment
            updated = await client.update_comment(
                owner, repo, comment_id,
                body="<!-- thestudio-evidence -->\nUpdated evidence comment.",
            )
            assert "Updated" in updated["body"]

            # Add labels
            labels = await client.add_labels(
                owner, repo, pr_number,
                labels=["agent:in-progress"],
            )
            assert any(lb["name"] == "agent:in-progress" for lb in labels)

            # Remove label (may 404 if label doesn't exist on repo — that's ok)
            try:
                await client.remove_label(owner, repo, pr_number, "agent:in-progress")
            except GitHubAPIError as e:
                if e.error_class != "not_found":
                    raise

        finally:
            # Cleanup: close PR and delete branch
            if pr_number:
                try:
                    await client._request_json(
                        "PATCH",
                        f"/repos/{owner}/{repo}/pulls/{pr_number}",
                        json={"state": "closed"},
                    )
                except Exception:  # noqa: S110 — cleanup, best-effort
                    pass  # noqa: S110
            try:
                await client._request_with_retry(
                    "DELETE",
                    f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
                )
            except Exception:  # noqa: S110 — cleanup, best-effort
                pass  # noqa: S110

    async def test_invalid_repo_returns_classified_error(
        self, client: ResilientGitHubClient
    ) -> None:
        """Invalid repo returns a not_found classified error."""
        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_default_branch("nonexistent-owner-xyz", "nonexistent-repo")
        assert exc_info.value.error_class == "not_found"
        assert exc_info.value.status_code == 404
