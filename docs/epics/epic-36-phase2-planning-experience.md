# Epic 36: Phase 2 — Planning Experience

> **Status:** Draft — Awaiting Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 8-10 weeks (backend + frontend in series)
> **Created:** 2026-03-20
> **Depends On:** Phase 0 (SSE scaffolding), Phase 1 (Pipeline Visibility)
> **Meridian Review:** Round 1: Pending

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

After the Intent Builder produces a draft spec, the Temporal workflow pauses (new wait point after Intent stage). A `GET /api/v1/dashboard/tasks/:id/intent` endpoint returns the Intent Specification with version history. The frontend displays a split-pane view: source context (issue body, affected files, complexity) on the left, rendered Intent Specification on the right. `POST /api/v1/dashboard/tasks/:id/intent/approve` sends a Temporal signal that resumes the workflow into the Router stage.

### AC 6: Intent Specification Editing

`PUT /api/v1/dashboard/tasks/:id/intent` accepts a developer-edited Intent Specification body. Each edit creates a new version (stored in PostgreSQL with timestamp and `source: developer`). Version history is visible in the UI via a dropdown showing v1, v2, v3... with timestamps and diff view between versions.

### AC 7: Intent Refinement Loop

`POST /api/v1/dashboard/tasks/:id/intent/refine` accepts a `feedback` text field and triggers the Intent Builder to re-run with the developer's notes. The new spec version is stored with `source: refinement`. The workflow remains paused until the developer approves the refined version.

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
| R3 | The frontend depends on Phase 0 (SSE bridge) and Phase 1 (dashboard API scaffolding) — if those are not yet built, frontend stories are blocked | High — calendar slip | Backend stories in this epic are independent of the React frontend. Start backend Slice 1 immediately. Frontend stories can begin once Phase 1 scaffolding exists. |
| R4 | Context stage pre-scan (lightweight complexity/cost estimate for triage cards) may require a new Temporal activity or significant refactoring of the existing Context stage | Medium — scope creep | For MVP, use a synchronous function call at webhook time (not a full Temporal workflow) that does file-impact heuristics. The full Context stage runs after acceptance. |
| R5 | Intent Specification version storage is new — no versioning exists today; the `intent_spec` table stores one row per TaskPacket | Medium — data model change | New `intent_spec_version` table with FK to `intent_spec`. The existing `intent_spec` table becomes the "latest" pointer. |

---

## 5. Constraints & Non-Goals

### Constraints

- **Phase 0 and Phase 1 must be delivered first.** The dashboard API router (`/api/v1/dashboard/`), SSE bridge, and React scaffolding are prerequisites. Backend stories in this epic that add new API endpoints mount on the router established in Phase 0.
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
| **Intent review rate** | 80%+ of tasks have developer-reviewed Intent Specifications (approved or edited) | Count of TaskPackets with `intent_spec_version.source IN ('developer', 'refinement')` or explicit approval signal / total TaskPackets past Intent stage |
| **Triage rejection rate** | >0% — proves developer is exercising judgment, not rubber-stamping | Count of REJECTED TaskPackets with triage-stage rejection reason / total TaskPackets entering triage |
| **Planning stage dwell time** | Median < 5 minutes from intent spec ready to developer approval | Timestamp diff between `pipeline.stage.exit(intent)` event and `approve_intent` signal receipt |
| **Rework reduction** | 20% fewer loopbacks from Verification/QA back to Implement (compared to pre-triage baseline) | Loopback count per TaskPacket, averaged over rolling 30-day windows |
| **Intent edit rate** | >10% of Intent Specifications are developer-edited (not just approved as-is) | Count of TaskPackets with `intent_spec_version.source = 'developer'` / total approved |
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
| Phase 0: SSE bridge + dashboard API router | Not yet built | Frontend stories blocked; backend stories can proceed independently by mounting on the existing FastAPI app |
| Phase 1: Pipeline Rail + TaskPacket list API | Not yet built | Backlog board (Slice 4) reuses the `GET /api/v1/dashboard/tasks` endpoint from Phase 1. If Phase 1 is not done, this endpoint must be built in Slice 4. |
| Temporal SDK signal handling | Available (used by `approve_publish`) | New wait points follow the same pattern |
| PostgreSQL + SQLAlchemy async | Available | New tables (intent_spec_version, board_state) use existing migration framework |
| React + Vite scaffolding (Phase 0) | Not yet built | Frontend stories blocked |
| NATS JetStream | Available | SSE events for real-time triage queue updates |

### Systems Affected

| System | Change |
|--------|--------|
| `src/models/taskpacket.py` | Add `TRIAGE` status to enum; add transitions `TRIAGE -> RECEIVED` and `TRIAGE -> REJECTED` |
| `src/ingress/webhook_handler.py` | Conditional: create in TRIAGE (when enabled) instead of RECEIVED; skip workflow start |
| `src/workflow/pipeline.py` | Add wait points after Intent and Router stages (new signal handlers: `approve_intent`, `approve_routing`) |
| `src/workflow/activities.py` | Emit SSE events for intent-ready and routing-ready states |
| `src/intent/intent_spec.py` | Add `IntentSpecVersionRow` model for version history |
| `src/intent/intent_crud.py` | Add version CRUD (create version, list versions, get diff) |
| `src/routing/` | Add API-serializable routing result model (experts, reasons, weights) |
| `src/dashboard/` (new) | New package with planning API endpoints (or extends Phase 0 dashboard router) |
| `src/context/` | Add lightweight pre-scan function for triage card enrichment |
| `src/db/migrations/` | New migration for `TRIAGE` status, `intent_spec_version` table, `board_state` table |
| `frontend/src/` (new, from Phase 0) | Triage queue, intent editor, complexity dashboard, routing preview, backlog board, task creation modal |

### Assumptions

- The Phase 0 dashboard API router exists at `/api/v1/dashboard/` by the time backend stories in this epic are ready to merge. If not, backend stories will mount on a temporary router that gets merged into the Phase 0 structure later.
- The Intent Builder (`src/intent/intent_builder.py`) can be called with additional `developer_feedback` text for the refinement loop without major refactoring. The existing `refine_intent()` function in `src/intent/refinement.py` already accepts feedback.
- The Router (`src/routing/`) produces a structured result that can be serialized to JSON for the API. If the current router returns opaque internal objects, a serialization adapter will be needed.
- The Temporal workflow is structured such that inserting a wait point between activities is feasible without rewriting the workflow definition. The existing `approve_publish` wait point after QA validates this pattern.
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

**Story 36.7: Intent Specification Version Storage**

Create `intent_spec_version` table: `id (UUID PK)`, `intent_spec_id (FK)`, `version_number (int)`, `body (text, Markdown)`, `source (enum: auto, developer, refinement)`, `created_at (timestamptz)`. Add CRUD: create version, list versions by intent_spec_id, get specific version. The existing `intent_spec` table is unchanged (remains the "latest" pointer).

- Files to create: `src/intent/intent_version.py` (model + Pydantic schemas), `src/db/migrations/NNN_intent_spec_versions.py`
- Files to modify: `src/intent/intent_crud.py` (add version CRUD)
- Tests: Unit tests for version creation, listing, ordering
- AC: AC 6
- Backend ref: B-2.12

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
- `PUT /api/v1/dashboard/tasks/:id/intent` — accepts edited Markdown body, creates new version with `source: developer`, updates the intent_spec row
- `POST /api/v1/dashboard/tasks/:id/intent/refine` — accepts `feedback` text, calls `refine_intent()` with developer notes, stores result as new version with `source: refinement`

Neither endpoint approves the spec — the developer must explicitly call `/approve` after editing or reviewing the refinement.

- Files to modify: `src/dashboard/planning_router.py`, `src/intent/intent_crud.py`
- Tests: Edit creates new version; refinement calls intent builder with feedback; version history grows
- AC: AC 6, AC 7
- Backend ref: B-2.9, B-2.11

**Story 36.11: Intent Editor Frontend — Split-Pane View**

React component with two panels. Left panel (read-only): original issue body rendered as Markdown, Context enrichment results (affected files, related PRs, complexity score, risk flags). Right panel: rendered Intent Specification in sections (Goal, Constraints, Acceptance Criteria, Validation Strategy). Four action buttons: Approve & Continue, Edit, Request Refinement, Reject. Version selector dropdown at bottom.

- Files to create: `frontend/src/components/planning/IntentEditor.tsx`, `frontend/src/components/planning/SourceContext.tsx`, `frontend/src/components/planning/IntentSpec.tsx`, `frontend/src/components/planning/VersionSelector.tsx`
- Tests: Component tests; verify split-pane layout; verify action buttons call correct endpoints
- AC: AC 5, AC 6
- Frontend ref: 01-PLANNING-EXPERIENCE.md Section 3

**Story 36.12: Intent Editor Frontend — Edit Mode and Refinement**

When "Edit" is clicked, the right panel switches to a textarea with the spec's Markdown source. Save creates a new version via PUT. "Request Refinement" opens a modal with a feedback text input; submitting calls the refine endpoint. After refinement returns a new version, the right panel re-renders the updated spec. Version dropdown allows viewing and diffing any two versions.

- Files to create: `frontend/src/components/planning/IntentEditMode.tsx`, `frontend/src/components/planning/RefinementModal.tsx`, `frontend/src/components/planning/VersionDiff.tsx`
- Tests: Edit mode toggles; save calls PUT; refinement calls POST; version diff renders
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

### Round 1: Pending

_This epic has not yet been reviewed by Meridian. Review is required before implementation begins._

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Is the goal statement specific enough to test against? | Pending | |
| 2 | Are acceptance criteria testable at epic scale? | Pending | |
| 3 | Are non-goals explicit? | Pending | |
| 4 | Are dependencies identified with owners and dates? | Pending | |
| 5 | Are success metrics measurable with existing instrumentation? | Pending | |
| 6 | Can an AI agent implement this epic without guessing scope? | Pending | |
| 7 | Is the narrative compelling enough to justify the investment? | Pending | |
