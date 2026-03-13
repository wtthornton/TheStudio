# Story 17.1 — Poll Client: GitHub API Fetch with Rate Limits

> **As a** platform developer,
> **I want** a poll client that fetches issues from the GitHub API with rate-limit awareness and conditional requests,
> **so that** polling stays within limits and avoids unnecessary API usage.

**Purpose:** Without a poll client that respects rate limits and uses conditional requests, polling would consume API quota and risk secondary rate limits. This story delivers the foundational client so subsequent stories can orchestrate polling safely.

**Intent:** Implement a GitHub API client that fetches issues with `since`, `sort=updated`, conditional headers (ETag/Last-Modified), PR filtering, and pagination. On 304, return empty issues (no rate limit spend). On 403/429, raise `RateLimitError` with `retry_after`. Requests are serial; rate limit headers are exposed to callers.

**Points:** 5 | **Size:** M
**Epic:** 17 — Poll for Issues as Backup to Webhooks
**Sprint:** A (Stories 17.1–17.2)
**Depends on:** None
**Status:** COMPLETE (2026-03-13)

---

## Description

The poll client is the core module that fetches issues from the GitHub REST API for repositories with polling enabled. It must respect rate limits, use conditional requests to minimize API usage (304 responses do not count against rate limit), filter out PRs (the issues endpoint returns both), and paginate via Link headers.

## Tasks

- [x] Create `src/ingress/poll/__init__.py`
- [x] Create `src/ingress/poll/models.py`:
  - `PollResult` dataclass: `issues: list[dict]`, `etag: str | None`, `last_modified: str | None`, `rate_limit_remaining: int`
  - `PollConfig` dataclass: `owner: str`, `repo: str`, `token: str`, `since: str | None`, `etag: str | None`, `last_modified: str | None`
  - `RateLimitError` exception: `retry_after: int | None`
- [x] Create `src/ingress/poll/client.py`:
  - `fetch_issues(config: PollConfig) -> PollResult`
  - Call `GET /repos/{owner}/{repo}/issues?since=...&sort=updated&state=open`
  - Add `If-None-Match: {etag}` or `If-Modified-Since: {last_modified}` when provided
  - On 304: return empty issues, preserve etag/last_modified
  - On 200: filter out items with `pull_request` key, return issues list
  - Follow `Link` header for pagination (no manual URL construction)
  - Check `x-ratelimit-remaining`; if < 100, return early with fetched issues
  - On 403/429: raise `RateLimitError(retry_after=...)` using `retry-after` header if present
- [x] Write unit tests in `tests/unit/test_ingress/test_poll_client.py`:
  - 200 with issues
  - 200 with issues and PRs (PRs filtered out)
  - 304 (empty issues)
  - Pagination via Link
  - 403/429 with retry-after
  - rate_limit_remaining near 0 triggers early return
  - ETag captured from response headers

## Acceptance Criteria

- [x] Client returns only issues (no PRs)
- [x] Conditional requests reduce API usage on 304
- [x] Pagination follows Link headers
- [x] Rate limit headers are captured and exposed
- [x] Unit tests cover 200, 304, 403, 429, pagination, ETag capture, low remaining early return

## Test Cases

| # | Scenario | Input | Expected Output | Status |
|---|----------|-------|-----------------|--------|
| 1 | Valid 200 | Mock 200 with 2 issues | PollResult with 2 issues | PASS |
| 2 | PR filtering | Mock 200 with 1 issue + 1 PR | PollResult with 1 issue | PASS |
| 3 | 304 Not Modified | Mock 304 | PollResult with empty issues, etag preserved | PASS |
| 4 | Pagination | Mock 200 + Link to next page | PollResult with all pages merged | PASS |
| 5 | Rate limit 403 | Mock 403 with retry-after: 60 | RateLimitError(retry_after=60) | PASS |
| 6 | Rate limit 429 | Mock 429 with retry-after: 120 | RateLimitError(retry_after=120) | PASS |
| 7 | Low remaining | x-ratelimit-remaining: 50 | Early return after current page | PASS |
| 8 | ETag captured | Mock 200 with etag header | PollResult.etag populated | PASS |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/poll/__init__.py` | Created |
| `src/ingress/poll/models.py` | Created |
| `src/ingress/poll/client.py` | Created |
| `tests/unit/test_ingress/test_poll_client.py` | Created (8 tests) |

## Technical Notes

- GitHub API: `GET /repos/{owner}/{repo}/issues` — supports `since` (ISO 8601), `sort=updated`, `state=open`
- Conditional: `If-None-Match` (ETag), `If-Modified-Since` (Last-Modified); 304 does not count against rate limit
- PRs have `pull_request` key in response; issues do not
- Uses `httpx` async client with 30s timeout; serial requests per GitHub best practices
