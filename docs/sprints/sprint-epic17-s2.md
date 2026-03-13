# Sprint Plan: Epic 17 — Poll for Issues (Sprint 2: Stories 17.4-17.8)

**Planned by:** Helm
**Date:** 2026-03-13
**Status:** COMPLETE (all stories delivered 2026-03-13)
**Epic:** `docs/epics/epic-17-poll-for-issues-backup.md`
**Sprint Duration:** 2 weeks (10 working days)
**Capacity:** Single developer, 80% commitment = 8 effective days, 2 days buffer

---

## Sprint Goal (Testable Format)

**Objective:** Complete the poll intake feature by adding per-repo poll configuration in the repo profile, Admin UI controls for poll settings, robust rate-limit handling with exponential backoff, integration tests covering the full poll-to-pipeline path, and deployment documentation — so that an operator can enable polling per repo from the Admin UI, and the poll feature is production-ready with documented configuration and verified behavior.

**Test:** After all stories are complete:
1. `RepoProfileRow` has `poll_enabled: bool` and `poll_interval_minutes: int | None` columns persisted via Alembic migration.
2. `PATCH /admin/repos/{id}/profile` with `{"poll_enabled": true, "poll_interval_minutes": 10}` succeeds and persists.
3. Admin UI repo settings page shows a poll toggle and interval input; changes persist via the Admin API.
4. On 403/429 from GitHub API, the scheduler backs off with exponential delay (doubling up to 15 min max), skips remaining repos, and logs `ingress.poll.rate_limited`.
5. When `x-ratelimit-remaining` drops below 50, the scheduler skips remaining repos for the current cycle.
6. Integration test: poll discovers a new issue (mocked GitHub API) -> TaskPacket created -> workflow started.
7. Integration test: poll with 304 -> no TaskPacket created.
8. Integration test: duplicate synthetic delivery ID -> no duplicate TaskPacket.
9. Integration test: mock API returns issue + PR -> only issue creates TaskPacket.
10. Integration test: `THESTUDIO_INTAKE_POLL_ENABLED=false` -> scheduler does not run.
11. `docs/deployment.md` includes `THESTUDIO_INTAKE_POLL_ENABLED`, `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`, and per-repo override guidance.
12. All existing tests pass unchanged: `pytest` exits 0 with no regressions.
13. `ruff check src/ingress/poll/ src/repo/ src/admin/` exits 0.

**Constraint:** 8 effective working days. The `THESTUDIO_INTAKE_POLL_REPOS` env var workaround from Sprint 1 is deprecated and replaced by per-repo `poll_enabled` in Story 17.4. All new code follows existing coding standards. No changes to existing webhook handler or pipeline workflow.

---

## Ordered Backlog (with rationale)

### Story 17.4: Repo Profile and Per-Repo Poll Config (2 days)

**Why first:** The scheduler (17.3) currently uses an env var workaround for repo selection. This story replaces it with proper per-repo config, which is a prerequisite for the Admin UI (17.5) and for rate limit handling to know which repos to poll. This is also the only story with a DB migration, so it should land first to unblock all other work.

**Deliverables:**
- Add `poll_enabled: bool = False` and `poll_interval_minutes: int | None = None` to `RepoProfileRow` model
- Alembic migration adding both columns to `repo_profile` table
- Update `PATCH /admin/repos/{id}/profile` to accept `poll_enabled` and `poll_interval_minutes`
- Update `PollScheduler` to read `poll_enabled` from repo profile instead of `THESTUDIO_INTAKE_POLL_REPOS` env var
- Deprecate `THESTUDIO_INTAKE_POLL_REPOS` with a log warning if set
- Unit tests for repo profile updates and scheduler repo filtering

**Estimation reasoning:** Schema change is straightforward — two columns, one migration. The Admin API PATCH endpoint already exists and accepts arbitrary profile fields. The scheduler modification to read from repo profile instead of env var is a ~20-line change. 2 days includes migration testing and verifying backward compatibility.

**Unknowns:**
- Whether existing `RepoProfileRow` uses a JSON field or explicit columns for extension fields (will verify)

**Acceptance criteria:**
- Repo profile stores `poll_enabled` and `poll_interval_minutes`
- Admin API PATCH updates both fields
- Scheduler reads `poll_enabled` from repo profile
- `THESTUDIO_INTAKE_POLL_REPOS` env var is deprecated (log warning, still works as fallback)
- Default interval from `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` when repo override is null

---

### Story 17.5: Admin UI — Poll Settings (1.5 days)

**Why second:** With the repo profile supporting poll config (17.4), the Admin UI can render controls. This unblocks operators who need a visual interface to configure polling. Placing it before rate-limit hardening (17.6) means operators can start configuring repos while the robustness work proceeds.

**Deliverables:**
- Poll settings section in repo settings page (Admin UI template)
- Toggle: "Enable issue polling (backup when webhooks unavailable)"
- Interval input: minutes (default 10, min 5, max 60)
- Help text explaining when to use polling
- Verify existing Playwright tests still pass

**Estimation reasoning:** Admin UI already has a repo settings page. Adding a toggle and input field with help text is template work. 1.5 days includes CSS/layout, validation, and verifying no Playwright regressions.

**Unknowns:**
- Whether the Admin UI repo settings partial uses HTMX or traditional form submission (will check existing patterns)

**Acceptance criteria:**
- Toggle and interval render in repo settings
- Changes persist via Admin API (PATCH)
- Existing Playwright tests still pass
- Help text guides operators on when to use polling

---

### Story 17.6: Rate Limit Handling and Backoff (1.5 days)

**Why third:** Sprint 1 implemented basic rate-limit detection (403/429 raises `RateLimitError`). This story hardens the scheduler with exponential backoff, `retry-after` header honoring, and proactive skip when `x-ratelimit-remaining` is low. This is critical for production safety before integration tests (17.7) validate the full path.

**Deliverables:**
- In `PollClient`: enhance rate-limit detection to parse `retry-after` header
- In `PollScheduler`: implement exponential backoff on repeated rate limits (double wait each consecutive hit, max 15 min)
- In `PollScheduler`: check `x-ratelimit-remaining` before each repo; if < 50, skip remaining repos
- Structured logging: `ingress.poll.rate_limited` with repo, retry_after, backoff_seconds
- Unit tests for exponential backoff sequence, retry-after parsing, low-remaining skip

**Estimation reasoning:** The rate-limit detection infrastructure exists from Sprint 1. This adds backoff state tracking (consecutive failures counter, last backoff duration) and proactive skip logic. 1.5 days includes thorough unit tests for the backoff sequence (1min -> 2min -> 4min -> 8min -> 15min cap).

**Unknowns:**
- Whether backoff state should persist across scheduler restarts (decision: no — reset on restart is acceptable; persistent backoff state is over-engineering for the poll interval)

**Acceptance criteria:**
- 403/429 triggers exponential backoff (1, 2, 4, 8, 15 min cap)
- `retry-after` header honored when present (overrides exponential calculation)
- `x-ratelimit-remaining < 50` skips remaining repos
- Consecutive success resets backoff to base
- No repeated hammering after rate limit
- Unit tests cover the full backoff sequence

---

### Story 17.7: Integration Tests for Poll Path (2 days)

**Why fourth:** All components are now in place (client, feed, scheduler, config, rate limits). Integration tests validate the end-to-end behavior with all pieces wired together. This is the verification step before documentation (17.8).

**Deliverables:**
- `tests/integration/test_poll_intake.py` with 5 scenarios:
  1. Happy path: poll discovers new issue -> TaskPacket created -> workflow started
  2. 304 path: conditional request returns 304 -> no TaskPackets created
  3. Dedupe path: same issue polled twice with same updated_at -> one TaskPacket only
  4. PR filtered: mock API returns issue + PR -> only issue creates TaskPacket
  5. Feature flag off: poll scheduler does not run when disabled
- Use mocked GitHub API (respx or httpx mock transport)
- No real GitHub API calls or tokens required

**Estimation reasoning:** 2 days. Integration tests require wiring multiple components together with mocked external dependencies. The test fixtures need to set up a mock GitHub API, configure repos with poll enabled, and verify TaskPacket creation through the CRUD layer. The 5 scenarios cover the critical paths. Mocking strategy (respx vs httpx mock) needs evaluation.

**Unknowns:**
- Whether `respx` is already in test dependencies (if not, `httpx` mock transport is the fallback)
- Whether integration tests need a real database session or can use the in-memory test database

**Acceptance criteria:**
- All 5 scenarios pass
- Tests run without real GitHub API or tokens
- No impact on existing integration tests
- Tests are independently runnable: `pytest tests/integration/test_poll_intake.py`

---

### Story 17.8: Documentation and Deployment Notes (1 day)

**Why last:** Documentation describes the complete, tested feature. Doing it last ensures accuracy — no documenting behavior that changes during the sprint.

**Deliverables:**
- Add poll section to `docs/deployment.md`:
  - `THESTUDIO_INTAKE_POLL_ENABLED` (default: false)
  - `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` (default: 10)
  - Per-repo override via Admin UI
  - When to use: no public URL, webhook backup
  - When not to use: prefer webhooks when public URL exists
- Create or update `docs/ingress.md`: webhook vs poll intake paths, architecture decision
- Link to `docs/ideas/poll-for-issues-backup.md` for rationale

**Estimation reasoning:** 1 day. Straightforward documentation. The feature is complete and tested at this point, so the docs describe reality. The deployment guide follows existing patterns (env vars table, Admin UI guidance).

**Unknowns:** None.

**Acceptance criteria:**
- Deployment doc includes poll env vars and guidance
- Intake architecture doc describes both webhook and poll paths
- Operator can enable poll from docs alone (no source code reading required)

---

## Dependency List

| Dependency | Type | Status | Impact if Missing |
|-----------|------|--------|-------------------|
| Sprint 1 complete (Stories 17.1-17.3) | Internal | DONE | Cannot proceed — all Sprint 2 stories build on Sprint 1 |
| `src/repo/repo_profile.py` — model extensible | Internal | Available | Must add poll fields (Story 17.4) |
| `src/admin/router.py` — PATCH endpoint exists | Internal | Available | Must extend to accept poll fields |
| Admin UI repo settings template | Internal | Available | Must add poll section (Story 17.5) |
| `respx` or `httpx` mock transport for tests | External | Evaluate | Integration tests need mock HTTP; fallback to httpx mock if respx unavailable |
| `docs/deployment.md` — exists | Internal | Available | Must add poll section |

**No external or cross-team dependencies.** All work is internal to the TheStudio codebase.

---

## Estimation Notes

| Story | Estimate | Confidence | Risk |
|-------|----------|-----------|------|
| 17.4: Repo Profile Config | 2 days | High | Low — schema change and API extension are well-understood |
| 17.5: Admin UI Poll Settings | 1.5 days | Medium | Low-Medium — depends on Admin UI template patterns |
| 17.6: Rate Limit Handling | 1.5 days | High | Low — builds on Sprint 1 infrastructure |
| 17.7: Integration Tests | 2 days | Medium | Medium — wiring multiple components with mocks has unknowns |
| 17.8: Documentation | 1 day | High | Low — straightforward |
| **Total** | **8 days** | **Medium-High** | — |

**Fits within 8 effective days (80% of 10-day sprint).** 2-day buffer for unknowns, debugging, and code review.

---

## Capacity Allocation

| Activity | Days | % |
|----------|------|---|
| Story 17.4 (Repo Profile Config) | 2 | 20% |
| Story 17.5 (Admin UI Poll Settings) | 1.5 | 15% |
| Story 17.6 (Rate Limit Handling) | 1.5 | 15% |
| Story 17.7 (Integration Tests) | 2 | 20% |
| Story 17.8 (Documentation) | 1 | 10% |
| Buffer (unknowns, review, debugging) | 2 | 20% |
| **Total** | **10** | **100%** |

Never at 100% commitment. 20% buffer for unknowns.

---

## Compressible Stories (What Gets Cut)

If time runs short:

1. **Cut first:** Story 17.8 (Documentation) — The feature works without docs. Documentation can be a Sprint 3 task or done asynchronously. Risk: operators must read source code to configure.
2. **Cut second:** Story 17.5 (Admin UI) — Operators can still configure poll via Admin API (PATCH). The UI is convenience, not capability. Risk: less discoverability.
3. **Do not cut:** Stories 17.4, 17.6, 17.7 — Per-repo config replaces the env var workaround (tech debt), rate limit hardening is production safety, and integration tests are verification. These are the core value of Sprint 2.

---

## Retro Reference

**Sprint 1 retro observations (from Sprint 1 plan):**
- All 3 Sprint 1 stories delivered with 21 new tests, 0 regressions
- Per-repo poll state (poll_etag, poll_last_modified, poll_since) was added to RepoProfileRow during Sprint 1, partially overlapping with Sprint 2's Story 17.4
- Feature flag pattern (THESTUDIO_INTAKE_POLL_ENABLED) works well
- Stories consistently completed faster than estimated in recent sprints

**Actions carried into this sprint:**
- Deprecate `THESTUDIO_INTAKE_POLL_REPOS` env var (tech debt from Sprint 1) — addressed in Story 17.4
- Epic-level Meridian review still pending — note: Sprint 2 stories are behind the same feature flag; epic review should proceed in parallel

---

## Definition of Done

- [x] All 5 stories delivered with unit and integration tests
- [x] `ruff check src/ingress/poll/ src/repo/ src/admin/` exits 0
- [x] `mypy src/ingress/poll/` exits 0
- [x] All existing tests pass (no regressions) — 1,745 passing
- [x] Per-repo `poll_enabled` and `poll_interval_minutes` in repo profile
- [x] Integration tests cover 6 poll scenarios (5 required + 1 bonus)
- [x] `docs/deployment.md` includes poll configuration guidance
- [x] Structured logging with correlation_id on all poll operations
- [x] Type annotations on all public interfaces
- [x] Code follows `thestudioarc/20-coding-standards.md`

---

## Meridian Review

**Reviewer:** Meridian (VP Success)
**Date:** 2026-03-13
**Verdict:** CONDITIONAL PASS — 3 gaps identified and resolved

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | Parent epic (17) still has not passed Meridian epic-level review; Sprint 2 increases feature surface | Low | Acceptable: feature flag defaults to false, no production behavior without opt-in. Epic review proceeds in parallel. |
| 2 | Story 17.5 references "existing Playwright tests" without specifying which tests or verification method | Low | Added: run Playwright test suite after Admin UI changes; verify zero regressions in repo settings tests. |
| 3 | Sprint 1 in-memory poll state vs DB-backed poll state columns not explicitly connected | Low | Clarified: Sprint 1 already added `poll_etag`, `poll_last_modified`, `poll_since` to `RepoProfileRow` and the scheduler reads from them. Story 17.4 adds `poll_enabled` and `poll_interval_minutes` to the same model — no state migration needed. |

**All 3 gaps resolved in plan.** Status updated to COMMITTED.
