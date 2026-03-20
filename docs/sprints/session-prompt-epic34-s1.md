# Sprint Plan: Epic 34 — Phase 0: SSE PoC + Frontend Scaffolding

**Planned by:** Helm
**Date:** 2026-03-20
**Status:** DRAFT -- Pending Meridian Review
**Epic:** `docs/epics/epic-34-phase0-sse-poc.md`
**Sprint Duration:** 2 weeks (10 working days, 2026-03-24 to 2026-04-04)
**Capacity:** Single developer, 60 hours total (10 days x 6 productive hours), 77% allocation = 46 hours, 14 hours buffer
**Buffer recommendation:** A 3rd week (2026-04-07 to 2026-04-11) should be held as contingency. The SSE-NATS bridge (B-0.2/B-0.3) and Temporal activity instrumentation (B-0.4) are novel integrations with no prior art in this codebase. If both resolve cleanly, the sprint completes in 2 weeks. If either requires a spike, the 3rd week absorbs it without schedule pressure.

---

## Sprint Goal (Testable Format)

**Objective:** Deliver a working vertical slice from Temporal workflow activity through NATS JetStream through FastAPI SSE endpoint to a React browser page. When complete, a developer opens a browser tab, triggers a pipeline run, and watches stage transitions appear in real time. If the tab is closed and reopened, it reconnects and catches up with zero missed events.

**Test:** After all 10 stories (B-0.1 through B-0.7 + F-0.1 through F-0.3) are complete:

1. `GET /api/v1/dashboard/health` returns `{"status": "ok"}` (B-0.1).
2. `GET /api/v1/dashboard/events/stream` returns `Content-Type: text/event-stream` and delivers events published to `pipeline.>` within 200ms (B-0.2).
3. Disconnect and reconnect with `Last-Event-ID: N` delivers exactly the missed events -- no duplicates, no gaps (B-0.3).
4. Running a pipeline produces `pipeline.stage.enter` and `pipeline.stage.exit` events for all 9 stages in the `THESTUDIO_PIPELINE` stream (B-0.4).
5. Verification and QA gates emit `pipeline.gate.pass` / `pipeline.gate.fail` to the same stream (B-0.5).
6. `npm run dev` in `frontend/` starts a Vite dev server; `npm run build` produces < 50KB gzipped output; `npm run typecheck` passes (F-0.1).
7. The Zustand pipeline store updates stage state when SSE events arrive; Vitest tests pass (F-0.2).
8. Opening `http://localhost:5173` shows a 9-stage pipeline rail that updates in real time as a TaskPacket flows through stages (F-0.3).
9. SSE endpoint returns 401 without a valid token; 200 with a valid token (B-0.7).
10. `http://localhost:8000/dashboard/` serves the built React app when `frontend/dist/` exists (B-0.6).
11. All existing backend tests pass (`pytest` green, 1783+ tests). Admin panel at `/admin/*` is unaffected.

**Constraint:** 2 weeks (10 working days). Backend changes confined to `src/dashboard/` (new), `src/workflow/activities.py`, `src/verification/signals.py`, `src/qa/signals.py`, and `src/app.py`. Frontend lives entirely in `frontend/` (new). No changes to `docker-compose.dev.yml` or `infra/docker-compose.prod.yml`. No new infrastructure services. Node.js 22+ required on dev machine.

---

## What's In / What's Out

**In this sprint (10 stories, ~44 estimated hours):**

| # | Story | Size | Est. Hours |
|---|-------|------|-----------|
| B-0.1 | Dashboard API Package | S | 2 |
| B-0.2 | SSE Endpoint with NATS JetStream Bridge | M | 6 |
| B-0.3 | Last-Event-ID Reconnection Support | M | 4 |
| B-0.4 | Emit Pipeline Stage Events from Temporal Activities | M | 6 |
| B-0.5 | Emit Gate Pass/Fail Events | S | 3 |
| F-0.1 | Frontend Project Scaffolding | M | 5 |
| F-0.2 | SSE Hook and Pipeline Store | M | 5 |
| F-0.3 | Minimal Pipeline Status Page | M | 5 |
| B-0.7 | Auth Token Support on SSE Endpoint | S | 3 |
| B-0.6 | FastAPI Static Mount for Frontend | S | 2 |
| | **Total estimated** | | **41 hours** |
| | **Slack (to 46 allocated)** | | **5 hours** |

**Out of scope:**
- Full Pipeline Rail UI (animations, tooltips, drill-down panels) -- Phase 1
- Activity stream events (`pipeline.activity`) -- Phase 1, Story B-1.7
- Cost events (`pipeline.cost_update`) -- Phase 1, Story B-1.9
- REST API endpoints (`/tasks`, `/gates`, `/budget`) -- Phase 1+
- Radix UI, Tremor, charts, drag-and-drop -- Phase 1+
- TanStack Router / TanStack Query -- Phase 1 (single-page PoC needs neither)
- Frontend Docker build -- Phase 1
- Playwright E2E tests -- Phase 1
- Dark/light mode toggle -- Phase 1 (ship dark only)
- Mobile/responsive layout -- not planned

---

## Dependency Review (30-Minute Pre-Planning)

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Node.js 22+ | **VERIFY BEFORE SPRINT** | Cannot run Vite 6 | Install before Day 1; if unavailable, fall back to Vite 5 + Node 20 |
| `nats-py` async client | Available (used by `src/verification/signals.py`, `src/qa/signals.py`) | Cannot create NATS bridge | Already in requirements -- no action |
| NATS JetStream running | Available via `docker-compose.dev.yml` | Cannot test SSE-NATS bridge | Existing dev stack -- no action |
| Temporal running | Available via `docker-compose.dev.yml` | Cannot test stage event emission | Existing dev stack -- no action |
| React 19 stable | **VERIFY BEFORE SPRINT** | JSX type issues, ecosystem compat | If not stable, use React 18.3 with TODO to upgrade |
| Zustand 5 | Available on npm | None | Standard install |
| Tailwind CSS v4 | Available on npm | **VERIFY API CHANGES** | v4 changed config format; confirm `tailwind.config.ts` approach still works or use CSS-based config |

### Internal Dependencies (Story-to-Story)

```
                    B-0.1 (Dashboard API Package)
                   /    |     \
                  v     v      v
              B-0.2   B-0.7*  B-0.6*
              (SSE)   (Auth)  (Static)
               |        |       |
               v        |       |
             B-0.3      |       |
           (Reconnect)  |       |
               |        |       |
               v        |       |
             B-0.4      |       |
         (Stage Events) |       |
               |        |       |
               v        |       |
             B-0.5      |       |
          (Gate Events)  |       |

   F-0.1 (Scaffolding) ----> F-0.2 (Hook + Store) ----> F-0.3 (Status Page)
```

*B-0.7 depends on B-0.2 (needs SSE endpoint to add auth to).
*B-0.6 depends on B-0.1 + F-0.1 (needs built frontend to serve).

**Critical path:** B-0.1 -> B-0.2 -> B-0.3 -> B-0.4 -> B-0.5 (backend chain).
**Parallel track:** F-0.1 -> F-0.2 -> F-0.3 (frontend chain, can start Day 1).

The backend and frontend chains are independent until F-0.2, which needs the SSE endpoint URL to exist (but can be developed against a mock). True integration happens at F-0.3 when the React page connects to the live SSE endpoint.

---

## Story Ordering: Sequence and Rationale

### Phase A: Foundation (Days 1-3)

**Why this order:** B-0.1 is the skeleton everything hangs on. F-0.1 can run in parallel because it has zero backend dependencies. B-0.2 is the architectural proof point -- if the SSE-NATS bridge does not work, the entire epic pivots. Front-loading it de-risks the sprint.

1. **Day 1 (Mon):** B-0.1 + F-0.1 in parallel
   - **B-0.1 (2h):** Create `src/dashboard/` package, health endpoint, register router in `src/app.py`. This is mechanical wiring -- low risk, high unblock value.
   - **F-0.1 (5h):** Scaffold `frontend/` with Vite + React + TypeScript + Zustand + Tailwind. Confirm `npm run dev`, `npm run build`, `npm run typecheck` all pass. Verify Vite proxy to FastAPI works with the health endpoint from B-0.1.

2. **Day 2 (Tue):** B-0.2
   - **B-0.2 (6h):** SSE endpoint with NATS JetStream bridge. This is the highest-risk story in the sprint. The async generator pattern, NATS subscription lifecycle, heartbeat timer, and client disconnect cleanup are all novel to this codebase. Allocate a full day. Write the integration test (publish to NATS, verify SSE client receives) as the acceptance gate.

3. **Day 3 (Wed):** B-0.3
   - **B-0.3 (4h):** Last-Event-ID reconnection. Extends B-0.2 with `DeliverPolicy.BY_START_SEQUENCE`. The integration test (connect, receive, disconnect, reconnect, verify gap-free replay) is the durability proof. If this passes, the real-time architecture is validated.
   - **Remaining time:** Begin F-0.2 (SSE hook) if B-0.3 completes early.

**Checkpoint (end of Day 3):** SSE-NATS bridge works with reconnection. This is the "architecture validated" gate. If we are here by Wednesday, the sprint is on track. If not, invoke the 3rd week buffer.

### Phase B: Event Emission (Days 4-5)

**Why this order:** B-0.4 instruments all 9 pipeline stages. B-0.5 extends existing signal modules -- smaller, depends on B-0.4's stream and publisher helper. These two stories make the SSE endpoint useful (it now has real events to deliver, not just test pings).

4. **Day 4 (Thu):** B-0.4
   - **B-0.4 (6h):** Create `THESTUDIO_PIPELINE` stream. Build `events_publisher.py` helper. Instrument all 9 stage activities in `src/workflow/activities.py` with enter/exit events. Fire-and-forget pattern (errors logged, never block the activity). There are 14 `@activity.defn` in activities.py -- each needs a publish call at entry and exit. Mechanical but requires care to avoid regressions.

5. **Day 5 (Fri):** B-0.5 + F-0.2
   - **B-0.5 (3h):** Extend `src/verification/signals.py` and `src/qa/signals.py` to also publish gate events to `THESTUDIO_PIPELINE`. Small delta on existing code.
   - **F-0.2 (remaining ~3h, continue Day 6):** Begin SSE hook and Zustand pipeline store. Write store tests first (state transition logic), then the `useSSE` hook with mock EventSource.

**Checkpoint (end of Day 5 / Week 1):** All backend event emission is complete. SSE endpoint streams real pipeline events. Backend is "done" except for auth (B-0.7) and static mount (B-0.6). Frontend scaffolding exists and hook development is underway.

### Phase C: Frontend Integration (Days 6-8)

**Why this order:** F-0.2 and F-0.3 are the frontend stories that consume what the backend now produces. B-0.7 (auth) is sequenced after the frontend hook exists so the token-passing logic can be implemented in the same pass.

6. **Day 6 (Mon):** F-0.2 (complete)
   - **F-0.2 (remaining 2h + testing):** Complete the SSE hook, pipeline store, and Vitest tests. Verify that connecting to the live SSE endpoint from the Vite dev server works (proxy test).

7. **Day 7 (Tue):** F-0.3
   - **F-0.3 (5h):** Build the minimal Pipeline Status Page. 9 stage nodes in a horizontal rail, color-coded by status, gate indicators, connection status, and a debug event log (last 20 events). Dark mode only. Tailwind styling. Component test with mocked store state.

8. **Day 8 (Wed):** B-0.7 + B-0.6
   - **B-0.7 (3h):** Add auth token validation to SSE endpoint (query parameter). Update `useSSE` hook to pass token. Unit tests for 401/200 behavior.
   - **B-0.6 (2h):** Conditional static mount in `src/app.py`. When `frontend/dist/` exists, serve at `/dashboard/`. SPA catch-all routing. Graceful skip when dist is missing.

**Checkpoint (end of Day 8):** All 10 stories are code-complete. Integration testing begins.

### Phase D: Integration and Validation (Days 9-10)

**Why this order:** End-to-end validation requires the full stack. Regression testing ensures the existing 1783+ tests still pass. This is the "ship or fix" phase.

9. **Day 9 (Thu):** End-to-end validation
   - Start full dev stack (FastAPI, Temporal, NATS, Postgres)
   - Open `http://localhost:5173` in browser
   - Trigger a pipeline run via webhook or admin
   - **Observe live stage transitions** in the browser
   - Close tab, wait for 2+ stage transitions, reopen
   - **Verify reconnection catches up** (no gaps)
   - Verify gate events appear during verify/QA stages
   - Measure SSE latency (target: < 200ms p95)
   - Document results in epic

10. **Day 10 (Fri):** Regression testing + cleanup
    - Run full `pytest` suite -- confirm 1783+ tests still pass
    - Run `ruff check .` and `ruff format .`
    - Run `npm run typecheck` and `npm run test` in frontend
    - Verify admin panel at `/admin/*` still works
    - Fix any issues found in validation
    - Update epic status, mark stories complete
    - **Request Meridian review of completed epic**

---

## Estimation Notes (Risk Discovery)

### B-0.2: SSE Endpoint (6h) -- Highest Risk

**Unknowns:**
- The `nats-py` async client has never been used for long-lived subscriptions in this codebase. The existing usage in `signals.py` is fire-and-forget publish, not subscribe. If the subscription blocks the event loop, the fallback is an `asyncio.Queue` bridge with a dedicated reader task.
- `StreamingResponse` + `async generator` + `is_disconnected()` is a pattern that works in theory but may have edge cases with Uvicorn's ASGI implementation (e.g., disconnect detection timing, buffering behavior).
- The heartbeat timer (15s keepalive) must coexist with the NATS message iterator. This likely requires `asyncio.wait` with a timeout rather than a simple `async for`.

**Assumption:** The `nats-py` async iterator yields messages without blocking indefinitely (it should use `asyncio`-native primitives). If this assumption is wrong, add 2-3 hours for the queue bridge pattern.

### B-0.4: Stage Event Emission (6h) -- Medium Risk

**Unknowns:**
- There are 14 `@activity.defn` in `activities.py`. Not all may map cleanly to the 9 pipeline stages (some may be utility activities). Need to audit which activities correspond to which stages before instrumenting.
- Activities run in the Temporal worker process, not the FastAPI process. The NATS connection must be established in the worker context, not reused from FastAPI. This means `events_publisher.py` needs its own connection management.

**Assumption:** Temporal activities can make outbound NATS connections without violating the activity sandbox. The `temporalio` Python SDK does not restrict network calls in activities (unlike some workflow restrictions). Confirmed by existing usage in the codebase (activities call LLM APIs).

### F-0.1: Frontend Scaffolding (5h) -- Low-Medium Risk

**Unknowns:**
- Tailwind CSS v4 changed its configuration model significantly (CSS-based config vs. JS config file). Need to verify whether `tailwind.config.ts` is still the correct approach or if v4 uses `@config` directive in CSS.
- React 19 may still have ecosystem compatibility issues (e.g., testing library, Zustand types). If blockers appear, fall back to React 18.3.

**Assumption:** The standard Vite + React + Tailwind template works as documented. If not, budget 1-2 hours for troubleshooting.

### F-0.2: SSE Hook + Store (5h) -- Low Risk

**Unknowns:**
- Mocking `EventSource` in Vitest requires either `vitest-fetch-mock` or a manual mock. The native `EventSource` API is not available in Node.js test environment (it is browser-only). Need `eventsource` polyfill or a mock implementation for tests.

**Assumption:** A mock EventSource is straightforward (it is a simple event emitter interface). Budget exists in the 5h estimate.

---

## Technical Spikes

### Spike 1: NATS Async Subscription in FastAPI SSE (30 min, Day 2 morning)

**Question:** Does `nats-py`'s async subscription iterator work correctly inside a FastAPI `StreamingResponse` async generator, or does it need a queue bridge?

**Method:** Write a minimal test script:
1. Connect to NATS, subscribe to a test subject
2. Wrap the subscription in an async generator
3. Use `StreamingResponse` to stream events
4. Publish a test message, verify the SSE client receives it
5. Disconnect the client, verify the subscription is cleaned up

**Decision point:** If the direct approach works, proceed with B-0.2 as designed. If it blocks, implement the `asyncio.Queue` bridge pattern (add 2h to B-0.2).

### Spike 2: Tailwind CSS v4 Configuration (15 min, Day 1 during F-0.1)

**Question:** Does Tailwind v4 still use `tailwind.config.ts`, or has it moved to CSS-based configuration?

**Method:** Check Tailwind v4 docs. If CSS-based, adjust F-0.1 to use the new approach. If `tailwind.config.ts` still works, proceed as designed.

**Decision point:** Adjust scaffolding approach if needed. No schedule impact (absorbed within F-0.1's 5h estimate).

---

## Compressible Stories (Cut if Time Runs Short)

Two stories are explicitly identified as compressible:

1. **B-0.6 (Static Mount, 2h):** Can be deferred entirely. Development uses the Vite dev server; the static mount is a production convenience. Deferring it does not block the end-to-end validation (which uses Vite proxy).

2. **B-0.7 (Auth, 3h):** Can be deferred to a follow-up. The SSE endpoint works without auth for local development. Auth is required before any non-local deployment, but Phase 0 is a local PoC.

If both are cut, 5 hours are recovered. The sprint still delivers the core proof: browser displays live pipeline stage transitions from a real Temporal workflow.

---

## Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | NATS async subscription blocks FastAPI event loop, causing SSE stalls | Medium | High | Spike 1 on Day 2 morning; fallback to asyncio.Queue bridge pattern |
| 2 | Vite proxy drops SSE streaming connection | Medium | Medium | Test on Day 1 (F-0.1); configure `changeOrigin: true` and `ws: true` in proxy; disable response buffering |
| 3 | React 19 not stable or ecosystem compat issues | Low | Medium | Fall back to React 18.3; no Phase 0 features require React 19 specifics |
| 4 | Tailwind v4 config model changed | Medium | Low | Spike 2; absorbed within F-0.1 estimate |
| 5 | Instrumenting 14 activities introduces regressions | Low | High | Fire-and-forget pattern with try/except; unit tests mock NATS; full pytest regression on Day 10 |
| 6 | NATS connection management differs between FastAPI process and Temporal worker | Medium | Medium | `events_publisher.py` manages its own singleton connection, separate from signals.py connections |
| 7 | Node.js 22 not installed on dev machine | Low | Medium | Install before Day 1; if blocked, use Vite 5 + Node 20 |
| 8 | EventSource mock unavailable in Vitest (Node env) | Low | Low | Write a simple mock class (EventSource interface is ~10 lines); or use `eventsource` npm package |

---

## Definition of Done (Sprint-Level)

- [ ] All 10 stories implemented and passing their individual acceptance criteria
- [ ] Backend: `pytest` passes (1783+ tests, zero regressions)
- [ ] Backend: `ruff check .` clean, `ruff format .` clean
- [ ] Frontend: `npm run typecheck` passes with zero errors
- [ ] Frontend: `npm run test` passes (Vitest, store + hook + component tests)
- [ ] Frontend: `npm run build` produces < 50KB gzipped JS
- [ ] End-to-end validation complete (Slice 6 from epic): browser shows live stage transitions, reconnection catches up
- [ ] SSE latency measured and documented (target: < 200ms p95)
- [ ] Admin panel at `/admin/*` confirmed unaffected
- [ ] No changes to `docker-compose.dev.yml` or `infra/docker-compose.prod.yml`
- [ ] Epic 34 acceptance criteria AC 1-7 all verified
- [ ] Meridian review requested and passed

---

## Day-by-Day Summary

| Day | Date | Stories | Hours | Cumulative |
|-----|------|---------|-------|------------|
| 1 | Mon 3/24 | B-0.1 + F-0.1 | 7h | 7h |
| 2 | Tue 3/25 | B-0.2 (+ Spike 1) | 6h | 13h |
| 3 | Wed 3/26 | B-0.3 (+ start F-0.2) | 5h | 18h |
| 4 | Thu 3/27 | B-0.4 | 6h | 24h |
| 5 | Fri 3/28 | B-0.5 + F-0.2 (partial) | 6h | 30h |
| 6 | Mon 3/31 | F-0.2 (complete) | 3h | 33h |
| 7 | Tue 4/1 | F-0.3 | 5h | 38h |
| 8 | Wed 4/2 | B-0.7 + B-0.6 | 5h | 43h |
| 9 | Thu 4/3 | E2E validation | 5h | 48h |
| 10 | Fri 4/4 | Regression + cleanup + Meridian review request | 4h | 52h |

**Note:** Days 9-10 use buffer hours. If stories complete faster than estimated (likely for the S-sized stories), validation starts sooner.

---

## Pre-Sprint Checklist (Before Day 1)

- [ ] Node.js 22+ installed and verified (`node --version`)
- [ ] `npm` or `pnpm` available
- [ ] React 19 availability confirmed on npm (`npm view react version`)
- [ ] Tailwind CSS v4 configuration approach confirmed
- [ ] Dev stack running: `docker-compose.dev.yml` (NATS, Temporal, Postgres)
- [ ] `pytest` baseline passing (1783+ tests)
- [ ] This sprint plan reviewed and approved by Meridian

---

## Retro Actions from Previous Sprints

| Action | Source | Applied Here |
|--------|--------|-------------|
| Always check for existing infra files before estimating | Epic 11 retro | Verified NATS signal modules exist; verified no `src/dashboard/` or `frontend/` yet |
| De-risk novel integrations with a spike before committing | Epic 18 retro | Spike 1 (NATS subscription in SSE) scheduled for Day 2 morning |
| Identify two compressible stories per sprint | Sprint planning pattern | B-0.6 (static mount) and B-0.7 (auth) identified as compressible |
| Spread creative work across slack time | Epic 23 retro | Frontend stories interleaved with backend rather than back-loaded |

---

**IMPORTANT: This plan requires Meridian review before commit.** The plan should be evaluated against the 7 Meridian questions and red flags before any work begins.
