# Epic 36: Phase 2 — Planning Experience

> **Status:** Approved — Ready for Sprint Planning (Meridian Round 2 PASS, 2026-03-21)
> **Epic Owner:** Primary Developer
> **Duration:** 8-10 weeks (backend + frontend in series); MVP (Slices 1+2): 4-5 weeks
> **Created:** 2026-03-20
> **Depends On:** Phase 0 (COMPLETE), Phase 1 (COMPLETE)
> **Meridian Review:** Round 1: CONDITIONAL PASS → Round 2: **PASS** (2026-03-21)
> **Kill Criterion:** If after MVP delivery (Slices 1+2), fewer than 30% of tasks use intent review within 2 weeks, pivot to auto-approve with notification instead of workflow pause.

---

## 1. Title

**Developers Plan with Confidence Before the Pipeline Writes a Single Line of Code**

---

## 2. Narrative

TheStudio's pipeline today is a one-way street. A GitHub issue arrives via webhook, and the system immediately starts processing it — Context, Intent, Router, Assembler, Implement. The developer has no opportunity to review the issue before it enters the pipeline, no chance to review or edit the Intent Specification that defines "what correct looks like," and no visibility into which experts were selected or why.

This means the developer's first real interaction with the system's understanding of a task happens when a draft PR appears. If the Intent Specification was wrong, the entire pipeline ran for nothing. If the experts were misselected, the code will be off-target. If the issue was ambiguous or out of scope, the system wasted budget processing something that should have been rejected at intake.

The planning experience changes this. It introduces three decision points where the developer can review and steer before compute is spent:

1. **Triage** — Review incoming issues, accept them into the pipeline, reject them, or edit them before they proceed. This is the front door.
2. **Intent Review** — After the Context and Intent stages produce a draft Intent Specification, the developer reviews it in a split-pane editor with source context on the left and the structured spec on the right. They can approve, edit, request AI refinement, or reject. The Temporal workflow pauses here until the developer acts.
3. **Routing Review** — After the Router selects experts, the developer sees which experts will work on the task and why, and can approve or override before the Assembler begins.

Beyond these wait points, the planning experience adds a Complexity Dashboard (visual risk assessment from the Context stage), a Backlog Board (Kanban view of all work across pipeline stages), and Manual Task Creation (tasks without GitHub issues).

**Why now:** Phase 0 and Phase 1 make the pipeline visible. Phase 2 makes it steerable. Without planning controls, increasing trust tiers (Phase 3) is reckless — you cannot give the system more autonomy if you cannot intervene at the planning stage. This phase is the prerequisite for the entire "trust escalation" story that follows.

**MVP vs Full:** The MVP is Slice 1 (Triage Queue) + Slice 2 (Intent Specification viewer with approve/reject). These two slices alone close the "blind pipeline" problem. Slices 3 and 4 add polish (complexity dashboard, expert routing preview, backlog board, manual task creation) and can be deferred if needed.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Master UI Vision (Phase 2 scope) | `docs/design/00-PIPELINE-UI-VISION.md` Section 8 |
| Planning Experience Design Spec | `docs/design/01-PLANNING-EXPERIENCE.md` |
| Backend Requirements (Phase 2 stories B-2.1 through B-2.18) | `docs/design/06-BACKEND-REQUIREMENTS.md` Section 3 |
| Technology Architecture | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` |
| TaskPacket model (current status enum, transitions) | `src/models/taskpacket.py` |
| Intent Specification model | `src/intent/intent_spec.py` |
| Intent Builder | `src/intent/intent_builder.py` |
| Intent Refinement | `src/intent/refinement.py` |
| Webhook Handler (current entry point) | `src/ingress/webhook_handler.py` |
| Temporal Workflow (current signal handlers) | `src/workflow/pipeline.py` |
| Workflow Activities | `src/workflow/activities.py` |
| Router (expert selection) | `src/routing/` |
| Current Admin Router (no dashboard API) | `src/admin/ui_router.py` |
| Primary Persona: Solo Developer | `docs/design/00-PIPELINE-UI-VISION.md` Section 6 |
| OKR: 80%+ tasks have developer-reviewed Intent Specs | `docs/design/00-PIPELINE-UI-VISION.md` Section 7 |
| Copilot Workspace comparison | `docs/design/01-PLANNING-EXPERIENCE.md` Section 3.5 |
| Current State Audit (NATS, Temporal, SSE) | `docs/design/06-BACKEND-REQUIREMENTS.md` Section 2 |

---

## 4. Acceptance Criteria

### AC 1: Triage Queue Receives and Holds Issues

When `TRIAGE_MODE_ENABLED=true`, incoming GitHub webhook issues create TaskPackets in `TRIAGE` status instead of immediately starting a Temporal workflow. A `GET /api/v1/dashboard/tasks?status=triage` endpoint returns these TaskPackets with issue metadata (title, body, labels, reporter). The triage queue frontend renders cards with issue details and action buttons. TaskPackets remain in TRIAGE until the developer acts.

### AC 2: Triage Accept Starts Pipeline

`POST /api/v1/dashboard/tasks/:id/accept` transitions a TaskPacket from `TRIAGE` to `RECEIVED` and starts the Temporal workflow. The TaskPacket then proceeds through the normal pipeline (Context, Intent, etc.). The triage queue removes the card on acceptance.

### AC 3: Triage Reject Archives with Reason

`POST /api/v1/dashboard/tasks/:id/reject` transitions a TaskPacket from `TRIAGE` to `REJECTED` with a required `reason` field (one of: duplicate, out_of_scope, needs_info, wont_fix). The card disappears from the active queue. Rejected TaskPackets are queryable via the API with `?status=rejected`.

### AC 4: Triage Edit Before Accept

`PATCH /api/v1/dashboard/tasks/:id` allows editing title, description, category, and priority while the TaskPacket is in `TRIAGE` status. Edits are persisted. The "Edit Before Accept" flow opens a side panel in the frontend, and accepting after editing starts the pipeline with the modified metadata.

### AC 5: Intent Specification Viewer with Approve/Reject

After the Intent Builder produces a draft spec, the Temporal workflow pauses (new wait point after Intent stage). A `GET /api/v1/dashboard/tasks/:id/intent` endpoint returns the Intent Specification (structured fields: `goal`, `constraints`, `acceptance_criteria`, `non_goals`) with version history. The frontend displays a split-pane view: source context (issue body, affected files, complexity) on the left, rendered Intent Specification sections on the right. `POST /api/v1/dashboard/tasks/:id/intent/approve` sends a Temporal signal that resumes the workflow into the Router stage.

### AC 6: Intent Specification Editing

`PUT /api/v1/dashboard/tasks/:id/intent` accepts a developer-edited Intent Specification as structured fields (`goal: str`, `constraints: list[str]`, `acceptance_criteria: list[str]`, `non_goals: list[str]`). Each edit creates a new `IntentSpecRow` version (stored in PostgreSQL with timestamp and `source: developer` — new column on existing table). Version history is visible in the UI via a dropdown showing v1, v2, v3... with timestamps and diff view between versions.

### AC 7: Intent Refinement Loop

`POST /api/v1/dashboard/tasks/:id/intent/refine` accepts a `feedback` text field and constructs a `RefinementTrigger(source="developer", questions=[feedback])` to call `refine_intent()`. The new spec version is stored with `source: refinement`. The workflow remains paused until the developer approves the refined version. Note: the existing `MAX_INTENT_VERSIONS = 2` cap in `src/intent/refinement.py` must be raised to support developer editing loops (see Story 36.7a).

### AC 8: Complexity Dashboard Displays Risk Assessment

A read-only dashboard tab for each TaskPacket shows: overall complexity score (numeric + color bar), files affected count with directory breakdown, dependency depth tree, test coverage gaps per affected file, risk flags checklist, and estimated cost range. All data comes from the Context stage's existing enrichment output.

### AC 9: Expert Routing Preview with Approve/Override

After the Router stage selects experts, the workflow pauses (new wait point after Router). A `GET /api/v1/dashboard/tasks/:id/routing` endpoint returns the list of selected experts with: role name, mandate, assigned files, selection reason (MANDATORY or AUTO), and reputation weight. `POST /api/v1/dashboard/tasks/:id/routing/approve` resumes the workflow into the Assembler. `POST /api/v1/dashboard/tasks/:id/routing/override` allows adding or removing AUTO experts before approval.

### AC 10: Backlog Board with Kanban View

A Kanban board displays all TaskPackets in six columns: Triage, Planning (Context through Router), Building (Assembler through Implement), Verify (Verification + QA), Done (Published), Rejected. Cards show issue number, title, category badge, complexity, and cost. Cards are clickable to open detail views.

### AC 11: Manual Task Creation

A `POST /api/v1/dashboard/tasks` endpoint creates a TaskPacket without a GitHub issue. Required fields: title, description. Optional fields: category, priority, acceptance_criteria. A "Skip triage" option sends the task directly to the Context stage. The frontend provides a modal form with Markdown-enabled description field.

---

## 4b. Top Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Temporal workflow wait points are new architecture — the pipeline has never paused for developer input mid-flow (only after QA for publish approval) | High — incorrect signal/timer implementation could deadlock workflows or lose state | Start with the intent wait point only (Slice 2), validate it end-to-end before adding the routing wait point (Slice 3). Use the existing `approve_publish` signal pattern as the template. |
| R2 | Adding `TRIAGE` status requires a database migration and touches the status transition map, which is referenced by 6+ modules | Medium — migration failure or missed transition could break existing TaskPackets | Add `TRIAGE` as a new entry point (TRIAGE -> RECEIVED), do not modify any existing transitions. Write migration as additive (ALTER TABLE ADD CHECK, not replace). |
| R3 | ~~RESOLVED~~ Phase 0 and Phase 1 are both COMPLETE. Frontend stories can proceed immediately using the existing React scaffolding, dashboard router, and SSE bridge. | ~~High~~ None | No action needed. |
| R4 | Context stage pre-scan (lightweight complexity/cost estimate for triage cards) may require a new Temporal activity or significant refactoring of the existing Context stage | Medium — scope creep | For MVP, use a synchronous function call at webhook time (not a full Temporal workflow) that does file-impact heuristics. The full Context stage runs after acceptance. |
| R5 | ~~RESOLVED~~ Intent versioning already exists — `IntentSpecRow` stores multiple rows per TaskPacket with incrementing `version` column, and `get_all_versions()` returns all versions. Only a `source` column addition is needed. | ~~Medium~~ Low | Add `source` column to existing table (Story 36.7). No new table. No parallel versioning system. |

---

## 5. Constraints & Non-Goals

### Constraints

- **Phase 0 and Phase 1 are COMPLETE.** The dashboard API router (`/api/v1/dashboard/`), SSE bridge, and React scaffolding exist. Backend stories in this epic mount new endpoints on the existing router at `src/dashboard/router.py`. Frontend stories extend the existing React app at `frontend/src/`.
- **Existing webhook behavior is default.** Triage mode is opt-in via `TRIAGE_MODE_ENABLED` environment variable. When disabled, webhooks create TaskPackets in `RECEIVED` status and start workflows immediately (current behavior preserved).
- **No modifications to existing Temporal signal handlers.** The three existing signals (`approve_publish`, `reject_publish`, `readiness_cleared`) remain untouched. New wait points use new signal names (`approve_intent`, `approve_routing`).
- **Single-user auth only.** The planning experience uses the same authentication as the existing admin panel (HTTP Basic Auth or session token from Phase 0). No RBAC, no multi-user.
- **Desktop-first layout.** Minimum viewport: 1024px. Tablet stacks split panes vertically. No mobile target.
- **No admin panel migration.** The existing Jinja-based admin at `/admin/*` continues to operate unchanged. The planning experience lives at `/dashboard/*`.

### Non-Goals

- **GitHub Projects bidirectional sync.** The backlog board is TheStudio-only. GitHub Projects sync is Phase 4 (tracked in `docs/design/04-GITHUB-INTEGRATION-ANALYTICS.md`).
- **Drag-and-drop reordering on the backlog board.** The board is read-only in this epic (cards reflect pipeline status). Interactive drag-and-drop to change status is deferred.
- **Structured issue form templates.** The `.github/ISSUE_TEMPLATE/thestudio-task.yml` feature from the design spec is deferred — it requires repo-level configuration changes and is a polish item.
- **Priority Matrix and Timeline views.** The backlog board ships with Kanban view only. Priority Matrix and Gantt timeline are deferred.
- **Historical comparison panel.** The "similar past tasks" comparison on the complexity dashboard requires sufficient outcome data (>5 similar tasks) and outcome pipeline maturity. Deferred.
- **Full Markdown editor with Monaco/CodeMirror.** Intent editing uses a textarea with Markdown preview toggle, not a rich editor. Rich editor is polish.
- **Keyboard shortcuts (j/k/a/e/r).** Keyboard-driven navigation is deferred to a polish pass after core functionality ships.
- **Constraint checkboxes on Intent Spec.** Inline constraint toggling is deferred. Editing is via the full editor mode.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | All implementation (backend + frontend) |
| Reviewer | Meridian | Epic review, story completeness, risk identification |
| Planner | Helm | Sprint sequencing, dependency verification |
| QA | Automated (pytest + Playwright/Vitest) | Backend: pytest for API endpoints and workflow signals. Frontend: component tests. |
| Design | Design specs in `docs/design/01-PLANNING-EXPERIENCE.md` | Wireframes and interaction patterns are defined in the design doc. No separate designer. |
| External Dependency | Temporal | Workflow wait point implementation requires Temporal signal handling |
| External Dependency | Phase 0 + Phase 1 | SSE bridge, dashboard API router, React scaffolding |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Intent review rate** | 80%+ of tasks have developer-reviewed Intent Specifications (approved or edited) | Count of TaskPackets with `intent_spec.source IN ('developer', 'refinement')` or explicit approval signal / total TaskPackets past Intent stage |
| **Triage rejection rate** | >0% — proves developer is exercising judgment, not rubber-stamping | Count of REJECTED TaskPackets with triage-stage rejection reason / total TaskPackets entering triage |
| **Planning stage dwell time** | Median < 5 minutes from intent spec ready to developer approval | Timestamp diff between `pipeline.stage.exit(intent)` event and `approve_intent` signal receipt |
| **Rework reduction** | 20% fewer loopbacks from Verification/QA back to Implement (compared to pre-triage baseline) | Loopback count per TaskPacket, averaged over rolling 30-day windows |
| **Intent edit rate** | >10% of Intent Specifications are developer-edited (not just approved as-is) | Count of TaskPackets with `intent_spec.source = 'developer'` / total approved |
| **Zero regression on existing flow** | All existing tests pass; TaskPackets created with `TRIAGE_MODE_ENABLED=false` follow the original path with no behavioral change | Existing pytest suite green; manual smoke test of webhook -> PR flow |

---

## 8. Context & Assumptions

### Business Rules

- **Triage mode is feature-flagged.** `TRIAGE_MODE_ENABLED` (env var, default `false`) controls whether webhooks create TaskPackets in TRIAGE or RECEIVED status. This allows gradual rollout and instant rollback.
- **Intent review is mandatory when enabled.** Once the intent wait point is active, there is no auto-approve timeout. The developer must explicitly approve, edit, or reject. (A future epic may add auto-approve after N minutes for trusted task categories.)
- **Routing review is optional.** The routing wait point can be enabled/disabled independently via `ROUTING_REVIEW_ENABLED` (env var, default `false`). When disabled, the Router stage proceeds directly to Assembler as it does today.
- **Rejected TaskPackets are soft-deleted.** They remain in the database with `REJECTED` status and a reason. They are queryable but do not appear in the active backlog.

### Dependencies

| Dependency | Status | Impact if Missing |
|------------|--------|-------------------|
| Phase 0: SSE bridge + dashboard API router (Epic 34) | **COMPLETE** (2026-03-21) | Dashboard router at `src/dashboard/router.py`, SSE bridge at `src/dashboard/events.py`, React app at `frontend/src/` |
| Phase 1: Pipeline Rail + TaskPacket list API (Epic 35) | **COMPLETE** (2026-03-21) | `GET /api/v1/dashboard/tasks` endpoint exists. Pipeline Rail, Gate Inspector, Activity Stream, Minimap all shipped. |
| Temporal SDK signal handling | **Available** (used by `approve_publish`) | New wait points follow the same pattern |
| PostgreSQL + SQLAlchemy async | **Available** | New columns and tables use existing migration framework |
| React + Vite scaffolding (Phase 0) | **COMPLETE** (2026-03-21) | Vite + React 19 + TypeScript + Zustand + Tailwind at `frontend/` |
| NATS JetStream | **Available** | SSE events for real-time triage queue updates |

### Systems Affected

| System | Change |
|--------|--------|
| `src/models/taskpacket.py` | Add `TRIAGE` status to enum; add transitions `TRIAGE -> RECEIVED` and `TRIAGE -> REJECTED` |
| `src/ingress/webhook_handler.py` | Conditional: create in TRIAGE (when enabled) instead of RECEIVED; skip workflow start |
| `src/workflow/pipeline.py` | Add wait points after Intent and Router stages (new signal handlers: `approve_intent`, `approve_routing`) |
| `src/workflow/activities.py` | Emit SSE events for intent-ready and routing-ready states |
| `src/intent/intent_spec.py` | Add `source` column to existing `IntentSpecRow`; update Pydantic schemas |
| `src/intent/intent_crud.py` | Pass `source` through `create_intent()`; existing `get_all_versions()` unchanged |
| `src/routing/` | Add API-serializable routing result model (experts, reasons, weights) |
| `src/dashboard/` (existing) | Extends Phase 0 dashboard router with planning API endpoints |
| `src/context/` | Add lightweight pre-scan function for triage card enrichment |
| `src/db/migrations/` | New migration for `TRIAGE` status, `intent_spec.source` column, `board_preferences` table |
| `frontend/src/` (existing, from Phase 0) | Triage queue, intent editor, complexity dashboard, routing preview, backlog board, task creation modal |

### Assumptions

- The Phase 0 dashboard API router exists at `src/dashboard/router.py` with `/api/v1/dashboard/` prefix. New planning endpoints mount on this router or a sub-router.
- The `refine_intent()` function in `src/intent/refinement.py` requires a `RefinementTrigger` dataclass (not a plain feedback string). The refinement endpoint must construct `RefinementTrigger(source="developer", questions=[feedback_text])`. The `source` field currently accepts `"qa_agent"` or `"assembler"` — `"developer"` must be added as a valid source.
- The Router (`src/routing/`) produces a structured result that can be serialized to JSON for the API. If the current router returns opaque internal objects, a serialization adapter will be needed.
- The Temporal workflow is structured such that inserting a wait point between activities is feasible without rewriting the workflow definition. The existing `approve_publish` wait point after QA validates this pattern.
- The existing `IntentSpecRow` table already supports multi-row versioning (multiple rows per TaskPacket with incrementing `version` column). `get_all_versions()` in `intent_crud.py` returns all versions. No new versioning table is needed — only a `source` column addition (Story 36.7).
- The existing `MAX_INTENT_VERSIONS = 2` cap in `src/intent/refinement.py` must be raised to support developer editing loops (Story 36.7a). The cap was designed for automated refinement loops (QA/Assembler), not developer-initiated edits.
- The existing Context stage enrichment data (files affected, complexity, risk flags) is persisted on the TaskPacket or retrievable from Temporal history. If not, the complexity dashboard will need a new API that re-runs context analysis.

---

## Story Map

### Slice 1: Triage Queue (Backend + Frontend)

**Goal:** Developers can review incoming issues before they enter the pipeline. This is the "front door" to the planning experience.

**Backend stories run first; frontend stories follow.**

---

**Story 36.1: Add TRIAGE Status to TaskPacket Model**

Add `TRIAGE = "triage"` to the `TaskPacketStatus` enum. Add transition rules: `TRIAGE -> RECEIVED` (accept), `TRIAGE -> REJECTED` (reject). Write an Alembic-style migration that adds the new enum value. No existing transitions are modified.

- Files to modify: `src/models/taskpacket.py` (enum + ALLOWED_TRANSITIONS)
- Files to create: `src/db/migrations/NNN_add_triage_status.py`
- Tests: Unit test for new transitions; verify existing transitions unchanged
- AC: AC 1

**Story 36.2: Conditional Triage Mode in Webhook Handler**

When `TRIAGE_MODE_ENABLED=true` in settings, the webhook handler creates TaskPackets in `TRIAGE` status and does NOT start a Temporal workflow. When `false` (default), behavior is unchanged (creates in `RECEIVED`, starts workflow). Add the feature flag to `src/settings.py`.

- Files to modify: `src/ingress/webhook_handler.py`, `src/settings.py`
- Tests: Test both modes; verify default behavior unchanged
- AC: AC 1, AC 2

**Story 36.3: Triage Action Endpoints (Accept, Reject, Edit)**

Create three endpoints:
- `POST /api/v1/dashboard/tasks/:id/accept` — transitions TRIAGE -> RECEIVED, starts Temporal workflow
- `POST /api/v1/dashboard/tasks/:id/reject` — transitions TRIAGE -> REJECTED, requires `reason` field
- `PATCH /api/v1/dashboard/tasks/:id` — edits title/description/category/priority while in TRIAGE

All endpoints validate the TaskPacket is in TRIAGE status before acting. Return 409 if status is wrong.

- Files to create: `src/dashboard/planning_router.py` (or extend Phase 0 dashboard router)
- Files to modify: `src/models/taskpacket_crud.py` (add accept/reject CRUD functions)
- Tests: API tests for each endpoint; 409 on wrong status; reject requires reason
- AC: AC 2, AC 3, AC 4
- Backend ref: B-2.1, B-2.2, B-2.4, B-2.5, B-2.6

**Story 36.4: Context Pre-Scan for Triage Enrichment**

When a TaskPacket is created in TRIAGE status, run a lightweight synchronous pre-scan that produces: estimated file count, complexity hint (low/medium/high), and cost estimate range. Store these on the TaskPacket as `triage_enrichment` JSON field. This is NOT the full Context stage — it is a fast heuristic.

- Files to create: `src/context/prescan.py`
- Files to modify: `src/ingress/webhook_handler.py` (call prescan after TRIAGE creation), `src/models/taskpacket.py` (add `triage_enrichment` nullable JSON column)
- Tests: Unit test prescan produces expected shape; integration test that webhook populates enrichment
- AC: AC 1
- Backend ref: B-2.7

**Story 36.5: Triage Queue Frontend Component**

React component that fetches `GET /api/v1/dashboard/tasks?status=triage` and renders a card list. Each card shows: issue number, title, age, labels, reporter, truncated description, complexity/risk/cost from pre-scan. Three action buttons per card: Accept & Plan, Edit Before Accept, Reject. Clicking Accept calls the accept endpoint. Clicking Reject opens a dropdown for reason selection, then calls reject. Clicking Edit opens a side panel.

- Files to create: `frontend/src/components/planning/TriageQueue.tsx`, `frontend/src/components/planning/TriageCard.tsx`, `frontend/src/components/planning/RejectDialog.tsx`, `frontend/src/components/planning/EditPanel.tsx`
- Tests: Component tests with mocked API responses; verify card rendering; verify action button behavior
- AC: AC 1, AC 2, AC 3, AC 4
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 2

**Story 36.6: Triage SSE Events**

Emit `triage.task.created`, `triage.task.accepted`, `triage.task.rejected` events to NATS when triage actions occur. The triage queue frontend subscribes to these via the Phase 0 SSE bridge to update in real-time without polling.

- Files to modify: `src/dashboard/planning_router.py` (emit events after actions), `src/ingress/webhook_handler.py` (emit on TRIAGE creation)
- Tests: Verify events are published to NATS with correct shape
- AC: AC 1

---

### Slice 2: Intent Specification Review (Backend + Frontend)

**Goal:** The Temporal workflow pauses after Intent Builder, and the developer can review, edit, refine, or reject the spec before the Router runs. This is the highest-value planning feature.

---

**Story 36.7: Add `source` Column to Existing IntentSpecRow**

Add a `source` column (`String`, enum values: `auto`, `developer`, `refinement`, default `auto`) to the existing `intent_spec` table via Alembic migration. The existing multi-row versioning pattern (`IntentSpecRow` with `version` column, `get_all_versions()` in `intent_crud.py`) is preserved — no new table is created. Update `IntentSpecCreate` and `IntentSpecRead` Pydantic schemas to include `source`. Update `create_intent()` to accept `source`.

- Files to modify: `src/intent/intent_spec.py` (add `source` column to `IntentSpecRow`, add to Pydantic schemas), `src/intent/intent_crud.py` (pass `source` through)
- Files to create: `src/db/migrations/NNN_add_intent_source_column.py`
- Tests: Unit tests for source column; verify existing versions default to `auto`; verify `get_all_versions()` returns source
- AC: AC 6
- Backend ref: B-2.12

**Story 36.7a: Raise MAX_INTENT_VERSIONS Cap for Developer Editing**

Increase `MAX_INTENT_VERSIONS` in `src/intent/refinement.py` from 2 to 10 (or make it configurable via settings). The current cap of 2 blocks the developer editing flow: v1 (auto) → v2 (developer edit) → v3 (refinement) would raise `RefinementCapExceededError`. The cap exists to prevent runaway automated refinement loops, but developer-initiated edits are intentional and should not be capped at the same level.

- Files to modify: `src/intent/refinement.py` (raise cap), `src/settings.py` (optional: make configurable)
- Tests: Verify developer can create 5+ versions; verify cap still applies
- AC: AC 6, AC 7

**Story 36.8: Temporal Workflow Wait Point After Intent Stage**

After the `build_intent` activity completes, the workflow enters a wait state listening for one of three signals: `approve_intent`, `edit_intent`, `reject_intent`. The `approve_intent` signal resumes the workflow into the Router stage. The `reject_intent` signal transitions the TaskPacket to REJECTED and terminates the workflow. The `edit_intent` signal is handled in Story 36.10. If `INTENT_REVIEW_ENABLED=false` (default), the wait point is skipped and the workflow proceeds directly to Router (backward compatible).

- Files to modify: `src/workflow/pipeline.py` (add signal handlers + wait point), `src/settings.py` (add `INTENT_REVIEW_ENABLED`)
- Tests: Workflow test with signal; test auto-proceed when disabled; test timeout behavior (no timeout = infinite wait)
- AC: AC 5
- Backend ref: B-2.13

**Story 36.9: Intent Review API Endpoints**

Create endpoints:
- `GET /api/v1/dashboard/tasks/:id/intent` — returns current Intent Specification + version history
- `POST /api/v1/dashboard/tasks/:id/intent/approve` — sends `approve_intent` Temporal signal
- `POST /api/v1/dashboard/tasks/:id/intent/reject` — sends `reject_intent` signal with reason

All endpoints validate the TaskPacket is in INTENT_BUILT status (waiting for review).

- Files to modify: `src/dashboard/planning_router.py`
- Tests: API tests for each endpoint; 409 on wrong status; verify Temporal signal sent
- AC: AC 5
- Backend ref: B-2.8, B-2.10

**Story 36.10: Intent Edit and Refinement Endpoints**

Create endpoints:
- `PUT /api/v1/dashboard/tasks/:id/intent` — accepts edited structured fields (`goal`, `constraints`, `acceptance_criteria`, `non_goals`), creates a new `IntentSpecRow` version with `source: developer` using `create_intent()`, updates the TaskPacket's intent version pointer via `update_intent_version()`
- `POST /api/v1/dashboard/tasks/:id/intent/refine` — accepts `feedback` text, constructs a `RefinementTrigger(source="developer", questions=[feedback])`, calls `refine_intent()`. The new version is stored with `source: refinement`.

Note: `refine_intent()` in `src/intent/refinement.py` requires a `RefinementTrigger` dataclass (not a plain string). The endpoint must construct the trigger. The `RefinementTrigger.source` field should accept `"developer"` in addition to `"qa_agent"` and `"assembler"`.

Neither endpoint approves the spec — the developer must explicitly call `/approve` after editing or reviewing the refinement.

- Files to modify: `src/dashboard/planning_router.py`, `src/intent/intent_crud.py`, `src/intent/refinement.py` (accept `"developer"` source)
- Tests: Edit creates new version with source=developer; refinement constructs RefinementTrigger correctly; version history grows
- AC: AC 6, AC 7
- Backend ref: B-2.9, B-2.11

**Story 36.11: Intent Editor Frontend — Split-Pane View**

React component with two panels. Left panel (read-only): original issue body rendered as Markdown, Context enrichment results (affected files, related PRs, complexity score, risk flags). Right panel: rendered Intent Specification as structured sections — Goal (text block), Constraints (bullet list), Acceptance Criteria (checklist), Non-Goals (bullet list). Four action buttons: Approve & Continue, Edit, Request Refinement, Reject. Version selector dropdown at bottom showing version number, source (auto/developer/refinement), and timestamp.

- Files to create: `frontend/src/components/planning/IntentEditor.tsx`, `frontend/src/components/planning/SourceContext.tsx`, `frontend/src/components/planning/IntentSpec.tsx`, `frontend/src/components/planning/VersionSelector.tsx`
- Tests: Component tests; verify split-pane layout; verify structured sections render; verify action buttons call correct endpoints
- AC: AC 5, AC 6
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 3

**Story 36.12: Intent Editor Frontend — Edit Mode and Refinement**

When "Edit" is clicked, the right panel switches to a structured form: Goal (textarea), Constraints (editable list with add/remove), Acceptance Criteria (editable list with add/remove), Non-Goals (editable list with add/remove). Save calls `PUT` with the structured fields JSON and creates a new version with `source: developer`. "Request Refinement" opens a modal with a feedback text input; submitting calls the refine endpoint. After refinement returns a new version, the right panel re-renders the updated spec. Version dropdown allows viewing and diffing any two versions (diff highlights changed fields and list item additions/removals).

- Files to create: `frontend/src/components/planning/IntentEditMode.tsx`, `frontend/src/components/planning/RefinementModal.tsx`, `frontend/src/components/planning/VersionDiff.tsx`
- Tests: Edit mode toggles; structured form renders fields; save calls PUT with correct JSON shape; refinement calls POST; version diff renders
- AC: AC 6, AC 7
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 3

---

### Slice 3: Complexity Dashboard + Expert Routing Preview

**Goal:** Developers see risk before they approve. This slice is informational (complexity) + decisional (routing approval).

---

**Story 36.13: Complexity Dashboard Frontend**

React component that renders Context stage enrichment data as a visual dashboard. Components: overall complexity score bar (color-coded), three metric cards (files affected, dependency depth, test gaps), file impact heatmap (tree view with intensity bars), risk flags checklist. All data comes from the TaskPacket's Context enrichment fields (already stored after Context stage).

- Files to create: `frontend/src/components/planning/ComplexityDashboard.tsx`, `frontend/src/components/planning/MetricCard.tsx`, `frontend/src/components/planning/FileHeatmap.tsx`, `frontend/src/components/planning/RiskFlags.tsx`
- Tests: Component tests with mock data; verify score bar colors; verify risk flag rendering
- AC: AC 8
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 4

**Story 36.14: Routing Result API and Temporal Wait Point**

Create `GET /api/v1/dashboard/tasks/:id/routing` endpoint that returns the Router's expert selection result: list of experts with role name, mandate, assigned files, selection reason (MANDATORY/AUTO), and reputation weight. Add a Temporal workflow wait point after Router stage (gated by `ROUTING_REVIEW_ENABLED` feature flag). Add `POST .../routing/approve` and `POST .../routing/override` (add/remove AUTO experts) endpoints.

- Files to modify: `src/workflow/pipeline.py` (add routing wait point + signals), `src/dashboard/planning_router.py`, `src/settings.py` (add `ROUTING_REVIEW_ENABLED`)
- Files to create: `src/routing/routing_result.py` (Pydantic schema for API serialization)
- Tests: API tests; workflow signal tests; override adds/removes experts; MANDATORY experts cannot be removed
- AC: AC 9
- Backend ref: B-2.14, B-2.15, B-2.16

**Story 36.15: Expert Routing Preview Frontend**

React component showing: expert list with detail cards (role, mandate, files, reason, weight), Approve Routing button, Add Expert dropdown (available roles not already selected), Remove Expert button on AUTO experts (with confirmation). MANDATORY experts show a lock icon.

- Files to create: `frontend/src/components/planning/RoutingPreview.tsx`, `frontend/src/components/planning/ExpertCard.tsx`, `frontend/src/components/planning/AddExpertDropdown.tsx`
- Tests: Component tests; verify MANDATORY lock; verify remove confirmation; verify approve calls endpoint
- AC: AC 9
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 5

---

### Slice 4: Backlog Board + Manual Task Creation

**Goal:** Big-picture view of all work and the ability to create tasks without GitHub issues.

---

**Story 36.16: Backlog Board Frontend — Kanban View**

React component rendering a six-column Kanban board: Triage, Planning, Building, Verify, Done, Rejected. Each column queries `GET /api/v1/dashboard/tasks?status=...` (mapping column to status group). Cards show: issue number, title, category badge, complexity, cost. Click card opens detail view (routes to TaskPacket detail page or opens right panel).

- Files to create: `frontend/src/components/planning/BacklogBoard.tsx`, `frontend/src/components/planning/BoardColumn.tsx`, `frontend/src/components/planning/BoardCard.tsx`
- Tests: Component tests; verify column rendering; verify card detail navigation
- AC: AC 10
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 6

**Story 36.17: Board State Persistence**

`POST /api/v1/dashboard/board/preferences` persists column width, collapse state, and sort order per column. `GET /api/v1/dashboard/board/preferences` retrieves them. Stored in PostgreSQL (`board_preferences` table). Defaults are provided if no preferences are saved.

- Files to create: `src/dashboard/board_router.py`, `src/db/migrations/NNN_board_preferences.py`
- Tests: Save and retrieve preferences; defaults work when no preferences exist
- AC: AC 10
- Backend ref: B-2.18

**Story 36.18: Manual Task Creation Endpoint**

`POST /api/v1/dashboard/tasks` creates a TaskPacket without a GitHub issue. Required fields: `title`, `description`. Optional: `category`, `priority`, `acceptance_criteria` (list of strings), `skip_triage` (boolean, default false). When `skip_triage=true`, the TaskPacket is created in `RECEIVED` status and a Temporal workflow starts immediately. When false, it enters TRIAGE.

- Files to modify: `src/dashboard/planning_router.py`, `src/models/taskpacket_crud.py`
- Tests: Create with minimal fields; create with all fields; skip_triage starts workflow; non-skip enters TRIAGE
- AC: AC 11
- Backend ref: B-2.3

**Story 36.19: Manual Task Creation Frontend**

Modal dialog with fields: title (required), description (Markdown textarea with preview toggle, required), category dropdown, priority dropdown, acceptance criteria (add/remove list), Skip Triage checkbox. Form validation on submit. Calls the manual creation endpoint.

- Files to create: `frontend/src/components/planning/CreateTaskModal.tsx`, `frontend/src/components/planning/MarkdownField.tsx`
- Tests: Form validation; submit calls API; skip triage checkbox behavior
- AC: AC 11
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 7

**Story 36.20: Historical Comparison Query (Stretch)**

`GET /api/v1/dashboard/tasks/:id/comparison` returns stats from similar past TaskPackets (same category + similar complexity): average cost, average time, average loopbacks, success rate. Only returns data when >5 similar tasks exist. This is a stretch story — it depends on sufficient historical data.

- Files to create: `src/dashboard/analytics_queries.py`
- Tests: Returns empty when <5 similar tasks; returns correct aggregation when data exists
- AC: AC 8 (informational enrichment)
- Backend ref: B-2.17

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS (2026-03-21)

**Overall Verdict: CONDITIONAL PASS — 5 blockers must be fixed before implementation begins.**

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Is the goal statement specific enough to test against? | **CONDITIONAL PASS** | Three testable decision points (triage, intent review, routing review) are well-defined. Missing: kill criterion — what outcome after MVP delivery triggers stop/pivot? |
| 2 | Are acceptance criteria testable at epic scale? | **CONDITIONAL PASS** | ACs 1-4 (Triage) are excellent — specific endpoints, status codes, transitions. ACs 5-7 (Intent) assume a Markdown body field that does not exist in `IntentSpecRow`. Must reconcile structured-fields vs Markdown before implementation. |
| 3 | Are non-goals explicit? | **PASS** | 8 explicit non-goals, well-bounded, with deferral targets. No issues. |
| 4 | Are dependencies identified with owners and dates? | **FAIL** | Phase 0/1 listed as "Not yet built" — both are COMPLETE. No milestone dates for slice boundaries. No target completion date. 8-10 week estimate with no anchor date. |
| 5 | Are success metrics measurable? | **CONDITIONAL PASS** | 4 of 6 metrics are measurable after new columns exist. "Rework reduction 20%" requires a baseline with insufficient sample size. Planning dwell time needs `approve_intent` signal timestamp storage not yet designed. |
| 6 | Can an AI agent implement without guessing? | **FAIL** | 5 source code discrepancies would cause an agent to build the wrong data model, call the wrong function signature, and hit an undocumented version cap. |
| 7 | Is the narrative compelling? | **PASS** | Clear problem statement, logical phase ordering, explicit MVP scope, strong "why now" argument. Best part of the epic. |

---

### Critical Discrepancies Found

**1. IntentSpec data model mismatch (Blocker)**
Story 36.7, AC 6 assume `intent_spec_version` stores a `body (text, Markdown)` column. Frontend stories describe editing Markdown. But `IntentSpecRow` stores **structured fields**: `goal` (String 2000), `constraints` (JSON list), `acceptance_criteria` (JSON list), `non_goals` (JSON list). No Markdown body exists.

**2. refine_intent() signature mismatch (Blocker)**
Story 36.10 and Assumptions claim `refine_intent()` "already accepts feedback." Actual signature requires a `RefinementTrigger` dataclass with `source`, `questions`, `triggering_defects`, and `triggering_conflict` — not a simple feedback text string.

**3. MAX_INTENT_VERSIONS = 2 cap (Blocker)**
`src/intent/refinement.py` line 29 enforces `MAX_INTENT_VERSIONS = 2`. Developer editing and refinement loops would create 3+ versions, raising `RefinementCapExceededError`. Epic does not mention this cap.

**4. Dependency table is STALE (Blocker)**
Phase 0 (SSE bridge + dashboard API router) and Phase 1 (Pipeline Rail + TaskPacket list API) are listed as "Not yet built." Both are **COMPLETE**. Dashboard router exists at `src/dashboard/router.py`. React app exists at `frontend/src/` with 20+ components. Risk R3 is moot.

**5. Parallel versioning system conflict (Blocker)**
Risk R5 says "the intent_spec table stores one row per TaskPacket." This is wrong. `intent_crud.py` already has `get_all_versions()` returning multiple `IntentSpecRow` rows with incrementing `version` fields. The proposed `intent_spec_version` table would create a **parallel versioning system**.

**6. ConsultPlan serialization (Noted, not blocking)**
Story 36.14 correctly notes a serialization adapter may be needed. `ConsultPlan` is a frozen dataclass with `tuple` fields. Story includes creating `routing_result.py`, which addresses this.

---

### What Must Be Fixed Before Commit

**Blockers (all FIXED 2026-03-21):**

1. ~~**Reconcile IntentSpec data model.**~~ **FIXED:** ACs 5-7, Stories 36.7, 36.10-36.12 updated to use structured fields (`goal`, `constraints`, `acceptance_criteria`, `non_goals`). No Markdown body.
2. ~~**Fix refine_intent() assumption.**~~ **FIXED:** Story 36.10 now documents constructing `RefinementTrigger(source="developer", questions=[feedback])`. Assumptions section updated.
3. ~~**Address MAX_INTENT_VERSIONS = 2 cap.**~~ **FIXED:** New Story 36.7a added to raise cap from 2 to 10 (or configurable). AC 7 references this.
4. ~~**Update dependency table.**~~ **FIXED:** Dependencies table shows Phase 0/1 as COMPLETE with file paths. Risk R3 marked RESOLVED. Risk R5 marked RESOLVED.
5. ~~**Decide on versioning architecture.**~~ **FIXED:** Story 36.7 rewritten to add `source` column to existing `IntentSpecRow` table. No new `intent_spec_version` table. Assumptions updated.

**Should Fix (partially addressed):**

6. ~~Add kill criterion.~~ **FIXED:** Kill criterion added to epic header: "<30% intent review adoption within 2 weeks → pivot to auto-approve with notification."
7. Add milestone dates (at minimum: Slice 1+2 MVP target, Slice 3+4 target). → **Deferred to Helm sprint planning.**
8. Revise "rework reduction 20%" metric — add minimum sample size or replace with a leading indicator. → **Open — insufficient baseline data until pipeline processes 20+ real issues.**

---

### Round 2: PASS (2026-03-21)

**Overall Verdict: PASS — All 7 questions pass. Epic approved for sprint planning.**

| # | Question | R1 Verdict | R2 Verdict | Detail |
|---|----------|------------|------------|--------|
| 1 | Goal statement testable? | CONDITIONAL | **PASS** | Kill criterion added: <30% intent review adoption → pivot. |
| 2 | Acceptance criteria testable? | CONDITIONAL | **PASS** | ACs 5-7 corrected to reference structured fields. All 11 ACs specify endpoints, HTTP verbs, status codes. |
| 3 | Non-goals explicit? | PASS | **PASS** | Unchanged. 8 explicit non-goals. |
| 4 | Dependencies identified? | FAIL | **PASS** | Phase 0/1 marked COMPLETE with file paths. Risks R3/R5 RESOLVED. |
| 5 | Success metrics measurable? | CONDITIONAL | **PASS** | `intent_spec.source` column enables 4/6 metrics directly. Rework baseline gap acknowledged. |
| 6 | AI agent can implement? | FAIL | **PASS** | All 5 source code discrepancies resolved. Stories reference correct file paths, signatures, schemas. 3 copy-edit residues fixed. |
| 7 | Narrative compelling? | PASS | **PASS** | Unchanged. Strong "why now" argument. |

**Blocker verification:** All 5 Round 1 blockers verified fixed against source code. No new architectural issues.

**Status:** Epic 36 is **APPROVED** for Helm sprint planning. Recommended start: Slice 1 (Triage Queue) backend stories.
