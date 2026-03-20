# 05 — Technology & Architecture Design Specification

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** Frontend technology stack, real-time data flow architecture, API contract design, component architecture, deployment model, and migration path from the current admin panel. How to build everything described in documents 01-04.

---

## 1. Design Philosophy

TheStudio's backend is Python (FastAPI, Temporal, NATS, PostgreSQL). The new frontend must integrate cleanly without forcing a rewrite. The architecture should:

- **Separate concerns**: React SPA communicates with FastAPI via REST + SSE. No server-rendered templates for the new UI.
- **Coexist with existing admin**: The current Jinja-based admin panel continues to work. The new SPA is deployed alongside it, not as a replacement (initially).
- **Leverage existing infrastructure**: NATS JetStream for real-time events, PostgreSQL for persistence, Temporal for workflow state — the frontend consumes these, it doesn't add new infrastructure.

---

## 2. Frontend Technology Stack

### 2.1 Core Stack Decision

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Framework** | React 19 | Largest ecosystem, best tooling, Aperant and Mission Control both use React — patterns are directly portable |
| **Build tool** | Vite 6 | Fast builds, native ESM, excellent DX |
| **Language** | TypeScript (strict) | Type safety critical for complex pipeline state |
| **State management** | Zustand 5 | Lightweight, proven at scale (Aperant uses 24+ stores), no boilerplate |
| **Styling** | Tailwind CSS v4 | Utility-first, fast iteration, consistent with existing admin panel classes |
| **Component library** | Radix UI (headless) | Accessible primitives, unstyled (we control the look), keyboard support built-in |
| **Charts** | Recharts or Tremor | Cost dashboards, analytics charts. Tremor preferred for dashboard-specific components |
| **Drag-and-drop** | @dnd-kit | Keyboard accessible, performant, proven in Aperant |
| **Markdown** | react-markdown + rehype-raw | Intent Spec rendering, evidence comments |
| **Code/Diff viewer** | Monaco Editor (React wrapper) | Intent Spec editing, diff views in PR Evidence Explorer |
| **Icons** | Lucide React | Clean, consistent (already a dependency in TheStudio's package.json via Aperant influence) |
| **HTTP client** | Native fetch + TanStack Query v5 | Caching, background refetch, optimistic updates |
| **Real-time** | Native EventSource (SSE) | Browser-native, auto-reconnect, no library needed |
| **Routing** | TanStack Router | Type-safe routing, file-based conventions |
| **Testing** | Vitest + React Testing Library | Fast, Vite-native, same as Aperant uses |

### 2.2 Why Not Other Options

| Alternative | Why Not |
|-------------|---------|
| Next.js / Remix | Server-side rendering unnecessary — this is a dashboard, not a public website. Added complexity without benefit. |
| Vue / Svelte | Smaller ecosystem for dashboard components. React has more off-the-shelf solutions (Tremor, Radix, etc.) |
| HTMX + Alpine.js | Insufficient for timeline visualization, drag-and-drop Kanban, and real-time streaming UIs. Good for simple admin panels, not rich dashboards. |
| Redux | Overkill for this use case. Zustand is simpler, less boilerplate, proven at similar scale. |
| Ant Design / MUI | Opinionated styling conflicts with our dark-mode dashboard aesthetic. Radix primitives give us full control. |

### 2.3 Design System

**Theme:**
- Dark mode primary (pipeline dashboards are typically dark — Temporal UI, Grafana, Devin)
- Light mode secondary (opt-in via system preference or toggle)
- Color palette: derived from existing admin panel colors, extended with pipeline stage colors

**Pipeline stage colors:**

| Stage | Color | Hex |
|-------|-------|-----|
| Intake | Slate | #64748b |
| Context | Blue | #3b82f6 |
| Intent | Indigo | #6366f1 |
| Router | Purple | #a855f7 |
| Assembler | Violet | #8b5cf6 |
| Implement | Cyan | #06b6d4 |
| Verify | Amber | #f59e0b |
| QA | Orange | #f97316 |
| Publish | Green | #22c55e |

**Status colors:**
- Active / In progress: Blue (#3b82f6)
- Passed / Success: Green (#22c55e)
- Failed / Error: Red (#ef4444)
- Warning / Loopback: Amber (#f59e0b)
- Idle / Queued: Gray (#6b7280)
- Review needed: Indigo (#6366f1)

**Typography:**
- UI: Inter (system font stack fallback)
- Code/monospace: JetBrains Mono or Fira Code
- Size scale: 12px base, 14px body, 16px headings

**Component patterns:**
- Cards with subtle border (1px border-color: white/10%)
- Rounded corners (8px standard, 12px for large containers)
- Shadows: minimal (dashboard aesthetic, not paper metaphor)
- Transitions: 150ms ease for interactive elements
- Toast notifications: bottom-right, auto-dismiss 5s

---

## 3. API Contract Design

### 3.1 REST API Endpoints

The frontend communicates with FastAPI through a versioned REST API. These endpoints are **new** — they don't replace the existing admin API.

```
Base: /api/v1/dashboard/

── TaskPackets ──
GET    /tasks                     List TaskPackets (paginated, filterable)
GET    /tasks/:id                 Get TaskPacket detail
POST   /tasks                     Create TaskPacket (manual task creation)
PATCH  /tasks/:id                 Update TaskPacket (edit metadata)
DELETE /tasks/:id                 Delete/abort TaskPacket

── Pipeline Control ──
POST   /tasks/:id/pause           Pause TaskPacket
POST   /tasks/:id/resume          Resume TaskPacket
POST   /tasks/:id/retry           Retry current stage
POST   /tasks/:id/redirect        Redirect to earlier stage
POST   /tasks/:id/abort           Abort with reason

── Intent ──
GET    /tasks/:id/intent          Get Intent Specification (current + versions)
PUT    /tasks/:id/intent          Update Intent Specification (developer edit)
POST   /tasks/:id/intent/approve  Approve Intent Spec
POST   /tasks/:id/intent/refine   Request refinement with feedback

── Gates ──
GET    /gates                     List gate events (paginated, filterable)
GET    /gates/:id                 Get gate detail with evidence
GET    /tasks/:id/gates           Get gates for specific TaskPacket

── Trust ──
GET    /trust/rules               Get trust tier rules
PUT    /trust/rules               Update trust tier rules
GET    /trust/safety-bounds       Get safety bounds
PUT    /trust/safety-bounds       Update safety bounds

── Budget ──
GET    /budget/summary            Get budget summary (current period)
GET    /budget/history            Get spend history (time series)
GET    /budget/by-stage           Get cost breakdown by stage
GET    /budget/by-model           Get cost breakdown by model
GET    /budget/config             Get budget configuration
PUT    /budget/config             Update budget configuration

── Analytics ──
GET    /analytics/throughput      Tasks per day/week
GET    /analytics/bottlenecks     Avg time per stage
GET    /analytics/categories      Performance by category
GET    /analytics/failures        Gate failure analysis

── Reputation ──
GET    /reputation/experts        Expert performance table
GET    /reputation/outcomes       Recent outcomes with signals
GET    /reputation/drift          Drift detection alerts

── GitHub ──
GET    /github/issues             List issues from connected repo
POST   /github/import             Import issues as TaskPackets
GET    /github/projects/config    Get Projects sync configuration
PUT    /github/projects/config    Update Projects sync configuration
POST   /github/projects/sync      Force full sync

── Real-Time ──
GET    /events/stream             SSE endpoint (all pipeline events)
```

### 3.2 SSE Event Stream

Single endpoint for all real-time events:

```
GET /api/v1/dashboard/events/stream
Accept: text/event-stream
Last-Event-ID: <sequence number>

Response (streaming):

id: 1042
event: pipeline.stage_enter
data: {"task_id":"142","stage":"implement","timestamp":"2026-03-20T10:49:00Z"}

id: 1043
event: pipeline.activity
data: {"task_id":"142","stage":"implement","type":"file_read","content":"Reading src/auth/login.py","timestamp":"2026-03-20T10:49:12Z"}

id: 1044
event: pipeline.cost_update
data: {"task_id":"142","cost_delta":0.02,"total_cost":0.42}

id: 1045
event: pipeline.gate_pass
data: {"task_id":"142","stage":"implement","gate":"verify","checks":[...],"timestamp":"2026-03-20T10:57:00Z"}

id: 1046
event: github.pr.created
data: {"task_id":"142","pr_number":289,"url":"..."}

id: 1047
event: notification
data: {"type":"review_needed","task_id":"143","message":"Intent Spec ready for review"}
```

**Event categories:**
- `pipeline.*` — Stage transitions, gate results, loopbacks
- `pipeline.activity` — Agent tool calls, reasoning, progress
- `pipeline.cost_update` — Incremental cost changes
- `github.*` — GitHub webhook events (PR status, comments, merges)
- `notification` — User-facing notifications
- `system.*` — Health, errors, reconnection signals

**Reconnection:**
- Client sends `Last-Event-ID` on reconnect
- Server replays from NATS JetStream by sequence number
- If gap > 1000 events, sends `system.full_state` with current snapshot instead

### 3.3 Response Format

All REST endpoints return:

```json
{
  "data": { ... },
  "meta": {
    "total": 26,
    "page": 1,
    "per_page": 20,
    "timestamp": "2026-03-20T10:55:00Z"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "TaskPacket 999 does not exist",
    "detail": null
  }
}
```

---

## 4. Component Architecture

### 4.1 Directory Structure

```
frontend/                          # New SPA (separate from existing admin)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── index.html
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                   # Entry point
│   ├── App.tsx                    # Root component + router
│   ├── api/                       # API client layer
│   │   ├── client.ts              # Base fetch + auth
│   │   ├── tasks.ts               # TaskPacket CRUD
│   │   ├── gates.ts               # Gate queries
│   │   ├── budget.ts              # Budget queries + mutations
│   │   ├── trust.ts               # Trust tier CRUD
│   │   ├── analytics.ts           # Analytics queries
│   │   ├── github.ts              # GitHub integration
│   │   └── events.ts              # SSE connection manager
│   ├── stores/                    # Zustand state stores
│   │   ├── pipeline-store.ts      # Pipeline rail state
│   │   ├── task-store.ts          # TaskPacket list + detail
│   │   ├── activity-store.ts      # Live activity streams
│   │   ├── gate-store.ts          # Gate events
│   │   ├── budget-store.ts        # Budget state
│   │   ├── trust-store.ts         # Trust tier rules
│   │   ├── notification-store.ts  # Notifications
│   │   ├── board-store.ts         # Kanban board state
│   │   └── settings-store.ts      # UI preferences
│   ├── components/                # Reusable UI components
│   │   ├── ui/                    # Design system primitives
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   ├── Progress.tsx
│   │   │   └── ...
│   │   ├── pipeline/              # Pipeline visualization
│   │   │   ├── PipelineRail.tsx
│   │   │   ├── StageNode.tsx
│   │   │   ├── StageDetailPanel.tsx
│   │   │   ├── LoopbackArc.tsx
│   │   │   └── TaskMinimap.tsx
│   │   ├── timeline/              # TaskPacket timeline
│   │   │   ├── TaskTimeline.tsx
│   │   │   ├── StageBar.tsx
│   │   │   ├── GateCard.tsx
│   │   │   └── LoopbackEntry.tsx
│   │   ├── activity/              # Live activity stream
│   │   │   ├── ActivityStream.tsx
│   │   │   ├── ActivityEntry.tsx
│   │   │   ├── SubphaseGroup.tsx
│   │   │   └── FilterBar.tsx
│   │   ├── planning/              # Planning experience
│   │   │   ├── TriageQueue.tsx
│   │   │   ├── TriageCard.tsx
│   │   │   ├── IntentEditor.tsx
│   │   │   ├── IntentViewer.tsx
│   │   │   ├── ComplexityDashboard.tsx
│   │   │   ├── RiskHeatmap.tsx
│   │   │   ├── ExpertRouting.tsx
│   │   │   └── TaskCreationModal.tsx
│   │   ├── board/                 # Backlog & Kanban
│   │   │   ├── BacklogBoard.tsx
│   │   │   ├── KanbanView.tsx
│   │   │   ├── PriorityMatrix.tsx
│   │   │   ├── TimelineView.tsx
│   │   │   ├── BoardCard.tsx
│   │   │   └── ColumnHeader.tsx
│   │   ├── gates/                 # Gate inspector
│   │   │   ├── GateInspector.tsx
│   │   │   ├── GateList.tsx
│   │   │   ├── GateDetail.tsx
│   │   │   └── GateHealthMetrics.tsx
│   │   ├── controls/              # Steering & governance
│   │   │   ├── TrustConfig.tsx
│   │   │   ├── RuleBuilder.tsx
│   │   │   ├── SafetyBounds.tsx
│   │   │   ├── SteeringActions.tsx
│   │   │   ├── RedirectModal.tsx
│   │   │   └── AbortConfirmation.tsx
│   │   ├── budget/                # Cost dashboard
│   │   │   ├── BudgetDashboard.tsx
│   │   │   ├── SpendChart.tsx
│   │   │   ├── CostByStage.tsx
│   │   │   ├── CostByModel.tsx
│   │   │   └── BudgetAlerts.tsx
│   │   ├── reputation/            # Reputation dashboard
│   │   │   ├── ReputationDashboard.tsx
│   │   │   ├── ExpertTable.tsx
│   │   │   ├── OutcomeSignals.tsx
│   │   │   └── DriftAlerts.tsx
│   │   ├── github/                # GitHub integration
│   │   │   ├── IssueImport.tsx
│   │   │   ├── ProjectsSync.tsx
│   │   │   ├── PREvidence.tsx
│   │   │   ├── DiffViewer.tsx
│   │   │   └── EvidenceComment.tsx
│   │   ├── analytics/             # Analytics
│   │   │   ├── AnalyticsDashboard.tsx
│   │   │   ├── ThroughputChart.tsx
│   │   │   ├── BottleneckChart.tsx
│   │   │   ├── CategoryBreakdown.tsx
│   │   │   └── FailureAnalysis.tsx
│   │   └── layout/                # App layout
│   │       ├── AppShell.tsx
│   │       ├── Sidebar.tsx
│   │       ├── TopBar.tsx
│   │       ├── BottomBar.tsx
│   │       └── NotificationBell.tsx
│   ├── hooks/                     # Custom React hooks
│   │   ├── useSSE.ts              # SSE connection + auto-reconnect
│   │   ├── usePipelineState.ts    # Derived pipeline state
│   │   ├── useSmartScroll.ts      # Auto-scroll with position preservation
│   │   ├── useKeyboardNav.ts      # Keyboard navigation
│   │   └── useDraft.ts            # Draft persistence to localStorage
│   ├── lib/                       # Utilities
│   │   ├── cn.ts                  # clsx + tailwind-merge
│   │   ├── format.ts              # Date, currency, duration formatters
│   │   ├── constants.ts           # Stage colors, status icons
│   │   └── types.ts               # Shared TypeScript types
│   └── styles/
│       └── globals.css            # Tailwind base + custom properties
└── tests/
    ├── setup.ts
    ├── components/
    └── stores/
```

### 4.2 State Management Pattern

```typescript
// Example: pipeline-store.ts
import { create } from 'zustand';

interface StageState {
  status: 'idle' | 'active' | 'review';
  taskCount: number;
  activeTasks: string[];
}

interface PipelineState {
  stages: Record<string, StageState>;
  loopbacks: Loopback[];
  totalActive: number;
  totalQueued: number;
  runningCost: number;

  // Actions
  updateStage: (stage: string, state: Partial<StageState>) => void;
  addLoopback: (loopback: Loopback) => void;
  resolveLoopback: (id: string) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  stages: {
    intake: { status: 'idle', taskCount: 0, activeTasks: [] },
    context: { status: 'idle', taskCount: 0, activeTasks: [] },
    // ... all 9 stages
  },
  loopbacks: [],
  totalActive: 0,
  totalQueued: 0,
  runningCost: 0,

  updateStage: (stage, state) =>
    set((prev) => ({
      stages: { ...prev.stages, [stage]: { ...prev.stages[stage], ...state } },
    })),
  addLoopback: (loopback) =>
    set((prev) => ({ loopbacks: [...prev.loopbacks, loopback] })),
  resolveLoopback: (id) =>
    set((prev) => ({ loopbacks: prev.loopbacks.filter((l) => l.id !== id) })),
}));
```

### 4.3 SSE Hook Pattern

```typescript
// hooks/useSSE.ts
import { useEffect, useRef } from 'react';
import { usePipelineStore } from '../stores/pipeline-store';
import { useActivityStore } from '../stores/activity-store';
import { useNotificationStore } from '../stores/notification-store';

export function useSSE() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const updateStage = usePipelineStore((s) => s.updateStage);
  const addActivity = useActivityStore((s) => s.addEntry);
  const addNotification = useNotificationStore((s) => s.add);

  useEffect(() => {
    const es = new EventSource('/api/v1/dashboard/events/stream');
    eventSourceRef.current = es;

    es.addEventListener('pipeline.stage_enter', (e) => {
      const data = JSON.parse(e.data);
      updateStage(data.stage, { status: 'active', activeTasks: [data.task_id] });
    });

    es.addEventListener('pipeline.activity', (e) => {
      const data = JSON.parse(e.data);
      addActivity(data.task_id, data);
    });

    es.addEventListener('notification', (e) => {
      const data = JSON.parse(e.data);
      addNotification(data);
    });

    es.onerror = () => {
      // EventSource auto-reconnects. Log for debugging.
      console.warn('SSE connection lost, reconnecting...');
    };

    return () => es.close();
  }, []);
}
```

---

## 5. Real-Time Data Flow Architecture

### 5.1 End-to-End Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│   Temporal    │    │    NATS      │    │   FastAPI     │    │  Browser  │
│   Workflow    │───▶│  JetStream   │───▶│  SSE Handler  │───▶│  React   │
│  Activities   │    │  (pipeline.*)│    │  (/events/    │    │  App     │
│              │    │              │    │   stream)     │    │          │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
       │                    │                   │                  │
  emit event          persist to           subscribe to       EventSource
  after each          stream with          NATS subjects,     + Zustand
  activity            replay support       filter by client   stores
```

### 5.2 NATS Subject Hierarchy

```
pipeline.stage.enter.{task_id}        — TaskPacket enters a stage
pipeline.stage.exit.{task_id}         — TaskPacket exits a stage
pipeline.gate.pass.{task_id}          — Gate passed
pipeline.gate.fail.{task_id}          — Gate failed
pipeline.loopback.start.{task_id}     — Loopback initiated
pipeline.loopback.resolve.{task_id}   — Loopback resolved
pipeline.activity.{task_id}           — Agent tool call / reasoning
pipeline.cost.{task_id}               — Cost increment
github.pr.{action}                    — GitHub PR events
github.issue.{action}                 — GitHub issue events
system.health                         — System health heartbeat
```

### 5.3 SSE Handler (FastAPI)

```python
# New file: src/dashboard/events.py

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import nats
import asyncio
import json

router = APIRouter(prefix="/api/v1/dashboard")

@router.get("/events/stream")
async def event_stream(request: Request, last_event_id: str | None = None):
    """SSE endpoint that bridges NATS JetStream to browser clients."""

    async def generate():
        nc = await nats.connect()
        js = nc.jetstream()

        # Subscribe to all pipeline events
        sub = await js.subscribe(
            "pipeline.>",
            deliver_policy=(
                nats.api.DeliverPolicy.BY_START_SEQUENCE
                if last_event_id
                else nats.api.DeliverPolicy.NEW
            ),
            opt_start_seq=int(last_event_id) + 1 if last_event_id else None,
        )

        sequence = int(last_event_id or 0)

        try:
            async for msg in sub.messages:
                if await request.is_disconnected():
                    break

                sequence += 1
                event_type = msg.subject.replace(".", "_", 1)  # pipeline.stage_enter
                data = json.loads(msg.data)

                yield f"id: {sequence}\nevent: {msg.subject}\ndata: {json.dumps(data)}\n\n"

                await msg.ack()
        finally:
            await sub.unsubscribe()
            await nc.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

---

## 6. Deployment Model

### 6.1 Development

```bash
# Terminal 1: Backend (existing)
uvicorn src.app:app --reload

# Terminal 2: Frontend (new)
cd frontend && npm run dev     # Vite dev server on :5173

# Vite proxies /api/* to FastAPI on :8000
```

Vite config:
```typescript
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

### 6.2 Production

Two deployment options:

**Option A: FastAPI serves the SPA (simpler)**
```
Build: cd frontend && npm run build → frontend/dist/
FastAPI: mount frontend/dist/ as static files
Route: /* → index.html (SPA routing), /api/* → API handlers
```

```python
# src/app.py addition
from fastapi.staticfiles import StaticFiles

app.mount("/dashboard", StaticFiles(directory="frontend/dist", html=True), name="dashboard")
```

**Option B: Separate containers (more scalable)**
```
nginx → /api/*       → FastAPI container
     → /dashboard/*  → Static files container (nginx serving frontend/dist/)
     → /admin/*      → FastAPI admin (existing Jinja templates)
```

**Recommendation:** Start with Option A for simplicity. Move to Option B when scaling requires it.

### 6.3 Docker Integration

Add to existing `docker-compose.prod.yml`:

```yaml
services:
  # ... existing services ...

  frontend-build:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    # Multi-stage build: Node for build, copy dist to runtime
```

Frontend Dockerfile:
```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

---

## 7. Migration Path

### 7.1 Phase 0: Coexistence

The new SPA runs alongside the existing admin panel:

```
/admin/*       → Existing Jinja admin (unchanged)
/dashboard/*   → New React SPA
/api/v1/admin/ → Existing admin API (unchanged)
/api/v1/dashboard/ → New dashboard API
```

Both share the same database, NATS, and Temporal connections. No migration needed for existing functionality.

### 7.2 Phase 1-5: Incremental Feature Addition

Each phase adds new React components and API endpoints without touching existing admin code:

| Phase | Frontend | Backend |
|-------|----------|---------|
| 1 | Pipeline Rail, Timeline, Activity Stream, Gate Inspector | SSE endpoint, gate query endpoints |
| 2 | Triage Queue, Intent Editor, Complexity Dashboard, Board | Task CRUD, intent endpoints, board state |
| 3 | Trust Config, Steering Controls, Budget Dashboard | Trust rules engine, control signal API, budget queries |
| 4 | GitHub Projects Sync, PR Evidence, Issue Import | GitHub GraphQL integration, projects sync worker |
| 5 | Analytics, Reputation, Outcomes | Analytics aggregation queries, drift computation |

### 7.3 Phase 6: Admin Panel Sunset (Future)

Once the React SPA covers all admin functionality, the Jinja admin panel can be retired. This is optional and not on the current roadmap.

---

## 8. Performance Budget

| Metric | Target | Rationale |
|--------|--------|-----------|
| Initial load (JS bundle) | < 200KB gzipped | Dashboard must feel fast on first load |
| Time to interactive | < 2s | Pipeline state visible quickly |
| SSE latency (event → render) | < 100ms | Real-time must feel real-time |
| Kanban drag operation | < 16ms per frame | Smooth 60fps drag-and-drop |
| Activity stream (5000 entries) | Smooth scroll | Virtual scrolling required |
| Memory (1hr session, 5 active tasks) | < 150MB | No memory leaks from SSE accumulation |

**Optimization strategies:**
- Code splitting by route (lazy load analytics, reputation, settings)
- Virtual scrolling for activity stream and gate list
- SSE event batching (50ms debounce before store update)
- TanStack Query for API response caching (avoid redundant fetches)
- IntersectionObserver for animation pausing (Aperant pattern)
- Zustand selectors for minimal re-renders

---

## 9. Security Considerations

### 9.1 Authentication

Phase 1-3: Basic token auth (same as existing admin)
Phase 4+: Consider OAuth2 / session-based auth if multi-user access is needed

### 9.2 API Security

- All dashboard API endpoints behind auth middleware
- CORS configured for dashboard origin only
- SSE endpoint requires auth token (passed as query parameter since EventSource doesn't support headers natively)
- Rate limiting on mutation endpoints (trust rules, budget config)
- Input validation via Pydantic models on all endpoints

### 9.3 GitHub Token Security

- GitHub PAT with `project` scope stored encrypted in PostgreSQL (not in environment variables)
- Token used only server-side — never exposed to browser
- Webhook signature verification on all incoming GitHub events (existing)

---

## 10. Testing Strategy

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Component tests | Vitest + React Testing Library | All interactive components |
| Store tests | Vitest | All Zustand stores (state transitions, actions) |
| API integration | Vitest + msw (Mock Service Worker) | All API calls, SSE reconnection |
| E2E | Playwright | Critical paths: pipeline rail → timeline → activity, triage → intent → approve |
| Visual regression | Playwright screenshots | Pipeline rail, board, timeline (dark + light mode) |

---

## 11. Open Source References

| Project | What to Study | Link |
|---------|---------------|------|
| Mission Control | Dashboard layout, 32-panel system, agent Kanban | [github.com/builderz-labs/mission-control](https://github.com/builderz-labs/mission-control) |
| Plane | GitHub sync, Gantt charts, open-source PM | [plane.so](https://plane.so) |
| temporal-flow-web | Temporal workflow visualization | [github.com/itaisoudry/temporal-flow-web](https://github.com/itaisoudry/temporal-flow-web) |
| Temporal UI | Timeline view, compact view, real-time liveness | [github.com/temporalio/ui](https://github.com/temporalio/ui) |
| Tremor | Dashboard components (charts, metrics, cards) | [tremor.so](https://tremor.so) |
| Radix UI | Accessible headless components | [radix-ui.com](https://radix-ui.com) |
| @dnd-kit | Drag-and-drop for Kanban | [dndkit.com](https://dndkit.com) |

---

## 12. Summary: Total Story Count Across All Documents

| Document | Features | Stories | Phase |
|----------|----------|---------|-------|
| 01 — Planning Experience | 6 | 45 | Phase 2 |
| 02 — Pipeline Visualization | 6 | 51 | Phase 1 |
| 03 — Interactive Controls | 5 | 44 | Phase 3, 5 |
| 04 — GitHub Integration | 6 | 45 | Phase 4, 5 |
| 05 — Technology (this doc) | Infrastructure | (cross-cutting) | Phase 0-1 |
| **Total** | **23 features** | **~185 stories** | |

### Phase Ordering

```
Phase 0: Frontend scaffolding (Vite + React + Zustand + Tailwind + SSE infrastructure)
Phase 1: Pipeline Visibility (51 stories) — the foundation
Phase 2: Planning Experience (45 stories) — the differentiator
Phase 3: Interactive Controls (36 stories) — steering and governance
Phase 4: GitHub Integration (37 stories) — ecosystem connectivity
Phase 5: Analytics & Learning (16 stories) — long-term intelligence
```

Each phase produces a usable increment. Phase 1 alone gives the developer a visible pipeline. Phase 2 adds planning. Phase 3 adds control. Phases 4 and 5 deepen integration and intelligence.
