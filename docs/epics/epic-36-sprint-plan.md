# Sprint Plan: Epic 36 MVP -- Planning Experience (Slices 1 + 2)

**Planned by:** Helm
**Date:** 2026-03-21
**Status:** APPROVED -- Meridian Review PASS (2026-03-21)
**Epic:** Epic 36 Phase 2 -- Planning Experience (Meridian Round 2 PASS, 2026-03-21)
**MVP Scope:** Slice 1 (Triage Queue, Stories 36.1-36.6) + Slice 2 (Intent Spec Review, Stories 36.7-36.12 + 36.7a)
**Total Duration:** 4 sprints across 4 weeks
**Capacity:** Single developer, 30 hours per week (5 days x 6 productive hours)

---

## MVP Architecture Overview

The MVP introduces two decision points into the existing pipeline:

1. **Triage Queue (Slice 1)** -- A front door where the developer reviews incoming issues before they enter the Temporal workflow. Feature-flagged via `TRIAGE_MODE_ENABLED`. New `TRIAGE` status added as a pre-`RECEIVED` state.

2. **Intent Spec Review (Slice 2)** -- A wait point after the Intent Builder where the developer can approve, edit, refine, or reject the spec before the Router runs. Feature-flagged via `INTENT_REVIEW_ENABLED`. New Temporal signals: `approve_intent`, `edit_intent`, `reject_intent`.

Both slices are additive. All existing behavior is preserved behind feature flags that default to `false`.

---

## Sprint 1: Triage Backend (Stories 36.1-36.4)

**Sprint Duration:** 1 week (2026-03-24 to 2026-03-28)
**Capacity:** 30 hours total, 77% allocation = 23 hours, 7 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Add a feature-flagged triage mode to the pipeline. When `TRIAGE_MODE_ENABLED=true`, incoming webhook issues create TaskPackets in `TRIAGE` status instead of starting a Temporal workflow. The developer can then accept (start workflow), reject (with reason), or edit the task via REST API before it enters the pipeline.

**Test:** After all four stories are complete:

1. `pytest tests/models/test_taskpacket.py` passes -- `TRIAGE` status exists in enum; transitions `TRIAGE -> RECEIVED` and `TRIAGE -> REJECTED` are valid; all existing transitions unchanged.
2. `pytest tests/ingress/test_webhook_handler.py` passes -- webhook creates TaskPacket in `TRIAGE` status when flag is true; creates in `RECEIVED` and starts workflow when flag is false (default).
3. `pytest tests/dashboard/test_planning_router.py` passes -- `POST .../accept` transitions `TRIAGE -> RECEIVED` and starts workflow; `POST .../reject` transitions `TRIAGE -> REJECTED` with required reason; `PATCH ...` edits fields while in `TRIAGE`; all three return 409 on wrong status.
4. `pytest tests/context/test_prescan.py` passes -- pre-scan returns `{file_count, complexity_hint, cost_estimate}` shape; `triage_enrichment` column is populated on TRIAGE creation.
5. All existing tests pass (`pytest` green, `ruff check .` clean).

**Constraint:** 5 working days. Changes are confined to: `src/models/taskpacket.py`, `src/settings.py`, `src/ingress/webhook_handler.py`, `src/dashboard/planning_router.py` (new), `src/context/prescan.py` (new), `src/models/taskpacket_crud.py`, and corresponding test files. No modifications to existing Temporal signal handlers. No frontend work.

---

### What's In / What's Out

**In this sprint (4 stories, ~22 estimated hours):**
- Story 36.1: Add TRIAGE status to TaskPacket model
- Story 36.2: Conditional triage mode in webhook handler
- Story 36.3: Triage action endpoints (accept, reject, edit)
- Story 36.4: Context pre-scan for triage enrichment

**Out of scope:**
- Frontend components (Sprint 2)
- SSE events for triage (Sprint 2)
- Intent review workflow or API (Sprints 3-4)
- Any modification to existing Temporal workflow signals

---

### Dependency Review (30-Minute Pre-Planning)

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Dashboard router at `src/dashboard/router.py` | COMPLETE (Phase 0) | No mount point for new planning endpoints | Confirmed: router exists with `/api/v1/dashboard/` prefix and 4 sub-routers |
| TaskPacket model at `src/models/taskpacket.py` | Available | Cannot add TRIAGE status | Confirmed: 13 statuses in `TaskPacketStatus` enum; transition map at `ALLOWED_TRANSITIONS` |
| Webhook handler at `src/ingress/webhook_handler.py` | Available | Cannot add conditional TRIAGE creation | Confirmed: creates TaskPacket with `TaskPacketStatus.RECEIVED` at line 176 |
| `taskpacket_crud.py` status transition validation | Available | Cannot validate accept/reject transitions | Confirmed: `update_status()` validates against `ALLOWED_TRANSITIONS` |
| PostgreSQL + Alembic migrations | Available | Cannot add new enum value or column | Confirmed: migration pattern established in codebase |

#### Internal Dependencies (Story-to-Story)

```
36.1 --> 36.2 --> 36.3
              \-> 36.4
```

- **36.1 has no dependencies** -- pure model change (enum + transitions). Foundation for everything.
- **36.2 depends on 36.1** -- webhook handler needs `TRIAGE` status to exist before conditionally creating TaskPackets in that status.
- **36.3 depends on 36.1** -- accept/reject endpoints need `TRIAGE -> RECEIVED` and `TRIAGE -> REJECTED` transitions to exist.
- **36.4 depends on 36.1** -- pre-scan writes to a new `triage_enrichment` column on TaskPacket; needs the TRIAGE status to make sense.

**Critical path:** 36.1 --> 36.2 --> 36.3 (36.4 can run in parallel with 36.3 after 36.1 is done)

---

### Ordered Work Items

#### Item 1: Story 36.1 -- Add TRIAGE Status to TaskPacket Model

**Estimate:** 3 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Foundation. Every other Sprint 1 story depends on the TRIAGE status existing and having valid transitions.

**Key tasks:**
- Add `TRIAGE = "triage"` to `TaskPacketStatus` enum in `src/models/taskpacket.py`
- Add transition rules to `ALLOWED_TRANSITIONS`:
  - `TaskPacketStatus.TRIAGE: {TaskPacketStatus.RECEIVED, TaskPacketStatus.REJECTED, TaskPacketStatus.FAILED}`
- Add new column to `TaskPacketRow`: `triage_enrichment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)`
- Add `triage_enrichment` to `TaskPacketRead` Pydantic model
- Create Alembic migration: `src/db/migrations/NNN_add_triage_status.py`
  - Add `triage` to the PostgreSQL enum type (ALTER TYPE ... ADD VALUE)
  - Add `triage_enrichment` JSON column (nullable)
- Write unit tests: verify new status in enum; verify TRIAGE transitions are valid; verify existing transitions unchanged; verify triage_enrichment field is nullable

**Estimation reasoning:** Straightforward enum extension and column addition. The migration is the trickiest part -- PostgreSQL enum ALTER TYPE requires careful syntax. Pattern is established from prior migrations (e.g., `stage_timings` column addition in Epic 35). 3 hours covers model change + migration + tests.

**Unknowns:**
- PostgreSQL enum migration: `ALTER TYPE taskpacket_status ADD VALUE 'triage'` is not transactional in PostgreSQL < 12. Our compose setup runs PG 16, so this is fine, but worth verifying.

**Done when:** `pytest tests/models/test_taskpacket.py` passes with TRIAGE status tests. `ruff check src/models/taskpacket.py` clean.

---

#### Item 2: Story 36.2 -- Conditional Triage Mode in Webhook Handler

**Estimate:** 5 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** After TRIAGE status exists, the webhook handler can conditionally use it. This is the entry point -- without it, no TaskPackets enter triage.

**Key tasks:**
- Add `triage_mode_enabled: bool = False` to `Settings` in `src/settings.py` (env var: `THESTUDIO_TRIAGE_MODE_ENABLED`)
- Modify `github_webhook()` in `src/ingress/webhook_handler.py`:
  - When `settings.triage_mode_enabled is True`: create TaskPacket with `status=TaskPacketStatus.TRIAGE` instead of `RECEIVED`, skip `start_workflow()` call
  - When `False` (default): behavior unchanged
  - Must update the `create()` function in `taskpacket_crud.py` to accept an optional `initial_status` parameter (currently hardcodes `TaskPacketStatus.RECEIVED`)
- Write tests:
  - Test webhook creates in TRIAGE when flag is true (no workflow started)
  - Test webhook creates in RECEIVED when flag is false (workflow started -- current behavior)
  - Test default behavior is unchanged (flag defaults to false)

**Estimation reasoning:** The webhook handler is well-structured (262 lines, clear step numbering). The conditional logic is a small insertion at step 11. The `taskpacket_crud.create()` hardcodes RECEIVED status (line 39), which needs a parameter to support TRIAGE. This is a one-line change but needs a test update. 5 hours accounts for webhook handler modification + CRUD change + comprehensive test coverage of both modes.

**Unknowns:**
- The `create()` function uses `INSERT ... ON CONFLICT DO NOTHING` with hardcoded `status=TaskPacketStatus.RECEIVED`. Changing this to accept a parameter is clean but must preserve the dedupe behavior. The on_conflict clause does not check status, so this should be safe.

**Done when:** Webhook handler tests pass in both triage and non-triage modes. Default behavior is identical to current behavior. No existing tests broken.

---

#### Item 3: Story 36.3 -- Triage Action Endpoints (Accept, Reject, Edit)

**Estimate:** 8 hours (M-L size, 2 Ralph loops)
**Rationale for sequence:** Depends on TRIAGE status and transitions (36.1). This is the largest story in the sprint -- three endpoints with validation, CRUD updates, and workflow trigger integration.

**Key tasks:**
- Create `src/dashboard/planning_router.py` with three endpoints:
  - `POST /tasks/{task_id}/accept`:
    - Validate TaskPacket is in `TRIAGE` status (return 409 if not)
    - Call `update_status(task_id, TaskPacketStatus.RECEIVED)`
    - Start Temporal workflow via `start_workflow()` (same pattern as webhook handler)
    - Return 200 with updated TaskPacket
  - `POST /tasks/{task_id}/reject`:
    - Validate TaskPacket is in `TRIAGE` status (return 409 if not)
    - Require `reason` field (body): one of `duplicate`, `out_of_scope`, `needs_info`, `wont_fix`
    - Call `update_status(task_id, TaskPacketStatus.REJECTED)`
    - Store rejection reason (add `rejection_reason: str | None` to TaskPacketRow or use existing fields)
    - Return 200 with updated TaskPacket
  - `PATCH /tasks/{task_id}`:
    - Validate TaskPacket is in `TRIAGE` status (return 409 if not)
    - Accept optional fields: `title`, `description`, `category`, `priority`
    - Persist edits to TaskPacket (need to add `title`, `description` columns or use the existing `issue_title`/`issue_body` pattern from webhook payload)
    - Return 200 with updated TaskPacket
- Add new CRUD functions to `src/models/taskpacket_crud.py`:
  - `accept_from_triage(session, task_id) -> TaskPacketRead` (transition + return)
  - `reject_from_triage(session, task_id, reason) -> TaskPacketRead` (transition + store reason)
  - `update_triage_fields(session, task_id, **fields) -> TaskPacketRead`
- Register `planning_router` in `src/dashboard/router.py`
- Pydantic request/response models for reject reason, edit payload
- Write comprehensive tests:
  - Accept: happy path, 409 on non-TRIAGE status, 404 on missing task, verify workflow started
  - Reject: happy path with each reason type, 409 on non-TRIAGE, missing reason returns 422
  - Edit: happy path, 409 on non-TRIAGE, partial update (only title), verify persistence

**Estimation reasoning:** This is the largest story because it involves three distinct endpoints, each with status validation, error handling, and integration (accept triggers workflow start). The reject endpoint needs a storage mechanism for the reason -- TaskPacketRow currently has no `rejection_reason` field. Options: (a) add a column, (b) store in the triage_enrichment JSON, (c) use the existing `scope` field. Recommend (a) for queryability. The edit endpoint needs to store issue metadata that currently only exists in the webhook payload, not on the TaskPacket row -- `issue_title` and `issue_body` are only in the Temporal workflow input, not persisted. Must decide: add columns to TaskPacketRow or store in triage_enrichment JSON. 8 hours accounts for the design decisions, three endpoints, CRUD layer, and thorough test coverage.

**Unknowns:**
- **Issue metadata storage:** The webhook handler stores `issue_title` and `issue_body` in the `PipelineInput` dataclass passed to Temporal, not on the TaskPacket row. The triage edit endpoint needs to persist these. Options: (a) add `issue_title`, `issue_body` columns to `TaskPacketRow`, (b) store in `triage_enrichment` JSON. Recommend (a) for clarity, but this adds two columns and a migration.
- **Rejection reason storage:** Need a column or JSON field. Recommend adding `rejection_reason: Mapped[str | None]` to TaskPacketRow.

**Done when:** All three endpoints respond correctly. 409 on wrong status. Reject requires reason. Accept starts workflow. Edit persists changes. All test assertions pass.

---

#### Item 4: Story 36.4 -- Context Pre-Scan for Triage Enrichment

**Estimate:** 6 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** Can run in parallel with 36.3 after 36.1 is done. Provides the pre-scan data that triage cards will display. Does not block any other Sprint 1 story.

**Key tasks:**
- Create `src/context/prescan.py`:
  - `prescan_issue(issue_title, issue_body, labels) -> dict`:
    - `file_count_estimate: int` -- heuristic based on issue body mentions of files/directories
    - `complexity_hint: str` -- "low" / "medium" / "high" based on body length, label keywords, mention of testing/migration/breaking
    - `cost_estimate_range: dict` -- `{"min": float, "max": float}` based on complexity hint
  - Pure function, no DB access, no LLM call, no external dependency
  - This is NOT the full Context stage -- it is a fast heuristic (<10ms)
- Modify webhook handler (in triage mode) to call `prescan_issue()` and store result in `triage_enrichment` JSON column
- Write tests:
  - Unit test prescan with known inputs: simple bug fix -> low complexity; multi-file migration -> high complexity
  - Test output shape matches expected dict structure
  - Integration test: webhook in triage mode populates `triage_enrichment` on the created TaskPacket

**Estimation reasoning:** The prescan function itself is straightforward heuristics (keyword matching, label checking). The integration with the webhook handler is a small addition (call prescan, store result). 6 hours covers the heuristic design (requires some thought about what keywords indicate complexity), implementation, webhook integration, and tests.

**Unknowns:**
- Prescan accuracy: the heuristics will be rough. This is acceptable for MVP -- the full Context stage runs after accept. The prescan is only for card display.
- Whether to also run prescan on edit (re-scan with updated content). Defer to Sprint 2 -- for now, prescan runs once at creation.

**Done when:** `prescan_issue()` returns correct shape for test inputs. Webhook in triage mode populates `triage_enrichment`. Unit and integration tests pass.

---

### Sprint 1 Capacity Summary

| Story | Estimate | Day | Cumulative | Ralph Loops |
|-------|----------|-----|------------|-------------|
| 36.1 TRIAGE Status | 3.0h | Day 1 | 3.0h | 1 |
| 36.2 Webhook Triage Mode | 5.0h | Day 1-2 | 8.0h | 1-2 |
| 36.3 Triage Action Endpoints | 8.0h | Day 2-4 | 16.0h | 2 |
| 36.4 Context Pre-Scan | 6.0h | Day 4-5 | 22.0h | 1-2 |
| **Total** | **22.0h** | | **73% of 30h** | |
| **Buffer** | **8.0h** | | **27%** | |

**Allocation rationale:** 73% allocation with 27% buffer. Justified because:
- Story 36.3 has two design decisions (issue metadata storage, rejection reason storage) that could go multiple ways
- The webhook handler modification (36.2) touches a critical path component -- extra care and testing required
- Database migrations (36.1) for PostgreSQL enum changes have historically needed debugging
- Buffer absorbs any discovery of additional columns needed for the PATCH endpoint

### Sprint 1 Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Issue metadata not on TaskPacketRow:** `issue_title` and `issue_body` are passed to Temporal but not stored on the TaskPacket. The triage queue needs them for card display and editing. | Confirmed | High (blocks 36.3 + 36.5) | Add `issue_title` and `issue_body` columns to TaskPacketRow in the 36.1 migration. This adds scope to 36.1 but prevents a second migration later. |
| 2 | **PostgreSQL enum migration:** Adding a value to an existing enum type in PostgreSQL has syntax constraints (cannot be done inside a transaction in PG < 12). | Low | Medium (migration fails) | PG 16 in compose supports transactional enum changes. Test migration on dev stack before merging. |
| 3 | **CRUD `create()` hardcodes RECEIVED:** The `create()` function uses `INSERT ... ON CONFLICT DO NOTHING` with `status=TaskPacketStatus.RECEIVED`. Parameterizing status could interact with the dedupe logic. | Medium | Medium (triage creation broken) | Review the on_conflict clause -- it targets `(delivery_id, repo)` not status, so parameterizing status is safe. Add test for duplicate handling in triage mode. |
| 4 | **Workflow trigger from accept endpoint:** The accept endpoint must call `start_workflow()` with the same parameters the webhook handler uses. If issue_title/issue_body are not on the TaskPacket, the accept endpoint cannot reconstruct the `PipelineInput`. | Confirmed | High (accept is broken) | Depends on Risk #1 resolution. With issue metadata on TaskPacketRow, accept can read it back. |

### Sprint 1 Compressible Stories

1. **Story 36.4 (Context Pre-Scan) -- first to defer.** The three core endpoints (36.1-36.3) deliver the full triage workflow without enrichment data on cards. Pre-scan adds polish (complexity hints) but is not functionally required. Deferring it to Sprint 2 means triage cards show issue metadata only, no complexity hint. **Impact:** Cards lack cost/complexity estimates but remain functional.

2. **Story 36.3 PATCH endpoint scope can compress** by storing edits in the `triage_enrichment` JSON field instead of adding dedicated columns. This saves migration work but makes querying edits harder. Acceptable for MVP since only one user.

---

## Sprint 2: Triage Frontend + SSE (Stories 36.5-36.6)

**Sprint Duration:** 1 week (2026-03-31 to 2026-04-04)
**Capacity:** 30 hours total, 77% allocation = 23 hours, 7 hours buffer
**Depends on:** Sprint 1 complete (all backend endpoints available)

### Sprint Goal (Testable Format)

**Objective:** Build the triage queue frontend that renders incoming issues as cards with action buttons, and wire real-time updates via SSE so the queue refreshes without polling.

**Test:** After both stories are complete:

1. `npm test -- --watchAll=false` (frontend test suite) passes -- TriageQueue component renders cards from mock API data; Accept button calls `/accept` endpoint; Reject button opens reason dropdown then calls `/reject`; Edit button opens side panel; edited fields persist on save.
2. SSE connection receives `triage.task.created` event and a new card appears in the queue without page refresh.
3. SSE connection receives `triage.task.accepted` event and the card is removed from the queue.
4. `pytest tests/dashboard/test_planning_router.py` still passes (backend unchanged from Sprint 1).
5. Manual smoke test: start stack with `TRIAGE_MODE_ENABLED=true`, open dashboard at `/dashboard/`, see the triage tab, create an issue via webhook, see card appear, accept it, confirm it starts the pipeline.

**Constraint:** 5 working days. Frontend work in `frontend/src/components/planning/`. Backend SSE event emission in `src/dashboard/planning_router.py` and `src/ingress/webhook_handler.py`. No modifications to Temporal workflow. No intent review work.

---

### Ordered Work Items

#### Item 1: Story 36.5 -- Triage Queue Frontend Component

**Estimate:** 12 hours (L size, 2-3 Ralph loops)
**Rationale for sequence:** Must come before SSE events (36.6) because the SSE subscription needs a rendered queue to update.

**Key tasks:**
- Create `frontend/src/components/planning/TriageQueue.tsx`:
  - Fetches `GET /api/v1/dashboard/tasks?status=triage` on mount
  - Renders a scrollable card list
  - Empty state: "No issues awaiting triage" message
- Create `frontend/src/components/planning/TriageCard.tsx`:
  - Displays: issue number, title, age (relative time), labels (badges), reporter name, truncated description (first 200 chars), complexity/risk/cost from `triage_enrichment`
  - Three action buttons: "Accept & Plan" (green), "Edit" (blue outline), "Reject" (red outline)
- Create `frontend/src/components/planning/RejectDialog.tsx`:
  - Dropdown with 4 reason options: Duplicate, Out of Scope, Needs Info, Won't Fix
  - Confirm/Cancel buttons
  - Calls `POST /tasks/{id}/reject` with selected reason
- Create `frontend/src/components/planning/EditPanel.tsx`:
  - Slide-in side panel with editable fields: title (text input), description (textarea), category (dropdown), priority (dropdown)
  - Save calls `PATCH /tasks/{id}` with changed fields
  - "Save & Accept" button saves then calls accept
- Add Zustand store slice for triage state (tasks, loading, error)
- Add route in React Router for `/dashboard/triage`
- Write component tests with mocked API responses:
  - TriageQueue renders correct number of cards
  - Accept button calls API and removes card
  - Reject dialog shows reasons, submits selected reason
  - Edit panel opens, saves, closes

**Estimation reasoning:** This is the largest frontend story. Four components, a Zustand store slice, routing, and tests. The TriageCard component has the most visual complexity (badges, relative time, enrichment display). The EditPanel requires form state management. 12 hours covers component development (8h), store/routing wiring (2h), and tests (2h). This follows the pattern established in Phase 1 where each major component took 8-12 hours.

**Unknowns:**
- The existing React app structure (Phase 0/1) uses a specific routing and layout pattern. Need to verify how the triage tab integrates with the existing dashboard layout (HeaderBar, sidebar navigation).
- Whether the existing Zustand store (from Phase 1) has a pattern for API fetching or whether each component manages its own fetch.

**Done when:** Frontend test suite passes. Manual render check shows cards with all fields. Action buttons trigger correct API calls.

---

#### Item 2: Story 36.6 -- Triage SSE Events

**Estimate:** 6 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** After the queue renders (36.5), SSE events provide real-time updates. Without the queue, there is nothing to update.

**Key tasks:**
- Backend: Emit NATS events from:
  - `src/ingress/webhook_handler.py`: publish `triage.task.created` after creating a TRIAGE TaskPacket (includes task_id, title, labels)
  - `src/dashboard/planning_router.py`: publish `triage.task.accepted` after accept (includes task_id)
  - `src/dashboard/planning_router.py`: publish `triage.task.rejected` after reject (includes task_id, reason)
- Use the existing NATS publish pattern from Phase 1 SSE bridge (`src/dashboard/events.py`)
- Frontend: Subscribe to these events in TriageQueue component via existing SSE connection
  - `triage.task.created` -> add card to list
  - `triage.task.accepted` -> remove card with animation
  - `triage.task.rejected` -> remove card with animation
- Write tests:
  - Backend: verify events are published to NATS with correct shape (subject, payload)
  - Frontend: mock SSE events trigger correct store updates

**Estimation reasoning:** The SSE bridge infrastructure exists from Phase 0 (Epic 34). NATS publishing is a known pattern. The frontend SSE subscription is also established. This story is glue work connecting existing infrastructure. 6 hours covers backend event emission (2h), frontend subscription (2h), and tests (2h).

**Unknowns:**
- NATS subject naming convention. Phase 1 uses `pipeline.*` subjects. Triage events should use `triage.*` or `planning.triage.*`. Align with existing convention.

**Done when:** Creating a webhook issue with triage mode on causes a card to appear in the open queue without refresh. Accepting a card removes it in real-time.

---

### Sprint 2 Capacity Summary

| Story | Estimate | Day | Cumulative | Ralph Loops |
|-------|----------|-----|------------|-------------|
| 36.5 Triage Queue Frontend | 12.0h | Day 1-3 | 12.0h | 2-3 |
| 36.6 Triage SSE Events | 6.0h | Day 3-4 | 18.0h | 1-2 |
| **Total** | **18.0h** | | **60% of 30h** | |
| **Buffer** | **12.0h** | | **40%** | |

**Allocation rationale:** 60% allocation with 40% buffer. This is intentionally generous because:
- Frontend estimation has higher variance than backend -- CSS layout issues, component testing setup, and React state management often take longer than expected
- This is the first major frontend sprint for this developer in the planning experience -- learning the established patterns from Phase 0/1 takes time
- The generous buffer also absorbs any Sprint 1 overflow (stories that did not complete in Sprint 1 carry forward here)
- If Sprint 1 completes cleanly with no overflow, the buffer can be used to start Sprint 3 stories early

### Sprint 2 Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Sprint 1 overflow:** If 36.3 or 36.4 carries over, Sprint 2 loses capacity. | Medium | Medium (frontend delayed) | 40% buffer absorbs 1 carried story. If both carry, defer 36.6 (SSE) and ship queue with polling. |
| 2 | **React component testing setup:** Phase 1 components have tests but the testing patterns (mocking API, testing Zustand stores) may not be documented. | Medium | Low (time lost to setup) | Read existing test files first. Adopt same patterns. |
| 3 | **SSE bridge event format mismatch:** If triage events use a different shape than Phase 1 events, the frontend SSE handler needs adaptation. | Low | Low (small code change) | Use same event shape as Phase 1 pipeline events. |

### Sprint 2 Compressible Stories

1. **Story 36.6 (Triage SSE Events) -- first to defer.** The queue works with polling (fetch on mount + periodic refetch). SSE adds polish (real-time updates). Deferring means the queue requires a page refresh to see new issues. Acceptable for a single-user MVP. **Impact:** Queue works but is not real-time.

---

## Sprint 3: Intent Review Backend (Stories 36.7, 36.7a, 36.8-36.10)

**Sprint Duration:** 1 week (2026-04-07 to 2026-04-11)
**Capacity:** 30 hours total, 77% allocation = 23 hours, 7 hours buffer
**Depends on:** Sprint 1 complete (TRIAGE status + triage endpoints). Sprint 2 does not block Sprint 3 -- backend can proceed without frontend.

### Sprint Goal (Testable Format)

**Objective:** Add a feature-flagged intent review wait point to the Temporal workflow. After the Intent Builder produces a spec, the workflow pauses until the developer approves, edits, or rejects via the dashboard API. Intent editing creates new versions with `source: developer`. Refinement creates versions with `source: refinement`. The version cap is raised to support developer editing loops.

**Test:** After all five stories are complete:

1. `pytest tests/intent/test_intent_spec.py` passes -- `IntentSpecRow` has `source` column; default is `auto`; `create_intent()` accepts and stores `source`; `get_all_versions()` returns source for each version.
2. `pytest tests/intent/test_refinement.py` passes -- `MAX_INTENT_VERSIONS` is 10; developer can create 5+ versions without `RefinementCapExceededError`; `RefinementTrigger(source="developer", ...)` is accepted.
3. `pytest tests/workflow/test_pipeline.py` passes -- workflow pauses after intent stage when `INTENT_REVIEW_ENABLED=true`; `approve_intent` signal resumes workflow to Router; `reject_intent` signal terminates workflow; workflow proceeds directly to Router when flag is false (default).
4. `pytest tests/dashboard/test_planning_router.py` passes -- `GET .../intent` returns spec + version history with source; `POST .../intent/approve` sends signal; `POST .../intent/reject` sends signal; `PUT .../intent` creates new version with `source=developer`; `POST .../intent/refine` constructs `RefinementTrigger` and creates new version with `source=refinement`.
5. All existing tests pass (`pytest` green, `ruff check .` clean).
6. Temporal workflow test: start workflow with `INTENT_REVIEW_ENABLED=true`, verify workflow is in waiting state after intent activity, send `approve_intent` signal, verify workflow continues to Router.

**Constraint:** 5 working days. Changes are confined to: `src/intent/intent_spec.py`, `src/intent/intent_crud.py`, `src/intent/refinement.py`, `src/workflow/pipeline.py`, `src/dashboard/planning_router.py`, `src/settings.py`, and corresponding test files + migration. No frontend work. Existing Temporal signals (`approve_publish`, `reject_publish`, `readiness_cleared`) are not modified.

---

### What's In / What's Out

**In this sprint (5 stories, ~23 estimated hours):**
- Story 36.7: Add `source` column to IntentSpecRow
- Story 36.7a: Raise MAX_INTENT_VERSIONS cap
- Story 36.8: Temporal workflow wait point after Intent stage
- Story 36.9: Intent review API endpoints (GET, approve, reject)
- Story 36.10: Intent edit and refinement endpoints (PUT, refine)

**Out of scope:**
- Frontend components (Sprint 4)
- Routing review wait point (Slice 3, future epic sprint)
- Any modification to existing Temporal signals
- SSE events for intent status changes (deferred -- can use polling initially)

---

### Dependency Review

#### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| `IntentSpecRow` at `src/intent/intent_spec.py` | Available | Cannot add source column | Confirmed: existing table with 7 columns, no `source` column |
| `IntentSpecCreate` / `IntentSpecRead` Pydantic models | Available | Cannot pass source through CRUD | Confirmed: both at `src/intent/intent_spec.py`, need `source` field added |
| `create_intent()` at `src/intent/intent_crud.py` | Available | Cannot create versioned specs with source | Confirmed: does not currently pass `source` (line 13) |
| `refine_intent()` at `src/intent/refinement.py` | Available | Cannot build refinement endpoint | Confirmed: accepts `RefinementTrigger` dataclass with `source`, `questions`, `triggering_defects`, `triggering_conflict` |
| `approve_publish` signal pattern in `pipeline.py` | Available (template) | Cannot model new wait point | Confirmed: lines 254-269 show signal handler + `workflow.wait_condition` pattern |
| Temporal SDK `workflow.signal` / `workflow.wait_condition` | Available | Cannot implement wait point | Confirmed: used by existing signals |

#### Internal Dependencies (Story-to-Story)

```
36.7  --> 36.9
36.7a --> 36.10
36.8  --> 36.9
```

- **36.7 has no dependencies** -- pure schema change (add source column). Must be first.
- **36.7a has no dependencies** -- standalone constant change. Can run in parallel with 36.7.
- **36.8 depends on neither** -- workflow change is independent of schema change, but 36.9 (which sends signals) depends on 36.8 (which adds signal handlers).
- **36.9 depends on 36.7 + 36.8** -- GET endpoint needs source column; approve/reject endpoints need signal handlers.
- **36.10 depends on 36.7 + 36.7a** -- edit creates new version with source; refine needs raised cap.

**Critical path:** 36.7 --> 36.9 (with 36.8 also feeding 36.9). Start 36.7, 36.7a, and 36.8 in parallel on Day 1.

---

### Ordered Work Items

#### Item 1: Story 36.7 -- Add `source` Column to IntentSpecRow

**Estimate:** 4 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** Foundation for version tracking. Every intent-related endpoint needs source.

**Key tasks:**
- Add `source: Mapped[str] = mapped_column(String(20), nullable=False, default="auto", server_default="auto")` to `IntentSpecRow`
- Add `source: str = "auto"` to `IntentSpecCreate` and `IntentSpecRead`
- Update `create_intent()` in `intent_crud.py` to pass `source=data.source`
- Create Alembic migration: `src/db/migrations/NNN_add_intent_source_column.py`
  - Add `source` column with default `auto` (backfills existing rows)
- Write tests:
  - Creating an IntentSpec without explicit source defaults to `auto`
  - Creating with `source="developer"` stores correctly
  - `get_all_versions()` includes source field in each version
  - Existing tests still pass (backward compatible due to default)

**Estimation reasoning:** Straightforward column addition with default value. Similar pattern to the `source_name` column on TaskPacketRow (Epic 27). Migration is simple. Tests are focused. 4 hours is conservative -- could be 3.

**Done when:** IntentSpec has source column. Default is `auto`. CRUD passes source through. Migration runs cleanly.

---

#### Item 2: Story 36.7a -- Raise MAX_INTENT_VERSIONS Cap

**Estimate:** 2 hours (S size, 1 Ralph loop)
**Rationale for sequence:** Quick, independent change. Unblocks 36.10 (refinement endpoint which creates multiple versions).

**Key tasks:**
- Change `MAX_INTENT_VERSIONS = 2` to `MAX_INTENT_VERSIONS = 10` in `src/intent/refinement.py`
- Optionally: add `max_intent_versions: int = 10` to Settings for configurability
- Update existing tests that assert on the cap value
- Add test: create 5 versions for a single TaskPacket without `RefinementCapExceededError`
- Add test: version 11 still raises `RefinementCapExceededError`

**Estimation reasoning:** One-line constant change plus test updates. 2 hours is generous but accounts for reviewing all test references to the old cap value.

**Done when:** 5+ versions can be created. Cap at 10 still enforced. Existing refinement tests pass.

---

#### Item 3: Story 36.8 -- Temporal Workflow Wait Point After Intent Stage

**Estimate:** 8 hours (M-L size, 2 Ralph loops)
**Rationale for sequence:** Most complex story in Sprint 3. The workflow modification is architecturally significant -- it introduces the second developer-facing wait point (after `approve_publish`). Must be done before 36.9 (API endpoints that send signals to this wait point).

**Key tasks:**
- Add `intent_review_enabled: bool = False` to Settings (env var: `THESTUDIO_INTENT_REVIEW_ENABLED`)
- Add signal handlers to `TheStudioPipelineWorkflow`:
  ```python
  @workflow.signal
  async def approve_intent(self, approved_by: str) -> None:
      self._intent_approved = True
      self._intent_approved_by = approved_by

  @workflow.signal
  async def reject_intent(self, rejected_by: str, reason: str) -> None:
      self._intent_rejected = True
      self._intent_rejected_by = rejected_by
      self._intent_rejection_reason = reason
  ```
- Add `WorkflowStep.AWAITING_INTENT_REVIEW = "awaiting_intent_review"` to enum
- Add `StepPolicy` for `AWAITING_INTENT_REVIEW` (no timeout -- developer must act; or very long timeout like 30 days as safety net)
- Insert wait point in `run()` method after step 3 (Intent Building), before step 4 (Expert Routing):
  ```python
  # Step 3.5: Intent Review (feature-flagged)
  if params.intent_review_enabled:
      output.step_reached = WorkflowStep.AWAITING_INTENT_REVIEW
      await workflow.wait_condition(
          lambda: self._intent_approved or self._intent_rejected,
      )
      if self._intent_rejected:
          output.rejection_reason = f"Intent rejected: {self._intent_rejection_reason}"
          return output
  ```
- Add `intent_review_enabled: bool = False` to `PipelineInput` dataclass
- Add `intent_approved_by: str | None = None` to `PipelineOutput` dataclass
- Modify `start_workflow()` to pass `intent_review_enabled` from settings
- Write workflow tests:
  - Test workflow pauses at intent review when enabled
  - Test `approve_intent` signal resumes workflow to Router
  - Test `reject_intent` signal terminates workflow with reason
  - Test workflow skips wait point when `intent_review_enabled=false` (default)
  - Test signal is idempotent (sending approve twice is harmless)
  - Test no timeout (workflow waits indefinitely for developer action)

**Estimation reasoning:** This follows the exact pattern of the `approve_publish` wait point (lines 254-270, 638-742 in pipeline.py), but with key differences: (1) it is between two activities rather than at the end, (2) it has no timeout (intentional -- developer must act), (3) it is feature-flagged. The workflow test infrastructure exists from prior epics. 8 hours covers: signal handlers (1h), wait point insertion (2h), `PipelineInput`/`PipelineOutput` updates (1h), comprehensive workflow tests (3h), and buffer for debugging Temporal signal behavior in tests (1h).

**Unknowns:**
- **Decision: 30-day safety timeout with escalation (not auto-approve).** The existing `approve_publish` has a 7-day timeout. The intent review wait point uses a 30-day safety timeout that emits an escalation event (`pipeline.intent_review.timeout`) and transitions the TaskPacket to `NEEDS_ATTENTION` — it does NOT auto-approve. This prevents orphaned workflows while respecting the epic's "no auto-approve timeout" requirement. 30 days is long enough that hitting it indicates a genuinely abandoned workflow, not a busy week.
- **SSE event emission:** When the workflow enters the intent review wait state, an SSE event should notify the dashboard. This is handled by the existing `update_project_status_activity` pattern or a new activity. Deferring the SSE event to Sprint 4 or handling it here depends on whether the dashboard frontend needs it immediately (it does not -- Sprint 4 is frontend).

**Done when:** Workflow tests pass. Signal handlers work. Feature flag controls behavior. Default is disabled. Existing workflow tests pass unchanged.

---

#### Item 4: Story 36.9 -- Intent Review API Endpoints (GET, Approve, Reject)

**Estimate:** 5 hours (M size, 1-2 Ralph loops)
**Rationale for sequence:** Depends on 36.7 (source column for GET response) and 36.8 (signal handlers for approve/reject). API layer connecting the frontend to the workflow.

**Key tasks:**
- Add to `src/dashboard/planning_router.py`:
  - `GET /tasks/{task_id}/intent`:
    - Calls `get_all_versions(session, taskpacket_id)` to return version history
    - Calls `get_latest_for_taskpacket(session, taskpacket_id)` for current version
    - Returns: `{current: IntentSpecRead, versions: list[IntentSpecRead]}`
    - Returns 404 if no intent exists for this task
  - `POST /tasks/{task_id}/intent/approve`:
    - Validates TaskPacket is in `INTENT_BUILT` status
    - Sends `approve_intent` Temporal signal via workflow handle
    - Returns 200 with `{status: "approved"}`
    - Returns 409 if TaskPacket is not in `INTENT_BUILT` status
  - `POST /tasks/{task_id}/intent/reject`:
    - Requires `reason: str` in request body
    - Validates TaskPacket is in `INTENT_BUILT` status
    - Sends `reject_intent` Temporal signal via workflow handle
    - Returns 200 with `{status: "rejected"}`
    - Returns 409 if TaskPacket is not in `INTENT_BUILT` status
- Pydantic response models for intent review
- Write API tests:
  - GET returns spec with source field and version list
  - Approve sends signal, 409 on wrong status
  - Reject sends signal with reason, 409 on wrong status
  - 404 when no intent exists

**Estimation reasoning:** Three endpoints with straightforward logic. The Temporal signal sending follows the pattern from the existing approve endpoint (`src/dashboard/` or signal sending in webhook handler). The GET endpoint reuses existing `intent_crud` functions. 5 hours covers endpoint implementation (2h), Pydantic models (0.5h), tests (2h), and signal sending integration (0.5h).

**Unknowns:**
- **Temporal client access from dashboard router:** The webhook handler gets a Temporal client via `get_temporal_client()` in `src/ingress/workflow_trigger.py`. The dashboard router needs the same access. Should import the same function or add a shared utility.
- **Design note: Status semantics.** `INTENT_BUILT` status on the TaskPacket confirms the workflow is in the intent review wait state. No new status value is needed for the wait state — the workflow state (paused via `workflow.wait_condition`) and TaskPacket status (`INTENT_BUILT`) are distinct concepts. The API validates the TaskPacket status, not the Temporal workflow state directly.

**Done when:** All three endpoints work. Signal sending verified. Status validation enforced. Tests pass.

---

#### Item 5: Story 36.10 -- Intent Edit and Refinement Endpoints

**Estimate:** 4 hours (S-M size, 1 Ralph loop)
**Rationale for sequence:** Last in sequence because it depends on both 36.7 (source column) and 36.7a (raised version cap). These endpoints do not send signals -- they modify the spec while the workflow remains paused.

**Key tasks:**
- Add to `src/dashboard/planning_router.py`:
  - `PUT /tasks/{task_id}/intent`:
    - Accepts body: `{goal: str, constraints: list[str], acceptance_criteria: list[str], non_goals: list[str]}`
    - Validates TaskPacket is in `INTENT_BUILT` status
    - Gets latest version number via `get_latest_for_taskpacket()`
    - Calls `create_intent()` with `source="developer"`, `version=latest.version + 1`
    - Calls `update_intent_version()` to update TaskPacket pointer
    - Returns the new IntentSpecRead
  - `POST /tasks/{task_id}/intent/refine`:
    - Accepts body: `{feedback: str}`
    - Validates TaskPacket is in `INTENT_BUILT` status
    - Constructs `RefinementTrigger(source="developer", questions=[feedback])`
    - Calls `refine_intent(session, taskpacket_id, trigger)`
    - Returns the new IntentSpecRead
- Ensure `RefinementTrigger.source` accepts `"developer"` (currently documents `"qa_agent"` or `"assembler"` -- no runtime validation, so this should work without code changes)
- Write tests:
  - Edit: creates new version with source=developer, version increments, TaskPacket pointer updated
  - Refine: creates new version with source=refinement, RefinementTrigger constructed correctly
  - Both: 409 on wrong status
  - Version history grows after edit and refine

**Estimation reasoning:** Both endpoints are thin API layers over existing CRUD/refinement functions. The edit endpoint manually creates a new IntentSpec version (bypassing `refine_intent()` which adds refinement-specific constraints). The refine endpoint delegates to `refine_intent()`. 4 hours covers both endpoints (2h) and tests (2h).

**Unknowns:**
- **RefinementTrigger source validation:** The `RefinementTrigger.source` field is a plain `str` with no enum validation in the dataclass. Passing `"developer"` should work without code changes to `refinement.py`. Verify at implementation time.
- **Edit vs Refine distinction:** Edit replaces the spec fields entirely (developer provides all four fields). Refine appends to existing fields via `refine_intent()`. The frontend will present these as distinct actions.

**Done when:** Edit creates new version with `source=developer`. Refine creates new version with `source=refinement`. Version cap of 10 is not hit in normal usage. Tests pass.

---

### Sprint 3 Capacity Summary

| Story | Estimate | Day | Cumulative | Ralph Loops |
|-------|----------|-----|------------|-------------|
| 36.7 Intent Source Column | 4.0h | Day 1 | 4.0h | 1 |
| 36.7a Raise Version Cap | 2.0h | Day 1 | 6.0h | 1 |
| 36.8 Temporal Wait Point | 8.0h | Day 1-3 | 14.0h | 2 |
| 36.9 Intent API Endpoints | 5.0h | Day 3-4 | 19.0h | 1-2 |
| 36.10 Edit + Refine Endpoints | 4.0h | Day 4-5 | 23.0h | 1 |
| **Total** | **23.0h** | | **77% of 30h** | |
| **Buffer** | **7.0h** | | **23%** | |

**Allocation rationale:** 77% allocation with 23% buffer. Standard allocation. The Temporal wait point (36.8) is the riskiest story -- it modifies a critical-path workflow definition. Buffer absorbs debugging time if signal handling does not work as expected. The other four stories are well-understood schema/API changes.

### Sprint 3 Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Temporal workflow modification breaks existing tests.** Adding signal handlers and a wait point to `TheStudioPipelineWorkflow` could affect the 20+ existing workflow test cases. | Medium | High (regression) | Feature-flag the wait point (default off). Run full workflow test suite after each change. The wait point is a no-op when disabled, so existing tests should pass unchanged. |
| 2 | **Signal ordering edge case.** If `approve_intent` signal arrives before the workflow reaches the wait point (race condition), the signal is queued by Temporal. But if the wait condition checks `self._intent_approved` and it was set before the wait, the workflow skips the wait immediately. This is the desired behavior but must be tested. | Low | Medium (workflow hangs or skips) | Temporal signals are durable and replayed. Test both orderings: signal-before-wait and signal-after-wait. |
| 3 | **Refinement endpoint creates unexpected constraint text.** `refine_intent()` appends `[Refinement v{N}] {question}` to constraints. Developer feedback like "make it clearer" becomes a constraint. This may confuse the downstream Router/Assembler. | Low | Low (cosmetic) | Document this behavior. The developer can edit the spec after refinement to clean up constraints. |
| 4 | **Sprint 2 overflow.** If frontend stories carry over, they do NOT block Sprint 3 (backend-only). But developer context switching between frontend and backend work reduces velocity. | Medium | Low (slightly slower) | Sprint 3 is entirely backend. Park any unfinished frontend work and pick it up after Sprint 3. |

### Sprint 3 Compressible Stories

1. **Story 36.10 (Edit + Refine Endpoints) -- first to defer.** The core intent review flow (GET + approve + reject from 36.9) works without editing. The developer can approve or reject but not modify the spec. Editing is a power-user feature that can ship in a follow-up. **Impact:** Developer can review and approve/reject intent specs but cannot edit them from the dashboard. They would need to reject and re-submit the issue.

2. **Story 36.7a (Raise Version Cap) -- second to defer if 36.10 is also deferred.** If editing is deferred, the version cap of 2 is sufficient for the approve/reject-only flow (auto v1 + optional single refinement). **Impact:** No multi-version editing, which is already deferred.

---

## Sprint 4: Intent Review Frontend (Stories 36.11a-36.11g)

> **Decomposition:** Stories 36.11 and 36.12 were right-sized on 2026-03-21 into 7
> Ralph-executable sub-stories (36.11a through 36.11g). See
> `docs/epics/epic-36-sprint4-story-decomposition.md` for full specifications
> including per-story deliverables, acceptance criteria, dependencies, and
> implementation details.

**Sprint Duration:** 1 week (2026-04-14 to 2026-04-18)
**Capacity:** 30 hours total, 73% allocation = 22 hours, 8 hours buffer
**Depends on:** Sprint 3 complete (all intent review endpoints available)

### Sprint Goal (Testable Format)

**Objective:** Build the intent editor UI with split-pane view (source context on left, structured spec on right), action buttons (approve, edit, refine, reject), edit mode with structured form, refinement modal, and version history with diff view.

**Test:** After both stories are complete:

1. `npm test -- --watchAll=false` (frontend test suite) passes -- IntentEditor renders split pane; SourceContext shows issue body and enrichment; IntentSpec renders structured sections (goal, constraints, ACs, non-goals); action buttons call correct endpoints.
2. Edit mode: clicking "Edit" switches right panel to structured form; saving calls `PUT` with correct JSON shape; new version appears in version selector.
3. Refinement: clicking "Request Refinement" opens modal with feedback textarea; submitting calls `POST /refine`; new version renders in right panel.
4. Version selector: dropdown shows all versions with source label and timestamp; selecting a version re-renders the right panel; diff view highlights changes between any two selected versions.
5. Manual smoke test: navigate to a task in `INTENT_BUILT` status, see split pane with source context and intent spec, click Approve, confirm workflow resumes to Router stage.

**Constraint:** 5 working days. Frontend work in `frontend/src/components/planning/`. No backend changes. All endpoints exist from Sprint 3.

---

### Ordered Work Items

#### Item 1: Story 36.11 -- Intent Editor Frontend -- Split-Pane View

**Estimate:** 12 hours (L size, 2-3 Ralph loops)
**Rationale for sequence:** The view/read mode must exist before edit mode (36.12) can toggle into it.

**Key tasks:**
- Create `frontend/src/components/planning/IntentEditor.tsx`:
  - Split-pane layout: left panel (40%), right panel (60%)
  - Fetches `GET /tasks/{id}/intent` on mount
  - Four action buttons in a toolbar: "Approve & Continue" (green), "Edit" (blue), "Request Refinement" (yellow), "Reject" (red)
  - Approve calls `POST /intent/approve`
  - Reject opens a confirmation dialog with reason text input, calls `POST /intent/reject`
- Create `frontend/src/components/planning/SourceContext.tsx`:
  - Left panel (read-only):
    - Issue body rendered as Markdown (use existing Markdown renderer if available, or `react-markdown`)
    - Context enrichment: affected files list, complexity score bar, risk flags as checkmarks
    - Data from TaskPacket's `scope`, `risk_flags`, `complexity_index` fields
- Create `frontend/src/components/planning/IntentSpec.tsx`:
  - Right panel (read mode):
    - Goal: rendered as text block with heading
    - Constraints: rendered as bullet list
    - Acceptance Criteria: rendered as numbered/checklist items
    - Non-Goals: rendered as bullet list with strikethrough styling
    - Source badge: "Auto" / "Developer" / "Refinement" with color
    - Created timestamp
- Create `frontend/src/components/planning/VersionSelector.tsx`:
  - Dropdown at bottom of right panel
  - Shows: "v{N} -- {source} -- {timestamp}" for each version
  - Selecting a version re-fetches and re-renders the IntentSpec panel
- Add Zustand store slice for intent state
- Add route: `/dashboard/tasks/{id}/intent`
- Write component tests:
  - Split pane renders both panels
  - SourceContext shows issue body and enrichment data
  - IntentSpec renders all four sections
  - Version selector shows correct version count
  - Approve button calls API
  - Reject button shows dialog

**Estimation reasoning:** Largest frontend story. Split-pane layout, multiple sub-components, Markdown rendering, and version selection. The SourceContext component requires rendering enrichment data from multiple TaskPacket fields. 12 hours: layout + components (7h), Zustand store (1h), routing (0.5h), tests (3h), Markdown rendering setup (0.5h).

**Unknowns:**
- **Markdown rendering library:** The epic says "textarea with Markdown preview toggle, not a rich editor." For the read-only source context panel, `react-markdown` is lightweight. Check if Phase 1 already includes a Markdown dependency.
- **Enrichment data availability:** The source context panel needs `scope`, `risk_flags`, and `complexity_index` from the TaskPacket. These are populated by the Context stage (step 2), which runs before Intent (step 3). So by the time the developer sees the intent review screen, this data exists.

**Done when:** Split pane renders. Source context shows issue body. Intent spec shows all four structured sections. Version selector works. Action buttons call correct endpoints. Tests pass.

---

#### Item 2: Story 36.12 -- Intent Editor Frontend -- Edit Mode and Refinement

**Estimate:** 10 hours (L size, 2-3 Ralph loops)
**Rationale for sequence:** Depends on 36.11 (the view mode that edit mode toggles from).

**Key tasks:**
- Create `frontend/src/components/planning/IntentEditMode.tsx`:
  - Replaces right panel when "Edit" is clicked
  - Structured form with:
    - Goal: textarea
    - Constraints: editable list (each item is a text input with remove button; "Add constraint" button at bottom)
    - Acceptance Criteria: editable list (same pattern)
    - Non-Goals: editable list (same pattern)
  - "Save" button calls `PUT /tasks/{id}/intent` with `{goal, constraints, acceptance_criteria, non_goals}`
  - "Cancel" button returns to read mode without saving
  - After save: re-fetch versions, display new version in read mode
- Create `frontend/src/components/planning/RefinementModal.tsx`:
  - Modal dialog triggered by "Request Refinement" button
  - Textarea for feedback text (required, min 10 characters)
  - "Submit" calls `POST /tasks/{id}/intent/refine` with `{feedback: text}`
  - After submit: close modal, re-fetch versions, display new version
  - "Cancel" closes modal
- Create `frontend/src/components/planning/VersionDiff.tsx`:
  - Triggered by "Compare versions" button or selecting two versions
  - Side-by-side or inline diff of two IntentSpec versions
  - Highlights: added/removed constraints, changed goal text, added/removed ACs
  - Uses field-level comparison (not text diff): iterate constraints arrays, mark additions/removals
- Write component tests:
  - Edit mode renders form with current values pre-filled
  - Adding/removing list items works
  - Save sends correct JSON shape
  - Cancel returns to read mode without API call
  - Refinement modal validates min length
  - Refinement submits and refreshes
  - Diff view highlights changes between two versions

**Estimation reasoning:** Three components with interactive state. The editable list pattern (add/remove items) requires careful form state management. The diff view is the most complex -- comparing structured fields (arrays of strings) requires custom logic, not a generic text diff. 10 hours: edit form + list management (4h), refinement modal (2h), diff view (2.5h), tests (1.5h).

**Unknowns:**
- **Editable list UX:** Adding and removing items from a list of text inputs is a common pattern but has edge cases (empty items, reordering). Keep it simple: no reordering, no drag-and-drop. Just add at bottom, remove with X button.
- **Diff algorithm for structured fields:** For arrays (constraints, ACs, non-goals), use simple set-difference logic: items in v2 not in v1 are "added" (green), items in v1 not in v2 are "removed" (red). For the goal string, use a simple "changed" indicator if text differs.

**Done when:** Edit mode works end-to-end (edit, save, see new version). Refinement modal submits and new version appears. Diff view shows changes between any two versions. Tests pass.

---

### Sprint 4 Capacity Summary (Decomposed)

| Story | Title | Size | Est. | Day | Ralph Loops |
|-------|-------|------|------|-----|-------------|
| 36.11a | API Types + Functions | S | 2.0h | Day 1 | 1 |
| 36.11b | Intent Zustand Store | S | 2.0h | Day 1 | 1 |
| 36.11c | SourceContext + IntentSpec Display | M | 4.0h | Day 1-2 | 1 |
| 36.11d | IntentEditor Container + Routing | M | 4.0h | Day 2 | 1 |
| 36.11e | Edit Mode Form | M | 4.0h | Day 3 | 1 |
| 36.11f | Refinement Modal | S | 3.0h | Day 3 | 1 |
| 36.11g | Version Diff + All Tests | M | 3.0h | Day 4 | 1 |
| **Total** | | | **22.0h** | | **7** |
| **Buffer** | | | **8.0h (Day 5)** | | |

**Allocation rationale:** 73% allocation with 27% buffer (unchanged from original). Decomposition reduces risk: each sub-story is 1 Ralph loop (3-6h) with clear boundaries. 36.11b and 36.11c can be parallelized (Day 1). 36.11e and 36.11f can be parallelized (Day 3). The diff view (36.11g) remains the biggest unknown but is now isolated and deferrable.

### Sprint 4 Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Split pane layout issues on different screen sizes.** The epic specifies minimum 1024px viewport. Responsive behavior below that may cause layout breaks. | Medium | Low (cosmetic) | Set `min-width: 1024px` on the container. Stack panes vertically below 1024px as specified in constraints. |
| 2 | **Version diff complexity.** Field-level diffing of arrays with partially matching strings is harder than simple set difference. If a constraint is edited (not added/removed), matching becomes fuzzy. | Medium | Medium (diff is wrong) | For MVP, treat any text change as "removed old + added new." Exact-match comparison only. Fuzzy matching deferred. Isolated in 36.11g so it cannot block other stories. |
| 3 | **Sprint 3 overflow.** If the Temporal wait point story (36.8) carries over, Sprint 4 cannot test approve/reject integration. | Low | High (frontend cannot demo) | The frontend can be built against mocked API responses. Integration testing happens when Sprint 3 completes, which may extend Sprint 4 by a day. |
| 4 | **No react-markdown dependency.** `react-markdown` is not installed. | Low | Low (resolved) | Story 36.11c renders issue body as plain preformatted text. Markdown rendering deferred to a follow-up story if needed. |

### Sprint 4 Compressible Stories (Updated)

1. **36.11g VersionDiff + tests** -- first to defer. Diff view is nice-to-have. Tests for 36.11a-36.11f can be written inline or deferred to a dedicated test story. **Impact:** No visual diff between versions; version selector still works for manual comparison.

2. **36.11f Refinement Modal** -- second to defer. Developer can manually edit the spec (36.11e) instead of requesting AI refinement. **Impact:** No AI-assisted refinement from the dashboard.

3. **36.11e Edit Mode Form** -- third to defer (most aggressive). Read-only view with approve/reject (36.11a-36.11d) is the minimum viable intent review. **Impact:** Developer must reject and re-submit to change intent.

---

## Cross-Sprint Dependency Map

```
Sprint 1 (Backend)          Sprint 2 (Frontend)
36.1 TRIAGE Status -------> 36.5 Triage Queue UI
36.2 Webhook Triage -------> 36.5
36.3 Action Endpoints -----> 36.5
36.4 Pre-Scan -------------> 36.5 (enrichment data on cards)
                              36.6 SSE Events (both backend + frontend)

Sprint 3 (Backend)          Sprint 4 (Frontend, decomposed)
36.7 Source Column --------> 36.11a (types), 36.11c (IntentSpec display)
36.7a Version Cap ---------> 36.11e (Edit), 36.11f (Refine)
36.8 Workflow Wait Point --> 36.11d (approve/reject integration)
36.9 Intent API -----------> 36.11a (API functions)
36.10 Edit/Refine API -----> 36.11e (Edit form), 36.11f (Refine modal)
```

**Key observation:** Sprints 1 and 3 (backend) are independent of each other. Sprint 2 depends only on Sprint 1. Sprint 4 depends only on Sprint 3. This means:
- If Sprint 1 finishes early, Sprint 3 can start early (backend work is not blocked by frontend)
- If Sprint 2 overflows, Sprint 3 is not affected (backend can proceed)
- Sprint 4 cannot start until Sprint 3 completes (frontend needs backend endpoints)

---

## Aggregate Capacity Summary

| Sprint | Stories | Estimated | Capacity | Allocation | Buffer |
|--------|---------|-----------|----------|------------|--------|
| Sprint 1: Triage Backend | 36.1-36.4 | 22.0h | 30h | 73% | 8.0h (27%) |
| Sprint 2: Triage Frontend | 36.5-36.6 | 18.0h | 30h | 60% | 12.0h (40%) |
| Sprint 3: Intent Backend | 36.7-36.10 | 23.0h | 30h | 77% | 7.0h (23%) |
| Sprint 4: Intent Frontend | 36.11a-36.11g (7 sub-stories) | 22.0h | 30h | 73% | 8.0h (27%) |
| **Total MVP** | **18 stories (11 + 7 decomposed)** | **85.0h** | **120h** | **71%** | **35.0h (29%)** |

**Overall allocation:** 71% across 4 weeks with 29% buffer. This is appropriate for an MVP that:
- Introduces a new status to the core domain model (TRIAGE)
- Adds a new Temporal workflow wait point (intent review)
- Includes both backend API development and frontend component development
- Requires database migrations for two separate schema changes
- Has frontend estimation uncertainty (first planning UI sprint)

---

## Definition of Done (MVP Level)

- [ ] `TRIAGE` status exists in `TaskPacketStatus` enum with valid transitions
- [ ] `TRIAGE_MODE_ENABLED=true` causes webhooks to create TaskPackets in TRIAGE status
- [ ] `TRIAGE_MODE_ENABLED=false` (default) preserves all existing behavior
- [ ] Accept, reject, and edit endpoints work for TRIAGE TaskPackets
- [ ] Triage queue frontend renders cards and handles all three actions
- [ ] SSE events provide real-time triage queue updates
- [ ] `source` column exists on `IntentSpecRow` with values: auto, developer, refinement
- [ ] `MAX_INTENT_VERSIONS` raised to 10
- [ ] `INTENT_REVIEW_ENABLED=true` causes workflow to pause after Intent stage
- [ ] `INTENT_REVIEW_ENABLED=false` (default) preserves all existing behavior
- [ ] Approve, reject, edit, and refine endpoints work for intent review
- [ ] Intent editor frontend shows split-pane view with structured spec
- [ ] Edit mode creates new versions with `source: developer`
- [ ] Refinement creates new versions with `source: refinement`
- [ ] Version history is visible and navigable
- [ ] All existing tests pass (`pytest` green, `ruff check .` clean)
- [ ] Frontend test suite passes (`npm test -- --watchAll=false`)
- [ ] Manual smoke test: full triage -> accept -> intent review -> approve flow works end-to-end

---

## Key Implementation Notes

### Feature Flag Strategy

Both features use environment variables that default to `false`:
- `THESTUDIO_TRIAGE_MODE_ENABLED=false` -- triage mode
- `THESTUDIO_INTENT_REVIEW_ENABLED=false` -- intent review wait point

This ensures:
1. Existing behavior is completely preserved when flags are off
2. Features can be enabled independently (triage without intent review, or vice versa)
3. Instant rollback by setting flag to false

### Database Migration Strategy

Two migrations are needed:
1. Sprint 1: Add `triage` to `taskpacket_status` enum + add `triage_enrichment` column + add `issue_title`, `issue_body`, `rejection_reason` columns to TaskPacket
2. Sprint 3: Add `source` column to `intent_spec` table

Both are additive (no column drops, no enum removals). Both use defaults for backfill. Order matters: Sprint 1 migration must run before Sprint 3 migration.

### Temporal Signal Pattern

The new `approve_intent` / `reject_intent` signals follow the exact pattern of existing `approve_publish` / `reject_publish`:
- Signal handlers set boolean flags on the workflow instance
- `workflow.wait_condition()` blocks until a flag is set
- Signals are idempotent (setting True twice is harmless)
- The workflow checks which flag was set to determine next action

Difference from `approve_publish`: no timeout. The developer must act. A 30-day safety timeout is recommended to prevent orphaned workflows.

### Issue Metadata Storage Decision

**Decision:** Add `issue_title: Mapped[str | None]` and `issue_body: Mapped[str | None]` columns to `TaskPacketRow` in the Sprint 1 migration.

**Rationale:** The webhook handler currently passes these to `PipelineInput` (Temporal) but does not persist them on the TaskPacket. The triage queue needs them for card display. The intent review source context panel also needs them. Adding columns now avoids having to reconstruct them from Temporal workflow history later.

**Impact:** The webhook handler must populate these columns at creation time. The `create()` function in `taskpacket_crud.py` needs these parameters.

---

## Retro Reference

This is the first sprint plan for Epic 36. Key decisions informed by prior sprint retros:

- **73-77% allocation** (learned from Epic 30 Sprint 1: 77% was right for first-time integration work)
- **Backend before frontend** (learned from Epic 34: building APIs first prevents frontend work from being blocked by missing endpoints)
- **Feature flags default to false** (learned from Epic 16: feature-flagged changes eliminate regression risk)
- **Two compressible stories per sprint** (established pattern from Epic 30 Sprint 1)
- **Cross-sprint dependency map** (new addition -- four sprints need explicit dependency tracking)
- **Issue metadata storage decision** surfaced during dependency review (exactly the kind of discovery the 30-minute review is designed to catch)

---

## Meridian Review: PASS (2026-03-21)

**Reviewer:** Meridian (VP of Success)
**Verdict:** PASS — 2 wording fixes applied, plan approved for execution.

### 7 Questions Answered

| # | Question | Verdict | Answer |
|---|----------|---------|--------|
| 1 | Is 4-sprint alternating structure correct? | **PASS** | Backend-before-frontend is correct. Sprint 3 is independent of Sprint 2. Avoids context-switching within sprints. |
| 2 | Is issue_title/issue_body column addition correct? | **PASS** | Columns are needed for card display (Sprint 2), source context (Sprint 4), and accept endpoint (Sprint 1). Cleaner than JSON blob. |
| 3 | Is 30-day safety timeout appropriate? | **PASS** | Escalation (not auto-approve) is correct. 30 days is long enough for a solo developer. Promoted from Unknown to Decision. |
| 4 | Is Sprint 2's 60% allocation too generous? | **PASS** | First planning UI sprint has highest estimation uncertainty. 40% buffer absorbs Sprint 1 overflow. Insurance, not waste. |
| 5 | Should Story 36.8 be split? | **PASS (no split)** | Signal handlers and wait point are tightly coupled. Cannot be independently tested. 8h estimate is appropriate. |
| 6 | Is compression strategy correct? | **PASS** | Deferring 36.10 (edit/refine) is a good call — core experience is "review and decide," editing is a power-user feature. |
| 7 | Are cross-sprint dependencies complete? | **PASS** | Sprint 1→Sprint 3 dependency noted in Sprint 3 header. Sprint 4 depends only on Sprint 3. |

### Standard Plan Review

| # | Checklist Item | Verdict |
|---|---------------|---------|
| 1 | Order of work justified? | **PASS** |
| 2 | Sprint goals testable (objective + test + constraint)? | **PASS** |
| 3 | Dependencies visible and tracked? | **PASS** |
| 4 | Estimation reasoning recorded? | **PASS** |
| 5 | Unknowns surfaced and buffered? | **PASS** |
| 6 | Retro learnings applied? | **PASS** |
| 7 | Executable without daily stand-ups? | **PASS** |

### Fixes Applied

1. Story 36.8: Promoted 30-day timeout from "Unknown" to "Decision: 30-day safety timeout with escalation."
2. Story 36.9: Promoted status semantics from "Unknown" to "Design note" explaining TaskPacket status vs workflow state.

### Source Code Verification

All 14 plan claims verified against source code. One minor line number discrepancy (TaskPacketCreate at line 171, not 176) — cosmetic only.
