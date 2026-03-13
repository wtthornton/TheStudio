"""Unit tests for poll scheduler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingress.poll.models import PollResult, RateLimitError
from src.ingress.poll.scheduler import run_poll_cycle


def _make_repo(owner: str = "org", repo_name: str = "repo1") -> MagicMock:
    """Create a mock RepoProfileRow with poll_enabled."""
    repo = MagicMock()
    repo.owner = owner
    repo.repo_name = repo_name
    repo.full_name = f"{owner}/{repo_name}"
    repo.poll_enabled = True
    return repo


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_cycle_disabled_by_feature_flag(mock_settings: MagicMock) -> None:
    """Feature flag off → no repos polled."""
    mock_settings.intake_poll_enabled = False
    repos, issues, hit = await run_poll_cycle()
    assert repos == 0
    assert issues == 0
    assert hit is False


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_cycle_no_token(mock_settings: MagicMock) -> None:
    """Missing poll token → skip with warning."""
    mock_settings.intake_poll_enabled = True
    mock_settings.intake_poll_token = ""
    repos, issues, _hit = await run_poll_cycle()
    assert repos == 0
    assert issues == 0


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.feed_issues_to_pipeline", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.fetch_issues", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.async_session_factory")
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_cycle_single_repo(
    mock_settings: MagicMock,
    mock_session_factory: MagicMock,
    mock_fetch: AsyncMock,
    mock_feed: AsyncMock,
) -> None:
    """One repo with poll enabled → poll client called once."""
    mock_settings.intake_poll_enabled = True
    mock_settings.intake_poll_token = "ghp_test"

    repo = _make_repo()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [repo]
    mock_session.execute.return_value = mock_result
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_fetch.return_value = PollResult(
        issues=[{"number": 1, "updated_at": "2026-03-11T12:00:00Z"}],
        etag='"abc"',
        last_modified=None,
        rate_limit_remaining=4999,
    )
    mock_feed.return_value = 1

    repos, issues, hit = await run_poll_cycle()

    assert repos == 1
    assert issues == 1
    assert hit is False
    mock_fetch.assert_called_once()
    mock_feed.assert_called_once()


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.feed_issues_to_pipeline", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.fetch_issues", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.async_session_factory")
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_cycle_two_repos_serial(
    mock_settings: MagicMock,
    mock_session_factory: MagicMock,
    mock_fetch: AsyncMock,
    mock_feed: AsyncMock,
) -> None:
    """Two repos → both polled serially."""
    mock_settings.intake_poll_enabled = True
    mock_settings.intake_poll_token = "ghp_test"

    repo1 = _make_repo("org", "repo1")
    repo2 = _make_repo("org", "repo2")
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [repo1, repo2]
    mock_session.execute.return_value = mock_result
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_fetch.return_value = PollResult(
        issues=[],
        etag=None,
        last_modified=None,
        rate_limit_remaining=4999,
    )
    mock_feed.return_value = 0

    repos, _issues, _hit = await run_poll_cycle()

    assert repos == 2
    assert mock_fetch.call_count == 2
    assert mock_feed.call_count == 2


@pytest.mark.asyncio
@patch("src.ingress.poll.scheduler.asyncio.sleep", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.feed_issues_to_pipeline", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.fetch_issues", new_callable=AsyncMock)
@patch("src.ingress.poll.scheduler.async_session_factory")
@patch("src.ingress.poll.scheduler.settings")
async def test_poll_cycle_rate_limit_skips_remaining(
    mock_settings: MagicMock,
    mock_session_factory: MagicMock,
    mock_fetch: AsyncMock,
    mock_feed: AsyncMock,
    mock_sleep: AsyncMock,
) -> None:
    """Rate limit on 2nd repo → backs off and skips remaining."""
    mock_settings.intake_poll_enabled = True
    mock_settings.intake_poll_token = "ghp_test"

    repo1 = _make_repo("org", "repo1")
    repo2 = _make_repo("org", "repo2")
    repo3 = _make_repo("org", "repo3")
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [repo1, repo2, repo3]
    mock_session.execute.return_value = mock_result
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # First repo succeeds, second hits rate limit
    mock_fetch.side_effect = [
        PollResult(issues=[], etag=None, last_modified=None, rate_limit_remaining=200),
        RateLimitError("rate limited", retry_after=30),
    ]
    mock_feed.return_value = 0

    repos, _issues, hit = await run_poll_cycle()

    assert repos == 1  # only first repo counted
    assert hit is True
    assert mock_fetch.call_count == 2  # tried 2, 3rd skipped
    mock_sleep.assert_called_once_with(30)
