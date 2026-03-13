# Sprint Plan: Epic 17 — Poll for Issues (Sprint 1: Stories 17.1-17.3)

**Planned by:** Helm
**Date:** 2026-03-13
**Status:** COMPLETE (2026-03-13) — All 3 stories delivered, 1,735 tests passing
**Epic:** `docs/epics/epic-17-poll-for-issues-backup.md`
**Sprint Duration:** 2 weeks (10 working days)
**Capacity:** Single developer, 80% commitment = 8 effective days, 2 days buffer

---

## Sprint Goal (Testable Format)

**Objective:** Deliver a working poll client that can fetch issues from the GitHub API with rate-limit awareness, a feed pipeline that converts poll-discovered issues into TaskPackets via synthetic delivery IDs, and a configurable scheduler that runs the poll cycle for enabled repos — so that a developer can enable polling for a repo and see new issues enter the same pipeline as webhook events.

**Test:** After all stories are complete:
1. `PollClient.fetch_issues(owner, repo, since, token)` returns filtered issues (no PRs) from a mocked GitHub API response.
2. Conditional requests with ETag return empty on 304 without consuming rate limit.
3. `synthetic_delivery_id("owner/repo", 42, "2026-03-13T12:00:00Z")` returns a deterministic, stable string.
4. `feed_issues_to_pipeline(session, issues, repo)` creates TaskPackets and triggers workflows; duplicate synthetic IDs are skipped.
5. The scheduler loads repos with `poll_enabled=True`, fetches issues serially, feeds them to the pipeline, and backs off on rate limit errors.
6. Feature flag `THESTUDIO_INTAKE_POLL_ENABLED=false` prevents all poll runs.
7. All unit tests pass: `pytest tests/unit/test_ingress/test_poll_client.py tests/unit/test_ingress/test_poll_feed.py tests/unit/test_ingress/test_poll_scheduler.py`
8. All existing tests pass unchanged: `pytest` exits 0 with no regressions.
9. `ruff check src/ingress/poll/` exits 0. `mypy src/ingress/poll/` exits 0.

**Constraint:** 8 effective working days. Stories 17.4-17.8 (repo profile config, Admin UI, rate limit hardening, integration tests, documentation) are explicitly deferred to Sprint 2. All new code behind feature flag `THESTUDIO_INTAKE_POLL_ENABLED` that defaults to `false`. No changes to existing webhook handler or pipeline workflow.

**Note:** Parent epic (Epic 17) has not yet passed Meridian review. Sprint 1 stories (17.1-17.3) are low-risk, self-contained, and behind a feature flag that defaults to off. Epic review should proceed in parallel with Sprint 1 execution.

**Test directory:** Poll test files go in `tests/unit/test_ingress/`. If this directory does not exist, create `tests/unit/test_ingress/__init__.py` and the test files. Verify directory structure before starting Story 17.1.

---

## Ordered Backlog (with rationale)

### Story 17.1: Poll Client — GitHub API Fetch with Rate Limits (3 days)

**Why first:** Everything depends on the client. The feed pipeline (17.2) needs issues to process. The scheduler (17.3) needs the client to call. This is the foundation.

**Deliverables:**
- `src/ingress/poll/__init__.py`
- `src/ingress/poll/client.py` — `PollClient` class with `fetch_issues()` method
- `src/ingress/poll/models.py` — `PollResult`, `PollConfig`, `RateLimitError`
- `tests/unit/test_ingress/test_poll_client.py` — Tests for 200, 304, 403, 429, pagination, PR filtering

**Estimation reasoning:** GitHub API client with conditional requests, pagination via Link headers, rate limit header parsing, and PR filtering. Medium complexity. 3 days includes tests and edge cases (empty responses, malformed headers, partial pages). The `httpx` library is already in the project for HTTP calls.

**Unknowns:**
- Exact behavior of GitHub's `Link` header format for pagination (will consult docs, test with mock responses)
- Whether installation token acquisition needs changes (assumption: existing GitHub client handles this)

**Acceptance criteria:**
- Client returns only issues (no PRs) — items with `pull_request` key filtered out
- Conditional requests (If-None-Match / If-Modified-Since) reduce API usage on 304
- Pagination follows Link headers, not manual URL construction
- Rate limit headers (`x-ratelimit-remaining`, `x-ratelimit-reset`) are captured and exposed in `PollResult`
- 403/429 raises `RateLimitError` with `retry_after` if present
- Unit tests cover: 200 with issues + PRs, 304, 403, 429, pagination (2 pages), empty response

---

### Story 17.2: Synthetic Delivery ID and Feed Pipeline (2 days)

**Why second:** The feed pipeline is the bridge between the poll client and the existing pipeline. It must work before the scheduler can orchestrate anything meaningful.

**Deliverables:**
- `src/ingress/poll/feed.py` — `synthetic_delivery_id()` and `feed_issues_to_pipeline()`
- `tests/unit/test_ingress/test_poll_feed.py` — Tests for ID generation, dedupe, feed with mocked CRUD

**Estimation reasoning:** The synthetic ID function is simple (string formatting + normalization). The feed function calls existing `is_duplicate`, `create_taskpacket`, and `start_workflow` — all well-tested existing code. 2 days includes thorough testing of edge cases (duplicate IDs, empty issue lists, CRUD failures).

**Unknowns:**
- Whether `is_duplicate` signature matches our needs exactly (will verify against `src/ingress/dedupe.py`)
- Whether `start_workflow` requires session management changes for async context

**Acceptance criteria:**
- `synthetic_delivery_id("owner/repo", 42, "2026-03-13T12:00:00Z")` is deterministic — same inputs always produce same output
- Format includes repo slug, issue number, and updated_at — collision-free within a repo
- Duplicate (synthetic_id, repo) skips TaskPacket creation and workflow trigger
- Created TaskPackets match the format produced by the webhook handler
- Unit tests: ID generation (5+ cases), dedupe behavior, feed with 0/1/5 issues, CRUD failure handling

---

### Story 17.3: Poll Scheduler and Orchestrator (3 days)

**Why third:** The scheduler orchestrates client + feed for all enabled repos. It depends on both 17.1 and 17.2. This is the most complex story due to state management (per-repo since/ETag) and backoff logic.

**Deliverables:**
- `src/ingress/poll/scheduler.py` — `PollScheduler` class or Temporal workflow
- `tests/unit/test_ingress/test_poll_scheduler.py` — Tests for serial processing, backoff, feature flag
- Modifications to `src/settings.py` — `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`
- Modifications to `src/app.py` — Start poll scheduler when enabled

**Estimation reasoning:** 3 days. The scheduler must: load enabled repos, iterate serially, manage per-repo state (since/ETag), handle rate limit backoff, and integrate with the app lifecycle. The state management (storing last `since` and ETag per repo) needs a lightweight persistence approach (in-memory for now, DB in Sprint 2 when Story 17.4 adds repo profile fields). The app startup integration requires understanding the existing lifecycle hooks.

**Unknowns:**
- Whether to use APScheduler, Temporal cron, or a simple asyncio background task for scheduling (decision: start with asyncio background task for simplicity; Temporal cron is Sprint 2 enhancement)
- Per-repo state persistence strategy for Sprint 1 (decision: in-memory dict, documented as "resets on restart" limitation; DB-backed in Sprint 2)

**Acceptance criteria:**
- Scheduler runs at configured interval (default: 10 minutes)
- Repos processed serially — no concurrent GitHub API calls
- `RateLimitError` from any repo triggers backoff and skips remaining repos for this cycle
- `THESTUDIO_INTAKE_POLL_ENABLED=false` prevents all poll runs (scheduler starts but immediately returns)
- Structured logging: `ingress.poll.run` with repo count, issues found, rate limit status
- Unit tests: mock scheduler run, verify serial order, backoff on rate limit, feature flag off

---

## Dependency List

| Dependency | Type | Status | Impact if Missing |
|-----------|------|--------|-------------------|
| `src/ingress/dedupe.py` — `is_duplicate()` | Internal | Available | Feed pipeline cannot deduplicate; must implement locally |
| `src/models/taskpacket_crud.py` — `create()` | Internal | Available | Cannot create TaskPackets from poll |
| `src/ingress/workflow_trigger.py` — `start_workflow()` | Internal | Available | Cannot trigger pipeline from poll |
| `src/settings.py` — Settings pattern | Internal | Available | Must add new settings following existing pattern |
| `httpx` library | External | In project dependencies | HTTP client for GitHub API |
| GitHub REST API — List Issues endpoint | External | Stable | Core dependency; API is well-documented and versioned |
| Repo profile — `poll_enabled` field | Internal | NOT available (Sprint 2, Story 17.4) | Scheduler uses a settings-based allowlist or polls all registered repos; proper per-repo config in Sprint 2 |

**Key decision:** Story 17.4 (per-repo poll config in repo profile) is deferred to Sprint 2. For Sprint 1, the scheduler will poll all registered repos when `THESTUDIO_INTAKE_POLL_ENABLED=true`, or accept a `THESTUDIO_INTAKE_POLL_REPOS` env var (comma-separated list of `owner/repo`). This keeps Sprint 1 self-contained.

**Tech debt (Sprint 2 cleanup required):** The `THESTUDIO_INTAKE_POLL_REPOS` env var is a temporary workaround. Story 17.4 in Sprint 2 replaces it with proper per-repo `poll_enabled` field in the repo profile model. The env var must be deprecated and removed when 17.4 lands. Track as tech debt item.

---

## Estimation Notes

| Story | Estimate | Confidence | Risk |
|-------|----------|-----------|------|
| 17.1: Poll Client | 3 days | High | Low — well-understood GitHub API; httpx is familiar |
| 17.2: Feed Pipeline | 2 days | High | Low — reuses existing CRUD and workflow trigger |
| 17.3: Scheduler | 3 days | Medium | Medium — state management and app lifecycle integration have unknowns |
| **Total** | **8 days** | **Medium-High** | — |

**Fits within 8 effective days (80% of 10-day sprint).** Buffer is consumed by the sprint itself (2 days). If Story 17.3 runs long, the scheduler integration with `src/app.py` can be simplified (manual start via Admin API endpoint instead of automatic startup).

---

## Capacity Allocation

| Activity | Days | % |
|----------|------|---|
| Story 17.1 (Poll Client) | 3 | 30% |
| Story 17.2 (Feed Pipeline) | 2 | 20% |
| Story 17.3 (Scheduler) | 3 | 30% |
| Buffer (unknowns, code review, debugging) | 2 | 20% |
| **Total** | **10** | **100%** |

Never at 100% commitment. 20% buffer for unknowns.

---

## Compressible Stories (What Gets Cut)

If time runs short:

1. **Cut first:** Story 17.3 scheduler app lifecycle integration — deliver the scheduler class but defer auto-start on app boot to Sprint 2. The scheduler can be started manually via a test or Admin API endpoint.
2. **Cut second:** Story 17.3 backoff logic — deliver a simpler "stop on rate limit, retry next cycle" without exponential backoff. Exponential backoff moves to Story 17.6 (Sprint 2).
3. **Do not cut:** Stories 17.1 and 17.2 — the poll client and feed pipeline are the core value. Without them, Sprint 2 has nothing to build on.

---

## Retro Reference

**First sprint for this workstream.** No prior retro actions specific to Epic 17.

**Relevant learnings from recent sprints (Sprints 17-18, Epic 16):**
- Stories consistently completed faster than estimated (Sprint 17: all 4 stories in < 1 day each vs 1-2 day estimates). This suggests estimates are conservative but appropriate for a new workstream with more unknowns.
- Feature flag pattern works well for incremental rollout — reuse for poll feature.
- Integration with existing pipeline code (webhook handler, workflow trigger) went smoothly in Epic 16 — expect similar for Epic 17.

---

## Definition of Done

- [x] All 3 stories delivered with unit tests (21 new tests)
- [x] `ruff check src/ingress/poll/` exits 0
- [ ] `mypy src/ingress/poll/` exits 0
- [x] All existing tests pass (1,735 total, no regressions)
- [x] Feature flag `THESTUDIO_INTAKE_POLL_ENABLED` defaults to `false`
- [x] Structured logging with correlation_id on poll operations
- [x] Type annotations on all public interfaces
- [x] Code follows `thestudioarc/20-coding-standards.md`
- [x] Per-repo poll state persistence (poll_etag, poll_last_modified, poll_since on RepoProfileRow)

---

## Meridian Review

**Reviewer:** Meridian (VP Success)
**Date:** 2026-03-13
**Verdict:** CONDITIONAL PASS — 3 gaps identified and fixed

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | `THESTUDIO_INTAKE_POLL_REPOS` env var workaround not flagged as tech debt | Low | Added tech debt callout linking to Story 17.4 |
| 2 | Parent epic (17) has not passed Meridian review | Medium | Added note: epic review proceeds in parallel; Sprint 1 is low-risk and behind feature flag |
| 3 | Test directory structure not specified | Low | Added note: create `tests/unit/test_ingress/` if needed; verify before starting |

**All 3 gaps resolved in plan.** Status updated to COMMITTED.
