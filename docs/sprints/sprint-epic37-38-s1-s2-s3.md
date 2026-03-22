# Sprint Plan: Epic 37 Test Debt + Epic 38 MVP (Slices 1+2)

**Planned by:** Helm
**Date:** 2026-03-22
**Status:** APPROVED -- Meridian Review PASS (2026-03-22)
**Epics:** Epic 37 (Test Debt Paydown) + Epic 38 Phase 4 (GitHub Deep Integration, Slices 1+2 MVP)
**Total Duration:** 3 sprints across 3 weeks
**Capacity:** Single developer, 30 hours per week (5 days x 6 productive hours)

---

## Work Stream Architecture

Two work streams with a strict prerequisite gate:

```
Sprint 1 (Week 1): Epic 37 Test Debt    [CRITICAL PREREQUISITE]
    |
    v  -- Gate: pytest green, ruff clean, all E37 modules covered --
    |
Sprint 2 (Week 2): Epic 38 Slice 1 (Issue Import) + Slice 2 Backend
    |
    v
Sprint 3 (Week 3): Epic 38 Slice 2 (PR Evidence Frontend + Integration Tests)
```

**Rationale for this sequence:**
1. Epic 37 shipped 12 modules with zero test coverage. Meridian flagged this as a critical blocker. Building new features on untested infrastructure creates compounding risk -- a bug in the trust engine or steering API discovered during Epic 38 would require context-switching back to Epic 37 code while also debugging Epic 38 code. Pay the debt first.
2. Epic 38 Slice 1 (Issue Import) is the simpler of the two MVP slices and establishes the GitHub API integration patterns that Slice 2 reuses.
3. Epic 38 Slice 2 backend stories must precede frontend stories because the Evidence Explorer frontend consumes the `EvidencePayload` JSON contract defined in 38.5-38.7.

---

## Sprint 1: Epic 37 Test Debt Paydown

**Sprint Duration:** 1 week (2026-03-23 to 2026-03-27)
**Capacity:** 30 hours total, 75% allocation = 22.5 hours, 7.5 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Write comprehensive unit tests for all 12 Epic 37 modules that shipped without coverage. Every public function, every API endpoint, every Pydantic model, and every operator path in the trust engine, budget checker, steering API, and notification system must have at least one passing test.

**Test:** After all stories are complete:

1. `pytest tests/dashboard/test_steering.py` passes -- all 5 steering endpoints tested (pause/resume/abort/redirect/retry) with happy path, 404, 409, and 400 status codes validated.
2. `pytest tests/dashboard/test_trust_engine.py` passes -- all 6 condition operators tested (equals, not_equals, less_than, greater_than, contains, matches_glob), first-match-wins verified, safety bounds override verified, default tier fallback verified.
3. `pytest tests/dashboard/test_trust_router.py` passes -- CRUD endpoints for rules (create/read/update/delete), safety bounds (get/update), and default tier (get/set) all tested including 404 on missing resources.
4. `pytest tests/dashboard/test_budget_checker.py` passes -- threshold comparison logic tested, pause-on-exceed action tested, model downgrade trigger tested with mocked dependencies.
5. `pytest tests/dashboard/test_budget_router.py` passes -- all 6 budget endpoints tested (summary, history, by-stage, by-model, config get, config put).
6. `pytest tests/dashboard/test_notification_generator.py` passes -- all 4 NATS event-to-notification builders tested (gate_fail, cost_update, steering_action, trust_tier_assigned), null/missing field handling verified.
7. `pytest tests/dashboard/test_notification_router.py` passes -- list (with filters), mark-read, mark-all-read endpoints tested including 404 on missing notification.
8. `pytest tests/dashboard/test_models_steering_audit.py` passes -- SteeringAction enum, SteeringAuditLogCreate/Read validation, CRUD functions tested.
9. `pytest tests/dashboard/test_models_trust_config.py` passes -- AssignedTier and ConditionOperator enums, all Pydantic schemas (Create/Update/Read for rules, SafeBounds, DefaultTier), CRUD functions tested.
10. `pytest tests/dashboard/test_models_budget_config.py` passes -- BudgetConfigRow singleton, BudgetConfigRead/Update schemas, CRUD functions tested.
11. `pytest tests/dashboard/test_models_notification.py` passes -- NotificationType enum, NotificationCreate/Read/ListResponse schemas, CRUD functions (create, list, mark_read, mark_all_read) tested.
12. `pytest tests/workflow/test_steering_signals.py` passes -- Temporal signal handlers tested with workflow test environment (pause_task, resume_task, abort_task, redirect_task, retry_stage).
13. All existing tests pass (`pytest` green, `ruff check .` clean).

**Constraint:** 5 working days. No new features, no refactoring of production code. Tests only. All test files created under `tests/dashboard/` (new directory) and `tests/workflow/`. Mocking strategy: mock Temporal client and NATS connections; use real Pydantic models; use SQLAlchemy async session with in-memory SQLite or test fixtures consistent with existing test patterns.

---

### What's In / What's Out

**In this sprint (12 test stories, ~22 estimated hours):**

| # | Story ID | Module Under Test | Type | Est. | Ralph Loops |
|---|----------|-------------------|------|------|-------------|
| 1 | T37.1 | Pydantic models (all 4 model files) | Unit test | 2h | 1 |
| 2 | T37.2 | Trust engine (`trust_engine.py`) | Unit test | 3h | 1 |
| 3 | T37.3 | Trust router (`trust_router.py`) | Unit test | 2h | 1 |
| 4 | T37.4 | Steering API (`steering.py`) | Unit test | 3h | 1 |
| 5 | T37.5 | Budget checker (`budget_checker.py`) | Unit test | 2.5h | 1 |
| 6 | T37.6 | Budget router (`budget_router.py`) | Unit test | 2h | 1 |
| 7 | T37.7 | Notification generator (`notification_generator.py`) | Unit test | 2h | 1 |
| 8 | T37.8 | Notification router (`notification_router.py`) | Unit test | 1.5h | 1 |
| 9 | T37.9 | Temporal signal handlers (`pipeline.py`) | Unit test | 3h | 1-2 |
| 10 | T37.10 | Test infra + conftest setup | Setup | 1h | 1 |
| | | **Total** | | **22h** | |

**Out of scope:**
- Integration tests (those belong to Epic 38 stories)
- Refactoring or bug-fixing production code (if bugs are found, file them; do not fix inline)
- Frontend test coverage (vitest -- frontend components from E37 are thin wrappers)
- Performance or load testing

---

### Dependency Review (30-Minute Pre-Planning)

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Existing test infrastructure (`conftest.py`, fixtures) | Available | Cannot create DB sessions for model tests | Note: root `tests/conftest.py` contains test ordering only. Async session patterns exist in per-test-file conftest files (e.g., `tests/unit/`, `tests/integration/`). T37.10 creates `tests/dashboard/conftest.py` with new async session fixture. |
| `src/dashboard/` modules (all 12 files) | COMPLETE (Epic 37) | Nothing to test | Confirmed: all files exist per git log |
| `src/workflow/pipeline.py` signal handlers | COMPLETE (Epic 37) | Cannot test steering signals | Confirmed: 5 signal handlers exist |

#### Internal Dependencies (Story-to-Story)

```
T37.10 (conftest/setup) --> T37.1 (models) --> T37.2 (trust engine)
                                            \-> T37.3 (trust router)
                                            \-> T37.4 (steering API)
                                            \-> T37.5 (budget checker)
                                            \-> T37.6 (budget router)
                                            \-> T37.7 (notif generator)
                                            \-> T37.8 (notif router)
                                            \-> T37.9 (temporal signals)
```

- **T37.10 has no dependencies** -- creates `tests/dashboard/__init__.py` and `tests/dashboard/conftest.py` with shared fixtures (mock DB session, mock Temporal client, mock NATS, sample TaskPacketRow factory).
- **T37.1 depends on T37.10** -- model tests need the conftest fixtures. Foundation for all router/engine tests since they import model schemas.
- **T37.2-T37.9 depend on T37.10 and T37.1** -- all module tests import Pydantic schemas from the model files and use conftest fixtures.
- **T37.2-T37.9 are independent of each other** -- no inter-module test dependencies. Can be done in any order after T37.1.

**Critical path:** T37.10 --> T37.1 --> T37.9 (Temporal signals are the highest-risk test to write due to Temporal test environment setup)

---

### Ordered Work Items

#### Item 1: Story T37.10 -- Test Infrastructure Setup

**Estimate:** 1 hour (S size, 1 Ralph loop)
**Rationale for sequence:** Foundation. Every other Sprint 1 story depends on the test directory structure and shared fixtures.

**Key tasks:**
- Create `tests/dashboard/__init__.py`
- Create `tests/dashboard/conftest.py` with:
  - Async DB session fixture (SQLite in-memory, matching existing test patterns)
  - `mock_temporal_client` fixture (AsyncMock with `get_workflow_handle` returning a mock handle with `.signal()`)
  - `sample_taskpacket_row` factory fixture (creates a `TaskPacketRow` with sensible defaults)
  - `mock_nats_msg` fixture (mock NATS message with `.data`, `.ack()`, `.subject`)
- Verify fixture imports work: `pytest tests/dashboard/ --co` (collect-only)

**Estimation reasoning:** Straightforward setup. Patterns exist in `tests/conftest.py` already. 1 hour is generous but accounts for verifying the async session fixture works with the dashboard models' table definitions.

**Done when:** `pytest tests/dashboard/ --co` succeeds (collects 0 tests, no import errors).

---

#### Item 2: Story T37.1 -- Pydantic Model Validation Tests

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** After infrastructure. Models are the foundation that all other modules import.

**Test file:** `tests/dashboard/test_models_steering_audit.py`, `tests/dashboard/test_models_trust_config.py`, `tests/dashboard/test_models_budget_config.py`, `tests/dashboard/test_models_notification.py`

**Key tests per model file:**

**steering_audit.py:**
- `SteeringAction` enum has all 7 values (pause, resume, abort, redirect, retry, trust_tier_assigned, trust_tier_overridden)
- `SteeringAuditLogCreate` validates required fields (task_id, action, timestamp)
- `SteeringAuditLogCreate` accepts optional fields (from_stage, to_stage, reason)
- `SteeringAuditLogRead` populates from ORM row via `from_attributes`

**trust_config.py:**
- `AssignedTier` enum has 3 values (observe, suggest, execute)
- `ConditionOperator` enum has 6 values
- `RuleCondition` validates field, op, value
- `TrustTierRuleCreate` accepts conditions list, validates priority range (1-9999)
- `TrustTierRuleUpdate` all fields optional
- `SafeBoundsUpdate` validates ge constraints
- `DefaultTierUpdate` validates tier is valid enum

**budget_config.py:**
- `BudgetConfigRead` populates from ORM row
- `BudgetConfigUpdate` validates ge=0 constraints on thresholds
- `BudgetConfigUpdate` validates downgrade_threshold_percent in 0-100 range

**notification.py:**
- `NotificationType` enum has 4 values
- `NotificationCreate` validates title max_length=500
- `NotificationListResponse` structure (items, total, unread_count, limit, offset)

**Estimation reasoning:** 4 model files, each with 3-5 test cases. Pure Pydantic validation -- no DB, no async. Fast to write, fast to run.

**Done when:** All 4 test files pass. `ruff check tests/dashboard/` clean.

---

#### Item 3: Story T37.2 -- Trust Engine Tests

**Estimate:** 3 hours (M size, 1 Ralph loop)
**Rationale for sequence:** Trust engine is the most complex pure-logic module. Testing it thoroughly reduces risk for the trust router tests and for Epic 38 which depends on trust tier evaluation.

**Test file:** `tests/dashboard/test_trust_engine.py`

**Key tests:**
- `_apply_operator` for each of 6 operators:
  - `EQUALS`: string match, int match, mismatch returns False
  - `NOT_EQUALS`: inverse of equals
  - `LESS_THAN`: numeric comparison, string coercion to float
  - `GREATER_THAN`: numeric comparison
  - `CONTAINS`: substring match, list membership
  - `MATCHES_GLOB`: fnmatch pattern matching (e.g., `"src/**"` matches `"src/main.py"`)
- `_resolve_field`: top-level attribute, dot-notation nested dict, missing key raises KeyError
- `_rule_matches`: all conditions must pass (AND logic), empty conditions list = vacuously true
- `evaluate_trust_tier` integration:
  - First matching rule wins (priority ordering)
  - No matching rule falls back to `default_tier`
  - Safety bounds: loopback_count > max_loopbacks caps tier to SUGGEST
  - Safety bounds: diff_lines > max_auto_merge_lines caps tier to SUGGEST
  - Safety bounds: repo matches mandatory_review_pattern caps tier to SUGGEST
  - `EvaluationResult` records `safety_capped=True` and `raw_tier` correctly
- `_cap_tier`: EXECUTE capped to SUGGEST returns SUGGEST; OBSERVE capped to SUGGEST stays OBSERVE

**Estimation reasoning:** The trust engine has 8 functions with nuanced behavior (fail-safe on resolution errors, type coercion in operators, safety bounds logic). 3 hours for ~15-20 test cases covering all operator branches and the safety bounds cap logic.

**Unknowns:**
- The `evaluate_trust_tier` function requires a real `AsyncSession` and calls `list_rules` and `get_safety_bounds`. Tests must either mock the session or set up in-memory DB with the trust config tables. Recommend mocking `list_rules` and `get_safety_bounds` at the module level to test the evaluation logic in isolation.

**Done when:** All operator branches covered. Safety bounds capping tested. First-match-wins verified.

---

#### Item 4: Story T37.4 -- Steering API Tests

**Estimate:** 3 hours (M size, 1 Ralph loop)
**Rationale for sequence:** After models. Steering API is the highest-risk module because it sends Temporal signals and validates TaskPacket status. Bugs here could cause incorrect pipeline state transitions in production.

**Test file:** `tests/dashboard/test_steering.py`

**Key tests per endpoint:**

**POST /tasks/{task_id}/pause:**
- Happy path: active task returns 202, signal sent to Temporal
- 404: unknown task_id
- 409: task in terminal state (PUBLISHED, FAILED, ABORTED)
- 409: task already PAUSED

**POST /tasks/{task_id}/resume:**
- Happy path: paused task returns 202
- 404: unknown task_id
- 409: task is not PAUSED (e.g., IN_PROGRESS)

**POST /tasks/{task_id}/abort:**
- Happy path: active task with reason returns 202
- 404: unknown task_id
- 409: task in terminal state
- 422: missing/empty reason (min_length=1 validation)

**POST /tasks/{task_id}/redirect:**
- Happy path: valid target_stage returns 202
- 404: unknown task_id
- 400: unknown target_stage
- 400: target_stage not earlier than current stage
- 409: task in terminal state

**POST /tasks/{task_id}/retry:**
- Happy path: task with active stage returns 202
- 404: unknown task_id
- 409: task in terminal state

**GET /steering/audit:**
- Returns list of audit entries
- Supports action filter
- Supports pagination (limit, offset)

**GET /tasks/{task_id}/audit:**
- Returns audit entries for specific task
- 404: task not found

**Helper tests:**
- `_detect_current_stage`: returns highest-order active stage, None when no active stage
- `_TERMINAL_STATUSES` contains exactly the expected 5 statuses

**Estimation reasoning:** 7 endpoints, each needing 2-5 test cases. Must mock both `get_by_id` (DB) and `get_temporal_client` (Temporal). FastAPI `TestClient` or `httpx.AsyncClient` pattern. 3 hours for ~20 test cases.

**Done when:** All status code paths verified. Temporal signal mock called with correct args. Helper functions tested in isolation.

---

#### Item 5: Story T37.3 -- Trust Router Tests

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** After models. Trust router is a CRUD wrapper -- lower risk than trust engine but must be covered.

**Test file:** `tests/dashboard/test_trust_router.py`

**Key tests:**
- **Rules CRUD:**
  - GET /trust/rules: returns list (empty and populated)
  - GET /trust/rules?active_only=true: filters correctly
  - POST /trust/rules: creates rule, returns 201
  - GET /trust/rules/{id}: returns rule, 404 on missing
  - PUT /trust/rules/{id}: partial update, 404 on missing
  - DELETE /trust/rules/{id}: returns 204, 404 on missing
- **Safety bounds:**
  - GET /trust/safety-bounds: returns singleton (auto-creates if absent)
  - PUT /trust/safety-bounds: updates, returns new values
- **Default tier:**
  - GET /trust/default-tier: returns current tier
  - PUT /trust/default-tier: updates, returns new tier

**Estimation reasoning:** Thin CRUD endpoints that delegate to model-layer functions. Mock or fixture the DB session. 2 hours for ~12 test cases.

**Done when:** All CRUD operations tested. 404 paths verified for rules.

---

#### Item 6: Story T37.5 -- Budget Checker Tests

**Estimate:** 2.5 hours (M size, 1 Ralph loop)
**Rationale for sequence:** After models. Budget checker has complex conditional logic (threshold comparison, pause-on-exceed, model downgrade) that must be tested with mocked dependencies.

**Test file:** `tests/dashboard/test_budget_checker.py`

**Key tests:**
- `_check_budget_thresholds`:
  - Weekly spend below cap: no action taken
  - Weekly spend >= cap with `pause_on_budget_exceeded=True`: `_pause_all_active_workflows` called
  - Weekly spend >= cap with `pause_on_budget_exceeded=False`: no pause
  - Spend approaching cap with `model_downgrade_on_approach=True`: `_enable_cost_optimization_routing` called
  - Spend approaching cap but `_downgrade_activated=True` (debounce): no duplicate write
  - `weekly_budget_cap` is None: no thresholds evaluated
- `_pause_all_active_workflows`:
  - Queries active TaskPackets, sends pause signal to each
  - Empty result: no signals sent
  - Temporal client failure: logged, not re-raised
- `_on_message`:
  - Parses JSON envelope correctly
  - Handles both bare payload and typed envelope
  - Always acks message (even on error)
- Module-level `_downgrade_activated` flag:
  - Reset on `start_budget_checker()` call
  - Set to True after first downgrade action

**Estimation reasoning:** Must mock 3 external dependencies (DB session, Temporal client, spend report). The conditional threshold logic has 6+ branches. 2.5 hours for ~12 test cases with mocking setup.

**Unknowns:**
- The `_check_budget_thresholds` function uses `global _downgrade_activated`. Tests must be careful to reset module state between runs. Use `monkeypatch` or import-and-set.

**Done when:** All threshold branches covered. Debounce flag tested. Mock ack verified.

---

#### Item 7: Story T37.6 -- Budget Router Tests

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** After budget checker. Budget router is a thin wrapper over `get_spend_report` and budget config CRUD.

**Test file:** `tests/dashboard/test_budget_router.py`

**Key tests:**
- GET /budget/summary: returns correct shape (window_hours, total_cost, total_calls, etc.)
- GET /budget/history: returns by_day and by_model arrays
- GET /budget/by-stage: returns by_stage array
- GET /budget/by-model: returns by_model array
- GET /budget/config: returns BudgetConfigRead
- PUT /budget/config: partial update, returns updated config
- Query parameter validation: window_hours ge=1, le=8760

**Estimation reasoning:** 6 endpoints, mostly GET-only, wrapping synchronous `get_spend_report`. Must mock the spend report function. 2 hours for ~8 test cases.

**Done when:** All endpoints return expected shape. Config CRUD tested.

---

#### Item 8: Story T37.7 -- Notification Generator Tests

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** After models. Notification generator is pure mapping logic (NATS event -> notification record) plus persistence.

**Test file:** `tests/dashboard/test_notification_generator.py`

**Key tests:**
- **Builder functions (4 tests each):**
  - `_notification_for_gate_fail`: builds correct type/title/message; handles missing checks; extracts task_id
  - `_notification_for_cost_update`: builds correctly; returns None when delta=0 (skip rule)
  - `_notification_for_steering_action`: builds correctly; includes optional from_stage/to_stage/reason
  - `_notification_for_trust_tier`: builds correctly; includes safety_capped note when True
- **_safe_task_id:** valid UUID string, invalid string returns None, None returns None
- **_on_message:** dispatches to correct builder based on `type` field; falls back to `msg.subject`; unknown subject skipped; always acks
- **_persist_notification:** creates NotificationCreate and calls create_notification (mock DB)
- **_BUILDERS dict:** has exactly 4 entries with correct keys

**Estimation reasoning:** 4 builder functions are pure (no async, no DB). The `_on_message` handler needs a mock NATS message. 2 hours for ~16 test cases.

**Done when:** All 4 builder functions tested including edge cases. Ack-always behavior verified.

---

#### Item 9: Story T37.8 -- Notification Router Tests

**Estimate:** 1.5 hours (S size, 1 Ralph loop)
**Rationale for sequence:** After models and notification generator. Thin endpoint wrapper.

**Test file:** `tests/dashboard/test_notification_router.py`

**Key tests:**
- GET /notifications: returns NotificationListResponse with items, total, unread_count
- GET /notifications?unread_only=true: filters unread
- GET /notifications?notification_type=gate_fail: filters by type
- Pagination: limit and offset work correctly
- PATCH /notifications/{id}/read: marks as read, returns updated notification
- PATCH /notifications/{id}/read: 404 on missing notification
- POST /notifications/mark-all-read: returns count of updated notifications

**Estimation reasoning:** 3 endpoints, one with query params. 1.5 hours for ~7 test cases.

**Done when:** All endpoints tested. Filter combinations verified. 404 path covered.

---

#### Item 10: Story T37.9 -- Temporal Signal Handler Tests

**Estimate:** 3 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** Last because it is the highest-complexity test to write. Temporal workflow testing requires either the Temporal test environment SDK or careful mocking of `workflow.execute_activity`. This is the riskiest story in the sprint.

**Test file:** `tests/workflow/test_steering_signals.py`

**Key tests:**
- `pause_task` signal: sets `_paused=True`, calls `persist_steering_audit_activity` with action="pause"
- `resume_task` signal: sets `_paused=False`, calls audit with action="resume"
- `abort_task` signal: sets `_aborted=True`, stores reason, clears pause flag, calls audit with action="abort"
- `redirect_task` signal: validates target_stage in STAGE_ORDER, validates target < current, sets redirect state, calls audit
- `redirect_task` with unknown stage: logs warning, does not set redirect
- `redirect_task` with forward redirect: logs warning, does not set redirect
- `retry_stage` signal: uses current_step as target, calls audit with action="retry"
- `retry_stage` with no current stage: logs warning, returns early
- Idempotency: calling pause_task twice keeps `_paused=True`
- Abort unblocks pause: after pause, abort sets `_paused=False`

**Estimation reasoning:** Temporal workflow signal testing is non-trivial. The `temporalio.testing` module provides `WorkflowEnvironment` for unit testing workflows. Must verify that: (a) signal handlers modify workflow state correctly, and (b) `workflow.execute_activity` is called with correct `PersistSteeringAuditInput` args. The existing `tests/workflow/test_approval_wait.py` may provide patterns to follow. 3 hours accounts for Temporal test environment setup and ~10 test cases.

**Unknowns:**
- Whether `temporalio.testing.WorkflowEnvironment` supports signal testing directly or if we need to run a mini-workflow that accepts signals. The existing `test_approval_wait.py` likely shows the pattern.
- Activity mocking in Temporal test environment -- need to mock `persist_steering_audit_activity` to avoid real DB writes.

**Done when:** All 5 signal handlers tested. State mutations verified. Audit activity calls verified with correct args.

---

### Compressible Stories (Cut if Time Runs Short)

1. **T37.8 (Notification Router)** -- 1.5h. This is the thinnest wrapper with the simplest logic. Can be deferred to Sprint 2 slack time.
2. **T37.6 (Budget Router)** -- 2h. Also a thin wrapper. The critical budget logic is in the checker (T37.5), not the router.

If both are cut: saves 3.5 hours, sprint still delivers coverage for all complex modules.

---

### Capacity Summary

| Category | Hours |
|----------|-------|
| Available | 30 |
| Allocated (75%) | 22.5 |
| Estimated work | 22 |
| Buffer | 8 |
| Utilization | 73% |

---

## Sprint 2: Epic 38 Slice 1 (Issue Import) + Slice 2 Backend

**Sprint Duration:** 1 week (2026-03-30 to 2026-04-03)
**Capacity:** 30 hours total, 75% allocation = 22.5 hours, 7.5 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Deliver the complete Issue Import feature (Slice 1) and the backend contract for PR Evidence Explorer (Slice 2 backend stories). After this sprint, a developer can browse GitHub issues via the dashboard API, import them as TaskPackets, and the `EvidencePayload` JSON schema is defined and served via API -- ready for frontend consumption in Sprint 3.

**Test:**

1. `pytest tests/dashboard/test_github_router.py` passes -- `GET /dashboard/github/issues` returns paginated GitHub issues; `POST /dashboard/github/import` creates TaskPackets for selected issues; duplicate import returns clear error.
2. `pytest tests/integration/test_issue_import.py` passes -- end-to-end: import 2 issues, verify TaskPackets created with `source_name="dashboard_import"`, verify duplicate blocked on re-import.
3. `pytest tests/publisher/test_evidence_payload.py` passes -- `EvidencePayload` Pydantic model validates; `format_evidence_json()` produces valid JSON matching the schema.
4. `pytest tests/dashboard/test_evidence_endpoint.py` passes -- `GET /dashboard/tasks/:id/evidence` returns structured JSON for a published TaskPacket; returns 404 for unknown task.
5. Frontend import modal renders and submits (manual verification or vitest if time permits).
6. All existing tests pass (`pytest` green, `ruff check .` clean).

**Constraint:** 5 working days. Backend stories 38.1-38.7 complete. Frontend story 38.3 (import modal) complete. Stories 38.8-38.12 deferred to Sprint 3. No Slice 3 or 4 work. GitHub API calls mocked in tests (no live API dependency for CI).

---

### What's In / What's Out

**In this sprint (7 stories, ~21.5 estimated hours):**

| # | Story ID | Title | Type | Est. | Ralph Loops |
|---|----------|-------|------|------|-------------|
| 1 | 38.1 | GET /dashboard/github/issues | Backend | 4h | 1-2 |
| 2 | 38.2 | POST /dashboard/github/import | Backend | 4h | 1-2 |
| 3 | 38.3 | Import modal frontend | Frontend | 3.5h | 1 |
| 4 | 38.4 | Integration test: import flow | Test | 2h | 1 |
| 5 | 38.5 | EvidencePayload Pydantic model | Backend | 2.5h | 1 |
| 6 | 38.6 | format_evidence_json() | Backend | 3h | 1 |
| 7 | 38.7 | GET /tasks/:id/evidence endpoint | Backend | 2.5h | 1 |
| | | **Total** | | **21.5h** | |

**Out of scope:**
- PR Evidence Explorer frontend (Sprint 3)
- Reviewer action endpoints and buttons (Sprint 3)
- Integration test for evidence explorer (Sprint 3)
- Slice 3 (Projects Sync) and Slice 4 (Pipeline Comments)

---

### Dependency Review

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| GitHub REST API (issues endpoint) | Available | Cannot list issues | Mock in tests; runtime requires valid GITHUB_TOKEN |
| `taskpacket_crud.py` create function | Available | Cannot create TaskPackets from import | Confirmed: `create()` exists; may need `source_name` parameter |
| `src/publisher/evidence_comment.py` | Available | Cannot extract evidence data for JSON format | Confirmed: generates Markdown evidence; 38.6 adds JSON output |
| Triage mode (Epic 36) | Available (E36 complete) | Import triage path works if TRIAGE status exists | Guard with runtime check: if TRIAGE not available, import direct to RECEIVED |
| Dashboard router mount point | Available (Phase 0) | No registration point for new github_router | Confirmed: `src/dashboard/router.py` exists |

#### Internal Dependencies (Story-to-Story)

```
38.1 --> 38.2 --> 38.3 --> 38.4
                  (import modal needs both API endpoints)

38.5 --> 38.6 --> 38.7
(schema before implementation before endpoint)
```

- **38.1 has no dependencies** -- new router file, new endpoint, calls GitHub REST API.
- **38.2 depends on 38.1** -- import endpoint lives in same router file; needs the GitHub issues list logic for deduplication check.
- **38.3 depends on 38.1 + 38.2** -- frontend modal calls both endpoints.
- **38.4 depends on 38.1 + 38.2** -- integration test exercises the full import flow.
- **38.5 has no dependencies** -- new Pydantic model file.
- **38.6 depends on 38.5** -- uses `EvidencePayload` schema to structure JSON output.
- **38.7 depends on 38.5 + 38.6** -- endpoint calls `format_evidence_json()` and returns `EvidencePayload`.

**Two independent tracks** can be worked in parallel:
- Track A: 38.1 -> 38.2 -> 38.3 -> 38.4
- Track B: 38.5 -> 38.6 -> 38.7

**Critical path:** Track A (38.1 -> 38.2 -> 38.3 -> 38.4) at 13.5h is longer than Track B (38.5 -> 38.6 -> 38.7) at 8h.

**Recommended sequence:** Interleave tracks to front-load risk:
38.5 -> 38.1 -> 38.6 -> 38.2 -> 38.7 -> 38.3 -> 38.4

This way, if the GitHub API integration in 38.1 reveals surprises, we have already locked down the evidence schema (38.5) and can adjust.

---

### Ordered Work Items

#### Item 1: Story 38.5 -- EvidencePayload Pydantic Model

**Estimate:** 2.5 hours (M size, 1 Ralph loop)
**Rationale for sequence:** No dependencies. Defines the JSON contract that 38.6, 38.7, and all of Sprint 3's frontend work depends on. Starting here means the contract is locked before any GitHub API work begins.

**Key tasks:**
- Create `src/publisher/evidence_payload.py`
- Define `EvidencePayload` Pydantic model with sections:
  - `task_summary`: task_id, repo, issue_number, status, timestamps
  - `intent`: goal, constraints, acceptance_criteria (from IntentSpecification)
  - `gate_results`: verification results, QA results (pass/fail + details)
  - `cost_breakdown`: total_cost, by_model, by_stage
  - `provenance`: expert names, assembler metadata
  - `files_changed`: list of file paths with change type
- Write unit tests: `tests/publisher/test_evidence_payload.py`

**Done when:** `EvidencePayload` validates with sample data. Tests pass.

---

#### Item 2: Story 38.1 -- GET /dashboard/github/issues

**Estimate:** 4 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** First GitHub API integration. Establishes the `github_router.py` file and the caching pattern that 38.2 reuses.

**Key tasks:**
- Create `src/dashboard/github_router.py` with `APIRouter(prefix="/github")`
- Implement `GET /issues` endpoint:
  - Accept query params: `repo` (required), `state` (open/closed/all, default: open), `labels` (comma-separated), `search` (title substring), `page`, `per_page`
  - Call GitHub REST API `GET /repos/{owner}/{repo}/issues` with appropriate filters
  - Cache results with 5-minute TTL (use `functools.lru_cache` with TTL wrapper or simple dict cache)
  - Return paginated list with `total_count` from GitHub response headers
- Register router in `src/dashboard/router.py`
- Write tests with mocked GitHub API responses

**Unknowns:**
- GitHub REST API returns pull requests in the issues endpoint. Must filter by `pull_request` key absence.
- Rate limiting: GitHub REST API has 5000 requests/hour for authenticated requests. The 5-min cache mitigates this.

**Done when:** Endpoint returns filtered, paginated issues. Cache works. Tests pass with mocked responses.

---

#### Item 3: Story 38.6 -- format_evidence_json()

**Estimate:** 3 hours (M size, 1 Ralph loop)
**Rationale for sequence:** After 38.5 (uses EvidencePayload schema). Before 38.7 (endpoint calls this function).

**Key tasks:**
- Add `format_evidence_json()` to `src/publisher/evidence_comment.py`
- Extract data from TaskPacket and related records to populate `EvidencePayload`:
  - Task summary from `TaskPacketRow`
  - Intent from intent specification (if stored on TaskPacket or in related table)
  - Gate results from verification/QA outputs
  - Cost from model call audit records
  - Files changed from implementation output
- Write tests: `tests/publisher/test_evidence_json.py`

**Done when:** Function produces valid `EvidencePayload` from a TaskPacket with all sections populated. Handles missing data gracefully (optional sections).

---

#### Item 4: Story 38.2 -- POST /dashboard/github/import

**Estimate:** 4 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** After 38.1 (same router file, uses GitHub API patterns). This is the core import functionality.

**Key tasks:**
- Add `POST /import` endpoint to `src/dashboard/github_router.py`
- Request body: `ImportRequest(issue_numbers: list[int], repo: str, import_mode: "triage" | "direct")`
- For each issue number:
  - Fetch issue details from GitHub API (or from cached list)
  - Check for existing TaskPacket with same `repo + issue_number` (dedup)
  - Create TaskPacket via `taskpacket_crud.create()` with `source_name="dashboard_import"`
  - If `import_mode == "triage"` and TRIAGE status available: create in TRIAGE status
  - If `import_mode == "direct"` or TRIAGE unavailable: create in RECEIVED, start Temporal workflow
- Return `ImportResponse(imported: list[TaskPacketRead], skipped: list[SkippedIssue], errors: list[str])`
- Write tests

**Verified:**
- The `create()` function in `taskpacket_crud.py` already accepts `source_name` via `data.source_name` (line 40). `source_name` exists on `TaskPacketRow` (migration 022). No changes needed to the CRUD layer.

**Done when:** Batch import works. Duplicates detected and skipped. Both triage and direct modes work. Tests pass.

---

#### Item 5: Story 38.7 -- GET /tasks/:id/evidence Endpoint

**Estimate:** 2.5 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** After 38.5 + 38.6 (needs the schema and the generator function).

**Key tasks:**
- Add endpoint to existing task router or create `src/dashboard/evidence_router.py`
- `GET /tasks/{task_id}/evidence`:
  - Fetch TaskPacket by ID (404 if not found)
  - Call `format_evidence_json()` to generate `EvidencePayload`
  - Return as JSON response
- Write tests: `tests/dashboard/test_evidence_endpoint.py`

**Done when:** Endpoint returns EvidencePayload JSON. 404 on missing task. Tests pass.

---

#### Item 6: Story 38.3 -- Import Modal Frontend

**Estimate:** 3.5 hours (M size, 1 Ralph loop)
**Rationale for sequence:** After 38.1 + 38.2 (frontend needs both backend endpoints operational).

**Key tasks:**
- Create `frontend/src/components/github/ImportModal.tsx`
- Components:
  - Repo selector (from admin settings)
  - Label/status filters, search input
  - Issue list with checkboxes (calls GET /github/issues)
  - "Already in pipeline" badge on issues that match existing TaskPackets
  - Import mode toggle (triage vs direct)
  - Import button (calls POST /github/import)
  - Result summary (imported count, skipped count)
- Wire into existing dashboard navigation

**Done when:** Modal opens, lists issues, allows selection, imports, shows results.

---

#### Item 7: Story 38.4 -- Integration Test: Import Flow

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Last in Slice 1. Validates end-to-end flow after all components exist.

**Test file:** `tests/integration/test_issue_import.py`

**Key tests:**
- Import 2 GitHub issues: verify 2 TaskPackets created with correct `source_name`
- Re-import same issues: verify duplicate detection returns skip
- Import in triage mode: verify TaskPackets created in TRIAGE status
- Import in direct mode: verify TaskPackets created in RECEIVED status

**Done when:** All integration tests pass with mocked GitHub API.

---

### Compressible Stories (Cut if Time Runs Short)

1. **38.3 (Import Modal Frontend)** -- 3.5h. Backend is the priority; frontend can be deferred to Sprint 3 if backend stories take longer than expected.
2. **38.4 (Integration Test)** -- 2h. Backend unit tests from 38.1 and 38.2 provide partial coverage. Integration test is ideal but can slip to Sprint 3.

---

### Capacity Summary

| Category | Hours |
|----------|-------|
| Available | 30 |
| Allocated (75%) | 22.5 |
| Estimated work | 21.5 |
| Buffer | 8.5 |
| Utilization | 72% |

---

## Sprint 3: Epic 38 Slice 2 Frontend + Integration Tests

**Sprint Duration:** 1 week (2026-04-06 to 2026-04-10)
**Capacity:** 30 hours total, 75% allocation = 22.5 hours, 7.5 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Deliver the complete PR Evidence Explorer frontend (tabbed viewer), reviewer action endpoints and UI buttons, and the integration test that validates the full Slice 2 flow. After this sprint, a reviewer can open a TaskPacket's evidence in an explorable tabbed interface and take action (approve & merge, request changes) directly from the dashboard.

**Test:**

1. PR Evidence Explorer renders all 5 tabs (Evidence, Diff, Intent, Gates, Cost) for a published TaskPacket (vitest component test or manual verification).
2. `pytest tests/dashboard/test_pr_router.py` passes -- approve and request-changes endpoints tested with mocked GitHub API.
3. Reviewer action buttons render and call correct endpoints (vitest or manual).
4. `pytest tests/integration/test_pr_evidence_explorer.py` passes -- evidence JSON generated for published TaskPacket, approve action calls GitHub merge API.
5. All existing tests pass (`pytest` green, `ruff check .` clean).
6. Any Sprint 2 carryover stories complete.

**Constraint:** 5 working days. All Slice 2 stories (38.8-38.12) complete. MVP (Slices 1+2) fully delivered. No Slice 3 or 4 work unless all Slice 2 stories finish early (use buffer for polish, not scope expansion).

---

### What's In / What's Out

**In this sprint (5 stories + potential Sprint 2 carryover, ~21 estimated hours):**

| # | Story ID | Title | Type | Est. | Ralph Loops |
|---|----------|-------|------|------|-------------|
| 1 | 38.8 | PR Evidence Explorer frontend | Frontend | 6h | 2 |
| 2 | 38.9 | POST /tasks/:id/pr/approve | Backend | 3.5h | 1 |
| 3 | 38.10 | POST /tasks/:id/pr/request-changes | Backend | 3.5h | 1 |
| 4 | 38.11 | Reviewer action buttons frontend | Frontend | 3h | 1 |
| 5 | 38.12 | Integration test: evidence + reviewer actions | Test | 3h | 1 |
| | | **Total** | | **19h** | |

**Out of scope:**
- Slice 3 (Projects Sync) -- separate sprint if MVP succeeds
- Slice 4 (Pipeline Comments + Webhook Bridge) -- separate sprint
- Frontend vitest setup (if not already in place; manual verification acceptable for MVP)

---

### Dependency Review

#### Internal Dependencies (Story-to-Story)

```
[Sprint 2: 38.5-38.7] --> 38.8 (Evidence Explorer needs EvidencePayload endpoint)
                      \-> 38.9 --> 38.11 (Approve button needs approve endpoint)
                      \-> 38.10 --> 38.11 (Request Changes button needs endpoint)
                                    \-> 38.12 (Integration test needs everything)
```

- **38.8 depends on 38.5-38.7 (Sprint 2)** -- frontend consumes the evidence JSON endpoint.
- **38.9 has no Sprint 3 dependencies** -- new endpoint, new router file.
- **38.10 has no Sprint 3 dependencies** -- same router file as 38.9.
- **38.11 depends on 38.9 + 38.10** -- buttons call the endpoints.
- **38.12 depends on all of 38.5-38.11** -- integration test exercises the full flow.

**Critical path:** 38.8 (6h) is the single longest story. Start it first.

**Recommended sequence:** 38.9 -> 38.10 -> 38.8 -> 38.11 -> 38.12

Start with the two backend endpoints (38.9, 38.10) which are quick and independent, then tackle the large frontend story (38.8), then wire up buttons (38.11), and close with integration test (38.12).

---

### Ordered Work Items

#### Item 1: Story 38.9 -- POST /tasks/:id/pr/approve

**Estimate:** 3.5 hours (M size, 1 Ralph loop)

**Key tasks:**
- Create `src/dashboard/pr_router.py`
- `POST /tasks/{task_id}/pr/approve`: fetch TaskPacket, extract PR number, call GitHub REST API `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge`, return result
- Handle: 404 task not found, 409 no PR exists, GitHub API errors
- Write tests with mocked GitHub API

**Done when:** Endpoint merges PR via GitHub API. Error paths tested.

---

#### Item 2: Story 38.10 -- POST /tasks/:id/pr/request-changes

**Estimate:** 3.5 hours (M size, 1 Ralph loop)

**Key tasks:**
- Add to `src/dashboard/pr_router.py`
- `POST /tasks/{task_id}/pr/request-changes`: accept review body, call GitHub REST API `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` with event="REQUEST_CHANGES"
- Optionally trigger loopback signal to Temporal workflow
- Write tests

**Done when:** Endpoint posts review comment via GitHub API. Loopback signal sent if task has active workflow.

---

#### Item 3: Story 38.8 -- PR Evidence Explorer Frontend

**Estimate:** 6 hours (L size, 2 Ralph loops)

**Key tasks:**
- Create `frontend/src/components/pr/EvidenceExplorer.tsx`
- Tabbed viewer with 5 tabs:
  - Evidence: rendered summary (task status, PR link, timestamps)
  - Diff: file list with change type indicators
  - Intent: goal, constraints, acceptance criteria
  - Gates: verification + QA results (pass/fail badges)
  - Cost: total cost, by-model breakdown, by-stage breakdown
- Fetch data from `GET /tasks/:id/evidence`
- Loading states, error handling, empty states

**Done when:** All 5 tabs render with real data from evidence endpoint. Loading and error states work.

---

#### Item 4: Story 38.11 -- Reviewer Action Buttons Frontend

**Estimate:** 3 hours (S-M size, 1 Ralph loop)

**Key tasks:**
- Create `frontend/src/components/pr/ReviewerActions.tsx`
- Buttons: Approve & Merge, Request Changes, Close PR, View on GitHub
- Approve & Merge calls `POST /tasks/:id/pr/approve`, shows confirmation dialog
- Request Changes calls `POST /tasks/:id/pr/request-changes`, shows textarea for review body
- View on GitHub opens PR URL in new tab
- Success/error feedback

**Done when:** All 4 buttons render and function. Confirmation dialogs work.

---

#### Item 5: Story 38.12 -- Integration Test: Evidence + Reviewer Actions

**Estimate:** 3 hours (M size, 1 Ralph loop)

**Test file:** `tests/integration/test_pr_evidence_explorer.py`

**Key tests:**
- Evidence JSON generated for a published TaskPacket (all 5 sections populated)
- Evidence endpoint returns valid `EvidencePayload`
- Approve action calls GitHub merge API with correct params
- Request-changes action calls GitHub review API with correct params
- Error cases: task not published (no evidence), task has no PR

**Done when:** All integration tests pass with mocked GitHub API.

---

### Compressible Stories (Cut if Time Runs Short)

1. **38.11 (Reviewer Action Buttons)** -- 3h. Evidence Explorer (38.8) is the higher-value frontend component. Reviewer buttons can be added as a follow-up if Sprint 3 runs long.
2. **38.12 (Integration Test)** -- 3h. Unit tests from 38.9, 38.10 provide partial coverage. Integration test is ideal but can be the first story of a Sprint 4 if needed.

---

### Capacity Summary

| Category | Hours |
|----------|-------|
| Available | 30 |
| Allocated (75%) | 22.5 |
| Estimated work | 19 |
| Buffer | 11 |
| Utilization | 63% |

Sprint 3 intentionally runs lighter (63%) because:
- Sprint 2 carryover is likely (GitHub API integration often has surprises)
- 38.8 (Evidence Explorer) is an L-sized frontend story with discovery risk
- Buffer absorbs scope from Sprint 2 if anything slips

---

## Cross-Sprint Dependency Graph

```
Sprint 1 (E37 Test Debt)          Sprint 2 (E38 S1 + S2 Backend)     Sprint 3 (E38 S2 Frontend)
========================          ==============================     ==========================

T37.10 (conftest)                 38.5 (EvidencePayload model)       38.9 (approve endpoint)
  |                                 |                                  |
  v                                 v                                  v
T37.1 (model tests)              38.6 (format_evidence_json)        38.10 (request-changes)
  |                                 |                                  |
  +-> T37.2 (trust engine)         v                                  |
  +-> T37.3 (trust router)       38.7 (evidence endpoint)            |
  +-> T37.4 (steering API)         |                                  |
  +-> T37.5 (budget checker)       |         38.1 (list issues)       v
  +-> T37.6 (budget router)        |           |                   38.8 (Evidence Explorer UI)
  +-> T37.7 (notif generator)      |           v                      |
  +-> T37.8 (notif router)         |         38.2 (import)           v
  +-> T37.9 (temporal signals)     |           |                   38.11 (reviewer buttons)
                                    |           v                      |
      GATE: all tests green ------->|         38.3 (import modal)     v
                                    |           |                   38.12 (integration test)
                                    |           v
                                    |         38.4 (import integ test)
                                    |
                                    +---> Sprint 3 depends on 38.5-38.7
```

---

## Critical Path

The critical path across all 3 sprints:

```
T37.10 -> T37.1 -> T37.9 -> [gate] -> 38.1 -> 38.2 -> 38.3 -> 38.4 -> [sprint break]
                                                                            |
                                        38.5 -> 38.6 -> 38.7 -----------> 38.8 -> 38.11 -> 38.12
```

**Total critical path duration:** ~35 hours across 3 weeks.

**Biggest risk points:**
1. **T37.9 (Temporal signal tests)** -- Temporal test environment setup is unfamiliar territory. If this blocks, defer to end of Sprint 1 buffer time. All other Sprint 1 stories are independent of it.
2. **38.1 (GitHub issues endpoint)** -- First real GitHub API integration. If the REST API has unexpected behavior (PR/issue conflation, pagination quirks), this takes longer than estimated.
3. **38.8 (Evidence Explorer frontend)** -- L-sized frontend story with 5 tabs. If the evidence JSON schema needs iteration after seeing it in the UI, this creates churn between 38.5/38.6 and 38.8.

---

## Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | Temporal test environment setup takes longer than 3h | Medium | Sprint 1 buffer consumed | Check `test_approval_wait.py` patterns first; fall back to mock-based testing if WorkflowEnvironment is too complex |
| R2 | Existing tests break due to import side effects from new test directory | Low | 1-2h to debug | Run full `pytest` after T37.10 setup before writing any test logic |
| R3 | GitHub REST API rate limiting during development | Low | Slows manual testing | Use mocked responses for automated tests; cache aggressively in dev |
| R4 | EvidencePayload schema needs revision after frontend sees it | Medium | Churn between 38.5/38.6/38.8 | Lock schema in Sprint 2; Sprint 3 frontend adapts to whatever shipped |
| R5 | Sprint 2 carryover exceeds Sprint 3 buffer | Low | MVP delivery slips by 1 week | Sprint 3 has 11h buffer (37% slack); compressible stories identified |
| R6 | Trust engine tests reveal bugs in production code | Medium | Scope creep in Sprint 1 | File bugs as issues; do NOT fix inline during Sprint 1. Fix in Sprint 2 buffer or dedicate Sprint 4 |

---

## Overall Capacity Summary

| Sprint | Available | Allocated (75%) | Estimated | Buffer | Utilization |
|--------|-----------|-----------------|-----------|--------|-------------|
| Sprint 1 (E37 tests) | 30h | 22.5h | 22h | 8h | 73% |
| Sprint 2 (E38 S1+S2 BE) | 30h | 22.5h | 21.5h | 8.5h | 72% |
| Sprint 3 (E38 S2 FE) | 30h | 22.5h | 19h | 11h | 63% |
| **Total** | **90h** | **67.5h** | **62.5h** | **27.5h** | **69%** |

Overall 69% utilization reflects the high uncertainty in two areas: Temporal test environment (Sprint 1) and first-time GitHub API integration (Sprint 2). The progressive tightening from Sprint 1 -> Sprint 3 is intentional: Sprint 3 runs lightest because it absorbs carryover.

---

## Exit Criteria (After Sprint 3)

When all 3 sprints are complete, the following must be true:

1. **Epic 37 Test Debt: PAID.** All 12 modules have passing tests. `pytest tests/dashboard/ tests/workflow/test_steering_signals.py` green.
2. **Epic 38 Slice 1 (Issue Import): COMPLETE.** Developer can browse and import GitHub issues from the dashboard.
3. **Epic 38 Slice 2 (PR Evidence Explorer): COMPLETE.** Reviewer can explore evidence in a tabbed interface and take approve/request-changes actions.
4. **No regression.** All pre-existing tests pass. `ruff check .` clean.
5. **Slices 3+4 decision.** Based on Sprint 1-3 learnings and the kill criterion (20% import adoption), decide whether to proceed with Slices 3+4 or move to Epic 39.

---

## Meridian Review: PASS (2026-03-22)

**Verdict: CONDITIONAL PASS → PASS** (2 gaps fixed)

| # | Question | Verdict |
|---|----------|---------|
| 1 | Work order justified? | **PASS** |
| 2 | Sprint goals testable? | **PASS** |
| 3 | Dependencies visible? | **PASS** |
| 4 | Estimation reasoning recorded? | **PASS** |
| 5 | Unknowns surfaced and buffered? | **PASS** |
| 6 | Reflects learning from retros? | **PASS** |
| 7 | Team can execute without clarification? | **PASS** (after fixes) |

**Red flags: NONE triggered.**

**Gaps found and fixed:**
1. ~~Root conftest dependency claim incorrect~~ **FIXED:** Updated to note root conftest has ordering only; T37.10 creates dashboard conftest.
2. ~~`taskpacket_crud.create()` source_name marked as unknown~~ **FIXED:** Confirmed `source_name` exists on `TaskPacketRow` (migration 022), accepted by `create()` at line 40.
