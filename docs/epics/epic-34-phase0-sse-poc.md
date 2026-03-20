# Epic 34: Phase 0 — SSE Proof-of-Concept + Frontend Scaffolding

> **Status:** Draft (Pending Meridian Review)
> **Epic Owner:** Primary Developer
> **Duration:** 2-3 weeks (~2-3 sprints)
> **Created:** 2026-03-20
> **Meridian Review:** Round 1: Pending

---

## 1. Title

**A Browser Displays Live Pipeline Stage Transitions from a Real Temporal Workflow**

---

## 2. Narrative

TheStudio operates as a headless backend. GitHub issues go in, draft PRs come out, and the only visibility into the 9-stage pipeline is Temporal UI and server-rendered admin pages that poll for state. There is no real-time connection between what the pipeline is doing and what a developer can see.

The frontend design suite (docs 00-06) describes a rich interactive dashboard: pipeline rail, live activity streams, gate inspectors, planning boards, cost dashboards. That vision spans 268 stories across 5 phases and 9-12 months of calendar time. Before committing to any of it, one question must be answered: **does SSE-over-NATS actually work end-to-end, from Temporal workflow activity to browser render, with reconnection support?**

This is that question, turned into shippable work.

The backend has NATS JetStream running with two streams (`THESTUDIO_VERIFICATION` and `THESTUDIO_QA`) that emit gate results. The frontend has nothing — no React app, no build toolchain, no SSE connection. The gap between "NATS has events" and "browser shows events" is the entire real-time architecture: a JetStream stream for pipeline events, a FastAPI SSE endpoint that subscribes to NATS and streams to the browser, event emission from Temporal workflow activities, and a React app with a Zustand store that turns SSE events into rendered state.

This epic builds the thinnest possible vertical slice through that entire stack. When it ships, a developer can open a browser, watch a TaskPacket flow through Intake, Context, Intent, and beyond, and see each stage transition appear in real time. If the browser tab closes and reopens, it reconnects and catches up from where it left off. That is the exit criteria. Everything in Phase 1-5 builds on this foundation.

**Why now:** The design suite is complete. The backend is stable (1783/1783 tests passing). Epics 30-33 closed the provider integration gaps. The next major initiative is the dashboard, and this epic is the architecture validation gate that determines whether the chosen technology stack (SSE, NATS bridging, React + Zustand) is viable before 268 stories of investment.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Pipeline UI Master Vision | `docs/design/00-PIPELINE-UI-VISION.md` (Section 8, Phase 0) |
| Technology & Architecture Spec | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Sections 2-6) |
| Backend Requirements (Phase 0 stories) | `docs/design/06-BACKEND-REQUIREMENTS.md` (Section 3, Phase 0: B-0.1 through B-0.7) |
| Current State Audit | `docs/design/06-BACKEND-REQUIREMENTS.md` (Section 2) |
| SSE Handler Reference Implementation | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 5.3) |
| SSE Hook Pattern (React) | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 4.3) |
| Zustand Store Pattern | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 4.2) |
| Frontend Directory Structure | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 4.1) |
| Deployment Model | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 6) |
| NATS Subject Hierarchy | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` (Section 5.2) |
| Existing NATS verification signals | `src/verification/signals.py` |
| Existing NATS QA signals | `src/qa/signals.py` |
| Temporal workflow activities | `src/workflow/activities.py` |
| Pipeline workflow | `src/workflow/pipeline.py` |
| FastAPI app entry point | `src/app.py` |
| Existing admin router | `src/admin/ui_router.py` |
| Production Docker Compose | `infra/docker-compose.prod.yml` |
| Pipeline Persona (Saga) | `thestudioarc/personas/saga-epic-creator.md` |
| OKRs | `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` |

---

## 4. Acceptance Criteria

### AC 1: Dashboard API Router Exists

A new `src/dashboard/` package exists with a FastAPI router mounted at `/api/v1/dashboard/`. The router is registered in `src/app.py` alongside the existing admin router. Hitting `GET /api/v1/dashboard/health` returns 200 with `{"status": "ok"}`. The existing admin panel at `/admin/*` continues to function without changes.

### AC 2: SSE Endpoint Streams NATS Events to Browser

`GET /api/v1/dashboard/events/stream` returns `Content-Type: text/event-stream`. When a pipeline event is published to NATS JetStream on any `pipeline.>` subject, the SSE endpoint delivers it to connected clients within 200ms. Each event includes `id` (NATS sequence number), `event` (NATS subject), and `data` (JSON payload). The response includes `Cache-Control: no-cache`, `Connection: keep-alive`, and `X-Accel-Buffering: no` headers.

### AC 3: Reconnection with Last-Event-ID

When a client reconnects with `Last-Event-ID: N`, the SSE endpoint replays events from NATS JetStream starting at sequence N+1 using `DeliverPolicy.BY_START_SEQUENCE`. A test demonstrates: connect, receive events, disconnect, reconnect with Last-Event-ID, and receive only missed events (no duplicates, no gaps).

### AC 4: Pipeline Stage Events Emitted from Temporal Activities

Temporal workflow activities emit `pipeline.stage.enter` and `pipeline.stage.exit` events to a new NATS JetStream stream (`THESTUDIO_PIPELINE`) at the start and end of each pipeline stage activity. Events include `task_id`, `stage` name, `timestamp`, and `status`. At minimum, Intake, Context, Intent, Router, Assembler, Implement, Verify, QA, and Publish stages emit events.

### AC 5: Gate Events Emitted

Existing verification and QA gate signal emission is extended to also publish `pipeline.gate.pass` and `pipeline.gate.fail` events to the `THESTUDIO_PIPELINE` stream. Events include `task_id`, `stage`, `gate` name, `passed` boolean, and a summary of check results. These events are delivered through the SSE endpoint alongside stage events.

### AC 6: Browser Displays Live Stage Transitions

A React application exists at `frontend/` built with Vite + TypeScript + React 19 + Zustand + Tailwind CSS v4. The app connects to the SSE endpoint and displays a minimal pipeline status page showing the 9 pipeline stages with their current status (idle, active, passed, failed). When a TaskPacket enters a stage, the corresponding stage node updates in real time without page refresh. The page is accessible at `/dashboard/` when served through the Vite dev proxy or FastAPI static mount.

### AC 7: SSE Endpoint Requires Auth Token

The SSE endpoint accepts an auth token via query parameter (`?token=...`), matching the existing admin panel authentication mechanism. Requests without a valid token receive 401. This is consistent with the constraint that `EventSource` does not support custom headers.

---

## 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| NATS JetStream subscription blocks the async event loop, causing SSE stalls | Medium | High | Use `nats-py` async client with proper `asyncio` integration; load test with 50 rapid events |
| Vite proxy to FastAPI SSE endpoint drops the streaming connection | Medium | Medium | Test early in Story F-0.1; configure proxy `changeOrigin` and disable response buffering |
| `EventSource` retry behavior differs across browsers (Chrome vs Firefox reconnect timing) | Low | Medium | Test in both browsers; document browser-specific behavior; implement server heartbeat as keepalive |
| NATS sequence numbers reset if stream is recreated, breaking Last-Event-ID replay | Low | High | Pin stream configuration; add `system.full_state` fallback for large gaps per design spec |
| Adding NATS publish calls to every activity slows down pipeline execution | Low | Medium | Publish is fire-and-forget (async, no ack wait in the activity); benchmark before/after |

---

## 5. Constraints & Non-Goals

### Constraints

- **Coexistence:** The existing admin panel at `/admin/*` must continue to function. The new dashboard API lives at `/api/v1/dashboard/` and the SPA at `/dashboard/*`. No admin routes are modified.
- **Infrastructure reuse:** No new infrastructure services. The SSE bridge uses existing NATS JetStream and FastAPI. No WebSocket server, no Redis pub/sub, no additional message broker.
- **Auth parity:** SSE auth uses the same mechanism as the existing admin panel. No new auth system in this epic.
- **TypeScript strict mode:** All frontend code uses TypeScript with strict mode enabled. No `any` types in committed code.
- **Dev Compose untouched:** `docker-compose.dev.yml` is not modified. Frontend runs via Vite dev server.

### Non-Goals

- **Full pipeline rail UI.** This epic builds a minimal status page that proves SSE works. The polished Pipeline Rail component with animations, tooltips, drill-down panels, and task minimap is Phase 1 scope.
- **Activity stream.** Agent tool call events (`pipeline.activity`) are Phase 1 (Story B-1.7). This epic emits only stage transitions and gate results.
- **Cost events.** `pipeline.cost_update` emission is Phase 1 (Story B-1.9). Not in scope here.
- **REST API endpoints.** No `/tasks`, `/gates`, `/budget`, or other REST endpoints. Only the SSE endpoint and health check.
- **Radix UI, Tremor, charts, drag-and-drop.** No component library integration beyond Tailwind. The status page uses plain HTML elements styled with Tailwind.
- **Dark mode / light mode toggle.** Ship dark mode only. Theme switching is Phase 1.
- **TanStack Router / TanStack Query.** Not needed for a single-page PoC. Add in Phase 1 when routing is required.
- **Production Docker build for frontend.** The frontend Dockerfile is Phase 1. This epic uses Vite dev server or FastAPI static mount.
- **Playwright E2E tests.** The PoC is validated by unit tests, integration tests, and manual verification. Playwright setup is Phase 1.
- **Mobile / responsive layout.** Desktop only. The status page does not need to work on mobile.

---

## 6. Stakeholders & Roles

| Role | Person | Responsibility |
|------|--------|---------------|
| Epic Owner | Primary Developer | All implementation, testing, and validation |
| Reviewer | Meridian (VP of Success) | Epic review, acceptance criteria validation |
| Planner | Helm | Sprint planning and story sequencing |
| Architecture | Design docs (00, 05, 06) | Source of truth for technology decisions |

---

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| SSE latency (NATS publish to browser render) | < 200ms p95 | Timestamp comparison in test page (event timestamp vs render timestamp) |
| Reconnection gap | 0 missed events on reconnect | Automated test: disconnect, publish 10 events, reconnect with Last-Event-ID, verify all 10 received |
| Stage event coverage | 9/9 pipeline stages emit enter/exit events | Count distinct stage names in NATS stream after full pipeline run |
| Frontend build size | < 50KB gzipped (PoC is minimal) | `npm run build` output |
| Time to interactive | < 1s on dev server | Lighthouse or manual measurement |
| Epic duration | Completed in 2-3 weeks | Calendar time from first commit to AC sign-off |

### Kill Criterion

If the SSE-over-NATS bridge cannot deliver events at **< 500ms p95 latency** after **3 calendar days of focused effort** (stories B-0.1 + B-0.2 + spike), this architecture is rejected. Fallback options, evaluated in order:

1. **Polling fallback:** Replace SSE with `GET /api/v1/dashboard/pipeline/state` polled every 2s. Simpler, higher latency, proven pattern.
2. **WebSocket fallback:** Replace SSE with FastAPI WebSocket. More complex but bidirectional.
3. **Abort initiative:** If neither alternative meets <2s latency for pipeline state updates, the rich dashboard initiative is shelved.

The Day 3 architecture gate in the sprint plan ([session-prompt-epic34-s1.md](../sprints/session-prompt-epic34-s1.md)) is the decision point.

---

## 8. Context & Assumptions

### Business Rules

- The `THESTUDIO_PIPELINE` JetStream stream uses `retention: limits`, `max_msgs: 100000`, and `max_age: 7d`. This is sufficient for PoC; production tuning is Phase 1.
- SSE events use the NATS subject as the SSE event type (e.g., `pipeline.stage.enter`). The frontend dispatches on event type.
- The SSE endpoint creates one NATS subscription per connected client. For Phase 0 (single developer, 1-2 browser tabs), this is acceptable. Connection pooling is a Phase 1 concern if needed.
- The frontend project lives in `frontend/` at the repository root, separate from the Python source in `src/`.
- Vite dev server proxies `/api/*` to `http://localhost:8000` (FastAPI).

### Dependencies

- **NATS JetStream** must be running (available in dev via `docker-compose.dev.yml`).
- **Temporal** must be running for workflow activities to fire (existing dev setup).
- **Node.js 22+** required for frontend toolchain (Vite 6 requires Node 22).
- **`nats-py`** async client already in `requirements.txt` (used by existing signal modules).
- **React 19** is the target version per design spec. If 19 is not yet stable, React 18.3 is acceptable with a TODO to upgrade.

### Systems Affected

| System | Change |
|--------|--------|
| `src/app.py` | Mount new dashboard router |
| `src/dashboard/` (new) | SSE endpoint, router, NATS bridge |
| `src/workflow/activities.py` | Add NATS publish calls at stage entry/exit |
| `src/verification/signals.py` | Extend to publish gate events to pipeline stream |
| `src/qa/signals.py` | Extend to publish gate events to pipeline stream |
| `frontend/` (new) | Entire React application |
| `infra/docker-compose.prod.yml` | No changes in Phase 0 |
| `docker-compose.dev.yml` | No changes |

### Assumptions

- The `nats-py` async client works correctly within FastAPI's async event loop for long-lived SSE subscriptions. If it does not, the fallback is a dedicated asyncio task with a queue.
- Browser `EventSource` auto-reconnect is sufficient for the PoC. Custom reconnection logic (exponential backoff, max retries) is Phase 1 polish.
- A single NATS JetStream consumer group is not needed for Phase 0. Each SSE client gets its own ephemeral subscription. Durable consumer groups are a Phase 1 optimization.

---

## Story Map

Stories are ordered as vertical slices. Each slice delivers testable value. Backend stories (B-0.x) come from the design doc; frontend stories (F-0.x) are new.

### Slice 1: Backend Foundation (B-0.1 + B-0.2)

Deliver the SSE endpoint that streams NATS events to the browser. This is the architectural proof point.

---

#### Story B-0.1: Create Dashboard API Package

**As a** developer extending TheStudio's API surface,
**I want** a new `src/dashboard/` package with a FastAPI router mounted at `/api/v1/dashboard/`,
**so that** all dashboard endpoints have a clean namespace separate from the admin panel.

**Acceptance Criteria:**
- `src/dashboard/__init__.py` exists
- `src/dashboard/router.py` defines a FastAPI `APIRouter` with prefix `/api/v1/dashboard`
- `src/dashboard/health.py` implements `GET /api/v1/dashboard/health` returning `{"status": "ok"}`
- Router is registered in `src/app.py` via `app.include_router()`
- Existing admin routes at `/admin/*` are unaffected (regression test)
- `pytest tests/unit/test_dashboard_router.py` passes

**Files to create:**
- `src/dashboard/__init__.py`
- `src/dashboard/router.py`
- `src/dashboard/health.py`
- `tests/unit/test_dashboard_router.py`

**Files to modify:**
- `src/app.py` (add router include)

**Size:** S
**Depends on:** Nothing

---

#### Story B-0.2: Implement SSE Endpoint with NATS JetStream Bridge

**As a** browser client,
**I want** to connect to `GET /api/v1/dashboard/events/stream` and receive real-time pipeline events via Server-Sent Events,
**so that** the frontend can display live pipeline state without polling.

**Acceptance Criteria:**
- `GET /api/v1/dashboard/events/stream` returns `Content-Type: text/event-stream`
- Endpoint uses `StreamingResponse` with an async generator
- Generator subscribes to `pipeline.>` on NATS JetStream
- Each event is formatted as SSE: `id: {seq}\nevent: {subject}\ndata: {json}\n\n`
- Response headers include `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- When the client disconnects, the NATS subscription is cleaned up (no leaked subscriptions)
- A heartbeat comment (`: keepalive\n\n`) is sent every 15 seconds if no events arrive (prevents proxy timeouts)
- Integration test: publish a message to `pipeline.test.ping`, verify SSE client receives it

**Files to create:**
- `src/dashboard/events.py`
- `tests/unit/test_sse_endpoint.py`
- `tests/integration/test_sse_nats_bridge.py`

**Files to modify:**
- `src/dashboard/router.py` (include events router)

**Size:** M
**Depends on:** B-0.1

---

### Slice 2: Reconnection (B-0.3)

Prove that clients can reconnect without data loss. This is the durability guarantee.

---

#### Story B-0.3: Last-Event-ID Reconnection Support

**As a** browser client that lost its connection,
**I want** to reconnect with `Last-Event-ID` and receive only the events I missed,
**so that** the frontend state stays consistent after network interruptions.

**Acceptance Criteria:**
- SSE endpoint reads `Last-Event-ID` header (sent automatically by `EventSource` on reconnect)
- When present, NATS subscription uses `DeliverPolicy.BY_START_SEQUENCE` with `opt_start_seq = last_event_id + 1`
- When absent, NATS subscription uses `DeliverPolicy.NEW` (only new events)
- Integration test: connect, receive 5 events, disconnect, publish 3 more events, reconnect with Last-Event-ID of event 5, verify exactly 3 events received (no duplicates, no gaps)
- If the requested sequence is beyond the stream's retention window, endpoint sends a `system.replay_failed` event and falls back to `DeliverPolicy.LAST`

**Files to modify:**
- `src/dashboard/events.py`
- `tests/integration/test_sse_nats_bridge.py` (add reconnection tests)

**Size:** M
**Depends on:** B-0.2

---

### Slice 3: Event Emission (B-0.4 + B-0.5)

Instrument the pipeline to emit the events the SSE endpoint will deliver.

---

#### Story B-0.4: Emit Pipeline Stage Events from Temporal Activities

**As a** dashboard watching a pipeline run,
**I want** each Temporal workflow activity to emit `pipeline.stage.enter` and `pipeline.stage.exit` events to NATS JetStream,
**so that** the SSE endpoint can deliver real-time stage transitions to the browser.

**Acceptance Criteria:**
- A new NATS JetStream stream `THESTUDIO_PIPELINE` is created (subjects: `pipeline.>`, retention: limits, max_msgs: 100000, max_age: 7d)
- Stream creation is idempotent (safe to call on every app startup)
- Each pipeline stage activity in `src/workflow/activities.py` publishes:
  - `pipeline.stage.enter.{task_id}` at activity start with `{"task_id": "...", "stage": "...", "timestamp": "...", "status": "active"}`
  - `pipeline.stage.exit.{task_id}` at activity end with `{"task_id": "...", "stage": "...", "timestamp": "...", "status": "completed|failed", "duration_ms": ...}`
- All 9 stages emit events (intake, context, intent, router, assembler, implement, verify, qa, publish)
- Event emission is fire-and-forget (does not block activity execution; errors are logged but do not fail the activity)
- Unit test: mock NATS, run an activity, verify publish was called with correct subject and payload
- Integration test: run a pipeline with NATS connected, verify stage events appear in the JetStream stream

**Files to create:**
- `src/dashboard/events_publisher.py` (NATS publish helper)
- `tests/unit/test_pipeline_events.py`

**Files to modify:**
- `src/workflow/activities.py` (add publish calls)
- `src/app.py` (create JetStream stream on startup)

**Size:** M
**Depends on:** B-0.2 (needs the stream to exist)

---

#### Story B-0.5: Emit Gate Pass/Fail Events

**As a** dashboard monitoring pipeline health,
**I want** verification and QA gates to emit `pipeline.gate.pass` and `pipeline.gate.fail` events to the pipeline stream,
**so that** gate transitions appear in the SSE event stream alongside stage transitions.

**Acceptance Criteria:**
- `src/verification/signals.py` publishes `pipeline.gate.pass.{task_id}` or `pipeline.gate.fail.{task_id}` to `THESTUDIO_PIPELINE` when emitting existing verification signals
- `src/qa/signals.py` does the same for QA gate results
- Event payload includes: `task_id`, `stage` ("verify" or "qa"), `gate` name, `passed` boolean, `checks` array (name + result for each check), `timestamp`
- Events are visible through the SSE endpoint (end-to-end test: trigger verification, observe gate event in SSE client)
- Existing `THESTUDIO_VERIFICATION` and `THESTUDIO_QA` streams continue to function (new events are in addition, not replacement)

**Files to modify:**
- `src/verification/signals.py`
- `src/qa/signals.py`
- `src/dashboard/events_publisher.py` (add gate event helper if needed)
- `tests/unit/test_pipeline_events.py` (add gate event tests)

**Size:** S
**Depends on:** B-0.4

---

### Slice 4: Frontend Scaffolding (F-0.1 + F-0.2 + F-0.3)

Build the React application that consumes SSE events and renders pipeline state.

---

#### Story F-0.1: Frontend Project Scaffolding

**As a** developer starting the dashboard frontend,
**I want** a Vite + React + TypeScript + Zustand + Tailwind project in `frontend/`,
**so that** there is a working build toolchain for all future frontend development.

**Acceptance Criteria:**
- `frontend/` directory exists at repository root with:
  - `package.json` with React 19, Zustand 5, Tailwind CSS v4, TypeScript (strict)
  - `vite.config.ts` with proxy configuration: `/api/*` -> `http://localhost:8000`
  - `tsconfig.json` with strict mode enabled, path aliases configured
  - `tailwind.config.ts` with dark mode enabled, pipeline stage color palette from design spec
  - `index.html` entry point
  - `src/main.tsx` rendering `<App />`
  - `src/App.tsx` with a placeholder route
  - `src/styles/globals.css` with Tailwind directives
- `npm install` completes without errors
- `npm run dev` starts Vite dev server on port 5173
- `npm run build` produces `frontend/dist/` with < 50KB gzipped JS
- `npm run typecheck` passes with zero errors
- `frontend/.gitignore` excludes `node_modules/` and `dist/`
- Pipeline stage color constants defined in `src/lib/constants.ts` matching design spec hex values

**Files to create:**
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.ts`
- `frontend/index.html`
- `frontend/.gitignore`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles/globals.css`
- `frontend/src/lib/constants.ts`
- `frontend/src/lib/types.ts`

**Size:** M
**Depends on:** Nothing (can run in parallel with backend stories)

---

#### Story F-0.2: SSE Hook and Pipeline Store

**As a** React component that needs live pipeline data,
**I want** a `useSSE` hook that connects to the SSE endpoint and a Zustand `pipeline-store` that holds stage state,
**so that** any component can subscribe to real-time pipeline updates with a single hook call.

**Acceptance Criteria:**
- `frontend/src/hooks/useSSE.ts` implements an SSE connection to `/api/v1/dashboard/events/stream`:
  - Uses native `EventSource` API
  - Listens for `pipeline.stage.enter`, `pipeline.stage.exit`, `pipeline.gate.pass`, `pipeline.gate.fail` events
  - Parses JSON data and dispatches to Zustand store actions
  - Logs reconnection attempts to console
  - Cleans up `EventSource` on component unmount
- `frontend/src/stores/pipeline-store.ts` implements a Zustand store with:
  - `stages`: Record of 9 stages, each with `status` (idle | active | passed | failed), `activeTasks` array, and `lastUpdated` timestamp
  - `gates`: Array of recent gate events (last 50)
  - `updateStage(stage, partial)` action
  - `addGateEvent(event)` action
  - `connectionStatus`: 'connecting' | 'connected' | 'disconnected'
- Vitest unit tests for the store (state transitions, action behavior)
- Vitest test for the hook using a mock EventSource

**Files to create:**
- `frontend/src/hooks/useSSE.ts`
- `frontend/src/stores/pipeline-store.ts`
- `frontend/tests/stores/pipeline-store.test.ts`
- `frontend/tests/hooks/useSSE.test.ts`
- `frontend/vitest.config.ts`
- `frontend/tests/setup.ts`

**Size:** M
**Depends on:** F-0.1

---

#### Story F-0.3: Minimal Pipeline Status Page

**As a** developer watching a pipeline run,
**I want** a minimal page that shows the 9 pipeline stages with their live status,
**so that** I can verify SSE-over-NATS works end-to-end in a real browser.

**Acceptance Criteria:**
- `frontend/src/components/pipeline/PipelineStatus.tsx` renders 9 stage nodes in a horizontal rail
- Each stage node displays: stage name, status indicator (color-coded per design spec), and active task count
- Stage nodes update in real time when SSE events arrive (no page refresh)
- Gate events appear as small pass/fail indicators under the relevant stage
- A connection status indicator shows whether SSE is connected, connecting, or disconnected
- The page includes a simple event log (last 20 events) showing raw event type and timestamp for debugging
- Page uses Tailwind CSS with dark background (consistent with design spec dark-mode-first approach)
- Component test: render with mocked store state, verify stage nodes display correct status

**Files to create:**
- `frontend/src/components/pipeline/PipelineStatus.tsx`
- `frontend/src/components/pipeline/StageNode.tsx`
- `frontend/src/components/pipeline/EventLog.tsx`
- `frontend/src/components/pipeline/ConnectionIndicator.tsx`
- `frontend/tests/components/PipelineStatus.test.tsx`

**Files to modify:**
- `frontend/src/App.tsx` (render PipelineStatus as the main view)

**Size:** M
**Depends on:** F-0.2

---

### Slice 5: Auth and Static Serving (B-0.7 + B-0.6)

Secure the SSE endpoint and provide the test page through FastAPI.

---

#### Story B-0.7: Auth Token Support on SSE Endpoint

**As a** system administrator,
**I want** the SSE endpoint to require authentication via query parameter,
**so that** unauthorized clients cannot subscribe to pipeline events.

**Acceptance Criteria:**
- `GET /api/v1/dashboard/events/stream?token=...` validates the token against the existing admin auth mechanism
- Requests without a token or with an invalid token receive 401 with JSON error body
- The token validation reuses existing auth logic (no new auth system)
- Unit test: verify 401 without token, 401 with bad token, 200 with valid token
- The SSE `useSSE` hook in the frontend passes the token as a query parameter

**Files to modify:**
- `src/dashboard/events.py` (add auth check)
- `frontend/src/hooks/useSSE.ts` (pass token query parameter)
- `tests/unit/test_sse_endpoint.py` (add auth tests)

**Size:** S
**Depends on:** B-0.2

---

#### Story B-0.6: FastAPI Static Mount for Frontend

**As a** developer testing the full stack locally,
**I want** FastAPI to serve the built frontend at `/dashboard/` in production mode,
**so that** the entire application (API + SPA) runs from a single server process.

**Acceptance Criteria:**
- When `frontend/dist/` exists, FastAPI mounts it as static files at `/dashboard/`
- SPA routing works: `/dashboard/`, `/dashboard/any-path` all serve `index.html`
- When `frontend/dist/` does not exist, the mount is skipped with a log warning (graceful degradation)
- Existing admin panel at `/admin/*` is unaffected
- Integration test: build frontend, start FastAPI, verify `/dashboard/` serves the React app
- This is the production serving path; development uses Vite proxy

**Files to modify:**
- `src/app.py` (add conditional static mount)
- `tests/unit/test_dashboard_router.py` (add static mount test)

**Size:** S
**Depends on:** B-0.1, F-0.1 (needs built frontend to test)

---

### Slice 6: Frontend CI (F-0.4)

---

#### Story F-0.4: Frontend CI Pipeline

**As a** developer maintaining the frontend,
**I want** CI to run lint, typecheck, and tests on the frontend code,
**so that** regressions are caught before merge and the frontend has the same quality gate as the backend.

**Acceptance Criteria:**
- GitHub Actions workflow (or extension of existing CI) includes a `frontend` job
- Job runs: `npm ci`, `npm run typecheck`, `npm run lint`, `npm test` in `frontend/`
- Job uses Node.js 22 (matching the Dockerfile spec in design doc 05)
- Job runs on every push and PR to `master`
- Job fails the PR check if any step fails
- Job caches `node_modules/` for speed

**Files to create:**
- `.github/workflows/frontend-ci.yml` (or add job to existing `ci.yml`)

**Size:** S
**Depends on:** F-0.1 (needs the project to exist)

---

### Slice 7: End-to-End Validation

This is not a separate story but the epic-level validation. After all stories are complete:

1. Start the full dev stack (FastAPI, Temporal, NATS, Postgres)
2. Open `http://localhost:5173` (Vite dev server)
3. Trigger a pipeline run (create a TaskPacket via webhook or admin)
4. **Observe live stage transitions in the browser** as the TaskPacket flows through the pipeline
5. Close the browser tab, wait for 2+ stage transitions, reopen the tab
6. **Verify reconnection catches up** with missed events (no gaps in the stage display)
7. Verify gate pass/fail events appear when verification and QA stages complete

If all 7 steps succeed, the epic exit criteria are met: **browser displays live stage transitions from a real Temporal workflow.**

---

## Definition of Done

- [ ] All 11 stories (B-0.1 through B-0.7 + F-0.1 through F-0.4) are implemented and merged
- [ ] All unit tests pass (`pytest` for backend, `npm run test` for frontend)
- [ ] All integration tests pass (SSE-NATS bridge, reconnection, stage events)
- [ ] End-to-end validation (Slice 6 above) completed and documented
- [ ] SSE latency measured and documented (target: < 200ms p95)
- [ ] No regressions: existing 1783+ backend tests still pass
- [ ] No regressions: existing admin panel functions correctly
- [ ] Epic reviewed and approved by Meridian

---

## Meridian Review Status

### Round 1: Pending

| # | Issue | Resolution |
|---|-------|------------|
| — | — | — |
