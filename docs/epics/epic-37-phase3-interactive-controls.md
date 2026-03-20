# Epic 37: Phase 3 -- Interactive Controls & Governance

> **Status:** Draft -- Awaiting Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 10-12 weeks (5 slices)
> **Created:** 2026-03-20
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**Developers Can Pause, Steer, Budget, and Trust-Configure the Pipeline Without Touching Code**

---

## 2. Narrative

TheStudio's pipeline runs autonomously. That is its strength and its liability. Today, if a TaskPacket enters the Implement stage and the developer realizes the wrong experts were selected, there is no "stop" button. If the pipeline burns through $30 on a runaway loopback, there is no budget brake. If the developer wants small, well-tested bug fixes to auto-merge but wants complex features to produce draft PRs for review, there is no way to express that policy. The only option is to wait, watch, and hope.

The pipeline has three trust tiers (Observe, Suggest, Execute) defined in the design but not yet configurable at the task level. The codebase has a separate concept -- expert-level reputation tiers (Shadow, Probation, Trusted) -- that governs expert selection. Both are needed, but today neither is visible or configurable through the UI. A developer who wants to gradually increase autonomy as trust builds has no lever to pull.

Meanwhile, cost data exists in `src/admin/model_spend.py` and `src/admin/model_gateway.py`, but it is trapped in the admin panel's server-rendered Jinja templates. There is no budget alerting, no automated pause-on-overspend, no per-stage or per-model breakdown in the dashboard, and no notification when something needs human attention.

This epic delivers the four control surfaces that transform TheStudio from "watch and hope" to "configure, steer, and govern":

1. **Pipeline Steering** -- Pause, resume, retry, redirect, and abort running TaskPackets through Temporal workflow signals.
2. **Trust Tier Configuration** -- A rule engine that evaluates task metadata (category, complexity, lines changed, cost, file paths) to assign Observe/Suggest/Execute tiers, with safety bounds and mandatory review patterns.
3. **Budget Dashboard** -- Real-time cost visibility with per-stage and per-model breakdowns, configurable alert thresholds, and automated actions (pause pipeline, downgrade models).
4. **Notifications** -- In-app notification system that alerts on gate failures, budget warnings, review requests, and drift.

This is the highest-risk phase in the UI initiative because it introduces Temporal signal handlers (pause/resume/redirect/abort) that directly alter workflow execution. A bug in a signal handler can orphan a workflow, corrupt state, or silently drop work. The slice ordering puts steering first specifically because the signal infrastructure is the foundation that budget-pause and other automated actions build on.

**Why now:** Phase 1 (pipeline visibility) and Phase 2 (planning experience) make the pipeline observable and plannable. Without Phase 3, the developer can see problems but cannot act on them. Steering controls are the bridge between visibility and control. Budget governance is non-negotiable before any production deployment -- the eval tests alone cost ~$5/run, and a pipeline processing real issues without budget limits is an open checkbook.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Interactive Controls Design Spec | `docs/design/03-INTERACTIVE-CONTROLS.md` |
| Backend Requirements (Phase 3 stories B-3.1 through B-3.24) | `docs/design/06-BACKEND-REQUIREMENTS.md` Section 3 |
| Pipeline UI Vision (Phase 3 scope) | `docs/design/00-PIPELINE-UI-VISION.md` Section 8 |
| Technology Architecture | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` |
| Trust tier reconciliation analysis | `docs/design/06-BACKEND-REQUIREMENTS.md` Section 6 |
| Existing Temporal signals (3 handlers) | `src/workflow/pipeline.py:254-277` |
| Existing expert reputation tiers | `src/reputation/tiers.py` (Shadow/Probation/Trusted) |
| Expert reputation engine | `src/reputation/engine.py` |
| TaskPacket status model | `src/models/taskpacket.py` |
| Cost tracking (ModelCallAudit, SpendReport) | `src/admin/model_spend.py`, `src/admin/model_gateway.py` |
| Pipeline budget enforcement | `src/agent/framework.py:66` (PipelineBudget class) |
| Existing cost dashboard templates | `src/admin/templates/cost_dashboard.html` |
| Budget utilization templates | `src/admin/templates/partials/budget_utilization_content.html` |
| SSE infrastructure (Phase 0 prerequisite) | `src/dashboard/` package (from Phase 0 epic) |
| Dashboard API router (Phase 0 prerequisite) | `/api/v1/dashboard/` (from Phase 0 epic) |
| NATS JetStream streams | `THESTUDIO_VERIFICATION`, `THESTUDIO_QA` |
| Competitive analysis (Factory AI, Aperant, Codegen) | `docs/design/00-PIPELINE-UI-VISION.md` Section 2 |
| OKR: Trust tier adoption | Developers increase trust tier within 2 weeks of use |
| OKR: Time-to-intervention | Developer can pause/redirect a pipeline in < 10 seconds |
| OKR: Cost awareness | Developer can predict cost within 30% before execution |

---

## 4. Acceptance Criteria

### AC 1: Pipeline Pause and Resume

A developer can pause a running TaskPacket from the dashboard UI. The Temporal workflow freezes at its current step -- no further activities execute. A "Resume" button appears, and clicking it continues the workflow from where it stopped. The pause/resume round-trip completes within 5 seconds of the button click. Paused TaskPackets display a distinct visual state (paused badge + grayed timeline).

### AC 2: Pipeline Abort

A developer can abort a running TaskPacket. Abort requires a confirmation dialog with a mandatory reason text input. The Temporal workflow terminates. The abort reason, timestamp, and actor are persisted in an audit log. Aborted TaskPackets display a terminal "Aborted" state and cannot be resumed.

### AC 3: Pipeline Retry and Redirect

A developer can retry the current or last-failed stage (re-runs from stage start, clears stage artifacts) or redirect a TaskPacket to an earlier stage (e.g., back to Router for re-expert-selection). Redirect requires a reason and shows a warning about which stages will re-run. Both actions produce audit log entries. The redirect modal lists only stages earlier than the current one.

### AC 4: Trust Tier Rule Engine

A configurable rule engine evaluates TaskPacket metadata against developer-defined rules to assign a task-level trust tier (Observe, Suggest, or Execute). Rules have conditions (category, complexity, lines changed, cost estimate, file path patterns, loopback count, gate results) joined by AND. Rules are ordered by priority (first match wins). A default tier applies when no rule matches. Rules persist to PostgreSQL and take effect on new TaskPackets immediately; in-flight TaskPackets keep their assigned tier.

### AC 5: Safety Bounds

Hard safety limits exist that override any rule: maximum auto-merge line count, maximum auto-merge cost, maximum loopbacks before hold, and mandatory review file patterns (globs). These bounds persist to PostgreSQL and are editable through a settings panel. When a safety bound is violated, the task-level tier is downgraded regardless of the matching rule.

### AC 6: Trust Tier Reconciliation

The task-level trust tier system (Observe/Suggest/Execute) coexists with the existing expert-level reputation tiers (Shadow/Probation/Trusted). The TaskPacket model gains a `task_trust_tier` field. The task-level tier governs Publisher behavior (report only, draft PR, auto-merge). The expert-level tier continues to govern expert selection and weighting. Both tiers are visible in the UI as separate concepts. No existing reputation tier logic is modified.

### AC 7: Budget Dashboard

A dashboard view displays: total spend, active cost, budget remaining (with progress bar), and average per-task cost as summary cards. A stacked bar chart shows spend over time segmented by model. Horizontal bar charts show cost by pipeline stage and cost by model (with token counts). A period selector allows 1d, 7d, 30d, and custom ranges. Data comes from the existing `ModelCallAudit` / `SpendReport` infrastructure via new dashboard API endpoints.

### AC 8: Budget Alerts and Automated Actions

Configurable alert thresholds exist for daily spend, weekly budget cap, and per-task cost warning. When a threshold is breached: (a) a notification is generated, and (b) optionally, an automated action fires. Two automated actions are available: "pause pipeline when weekly budget exceeded" (sends pause signal to all active workflows) and "downgrade models when approaching budget" (switches routing preference from opus to sonnet). Alert configuration persists to PostgreSQL.

### AC 9: Notification System

An in-app notification bell displays an unread count. Clicking it reveals a dropdown listing notifications categorized by type: gate failure, review needed, budget warning, task complete, drift alert, escalation, trust tier change. Each notification links to the relevant view (gate inspector, budget dashboard, task detail). Notifications can be marked as read individually or in bulk. Notifications are generated from SSE events.

### AC 10: Steering Audit Trail

Every steering action (pause, resume, retry, redirect, abort, hold-at-gate) is persisted to PostgreSQL with: task_id, action type, from_stage, to_stage (if redirect), reason, timestamp, and actor. Audit entries appear in the TaskPacket timeline as a distinct entry type. A dedicated "Activity Log" in Settings shows all steering actions across all TaskPackets.

---

## 4b. Top Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Temporal signal handlers for pause/resume/redirect can orphan workflows or corrupt state if not implemented with idempotent handlers and proper cancellation scopes | Critical -- lost work, silent failures | Implement signals with Temporal best practices: use workflow.condition() for pause/resume, CancellationScope for abort, and explicit state tracking. Write integration tests that pause/resume/abort at every stage boundary. |
| R2 | Redirect signal requires cancelling the current activity and restarting from an earlier stage. Temporal does not natively support "jump to step N" -- this must be modeled as workflow logic. | High -- complex implementation, potential for state inconsistency | Model redirect as: cancel current activity, set a redirect flag with target stage, and let the main workflow loop re-enter at the target stage. Store redirect history on the TaskPacket for debugging. |
| R3 | Trust tier reconciliation (AC 6) requires adding a new field to TaskPacket and ensuring existing Shadow/Probation/Trusted logic is not broken | Medium -- regression risk in expert selection | Add `task_trust_tier` as a new, nullable field. Keep expert-level tiers completely untouched. Write regression tests for `compute_tier()` and `compute_tier_transition()`. |
| R4 | Budget-pause automation (AC 8) sends pause signals to all active workflows. If multiple workflows are active, this must be atomic and handle partial failures. | Medium -- some workflows pause, others do not | Iterate through active workflow IDs, send pause to each, log failures, and retry. Do not treat partial failure as success. |
| R5 | Notification generation from SSE events (AC 9) creates a coupling between the SSE event stream and the notification persistence layer. If SSE events are missed, notifications are lost. | Medium -- silent notification loss | Notifications should be generated from NATS JetStream (durable) events, not from the SSE client-side stream. SSE is for real-time display; NATS is for durable notification generation. |

---

## 5. Constraints & Non-Goals

### Constraints

- **Phase 0 and Phase 1 must be complete.** This epic depends on the SSE-over-NATS bridge (`/api/v1/dashboard/events/stream`), the dashboard API router (`/api/v1/dashboard/`), and the `pipeline.stage.enter`/`pipeline.stage.exit` events. Without these, steering controls have no real-time feedback.
- **Phase 2 should be complete or in progress.** The triage queue and intent review workflows provide the context in which steering controls are most useful, though steering can function independently.
- **No modifications to existing Temporal signal handlers.** The three existing signals (`approve_publish`, `reject_publish`, `readiness_cleared`) must continue to work unchanged. New signals are additive.
- **No modifications to expert-level reputation tiers.** `src/reputation/tiers.py` and `src/reputation/engine.py` are not touched. The task-level trust tier is a parallel concept.
- **Single-user auth model.** This epic uses the same auth as the existing admin panel (Basic Auth). RBAC is out of scope.
- **No external notification integrations.** Slack, Discord, email, and webhook push are Phase 4+ considerations. This epic delivers in-app notifications only.
- **Budget data source.** Budget dashboard reads from the existing `ModelCallAudit` records and `SpendReport` aggregation. No new cost tracking instrumentation is required (existing `PipelineBudget` and `model_gateway` audit recording are sufficient).

### Non-Goals

1. **Reputation & Outcome Dashboard.** Design doc 03 Section 5 (expert performance, outcome signals, drift detection) belongs to Phase 5. It requires significant outcome data to be meaningful.
2. **Trust tier badge on all views.** The design spec calls for trust tier badges on triage queue cards, backlog board cards, timeline headers, pipeline rail tooltips, and PR evidence explorer. This epic adds the badge to the TaskPacket detail view and the task list only. Other views are follow-on work as those views are built.
3. **Drag-to-reorder rules.** The rule builder supports add/edit/delete and a priority number field. Drag-and-drop reordering is deferred as a polish item.
4. **Custom date range picker.** Period selector supports 1d, 7d, 30d. Custom date range input is deferred.
5. **Model downgrade path configurability.** The automated model downgrade action uses a hardcoded path (opus -> sonnet -> haiku). Custom downgrade chains are deferred.
6. **Notification preferences.** All notification types are enabled by default. A preferences panel to disable specific types is deferred to a follow-on.
7. **Pipeline Rail context menu.** The design spec shows a right-click context menu on pipeline stages for bulk actions (pause all in stage, abort all in stage). This epic delivers steering actions on individual TaskPackets only.
8. **Hold at Next Gate action.** This action (let current stage finish, pause before gate evaluation) is a specialized variant of pause that requires instrumenting every gate entry point. Deferred.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Implementation of all backend and frontend stories |
| Reviewer | Meridian | Epic review, story completeness, risk assessment |
| Planner | Helm | Sprint sequencing, dependency ordering |
| QA | Automated (pytest + Playwright) | Backend unit/integration tests; frontend component tests |
| External Dependency | Temporal | Workflow signal handling; must support `workflow.signal` for new handlers |
| External Dependency | NATS JetStream | Durable event delivery for notification generation |
| Design Source | Design docs 03 and 06 | Feature specifications and wireframes |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Time-to-intervention** | Pause action round-trip (click → SSE confirmation) completes in < 5 seconds | Playwright: click pause button, assert SSE `pipeline.paused` event received and UI shows paused state within 5s |
| **Steering action reliability** | 100% of pause/resume/abort signals result in expected workflow state within 5 seconds | Integration test: signal sent, workflow state asserted via Temporal query |
| **Trust tier adoption** | At least 1 custom trust tier rule exists in DB within 2 weeks of deployment | Automated: `SELECT count(*) FROM trust_tier_rule` > 0 |
| **Budget visibility** | Budget dashboard page load (API response + render) completes in < 2 seconds | Playwright: navigate to budget page, assert summary cards rendered within 2s |
| **Budget breach detection** | 100% of threshold breaches generate a notification within 30 seconds | Integration test: inject cost event exceeding threshold, assert notification row created |
| **Notification delivery** | All gate failures, budget warnings, and review requests generate notifications with zero silent drops | Integration test: compare NATS event count to notification table count |
| **Redirect accuracy** | Redirect to an earlier stage results in that stage executing with correct TaskPacket context | Integration test: redirect from Implement to Router, assert Router activity log shows current TaskPacket data |
| **Zero regression in existing signals** | `approve_publish`, `reject_publish`, `readiness_cleared` continue to work identically | Existing signal handler tests pass without modification |

---

## 8. Context & Assumptions

### Business Rules

- **Task-level trust tiers are a new concept.** The design uses Observe/Suggest/Execute to govern Publisher behavior at the task level. The codebase uses Shadow/Probation/Trusted to govern expert selection at the expert level. Both systems are needed and operate independently. See `docs/design/06-BACKEND-REQUIREMENTS.md` Section 6 for the full reconciliation analysis.
- **Trust tier rules apply to new TaskPackets only.** Changing a rule does not retroactively change the tier of in-flight work. This prevents mid-execution tier shifts that could change Publisher behavior after the pipeline has already made decisions based on the original tier.
- **Safety bounds are hard limits.** Even if a rule assigns Execute tier, safety bounds can downgrade it to Suggest or Observe. The hierarchy is: safety bounds > rules > default tier.
- **Pause is non-destructive.** A paused workflow retains all state. Resume continues from the exact point of pause. No artifacts are lost or regenerated.
- **Abort is terminal.** An aborted TaskPacket cannot be resumed, retried, or redirected. It moves to a terminal status. The developer must create a new TaskPacket to retry the work.
- **Redirect discards downstream progress.** Redirecting from Implement to Router discards Implement stage artifacts and re-runs Router, Assembler, and Implement. The developer is warned of this before confirming.

### Dependencies

| Dependency | Status | Required By |
|------------|--------|-------------|
| Phase 0: SSE-over-NATS bridge | Must be complete | All slices (real-time feedback) |
| Phase 1: Dashboard API router at `/api/v1/dashboard/` | Must be complete | All slices (API endpoints) |
| Phase 1: `pipeline.stage.enter`/`pipeline.stage.exit` events | Must be complete | Slice 1 (steering needs stage awareness) |
| Phase 1: `pipeline.cost_update` SSE events | Must be complete | Slice 4 (real-time cost display) |
| Temporal SDK signal support | Available (already used for 3 signals) | Slice 1 (new signal handlers) |
| NATS JetStream durable subscriptions | Available (2 existing streams) | Slice 5 (notification generation) |
| PostgreSQL with Alembic migrations | Available | All slices (new tables for rules, audit, budget config, notifications) |
| Existing `ModelCallAudit` audit store | Available (`src/admin/model_gateway.py`) | Slice 4 (budget data source) |
| Existing `SpendReport` aggregation | Available (`src/admin/model_spend.py`) | Slice 4 (budget summary) |
| Existing `PipelineBudget` enforcement | Available (`src/agent/framework.py`) | Slice 4 (budget-pause integration point) |

### Systems Affected

| System | Impact |
|--------|--------|
| `src/workflow/pipeline.py` | New signal handlers: pause, resume, redirect, abort. New state tracking for paused/redirected states. |
| `src/models/taskpacket.py` | New `task_trust_tier` field (Observe/Suggest/Execute). New statuses: PAUSED, ABORTED. New status transitions. |
| `src/dashboard/` | New API endpoints for steering, trust rules, budget config, notifications (24 backend stories from doc 06). |
| `src/admin/model_spend.py` | Budget summary/history/breakdown queries adapted for dashboard API (may extract to shared service). |
| `src/agent/framework.py` | Budget-pause integration: `PipelineBudget` must be able to trigger a pause signal when budget is exceeded. |
| PostgreSQL schema | New tables: `trust_tier_rule`, `safety_bounds`, `steering_audit_log`, `budget_config`, `notification`. Alembic migrations required. |
| NATS JetStream | New consumer for notification generation (subscribes to gate, cost, and steering events). |
| Frontend (React/Vite) | New components: steering action bar, trust rule builder, budget dashboard, notification bell + dropdown. |

### Assumptions

- The Temporal SDK version in use supports multiple signal handlers on a single workflow. This is standard Temporal behavior and is already demonstrated by the three existing signal handlers.
- The `workflow.signal` decorator allows adding new signal methods without modifying the workflow's main execution path. The existing `run()` method uses `workflow.wait_condition()` which is compatible with pause/resume patterns.
- The SSE infrastructure from Phase 0 can deliver steering confirmation events (e.g., "TaskPacket #139 paused") back to the browser within 5 seconds of the signal being sent.
- The existing `ModelCallAudit` records contain sufficient data (model, token counts, cost, timestamp, stage context) to power the budget dashboard without new instrumentation.
- NATS JetStream durable subscriptions are reliable enough for notification generation. If a consumer is temporarily down, messages are retained and delivered on reconnection (at-least-once delivery).

---

## Story Map

### MVP Designation

Stories in **Slices 1 and 4** are MVP (Pause/Abort + Budget Dashboard read-only). These deliver the minimum viable intervention capability and cost visibility. Slices 2, 3, and 5 are full-scope enhancements.

| Slice | MVP? | Rationale |
|-------|------|-----------|
| Slice 1: Pause/Resume/Abort | **MVP** | Core intervention — must be able to stop a runaway task |
| Slice 2: Retry/Redirect | Full | Refinement — nice-to-have but not blocking |
| Slice 3: Trust Tier Config | Full | Governance — value grows with usage volume |
| Slice 4: Budget Dashboard | **MVP** | Cost visibility — must know what you're spending |
| Slice 5: Notifications | Full | Quality of life — alerts reduce dashboard polling |

---

### Slice 1: Pipeline Steering -- Pause/Resume/Abort (MVP, Highest Risk, Foundational)

**Goal:** A developer can freeze, continue, or kill a running TaskPacket from the dashboard. This slice establishes the Temporal signal infrastructure that all other automated actions (budget-pause, hold-at-gate) will build on.

**Story 37.1: Temporal Signal Handlers -- Pause and Resume**
Add `pause_task` and `resume_task` signal handlers to `PipelineWorkflow`. Pause sets a workflow-level flag checked via `workflow.wait_condition()` before each activity execution. Resume clears the flag. The workflow's main `run()` method checks the pause flag at each stage boundary. Pausing mid-activity waits for the current activity to complete, then holds.
- Files to modify: `src/workflow/pipeline.py`
- Files to create: none (modify existing workflow class)
- Tests: Integration test that starts a workflow, sends pause signal, asserts no further activities execute, sends resume, asserts continuation.
- AC: AC 1

**Story 37.2: Temporal Signal Handler -- Abort**
Add `abort_task(reason: str)` signal handler. Sets an abort flag and cancels the current activity's CancellationScope. The workflow transitions the TaskPacket to a new ABORTED status. The abort reason is stored on the TaskPacket metadata.
- Files to modify: `src/workflow/pipeline.py`, `src/models/taskpacket.py` (add ABORTED status + transitions)
- Tests: Integration test that sends abort during Implement stage, asserts workflow terminates and TaskPacket status is ABORTED with reason.
- AC: AC 2

**Story 37.3: Steering API Endpoints -- Pause/Resume/Abort**
Create `POST /api/v1/dashboard/tasks/:id/pause`, `POST /api/v1/dashboard/tasks/:id/resume`, `POST /api/v1/dashboard/tasks/:id/abort` (body: `{reason: string}`). Each endpoint looks up the Temporal workflow ID for the TaskPacket and sends the appropriate signal. Returns 202 on success, 404 if TaskPacket not found, 409 if action is invalid for current state (e.g., resume on non-paused task).
- Files to modify: `src/dashboard/` router (or create `src/dashboard/steering.py`)
- Tests: Unit tests with mocked Temporal client. Integration test through FastAPI test client.
- AC: AC 1, AC 2

**Story 37.4: Steering Audit Log Model and Persistence**
Create `SteeringAuditLog` SQLAlchemy model with fields: id, task_id, action (enum: pause/resume/retry/redirect/abort), from_stage, to_stage (nullable), reason (nullable), timestamp, actor. Create Alembic migration. Create repository functions for insert and query.
- Files to create: `src/dashboard/models/steering_audit.py`, Alembic migration
- Tests: Unit tests for model validation. Integration test for insert + query.
- AC: AC 10

**Story 37.5: Steering Audit Persistence in Signal Handlers**
After each signal handler executes successfully, persist a `SteeringAuditLog` entry. Use a Temporal activity for the database write (signals cannot do I/O directly). Emit a `pipeline.steering.action` event to NATS for SSE propagation.
- Files to modify: `src/workflow/pipeline.py`, `src/workflow/activities.py`
- Tests: Integration test that sends pause signal, asserts audit log entry exists with correct fields.
- AC: AC 10

**Story 37.6: Frontend -- Steering Action Bar on TaskPacket Detail**
Add Pause, Resume, and Abort buttons to the TaskPacket detail view. Pause and Resume toggle based on current state. Abort opens a confirmation dialog with mandatory reason input. Buttons are disabled while an action is in flight. SSE events update the UI state when the signal is confirmed.
- Files to create: Frontend component (e.g., `SteeringActionBar.tsx`)
- Tests: Component test for button state transitions. E2E test for pause/abort flow.
- AC: AC 1, AC 2

**Story 37.7: Frontend -- Steering Audit Entries in TaskPacket Timeline**
Steering audit log entries appear in the TaskPacket timeline as a distinct entry type with a wrench icon, showing action, reason, and timestamp. Entries are fetched via `GET /api/v1/dashboard/tasks/:id/audit` or included in the activity feed.
- Files to modify: TaskPacket timeline component
- Files to create: `GET /api/v1/dashboard/tasks/:id/audit` endpoint if not part of existing activity feed
- Tests: Component test rendering audit entries.
- AC: AC 10

---

### Slice 2: Pipeline Steering -- Retry/Redirect (Complex Workflow Logic)

**Goal:** A developer can retry a failed stage or redirect a TaskPacket to an earlier stage. This is the most complex workflow logic in the epic.

**Story 37.8: Temporal Signal Handler -- Redirect**
Add `redirect_task(target_stage: str, reason: str)` signal handler. Sets a redirect flag with the target stage. The workflow's main loop detects the redirect flag after the current activity completes, discards downstream state, and re-enters the pipeline at the target stage. Only stages earlier than the current stage are valid targets. The handler validates the target and raises if invalid.
- Files to modify: `src/workflow/pipeline.py`
- Tests: Integration test that redirects from Implement to Router, asserts Router activity re-executes, Implement re-executes with new routing.
- AC: AC 3
- Risk: R2 (redirect complexity)

**Story 37.9: Temporal Signal Handler -- Retry Stage**
Add `retry_stage` signal handler. Functionally equivalent to a redirect to the current stage. Clears current stage artifacts on the TaskPacket and re-enters the stage from the beginning. Requires confirmation (handled by frontend).
- Files to modify: `src/workflow/pipeline.py`
- Tests: Integration test that retries Verify after a failure, asserts Verify re-executes.
- AC: AC 3

**Story 37.10: Steering API Endpoints -- Redirect/Retry**
Create `POST /api/v1/dashboard/tasks/:id/redirect` (body: `{target_stage: string, reason: string}`) and `POST /api/v1/dashboard/tasks/:id/retry`. Redirect validates that target_stage is earlier than current stage. Returns 202 on success, 400 if target stage is invalid.
- Files to modify: `src/dashboard/steering.py`
- Tests: Unit tests for stage validation logic. Integration test through FastAPI test client.
- AC: AC 3

**Story 37.11: Frontend -- Redirect Modal and Retry Confirmation**
Redirect button opens a modal showing current stage, radio buttons for valid earlier stages, a required reason text input, and a warning about which stages will re-run. Retry button opens a confirmation dialog warning that current stage progress will be discarded.
- Files to create: `RedirectModal.tsx`, `RetryConfirmation.tsx`
- Tests: Component tests for modal state and validation.
- AC: AC 3

---

### Slice 3: Trust Tier Configuration (New Data Model + Rule Engine)

**Goal:** A developer can define rules that automatically assign Observe/Suggest/Execute tiers to TaskPackets based on metadata, with safety bounds as hard limits.

**Story 37.12: Trust Tier Rule Data Model**
Create `TrustTierRule` SQLAlchemy model with fields: id, priority (integer, lower = higher priority), conditions (JSON -- array of {field, operator, value} objects), assigned_tier (enum: Observe/Suggest/Execute), active (boolean), created_at, updated_at. Create `SafetyBounds` model with fields: max_auto_merge_lines, max_auto_merge_cost, max_loopbacks_before_hold, mandatory_review_patterns (JSON array of glob strings). Create Alembic migrations.
- Files to create: `src/dashboard/models/trust_config.py`, Alembic migration
- Tests: Unit tests for model validation and defaults.
- AC: AC 4, AC 5

**Story 37.13: Task-Level Trust Tier on TaskPacket**
Add `task_trust_tier` field to `TaskPacketRow` (nullable StrEnum: observe/suggest/execute). Add `default_trust_tier` to a settings/config table. Create Alembic migration.

**Reconciliation decision (resolves B-3.5):** Task-level tiers (Observe/Suggest/Execute) and expert-level tiers (Shadow/Probation/Trusted) are **parallel, independent concepts**. Task tiers govern Publisher behavior (what happens to the PR). Expert tiers govern Router behavior (which experts are selected). Both fields coexist on the system. Existing expert-level tiers in `src/reputation/tiers.py` are **not modified, not renamed, and not removed**. The new `task_trust_tier` field is additive only.

- Files to modify: `src/models/taskpacket.py` (add field), Alembic migration (add column)
- Files NOT modified: `src/reputation/tiers.py` (explicitly untouched)
- Tests: Regression tests for `compute_tier()` and `compute_tier_transition()` to prove zero change. Unit test for new `task_trust_tier` field and its StrEnum values.
- AC: AC 6
- Risk: R3 (reconciliation — mitigated by this explicit decision)

**Story 37.14: Trust Tier Rule Evaluation Engine**
Create a rule evaluation function that takes TaskPacket metadata and the ordered list of active rules, evaluates conditions against metadata, and returns the matching tier (or default tier if no match). Safety bounds are checked after rule evaluation and can downgrade the tier. Condition evaluation supports: equals, less_than, greater_than, contains, matches_glob.
- Files to create: `src/dashboard/trust_engine.py`
- Tests: Unit tests for each condition operator. Test for first-match-wins ordering. Test for safety bound override. Test for default tier fallback.
- AC: AC 4, AC 5

**Story 37.15: Trust Tier CRUD API**
Create `GET /api/v1/dashboard/trust/rules` (list all rules ordered by priority), `POST /api/v1/dashboard/trust/rules` (create rule), `PUT /api/v1/dashboard/trust/rules/:id` (update rule), `DELETE /api/v1/dashboard/trust/rules/:id`. Create `GET /PUT /api/v1/dashboard/trust/safety-bounds`. Create `GET /PUT /api/v1/dashboard/trust/default-tier`.
- Files to create: `src/dashboard/trust_router.py`
- Tests: Integration tests through FastAPI test client for all CRUD operations.
- AC: AC 4, AC 5

**Story 37.16: Trust Tier Assignment at Pipeline Start**
At the beginning of the Temporal workflow (before the first activity), evaluate the trust tier rule engine against the TaskPacket metadata and set `task_trust_tier` on the TaskPacket. Log the assigned tier, the matching rule (or "default"), and any safety bound overrides. Emit a `pipeline.trust_tier.assigned` event to NATS.
- Files to modify: `src/workflow/pipeline.py`, `src/workflow/activities.py`
- Tests: Integration test that creates a rule, starts a workflow, asserts the correct tier is assigned.
- AC: AC 4, AC 6

**Story 37.17: Frontend -- Trust Tier Rule Builder**
Settings panel with: default tier dropdown, rule list (add/edit/delete), condition builder (field dropdown, operator dropdown, value input), tier assignment dropdown, priority number input, active toggle. Active tier display showing a plain-English summary of current rules. Safety bounds panel with number inputs and glob pattern input.
- Files to create: `TrustConfiguration.tsx`, `RuleBuilder.tsx`, `SafetyBoundsPanel.tsx`, `ActiveTierDisplay.tsx`
- Tests: Component tests for rule CRUD, condition builder, safety bounds editing.
- AC: AC 4, AC 5

**Story 37.18: Trust Tier Audit Log**
When a tier is assigned or overridden (by safety bounds), log the event to the steering audit log with action type `trust_tier_assigned` or `trust_tier_overridden`. Include the matching rule ID, original tier, and final tier.
- Files to modify: `src/dashboard/models/steering_audit.py` (extend action enum), `src/workflow/activities.py`
- Tests: Unit test for audit entry creation on tier assignment.
- AC: AC 10

---

### Slice 4: Budget Dashboard (Read Path + Alerts + Automated Actions)

**Goal:** A developer can see where money is going, set budget limits, and have the pipeline automatically respond to budget pressure.

**Story 37.19: Budget API Endpoints**
Create `GET /api/v1/dashboard/budget/summary` (total spend, active cost, budget remaining, avg per task for the selected period), `GET /api/v1/dashboard/budget/history` (time series spend by day, segmented by model), `GET /api/v1/dashboard/budget/by-stage` (cost per pipeline stage), `GET /api/v1/dashboard/budget/by-model` (cost per model with token counts). Data sourced from existing `ModelCallAudit` records via `SpendReport` aggregation logic.
- Files to create: `src/dashboard/budget_router.py`
- Files to reference: `src/admin/model_spend.py` (reuse or extract aggregation logic)
- Tests: Unit tests with fixture data for each endpoint. Integration test with seeded audit records.
- AC: AC 7

**Story 37.20: Budget Configuration API**
Create `GET /PUT /api/v1/dashboard/budget/config`. Configuration fields: daily_spend_warning (decimal), weekly_budget_cap (decimal), per_task_warning (decimal), pause_on_budget_exceeded (boolean), model_downgrade_on_approach (boolean), downgrade_threshold_percent (integer, e.g., 80 = pause-or-downgrade at 80% of cap). Persist to PostgreSQL.
- Files to create: `src/dashboard/models/budget_config.py`, Alembic migration
- Tests: CRUD integration test.
- AC: AC 8

**Story 37.21: Budget Threshold Checker**
A function that runs after each `pipeline.cost_update` event (or after each `ModelCallAudit` record). Compares current spend against configured thresholds. Returns a list of breached thresholds with severity. If `pause_on_budget_exceeded` is true and weekly cap is breached, sends pause signals to all active workflows. If `model_downgrade_on_approach` is true and spend exceeds downgrade threshold, updates the model routing preference (integrates with `src/admin/model_gateway.py` tier budget system).
- Files to create: `src/dashboard/budget_checker.py`
- Files to modify: `src/agent/framework.py` (hook into PipelineBudget), `src/admin/model_gateway.py` (model downgrade API)
- Tests: Unit test for threshold comparison. Integration test for pause-on-exceed. Integration test for model downgrade trigger.
- AC: AC 8
- Risk: R4 (atomic multi-workflow pause)

**Story 37.22: Frontend -- Budget Dashboard View**
Summary cards row, spend-over-time stacked bar chart (Chart.js or similar), cost-by-stage horizontal bars, cost-by-model horizontal bars with token counts, period selector (1d/7d/30d). Budget alert configuration section with threshold inputs and automated action toggles. Real-time cost updates via `pipeline.cost_update` SSE events.
- Files to create: `BudgetDashboard.tsx`, `SpendChart.tsx`, `CostBreakdown.tsx`, `BudgetAlertConfig.tsx`
- Tests: Component tests for data rendering. Mock SSE event test for real-time update.
- AC: AC 7, AC 8

**Story 37.23: Per-Task Cost Breakdown**
Add cost breakdown panel to TaskPacket detail view showing cost by stage and cost by model for that specific task. Data from `GET /api/v1/dashboard/tasks/:id` (which should include cost breakdown from Phase 1 backend).
- Files to modify: TaskPacket detail component
- Tests: Component test rendering per-task cost data.
- AC: AC 7

---

### Slice 5: Notifications (Durable Event-Driven Alerts)

**Goal:** A developer sees a notification whenever something needs their attention -- gate failures, budget warnings, review requests -- without polling.

**Story 37.24: Notification Data Model**
Create `Notification` SQLAlchemy model with fields: id, type (enum: gate_failure, review_needed, budget_warning, task_complete, drift_alert, escalation, trust_tier_change), title, message, task_id (nullable FK), read (boolean, default false), created_at. Create Alembic migration.
- Files to create: `src/dashboard/models/notification.py`, Alembic migration
- Tests: Unit tests for model validation.
- AC: AC 9

**Story 37.25: Notification API Endpoints**
Create `GET /api/v1/dashboard/notifications` (paginated, filterable by read/unread, includes unread count in response metadata), `PATCH /api/v1/dashboard/notifications/:id/read`, `POST /api/v1/dashboard/notifications/mark-all-read`.
- Files to create: `src/dashboard/notification_router.py`
- Tests: Integration tests for list, mark-read, mark-all-read.
- AC: AC 9

**Story 37.26: Notification Generation from NATS Events**
Create a NATS JetStream consumer that subscribes to relevant event subjects: `pipeline.gate.fail`, `pipeline.cost_update` (when threshold breached), `pipeline.steering.action`, `pipeline.trust_tier.assigned`. For each event, generate a `Notification` record with appropriate type, title, and message. Run as an async background task in the FastAPI app lifecycle.
- Files to create: `src/dashboard/notification_generator.py`
- Files to modify: `src/app.py` (register background task on startup)
- Tests: Integration test that publishes a NATS event and asserts a notification was created.
- AC: AC 9
- Risk: R5 (durable delivery)

**Story 37.27: Frontend -- Notification Bell and Dropdown**
Notification bell in top bar with unread count badge. Click opens dropdown showing recent notifications grouped into "New" and "Earlier" sections. Each notification shows type icon, title, message excerpt, relative timestamp, and a link to the relevant view. "Mark all read" button at top. Individual mark-as-read on click-through.
- Files to create: `NotificationBell.tsx`, `NotificationDropdown.tsx`, `NotificationItem.tsx`
- Tests: Component tests for unread count, click-through navigation, mark-as-read.
- AC: AC 9

**Story 37.28: Settings Activity Log**
A "Steering Activity" section in the Settings view that shows all steering actions across all TaskPackets as a paginated, filterable table. Columns: timestamp, TaskPacket ID, action, from/to stage, reason, actor. Uses `GET /api/v1/dashboard/steering/audit` endpoint.
- Files to create: `SteeringActivityLog.tsx`, `GET /api/v1/dashboard/steering/audit` endpoint
- Tests: Component test for table rendering and filtering.
- AC: AC 10

---

## Meridian Review Status

### Round 1: Pending

*This epic has not yet been reviewed by Meridian. It must pass Meridian review (7 questions + red flags) before implementation begins.*
