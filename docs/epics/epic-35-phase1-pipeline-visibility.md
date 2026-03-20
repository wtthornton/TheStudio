# Epic 35: Phase 1 -- Pipeline Visibility

> **Status:** Draft (Pending Meridian Review)
> **Epic Owner:** Primary Developer
> **Duration:** 8-10 weeks (incl. backend)
> **Created:** 2026-03-20
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**Developers See Every TaskPacket Flow Through the Pipeline in Real Time**

---

## 2. Narrative

TheStudio processes GitHub issues through a 9-stage pipeline -- Intake through Publish -- producing evidence-backed draft PRs. Today this pipeline is invisible. A developer sends in an issue and waits. They cannot see which stage their work is in, whether a gate passed or failed, why a loopback occurred, or what the agent is doing right now. The admin panel shows workflow lists and cost tables, but nothing that answers the three questions that matter: *Where is my work? Is it healthy? What is happening?*

This blindness has real consequences. When a gate fails and triggers a loopback, the developer has no way to know without checking Temporal UI directly. When the agent spends 8 minutes in the Implement stage, there is no indication whether it is stuck or making progress. When a verification gate catches a test failure, the defect evidence is buried in Temporal history rather than surfaced in a UI the developer actually uses.

Competitors have noticed this gap. Devin shows a replay timeline. Factory AI has a Command Center. Codegen 3.0 ships analytics dashboards. But none of them show what TheStudio can show: a governed multi-stage pipeline with explicit gates, evidence artifacts, and loopback self-healing. The pipeline *is* the differentiator -- but only if the developer can see it.

This epic delivers the core pipeline visualization layer: a Pipeline Rail showing all 9 stages with live status, a TaskPacket Timeline showing the journey of each work item, a Gate Inspector making every gate decision auditable, a Live Activity Stream showing what the agent is doing, loopback visualization making self-healing visible, and a minimap for quick navigation between active tasks. The backend delivers the APIs and event emission that power all of these views.

**Why now:** Phase 0 (Epic 34, not yet written) establishes the SSE-over-NATS bridge and React scaffolding. This epic is the first real payload over that bridge. Every subsequent phase (Planning, Controls, GitHub Integration, Analytics) builds on the components delivered here. The Pipeline Rail is the home screen. The SSE event vocabulary defined here is the contract for all future real-time features. Getting this right first means every phase after it composes rather than reworks.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Pipeline UI Master Vision | `docs/design/00-PIPELINE-UI-VISION.md` (Section 8, Phase 1) |
| Pipeline Visualization Design Spec | `docs/design/02-PIPELINE-VISUALIZATION.md` (all sections) |
| Backend Requirements | `docs/design/06-BACKEND-REQUIREMENTS.md` (Section 3, Phase 1: B-1.1 through B-1.14) |
| Technology Architecture | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` |
| TaskPacket model | `src/models/taskpacket.py` |
| Existing NATS event emission | `src/verification/signals.py`, `src/qa/signals.py` |
| Workflow activities | `src/workflow/activities.py` |
| Agent framework (cost tracking) | `src/agent/framework.py` |
| Pipeline workflow | `src/workflow/pipeline.py` |
| Competitive analysis (Devin, Factory, Codegen, Aperant) | `docs/design/00-PIPELINE-UI-VISION.md` Section 2 |
| Temporal UI timeline inspiration | `docs/design/02-PIPELINE-VISUALIZATION.md` Section 3.3 |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` |
| Architecture overview | `thestudioarc/00-overview.md` |

---

## 4. Acceptance Criteria

### AC 1: Pipeline Rail Shows Live Stage Status

A 9-node horizontal pipeline visualization renders on the dashboard home page. Each node displays the stage name, a status indicator (idle/active/review/passed/failed), and a count of TaskPackets currently in that stage. Nodes connect via directional arrows. When a TaskPacket enters or exits a stage, the display updates within 2 seconds via SSE without a page refresh. A header bar shows total active tasks, queued tasks, and running cost.

### AC 2: Stage Detail Panel Surfaces Active Work

Clicking any stage node opens a slide-in panel showing: all TaskPackets currently in that stage with progress indicators, the model and agent assigned, cost-so-far per TaskPacket, and stage-level metrics (pass rate, average time, throughput over the last 30 days). Each TaskPacket in the panel links to its full timeline.

### AC 3: TaskPacket Timeline Tells the Full Story

A timeline view for any TaskPacket shows every stage it has passed through as a horizontal duration bar, proportional to time spent. Each completed stage shows its gate result (pass/fail icon + summary). The currently active stage shows the last 5 activity entries inline. Queued stages render as dashed/gray placeholders. A header shows TaskPacket ID, title, current status with percentage, total elapsed time, and total cost.

### AC 4: Gate Inspector Makes Every Decision Auditable

A dedicated gate view lists all gate transitions across all TaskPackets in reverse chronological order. Each entry shows: pass/fail, TaskPacket ID, the transition (from stage to stage), timestamp, and issue count. Clicking a gate entry expands to show every check performed (lint, type check, pytest, security scan), per-check results, the gate decision rule that fired, the action taken (pass or loopback + target), and defect categorization. Filters allow narrowing by pass/fail, TaskPacket, stage, and date range. A summary panel shows pass rate, average issues per gate, top failure type, and loopback rate.

### AC 5: Activity Stream Shows Agent Work in Progress

For any active Implement, Verify, or QA stage, a real-time activity stream renders structured entries: file reads, file edits (with 3-line diff preview), searches, test runs (with pass/fail counts), shell commands, agent reasoning, and LLM calls. Entries group under collapsible subphases (Context Gathering, Implementation, Testing). The stream auto-scrolls when the user is at the bottom and preserves scroll position when the user scrolls up. A filter bar allows toggling entry types and searching within entries.

### AC 6: Loopbacks Are Visible and Traceable

When a gate fails and triggers a loopback, the Pipeline Rail shows an animated arc from the failing stage back to the target stage with a badge (TaskPacket ID, reason, attempt count). The TaskPacket Timeline shows loopback entries with backward arrows and attempt counters. If max loopbacks are reached, the UI shows an escalation indicator. When a loopback resolves, the arc fades.

### AC 7: Minimap Enables Quick Task Switching

A persistent bottom bar shows all in-flight TaskPackets as compact cards (status dot, ID, title, current stage, progress, cost). Clicking a card navigates to that TaskPacket's timeline. Cards scroll horizontally for overflow. The bar is collapsible.

### AC 8: Error and Empty States Are First-Class

SSE disconnection shows a reconnection banner with retry count and marks all stage data as stale. API failures render error cards scoped to the affected panel, not full-page errors. Empty states for Pipeline Rail, Activity Stream, Gate Inspector, and Minimap show helpful messages with action buttons (import issues, create task). On SSE reconnection, the client requests a full state refresh.

### AC 9: Backend APIs Serve All Dashboard Data

The following REST endpoints exist and return JSON: `GET /api/v1/dashboard/tasks` (paginated, filterable), `GET /api/v1/dashboard/tasks/:id` (detail with stage timestamps and cost), `GET /api/v1/dashboard/tasks/:id/gates` (gate results), `GET /api/v1/dashboard/tasks/:id/activity` (paginated activity log), `GET /api/v1/dashboard/gates` (all gates, filterable), `GET /api/v1/dashboard/gates/:id` (gate detail with evidence). All endpoints require auth consistent with the existing admin auth mechanism.

### AC 10: Backend Emits All Required SSE Events

The pipeline emits structured events to NATS JetStream for: stage enter/exit, gate pass/fail, activity entries (file_read, file_edit, search, test_run, shell, reasoning, llm_call), cost updates, loopback start/resolve. Events flow through the SSE endpoint established in Phase 0. Stage timing data (start/end per stage) is persisted on the TaskPacket model.

---

## 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | SSE event volume overwhelms browser during active Implement stage (hundreds of activity entries per minute) | Medium | High | Virtual scrolling (>500 entries), 50ms debounce on SSE batch rendering, IntersectionObserver to pause off-screen animations |
| R2 | Activity event emission from agent framework requires deep instrumentation that destabilizes the pipeline | Medium | High | Emit events as fire-and-forget NATS publishes (never block agent execution). Wrap in try/except so emission failures are logged, not propagated |
| R3 | Gate evidence not currently persisted in PostgreSQL -- only in NATS + Temporal history, which may lack structure for dashboard queries | High | Medium | B-1.6 stores structured evidence in Postgres. Design schema before starting frontend gate detail view |
| R4 | Phase 0 SSE bridge not yet delivered -- this entire epic is blocked | High | Critical | Phase 0 (Epic 34) must be completed first. Acceptance test: browser displays live stage transitions from a real Temporal workflow |
| R5 | Stage timing data not on TaskPacket model -- metrics queries have no data source | Medium | Medium | B-1.12 adds stage timing early in Slice 1 so all subsequent stories can use it |

---

## 5. Constraints & Non-Goals

### Constraints

- **Phase 0 prerequisite:** The SSE-over-NATS bridge, React scaffolding, and `src/dashboard/` package from Phase 0 (Epic 34) must be delivered before this epic begins. This epic does not create those foundations.
- **Single-user auth:** Uses the same auth mechanism as the existing admin panel. No RBAC, no user accounts, no session management beyond what exists.
- **Desktop-first:** Optimized for desktop viewport (1280px+). Tablet responsive is a stretch goal. Mobile is out of scope.
- **No admin panel changes:** The existing Jinja-based admin panel at `/admin/*` continues to operate unchanged. The new dashboard runs at `/dashboard/*` and `/api/v1/dashboard/*`.
- **SSE event contract:** All SSE events must conform to the event vocabulary defined in `docs/design/02-PIPELINE-VISUALIZATION.md` Section 8 (pipeline.stage_enter, pipeline.stage_exit, pipeline.gate_pass, pipeline.gate_fail, pipeline.activity, pipeline.cost_update, pipeline.loopback.start, pipeline.loopback.resolve).
- **Performance:** Pipeline Rail renders in under 1 second. Activity stream handles 5,000 entries without jank (virtual scrolling required above 500). SSE reconnection replays missed events within 5 seconds.
- **Tech stack:** React + Zustand + Tailwind (per `docs/design/05-TECHNOLOGY-ARCHITECTURE.md`). Backend endpoints use FastAPI with async SQLAlchemy.

### Non-Goals

- **Planning features:** No triage queue, intent editor, manual task creation, or expert routing preview. Those are Phase 2.
- **Pipeline steering:** No pause, resume, redirect, abort, or retry actions. Those are Phase 3.
- **Budget governance:** No budget configuration, alerts, or model downgrade automation. Cost is *displayed* but not *controlled*.
- **Trust tier configuration:** No trust rule builder or tier modification. Tiers are displayed read-only where relevant.
- **GitHub deep integration:** No issue import, PR merge, bidirectional Projects sync, or pipeline comments on issues. Those are Phase 4.
- **Analytics dashboards:** No throughput charts, bottleneck analysis, or reputation dashboard. Those are Phase 5.
- **Keyboard navigation:** Keyboard shortcuts are a polish item, not MVP. Mouse interaction is sufficient for this epic.
- **TaskPacket transition animation:** The "dot slides between nodes" animation is a polish item. Stage status changes are sufficient without animation.
- **Timeline scrubbing:** The Devin-style replay slider is a future enhancement, not in scope.
- **Notifications:** No notification bell, notification list, or notification generation. Phase 3.
- **Custom themes:** Ships with dark mode (primary). Light mode toggle is a stretch goal.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | All implementation (solo developer) |
| Design | Design specs in `docs/design/02-PIPELINE-VISUALIZATION.md` | Reference only -- no separate design review cycle |
| Tech Lead | Primary Developer | Architecture decisions, SSE event schema, API contracts |
| QA | Automated tests (pytest + Playwright/testing-library) | Unit tests for components, integration tests for API endpoints, E2E for SSE flow |
| Meridian (Review) | Meridian persona | Epic review before implementation begins |
| Helm (Planning) | Helm persona | Sprint decomposition and session prompts |

---

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Pipeline stage identification | Pipeline Rail renders current stage of any TaskPacket within 1 render cycle of SSE event | Playwright: trigger stage_enter event, assert stage node shows "active" status within 2s |
| Gate transparency | 100% of gate transitions have visible, drill-down evidence in Gate Inspector | Playwright: trigger gate event, assert Gate Inspector entry count matches NATS event count |
| Real-time latency | Stage transitions appear in browser within 2 seconds of Temporal activity completion | Automated: timestamp comparison in integration test (NATS publish time vs browser render callback) |
| Activity stream rendering | Activity stream displays latest entry within 1 render cycle of SSE event | Playwright: emit activity event, assert entry appears in stream container within 2s |
| Error resilience | SSE disconnection shows stale banner within 5 seconds; reconnection restores state within 10 seconds | Playwright: intercept SSE connection, assert stale banner visible, restore connection, assert banner dismissed |
| API response time | All dashboard API endpoints respond in < 500ms for datasets up to 1,000 TaskPackets | pytest load test with seeded data |
| Loopback visibility | Every loopback event shows on both Pipeline Rail (arc) and TaskPacket Timeline (backward entry) | Playwright: trigger loopback event, assert arc element and timeline entry both exist |
| Component test coverage | > 80% line coverage on new frontend components and backend endpoints | pytest + vitest coverage reports |

---

## 8. Context & Assumptions

### Business Rules

- Gates fail closed. The Gate Inspector must show "fail" as the default for any gate that did not explicitly pass.
- Loopbacks carry evidence. The loopback arc and timeline entry must include the defect report from the failing gate.
- TaskPacket is the single source of truth. All dashboard views derive their data from the TaskPacket model and its associated events.
- The 9-stage pipeline is fixed (Intake, Context, Intent, Router, Assembler, Implement, Verify, QA, Publish). The Pipeline Rail layout is static, not dynamic.

### Dependencies

- **Phase 0 (Epic 34):** SSE-over-NATS bridge (`GET /api/v1/dashboard/events/stream`), `Last-Event-ID` reconnection, `src/dashboard/` package with FastAPI router, React + Zustand + Tailwind scaffolding, `pipeline.stage.enter`/`pipeline.stage.exit` events from Temporal activities, `pipeline.gate.pass`/`pipeline.gate.fail` events. **This is a hard blocker.**
- **PostgreSQL:** Existing database with TaskPacket, ModelCallAudit, and related models. New models added: `ActivityEntry` (B-1.8), `GateEvidence` (B-1.6), stage timing fields on TaskPacket (B-1.12).
- **NATS JetStream:** Existing streams for verification/QA signals. New subjects added: `pipeline.activity.*`, `pipeline.cost.*`, `pipeline.loopback.*`.
- **Temporal:** Workflow activities instrumented to emit NATS events. No new Temporal signals or wait points required (those are Phase 2/3).

### Systems Affected

| System | Changes |
|--------|---------|
| `src/dashboard/` | New package: REST API endpoints (B-1.1 through B-1.5, B-1.10, B-1.13, B-1.14) |
| `src/workflow/activities.py` | Instrument to emit `pipeline.activity` events (B-1.7) |
| `src/agent/framework.py` | Instrument to emit structured tool call activity events (B-1.7) |
| `src/agent/framework.py` | Emit `pipeline.cost_update` on model call completion (B-1.9) |
| `src/workflow/pipeline.py` | Emit `pipeline.loopback.start` and `pipeline.loopback.resolve` events (B-1.11) |
| `src/models/taskpacket.py` | Add stage timing fields (B-1.12) |
| `src/db/` | New models: `ActivityEntry`, `GateEvidence` + migrations (B-1.6, B-1.8) |
| `frontend/` | New React app (Pipeline Rail, Timeline, Activity Stream, Gate Inspector, Loopback Viz, Minimap, Error States) |

### Assumptions

- Phase 0 delivers a working SSE endpoint that the browser can connect to and receive events from. If Phase 0 is not complete, this epic cannot start.
- The existing admin panel auth (HTTP Basic Auth behind Caddy) is sufficient for Phase 1. No changes to auth are needed.
- The `ActivityEntry` model caps at 5,000 entries per TaskPacket (older entries are pruned on write). This is acceptable for Phase 1.
- Gate evidence stored in PostgreSQL duplicates data available in NATS/Temporal history. This duplication is intentional -- the dashboard needs fast queryable access, not stream replay.
- A solo developer will work backend and frontend in series within each slice, not in parallel.

---

## Story Map

Stories are organized into 4 vertical slices. Each slice delivers end-to-end value. MVP stories are marked with **(MVP)**. Polish stories are unmarked.

### Slice 1: Pipeline Rail (Static + SSE + Stage Detail Panel)

The home screen. A developer opens the dashboard and sees all 9 pipeline stages with live status. They click a stage and see what is in it.

#### Backend Stories (Slice 1)

| # | Story | AC | Est. | Backend Ref |
|---|-------|----|------|-------------|
| S1.B1 | **Add stage timing fields to TaskPacket model** (start/end timestamp per stage, migration) | Stage entry/exit timestamps persisted. Migration runs cleanly on existing data (nulls for historical records). | M | B-1.12 |
| S1.B2 | **`GET /api/v1/dashboard/tasks` -- List TaskPackets** with pagination (offset/limit), filtering by status, date range, category. Returns JSON array with id, title, status, current_stage, created_at, cost_total. | Endpoint returns paginated results. Filter by status returns only matching records. Empty result returns `[]`, not error. Auth required. | M | B-1.1 |
| S1.B3 | **`GET /api/v1/dashboard/tasks/:id` -- TaskPacket detail** with current status, all stage timestamps, cost breakdown by stage, model used per stage. | Endpoint returns full detail including stage_timings array. 404 for unknown ID. | S | B-1.2 |
| S1.B4 | **Pipeline stage metrics aggregation** -- query returning per-stage pass rate, average duration, throughput (tasks/day) over configurable window (default 30 days). | `GET /api/v1/dashboard/stages/metrics` returns 9-element array (one per stage). Metrics computed from persisted stage timing and gate data. | M | B-1.13 |
| S1.B5 | **Emit `pipeline.cost_update` events** from `PipelineBudget` on each model call completion. Event payload: task_id, cost_delta, total_cost, model, stage. | Cost events appear on NATS `pipeline.cost.*` subject. SSE clients receive them. Events are fire-and-forget (never block agent execution). | S | B-1.9 |

#### Frontend Stories (Slice 1)

| # | Story | AC | Est. | MVP? |
|---|-------|----|------|------|
| S1.F1 | **Static 9-node pipeline layout with connecting arrows** -- React component rendering 9 stage nodes in a two-row layout with directional SVG arrows between them. | All 9 stages render with correct names and order. Arrows connect stages in pipeline order. Component renders in < 100ms. | M | **(MVP)** |
| S1.F2 | **Stage node status rendering** -- each node shows status icon (idle/active/review/passed/failed) and TaskPacket count badge. Data from Zustand store. | Nodes reflect current state. Count badge updates when store changes. Icons match status enum. | M | **(MVP)** |
| S1.F3 | **SSE connection for Pipeline Rail** -- connect to Phase 0 SSE endpoint, parse `pipeline.stage_enter`, `pipeline.stage_exit`, `pipeline.gate_pass`, `pipeline.gate_fail` events, update Zustand store. | Pipeline Rail updates within 2 seconds of event emission. No page refresh. Connection auto-establishes on component mount. | M | **(MVP)** |
| S1.F4 | **Header bar** -- display active TaskPacket count, queued count, and running cost total. Updated via SSE cost events. | Counts and cost update in real time. Cost formatted as currency. Zero state shows "0 active / 0 queued / $0.00". | S | **(MVP)** |
| S1.F5 | **Stage detail panel (slide-in right)** -- click a stage node to open a panel showing TaskPackets in that stage, progress indicators, model/agent info, cost, and link to timeline. | Panel opens on click, closes on X or Escape. Lists all TaskPackets in that stage. Each entry shows progress %, model, cost. "View Timeline" link works. | L | **(MVP)** |
| S1.F6 | **Stage metrics in detail panel** -- pass rate, avg time, throughput from `GET /api/v1/dashboard/stages/metrics`. | Metrics load when panel opens. Show "last 30 days" label. Handle loading and error states. | S | **(MVP)** |
| S1.F7 | **Active stage pulse animation** -- subtle CSS glow/pulse on stage nodes with active TaskPackets. Paused via IntersectionObserver when off-screen. | Active nodes visually distinct from idle. Animation pauses when not in viewport. No jank on low-end hardware. | S | |
| S1.F8 | **Hover tooltips on stage nodes** -- tooltip showing avg time in stage, pass rate, and titles of current TaskPackets. | Tooltip appears on hover after 300ms delay. Dismisses on mouseout. Contains accurate data from store. | S | |
| S1.F9 | **Initial data load** -- on dashboard mount, fetch `GET /api/v1/dashboard/tasks` and `GET /api/v1/dashboard/stages/metrics` to populate Zustand store before SSE provides incremental updates. | Pipeline Rail shows current state immediately on load (not blank until first SSE event). Loading spinner during fetch. | M | **(MVP)** |

**Slice 1 total: 5 backend + 9 frontend = 14 stories (7 MVP)**

---

### Slice 2: TaskPacket Timeline + Gate Inspector

A developer clicks a TaskPacket and sees its full journey. They inspect any gate decision with full evidence.

#### Backend Stories (Slice 2)

| # | Story | AC | Est. | Backend Ref |
|---|-------|----|------|-------------|
| S2.B1 | **`GET /api/v1/dashboard/tasks/:id/gates` -- Gate results for a TaskPacket** Returns array of gate events with: stage_from, stage_to, result (pass/fail), timestamp, checks performed, defect_category, summary. | Returns gate events in chronological order. Includes check-level detail (lint result, test result, security result). Empty array if no gates yet. | S | B-1.3 |
| S2.B2 | **Store gate evidence artifacts in PostgreSQL** -- `GateEvidence` model with: task_id, stage, result, checks (JSONB), defect_category, evidence_artifact (JSONB), timestamp. Populated from existing verification/QA signal data + new event emission. | Evidence queryable by task_id and stage. JSONB contains per-check command, output, pass/fail. Migration creates table. Existing gate events backfilled on next pipeline run. | L | B-1.6 |
| S2.B3 | **`GET /api/v1/dashboard/gates` -- List all gate events** (paginated, filterable by pass/fail, stage, task_id, date range). | Pagination via offset/limit. Filters compose (AND logic). Returns newest-first by default. | M | B-1.4 |
| S2.B4 | **`GET /api/v1/dashboard/gates/:id` -- Gate detail with full evidence** Returns single gate event with all checks, commands, outputs, decision rule, action taken, defect taxonomy entry. | Returns structured evidence. 404 for unknown ID. Check outputs include full text (not truncated). | S | B-1.5 |
| S2.B5 | **Gate health metrics aggregation** -- pass rate (30d), avg issues per gate, top failure type, loopback rate. | `GET /api/v1/dashboard/gates/metrics` returns summary object. Computes from GateEvidence table. | M | B-1.14 |

#### Frontend Stories (Slice 2)

| # | Story | AC | Est. | MVP? |
|---|-------|----|------|------|
| S2.F1 | **Vertical timeline layout with stage bars** -- static rendering from TaskPacket detail data. Horizontal duration bars per stage, color-coded (green/blue/gray/red/amber). | Timeline renders for any TaskPacket. Bar widths proportional to duration. Colors match stage result. | M | **(MVP)** |
| S2.F2 | **Duration-proportional bar widths** -- bar width calculated from stage start/end timestamps. Minimum width for very short stages. | Bars visually represent relative time. A 4-minute stage is visually ~4x wider than a 1-minute stage. Sub-second stages still visible. | S | **(MVP)** |
| S2.F3 | **Gate result display under each stage bar** -- pass/fail icon + summary text inline below each completed stage. | Every completed stage shows its gate result. Failed gates show in red with defect summary. | S | **(MVP)** |
| S2.F4 | **TaskPacket timeline header** -- ID, title, current status with progress %, total elapsed time, total cost. | Header shows all fields. Cost updates via SSE. Progress shows percentage for active stage. | S | **(MVP)** |
| S2.F5 | **Queued stage rendering** -- dashed/gray bars for stages not yet reached with "(queued)" label. | Future stages render as placeholders. Clearly distinguishable from completed/active stages. | S | **(MVP)** |
| S2.F6 | **Click-to-expand gate evidence** -- clicking a completed stage bar expands to show full checks performed, per-check results, decision rule, and action taken. Data from `GET /api/v1/dashboard/tasks/:id/gates`. | Expand/collapse toggles. Evidence loads on first click (cached after). Shows all checks with pass/fail per check. | M | **(MVP)** |
| S2.F7 | **Gate Inspector list view** -- chronological list of all gate transitions. Each entry: pass/fail icon, TaskPacket ID, transition (from/to), timestamp, issue count. | List renders from `GET /api/v1/dashboard/gates`. Newest first. Failed gates visually distinct. | M | **(MVP)** |
| S2.F8 | **Gate Inspector detail view** -- click a gate entry to expand full evidence (checks, results, decision, defect category, evidence artifact link). | All check results visible. Test failures show formatted error output. Decision rule displayed. | M | **(MVP)** |
| S2.F9 | **Gate Inspector filter bar** -- filter by pass/fail toggle, TaskPacket selector, stage selector, date range picker. | Filters apply immediately. Multiple filters compose. Clear-all resets to unfiltered. | M | |
| S2.F10 | **Gate health metrics summary panel** -- pass rate, avg issues, top failure type, loopback rate displayed at top of Gate Inspector. | Metrics from `GET /api/v1/dashboard/gates/metrics`. Shows trend indicator (up/down vs. prior period). | S | |
| S2.F11 | **Real-time SSE updates on timeline** -- new gate events and activity entries append to the timeline. Bar for active stage grows. | Timeline updates without refresh. New gate results appear within 2 seconds of event. | M | |
| S2.F12 | **Hover tooltips on stage bars** -- exact start/end timestamps, model used, cost for that stage. | Tooltip on hover. Shows ISO timestamps and cost formatted as currency. | S | |

**Slice 2 total: 5 backend + 12 frontend = 17 stories (8 MVP)**

---

### Slice 3: Activity Stream

A developer watches the agent work in real time. They see what files it reads, what code it writes, what tests it runs, and why.

#### Backend Stories (Slice 3)

| # | Story | AC | Est. | Backend Ref |
|---|-------|----|------|-------------|
| S3.B1 | **Emit `pipeline.activity` events from agent framework** -- instrument `src/agent/framework.py` to emit structured events for: file_read, file_edit, search, test_run, shell, reasoning, llm_call. Each event includes task_id, stage, timestamp, type, content, metadata (file_path, diff_preview, test_results, model, tokens, cost). | Events appear on NATS `pipeline.activity.*`. Events are fire-and-forget (try/except, never block agent). Metadata fields populated correctly per type. | L | B-1.7 |
| S3.B2 | **`ActivityEntry` PostgreSQL model** -- task_id, stage, timestamp, type, subphase, content, detail, metadata (JSONB). Auto-prune at 5,000 entries per task (delete oldest on insert). | Table created via migration. Entries persist from NATS consumer. Prune logic verified with > 5,000 entries. | M | B-1.8 |
| S3.B3 | **`GET /api/v1/dashboard/tasks/:id/activity` -- Paginated activity log** for a TaskPacket. Supports offset/limit, filter by type, filter by subphase. | Returns entries newest-first (default) or oldest-first (param). Pagination works. Type filter returns only matching types. | M | B-1.10 |

#### Frontend Stories (Slice 3)

| # | Story | AC | Est. | MVP? |
|---|-------|----|------|------|
| S3.F1 | **Activity stream container with basic entry rendering** -- renders a list of activity entries with timestamp, type icon, and content text. | Container renders entries in chronological order. Each entry shows timestamp (HH:MM:SS), icon, and content. | M | **(MVP)** |
| S3.F2 | **Entry type icons and formatting** -- distinct icon and styling for each type (file_read, file_edit, search, test_run, shell, reasoning, error, success, llm_call). | Each type has a unique icon. Reasoning entries styled distinctly (italic or muted). Error entries styled in red. | M | **(MVP)** |
| S3.F3 | **SSE connection for activity stream** -- subscribe to `pipeline.activity` events for the current TaskPacket. Append entries to stream in real time. | New entries appear within 1 second. Only events for the viewed TaskPacket are displayed. | M | **(MVP)** |
| S3.F4 | **Smart auto-scroll** -- auto-scroll to bottom when user is within 100px of bottom. Preserve position when user has scrolled up. "New entries below" indicator when auto-scroll is paused. | Auto-scroll works when at bottom. Scrolling up disables auto-scroll. Indicator appears when new entries arrive while scrolled up. Clicking indicator scrolls to bottom. | M | **(MVP)** |
| S3.F5 | **Subphase grouping with collapsible sections** -- entries grouped under headers (CONTEXT GATHERING, IMPLEMENTATION, TESTING). Collapse/expand toggle. Time range per subphase. | Subphases render as collapsible groups. Time range shows in header. Collapse hides entries. Default expanded. | M | |
| S3.F6 | **Detail expansion** -- file edits show 3-line diff preview with "Show full" toggle. Test failures show error message with "Show full" for stack trace. | Diff preview renders first 3 changed lines. Full diff toggles on click. Test error shows assertion with full trace on expand. | M | |
| S3.F7 | **Virtual scrolling for long streams** -- when entry count exceeds 500, switch to virtualized rendering (only render visible entries + buffer). | Scrolling remains smooth with 5,000 entries. Memory usage stays bounded. Scroll position maintained during virtualization transition. | M | |
| S3.F8 | **Filter bar** -- toggle entry types on/off via icon buttons. Text search across content and detail fields. Show/hide reasoning toggle. Show/hide LLM call toggle. | Type toggles filter immediately. Text search highlights matches. Combined filters compose. | M | |
| S3.F9 | **File edit diff preview** -- render first 3 lines of diff with syntax-aware formatting (green for additions, red for removals). | Diff lines color-coded. File path shown. Line count summary ("12 more lines"). | S | |
| S3.F10 | **Test result formatting** -- pass/fail counts with colored badges. Failed test names listed. Error messages formatted with monospace font. | Pass count in green, fail in red. Failed tests clickable to expand full output. | S | |
| S3.F11 | **Active stage activity preview in timeline** -- the TaskPacket Timeline (Slice 2) shows the last 5 activity entries inline for the currently active stage. | Preview updates in real time. Entries are a subset of the full activity stream. "View full stream" link navigates to full Activity Stream. | S | **(MVP)** |

**Slice 3 total: 3 backend + 11 frontend = 14 stories (5 MVP)**

---

### Slice 4: Loopback Visualization + Minimap + Error States

Self-healing becomes visible. Navigation becomes effortless. Failures become graceful.

#### Backend Stories (Slice 4)

| # | Story | AC | Est. | Backend Ref |
|---|-------|----|------|-------------|
| S4.B1 | **Emit `pipeline.loopback.start` and `pipeline.loopback.resolve` events** from workflow loopback logic in `src/workflow/pipeline.py`. Payload: task_id, from_stage, to_stage, reason, attempt_number, max_attempts, defect_category. | Events appear on NATS `pipeline.loopback.*`. Start event fires when gate fails and loopback is initiated. Resolve event fires when the re-attempt passes the gate. | S | B-1.11 |

#### Frontend Stories (Slice 4)

| # | Story | AC | Est. | MVP? |
|---|-------|----|------|------|
| S4.F1 | **Loopback arc on Pipeline Rail** -- animated dashed arc from failing stage back to target stage with badge (TaskPacket ID, reason, attempt count). Color: amber for in-progress, red for repeated (>1). | Arc renders on `pipeline.loopback.start` event. Badge shows correct info. Color changes on repeated loopback. | M | **(MVP)** |
| S4.F2 | **Loopback entries in TaskPacket Timeline** -- backward arrows with attempt counter ("attempt 2 of 3"). Stage re-entries shown as separate timeline entries. | Loopback visible in timeline with backward indicator. Attempt counter accurate. Re-entry stage bar labeled with attempt number. | M | **(MVP)** |
| S4.F3 | **Escalation indicator** -- when max loopbacks reached, arc turns red, badge shows "ESCALATED -- needs human review". | Escalation triggers at max_attempts. Visual clearly different from normal loopback. | S | |
| S4.F4 | **Loopback resolution animation** -- when loopback resolves, arc fades to green briefly then disappears. | Animation plays on `pipeline.loopback.resolve` event. Arc removed from display after animation completes. | S | |
| S4.F5 | **Loopback history panel** -- all loopbacks for a TaskPacket listed with: from/to stages, reason, outcome, duration. Accessed from TaskPacket Timeline. | Panel lists all loopbacks chronologically. Each entry shows stage pair, defect reason, and whether it resolved. | S | |
| S4.F6 | **Minimap bottom bar container** -- persistent bar at viewport bottom with horizontal card layout. Each card: status dot, TaskPacket ID + title (truncated), current stage + progress %, cost. | Bar renders at bottom of all views. Cards show correct current state. Truncation handles long titles. | M | **(MVP)** |
| S4.F7 | **Minimap click-to-navigate** -- clicking a card navigates to that TaskPacket's timeline view. | Navigation works. Correct TaskPacket timeline loads. Active card highlighted. | S | **(MVP)** |
| S4.F8 | **Minimap horizontal scroll** -- cards scroll horizontally when more than ~5 active TaskPackets. | Scroll works with mouse wheel and drag. No cards clipped. Scroll indicators visible. | S | |
| S4.F9 | **Minimap collapse/expand toggle** -- click toggle to minimize bar to just the active task count. | Toggle works. Collapsed state shows count only. Expanded state shows full cards. Preference persisted in localStorage. | S | |
| S4.F10 | **SSE disconnection banner** -- when SSE connection drops, show banner with "Reconnecting... (attempt N of 10)" and "Retry Now" button. Mark all stage data as stale (gray with "?" instead of count). | Banner appears within 5 seconds of disconnect. Stage nodes show stale state. "Retry Now" triggers immediate reconnection attempt. | M | **(MVP)** |
| S4.F11 | **SSE reconnection with full state refresh** -- on reconnect, request `system.full_state` event to restore current pipeline state. Show "Connection restored" toast. | Full state refreshes all components. Toast dismisses after 3 seconds. No stale data remains after reconnect. | M | **(MVP)** |
| S4.F12 | **API error cards** -- when a REST API call fails, render an error card in the affected panel only (not full-page). Shows error message, "Retry" button, "Dismiss" button. | Error card scoped to failing panel. Rest of UI functional. Retry re-fetches. Dismiss removes card. | M | **(MVP)** |
| S4.F13 | **Empty state: Pipeline Rail** -- when no tasks are in the pipeline, show message with "Import Issues" and "Create Task" action buttons. | Empty state renders when zero TaskPackets. Buttons are visible (functional wiring deferred to Phase 2). | S | **(MVP)** |
| S4.F14 | **Empty states: Activity Stream, Gate Inspector, Minimap** -- contextual empty messages for each component when no data exists. | Each component shows appropriate empty message. Messages guide user to take action. | S | **(MVP)** |

**Slice 4 total: 1 backend + 14 frontend = 15 stories (10 MVP)**

---

## Story Summary

| Slice | Backend | Frontend | Total | MVP |
|-------|---------|----------|-------|-----|
| 1: Pipeline Rail | 5 | 9 | 14 | 7 |
| 2: TaskPacket Timeline + Gate Inspector | 5 | 12 | 17 | 8 |
| 3: Activity Stream | 3 | 11 | 14 | 5 |
| 4: Loopback + Minimap + Error States | 1 | 14 | 15 | 10 |
| **Total** | **14** | **46** | **60** | **30** |

**MVP path (30 stories):** Delivers a functional pipeline dashboard where a developer can see live stage status, inspect any TaskPacket's journey, audit gate decisions with full evidence, watch agent activity in real time, see loopbacks, switch between active tasks, and recover gracefully from connection failures.

**Polish path (30 additional stories):** Adds tooltips, animations, subphase grouping, virtual scrolling, filter bars, diff previews, keyboard nav, and visual refinements.

---

## Meridian Review Status

**Round 1: Pending**

| # | Question | Status |
|---|----------|--------|
| 1 | Are acceptance criteria testable at epic scale? | Pending |
| 2 | Are non-goals explicit enough to prevent scope creep? | Pending |
| 3 | Are dependencies identified and sequenced? | Pending |
| 4 | Are success metrics measurable? | Pending |
| 5 | Is the story map ordered by risk reduction? | Pending |
| 6 | Are backend/frontend stories traceable to design specs? | Pending |
| 7 | Is the epic AI-implementable (files, endpoints, models named)? | Pending |
