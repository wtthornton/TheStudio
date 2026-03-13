"""Unit tests for poll scheduler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingress.poll.models import PollResult, RateLimitError
from src.ingress.poll.scheduler import (
    _backoff_seconds,
    _repo_due_for_poll,
    _reset_backoff,
    run_poll_cycle,
)


def _make_repo(
    owner: str = "org",
    repo_name: str = "repo1",
    poll_last_run_at: datetime | None = None,
    poll_interval_minutes: int | None = None,
) -> MagicMock:
    """Create a mock RepoProfileRow with poll_enabled."""
    repo = MagicMock()
    repo.owner = owner
    repo.repo_name = repo_name
    repo.full_name = f"{owner}/{repo_name}"
    repo.poll_enabled = True
    repo.poll_interval_minutes = poll_interval_minutes
    repo.poll_etag = None
    repo.poll_last_modified = None
    repo.poll_since = None
    repo.poll_last_run_at = poll_last_run_at
    return repo


@pytest.fixture(autouse=True)
def _reset_backoff_state() -> None:
    """Reset exponential backoff state between tests."""
    _reset_backoff()


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
    mock_settings.intake_poll_interval_minutes = 10

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
    mock_settings.intake_poll_interval_minutes = 10

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
    mock_settings.intake_poll_interval_minutes = 10

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
    mock_sleep.assert_called_once_with(30)  # first hit → 30s (no multiplier yet)


# ---------------------------------------------------------------------------
# Per-repo interval tests (Story 17.4)
# ---------------------------------------------------------------------------


def test_repo_due_for_poll_never_polled() -> None:
    """Repo never polled → always due."""
    repo = _make_repo(poll_last_run_at=None)
    assert _repo_due_for_poll(repo) is True


@patch("src.ingress.poll.scheduler.settings")
def test_repo_due_for_poll_interval_elapsed(mock_settings: MagicMock) -> None:
    """Repo polled 15 min ago, interval=10 → due."""
    mock_settings.intake_poll_interval_minutes = 10
    repo = _make_repo(poll_last_run_at=datetime.now(timezone.utc) - timedelta(minutes=15))
    assert _repo_due_for_poll(repo) is True


@patch("src.ingress.poll.scheduler.settings")
def test_repo_not_due_for_poll_interval_not_elapsed(mock_settings: MagicMock) -> None:
    """Repo polled 3 min ago, interval=10 → not due."""
    mock_settings.intake_poll_interval_minutes = 10
    repo = _make_repo(poll_last_run_at=datetime.now(timezone.utc) - timedelta(minutes=3))
    assert _repo_due_for_poll(repo) is False


@patch("src.ingress.poll.scheduler.settings")
def test_repo_due_uses_per_repo_interval(mock_settings: MagicMock) -> None:
    """Per-repo interval=5 overrides global=10; polled 6 min ago → due."""
    mock_settings.intake_poll_interval_minutes = 10
    repo = _make_repo(
        poll_last_run_at=datetime.now(timezone.utc) - timedelta(minutes=6),
        poll_interval_minutes=5,
    )
    assert _repo_due_for_poll(repo) is True


@patch("src.ingress.poll.scheduler.settings")
def test_repo_not_due_per_repo_interval(mock_settings: MagicMock) -> None:
    """Per-repo interval=30; polled 10 min ago → not due."""
    mock_settings.intake_poll_interval_minutes = 10
    repo = _make_repo(
        poll_last_run_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        poll_interval_minutes=30,
    )
    assert _repo_due_for_poll(repo) is False


# ---------------------------------------------------------------------------
# Exponential backoff tests (Story 17.6)
# ---------------------------------------------------------------------------


def test_backoff_first_hit_uses_retry_after() -> None:
    """First rate limit → uses retry_after directly."""
    wait = _backoff_seconds(30)
    assert wait == 30


def test_backoff_second_hit_doubles() -> None:
    """Second consecutive rate limit → doubles."""
    _backoff_seconds(30)  # first
    wait = _backoff_seconds(30)  # second
    assert wait == 60  # 30 * 2


def test_backoff_capped_at_15_minutes() -> None:
    """Backoff caps at 900 seconds (15 minutes)."""
    for _ in range(10):
        wait = _backoff_seconds(120)
    assert wait <= 900


def test_backoff_default_retry_after() -> None:
    """No retry_after → uses 60s default."""
    wait = _backoff_seconds(None)
    assert wait == 60


def test_reset_backoff_resets_counter() -> None:
    """Reset clears consecutive counter."""
    _backoff_seconds(30)  # first
    _backoff_seconds(30)  # second
    _reset_backoff()
    wait = _backoff_seconds(30)  # after reset → back to first
    assert wait == 30
