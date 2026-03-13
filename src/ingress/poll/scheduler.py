"""Poll scheduler — runs poll cycle at configurable interval.

Epic 17 — Poll for Issues as Backup to Webhooks.
"""

import asyncio
import logging

from sqlalchemy import select

from src.db.connection import async_session_factory
from src.ingress.poll.client import fetch_issues
from src.ingress.poll.feed import feed_issues_to_pipeline
from src.ingress.poll.models import PollConfig, RateLimitError
from src.repo.repo_profile import RepoProfileRow, RepoStatus
from src.settings import settings

logger = logging.getLogger(__name__)


async def run_poll_cycle() -> tuple[int, int, bool]:
    """Run one poll cycle for all repos with poll_enabled.

    Processes repos serially. On RateLimitError, backs off and skips remaining repos.

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
                count = await feed_issues_to_pipeline(session, result.issues, repo.full_name)

                # Persist poll state for next cycle
                if result.etag:
                    repo.poll_etag = result.etag
                if result.last_modified:
                    repo.poll_last_modified = result.last_modified
                if result.issues:
                    latest = max(i.get("updated_at", "") for i in result.issues)
                    if latest:
                        repo.poll_since = latest
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
                wait_sec = exc.retry_after or 60
                logger.warning(
                    "poll.rate_limited repo=%s retry_after=%ds skipping remaining repos",
                    repo.full_name,
                    wait_sec,
                )
                await asyncio.sleep(wait_sec)
                break

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
