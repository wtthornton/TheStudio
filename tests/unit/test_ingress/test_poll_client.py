"""Unit tests for poll client."""

import asyncio

import httpx
import pytest
import respx

from src.ingress.poll.client import _filter_issues, fetch_issues
from src.ingress.poll.models import PollConfig, RateLimitError


def test_filter_issues_excludes_prs() -> None:
    """Filter out items with pull_request key."""
    issues = [{"number": 1, "title": "Bug"}, {"number": 2, "title": "Feature", "pull_request": {}}]
    filtered = _filter_issues(issues)
    assert len(filtered) == 1
    assert filtered[0]["number"] == 1


@respx.mock
def test_fetch_issues_200() -> None:
    """200 returns issues, filters PRs."""
    respx.get("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"number": 1, "updated_at": "2026-03-11T12:00:00Z", "title": "Issue"},
                {"number": 2, "updated_at": "2026-03-11T13:00:00Z", "pull_request": {}, "title": "PR"},
            ],
            headers={"x-ratelimit-remaining": "4999"},
        )
    )
    config = PollConfig(owner="owner", repo="repo", token="secret")
    result = asyncio.run(fetch_issues(config))
    assert len(result.issues) == 1
    assert result.issues[0]["number"] == 1
    assert result.rate_limit_remaining == 4999


@respx.mock
def test_fetch_issues_304() -> None:
    """304 returns empty issues."""
    respx.get("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(
            304,
            headers={"x-ratelimit-remaining": "5000"},
        )
    )
    config = PollConfig(owner="owner", repo="repo", token="secret", etag='"abc"')
    result = asyncio.run(fetch_issues(config))
    assert len(result.issues) == 0
    assert result.rate_limit_remaining == 5000


@respx.mock
def test_fetch_issues_403_rate_limit() -> None:
    """403 with retry-after raises RateLimitError."""
    respx.get("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(403, headers={"retry-after": "60"})
    )
    config = PollConfig(owner="owner", repo="repo", token="secret")
    with pytest.raises(RateLimitError) as exc_info:
        asyncio.run(fetch_issues(config))
    assert exc_info.value.retry_after == 60
