"""Poll scheduler — runs poll cycle at configurable interval.

Epic 17 — Poll for Issues as Backup to Webhooks.
Supports per-repo poll intervals and exponential backoff on rate limits.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from src.db.connection import async_session_factory
from src.ingress.poll.client import fetch_issues
from src.ingress.poll.feed import feed_issues_to_pipeline
from src.ingress.poll.models import PollConfig, RateLimitError
from src.repo.repo_profile import RepoProfileRow, RepoStatus
from src.settings import settings

logger = logging.getLogger(__name__)

# Exponential backoff state (Story 17.6)
_consecutive_rate_limits = 0
MAX_BACKOFF_SECONDS = 900  # 15 minutes


def _backoff_seconds(retry_after: int | None) -> int:
    """Calculate backoff with exponential escalation on consecutive rate limits.

    First hit: use retry_after (or 60s default).
    Consecutive hits: double the wait each time, capped at 15 minutes.
    """
    global _consecutive_rate_limits
    _consecutive_rate_limits += 1

    base = retry_after or 60
    multiplier = 2 ** (_consecutive_rate_limits - 1)
    wait = min(base * multiplier, MAX_BACKOFF_SECONDS)

    logger.warning(
        "ingress.poll.rate_limited consecutive=%d backoff=%ds",
        _consecutive_rate_limits,
        wait,
    )
    return wait


def _reset_backoff() -> None:
    """Reset consecutive rate limit counter after a successful cycle."""
    global _consecutive_rate_limits
    _consecutive_rate_limits = 0


def _repo_due_for_poll(repo: RepoProfileRow) -> bool:
    """Check if a repo is due for polling based on its per-repo interval.

    Uses repo.poll_interval_minutes if set, otherwise the global default.
    Returns True if the repo has never been polled or the interval has elapsed.
    """
    if repo.poll_last_run_at is None:
        return True

    interval_minutes = repo.poll_interval_minutes or settings.intake_poll_interval_minutes
    now = datetime.now(UTC)
    elapsed = (now - repo.poll_last_run_at).total_seconds()
    return elapsed >= interval_minutes * 60


async def run_poll_cycle() -> tuple[int, int, bool]:
    """Run one poll cycle for all repos with poll_enabled.

    Processes repos serially. Skips repos not due for polling (per-repo interval).
    On RateLimitError, backs off exponentially and skips remaining repos.

    Returns:
        (repos_polled, issues_created, rate_limit_hit)
    """
    if not settings.intake_poll_enabled:
        return 0, 0, False

    token = settings.intake_poll_token
    if not token:
        logger.warning("poll.scheduler.skip intake_poll_token not set")
        return 0, 0, False

    repos_polled = 0
    issues_created = 0
    rate_limit_hit = False

    async with async_session_factory() as session:
        stmt = select(RepoProfileRow).where(
            RepoProfileRow.poll_enabled.is_(True),
            RepoProfileRow.status == RepoStatus.ACTIVE,
            RepoProfileRow.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        repos = list(result.scalars().all())

        for repo in repos:
            if not _repo_due_for_poll(repo):
                logger.debug(
                    "poll.skip repo=%s not due (interval=%dm)",
                    repo.full_name,
                    repo.poll_interval_minutes or settings.intake_poll_interval_minutes,
                )
                continue

            try:
                config = PollConfig(
                    owner=repo.owner,
                    repo=repo.repo_name,
                    token=token,
                    since=repo.poll_since,
                    etag=repo.poll_etag,
                    last_modified=repo.poll_last_modified,
                )
                result = await fetch_issues(config)
                count = await feed_issues_to_pipeline(
                    session,
                    result.issues,
                    repo.full_name,
                    pipeline_comments_override=repo.pipeline_comments_enabled,
                )

                # Persist poll state for next cycle
                if result.etag:
                    repo.poll_etag = result.etag
                if result.last_modified:
                    repo.poll_last_modified = result.last_modified
                if result.issues:
                    latest = max(i.get("updated_at", "") for i in result.issues)
                    if latest:
                        repo.poll_since = latest
                repo.poll_last_run_at = datetime.now(UTC)
                await session.commit()

                repos_polled += 1
                issues_created += count
                logger.info(
                    "poll.run repo=%s issues=%d rate_limit_remaining=%d",
                    repo.full_name,
                    count,
                    result.rate_limit_remaining,
                )
            except RateLimitError as exc:
                rate_limit_hit = True
                wait_sec = _backoff_seconds(exc.retry_after)
                logger.warning(
                    "ingress.poll.rate_limited repo=%s retry_after=%ds",
                    repo.full_name,
                    wait_sec,
                )
                await asyncio.sleep(wait_sec)
                break

    if not rate_limit_hit and repos_polled > 0:
        _reset_backoff()

    return repos_polled, issues_created, rate_limit_hit


def start_poll_scheduler() -> asyncio.Task | None:
    """Start background poll scheduler (when enabled).

    Runs poll cycle every intake_poll_interval_minutes.
    Returns the background task, or None if polling disabled.
    """
    if not settings.intake_poll_enabled:
        return None

    interval_sec = settings.intake_poll_interval_minutes * 60

    async def _loop() -> None:
        while True:
            try:
                repos, issues, _ = await run_poll_cycle()
                if repos > 0:
                    logger.info("poll.cycle complete repos=%d issues=%d", repos, issues)
            except Exception:
                logger.exception("poll.cycle failed")
            await asyncio.sleep(interval_sec)

    task = asyncio.create_task(_loop())
    logger.info("poll.scheduler started interval=%dmin", settings.intake_poll_interval_minutes)
    return task
