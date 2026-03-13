# Epic 17 — Poll for Issues as Backup to Webhooks

**Author:** Saga
**Date:** 2026-03-11
**Status:** Complete — All Stories Delivered (17.1-17.8)
**Target Sprint:** Sprint 1 complete (2026-03-13); Sprint 2 complete (2026-03-13)

---

## 1. Title

Poll for Issues as Backup to Webhooks — Add an optional polling intake path that periodically checks configured repos for new or updated issues and feeds the same pipeline as webhooks, so environments without a public URL (dev, air-gapped, NAT-only) or with misconfigured webhooks can still trigger the pipeline on real issue events.

## 2. Purpose

**Why this epic exists:** TheStudio today has no way to receive real GitHub issue events when the deployment lacks a public URL (local dev, air-gapped, NAT-only) or when webhooks are misconfigured or temporarily unreachable. Users who want "open an issue → pipeline runs" in those environments have no built-in alternative. This epic adds a polling intake path so the platform can operate in those scenarios and have a backup when webhooks fail.

## 3. Intent

**What we intend to achieve:** Environments without a public URL or with unreliable webhooks can use polling as the primary or backup intake path. Poll-originated issues enter the same pipeline as webhook events, with at-most-once semantics and no rate-limit abuse. Webhooks remain the preferred path when a public URL exists; polling is clearly documented as backup/no-public-URL only. The implementation is opt-in, configurable per repo, and respectful of GitHub API limits.

## 4. Narrative

TheStudio today receives GitHub issue events only via webhook. GitHub must POST to a URL that is reachable from the internet. If the deployment has no public URL (e.g. local dev, air-gapped, or NAT-only), webhooks never arrive and the pipeline is not triggered by real issue events.

**The problem is clear.** Deployments without a public URL can run TheStudio with mock GitHub and use Admin UI, APIs, and the production test rig — but they cannot receive real issue events. Users who want "open an issue → pipeline runs" without exposing a webhook endpoint have no built-in alternative today. Even when a public URL exists, webhooks can be misconfigured or temporarily unreachable; there is no backup path.

**This epic adds an optional polling intake path.** A background task runs on a configurable interval (e.g. every 5–15 minutes), calls the GitHub REST API (`GET /repos/{owner}/{repo}/issues`), identifies new or updated issues not yet seen, and feeds them into the same webhook-handler logic (TaskPacket creation, workflow start). The rest of the pipeline is unchanged. Polling acts as a **backup** when webhooks are unavailable, or as the **primary** intake when no public URL exists.

**Why polling, not other options?** GitHub explicitly recommends webhooks over polling; polling is the documented fallback when webhooks are not feasible. The epic scopes polling as issues-only (no PRs, no other event types) and documents it as "backup / no-public-URL" — never as a replacement for low-latency webhooks where a public URL exists.

**Alignment with architecture.** The idea doc (`docs/ideas/poll-for-issues-backup.md`) and 2025–2026 GitHub API research specify: use `since` and `sort=updated` to minimize API usage; use conditional requests (ETag/Last-Modified) so 304 responses do not count against the rate limit; generate synthetic delivery IDs for poll-originated events to align with existing `(delivery_id, repo)` dedupe; filter out PRs (the issues endpoint returns both). All of this is incorporated into the epic.

**Scope:** This is approximately 2–3 weeks of work across 2 sprints. Sprint 1 builds the poll client, scheduler, and feed pipeline. Sprint 2 adds Admin UI configuration, rate-limit handling, and integration tests.

## 5. References

- Idea and research: `docs/ideas/poll-for-issues-backup.md`
- Current intake: `src/ingress/webhook_handler.py` (webhook only)
- Dedupe: `src/ingress/dedupe.py` (delivery_id + repo)
- TaskPacket model: `src/models/taskpacket.py` (delivery_id, repo, issue_id)
- TaskPacket CRUD: `src/models/taskpacket_crud.py` (get_by_delivery, create)
- Repo registration: `src/repo/` (owner, repo, installation_id)
- Workflow trigger: `src/ingress/workflow_trigger.py` (start_workflow)
- GitHub REST API: [List repository issues](https://docs.github.com/en/rest/issues/issues#list-repository-issues)
- GitHub best practices: [Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)
- Deployment: `docs/deployment.md` (feature flags, THESTUDIO_* env vars)
- Architecture: `thestudioarc/15-system-runtime-flow.md` (Step 1: Intake)
- Domain objects: `.claude/rules/domain-objects.md` (TaskPacket, Intent Specification)
- Pipeline stages: `.claude/rules/pipeline-stages.md`

## 6. Acceptance Criteria

**AC-1: A poll client fetches issues from GitHub API with rate-limit awareness.**
A module in `src/ingress/poll/` exists that:
- Calls `GET /repos/{owner}/{repo}/issues` with `since` (ISO 8601), `sort=updated`, `state=open` (or `all` if configured)
- Uses `Link` headers for pagination (no manual URL construction)
- Filters out PRs (items with `pull_request` key)
- Uses conditional requests (`If-None-Match` or `If-Modified-Since`); on 304, returns empty list and avoids counting against rate limit
- Respects rate limits: checks `x-ratelimit-remaining`, honors `retry-after` and `x-ratelimit-reset`, makes requests serially (no concurrent calls)
- Uses GitHub App installation token when available; falls back to PAT when configured

**AC-2: Polling runs on a configurable interval.**
A scheduler or Temporal workflow runs the poll step at a configurable interval (default 5–15 minutes). The interval is controlled by:
- Feature flag: `THESTUDIO_INTAKE_POLL_ENABLED` (default: `false`)
- Per-repo or global interval (e.g. `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` or repo profile field `poll_interval_minutes`)
- Only repos with polling enabled are polled

**AC-3: Poll-originated issues feed the same pipeline as webhooks.**
For each new or updated issue returned by the poll client:
- Build a payload in webhook shape (repository, issue, etc.)
- Generate a synthetic delivery ID: stable per `(repo, issue_number, updated_at)` so the same issue update is not processed twice
- Call the same TaskPacket creation and workflow trigger logic as the webhook handler
- Use `TaskPacketCreate(repo, issue_id, delivery_id, correlation_id)` and `start_workflow()`
- Existing dedupe (`ix_taskpacket_delivery_repo`) ensures at-most-once processing

**AC-4: Deduplication prevents duplicate processing.**
- Synthetic delivery ID format: e.g. `poll-{repo_slug}-{issue_number}-{updated_at_iso}` (deterministic, collision-free within repo)
- If `get_by_delivery(delivery_id, repo)` returns existing, skip (no TaskPacket, no workflow)
- Per-repo last `since` value (or ETag/Last-Modified) stored so subsequent polls only fetch new/updated issues

**AC-5: Admin UI exposes poll configuration.**
- Admin API: enable/disable polling per repo, set poll interval
- Admin UI: toggle and interval control on repo settings
- Metrics: poll runs, issues discovered, rate limit hits (optional)

**AC-6: Rate limit handling is robust.**
- On 403/429: back off (honor `retry-after`; wait ≥1 min if absent), exponential backoff on repeated failures
- On `x-ratelimit-remaining` near 0: skip remaining repos for this cycle, resume next cycle
- Structured logging: `ingress.poll.rate_limited`, `ingress.poll.backoff`

**AC-7: Poll feature has test coverage.**
- Unit tests: poll client (mock GitHub API), synthetic delivery ID generation, PR filtering
- Integration test: poll discovers new issue → TaskPacket created → workflow started
- Integration test: poll with 304 → no API usage, no TaskPacket created
- Integration test: duplicate synthetic delivery ID → no duplicate TaskPacket

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Polling exceeds rate limits in multi-repo setups | Medium | High | Use `since` and conditional requests; serial processing; skip repos when near limit |
| Synthetic delivery ID collisions | Low | High | Include repo, issue_number, updated_at; format is deterministic |
| Poll and webhook both fire for same issue | Medium | Medium | Synthetic ID is distinct from webhook delivery ID; dedupe by (delivery_id, repo) works for both |
| Scheduler reliability | Medium | Medium | Use Temporal workflow for cron-like scheduling (existing infra) |

## 7. Constraints & Non-Goals

**Constraints:**
- Polling MUST be opt-in (feature flag and per-repo)
- Poll MUST NOT replace webhooks when a public URL exists — document as backup only
- Requests MUST be serial (no concurrent GitHub API calls)
- Synthetic delivery IDs MUST be deterministic and unique per (repo, issue, update)
- Poll MUST use the same pipeline (TaskPacket + workflow) as webhooks
- Issues only — PRs MUST be filtered out
- All code follows existing conventions: type annotations, structured logging with correlation_id

**Non-Goals:**
- Replacing webhooks where a public URL exists
- Real-time or sub-minute latency
- Supporting PRs or other GitHub event types (push, release, etc.)
- Polling when webhooks are healthy and preferred (optional: disable poll when webhook health is good — future enhancement)

## 8. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| **Epic Owner** | Platform Lead | Scope, priority, approve config and behavior |
| **Tech Lead** | Core Engineer | Poll client design, scheduler integration, rate-limit handling |
| **DevOps** | Infrastructure | Feature flags, interval config, metrics |
| **QA** | Quality Engineer | Integration tests, rate-limit and dedupe coverage |

*Note: Role assignments are placeholders for a solo-developer project.*

## 9. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Poll-discovered issues processed | 100% of new/updated issues in polled repos (when poll enabled) | TaskPackets created from poll vs issues in GitHub |
| Duplicate rate | 0% duplicate TaskPackets for same issue/update | No (delivery_id, repo) conflicts |
| Rate limit violations | 0 secondary rate limit hits | No 403/429 from GitHub during normal operation |
| Latency | Poll interval respected (e.g. 5–15 min) | Scheduler run timing |
| Adoption | Configurable; no impact when disabled | Feature flag off = no poll runs |

## 10. Context & Assumptions

**Assumptions:**
- Repo registration (owner, repo, installation_id) and GitHub App/Token acquisition already exist
- `create_taskpacket` and `start_workflow` accept the same inputs as webhook path (verified in `webhook_handler.py`)
- Temporal is available for scheduling (cron-like workflow)
- Admin UI can add repo-level settings (toggle, interval)
- `GET /repos/{owner}/{repo}/issues` returns both issues and PRs; PRs have `pull_request` key

**Dependencies:**
- **[BLOCKING]** Repo profile must support `poll_enabled: bool` and `poll_interval_minutes: int | None`
- **[BLOCKING]** GitHub client must support installation token and conditional request headers

**Systems Affected:**
- `src/ingress/` — new `poll/` submodule (client, scheduler, feed)
- `src/repo/repo_profile.py` — new fields for poll config
- `src/admin/` — poll settings in repo management
- `src/settings.py` — `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`
- `tests/` — unit and integration tests for poll path

**Business Rules:**
- Webhook remains primary when public URL exists; poll is backup or primary-only-when-no-URL
- Poll is issues-only; PRs are never fed into the pipeline from poll
- At-most-once: synthetic delivery ID + existing dedupe ensures no duplicate TaskPackets

---

## Story Map

Stories are ordered by vertical slice: poll client first, feed pipeline second, scheduler third, Admin UI and tests last.

---

### Story 17.1: Poll Client — GitHub API Fetch with Rate Limits

**As a** platform developer,
**I want** a poll client that fetches issues from the GitHub API with rate-limit awareness and conditional requests,
**so that** polling stays within limits and avoids unnecessary API usage.

**Details:**
- Create `src/ingress/poll/__init__.py`
- Create `src/ingress/poll/client.py` with:
  - `fetch_issues(owner: str, repo: str, since: str | None, etag: str | None, last_modified: str | None, token: str) -> PollResult`
  - Uses `GET /repos/{owner}/{repo}/issues` with `since`, `sort=updated`, `state=open`
  - Sends `If-None-Match` or `If-Modified-Since` when provided
  - On 304: return `PollResult(issues=[], etag=..., last_modified=..., rate_limit_remaining=...)`
  - On 200: filter out items with `pull_request` key, return issues only
  - Paginate via `Link` header (no manual URL construction)
  - Check `x-ratelimit-remaining`; if &lt; 100, return early with issues fetched so far
  - On 403/429: raise `RateLimitError` with `retry_after` if present
- Create `src/ingress/poll/models.py`: `PollResult`, `PollConfig`, `RateLimitError`

**Acceptance Criteria:**
- Client returns only issues (no PRs)
- Conditional requests reduce API usage on 304
- Pagination follows Link headers
- Rate limit headers are captured and exposed
- Unit tests with mocked GitHub API (200, 304, 403, 429, pagination)

**Files to create:**
- `src/ingress/poll/__init__.py`
- `src/ingress/poll/client.py`
- `src/ingress/poll/models.py`
- `tests/unit/test_ingress/test_poll_client.py`

---

### Story 17.2: Synthetic Delivery ID and Feed Pipeline

**As a** platform developer,
**I want** a stable synthetic delivery ID for poll-originated events and a feed that creates TaskPackets and starts workflows,
**so that** poll-discovered issues enter the pipeline exactly like webhook events.

**Details:**
- Create `src/ingress/poll/feed.py`:
  - `synthetic_delivery_id(repo_full_name: str, issue_number: int, updated_at: str) -> str`
    - Format: `poll-{repo_slug}-{issue_number}-{updated_at_normalized}` (e.g. `poll-owner-repo-42-2026-03-11T12-00-00Z`)
    - Deterministic; same (repo, issue, updated_at) yields same ID
  - `feed_issues_to_pipeline(session, issues: list, repo_full_name: str) -> int`
    - For each issue: compute synthetic_delivery_id
    - Call `is_duplicate(session, delivery_id, repo)` — skip if duplicate
    - Build `TaskPacketCreate(repo, issue_id, delivery_id, correlation_id)`
    - Call `create_taskpacket`, then `start_workflow`
    - Return count of TaskPackets created
- Reuse `src/ingress/dedupe.is_duplicate` and `src/models/taskpacket_crud.create`
- Reuse `src/ingress/workflow_trigger.start_workflow`

**Acceptance Criteria:**
- Synthetic ID is deterministic and unique per (repo, issue_number, updated_at)
- Duplicate (synthetic_id, repo) skips creation
- Created TaskPackets match webhook-created format
- Unit tests: ID generation, dedupe behavior, feed with mocked CRUD

**Files to create:**
- `src/ingress/poll/feed.py`
- `tests/unit/test_ingress/test_poll_feed.py`

---

### Story 17.3: Poll Scheduler and Orchestrator

**As a** platform operator,
**I want** a scheduler that runs the poll step at a configurable interval for all repos with polling enabled,
**so that** new issues are discovered and fed into the pipeline without manual action.

**Details:**
- Create `src/ingress/poll/scheduler.py` (or Temporal workflow `PollIntakeWorkflow`):
  - Load repos with `poll_enabled=True` from repo profile
  - For each repo (serial): get token (installation or PAT), fetch issues, feed to pipeline
  - Store per-repo `since` / ETag / Last-Modified for next run
  - On `RateLimitError`: back off, skip remaining repos this cycle
  - Emit structured log: `ingress.poll.run` with repo count, issues found, rate limit status
- Integrate with app startup (APScheduler, background task, or Temporal cron)
- Feature flag: `THESTUDIO_INTAKE_POLL_ENABLED` — when false, scheduler does nothing

**Acceptance Criteria:**
- Scheduler runs at configured interval
- Repos processed serially
- Rate limit triggers backoff and skips remaining repos
- Feature flag disables all poll runs
- Unit tests: mock scheduler run, verify serial order and backoff

**Files to create:**
- `src/ingress/poll/scheduler.py`
- `tests/unit/test_ingress/test_poll_scheduler.py`

**Files to modify:**
- `src/settings.py` — `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`
- `src/app.py` — start poll scheduler when enabled

---

### Story 17.4: Repo Profile and Per-Repo Poll Config

**As a** platform operator,
**I want** per-repo poll enable and interval configuration,
**so that** I can enable polling only for repos that need it.

**Details:**
- Add to repo profile model: `poll_enabled: bool = False`, `poll_interval_minutes: int | None = None`
- Migration: add columns to `repo_profile`
- Admin API: `PATCH /admin/repos/{id}` accepts `poll_enabled`, `poll_interval_minutes`
- Default interval from `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` (e.g. 10) when repo override is null

**Acceptance Criteria:**
- Repo profile stores poll config
- Admin API updates poll config
- Scheduler reads poll_enabled from repo profile

**Files to modify:**
- `src/repo/repo_profile.py` — model fields
- `src/db/migrations/` — new migration
- `src/admin/router.py` — PATCH body includes poll fields

---

### Story 17.5: Admin UI — Poll Settings

**As a** platform operator,
**I want** to enable polling and set the interval per repo in the Admin UI,
**so that** I can configure poll intake without API calls.

**Details:**
- Add poll section to repo settings in Admin UI
- Toggle: "Enable issue polling (backup when webhooks unavailable)"
- Interval input: minutes (default 10, min 5, max 60)
- Help text: "Polling checks GitHub for new/updated issues. Use when webhooks are not available (e.g. no public URL)."

**Acceptance Criteria:**
- Toggle and interval render in repo settings
- Changes persist via Admin API
- Existing Playwright tests still pass

**Files to modify:**
- Admin UI templates (repo settings partial)
- `src/admin/ui_router.py` or equivalent

---

### Story 17.6: Rate Limit Handling and Backoff

**As a** platform operator,
**I want** robust rate limit handling so polling never causes GitHub API abuse,
**so that** the integration remains in good standing with GitHub.

**Details:**
- In poll client: on 403/429, raise `RateLimitError` with `retry_after` seconds
- In scheduler: catch `RateLimitError`, wait `retry_after` (or 60s if absent), then skip remaining repos for this cycle
- Log: `ingress.poll.rate_limited` with repo, retry_after
- Exponential backoff: if rate limited N times in a row, double wait up to max 15 min
- Respect `x-ratelimit-remaining` before each request; if &lt; 50, skip remaining repos

**Acceptance Criteria:**
- 403/429 triggers backoff and repo skip
- `retry-after` honored when present
- No repeated hammering after rate limit
- Unit tests: rate limit response handling

**Files to modify:**
- `src/ingress/poll/client.py` — rate limit detection
- `src/ingress/poll/scheduler.py` — backoff logic

---

### Story 17.7: Integration Tests for Poll Path

**As a** developer maintaining the pipeline,
**I want** integration tests for the poll intake path,
**so that** I can verify end-to-end behavior and dedupe.

**Details:**
- Create `tests/integration/test_poll_intake.py`:
  1. **Happy path:** Poll discovers new issue → TaskPacket created → workflow started
  2. **304 path:** Conditional request returns 304 → no TaskPackets created
  3. **Dedupe path:** Same issue polled twice with same updated_at → one TaskPacket only
  4. **PR filtered:** Mock API returns issue + PR → only issue creates TaskPacket
  5. **Feature flag off:** Poll scheduler does not run when disabled
- Use mocked GitHub API (respx, httpx, or similar)

**Acceptance Criteria:**
- All 5 scenarios pass
- Tests run without real GitHub API or tokens
- No impact on existing integration tests

**Files to create:**
- `tests/integration/test_poll_intake.py`

---

### Story 17.8: Documentation and Deployment Notes

**As a** platform operator,
**I want** clear documentation for the poll feature,
**so that** I know when and how to use it.

**Details:**
- Add poll section to `docs/deployment.md`:
  - `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`
  - Per-repo override via Admin UI
  - When to use: no public URL, webhook backup
  - When not to use: prefer webhooks when public URL exists
- Add `docs/ingress.md` or expand existing intake doc: webhook vs poll paths
- Link to `docs/ideas/poll-for-issues-backup.md` for rationale and research

**Acceptance Criteria:**
- Deployment doc includes poll env vars and guidance
- Intake architecture doc describes both paths
- Operator can enable poll from docs alone

**Files to modify:**
- `docs/deployment.md`
- Create or update `docs/ingress.md`

---

## Sprint Mapping (Suggested)

### Sprint A — Poll Client and Feed (Stories 17.1–17.2)
- 17.1: Poll client (2 days)
- 17.2: Synthetic ID and feed (1 day)
- **Sprint goal:** A developer can call the poll client with a mock GitHub response and get issues; feed creates TaskPackets from them.

### Sprint B — Scheduler, Config, UI (Stories 17.3–17.5)
- 17.3: Scheduler (2 days)
- 17.4: Repo profile config (1 day)
- 17.5: Admin UI (1 day)
- **Sprint goal:** Operator can enable polling per repo and see issues discovered on schedule.

### Sprint C — Robustness and Docs (Stories 17.6–17.8)
- 17.6: Rate limit handling (1 day)
- 17.7: Integration tests (1 day)
- 17.8: Documentation (0.5 day)
- **Sprint goal:** Poll is production-ready with tests and docs.

---

## Meridian Review Status

**Status:** Pending (Epic-level review)
**Date:** —
**Verdict:** —

*Epic requires Meridian review before commit. Use `thestudioarc/personas/meridian-review-checklist.md` (Saga section).*

## Sprint 1 Completion (2026-03-13)

Stories 17.1-17.3 delivered with full test coverage:
- **17.1 Poll Client:** 8 unit tests (200, 304, 403, 429, pagination, low remaining, ETag)
- **17.2 Feed Pipeline:** 8 unit tests (ID determinism, format, dedupe, feed CRUD, mixed, missing fields)
- **17.3 Scheduler:** 5 unit tests (feature flag, no token, single repo, serial, rate limit backoff)
- **Per-repo poll state:** `poll_etag`, `poll_last_modified`, `poll_since` columns on RepoProfileRow
- **Total:** 21 new tests, 1,735 unit tests passing, 0 regressions
- All code behind `THESTUDIO_INTAKE_POLL_ENABLED` feature flag (default: `false`)

## Sprint 2 Completion (2026-03-13)

Stories 17.4-17.8 delivered, epic fully complete:
- **17.4 Repo Profile Config:** `poll_last_run_at` column added (migration 021), per-repo interval in scheduler
- **17.5 Admin UI Poll Settings:** Help text added to poll toggle and interval inputs
- **17.6 Rate Limit Handling:** Exponential backoff (2^N, capped 15 min), threshold lowered to 50, backoff resets on success
- **17.7 Integration Tests:** 6 test scenarios (happy path, 304, dedupe, PR filter, feature flag off, full cycle)
- **17.8 Documentation:** `docs/deployment.md` expanded with per-repo override and rate limit info; `docs/ingress.md` created with full architecture
- **Total:** 37 poll tests (16 new), 1,745 unit tests passing, 0 regressions
- All acceptance criteria met across all 8 stories
