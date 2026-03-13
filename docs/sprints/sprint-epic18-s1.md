# Sprint Plan: Epic 18 — Production Test Rig Module Split and Contract Coverage

**Planned by:** Helm
**Date:** 2026-03-12
**Status:** DRAFT -- Awaiting Meridian review
**Epic:** `docs/epics/epic-18-production-test-rig-expansion.md`
**Sprint Duration:** 1 week (5 working days, 2026-03-17 to 2026-03-21)
**Capacity:** Single developer, 30 hours total (5 days x 6 productive hours), 83% allocation = 25 hours, 5 hours buffer

---

## Sprint Goal (Testable Format)

**Objective:** Split the monolithic `test_production_smoke.py` into five focused test modules, add the three missing webhook signature validation tests plus a missing-delivery-header test, add standalone admin API tests decoupled from poll logic, add a pipeline smoke test proving webhooks create TaskPackets, and align the README and contract documentation to reflect 100% endpoint coverage.

**Test:** After all 12 stories are complete:

1. `pytest --collect-only` in `thestudio-production-test-rig/` discovers tests across exactly 5 modules: `test_health.py`, `test_webhook.py`, `test_admin_api.py`, `test_poll_intake.py`, `test_pipeline_smoke.py`. The old `test_production_smoke.py` does not exist.
2. `pytest tests/test_webhook.py --collect-only` shows >= 4 test functions (valid sig, missing sig, bad sig, missing delivery).
3. `pytest tests/test_admin_api.py --collect-only` shows >= 5 test functions (admin health, OpenAPI, repo register, repo list/detail, profile PATCH).
4. `pytest tests/test_pipeline_smoke.py --collect-only` shows >= 1 test function.
5. Running `pytest -v` with no deployment and no env vars produces 0 failures, all skipped.
6. Running `pytest -v` with `WEBHOOK_SECRET` unset produces 0 failures; non-webhook tests run, webhook tests skip with a clear message.
7. Every endpoint in the "Contract: endpoints and behavior" section of `docs/production-test-rig-contract.md` appears in the README's contract-to-test mapping table.
8. `ruff check thestudio-production-test-rig/` exits 0.

**Constraint:** 5 working days. All changes confined to `thestudio-production-test-rig/` and `docs/production-test-rig-contract.md`. No changes to `src/`, `tests/`, or `infra/`. No new runtime dependencies. Tests must remain idempotent and skip gracefully when the deployment is unreachable.

---

## What's In / What's Out

**In this sprint (5 slices, 12 stories, ~25 estimated hours):**
- Slice 1: Module split + conftest hardening (foundation)
- Slice 2: Webhook signature tests (highest-value gap)
- Slice 3: Standalone admin API tests (contract alignment)
- Slice 4: Pipeline smoke test (webhook-triggered TaskPacket)
- Slice 5: Contract alignment and documentation

**Out of scope:**
- Browser/Playwright tests (Epic 12)
- Full pipeline E2E (issue in, PR out) (Epic 15)
- Load testing or performance benchmarking
- Changes to the webhook handler or any application code
- Auth beyond dev-mode `X-User-ID`

---

## Dependency Review (30-Minute Pre-Planning)

### External Dependencies

| Dependency | Status | Owner | Impact if Missing | Mitigation |
|-----------|--------|-------|-------------------|------------|
| Running prod/staging TheStudio deployment | Required at test time | DevOps / developer | All tests skip cleanly | Tests designed to skip; development can proceed against code review alone |
| `WEBHOOK_SECRET` env var matching deployment's `THESTUDIO_WEBHOOK_SECRET` | Required for Slice 2 + 4 | Developer running tests | Webhook + pipeline smoke tests skip | `pytest.skip()` with descriptive message |
| `THESTUDIO_POLL_TEST_REPO` env var | Required for poll E2E only | Developer running tests | Poll E2E skips | Already handled in current code |
| Epic 17 poll endpoints deployed | Optional | N/A | Poll tests skip on 404 | Guard with `poll_enabled` fixture |

### Internal Dependencies (Story-to-Story)

| Story | Depends On | Rationale |
|-------|-----------|-----------|
| 1.2 (conftest hardening) | 1.1 (module split) | New fixtures must exist in the conftest before test modules reference them |
| 2.1-2.4 (webhook tests) | 1.1 + 1.2 | Webhook tests land in `test_webhook.py` (created in 1.1) and use `webhook_secret` fixture (created in 1.2) |
| 3.1-3.2 (admin API tests) | 1.1 | Admin tests land in `test_admin_api.py` (created in 1.1) |
| 4.1 (pipeline smoke) | 1.2 + 2.1 | Pipeline smoke depends on `webhook_secret` fixture and reuses the valid-signature pattern from 2.1 |
| 5.1-5.2 (docs) | 1.1, 2.x, 3.x, 4.1 | Documentation maps tests to contract; needs all tests to exist first |
| 5.3 (delete monolith) | All of the above | Must be last; final validation that nothing references the old file |

### Dependency Verdict

No external blockers. All dependencies are internal and sequential within slices. The critical path is: 1.1 -> 1.2 -> 2.1 -> (2.2, 2.3, 2.4 parallel) -> 3.1 -> 3.2 -> 4.1 -> 5.1 -> 5.2 -> 5.3.

---

## Ordered Backlog

### Day 1 (Stories 1.1, 1.2) -- Foundation

**Story 1.1: Split test_production_smoke.py into focused modules**
- Estimate: 3 hours
- Risk: Low. Mechanical extraction. Highest risk is a subtle import error or fixture scope issue.
- Unknowns: None significant. The current code is 162 lines, well-organized by class.
- Acceptance: `pytest --collect-only` discovers all existing tests in new locations, zero collection errors.
- Files: Create `test_health.py`, `test_admin_api.py`, `test_poll_intake.py`; create stubs in `test_webhook.py`, `test_pipeline_smoke.py`; retain `test_production_smoke.py` temporarily as empty (delete in 5.3).

**Story 1.2: Harden conftest with webhook_secret and poll_enabled fixtures**
- Estimate: 1.5 hours
- Risk: Low. Adding fixtures, not changing existing ones.
- Unknowns: Should `webhook_secret` be session-scoped or function-scoped? Session-scoped is correct -- the env var does not change mid-run.
- Assumptions: `WEBHOOK_SECRET` env var name matches what the README documents. Confirmed.
- Acceptance: Running with no env vars gives clean skips, no errors. `webhook_secret` fixture returns the secret string or skips. `poll_enabled` fixture probes the deployment.
- Files: Modify `conftest.py`.

**Rationale for Day 1 ordering:** Everything downstream depends on the split (1.1) and the fixtures (1.2). This is pure risk reduction -- if the split breaks something, we find out immediately. No creative work required; this is mechanical restructuring.

---

### Day 2 (Stories 2.1, 2.2, 2.3, 2.4) -- Webhook Tests

**Story 2.1: Webhook test with valid signature**
- Estimate: 2.5 hours
- Risk: Medium. This is the most technically complex story.
- Unknowns discovered during estimation:
  - The webhook handler looks up the secret per-repo (via `get_webhook_secret()`). This means the test must register a repo first (so the deployment stores the secret), then send a webhook for that repo. The `WEBHOOK_SECRET` env var must match the deployment's `THESTUDIO_WEBHOOK_SECRET` (which is used as the default secret when repos are registered via admin API).
  - The handler checks `X-GitHub-Delivery` before `X-Hub-Signature-256`. Order matters for test 2.4.
  - The handler returns 404 if the repo is not registered. The valid-signature test must register first.
  - The handler returns 200 for non-`issues` events (event type filter is after signature validation). Using `X-GitHub-Event: issues` should yield 201 if the repo is registered and the issue is new.
- Assumptions: The deployment's `THESTUDIO_WEBHOOK_SECRET` matches the `WEBHOOK_SECRET` env var provided to the test rig. This is documented in the README and contract.
- Acceptance: POST with valid HMAC-SHA256 returns 200 or 201.
- Files: Implement in `test_webhook.py`.

**Story 2.2: Webhook test for missing signature (401)**
- Estimate: 0.5 hours
- Risk: Low. Negative test, straightforward.
- Acceptance: POST without `X-Hub-Signature-256` returns 401 (handler checks delivery header first, so this test must include `X-GitHub-Delivery`).
- Files: Add to `test_webhook.py`.

**Story 2.3: Webhook test for invalid signature (401/403)**
- Estimate: 0.5 hours
- Risk: Low. Negative test.
- Acceptance: POST with wrong `X-Hub-Signature-256` returns 401.
- Files: Add to `test_webhook.py`.

**Story 2.4: Webhook test for missing delivery header (400)**
- Estimate: 0.5 hours
- Risk: Low. Negative test. Confirmed: handler returns 400 for missing `X-GitHub-Delivery` before checking signature.
- Acceptance: POST without `X-GitHub-Delivery` returns 400.
- Files: Add to `test_webhook.py`.

**Rationale for Day 2 ordering:** Webhook tests are the highest-value gap. The README claims they exist but they do not. Story 2.1 is the hardest (figuring out the registration + signing flow); 2.2-2.4 are quick negative tests that piggyback on the fixtures and helpers created in 2.1. All four should land in a single session.

**Key technical insight for the implementer:** The webhook handler checks headers in this order: (1) `X-GitHub-Delivery` missing -> 400, (2) `X-Hub-Signature-256` missing -> 401, (3) parse payload for repo, (4) look up per-repo secret, (5) validate signature. Tests 2.2 and 2.3 must include `X-GitHub-Delivery` to reach the signature check. Test 2.1 must register a repo first so the handler finds a stored secret. Build a `_sign_payload(payload_bytes, secret)` helper in the test module for reuse across 2.1, 2.3, and 4.1.

---

### Day 3 (Stories 3.1, 3.2) -- Standalone Admin API Tests

**Story 3.1: Repo registration and listing tests**
- Estimate: 2.5 hours
- Risk: Low-Medium. The registration logic exists in the current `TestPollConfig` but is entangled with poll-specific assertions. Need to extract and add standalone assertions for `GET /admin/repos/{id}`.
- Unknowns: Does `GET /admin/repos/{id}` return fields like `owner` and `repo` at the top level? Need to verify from the admin router schema. Worst case, adjust field names.
- Acceptance: `POST /admin/repos` -> 201 or 409; `GET /admin/repos` -> 200 with `repos` list; `GET /admin/repos/{id}` -> 200 with `owner` and `repo` fields.
- Files: Implement in `test_admin_api.py`.

**Story 3.2: Repo profile PATCH test (standalone)**
- Estimate: 1.5 hours
- Risk: Low. Similar logic exists in `TestPollConfig`; this decouples it.
- Acceptance: PATCH updates fields, response includes `updated_fields`, GET confirms update, cleanup restores original value.
- Files: Add to `test_admin_api.py`.

**Rationale for Day 3 ordering:** Admin API tests (Slice 3) depend only on the module split (Day 1). They could theoretically run in parallel with Day 2 webhook work, but sequencing them after webhooks ensures the implementer has the registration + fixture patterns established.

---

### Day 4 (Story 4.1) -- Pipeline Smoke

**Story 4.1: Pipeline smoke test via webhook**
- Estimate: 3 hours
- Risk: Medium-High. This is the riskiest story in the sprint.
- Unknowns discovered during estimation:
  - How do we verify a TaskPacket was created? The admin API does not currently expose a TaskPacket list endpoint. We may need to rely on indirect signals (e.g., the webhook returning 201, or checking admin health counters).
  - If the only verification is the webhook return code (201 = TaskPacket created), then this test is thin but still valuable as a smoke test.
  - The Temporal workflow may fail to start (handler returns 201 with "workflow pending" message), which is still a valid smoke-test pass (TaskPacket was created).
- Assumption: A 201 from the webhook endpoint is sufficient evidence of TaskPacket creation for a smoke test. If we need deeper verification, that is Epic 15 scope.
- Mitigation: If the admin API has no TaskPacket visibility, document this gap and accept the 201 as the observable outcome.
- Acceptance: Register test repo -> send valid signed webhook -> get 201 (or 200 for non-issue events); skip if `WEBHOOK_SECRET` not set.
- Files: Implement in `test_pipeline_smoke.py`.

**Rationale for Day 4 ordering:** Pipeline smoke depends on the webhook signing pattern from Day 2 and the repo registration pattern from Day 3. It is also the riskiest story, so placing it on Day 4 gives the implementer maximum context before tackling the unknowns.

---

### Day 5 (Stories 5.1, 5.2, 5.3) -- Documentation and Cleanup

**Story 5.1: Add contract-to-test mapping to README**
- Estimate: 1.5 hours
- Risk: Low. Documentation only. The mapping table requires auditing every contract endpoint against every test file.
- Acceptance: Every endpoint in contract's "endpoints and behavior" section appears in the mapping table with its test file and test class/function. No endpoint is unmapped.
- Files: Update `thestudio-production-test-rig/README.md`.

**Story 5.2: Update contract with test rig cross-reference**
- Estimate: 1 hour
- Risk: Low. Addendum only, no endpoint changes.
- Acceptance: `docs/production-test-rig-contract.md` has a "Test Coverage" section listing which test modules cover which contract sections.
- Files: Append to `docs/production-test-rig-contract.md`.

**Story 5.3: Delete old monolith file**
- Estimate: 0.5 hours
- Risk: Low. Final validation step.
- Acceptance: `test_production_smoke.py` does not exist; `pytest -v` passes with zero collection errors.
- Files: Delete `thestudio-production-test-rig/tests/test_production_smoke.py`.

**Rationale for Day 5 ordering:** Documentation and cleanup require all tests to exist. This is also the lowest-risk slice, so it sits at the end where it can absorb any schedule pressure from earlier days. If time runs short, 5.2 (contract cross-reference) is the compressible story -- the README mapping (5.1) is more valuable.

---

## Estimation Summary

| Story | Est. (hrs) | Risk | Confidence |
|-------|-----------|------|------------|
| 1.1 Module split | 3.0 | Low | High -- mechanical extraction |
| 1.2 Conftest hardening | 1.5 | Low | High -- additive fixtures |
| 2.1 Valid webhook signature | 2.5 | Medium | Medium -- per-repo secret lookup flow needs care |
| 2.2 Missing signature (401) | 0.5 | Low | High |
| 2.3 Invalid signature (401) | 0.5 | Low | High |
| 2.4 Missing delivery (400) | 0.5 | Low | High |
| 3.1 Repo register + list | 2.5 | Low-Med | High -- existing pattern, decouple from poll |
| 3.2 Profile PATCH | 1.5 | Low | High |
| 4.1 Pipeline smoke | 3.0 | Med-High | Medium -- TaskPacket verification uncertainty |
| 5.1 README mapping | 1.5 | Low | High |
| 5.2 Contract cross-ref | 1.0 | Low | High |
| 5.3 Delete monolith | 0.5 | Low | High |
| **Total** | **18.5** | | |
| **Buffer (5 hrs)** | | | For unknowns in 2.1 and 4.1 |
| **Sprint capacity** | **25** | | 83% of 30 hours |

### Estimation Notes (Risk Discovery)

1. **Story 2.1 is the riskiest "small" story.** The webhook handler validates signatures against per-repo stored secrets, not a global secret. The test must: (a) register a repo via admin API (which stores the deployment's global `THESTUDIO_WEBHOOK_SECRET` as the repo's secret), (b) construct a payload for that repo, (c) sign it with the same secret from the `WEBHOOK_SECRET` env var. If the deployment's global secret and the test rig's env var mismatch, the test fails. This is a configuration risk, not a code risk.

2. **Story 4.1 has the biggest unknown.** We cannot directly query TaskPackets via the admin API. The smoke test relies on the webhook endpoint returning 201 as evidence of TaskPacket creation. This is acceptable for a smoke test but should be documented as a known limitation. If a future admin API exposes TaskPacket listing, this test should be upgraded.

3. **Stories 2.2-2.4 are trivially small** (0.5 hrs each) because they are negative tests that reuse the payload and signing helpers from 2.1. If 2.1 takes longer than expected, these shrink further because the helpers already exist.

4. **The total estimate (18.5 hrs) leaves 6.5 hrs of buffer** against the 25-hour allocation. This is generous (35% buffer) but appropriate given the webhook signing unknowns and the pipeline smoke uncertainty. If buffer is not consumed, use slack time to improve test fixtures or add edge-case tests.

### Compressible Stories (If Time Runs Short)

1. **Story 5.2** (contract cross-reference, 1 hr) -- can be deferred to a follow-up without affecting the sprint goal's test criteria.
2. **Story 4.1** (pipeline smoke, 3 hrs) -- can be reduced to a minimal "webhook returns 201" check without the full register-send-verify flow. Still valuable as a thin smoke test.

---

## Capacity Allocation

| Category | Hours | % |
|----------|-------|---|
| Estimated story work | 18.5 | 62% |
| Buffer for unknowns | 5.0 | 17% |
| Slack (testing, review, rework) | 6.5 | 21% |
| **Total available** | **30** | **100%** |

Never 100% allocated. The 17% explicit buffer targets the two medium-to-high risk stories (2.1 and 4.1). The 21% slack handles code review, rework from Meridian review, and any environmental issues (e.g., deployment not reachable during testing).

---

## Day-by-Day Schedule

| Day | Stories | Hours (est.) | Milestone |
|-----|---------|-------------|-----------|
| Mon (Day 1) | 1.1, 1.2 | 4.5 | `pytest --collect-only` discovers all tests in new modules |
| Tue (Day 2) | 2.1, 2.2, 2.3, 2.4 | 4.0 | All 4 webhook tests in `test_webhook.py`, pass against deployment |
| Wed (Day 3) | 3.1, 3.2 | 4.0 | Admin API tests decoupled from poll, pass standalone |
| Thu (Day 4) | 4.1 | 3.0 | Pipeline smoke proves webhook -> TaskPacket flow |
| Fri (Day 5) | 5.1, 5.2, 5.3 | 3.0 | README mapped, contract updated, monolith deleted, full green run |

---

## Critical Path

```
1.1 (split) -> 1.2 (fixtures) -> 2.1 (valid webhook) -> 4.1 (pipeline smoke)
                                      |
                                      +-> 2.2, 2.3, 2.4 (negative webhook tests)

1.1 (split) -> 3.1 (admin register) -> 3.2 (admin PATCH)

All stories -> 5.1 (README) -> 5.2 (contract) -> 5.3 (delete monolith)
```

Longest path: 1.1 -> 1.2 -> 2.1 -> 4.1 -> 5.1 -> 5.2 -> 5.3 = 13 hours on the critical path.

---

## Meridian Review Checklist

This plan is DRAFT. Before commit, Meridian must verify:

- [ ] Sprint goal is testable (objective, test, constraint all present and specific)
- [ ] Every story has acceptance criteria that can be verified by running code
- [ ] Dependencies are sequenced correctly (no story starts before its dependency completes)
- [ ] Risk in stories 2.1 and 4.1 is adequately mitigated
- [ ] Capacity allocation includes buffer (never 100%)
- [ ] Compressible stories identified for schedule pressure
- [ ] No scope creep beyond `thestudio-production-test-rig/` and `docs/production-test-rig-contract.md`
- [ ] Constraint about no application code changes is enforceable

---

*This plan must pass Meridian review before execution begins. See `thestudioarc/personas/meridian-vp-success.md` for the review protocol.*
