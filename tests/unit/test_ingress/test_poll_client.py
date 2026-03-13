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


@respx.mock
def test_fetch_issues_429_rate_limit() -> None:
    """429 with retry-after raises RateLimitError."""
    respx.get("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(429, headers={"retry-after": "120"})
    )
    config = PollConfig(owner="owner", repo="repo", token="secret")
    with pytest.raises(RateLimitError) as exc_info:
        asyncio.run(fetch_issues(config))
    assert exc_info.value.retry_after == 120


@respx.mock
def test_fetch_issues_pagination_via_link_header() -> None:
    """Follows Link header for pagination and merges results."""
    base_url = "https://api.github.com/repos/owner/repo/issues"
    page2_url = "https://api.github.com/repos/owner/repo/issues?page=2"

    call_count = 0

    def _side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json=[{"number": 1, "updated_at": "2026-03-11T12:00:00Z"}],
                headers={
                    "x-ratelimit-remaining": "4998",
                    "link": f'<{page2_url}>; rel="next"',
                },
            )
        return httpx.Response(
            200,
            json=[{"number": 2, "updated_at": "2026-03-11T13:00:00Z"}],
            headers={"x-ratelimit-remaining": "4997"},
        )

    respx.get(base_url).mock(side_effect=_side_effect)
    respx.route(url__regex=r".*/issues\?page=2").mock(side_effect=_side_effect)
    config = PollConfig(owner="owner", repo="repo", token="secret")
    result = asyncio.run(fetch_issues(config))
    assert len(result.issues) == 2
    assert result.issues[0]["number"] == 1
    assert result.issues[1]["number"] == 2


@respx.mock
def test_fetch_issues_low_remaining_early_return() -> None:
    """Low x-ratelimit-remaining triggers early return (no pagination)."""
    base_url = "https://api.github.com/repos/owner/repo/issues"
    page2_url = "https://api.github.com/repos/owner/repo/issues?page=2"

    respx.get(base_url).mock(
        return_value=httpx.Response(
            200,
            json=[{"number": 1, "updated_at": "2026-03-11T12:00:00Z"}],
            headers={
                "x-ratelimit-remaining": "50",
                "link": f'<{page2_url}>; rel="next"',
            },
        )
    )
    config = PollConfig(owner="owner", repo="repo", token="secret")
    result = asyncio.run(fetch_issues(config))
    assert len(result.issues) == 1
    assert result.rate_limit_remaining == 50


@respx.mock
def test_fetch_issues_etag_captured() -> None:
    """ETag from response headers is captured in PollResult."""
    respx.get("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(
            200,
            json=[{"number": 1, "updated_at": "2026-03-11T12:00:00Z"}],
            headers={"x-ratelimit-remaining": "4999", "etag": '"new-etag"'},
        )
    )
    config = PollConfig(owner="owner", repo="repo", token="secret")
    result = asyncio.run(fetch_issues(config))
    assert result.etag == '"new-etag"'
