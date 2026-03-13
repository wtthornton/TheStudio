# Story 17.3 — Poll Scheduler and Orchestrator

> **As a** platform operator,
> **I want** a scheduler that runs the poll step at a configurable interval for all repos with polling enabled,
> **so that** new issues are discovered and fed into the pipeline without manual action.

**Purpose:** Without a scheduler, polling would never run automatically. This story delivers the orchestration that periodically fetches issues and feeds them into the pipeline so operators get hands-free intake when webhooks are unavailable.

**Intent:** Run the poll cycle at a configurable interval (e.g. 5–15 minutes). Load repos with `poll_enabled=True`, process them serially, store per-repo since/etag for the next run, and handle rate limits by backing off and skipping remaining repos. Respect feature flag `THESTUDIO_INTAKE_POLL_ENABLED`.

**Points:** 5 | **Size:** M
**Epic:** 17 — Poll for Issues as Backup to Webhooks
**Sprint:** B (Stories 17.3–17.5)
**Depends on:** Story 17.1, 17.2
**Status:** COMPLETE (2026-03-13)

---

## Description

The scheduler runs the poll step periodically. It loads repos with `poll_enabled=True`, processes them serially (to respect GitHub secondary rate limits), stores per-repo `since` / ETag / Last-Modified for the next run, and handles rate limit errors with backoff and skip-remaining logic.

## Tasks

- [x] Create `src/ingress/poll/scheduler.py`:
  - `run_poll_cycle() -> tuple[int, int, bool]` (repos_polled, issues_created, rate_limit_hit)
    - Query repos with `poll_enabled=True`
    - For each repo (serial): get token, build PollConfig with stored since/etag, call `fetch_issues`, call `feed_issues_to_pipeline`
    - On `RateLimitError`: back off (wait retry_after or 60s), skip remaining repos, log
    - Store per-repo `since` / ETag / Last-Modified for next run via RepoProfileRow columns
  - `start_poll_scheduler() -> asyncio.Task | None`
    - asyncio background task
    - Run `run_poll_cycle` every `intake_poll_interval_minutes`
- [x] Add `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`, `THESTUDIO_INTAKE_POLL_TOKEN` to `src/settings.py`
- [x] In `src/app.py`: start scheduler on startup when `THESTUDIO_INTAKE_POLL_ENABLED=True`
- [x] Feature flag: if False, scheduler does nothing
- [x] Structured log: `ingress.poll.run` with repo_count, issues_found, rate_limit_hit
- [x] Per-repo poll state persistence: `poll_etag`, `poll_last_modified`, `poll_since` columns on `RepoProfileRow`
- [x] Write unit tests in `tests/unit/test_ingress/test_poll_scheduler.py`

## Acceptance Criteria

- [x] Scheduler runs at configured interval
- [x] Repos processed serially (one at a time)
- [x] Rate limit triggers backoff and skips remaining repos
- [x] Feature flag `THESTUDIO_INTAKE_POLL_ENABLED=False` disables all poll runs
- [x] Per-repo poll state (since/etag/last_modified) persisted between cycles
- [x] Unit tests: mock cycle run, verify serial order and backoff

## Test Cases

| # | Scenario | Input | Expected Output | Status |
|---|----------|-------|-----------------|--------|
| 1 | Feature flag off | THESTUDIO_INTAKE_POLL_ENABLED=False | Scheduler never runs | PASS |
| 2 | No token | intake_poll_token="" | Skip with warning | PASS |
| 3 | One repo | 1 repo with poll enabled | Poll client called once | PASS |
| 4 | Two repos | 2 repos | Poll client called twice, serially | PASS |
| 5 | Rate limit mid-cycle | 2nd repo raises RateLimitError | 1st repo processed; 2nd skipped; backoff logged | PASS |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/poll/scheduler.py` | Created |
| `src/settings.py` | Modified (add env vars) |
| `src/app.py` | Modified (start scheduler when enabled) |
| `src/repo/repo_profile.py` | Modified (add poll_etag, poll_last_modified, poll_since columns) |
| `tests/unit/test_ingress/test_poll_scheduler.py` | Created (5 tests) |
