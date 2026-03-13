"""Integration tests for poll intake path (Epic 17, Story 17.7).

Five scenarios with mocked GitHub API — no real tokens or API calls required.
Tests the full poll path: client → feed → TaskPacket + workflow.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
import respx

from src.ingress.poll.client import fetch_issues
from src.ingress.poll.feed import feed_issues_to_pipeline, synthetic_delivery_id
from src.ingress.poll.models import PollConfig, PollResult
from src.ingress.poll.scheduler import run_poll_cycle


def _make_repo(
    owner: str = "test-org",
    repo_name: str = "test-repo",
    poll_enabled: bool = True,
) -> MagicMock:
    """Create a mock RepoProfileRow with poll fields."""
    repo = MagicMock()
    repo.owner = owner
    repo.repo_name = repo_name
    repo.full_name = f"{owner}/{repo_name}"
    repo.poll_enabled = poll_enabled
    repo.poll_interval_minutes = None
    repo.poll_etag = None
    repo.poll_last_modified = None
    repo.poll_since = None
    repo.poll_last_run_at = None
    return repo


# ---------------------------------------------------------------------------
# Scenario 1: Happy path — new issue → TaskPacket + workflow
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_poll_happy_path_creates_taskpacket_and_workflow() -> None:
    """Mock 200 with 1 new issue → feed creates TaskPacket → workflow started."""
    # Mock GitHub API returning one issue
    respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 42,
                    "updated_at": "2026-03-12T10:00:00Z",
                    "title": "Fix login bug",
                },
            ],
            headers={"x-ratelimit-remaining": "4999"},
        )
    )

    # Fetch issues
    config = PollConfig(owner="test-org", repo="test-repo", token="ghp_test")
    result = await fetch_issues(config)

    assert len(result.issues) == 1
    assert result.issues[0]["number"] == 42
    assert result.rate_limit_remaining == 4999

    # Feed to pipeline
    mock_session = AsyncMock()

    with (
        patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock, return_value=False),
        patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock) as mock_create,
        patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock) as mock_workflow,
    ):
        taskpacket = MagicMock()
        taskpacket.id = uuid4()
        mock_create.return_value = taskpacket

        count = await feed_issues_to_pipeline(mock_session, result.issues, "test-org/test-repo")

    assert count == 1
    mock_create.assert_called_once()
    mock_workflow.assert_called_once_with(taskpacket.id, mock_create.call_args[1].get("correlation_id", mock_workflow.call_args[0][1]))


# ---------------------------------------------------------------------------
# Scenario 2: 304 Not Modified → no TaskPackets created
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_poll_304_creates_no_taskpackets() -> None:
    """Mock 304 → no TaskPackets created, no workflow."""
    respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
        return_value=httpx.Response(
            304,
            headers={"x-ratelimit-remaining": "5000"},
        )
    )

    config = PollConfig(
        owner="test-org", repo="test-repo", token="ghp_test", etag='"abc123"'
    )
    result = await fetch_issues(config)

    assert len(result.issues) == 0
    assert result.rate_limit_remaining == 5000

    # Feed empty issues → nothing created
    mock_session = AsyncMock()
    with (
        patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock) as mock_dedupe,
        patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock) as mock_create,
    ):
        count = await feed_issues_to_pipeline(mock_session, result.issues, "test-org/test-repo")

    assert count == 0
    mock_dedupe.assert_not_called()
    mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3: Dedupe — same issue polled twice → one TaskPacket only
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_poll_dedupe_prevents_duplicate_taskpackets() -> None:
    """Same issue polled twice (same updated_at) → one TaskPacket only."""
    issue = {
        "number": 7,
        "updated_at": "2026-03-12T09:00:00Z",
        "title": "Duplicate candidate",
    }

    respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
        return_value=httpx.Response(
            200,
            json=[issue],
            headers={"x-ratelimit-remaining": "4998"},
        )
    )

    config = PollConfig(owner="test-org", repo="test-repo", token="ghp_test")
    result = await fetch_issues(config)

    mock_session = AsyncMock()
    taskpacket = MagicMock()
    taskpacket.id = uuid4()

    # First feed: not a duplicate → creates TaskPacket
    with (
        patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock, return_value=False),
        patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock, return_value=taskpacket),
        patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock),
    ):
        count1 = await feed_issues_to_pipeline(mock_session, result.issues, "test-org/test-repo")

    # Second feed: IS a duplicate → no new TaskPacket
    with (
        patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock, return_value=True),
        patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock) as mock_create,
        patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock) as mock_workflow,
    ):
        count2 = await feed_issues_to_pipeline(mock_session, result.issues, "test-org/test-repo")

    assert count1 == 1
    assert count2 == 0
    mock_create.assert_not_called()
    mock_workflow.assert_not_called()

    # Verify deterministic delivery ID
    did1 = synthetic_delivery_id("test-org/test-repo", 7, "2026-03-12T09:00:00Z")
    did2 = synthetic_delivery_id("test-org/test-repo", 7, "2026-03-12T09:00:00Z")
    assert did1 == did2


# ---------------------------------------------------------------------------
# Scenario 4: PR filtered — issue + PR → only issue processed
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_poll_filters_prs_only_processes_issues() -> None:
    """Mock 200 with 1 issue + 1 PR → only 1 TaskPacket (PR ignored)."""
    respx.get("https://api.github.com/repos/test-org/test-repo/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 10,
                    "updated_at": "2026-03-12T11:00:00Z",
                    "title": "Real issue",
                },
                {
                    "number": 11,
                    "updated_at": "2026-03-12T11:05:00Z",
                    "title": "Pull request",
                    "pull_request": {"url": "https://api.github.com/repos/test-org/test-repo/pulls/11"},
                },
            ],
            headers={"x-ratelimit-remaining": "4997"},
        )
    )

    config = PollConfig(owner="test-org", repo="test-repo", token="ghp_test")
    result = await fetch_issues(config)

    # Only the issue should come through, not the PR
    assert len(result.issues) == 1
    assert result.issues[0]["number"] == 10

    # Feed to pipeline
    mock_session = AsyncMock()
    taskpacket = MagicMock()
    taskpacket.id = uuid4()

    with (
        patch("src.ingress.poll.feed.is_duplicate", new_callable=AsyncMock, return_value=False),
        patch("src.ingress.poll.feed.create_taskpacket", new_callable=AsyncMock, return_value=taskpacket),
        patch("src.ingress.poll.feed.start_workflow", new_callable=AsyncMock),
    ):
        count = await feed_issues_to_pipeline(mock_session, result.issues, "test-org/test-repo")

    assert count == 1


# ---------------------------------------------------------------------------
# Scenario 5: Feature flag off → scheduler does not run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_feature_flag_off_scheduler_idle(mock_settings: MagicMock) -> None:
    """Feature flag off → scheduler returns immediately, no repos polled."""
    mock_settings.intake_poll_enabled = False

    repos, issues, hit = await run_poll_cycle()

    assert repos == 0
    assert issues == 0
    assert hit is False


# ---------------------------------------------------------------------------
# Bonus: Full scheduler cycle with mocked GitHub API
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.feed_issues_to_pipeline", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.fetch_issues", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.async_session_factory")
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_scheduler_full_cycle(
    mock_settings: MagicMock,
    mock_session_factory: MagicMock,
    mock_fetch: AsyncMock,
    mock_feed: AsyncMock,
) -> None:
    """Full scheduler cycle: enabled repo → poll → feed → TaskPacket created."""
    mock_settings.intake_poll_enabled = True
    mock_settings.intake_poll_token = "ghp_test"
    mock_settings.intake_poll_interval_minutes = 10

    repo = _make_repo()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [repo]
    mock_session.execute.return_value = mock_result
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_fetch.return_value = PollResult(
        issues=[{"number": 1, "updated_at": "2026-03-12T10:00:00Z"}],
        etag='"etag-1"',
        last_modified="Thu, 12 Mar 2026 10:00:00 GMT",
        rate_limit_remaining=4999,
    )
    mock_feed.return_value = 1

    repos_polled, issues_created, hit = await run_poll_cycle()

    assert repos_polled == 1
    assert issues_created == 1
    assert hit is False
    mock_fetch.assert_called_once()
    mock_feed.assert_called_once()
