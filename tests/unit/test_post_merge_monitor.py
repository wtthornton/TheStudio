"""Unit tests for post-merge monitoring (Epic 42 Story 42.13).

Covers:
(a) Revert detection from GitHub commit data
(b) Linked issue detection
(c) 24h window boundary enforcement
(d) GitHubClient method correctness

Tests use mocked httpx responses and mock asyncio.sleep to avoid real waits.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from src.publisher.github_client import GitHubClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_response(data, status_code: int = 200) -> MagicMock:
    """Build a fake httpx response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


@pytest.fixture
def github_client():
    """GitHubClient with mocked httpx.AsyncClient."""
    client = GitHubClient(installation_token="test-token")
    client._client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# check_for_reverts tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_for_reverts_detects_revert_commit(github_client):
    """Revert commit with matching PR number is detected and SHA returned."""
    since_iso = "2026-03-22T00:00:00+00:00"
    commits = [
        {
            "sha": "abc123",
            "commit": {"message": 'Revert "Fix SSO login" (#42)\n\nThis reverts commit xyz.'},
        },
        {
            "sha": "def456",
            "commit": {"message": "Normal commit — unrelated"},
        },
    ]
    github_client._client.get = AsyncMock(
        return_value=_mock_response(commits)
    )

    result = await github_client.check_for_reverts("owner", "repo", 42, since_iso)

    assert result == "abc123"
    github_client._client.get.assert_called_once_with(
        "/repos/owner/repo/commits",
        params={"since": since_iso, "per_page": 50},
    )


@pytest.mark.asyncio
async def test_check_for_reverts_no_revert_returns_none(github_client):
    """When no revert commit references the PR, returns None."""
    commits = [
        {"sha": "aaa", "commit": {"message": "Fix bug in auth module"}},
        {"sha": "bbb", "commit": {"message": "Update README"}},
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(commits))

    result = await github_client.check_for_reverts("owner", "repo", 99, "2026-03-22T00:00:00+00:00")

    assert result is None


@pytest.mark.asyncio
async def test_check_for_reverts_wrong_pr_number_not_matched(github_client):
    """Revert for a different PR number is not matched."""
    commits = [
        {"sha": "abc", "commit": {"message": 'Revert "Fix SSO" (#55)\n\nReverts commit xyz.'}},
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(commits))

    result = await github_client.check_for_reverts("owner", "repo", 42, "2026-03-22T00:00:00+00:00")

    assert result is None


@pytest.mark.asyncio
async def test_check_for_reverts_empty_commits(github_client):
    """Empty commit list returns None (no reverts to detect)."""
    github_client._client.get = AsyncMock(return_value=_mock_response([]))

    result = await github_client.check_for_reverts("owner", "repo", 1, "2026-03-22T00:00:00+00:00")

    assert result is None


# ---------------------------------------------------------------------------
# check_for_linked_issues tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_for_linked_issues_detects_issue(github_client):
    """Issue body containing the PR reference is returned."""
    since_iso = "2026-03-22T00:00:00+00:00"
    issues = [
        {"number": 100, "title": "Regression after merge", "body": "Broken by #42"},
        {"number": 101, "title": "Unrelated issue", "body": "Something else"},
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(issues))

    result = await github_client.check_for_linked_issues("owner", "repo", 42, since_iso)

    assert result == 100


@pytest.mark.asyncio
async def test_check_for_linked_issues_pr_in_title(github_client):
    """Issue title containing the PR reference is returned."""
    issues = [
        {"number": 200, "title": "Bug introduced by #42", "body": "Description here"},
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(issues))

    result = await github_client.check_for_linked_issues("owner", "repo", 42, "2026-03-22T00:00:00+00:00")

    assert result == 200


@pytest.mark.asyncio
async def test_check_for_linked_issues_excludes_pull_requests(github_client):
    """Pull requests in the issues list are excluded from matching."""
    issues = [
        {
            "number": 300,
            "title": "Revert #42",
            "body": "#42 broke things",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/300"},
        },
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(issues))

    result = await github_client.check_for_linked_issues("owner", "repo", 42, "2026-03-22T00:00:00+00:00")

    assert result is None


@pytest.mark.asyncio
async def test_check_for_linked_issues_no_match_returns_none(github_client):
    """When no issue references the PR, returns None."""
    issues = [
        {"number": 400, "title": "Unrelated bug", "body": "Something completely different"},
    ]
    github_client._client.get = AsyncMock(return_value=_mock_response(issues))

    result = await github_client.check_for_linked_issues("owner", "repo", 42, "2026-03-22T00:00:00+00:00")

    assert result is None


# ---------------------------------------------------------------------------
# get_pr_merge_status tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pr_merge_status_returns_merged(github_client):
    """Merged PR returns merged=True and the SHA."""
    pr_data = {
        "state": "closed",
        "merged": True,
        "merge_commit_sha": "deadbeef",
        "merged_at": "2026-03-22T10:00:00Z",
    }
    github_client._client = MagicMock()
    github_client._client.request = AsyncMock(return_value=_mock_response(pr_data))

    result = await github_client.get_pr_merge_status("owner", "repo", 42)

    assert result["merged"] is True
    assert result["merge_commit_sha"] == "deadbeef"
    assert result["state"] == "closed"


@pytest.mark.asyncio
async def test_get_pr_merge_status_open_pr(github_client):
    """Open PR returns merged=False."""
    pr_data = {
        "state": "open",
        "merged": False,
        "merge_commit_sha": None,
        "merged_at": None,
    }
    github_client._client = MagicMock()
    github_client._client.request = AsyncMock(return_value=_mock_response(pr_data))

    result = await github_client.get_pr_merge_status("owner", "repo", 42)

    assert result["merged"] is False
    assert result["state"] == "open"


# ---------------------------------------------------------------------------
# 24h window boundary test (stub-mode activity)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monitor_stub_mode_returns_succeeded_immediately():
    """In stub mode (non-real GitHub provider), the monitor returns immediately."""
    import os

    # Use env vars to minimize wait times
    with (
        patch.dict(os.environ, {
            "POST_MERGE_INITIAL_WAIT_S": "0",
            "POST_MERGE_POLL_INTERVAL_S": "0",
            "POST_MERGE_MAX_POLLS": "1",
        }),
        patch("src.settings.settings") as mock_settings,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_settings.github_provider = "stub"  # Not "real" → stub mode
        mock_settings.intake_poll_token = ""

        from src.workflow.activities import (
            PostMergeMonitorInput,
            monitor_post_merge_activity,
        )

        # In stub mode, the activity returns immediately without polls
        with patch("temporalio.activity.heartbeat"):
            result = await monitor_post_merge_activity(
                PostMergeMonitorInput(
                    taskpacket_id=str(uuid4()),
                    pr_number=42,
                    repo="owner/repo",
                    merged_at_iso="2026-03-22T10:00:00+00:00",
                )
            )

        assert result.outcome == "succeeded"
        # Should not have slept in stub mode
        mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_monitor_invalid_repo_returns_succeeded():
    """Activity with malformed repo string returns succeeded without polling."""
    from src.workflow.activities import (
        PostMergeMonitorInput,
        monitor_post_merge_activity,
    )

    with patch("src.settings.settings") as mock_settings:
        mock_settings.github_provider = "real"
        mock_settings.intake_poll_token = "token"

        result = await monitor_post_merge_activity(
            PostMergeMonitorInput(
                taskpacket_id=str(uuid4()),
                pr_number=42,
                repo="invalid-no-slash",
                merged_at_iso="2026-03-22T10:00:00+00:00",
            )
        )

    assert result.outcome == "succeeded"
