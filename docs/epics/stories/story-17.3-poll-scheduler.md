# Story 17.3 — Poll Scheduler and Orchestrator

> **As a** platform operator,
> **I want** a scheduler that runs the poll step at a configurable interval for all repos with polling enabled,
> **so that** new issues are discovered and fed into the pipeline without manual action.

**Purpose:** Without a scheduler, polling would never run automatically. This story delivers the orchestration that periodically fetches issues and feeds them into the pipeline so operators get hands-free intake when webhooks are unavailable.

**Intent:** Run the poll cycle at a configurable interval (e.g. 5–15 minutes). Load repos with `poll_enabled=True`, process them serially, store per-repo since/etag for the next run, and handle rate limits by backing off and skipping remaining repos. Respect feature flag `THESTUDIO_INTAKE_POLL_ENABLED`.

**Points:** 5 | **Size:** M  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** B (Stories 17.3–17.5)  
**Depends on:** Story 17.1, 17.2, 17.4 (repo profile config)

---

## Description

The scheduler runs the poll step periodically. It loads repos with `poll_enabled=True`, processes them serially (to respect GitHub secondary rate limits), stores per-repo `since` / ETag / Last-Modified for the next run, and handles rate limit errors with backoff and skip-remaining logic.

## Tasks

- [ ] Create `src/ingress/poll/scheduler.py`:
  - `run_poll_cycle(session: AsyncSession) -> PollCycleResult`
    - Query repos with `poll_enabled=True`
    - For each repo (serial): get token, build PollConfig with stored since/etag, call `fetch_issues`, call `feed_issues_to_pipeline`
    - On `RateLimitError`: back off (wait retry_after or 60s), skip remaining repos, log
    - Store per-repo `since` / ETag / Last-Modified for next run (e.g. in poll_state table or repo profile)
  - `start_poll_scheduler(interval_minutes: int) -> None`
    - APScheduler, background task, or Temporal cron
    - Run `run_poll_cycle` every `interval_minutes`
- [ ] Add `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` to `src/settings.py`
- [ ] In `src/app.py`: start scheduler on startup when `THESTUDIO_INTAKE_POLL_ENABLED=True`
- [ ] Feature flag: if False, scheduler does nothing
- [ ] Structured log: `ingress.poll.run` with repo_count, issues_found, rate_limit_hit

## Acceptance Criteria

- [ ] Scheduler runs at configured interval
- [ ] Repos processed serially (one at a time)
- [ ] Rate limit triggers backoff and skips remaining repos
- [ ] Feature flag `THESTUDIO_INTAKE_POLL_ENABLED=False` disables all poll runs
- [ ] Unit tests: mock cycle run, verify serial order and backoff

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Feature flag off | THESTUDIO_INTAKE_POLL_ENABLED=False | Scheduler never runs |
| 2 | One repo | 1 repo with poll enabled | Poll client called once |
| 3 | Two repos | 2 repos | Poll client called twice, serially |
| 4 | Rate limit mid-cycle | 2nd repo raises RateLimitError | 1st repo processed; 2nd skipped; backoff logged |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/poll/scheduler.py` | Create |
| `src/settings.py` | Modify (add env vars) |
| `src/app.py` | Modify (start scheduler when enabled) |
| `tests/unit/test_ingress/test_poll_scheduler.py` | Create |
