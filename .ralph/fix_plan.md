# Fix Plan — TheStudio: Pipeline UI Initiative

> Epic details: `docs/epics/epic-34-phase0-sse-poc.md` and `docs/epics/epic-35-phase1-pipeline-visibility.md`
> Sprint plan: `docs/sprints/session-prompt-epic34-s1.md`

## Time Tracking

**Instructions:** Ralph updates `actual_loops` and `actual_min` after completing each story. After Epic 34 completes, compute the calibration ratio (actual/estimated) and apply it to Epic 35 estimates.

### Run 1: Epic 34 (Calibration Run)

| Story | Est. Loops | Est. Min | Actual Loops | Actual Min | Notes |
|-------|-----------|---------|-------------|-----------|-------|
| B-0.1 | 1 | 8 | | | |
| B-0.2a | 1 | 12 | | | |
| B-0.2b | 2 | 25 | | | Highest risk — NATS in SSE |
| B-0.3 | 1 | 15 | | | |
| B-0.4a | 1 | 12 | | | |
| B-0.4b | 1 | 12 | | | |
| B-0.5 | 1 | 10 | | | |
| F-0.1 | 1 | 15 | | | |
| F-0.2 | 1 | 15 | | | |
| F-0.3a | 1 | 12 | | | |
| F-0.3b | 1 | 10 | | | |
| B-0.7 | 1 | 10 | | | Compressible |
| B-0.6 | 1 | 8 | | | Compressible |
| F-0.4 | 1 | 6 | | | |
| **Total** | **15** | **170 min** | | | **Est: ~3 hrs** |

**Start time:** _______________
**End time:** _______________
**Wall clock total:** _______________
**Calibration ratio:** actual_min / 170 = _______________

---

## Epic 34 — Phase 0: SSE PoC + Frontend Scaffolding

### Slice 1: Backend Foundation
- [x] B-0.1: Create `src/dashboard/` package with FastAPI router at `/api/v1/dashboard/`, health endpoint, register in `src/app.py`. Test: `GET /api/v1/dashboard/health` returns `{"status": "ok"}`.

### Slice 2: SSE Endpoint
- [x] B-0.2a: SSE endpoint with hardcoded test events. Create `src/dashboard/events.py` with `GET /api/v1/dashboard/events/stream` returning `StreamingResponse` with `text/event-stream`. Heartbeat every 15s. Test: curl the endpoint, verify event-stream content type and heartbeat events arrive.
- [x] B-0.2b: Wire SSE endpoint to NATS JetStream. Subscribe to `pipeline.>` subject on `THESTUDIO_PIPELINE` stream (create stream if not exists). Replace hardcoded events with NATS messages. Add disconnect cleanup. Test: publish to NATS, verify SSE client receives within 200ms.

### Slice 3: Reconnection
- [x] B-0.3: Add `Last-Event-ID` reconnection support. Parse header, use `DeliverPolicy.BY_START_SEQUENCE` to replay missed events. If gap >1000, send `system.full_state`. Test: disconnect, reconnect with Last-Event-ID, verify zero missed events.

### Slice 4: Pipeline Event Emission
- [x] B-0.4a: Create `src/dashboard/events_publisher.py` with fire-and-forget NATS publish helper. Instrument first 3 stages (intake, context, intent) with `pipeline.stage.enter`/`exit` events. Create `THESTUDIO_PIPELINE` JetStream stream on startup. Test: mock NATS, run activity, verify publish called.
- [x] B-0.4b: Instrument remaining 6 stages (router, assembler, implement, verify, qa, publish). Integration test: full pipeline run emits 9/9 stage enter/exit events.
- [x] B-0.5: Extend `src/verification/signals.py` and `src/qa/signals.py` to publish `pipeline.gate.pass`/`fail` to `THESTUDIO_PIPELINE`. Existing streams unchanged. Test: trigger verification, observe gate event in SSE.

### Slice 5: Frontend Scaffolding
- [x] F-0.1: Scaffold `frontend/` with Vite + React 19 + TypeScript strict + Zustand 5 + Tailwind CSS v4. Vite proxy `/api/*` to localhost:8000. Pipeline stage colors in `src/lib/constants.ts`. Test: `npm run build` < 50KB gzipped, `npm run typecheck` passes.
- [x] F-0.2: Create `useSSE` hook (`frontend/src/hooks/useSSE.ts`) and Zustand pipeline store (`frontend/src/stores/pipeline-store.ts`). Store tracks 9 stages with status/taskCount/activeTasks. Hook connects via EventSource, dispatches to store. Vitest tests with mock EventSource.
- [x] F-0.3a: Create `PipelineStatus.tsx` and `StageNode.tsx`. Render 9 stage nodes in horizontal rail, color-coded by status from store, with task count. Component test with mocked store.
- [x] F-0.3b: Create `ConnectionIndicator.tsx` and `EventLog.tsx` (last 20 events). Wire into App.tsx. Dark mode Tailwind styling. Component test for disconnected state.

### Slice 6: Auth + Serving
- [x] B-0.7: Auth token on SSE endpoint via `?token=` query param, matching admin auth. Test: 401 without, 200 with valid token. (COMPRESSIBLE)
- [x] B-0.6: Conditional static mount in `src/app.py` — serve `frontend/dist/` at `/dashboard/` when exists, skip with warning when missing. SPA catch-all. (COMPRESSIBLE)

### Slice 7: CI
- [x] F-0.4: GitHub Actions frontend CI workflow. `npm ci`, `npm run typecheck`, `npm run lint`, `npm test`. Node.js 22, cache node_modules.

---

## Epic 35 — Phase 1: Pipeline Visibility

> **Load after Epic 34 completes.** Apply calibration ratio to adjust estimates below.
> **Estimated runtime:** ~20-28 hrs single instance. With parallelism: ~8-12 hrs.

### Time Tracking — Run 2+

| Slice | Stories | Est. Loops | Est. Min | Actual Loops | Actual Min |
|-------|---------|-----------|---------|-------------|-----------|
| S1 Backend | 5 | 6 | 70 | | |
| S1 Frontend | 9 | 10 | 110 | | |
| S2 Backend | 6 | 7 | 80 | | |
| S2 Frontend | 12 | 14 | 150 | | |
| S3 Backend | 4 | 5 | 55 | | |
| S3 Frontend | 11 | 13 | 140 | | |
| S4 Backend | 1 | 1 | 10 | | |
| S4 Frontend | 14 | 16 | 170 | | |
| **Total** | **63** | **72** | **785 min** | | |

### Slice 1: Pipeline Rail

#### Backend
- [x] S1.B1: Add stage timing fields to TaskPacket model (start/end timestamp per stage). Alembic migration. Nulls for historical records. (M)
- [x] S1.B2: `GET /api/v1/dashboard/tasks` — List TaskPackets with pagination (offset/limit), filter by status/date/category. Returns JSON array. Auth required. (M)
- [x] S1.B3: `GET /api/v1/dashboard/tasks/:id` — TaskPacket detail with stage timestamps, cost breakdown by stage, model per stage. 404 for unknown ID. (S)
- [x] S1.B4: Pipeline stage metrics aggregation query — per-stage pass rate, avg duration, throughput over configurable window. `GET /api/v1/dashboard/stages/metrics`. (M)
- [x] S1.B5: Emit `pipeline.cost_update` events from `PipelineBudget` on each model call. Payload: task_id, cost_delta, total_cost, model, stage. Fire-and-forget. (S)

#### Frontend
- [ ] S1.F1: Static 9-node pipeline layout with connecting arrows. React component, two-row layout, directional SVG arrows. All 9 stages render with correct names/order. (M, MVP)
- [ ] S1.F2: Stage node status rendering — status icon (idle/active/review/passed/failed) and TaskPacket count badge from Zustand store. (M, MVP)
- [ ] S1.F3: SSE connection for Pipeline Rail — parse stage_enter/exit and gate events, update store. Rail updates within 2s of event. (M, MVP)
- [ ] S1.F4: Header bar — active count, queued count, running cost total. Updated via SSE cost events. Zero state: "0 active / 0 queued / $0.00". (S, MVP)
- [ ] S1.F5a: Stage detail panel shell — slide-in right panel on stage node click. Close on X or Escape. Animation transition. (M, MVP)
- [ ] S1.F5b: Stage detail panel content — list TaskPackets in stage with progress %, model, cost. "View Timeline" link. Stage metrics (pass rate, avg time). (M, MVP)
- [ ] S1.F7: Active stage pulse animation — CSS glow on active nodes. IntersectionObserver pauses when off-screen. (S)
- [ ] S1.F8: Hover tooltips on stage nodes — avg time, pass rate, current TaskPacket titles. 300ms delay. (S)
- [ ] S1.F9: Initial data load — fetch tasks + stage metrics on mount to populate store before SSE events. Loading spinner. (M, MVP)

### Slice 2: TaskPacket Timeline + Gate Inspector

#### Backend
- [ ] S2.B1: `GET /api/v1/dashboard/tasks/:id/gates` — Gate results array with stage_from/to, result, checks, defect_category. Chronological. (S)
- [ ] S2.B2a: GateEvidence SQLAlchemy model — task_id, stage, result, checks (JSONB), defect_category, evidence_artifact (JSONB), timestamp. Alembic migration. (M)
- [ ] S2.B2b: NATS consumer to populate GateEvidence from verification/QA signals. Subscribe to existing streams, write to PostgreSQL. (M)
- [ ] S2.B3: `GET /api/v1/dashboard/gates` — List all gate events, paginated, filterable by pass/fail, stage, task_id, date range. Newest-first. (M)
- [ ] S2.B4: `GET /api/v1/dashboard/gates/:id` — Gate detail with full evidence, checks, outputs, decision rule. 404 for unknown. (S)
- [ ] S2.B5: Gate health metrics aggregation — pass rate, avg issues, top failure type, loopback rate. `GET /api/v1/dashboard/gates/metrics`. (M)

#### Frontend
- [ ] S2.F1: Vertical timeline layout with stage bars — static rendering from TaskPacket detail. Duration bars color-coded. (M, MVP)
- [ ] S2.F2: Duration-proportional bar widths from timestamps. Minimum width for short stages. (S, MVP)
- [ ] S2.F3: Gate result display under each stage bar — pass/fail icon + summary. Failed in red. (S, MVP)
- [ ] S2.F4: TaskPacket timeline header — ID, title, status with progress %, elapsed time, cost. (S, MVP)
- [ ] S2.F5: Queued stage rendering — dashed/gray bars for unreached stages with "(queued)" label. (S, MVP)
- [ ] S2.F6: Click-to-expand gate evidence — expand completed stage to show checks, per-check results, decision. Loads from API, cached. (M, MVP)
- [ ] S2.F7: Gate Inspector list view — chronological gate transitions. Pass/fail icon, TaskPacket ID, transition, timestamp, issue count. (M, MVP)
- [ ] S2.F8: Gate Inspector detail view — click to expand full evidence, checks, decision, defect category. (M, MVP)
- [ ] S2.F9: Gate Inspector filter bar — pass/fail toggle, TaskPacket selector, stage selector, date range. (M)
- [ ] S2.F10: Gate health metrics summary panel — pass rate, avg issues, top failure, loopback rate with trend. (S)
- [ ] S2.F11: Real-time SSE updates on timeline — gate events and activity entries append, active bar grows. (M)
- [ ] S2.F12: Hover tooltips on stage bars — timestamps, model, cost. (S)

### Slice 3: Activity Stream

#### Backend
- [ ] S3.B1a: Activity event publisher — create `src/dashboard/activity_publisher.py`. Instrument agent framework for file_read, file_edit, search event types. Fire-and-forget. (M)
- [ ] S3.B1b: Instrument agent framework for test_run, shell, reasoning, llm_call event types. Integration test: all 7 types emit correctly. (M)
- [ ] S3.B2: ActivityEntry PostgreSQL model — task_id, stage, timestamp, type, subphase, content, detail, metadata (JSONB). Auto-prune at 5000/task. Migration. (M)
- [ ] S3.B3: `GET /api/v1/dashboard/tasks/:id/activity` — Paginated activity log. Filter by type, subphase. Newest-first or oldest-first. (M)

#### Frontend
- [ ] S3.F1: Activity stream container — list of entries with timestamp (HH:MM:SS), type icon, content text. Chronological. (M, MVP)
- [ ] S3.F2: Entry type icons and formatting — distinct icon per type. Reasoning italic/muted. Errors red. (M, MVP)
- [ ] S3.F3: SSE connection for activity stream — subscribe to `pipeline.activity` for current TaskPacket. Append in real time. (M, MVP)
- [ ] S3.F4: Smart auto-scroll — scroll to bottom when within 100px. Preserve position when scrolled up. "New entries below" indicator. (M, MVP)
- [ ] S3.F5: Subphase grouping with collapsible sections — CONTEXT GATHERING, IMPLEMENTATION, TESTING headers. Time range per subphase. (M)
- [ ] S3.F6: Detail expansion — file edits show 3-line diff preview with "Show full". Test failures show error with "Show full" for trace. (M)
- [ ] S3.F7: Virtual scrolling for long streams — virtualize when >500 entries. Smooth with 5000. Memory bounded. (M)
- [ ] S3.F8: Filter bar — type toggles, text search, reasoning toggle, LLM call toggle. (M)
- [ ] S3.F9: File edit diff preview — first 3 lines, green additions, red removals, line count summary. (S)
- [ ] S3.F10: Test result formatting — pass/fail counts with badges, failed test names, monospace errors. (S)
- [ ] S3.F11: Active stage activity preview in timeline — last 5 entries inline in TaskPacket Timeline for active stage. "View full stream" link. (S, MVP)

### Slice 4: Loopback + Minimap + Error States

#### Backend
- [ ] S4.B1: Emit `pipeline.loopback.start` and `pipeline.loopback.resolve` events from workflow loopback logic. Payload: task_id, from/to stage, reason, attempt, max_attempts. (S)

#### Frontend
- [ ] S4.F1: Loopback arc on Pipeline Rail — animated dashed arc from failing stage to target. Badge with ID, reason, attempt count. Amber/red coloring. (M, MVP)
- [ ] S4.F2: Loopback entries in TaskPacket Timeline — backward arrows, attempt counter, re-entry as separate entries. (M, MVP)
- [ ] S4.F3: Escalation indicator — max loopbacks: red arc, "ESCALATED — needs human review". (S)
- [ ] S4.F4: Loopback resolution animation — arc fades to green, then disappears. (S)
- [ ] S4.F5: Loopback history panel — all loopbacks for a TaskPacket with stages, reason, outcome, duration. (S)
- [ ] S4.F6: Minimap bottom bar — persistent, horizontal cards. Status dot, ID + title (truncated), stage + progress %, cost. (M, MVP)
- [ ] S4.F7: Minimap click-to-navigate — click card → navigate to TaskPacket timeline. Active card highlighted. (S, MVP)
- [ ] S4.F8: Minimap horizontal scroll — mouse wheel and drag when >5 cards. No clipping. (S)
- [ ] S4.F9: Minimap collapse/expand toggle — minimize to count only. Preference in localStorage. (S)
- [ ] S4.F10: SSE disconnection banner — "Reconnecting..." with attempt count, "Retry Now" button, stale stage indicators. Within 5s of disconnect. (M, MVP)
- [ ] S4.F11: SSE reconnection with full state refresh — `system.full_state` on reconnect. "Connection restored" toast. No stale data after reconnect. (M, MVP)
- [ ] S4.F12: API error cards — per-panel error card (not full-page). Error message, Retry, Dismiss. Rest of UI functional. (M, MVP)
- [ ] S4.F13: Empty state: Pipeline Rail — message with "Import Issues" and "Create Task" buttons (wiring deferred to Phase 2). (S, MVP)
- [ ] S4.F14: Empty states: Activity Stream, Gate Inspector, Minimap — contextual empty messages. (S, MVP)

---

## Completed
