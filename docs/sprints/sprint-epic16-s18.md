# Sprint 18 Plan: Epic 16 — Issue Readiness Gate (Stories 16.5-16.8)

**Planned by:** Helm
**Date:** 2026-03-13
**Status:** COMPLETE -- All 4 stories delivered, 1,721 tests passing
**Epic:** `docs/epics/epic-16-issue-readiness-gate.md`
**Sprint Duration:** 2 weeks (10 working days, 2026-03-31 to 2026-04-11)
**Capacity:** Single developer, 80% commitment = 8 effective days, 2 days buffer

---

## Sprint Goal (Testable Format)

**Objective:** Complete the Issue Readiness Gate epic by delivering re-evaluation on issue update, outcome signal feedback for gate calibration, admin API and metrics endpoints, and comprehensive integration tests. By sprint end, a submitter who responds to a clarification request gets their issue automatically re-evaluated, operators can view gate metrics and trigger calibration via Admin API, and all 6 integration test scenarios pass.

**Test:** After all stories are complete:
1. Submit a low-quality issue to a Suggest-tier repo with `readiness_gate_enabled=True` -- gate holds and posts clarification comment.
2. Edit the issue body to add acceptance criteria and scope -- webhook triggers re-evaluation, gate passes, pipeline resumes from Intent.
3. Submit a low-quality issue 3 times without improvement -- gate escalates to human review on 3rd re-evaluation.
4. `GET /admin/readiness/metrics?repo_id={id}` returns pass/hold/escalate counts.
5. `POST /admin/readiness/calibrate` triggers calibration (returns no-op if < 20 samples).
6. `pytest tests/integration/test_readiness_gate.py` passes all 6 scenarios.
7. All existing tests pass unchanged: `pytest` exits 0 with no regressions.
8. `ruff check src/readiness/ src/ingress/webhook_handler.py src/outcome/ src/admin/readiness_routes.py` exits 0.
9. `mypy src/readiness/ src/admin/readiness_routes.py` exits 0.

**Constraint:** 8 effective working days. Story 16.9 (issue templates and documentation) is explicitly deferred -- it is pure documentation and does not affect gate functionality. No changes to the scoring engine logic (Stories 16.1-16.2 are stable). All new code behind existing feature flag (`readiness_gate_enabled`) that defaults to off.

---

## What's In / What's Out

**In Sprint 18 (4 stories, 7 estimated days):**
- 16.5: Re-evaluation on issue update (3 days)
- 16.6: Outcome signal feedback calibrator (1 day)
- 16.7: Admin API and metrics (2 days)
- 16.8: Integration tests (1 day)

**Deferred (out of Sprint 18):**
- 16.9: Issue templates and documentation (1 day) -- pure docs, no gate functionality impact. Can ship at any time without coordination.

**Rationale for cut line:** Stories 16.5-16.8 complete the gate's functional loop: re-evaluation closes the submitter feedback cycle, calibration enables learning, admin API provides operator visibility, and integration tests provide confidence. Story 16.9 is valuable but independent -- templates and docs can ship without any code dependency on the gate being complete.

---

## Ordered Backlog

### Days 1-3 (Story 16.5) -- Re-evaluation on issue update (highest risk, highest value)

#### Story 16.5: Re-Evaluation on Issue Update (Est: 3 days)

**Sequence rationale:** This is the highest-risk and highest-value story in the sprint. It modifies the webhook handler to accept new event types (`issue_comment.created`, `issues.edited`), adds payload parsing for a different structure, and wires the `readiness_cleared` Temporal signal. Every other story in this sprint can proceed without it, but the gate is incomplete without re-evaluation -- submitters who respond to clarification comments get no feedback. Build and stabilize this first.

**Work:**
- Modify `src/ingress/webhook_handler.py` (line 74) to accept `issue_comment` events alongside `issues` events
- Add payload parsing for `issue_comment.created` events (issue data at `payload.issue`, not top level)
- Add re-evaluation trigger logic: when `issue_comment.created` or `issues.edited` arrives for a TaskPacket in `clarification_requested` status:
  - Look up TaskPacket by `(repo, issue_number)`
  - Send `readiness_cleared` Temporal signal to the waiting workflow
  - Debounce: if multiple updates arrive within 60 seconds, process only the last
- Modify `src/workflow/pipeline.py` to handle `readiness_cleared` signal:
  - Re-run Context -> Readiness Gate with updated issue content
  - If gate passes: update TaskPacket status, resume pipeline from Intent
  - If gate fails: update existing clarification comment (not post a new one)
  - If `readiness_evaluation_count >= 3`: escalate to human review
- Add `readiness_evaluation_count: int = 0` and `readiness_hold_comment_id: str | None = None` fields to TaskPacket model
- HMAC signature validation for `issue_comment` payloads (same secret, verify compatibility)

**Knowns:**
- Webhook handler currently filters on `x_github_event == "issues"` at line 74 -- verified
- `readiness_activity` already exists in `src/workflow/activities.py` -- verified
- Pipeline already has `WorkflowStep.READINESS` enum value and conditional execution at line 265 -- verified
- TaskPacket status `CLARIFICATION_REQUESTED` already exists -- verified from Sprint 17 delivery

**Unknowns:**
- `issue_comment` payload structure differs from `issues` payload -- the issue data nests under `payload.issue` instead of top-level. Need to handle both shapes cleanly. Decision: create a `normalize_webhook_payload()` helper that extracts issue data from either event type.
- Debounce implementation: in-memory with TTL cache (e.g., dict with timestamps) or defer to Temporal signal deduplication. Decision: use Temporal's built-in signal handling -- if multiple signals arrive while the workflow is processing, only the latest state matters when re-evaluation runs.
- Whether updating an existing clarification comment requires the GitHub comment ID. Decision: store `readiness_hold_comment_id` on TaskPacket when the first clarification comment is posted (Story 16.4 already posts the comment; this story adds ID capture).

**Confidence:** Medium (65%). This is the riskiest story. Three independent changes converge: webhook handler expansion, Temporal signal wiring, and GitHub comment updates. The 3-day estimate includes a full day of integration testing and edge case handling.

**Risk mitigation:**
1. Day 1: Webhook handler changes only -- add event type filter and payload parsing, verify with unit tests. Run `pytest` before touching pipeline.
2. Day 2: Pipeline signal handling -- wire `readiness_cleared` signal, implement re-evaluation loop. Run `pytest` after each change.
3. Day 3: GitHub comment update logic, debounce, edge cases (3-strike escalation). Full regression run.

**Files to modify:**
- `src/ingress/webhook_handler.py`
- `src/workflow/pipeline.py`
- `src/models/taskpacket.py`
- `src/readiness/clarification.py` (add comment update support)

**Files to create:**
- `tests/unit/test_readiness/test_reevaluation.py`

---

### Day 4 (Story 16.6) -- Outcome signal feedback

#### Story 16.6: Outcome Signal Feedback -- `intent_gap` to Readiness Calibration (Est: 1 day)

**Sequence rationale:** Independent of 16.5 at the code level. Depends only on Sprint 17 deliverables (readiness scorer and models). The calibrator is a standalone module that records misses and adjusts weights. Building it on Day 4 gives a full day of focus after the high-risk Story 16.5 is stabilized.

**Work:**
- Create `src/readiness/calibrator.py` with:
  - `ReadinessCalibrator` class
  - `record_readiness_miss(taskpacket_id, readiness_score, defect_category)` -- records when a gate-passed issue later receives an `intent_gap` defect
  - `calibrate(repo_id: str | None = None)` -- analyzes miss data, adjusts dimension weights by up to +/-10% per cycle, requires minimum 20 samples
  - All adjustments logged with before/after weights, sample size, rationale
- Modify `src/outcome/ingestor.py` to call `record_readiness_miss()` when `intent_gap` is detected on a TaskPacket that has a stored readiness score
- Calibration is periodic (callable via Admin API in Story 16.7) or on-demand

**Knowns:**
- `INTENT_GAP` exists as `DefectCategory` in `src/outcome/models.py:36` -- verified
- Outcome ingestor processes QA defect signals at `src/outcome/ingestor.py:169` -- verified
- Readiness models and scorer exist from Sprint 17 -- verified

**Unknowns:**
- Storage for miss records: use existing PostgreSQL with a new `readiness_miss` table or append to TaskPacket metadata. Decision: lightweight -- store in TaskPacket metadata JSON field (readiness_score is already computed; add `readiness_miss: bool` flag). Calibrator queries TaskPackets with `readiness_miss=True` and stored readiness scores.
- Per-repo vs global calibration: the epic specifies both. Decision: implement per-repo first (repos have different issue quality norms), with global as aggregation across repos.

**Confidence:** High (85%). Self-contained module with clear math (weighted average adjustment with caps). No pipeline modifications.

**Files to create:**
- `src/readiness/calibrator.py`
- `tests/unit/test_readiness/test_calibrator.py`

**Files to modify:**
- `src/outcome/ingestor.py`

---

### Days 5-6 (Story 16.7) -- Admin API and metrics

#### Story 16.7: Admin API -- Readiness Metrics and Configuration (Est: 2 days)

**Sequence rationale:** Depends on 16.6 (calibrator) for the calibration endpoints. The metrics endpoints depend on Sprint 17 models and data. Building this after the calibrator means all four admin endpoints can be delivered together.

**Work:**
- Create `src/admin/readiness_routes.py` with 4 endpoints:
  - `GET /admin/readiness/metrics?repo_id=&period=7d` -- pass/hold/escalate counts, average scores, top missing dimensions
  - `GET /admin/readiness/calibration?repo_id=` -- current dimension weights, recent adjustments, miss rate
  - `PUT /admin/readiness/thresholds?repo_id=` -- update per-repo threshold overrides
  - `POST /admin/readiness/calibrate?repo_id=` -- trigger on-demand calibration (calls `ReadinessCalibrator.calibrate()`)
- Register routes in `src/admin/router.py`
- All endpoints require ADMIN role (reuse existing RBAC from `src/admin/rbac.py`)
- Note: Admin UI tab (charts, tables) is descoped from this story. API-only. The Admin UI already has patterns for rendering data from API endpoints; adding a tab is incremental work that can happen independently.

**Knowns:**
- Admin router pattern: `src/admin/router.py` registers sub-routers -- verified
- RBAC middleware exists at `src/admin/rbac.py` -- verified
- Existing admin endpoints follow FastAPI router pattern with Pydantic response models -- standard pattern

**Unknowns:**
- Metrics query performance: if TaskPacket volume is high, aggregating readiness scores over a period could be slow. Decision: use SQL aggregation (COUNT, AVG, GROUP BY) with index on `created_at`. If performance is an issue, add a materialized view later.
- Whether to include the Admin UI tab in this sprint. Decision: descope UI tab. API endpoints are the deliverable. UI can follow in a future sprint or as part of an Admin UI enhancement epic.

**Confidence:** High (85%). Standard FastAPI endpoint pattern with known RBAC integration.

**Files to create:**
- `src/admin/readiness_routes.py`
- `tests/unit/test_admin/test_readiness_routes.py`

**Files to modify:**
- `src/admin/router.py` -- register readiness routes

---

### Day 7 (Story 16.8) -- Integration tests

#### Story 16.8: Integration Tests and Pipeline Compatibility (Est: 1 day)

**Sequence rationale:** Last in sequence because it validates all prior stories working together. All functional code must be stable before writing integration tests that exercise the full path.

**Work:**
- Create `tests/integration/test_readiness_gate.py` with 6 scenarios:
  1. **Happy path:** High-readiness issue passes gate, pipeline continues to Intent
  2. **Hold path:** Low-readiness issue at Suggest tier held, clarification comment generated, re-evaluation with improved issue passes, pipeline completes
  3. **Escalation path:** High-risk + low-readiness at Execute tier escalates to human review
  4. **Observe tier:** Low-readiness issue at Observe tier records score but does not block
  5. **Feature flag off:** Pipeline with `readiness_gate_enabled=False` behaves exactly as before
  6. **Re-evaluation cap:** Issue fails readiness 3 times, escalated to human review
- Add mock readiness activity to `tests/integration/mock_providers.py`
- Verify all existing Epic 15 integration tests pass unchanged

**Knowns:**
- Integration test patterns established in `tests/integration/` from Epic 15 -- verified
- Mock providers exist at `tests/integration/mock_providers.py` -- verified
- Tests run without Docker, API keys, or external services -- convention from Epic 15

**Unknowns:**
- Whether re-evaluation loop (Scenario 2 and 6) can be simulated in integration tests without a real Temporal server. Decision: use Temporal's test server (`temporalio.testing.WorkflowEnvironment`) if available, or mock the signal flow. Epic 15 established the mock pattern.

**Confidence:** High (85%). Clear test scenarios, established patterns.

**Files to create:**
- `tests/integration/test_readiness_gate.py`

**Files to modify:**
- `tests/integration/mock_providers.py` -- add mock readiness activity
- `tests/integration/conftest.py` -- add readiness fixtures if needed

---

### Days 8-10 -- Buffer and hardening

**Buffer allocation (2 days + 1 day sprint overhead):**
- Day 8: Full regression run. Fix any issues from Story 16.5 signal handling or Story 16.8 integration tests.
- Day 9: Edge case coverage, code cleanup, ruff/mypy pass on all modified files.
- Day 10: Sprint overhead (planning, review, ad-hoc issues).

**What the buffer is for:**
1. Story 16.5 overrun (most likely -- webhook handler expansion and Temporal signal wiring have the highest uncertainty)
2. Integration test failures from re-evaluation loop complexity
3. Outcome ingestor integration with calibrator (cross-module wiring)
4. Edge cases in debounce logic or 3-strike escalation

---

## Dependencies

### Internal (between stories)

```
Sprint 17 (16.1-16.4) -- all stable and delivered
  |
  +---> 16.5 (re-evaluation) -- independent, highest risk
  |
  +---> 16.6 (calibrator) -- independent
  |         |
  |         +---> 16.7 (admin API) -- depends on 16.6 for calibration endpoint
  |
  +---> 16.8 (integration tests) -- depends on 16.5, 16.6, 16.7 all being stable
```

- **16.5 and 16.6 are independent** and could theoretically be developed in parallel
- **16.7 depends on 16.6** for the calibration trigger endpoint
- **16.8 depends on all prior stories** being functional

### External (blocking items)

| Dependency | Status | Verification |
|---|---|---|
| Readiness scorer (`src/readiness/scorer.py`) | DELIVERED -- Sprint 17 | `score_readiness()` pure function, 92 unit tests passing |
| Readiness models (`src/readiness/models.py`) | DELIVERED -- Sprint 17 | `ReadinessScore`, `GateDecision`, `ReadinessOutput` all exist |
| Clarification formatter (`src/readiness/clarification.py`) | DELIVERED -- Sprint 17 | `format_clarification_comment()` produces marker-tagged comment |
| Pipeline readiness activity (`src/workflow/activities.py`) | DELIVERED -- Sprint 17 | `readiness_activity` registered and callable |
| Pipeline workflow integration (`src/workflow/pipeline.py`) | DELIVERED -- Sprint 17 | `WorkflowStep.READINESS` at line 80, conditional execution at line 265 |
| TaskPacket statuses (`CLARIFICATION_REQUESTED`, `HUMAN_REVIEW_REQUIRED`) | DELIVERED -- Sprint 17 | Both statuses in `TaskPacketStatus` enum with valid transitions |
| Webhook handler (`src/ingress/webhook_handler.py`) | VERIFIED -- filters on `x_github_event` at line 74 | Accepts `issues` event type only; expansion needed for `issue_comment` |
| Outcome ingestor (`src/outcome/ingestor.py`) | VERIFIED -- `intent_gap` handling at line 169 | Already processes QA defect signals; hook point for `record_readiness_miss()` |
| Admin router (`src/admin/router.py`) | VERIFIED -- sub-router registration pattern | Standard FastAPI pattern for adding new route modules |

**Verdict:** All external dependencies are verified and resolved. No blockers.

---

## Estimation Summary

| Story | Estimate | Confidence | Primary Risk |
|---|---|---|---|
| 16.5: Re-evaluation on issue update | 3 days | Medium (65%) | Webhook handler expansion + Temporal signal + comment update = 3 independent changes |
| 16.6: Outcome signal feedback | 1 day | High (85%) | Self-contained calibrator module |
| 16.7: Admin API and metrics | 2 days | High (85%) | Standard FastAPI endpoint pattern |
| 16.8: Integration tests | 1 day | High (85%) | Clear scenarios, established patterns |
| **Total** | **7 days** | | |
| Buffer | 2 days | | Story 16.5 overrun most likely consumer |
| Sprint overhead | 1 day | | Planning, review, ad-hoc |
| **Sprint total** | **10 days / 10 available** | | 70% story work, 20% buffer, 10% overhead |

---

## Capacity and Buffer

- **Available:** 10 working days (2 weeks)
- **Committed:** 7 days of story work (70%)
- **Buffer:** 2 days (20%) -- explicitly reserved, not allocated to stories
- **Overhead:** 1 day (10%) -- sprint planning, code review, ad-hoc
- **Effective allocation:** 70% to stories

**Buffer is explicitly for:**
1. Story 16.5 overrun (highest probability -- 35% chance of needing an extra day)
2. Integration test failures from re-evaluation loop
3. Outcome ingestor cross-module wiring issues
4. Debounce or escalation edge cases

**Compressible stories (what gets cut if time runs short):**
1. **16.7 Admin API** can be reduced to 2 endpoints (metrics + calibrate) instead of 4. Threshold override and calibration detail endpoints can move to a follow-up.
2. **16.8 Integration tests** can be reduced to 3 scenarios (happy path, hold+re-eval, feature flag off) instead of 6. Escalation, Observe tier, and 3-strike scenarios can be added later.

---

## Retro Actions

**Prior sprint:** Sprint 17 / Epic 16 (Stories 16.1-16.4) -- COMPLETE, all 4 stories delivered, 1,689 tests passing.

**Lessons applied to this plan:**

1. **Sprint 17 pipeline integration (Story 16.3) was the riskiest story and used 70% confidence.** It completed within estimate but consumed buffer time for TaskPacket status transition edge cases. Action: Story 16.5 (which also modifies the pipeline) is given 3 days (up from the epic's suggestion of 2 days for webhook changes) and 65% confidence, with explicit daily checkpoints.

2. **Sprint 17 Meridian Round 1 found that the Temporal wait-state mechanism was ambiguous.** Action: This plan specifies the exact signal name (`readiness_cleared`), the trigger conditions (issue edit or comment on held TaskPacket), and the debounce strategy (Temporal signal deduplication, not in-memory cache).

3. **Sprint 17 delivered the clarification comment (Story 16.4) at 90% confidence and within estimate.** The comment formatting work is stable and the `format_clarification_comment()` function is well-tested. Action: Story 16.5 builds on this confidence by extending comment update support rather than rewriting.

---

## Key Decisions Made in This Plan

1. **Descoped Admin UI tab.** The epic specifies charts and tables in Admin UI. This plan delivers API endpoints only. Rationale: API endpoints are the contract; UI rendering is incremental and can be done independently without blocking the gate's operational visibility.

2. **Descoped Story 16.9 (issue templates and documentation).** Pure documentation work with no code dependency. Can ship at any time. Keeps the sprint within capacity.

3. **3-day estimate for Story 16.5.** The epic suggests 2 days for "re-evaluation on issue update" but the story detail reveals 3 independent changes (webhook handler, pipeline signal, comment update) plus debounce and escalation logic. 3 days is more realistic for a 65% confidence story.

4. **Calibrator stores miss data in TaskPacket metadata.** Rather than creating a new `readiness_miss` table, misses are flagged on the TaskPacket itself. The calibrator queries TaskPackets with `readiness_miss=True`. This avoids a migration for a lightweight feature.

5. **Admin UI tab deferred, not abandoned.** The readiness metrics API is designed to support a future UI tab. Response schemas match what a chart component would consume.

---

## Definition of Done for Sprint 18

- [x] Webhook handler accepts `issue_comment.created` and `issues.edited` events
- [x] `issue_comment` payload parsing correctly extracts issue data from nested structure
- [x] HMAC validation works for `issue_comment` event payloads
- [x] Re-evaluation triggers for TaskPackets in `clarification_requested` status
- [x] Re-evaluation that passes resumes pipeline from Intent
- [x] Re-evaluation that fails updates existing comment (no duplicate)
- [x] 3rd failed re-evaluation escalates to human review
- [x] `readiness_evaluation_count` and `readiness_hold_comment_id` fields exist on TaskPacket
- [x] `ReadinessCalibrator` exists with `record_readiness_miss()` and `calibrate()` methods
- [x] Weight adjustments capped at +/-10% per cycle with minimum 20 sample requirement
- [x] Outcome ingestor calls `record_readiness_miss()` on `intent_gap` detection
- [x] 4 Admin API endpoints exist: metrics, calibration, thresholds, calibrate trigger
- [x] All admin endpoints require ADMIN role
- [x] 6 integration test scenarios pass in `tests/integration/test_readiness_gate.py`
- [x] All existing tests pass unchanged (no regressions)
- [x] `ruff check` and `mypy` pass on all new and modified files
- [x] Code committed to master

---

## Meridian Review Status

### Round 1: PASS -- 2026-03-13

**Date:** 2026-03-13
**Verdict:** 7/7 PASS. COMMITTABLE.

| # | Question | Verdict |
|---|----------|---------|
| 1 | Testable sprint goal | PASS -- 9 specific verification tests with concrete scenarios |
| 2 | Single order of work | PASS -- strict sequence with rationale; 16.5 first (highest risk), dependency graph explicit |
| 3 | Dependencies confirmed | PASS -- 9 external deps verified with line numbers, function names, enum values |
| 4 | Estimation reasoning | PASS -- confidence %, knowns, unknowns, daily checkpoints for highest-risk story |
| 5 | Retro actions | PASS -- 3 lessons from Sprint 17 applied with specific actions |
| 6 | Capacity and buffer | PASS -- 70/20/10 split, named buffer consumers, compressible stories identified |
| 7 | Async-readable | PASS -- 17-item DoD, 5 decisions documented, ASCII dependency graph |

**Advisory:** Story 16.5 at 65% confidence is the single point of risk. If webhook handler expansion reveals unexpected payload parsing complexity, the compressible stories (16.7 reduced to 2 endpoints, 16.8 reduced to 3 scenarios) provide adequate relief.

**Status: COMMITTED. Ready to execute on 2026-03-31.**
