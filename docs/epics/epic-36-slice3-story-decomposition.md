# Epic 36 Slice 3: Complexity Dashboard + Expert Routing Preview -- Story Decomposition

> **Original Stories:** 36.13 (frontend, 8h, L), 36.14 (backend, 12h, L), 36.15 (frontend, 10h, L)
> **Decomposed into:** 10 right-sized sub-stories (36.13a-36.13c, 36.14a-36.14d, 36.15a-36.15c)
> **Rationale:** Stories 36.14 and 36.15 each span multiple concern boundaries (settings, Pydantic schema,
> Temporal signals, API endpoints, TypeScript types, store, display components, interactive components).
> Story 36.13 is pure frontend with no backend dependency but has four distinct components.
> Decomposing gives Ralph clear scope boundaries, one concern per loop, and testable increments.
> **Total estimated hours:** 30h (unchanged from original)
> **Created:** 2026-03-21

---

## Numbering Convention

Sub-stories use `36.13{letter}` for the complexity dashboard (original 36.13 scope),
`36.14{letter}` for the routing backend (original 36.14 scope), and `36.15{letter}` for
the routing frontend (original 36.15 scope). This preserves traceability to the epic's story map.

---

## Parallel Execution Tracks

Story 36.13 (complexity dashboard) has NO backend dependencies -- all data already exists on
`TaskPacketRead` fields (`complexity_index`, `risk_flags`, `scope`). These stories can execute
in parallel with the routing backend stories (36.14a-36.14d).

```
TRACK A (Complexity Dashboard)         TRACK B (Routing Backend)
------------------------------         -----------------------
36.13a MetricCard + RiskFlags          36.14a Settings + Pydantic schema
     |                                      |
36.13b FileHeatmap                     36.14b Temporal wait point + signals
     |                                      |
36.13c ComplexityDashboard container   36.14c API endpoints + planning.py
                                            |
                                       36.14d Routing API + store tests
                                            |
                              TRACK C (Routing Frontend)
                              -------------------------
                              36.15a Routing API client + store
                                   |
                              36.15b ExpertCard + RoutingPreview
                                   |
                              36.15c AddExpertDropdown + integration
```

---

## Story 36.13a: MetricCard and RiskFlags Display Components

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** None -- these are pure display components using existing `TaskPacketRead` fields.

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/MetricCard.tsx` | Create | Reusable metric card component |
| `frontend/src/components/planning/RiskFlags.tsx` | Create | Risk flags checklist component |

### Specific Implementation

**MetricCard.tsx** -- Generic metric display card:

Props:
```typescript
interface MetricCardProps {
  label: string           // e.g. "Files Affected", "Dependency Depth", "Test Gaps"
  value: string | number  // the metric value
  icon?: string           // optional emoji or text icon
  color?: 'green' | 'amber' | 'red' | 'gray'  // severity color
}
```

Layout:
- Container: `rounded-lg border border-gray-700 bg-gray-900 p-4`
- Icon/label row at top: `text-sm text-gray-400`
- Value below: `text-2xl font-bold` with color mapped to Tailwind:
  - `green` -> `text-emerald-400`
  - `amber` -> `text-amber-400`
  - `red` -> `text-red-400`
  - `gray` -> `text-gray-300` (default)

**RiskFlags.tsx** -- Checklist of risk flags:

Props:
```typescript
interface RiskFlagsProps {
  riskFlags: Record<string, boolean> | null  // from TaskPacketRead.risk_flags
}
```

Layout:
- Header: "Risk Flags" as `<h4 className="text-sm font-semibold text-gray-300 mb-2">`
- When `riskFlags` is null: show "Risk analysis: pending" in `text-gray-500 italic`
- When present: render each key-value pair as a row:
  - Key name formatted: strip `risk_` prefix, replace `_` with space, title case
    (e.g., `risk_security` -> "Security", `risk_cross_team` -> "Cross Team")
  - Value `true`: red circle icon + flag name in `text-red-400`
  - Value `false`: green checkmark + flag name in `text-emerald-400`
- Container: `rounded-lg border border-gray-700 bg-gray-900 p-4`

Known risk flag keys from `TaskPacketRead.risk_flags`:
- `risk_security`, `risk_breaking`, `risk_cross_team`, `risk_data`

Both components are pure display. No API calls. No store dependencies.

### Acceptance Criteria

- [ ] `MetricCard` renders label, value, and icon
- [ ] `MetricCard` applies correct color class per `color` prop
- [ ] `MetricCard` defaults to gray when no color is specified
- [ ] `RiskFlags` renders "Risk analysis: pending" when `riskFlags` is null
- [ ] `RiskFlags` renders each flag with correct icon (red for true, green for false)
- [ ] `RiskFlags` formats flag names correctly (strips `risk_` prefix, title case)
- [ ] Both components match dark theme (`bg-gray-900`, `border-gray-700`)
- [ ] `npm run typecheck` passes

---

## Story 36.13b: FileHeatmap Component

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** None -- pure display component.

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/FileHeatmap.tsx` | Create | File impact tree view with intensity bars |

### Specific Implementation

**FileHeatmap.tsx** -- Displays affected files from the Context stage scope data:

Props:
```typescript
interface FileHeatmapProps {
  scope: {
    affected_files_estimate?: number
    components?: string[]
    file_references?: string[]
  } | null
}
```

Layout:
- Container: `rounded-lg border border-gray-700 bg-gray-900 p-4`
- Header: "File Impact" as `<h4 className="text-sm font-semibold text-gray-300 mb-3">`
- When `scope` is null: show "Scope: pending" in `text-gray-500 italic`
- When present:
  - **Summary row:** "~{affected_files_estimate} files affected" as a summary badge
  - **Components list:** If `components` exists and is non-empty, render as a list of
    component names with folder icon prefix, each in `text-sm text-gray-300`
  - **File references:** If `file_references` exists and is non-empty, render as a flat list
    grouped by directory:
    - Extract directory from each file path (everything before last `/`)
    - Group files by directory
    - Render each directory as a collapsible section header (`text-gray-400 font-mono text-xs`)
    - Files under each directory: `text-gray-300 font-mono text-xs pl-4`
    - Intensity bar next to each directory: wider bar = more files in that directory
      (width = `(filesInDir / totalFiles) * 100%`, min 10%, `bg-amber-600/40`)
  - If both `components` and `file_references` are empty/null, show file count only

**Directory grouping helper** (pure function within the file):
```typescript
function groupByDirectory(files: string[]): Map<string, string[]>
```
- Split each path on `/`
- Group by `path.split('/').slice(0, -1).join('/')`
- Sort directories alphabetically

### Acceptance Criteria

- [ ] FileHeatmap renders "Scope: pending" when `scope` is null
- [ ] FileHeatmap shows file count estimate when `affected_files_estimate` exists
- [ ] FileHeatmap renders component list when `components` is non-empty
- [ ] FileHeatmap groups `file_references` by directory
- [ ] Each directory shows an intensity bar proportional to file count
- [ ] Directories are sorted alphabetically
- [ ] Empty `file_references` and `components` shows file count only
- [ ] Component matches dark theme
- [ ] `npm run typecheck` passes

---

## Story 36.13c: ComplexityDashboard Container and App Integration

**Size:** M (3 hours, 1 Ralph loop)
**Dependencies:** 36.13a (MetricCard, RiskFlags), 36.13b (FileHeatmap)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/ComplexityDashboard.tsx` | Create | Container assembling all complexity sub-components |

### Specific Implementation

**ComplexityDashboard.tsx** -- Renders full complexity dashboard from TaskPacket enrichment data:

Props:
```typescript
interface ComplexityDashboardProps {
  task: {
    complexity_index?: {
      score: number
      band: string  // "low", "medium", "high"
      dimensions: {
        scope_breadth: number
        risk_flag_count: number
        dependency_count: number
        lines_estimate: number
        expert_coverage: number
      }
    } | null
    risk_flags?: Record<string, boolean> | null
    scope?: {
      affected_files_estimate?: number
      components?: string[]
      file_references?: string[]
    } | null
  }
}
```

This is a display-only component that receives data via props. It does NOT fetch its own data.
The parent component (IntentEditor from Sprint 4, or any future container) passes the task data.

Layout:
- **Complexity Score Bar** (top section):
  - When `complexity_index` is null: "Complexity: pending" in `text-gray-500 italic`
  - When present:
    - Band label: `complexity_index.band` as uppercase badge
      - `low` -> `bg-emerald-900 text-emerald-300`
      - `medium` -> `bg-amber-900 text-amber-300`
      - `high` -> `bg-red-900 text-red-300`
    - Score bar: `<div>` with width = `(score / 100) * 100%` (capped at 100%), height 8px
      - Color same as band (emerald/amber/red gradient)
      - Background track: `bg-gray-800 rounded-full`
      - Fill: `rounded-full` with band color
    - Numeric score: `text-2xl font-bold` next to the bar

- **Metric Cards Row** (3-column grid, `grid grid-cols-3 gap-3`):
  - Card 1: "Files Affected" -- value from `scope?.affected_files_estimate ?? '--'`
    Color: `amber` if > 20, `green` if <= 20, `gray` if missing
  - Card 2: "Risk Flags" -- value = count of `true` values in `risk_flags`
    Color: `red` if > 0, `green` if 0, `gray` if missing
  - Card 3: "Expert Coverage" -- value from `complexity_index?.dimensions?.expert_coverage ?? '--'`
    Color: `green` if >= 2, `amber` if 1, `red` if 0, `gray` if missing
    (Note: `expert_coverage` is an integer count of required expert classes, not a 0-1 ratio)

- **Bottom Row** (2-column grid, `grid grid-cols-1 lg:grid-cols-2 gap-3`):
  - Left: `<FileHeatmap scope={task.scope} />`
  - Right: `<RiskFlags riskFlags={task.risk_flags} />`

### Acceptance Criteria

- [ ] ComplexityDashboard renders score bar with correct band color
- [ ] Score bar width is proportional to `complexity_index.score` (0-100)
- [ ] Band label renders as colored badge (green/amber/red)
- [ ] Three MetricCards render with correct labels and values
- [ ] MetricCards show '--' when data is missing
- [ ] MetricCards apply correct color thresholds (files > 20 = amber, risk > 0 = red)
- [ ] FileHeatmap and RiskFlags render in the bottom row
- [ ] All sections show "pending" state when enrichment data is null
- [ ] Component matches dark theme
- [ ] `npm run typecheck` passes

---

## Story 36.14a: Routing Review Setting and Pydantic Schema

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** None -- this is backend foundation.

### Deliverables

| File | Action | What |
|------|--------|------|
| `src/settings.py` | Modify | Add `routing_review_enabled: bool = False` |
| `src/routing/routing_result.py` | Create | Pydantic schema for API-serializable routing results |

### Specific Implementation

**src/settings.py** -- Add one setting after the existing `intent_review_enabled` line (line 105):

```python
routing_review_enabled: bool = False  # When True, workflow pauses after Router stage
```

**src/routing/routing_result.py** -- Pydantic models wrapping the Router's output for API consumption:

```python
"""API-serializable routing result models (Epic 36, Story 36.14).

Wraps the internal ConsultPlan and ExpertSelection dataclasses into
Pydantic models suitable for JSON serialization via FastAPI.
"""

from pydantic import BaseModel


class ExpertSelectionRead(BaseModel):
    """API representation of a single expert selection."""

    expert_id: str          # UUID as string
    expert_class: str       # ExpertClass enum value
    pattern: str            # "parallel" or "staged"
    reputation_weight: float
    reputation_confidence: float
    selection_score: float
    selection_reason: str   # "MANDATORY" or "AUTO"


class RoutingResultRead(BaseModel):
    """API representation of the Router's ConsultPlan."""

    selections: list[ExpertSelectionRead]
    recruiter_requests: list[dict[str, str]]  # Passthrough from ConsultPlan
    rationale: str
    budget_remaining: int
```

The `selection_reason` field ("MANDATORY" or "AUTO") is computed when building the response:
- If the expert's class is in `effective_role.mandatory_expert_classes`, it is "MANDATORY"
- Otherwise, it is "AUTO"
- For MVP, all selections default to "AUTO" since the mandatory classification is not
  currently persisted. A future enhancement can add MANDATORY detection.

**IMPORTANT: Wire format gap.** The existing `RouterOutput` dataclass in
`src/workflow/activities.py` (line 125) stores `selections` as
`list[dict[str, str]]` with only 3 keys: `expert_class`, `pattern`, `rationale`.
But `ExpertSelectionRead` has 7 fields including `expert_id`, `reputation_weight`,
`reputation_confidence`, and `selection_score` — these exist on the internal
`ExpertSelection` dataclass in `src/routing/router.py` but are discarded during
serialization to `RouterOutput`.

**Resolution:** Story 36.14c must update `router_activity()` to persist the full
`ConsultPlan` data (not the reduced `RouterOutput`) as a `routing_result` JSONB
column on the TaskPacket. The serialization should use:
```python
routing_result = {
    "selections": [
        {
            "expert_id": str(sel.expert_id),
            "expert_class": sel.expert_class.value,
            "pattern": sel.pattern,
            "reputation_weight": sel.reputation_weight,
            "reputation_confidence": sel.reputation_confidence,
            "selection_score": sel.selection_score,
            "selection_reason": "AUTO",  # MVP default
        }
        for sel in consult_plan.selections
    ],
    "recruiter_requests": [...],
    "rationale": consult_plan.rationale,
    "budget_remaining": consult_plan.budget_remaining,
}
```
This requires accessing the `ConsultPlan` object (not `RouterOutput`) within
`router_activity()` and persisting it via a DB session write.

### Acceptance Criteria

- [ ] `routing_review_enabled` setting exists with default `False`
- [ ] Setting is loadable via `THESTUDIO_ROUTING_REVIEW_ENABLED` env var
- [ ] `ExpertSelectionRead` Pydantic model has all 7 fields
- [ ] `RoutingResultRead` Pydantic model has `selections`, `recruiter_requests`, `rationale`, `budget_remaining`
- [ ] Both models serialize to valid JSON
- [ ] `ruff check src/settings.py src/routing/routing_result.py` passes
- [ ] `mypy src/routing/routing_result.py` passes
- [ ] Unit test: `RoutingResultRead` round-trips through `.model_dump()` and `.model_validate()`

---

## Story 36.14b: Temporal Wait Point After Router Stage

**Size:** M (4 hours, 1 Ralph loop)
**Dependencies:** 36.14a (needs `routing_review_enabled` setting)

### Deliverables

| File | Action | What |
|------|--------|------|
| `src/workflow/pipeline.py` | Modify | Add routing wait point, signal handlers, timeout |

### Specific Implementation

**Signal handlers** -- Add two new signals to `TheStudioPipelineWorkflow` (after the existing
`readiness_cleared` signal at line 309):

```python
# Routing review state (initialized in __init__)
self._routing_approved = False
self._routing_approved_by: str | None = None
self._routing_overridden = False
self._routing_override_data: dict | None = None

@workflow.signal
async def approve_routing(self, approved_by: str) -> None:
    """Signal handler -- developer approves expert routing as-is."""
    self._routing_approved = True
    self._routing_approved_by = approved_by

@workflow.signal
async def override_routing(self, approved_by: str, override_data: dict) -> None:
    """Signal handler -- developer approves routing with modifications."""
    self._routing_approved = True
    self._routing_overridden = True
    self._routing_approved_by = approved_by
    self._routing_override_data = override_data
```

**Workflow step enum** -- Add to `WorkflowStep`:
```python
AWAITING_ROUTING_REVIEW = "awaiting_routing_review"
```

**Step policy** -- Add to `STEP_POLICIES`:
```python
WorkflowStep.AWAITING_ROUTING_REVIEW: StepPolicy(
    timeout=timedelta(days=30), max_retries=0,  # safety timeout, not auto-approve
),
```

**Timeout constant** -- Add after `INTENT_REVIEW_TIMEOUT`:
```python
ROUTING_REVIEW_TIMEOUT = timedelta(days=30)
```

**Wait point in `run()`** -- Insert after Step 4 (Router) at line 518, before Step 5 (Assembler):

```python
# Step 4.5: Routing Review (feature-flagged)
if params.routing_review_enabled:
    output.step_reached = WorkflowStep.AWAITING_ROUTING_REVIEW

    try:
        await workflow.wait_condition(
            lambda: self._routing_approved,
            timeout=ROUTING_REVIEW_TIMEOUT,
        )
    except TimeoutError:
        workflow.logger.warning(
            "routing_review.timeout",
            extra={"taskpacket_id": params.taskpacket_id},
        )
        output.rejection_reason = "routing_review_timeout"
        return output

    # Record routing review outcome
    output.routing_approved_by = self._routing_approved_by
```

**PipelineInput** -- Add field:
```python
routing_review_enabled: bool = False
```

**PipelineOutput** -- Add field:
```python
routing_approved_by: str | None = None
```

**Pattern reference:** This exactly mirrors the existing intent review wait point at lines 477-503.

### Acceptance Criteria

- [ ] `approve_routing` signal handler exists on `TheStudioPipelineWorkflow`
- [ ] `override_routing` signal handler exists and sets override data
- [ ] `AWAITING_ROUTING_REVIEW` added to `WorkflowStep` enum
- [ ] Step policy added for `AWAITING_ROUTING_REVIEW` (30-day timeout, 0 retries)
- [ ] Wait point inserted after Router activity, before Assembler
- [ ] Wait point is gated by `params.routing_review_enabled`
- [ ] When `routing_review_enabled=False`, workflow skips wait (backward compatible)
- [ ] Timeout after 30 days returns failure (does NOT auto-approve)
- [ ] `approve_routing` signal resumes workflow into Assembler
- [ ] `PipelineInput.routing_review_enabled` field added with default `False`
- [ ] `PipelineOutput.routing_approved_by` field added
- [ ] `ruff check src/workflow/pipeline.py` passes
- [ ] Unit test: workflow proceeds without wait when flag is False
- [ ] Unit test: workflow pauses and resumes on `approve_routing` signal
- [ ] Unit test: workflow times out and returns failure after timeout

---

## Story 36.14c: Routing Review API Endpoints

**Size:** M (4 hours, 1 Ralph loop)
**Dependencies:** 36.14a (Pydantic schema), 36.14b (Temporal signals)

### Deliverables

| File | Action | What |
|------|--------|------|
| `src/dashboard/planning.py` | Modify | Add routing review endpoints |
| `src/workflow/activities.py` | Modify | Add DB persist of full ConsultPlan data in `router_activity()` |
| `src/models/taskpacket.py` | Modify | Add `routing_result: Mapped[dict | None]` JSONB column to `TaskPacketRow` and `TaskPacketRead` |
| `src/db/migrations/NNN_add_routing_result.py` | Create | Alembic migration adding `routing_result` nullable JSONB column |

### Specific Implementation

**Database changes:**
- Add `routing_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)` to `TaskPacketRow`
- Add `routing_result: dict[str, Any] | None = None` to `TaskPacketRead`
- Create Alembic migration: `ALTER TABLE taskpacket ADD COLUMN routing_result JSONB`

**Persist routing result in `router_activity()`:**
- Import `get_async_session` (following the pattern in `intent_activity()` at activities.py lines 527-551)
- After computing the `ConsultPlan`, serialize the full selection data (including `expert_id`, `reputation_weight`, `reputation_confidence`, `selection_score` from each `ExpertSelection`)
- Write to `TaskPacketRow.routing_result` via async session
- Wrap in try/except so persistence failure does not block the workflow

Add the following endpoints to `src/dashboard/planning.py` after the existing intent endpoints
(after line 345):

**Request/Response models** (add after existing `IntentActionResponse` at line 104):

```python
class RoutingApproveResponse(BaseModel):
    """Response after approving routing."""
    status: str

class RoutingOverrideRequest(BaseModel):
    """Request body for overriding routing selections."""
    add_experts: list[str] = []      # expert_class values to add
    remove_experts: list[str] = []   # expert_class values to remove (AUTO only)

class RoutingOverrideResponse(BaseModel):
    """Response after overriding routing."""
    status: str
```

**Helper** -- Add after existing helpers:

```python
async def _get_routed_task(
    session: AsyncSession, task_id: UUID,
) -> TaskPacketRead:
    """Fetch a TaskPacket and verify it is in a routing-reviewable state."""
    task = await _get_task(session, task_id)
    # Task should be past the Router stage. For MVP, check that it has
    # routing data stored. The Temporal workflow is in AWAITING_ROUTING_REVIEW.
    # We check status is IN_PROGRESS or a new AWAITING_ROUTING status.
    # For now, any non-terminal task past INTENT_BUILT is acceptable.
    if task.status in (
        TaskPacketStatus.TRIAGE,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.FAILED,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"TaskPacket is in {task.status.value} status, not reviewable",
        )
    return task
```

**Endpoints:**

1. `GET /tasks/{task_id}/routing` -- Returns routing result from TaskPacket:

```python
@router.get("/tasks/{task_id}/routing")
async def get_routing(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> RoutingResultRead:
    """Get the routing result (expert selections) for a task."""
    task = await _get_task(session, task_id)

    # Routing data is stored on the TaskPacket after the Router activity runs.
    # The router_activity stores selections in the Temporal workflow output.
    # For dashboard access, we need to retrieve from the TaskPacket or query
    # the workflow. For MVP, store routing result on TaskPacket as JSONB.
    from src.models.taskpacket import TaskPacketRow
    row = await session.get(TaskPacketRow, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TaskPacket not found")

    routing_data = getattr(row, 'routing_result', None)
    if routing_data is None:
        raise HTTPException(status_code=404, detail="No routing result for this task")

    from src.routing.routing_result import RoutingResultRead
    return RoutingResultRead.model_validate(routing_data)
```

2. `POST /tasks/{task_id}/routing/approve` -- Sends approve signal:

```python
@router.post("/tasks/{task_id}/routing/approve")
async def approve_routing(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> RoutingApproveResponse:
    """Approve routing -- sends approve_routing signal to Temporal."""
    await _get_routed_task(session, task_id)

    from src.ingress.workflow_trigger import get_temporal_client
    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal("approve_routing", args=["dashboard_user"])

    return RoutingApproveResponse(status="approved")
```

3. `POST /tasks/{task_id}/routing/override` -- Sends override signal:

```python
@router.post("/tasks/{task_id}/routing/override")
async def override_routing(
    task_id: UUID,
    body: RoutingOverrideRequest,
    session: AsyncSession = Depends(get_session),
) -> RoutingOverrideResponse:
    """Override routing -- sends override_routing signal with modifications."""
    await _get_routed_task(session, task_id)

    from src.ingress.workflow_trigger import get_temporal_client
    client = await get_temporal_client()
    handle = client.get_workflow_handle(str(task_id))
    await handle.signal(
        "override_routing",
        args=["dashboard_user", body.model_dump()],
    )

    return RoutingOverrideResponse(status="overridden")
```

**TaskPacket routing_result storage** -- The Router activity must persist its output to
the TaskPacket so the dashboard API can read it. This requires:
- Adding `routing_result: Mapped[dict | None]` as a nullable JSONB column to `TaskPacketRow`
- Adding `routing_result` to `TaskPacketRead` Pydantic model
- Updating `router_activity()` in `activities.py` to persist the result after routing

These changes are part of this story's scope since the API endpoint cannot function without them.

### Acceptance Criteria

- [ ] `GET /tasks/{id}/routing` returns `RoutingResultRead` with selections, rationale, budget
- [ ] `GET /tasks/{id}/routing` returns 404 when no routing result exists
- [ ] `POST /tasks/{id}/routing/approve` sends `approve_routing` signal to Temporal
- [ ] `POST /tasks/{id}/routing/approve` returns 409 for terminal-status tasks
- [ ] `POST /tasks/{id}/routing/override` sends `override_routing` signal with add/remove data
- [ ] `RoutingOverrideRequest` accepts `add_experts` and `remove_experts` lists
- [ ] `routing_result` JSONB column added to `TaskPacketRow`
- [ ] `routing_result` field added to `TaskPacketRead`
- [ ] Router activity persists result to TaskPacket after routing
- [ ] `ruff check src/dashboard/planning.py` passes
- [ ] API tests for all three endpoints

---

## Story 36.14d: Routing Backend Tests

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** 36.14a, 36.14b, 36.14c (needs all backend pieces in place)

### Deliverables

| File | Action | What |
|------|--------|------|
| `tests/test_routing_result.py` | Create | Unit tests for Pydantic schema |
| `tests/test_routing_endpoints.py` | Create | API tests for routing endpoints |

### Specific Implementation

**test_routing_result.py:**

1. `ExpertSelectionRead` round-trips through `.model_dump()` and `.model_validate()`
2. `RoutingResultRead` with empty selections is valid
3. `RoutingResultRead` with multiple selections serializes correctly
4. All fields have correct types after deserialization

**test_routing_endpoints.py** (follow `tests/test_planning_endpoints.py` pattern):

1. `GET /routing` returns 404 when no routing data exists
2. `GET /routing` returns valid `RoutingResultRead` when data exists
3. `POST /routing/approve` returns 200 with `{"status": "approved"}`
4. `POST /routing/approve` returns 409 for REJECTED task
5. `POST /routing/override` returns 200 with valid override body
6. `POST /routing/override` accepts empty add/remove lists

### Acceptance Criteria

- [ ] All Pydantic schema tests pass
- [ ] All API endpoint tests pass
- [ ] Tests mock Temporal client (no real workflow)
- [ ] Tests use async test client (`httpx.AsyncClient`)
- [ ] `pytest tests/test_routing_result.py tests/test_routing_endpoints.py` passes
- [ ] No test depends on real database (use fixtures)

---

## Story 36.15a: Routing API Client Functions and Zustand Store

**Size:** S (3 hours, 1 Ralph loop)
**Dependencies:** 36.14c (routing API endpoints must exist)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/lib/api.ts` | Modify | Add routing types and API functions |
| `frontend/src/stores/routing-store.ts` | Create | Zustand store for routing review state |

### Specific Implementation

**api.ts** -- Add after the existing intent API section (or the triage section):

Types:
```typescript
export interface ExpertSelectionRead {
  expert_id: string
  expert_class: string
  pattern: string
  reputation_weight: number
  reputation_confidence: number
  selection_score: number
  selection_reason: string  // "MANDATORY" or "AUTO"
}

export interface RoutingResultRead {
  selections: ExpertSelectionRead[]
  recruiter_requests: { expert_class: string; capability_tags: string[]; reason: string }[]
  rationale: string
  budget_remaining: number
}
```

API functions (follow existing `fetchIntent`/`approveIntent` patterns):
```typescript
export async function fetchRouting(taskId: string): Promise<RoutingResultRead>
  // GET ${API_BASE}/tasks/${taskId}/routing

export async function approveRouting(taskId: string): Promise<{ status: string }>
  // POST .../routing/approve

export async function overrideRouting(taskId: string, overrides: {
  add_experts: string[]
  remove_experts: string[]
}): Promise<{ status: string }>
  // POST .../routing/override with JSON body
```

All functions use `withToken()`. POST functions include `Content-Type: application/json`.

**routing-store.ts** -- Follow `triage-store.ts` pattern:

State interface (`RoutingState`):
- `taskId: string | null`
- `result: RoutingResultRead | null`
- `loading: boolean`
- `error: string | null`
- `saving: boolean`  -- true during approve/override

Actions interface (`RoutingActions`):
- `loadRouting(taskId: string): Promise<void>` -- calls `fetchRouting`, sets `result`
- `approve(): Promise<void>` -- calls `approveRouting(taskId!)`
- `override(overrides: { add_experts: string[]; remove_experts: string[] }): Promise<void>` -- calls `overrideRouting`
- `reset(): void` -- clears all state

Error handling: same catch pattern as triage-store.

### Acceptance Criteria

- [ ] `ExpertSelectionRead` and `RoutingResultRead` interfaces exported from `api.ts`
- [ ] `fetchRouting`, `approveRouting`, `overrideRouting` exported from `api.ts`
- [ ] All API functions follow existing error-handling pattern (`if (!res.ok) throw`)
- [ ] `useRoutingStore` exported from `routing-store.ts`
- [ ] `loadRouting` fetches and populates `result`
- [ ] `approve` calls API and sets `saving` flag
- [ ] `override` calls API with correct body shape
- [ ] Error states set `error` string
- [ ] `npm run typecheck` passes
- [ ] No changes to existing API functions

---

## Story 36.15b: ExpertCard and RoutingPreview Display Components

**Size:** M (3 hours, 1 Ralph loop)
**Dependencies:** 36.15a (needs `ExpertSelectionRead` type and store)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/ExpertCard.tsx` | Create | Individual expert selection card |
| `frontend/src/components/planning/RoutingPreview.tsx` | Create | Container for expert list + approve button |

### Specific Implementation

**ExpertCard.tsx** -- Displays one expert selection:

Props:
```typescript
interface ExpertCardProps {
  selection: ExpertSelectionRead
  onRemove?: () => void  // only provided for AUTO experts
}
```

Layout:
- Container: `rounded-lg border border-gray-700 bg-gray-900 p-4`
- **Header row:**
  - Expert class as badge: `bg-blue-900 text-blue-300 text-xs px-2 py-0.5 rounded`
  - Selection reason badge:
    - "MANDATORY": `bg-gray-700 text-gray-300` with lock icon (unicode `U+1F512` or text "[M]")
    - "AUTO": `bg-gray-800 text-gray-400`
- **Pattern:** "Pattern: {selection.pattern}" in `text-sm text-gray-400`
- **Reputation row:**
  - "Weight: {reputation_weight.toFixed(2)}" with color:
    - >= 0.7: `text-emerald-400`
    - >= 0.4: `text-amber-400`
    - < 0.4: `text-red-400`
  - "Confidence: {reputation_confidence.toFixed(2)}" in `text-gray-400`
- **Score:** "Score: {selection_score.toFixed(2)}" as `text-sm font-semibold text-gray-200`
- **Remove button:** Only visible when `onRemove` is provided (i.e., AUTO experts)
  - "Remove" button: `text-red-400 hover:text-red-300 text-xs` at bottom right
  - Click calls `onRemove()`
- **Lock icon for MANDATORY:** When `selection_reason === "MANDATORY"`, render a lock icon
  next to the expert class name. No remove button.

**RoutingPreview.tsx** -- Container orchestrating routing review:

Props: `{ taskId: string; onClose?: () => void }`

On mount:
- Calls `useRoutingStore().loadRouting(taskId)`
- Reads `result`, `loading`, `error`, `saving` from store

Layout:
- **Header:** "Expert Routing Review" with task ID badge, optional close button
- **Rationale section:** Renders `result.rationale` in `text-sm text-gray-400 italic` block
- **Expert cards grid:** `grid grid-cols-1 md:grid-cols-2 gap-3`
  - One `<ExpertCard>` per selection in `result.selections`
  - AUTO experts get an `onRemove` callback that calls `store.override({ add_experts: [], remove_experts: [selection.expert_class] })`
- **Budget remaining:** "Budget: {result.budget_remaining} expert slots remaining" badge
- **Recruiter requests:** If `result.recruiter_requests` is non-empty, render as a warning
  section: "Expert Gaps" with list of missing classes
- **Action bar** (bottom):
  - "Approve Routing" button: `bg-emerald-700 text-white`, disabled when `saving`
    Calls `store.approve()`
  - "Add Expert" button (placeholder for 36.15c): `border-blue-700 text-blue-400`
- **Loading state:** Spinner
- **Error state:** Error banner with retry

### Acceptance Criteria

- [ ] ExpertCard renders expert class, pattern, reputation, and score
- [ ] ExpertCard shows lock icon for MANDATORY experts
- [ ] ExpertCard shows remove button only for AUTO experts
- [ ] RoutingPreview loads routing data on mount
- [ ] RoutingPreview renders all expert cards in a grid
- [ ] RoutingPreview shows rationale text
- [ ] RoutingPreview shows budget remaining
- [ ] RoutingPreview shows recruiter request warnings when present
- [ ] Approve button calls `store.approve()` and disables during save
- [ ] Loading and error states render correctly
- [ ] All components match dark theme
- [ ] `npm run typecheck` passes

---

## Story 36.15c: AddExpertDropdown, Integration, and Component Tests

**Size:** M (3 hours, 1 Ralph loop)
**Dependencies:** 36.15b (needs RoutingPreview and ExpertCard)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/AddExpertDropdown.tsx` | Create | Dropdown to add available experts |
| `frontend/src/components/planning/RoutingPreview.tsx` | Modify | Wire AddExpertDropdown into action bar |
| `frontend/src/components/planning/__tests__/RoutingPreview.test.tsx` | Create | Component tests |

### Specific Implementation

**AddExpertDropdown.tsx:**

Props:
```typescript
interface AddExpertDropdownProps {
  selectedClasses: string[]   // expert classes already selected
  onAdd: (expertClass: string) => void
  disabled?: boolean
}
```

Available expert classes (from `ExpertClass` enum in `src/experts/expert.py`):
```typescript
const ALL_EXPERT_CLASSES = [
  'technical', 'business', 'partner', 'qa_validation',
  'security', 'compliance', 'service', 'process_quality',
]
```

Layout:
- `<select>` dropdown styled with dark theme: `bg-gray-800 border-gray-700 text-gray-200`
- Default option: "Add Expert..." (disabled, selected)
- Options: `ALL_EXPERT_CLASSES` filtered to exclude `selectedClasses`
- `onChange` calls `onAdd(selectedValue)` and resets dropdown to default
- When no classes are available (all selected), dropdown is disabled with "All experts assigned"

**RoutingPreview.tsx modification:**

Replace the placeholder "Add Expert" button with:
```tsx
<AddExpertDropdown
  selectedClasses={result.selections.map((s) => s.expert_class)}
  onAdd={(cls) => void store.override({
    add_experts: [cls],
    remove_experts: [],
  })}
  disabled={saving}
/>
```

After a successful override (add or remove), re-load routing data:
- In the store, after `override()` succeeds, call `loadRouting(taskId)` to refresh

**Component Tests** (`RoutingPreview.test.tsx`):

Follow the `TriageQueue.test.tsx` pattern:
- Mock `../../lib/api` with `vi.mock`
- Mock `fetchRouting`, `approveRouting`, `overrideRouting`
- Create `mockRoutingResult` and `mockExpertSelection` factory functions

Test cases:
1. **Loading state:** Shows spinner when loading
2. **Expert cards render:** All selections appear as ExpertCard components
3. **MANDATORY lock:** MANDATORY experts show lock indicator, no remove button
4. **AUTO remove:** AUTO experts show remove button, clicking calls override
5. **Approve button:** Calls `approveRouting` API
6. **Approve disabled during save:** Button disabled when `saving` is true
7. **Rationale display:** Rationale text renders in italic block
8. **Budget remaining:** Shows correct budget count
9. **Recruiter gaps:** Warning section appears when `recruiter_requests` is non-empty
10. **Add expert dropdown:** Shows available classes (excludes already selected)
11. **Add expert action:** Selecting from dropdown calls override with add_experts
12. **Error state:** Error message renders with retry option
13. **Empty selections:** Renders gracefully with "No experts selected" message

### Acceptance Criteria

- [ ] AddExpertDropdown renders available expert classes (excludes selected)
- [ ] Selecting a class calls `onAdd` with the class value
- [ ] Dropdown disabled when all classes are assigned
- [ ] RoutingPreview wires AddExpertDropdown to store override action
- [ ] After override, routing data re-loads from API
- [ ] All 13 test cases pass
- [ ] Tests mock API functions (no real HTTP calls)
- [ ] `npm test` passes with no failures
- [ ] `npm run typecheck` passes

---

## Dependency Graph

```
TRACK A (parallel)                    TRACK B (serial)
==================                    ================

36.13a (MetricCard + RiskFlags)       36.14a (Settings + Pydantic schema)
     |                                     |
36.13b (FileHeatmap)                  36.14b (Temporal wait point)
     |                                     |
36.13c (ComplexityDashboard)          36.14c (API endpoints)
                                           |
                                      36.14d (Backend tests)
                                           |
                                      36.15a (API client + store)
                                           |
                                      36.15b (ExpertCard + RoutingPreview)
                                           |
                                      36.15c (AddExpert + integration tests)
```

**Track A critical path:** 36.13a -> 36.13b -> 36.13c (3 stories, 7 hours)
**Track B critical path:** 36.14a -> 36.14b -> 36.14c -> 36.14d -> 36.15a -> 36.15b -> 36.15c (7 stories, 21 hours)

**Parallelizable pairs:**
- 36.13a can run in parallel with 36.14a
- 36.13b can run in parallel with 36.14b
- 36.13c can run in parallel with 36.14c or 36.14d

---

## Capacity Summary

| Story | Title | Size | Est. Hours | Ralph Loops | Track |
|-------|-------|------|-----------|-------------|-------|
| 36.13a | MetricCard + RiskFlags | S | 2.0 | 1 | A |
| 36.13b | FileHeatmap | S | 2.0 | 1 | A |
| 36.13c | ComplexityDashboard Container | M | 3.0 | 1 | A |
| 36.14a | Settings + Pydantic Schema | S | 2.0 | 1 | B |
| 36.14b | Temporal Wait Point | M | 4.0 | 1 | B |
| 36.14c | Routing API Endpoints | M | 4.0 | 1 | B |
| 36.14d | Routing Backend Tests | S | 2.0 | 1 | B |
| 36.15a | Routing API Client + Store | S | 3.0 | 1 | B |
| 36.15b | ExpertCard + RoutingPreview | M | 3.0 | 1 | B |
| 36.15c | AddExpert + Integration Tests | M | 3.0 | 1 | B |
| **Total** | | | **28.0** | **10** | |
| **Buffer** | | | **7.0** | | |

**Allocation:** 28 of 35 hours = 80% with 20% buffer.

---

## Compressibility (Ordered)

1. **36.15c AddExpertDropdown + integration tests** -- first to defer. The approve-as-is flow
   (36.15b) still works. The developer can approve routing without adding experts. Tests for
   36.15a-36.15b can be written inline with each story.
   **Impact:** No add-expert UI. Override requires API call or re-triggering.

2. **36.14d Routing backend tests** -- second to defer. Core functionality is in 36.14a-36.14c.
   Tests can be caught up later or written inline.
   **Impact:** No dedicated test coverage for routing endpoints (risky but recoverable).

3. **36.13b FileHeatmap** -- third to defer. The ComplexityDashboard (36.13c) can render
   MetricCards and RiskFlags without the heatmap. File list can be shown as a simple count.
   **Impact:** No visual file impact breakdown. Score bar and risk flags still render.

4. **36.13c ComplexityDashboard container** -- fourth to defer (most aggressive compression).
   MetricCard and RiskFlags (36.13a) can be used standalone in the IntentEditor's SourceContext
   panel without a dedicated dashboard container.
   **Impact:** No dedicated complexity view. Components still usable inline.

---

## Relationship to Original Stories

| Original Story | Decomposed Into | Scope |
|---------------|-----------------|-------|
| 36.13 (8h, L) | 36.13a + 36.13b + 36.13c | MetricCard, RiskFlags, FileHeatmap, ComplexityDashboard container |
| 36.14 (12h, L) | 36.14a + 36.14b + 36.14c + 36.14d | Settings, Pydantic schema, Temporal wait point, API endpoints, routing storage, tests |
| 36.15 (10h, L) | 36.15a + 36.15b + 36.15c | API client, Zustand store, ExpertCard, RoutingPreview, AddExpertDropdown, integration tests |

---

## Notes for Ralph Execution

1. **No new TaskPacket status needed for routing review.** Unlike the intent wait point
   (which uses `INTENT_BUILT` status), the routing review wait happens within the Temporal
   workflow without a dedicated TaskPacket status. The workflow step enum
   `AWAITING_ROUTING_REVIEW` provides observability. If a status is later needed, it can
   be added without breaking this decomposition.

2. **Routing result storage.** The `RouterOutput` from the Temporal activity must be persisted
   to the TaskPacket so the dashboard API can read it without querying Temporal history.
   Story 36.14c handles this by adding a `routing_result` JSONB column to `TaskPacketRow`.
   The `router_activity()` in `activities.py` must be updated to persist this.

3. **ExpertClass enum values.** The frontend hardcodes `ALL_EXPERT_CLASSES` in 36.15c.
   These values come from `src/experts/expert.py` (`ExpertClass` enum): `technical`,
   `business`, `partner`, `qa_validation`, `security`, `compliance`, `service`,
   `process_quality`. If the enum changes, the frontend constant must be updated.

4. **Dark theme constants.** Same as Sprint 4: `bg-gray-900`, `bg-gray-950`, `text-gray-100`,
   `text-gray-400`, `border-gray-700`, `border-gray-800`. Button colors follow existing patterns.

5. **Test pattern.** Backend tests follow `tests/test_planning_endpoints.py`. Frontend tests
   follow `TriageQueue.test.tsx`: `vi.mock('../../lib/api')`, factory functions, render + screen
   assertions.

6. **Complexity dashboard is pure frontend.** All data exists on `TaskPacketRead` fields
   (`complexity_index`, `risk_flags`, `scope`). The `TaskPacketRead` interface in `api.ts`
   was extended in Sprint 4 (Story 36.11a) with these optional fields. No new API endpoint
   is needed.

7. **AC 9 scope reduction.** Epic AC 9 specifies the routing API returns "role name, mandate,
   assigned files, selection reason, and reputation weight." However, `mandate` and
   `assigned_files` do not exist in the current router data model (`ExpertSelection`,
   `RouterOutput`, `ConsultPlan`). They are deferred to a future enhancement. The MVP
   routing preview shows `expert_class`, `pattern`, reputation data, and `selection_score`.

8. **Override flow for routing.** The override endpoint sends a Temporal signal with the
   add/remove expert classes. The Temporal workflow receives this via `override_routing`
   signal but does NOT re-run the router activity in this MVP. The override data is logged
   and the workflow proceeds to Assembler. A future epic can implement re-routing based
   on override data.

---

## Meridian Review: PASS (2026-03-21)

**Reviewer:** Meridian (VP of Success)
**Initial Verdict:** CONDITIONAL PASS -- 4 blockers, 1 recommendation.
**Final Verdict:** PASS -- all issues fixed.

### Blockers Found and Fixed

**Blocker 1: `RouterOutput` wire format mismatch.** The `RouterOutput` discards 4 of 7 fields needed by `ExpertSelectionRead`. **Fixed:** Story 36.14c now specifies persisting full `ConsultPlan` data (not reduced `RouterOutput`) with all `ExpertSelection` fields serialized to the `routing_result` JSONB column.

**Blocker 2: `router_activity()` has no DB access.** Adding persistence requires importing `get_async_session` and adding a try/except block. **Fixed:** Story 36.14c implementation section now specifies DB session handling following the `intent_activity()` pattern.

**Blocker 3: Missing Alembic migration.** Adding `routing_result` column requires a migration file. **Fixed:** Added `src/db/migrations/NNN_add_routing_result.py` to deliverables and `src/models/taskpacket.py` modification.

**Blocker 4: `expert_coverage` color thresholds nonsensical.** Used float thresholds (0.8, 0.5) on integer data (expert class count). **Fixed:** Changed to integer thresholds (green >= 2, amber = 1, red = 0).

**Recommendation: AC 9 scope reduction undocumented.** `mandate` and `assigned_files` from AC 9 don't exist in router data model. **Fixed:** Added Note 7 documenting the deferral.

### 7 Questions

| # | Question | Verdict |
|---|----------|---------|
| 1 | Goal testable? | PASS |
| 2 | ACs testable? | PASS (after fix) |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified? | PASS |
| 5 | Metrics measurable? | PASS (deferred to epic) |
| 6 | AI agent can implement? | PASS (after fixes) |
| 7 | Narrative compelling? | PASS |

### Source Code Verification

All 10 claims verified against live source code. No false assumptions found.

---
