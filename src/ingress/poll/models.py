"""Data models for poll intake.

Epic 17 — Poll for Issues as Backup to Webhooks.
"""

from dataclasses import dataclass


@dataclass
class PollResult:
    """Result of fetching issues from GitHub API."""

    issues: list[dict]
    etag: str | None
    last_modified: str | None
    rate_limit_remaining: int


@dataclass
class PollConfig:
    """Configuration for a single repo poll."""

    owner: str
    repo: str
    token: str
    since: str | None = None
    etag: str | None = None
    last_modified: str | None = None


class RateLimitError(Exception):
    """Raised when GitHub API rate limit (403/429) is hit."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
