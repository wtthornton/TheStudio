# Epic 36 Sprint 4: Intent Editor Frontend -- Story Decomposition

> **Original Stories:** 36.11 (12h, L) and 36.12 (10h, L)
> **Decomposed into:** 7 right-sized sub-stories (36.11a through 36.11g)
> **Rationale:** The original two L-sized stories each span 2-3 Ralph loops with multiple
> concern boundaries (types, store, layout, display components, interactive components, tests).
> Decomposing into single-loop stories gives Ralph clear scope boundaries, reduces context
> requirements per loop, and produces testable increments at each step.
> **Total estimated hours:** 22h (unchanged from original)
> **Created:** 2026-03-21

---

## Numbering Convention

All sub-stories use `36.11{letter}` numbering. Stories 36.11a-36.11d correspond to the
original 36.11 scope (read-only view). Stories 36.11e-36.11g correspond to the original
36.12 scope (edit, refinement, diff). This keeps the epic's story count clean while
preserving traceability back to the original definitions.

---

## Story 36.11a: Intent API Client Functions and TypeScript Types

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** None -- this is the foundation layer.

### Deliverables

Files to create or modify:

| File | Action | What |
|------|--------|------|
| `frontend/src/lib/api.ts` | Modify | Add `IntentSpecRead` interface and 5 intent API functions |

### Specific Implementation

Add to `frontend/src/lib/api.ts` (after the existing Triage API section):

0. **Extend existing `TaskPacketRead` interface** with fields the backend already returns but the frontend type omits:
   - `issue_title?: string | null`
   - `issue_body?: string | null`
   - `scope?: Record<string, unknown> | null`
   - `risk_flags?: Record<string, boolean> | null`
   - `complexity_index?: Record<string, unknown> | null`

   These fields are on the Python `TaskPacketRead` Pydantic model (lines 189-204 of `src/models/taskpacket.py`) and are returned by `GET /tasks/{id}`. The frontend type was under-specified. All fields are optional (`?`) so no existing code breaks.

1. **TypeScript interface** `IntentSpecRead`:
   - `id: string` (UUID as string, matching existing `TaskPacketRead` convention)
   - `taskpacket_id: string`
   - `version: number`
   - `goal: string`
   - `constraints: string[]`
   - `acceptance_criteria: string[]`
   - `non_goals: string[]`
   - `source: 'auto' | 'developer' | 'refinement'`
   - `created_at: string` (ISO datetime as string, matching existing convention)

2. **Response interface** `IntentResponse`:
   - `current: IntentSpecRead`
   - `versions: IntentSpecRead[]`

3. **API functions** (follow existing `fetchTriageTasks`/`acceptTriageTask` patterns exactly):
   - `fetchIntent(taskId: string): Promise<IntentResponse>` -- `GET ${API_BASE}/tasks/${taskId}/intent`
   - `approveIntent(taskId: string): Promise<{ status: string }>` -- `POST .../intent/approve`
   - `rejectIntent(taskId: string, reason: string): Promise<{ status: string }>` -- `POST .../intent/reject` with `{ reason }` body
   - `editIntent(taskId: string, spec: { goal: string; constraints: string[]; acceptance_criteria: string[]; non_goals: string[] }): Promise<IntentSpecRead>` -- `PUT .../intent` with body
   - `refineIntent(taskId: string, feedback: string): Promise<IntentSpecRead>` -- `POST .../intent/refine` with `{ feedback }` body

All functions use `withToken()` for auth. POST/PUT/PATCH functions include `Content-Type: application/json` header and `JSON.stringify` body (matching `rejectTriageTask` and `editTriageTask` patterns).

### Acceptance Criteria

- [ ] `TaskPacketRead` interface extended with `issue_title`, `issue_body`, `scope`, `risk_flags`, `complexity_index` (all optional)
- [ ] `IntentSpecRead` interface exported from `api.ts` with all 9 fields
- [ ] `IntentResponse` interface exported with `current` and `versions` fields
- [ ] All 5 API functions exported and follow existing error-handling pattern (`if (!res.ok) throw new Error(...)`)
- [ ] `npm run typecheck` passes with no new errors
- [ ] No changes to any existing API functions

---

## Story 36.11b: Intent Zustand Store

**Size:** S (2 hours, 1 Ralph loop)
**Dependencies:** 36.11a (needs `IntentSpecRead`, `IntentResponse`, and API functions)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/stores/intent-store.ts` | Create | Zustand store for intent state and actions |

### Specific Implementation

Create `frontend/src/stores/intent-store.ts` following the `triage-store.ts` pattern exactly:

**State interface** (`IntentState`):
- `taskId: string | null` -- currently loaded task
- `current: IntentSpecRead | null` -- the latest version
- `versions: IntentSpecRead[]` -- all versions for the task
- `selectedVersion: IntentSpecRead | null` -- version currently displayed (defaults to `current`)
- `loading: boolean`
- `error: string | null`
- `mode: 'view' | 'edit'` -- right panel mode
- `refineModalOpen: boolean`
- `saving: boolean` -- true during approve/reject/edit/refine operations

**Actions interface** (`IntentActions`):
- `loadIntent(taskId: string): Promise<void>` -- calls `fetchIntent`, sets `current`, `versions`, `selectedVersion = current`, clears error
- `approve(): Promise<void>` -- calls `approveIntent(taskId!)`, sets saving during call
- `reject(reason: string): Promise<void>` -- calls `rejectIntent(taskId!, reason)`, sets saving during call
- `saveEdit(spec: { goal, constraints, acceptance_criteria, non_goals }): Promise<void>` -- calls `editIntent`, re-fetches intent, switches to view mode
- `requestRefine(feedback: string): Promise<void>` -- calls `refineIntent`, re-fetches intent, closes modal, switches to view mode
- `selectVersion(version: IntentSpecRead): void` -- sets `selectedVersion`
- `setMode(mode: 'view' | 'edit'): void`
- `setRefineModalOpen(open: boolean): void`
- `reset(): void` -- clears all state to defaults

**Error handling pattern:** Same as triage-store -- catch block sets `error` to `err.message`, finally sets `loading`/`saving` to false.

**Key behavior:** After `saveEdit` and `requestRefine`, the store re-fetches the full intent (calls `loadIntent` internally) to get the updated version list from the server, then displays the latest version. This avoids client-side version number tracking.

### Acceptance Criteria

- [ ] `useIntentStore` exported as named export
- [ ] `loadIntent` fetches and populates `current`, `versions`, `selectedVersion`
- [ ] `approve` calls API and sets `saving` flag during operation
- [ ] `reject` calls API with reason string
- [ ] `saveEdit` calls API, re-loads intent, switches mode to `view`
- [ ] `requestRefine` calls API, re-loads intent, closes modal
- [ ] `selectVersion` updates `selectedVersion` without API call
- [ ] `setMode('edit')` and `setMode('view')` toggle mode
- [ ] Error states set `error` string, not throw
- [ ] `npm run typecheck` passes

---

## Story 36.11c: SourceContext and IntentSpec Display Components

**Size:** M (4 hours, 1 Ralph loop)
**Dependencies:** 36.11a (needs `IntentSpecRead` type)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/SourceContext.tsx` | Create | Left panel -- read-only source context display |
| `frontend/src/components/planning/IntentSpec.tsx` | Create | Right panel -- read-only intent spec display |

### Specific Implementation

**SourceContext.tsx** -- Left panel showing the source material that produced the intent:

Props: `{ task: TaskPacketRead }` (the TaskPacket with enrichment data)

Layout (dark mode, matching existing `bg-gray-900 border-gray-700` patterns):
- **Header:** "Source Context" with task ID badge
- **Issue section:**
  - Issue title as `<h3>`
  - Issue body as plain text in a `<pre className="whitespace-pre-wrap">` block (no Markdown rendering -- `react-markdown` is not installed and adding a dependency is out of scope for this story; plain text is acceptable for MVP)
- **Enrichment section** (from `TaskPacketRead` fields populated by the Context stage before Intent runs):
  - Repo name as badge (`task.repo`)
  - Issue number (`task.issue_id`)
  - Status badge (`task.status`)
  - Complexity score: if `task.complexity_index` exists, render `complexity_index.score` as a colored bar (low=green, medium=amber, high=red) and `complexity_index.band` as a label. If null, show "Complexity: pending".
  - Risk flags: if `task.risk_flags` exists, render as a checklist of flag names with pass/fail icons. If null, show "Risk analysis: pending".
  - Scope/affected files: if `task.scope` exists, render file list from `scope.files_affected` (if present). If null, show "Scope: pending".
  - Created timestamp using the `timeAgo` pattern from `TriageCard.tsx` (extract to shared util if clean, or inline)
- Scrollable with `overflow-y-auto`
- Minimum height to prevent collapse in split layout
- All enrichment fields are optional and may be null -- always render graceful fallbacks

**IntentSpec.tsx** -- Right panel showing the structured intent specification:

Props: `{ spec: IntentSpecRead }`

Layout:
- **Source badge** at top: colored pill showing spec `source` value
  - `auto` -> gray badge (`bg-gray-700 text-gray-300`)
  - `developer` -> blue badge (`bg-blue-900 text-blue-300`)
  - `refinement` -> amber badge (`bg-amber-900 text-amber-300`)
- **Version + timestamp:** "v{version} -- {formatted date}"
- **Goal section:** `<h4>` heading "Goal" followed by text block
- **Constraints section:** `<h4>` heading "Constraints" followed by `<ul>` bullet list
- **Acceptance Criteria section:** `<h4>` heading "Acceptance Criteria" followed by numbered `<ol>` list
- **Non-Goals section:** `<h4>` heading "Non-Goals" followed by `<ul>` with `line-through` styling on items
- Empty list handling: if a section has zero items, show "None specified" in `text-gray-500`

Both components are pure display components. No API calls. No store dependencies. They receive data via props.

### Acceptance Criteria

- [ ] `SourceContext` renders task issue title and body as plain text
- [ ] `SourceContext` renders repo name, issue number, and status
- [ ] `IntentSpec` renders all 4 sections (goal, constraints, ACs, non-goals)
- [ ] `IntentSpec` shows source badge with correct color per source type
- [ ] `IntentSpec` shows version number and formatted timestamp
- [ ] Empty lists show "None specified" placeholder
- [ ] Non-goals items have strikethrough styling
- [ ] Both components match dark theme (bg-gray-900, text-gray-100, border-gray-700)
- [ ] `npm run typecheck` passes

---

## Story 36.11d: IntentEditor Container, Routing, and Action Buttons

**Size:** M (4 hours, 1 Ralph loop)
**Dependencies:** 36.11a, 36.11b, 36.11c (needs types, store, and display components)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/IntentEditor.tsx` | Create | Container with split-pane layout and action toolbar |
| `frontend/src/components/planning/VersionSelector.tsx` | Create | Version dropdown for right panel |
| `frontend/src/App.tsx` | Modify | Add 'intent' tab and IntentEditor rendering |

### Specific Implementation

**IntentEditor.tsx** -- Container component orchestrating the intent review experience:

Props: `{ taskId: string; onClose: () => void }`

On mount:
- Calls `fetchTaskDetail(taskId)` to get the full `TaskPacketRead` (stored in local `useState`, matching `TaskTimeline.tsx` pattern at line 164)
- Calls `useIntentStore().loadIntent(taskId)` for the intent spec data
- Reads `current`, `selectedVersion`, `versions`, `loading`, `error`, `mode`, `saving` from store
- The component fetches its own task — it does NOT receive a pre-fetched task as a prop. This matches the `TaskTimeline` pattern and avoids coupling to the parent's data.

Layout:
- **Header bar:** Task title, close button (calls `onClose`)
- **Action toolbar** (below header, horizontal button row):
  - "Approve & Continue" -- green (`bg-emerald-700`), calls `store.approve()`, disabled when `saving`
  - "Edit" -- blue outline (`border-blue-700 text-blue-400`), calls `store.setMode('edit')`, disabled when `saving`
  - "Request Refinement" -- amber outline (`border-amber-700 text-amber-400`), calls `store.setRefineModalOpen(true)`, disabled when `saving`
  - "Reject" -- red outline (`border-red-700 text-red-400`), opens inline reject confirmation (text input + confirm/cancel), disabled when `saving`
- **Split pane** (below toolbar):
  - Container: `grid grid-cols-[2fr_3fr] gap-4` (40/60 split)
  - Left: `<SourceContext task={task} />` (where `task` is the locally-fetched `TaskPacketRead`)
  - Right: `<IntentSpec spec={selectedVersion} />` when `mode === 'view'`; placeholder `<div>Edit mode placeholder</div>` when `mode === 'edit'` (actual edit form comes in 36.11e)
- **Bottom bar:** `<VersionSelector />` component
- **Loading state:** Spinner matching `TriageQueue` loading pattern
- **Error state:** Error banner with retry button matching `TriageQueue` error pattern

**Reject flow:**
- Clicking "Reject" toggles a small inline form (below the button row or replacing it):
  - Text input for reason (required)
  - "Confirm Reject" button (red) calls `store.reject(reason)`
  - "Cancel" button returns to normal toolbar

**VersionSelector.tsx:**

Props: none (reads from `useIntentStore`)

- `<select>` dropdown styled as dark theme select
- Options: one per version in `versions` array, formatted as `v{version} - {source} - {date}`
- `onChange` calls `store.selectVersion(selectedVersion)`
- Current selection matches `selectedVersion.id`

**App.tsx modification:**

Add a third tab `'intent'` to the `Tab` type union. The intent tab shows `<IntentEditor>` with a hardcoded or URL-param-derived task ID. However, the more natural UX is: clicking a task in `INTENT_BUILT` status from the pipeline view or triage view navigates to the intent editor. For MVP, add the intent view as a panel that appears when `selectedTaskId` is set and the task is in `INTENT_BUILT` status, OR add an `'intent'` tab that accepts a task ID.

**Simpler approach (recommended):** Add the intent editor as a view state within App.tsx. When a user needs to review intent, they click a task and it shows the IntentEditor instead of the TaskTimeline. This avoids URL routing complexity. The trigger can come from:
- A new `intentReviewTaskId` state in App.tsx
- Set by clicking a task card or a "Review Intent" action somewhere

For this story: wire it as a third tab `'intent'` with a task ID input field at the top. This is a scaffold -- the full navigation integration will come when the pipeline minimap or triage queue links to intent review.

### Acceptance Criteria

- [ ] IntentEditor renders split-pane layout with SourceContext left, IntentSpec right
- [ ] Four action buttons render in toolbar with correct colors
- [ ] Approve button calls `store.approve()` and is disabled during `saving`
- [ ] Reject shows inline confirmation with reason text input
- [ ] Reject confirmation calls `store.reject(reason)` with entered text
- [ ] Edit button calls `store.setMode('edit')` (right panel shows placeholder for now)
- [ ] Refinement button calls `store.setRefineModalOpen(true)` (modal placeholder for now)
- [ ] VersionSelector dropdown shows all versions with correct formatting
- [ ] Selecting a version updates the displayed spec
- [ ] Loading state shows spinner; error state shows retry
- [ ] IntentEditor is accessible from App.tsx (via tab or other navigation)
- [ ] `npm run typecheck` passes

---

## Story 36.11e: Intent Edit Mode Form

**Size:** M (4 hours, 1 Ralph loop)
**Dependencies:** 36.11d (needs IntentEditor container to host the edit form in right panel)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/IntentEditMode.tsx` | Create | Structured edit form replacing right panel |
| `frontend/src/components/planning/IntentEditor.tsx` | Modify | Replace edit placeholder with `<IntentEditMode>` |

### Specific Implementation

**IntentEditMode.tsx:**

Props: `{ spec: IntentSpecRead; onSave: (edited: { goal, constraints, acceptance_criteria, non_goals }) => void; onCancel: () => void; saving: boolean }`

Component state (local `useState`, not Zustand -- form state is ephemeral):
- `goal: string` -- initialized from `spec.goal`
- `constraints: string[]` -- initialized from `spec.constraints`
- `acceptanceCriteria: string[]` -- initialized from `spec.acceptance_criteria`
- `nonGoals: string[]` -- initialized from `spec.non_goals`

Layout:
- **Goal:** `<textarea>` with label "Goal", 3-4 rows, full width
- **Constraints:** Editable list component:
  - Each item: `<input type="text">` with an "X" remove button on the right
  - Below the list: "+ Add constraint" button (appends empty string to array)
  - Empty items are filtered out on save
- **Acceptance Criteria:** Same editable list pattern, label "Acceptance Criteria"
- **Non-Goals:** Same editable list pattern, label "Non-Goals"
- **Footer buttons:**
  - "Save" (blue, `bg-blue-700`) -- calls `onSave({ goal, constraints: constraints.filter(Boolean), acceptance_criteria: acceptanceCriteria.filter(Boolean), non_goals: nonGoals.filter(Boolean) })`, disabled when `saving` or when no fields changed from original
  - "Cancel" (gray text) -- calls `onCancel()`

**Editable list pattern:** Extract to a local sub-component `EditableList` within the file:
```
function EditableList({ label, items, onChange }: { label: string; items: string[]; onChange: (items: string[]) => void })
```
- Renders inputs mapped from `items` array
- `onChange` receives new array on add/remove/edit
- No drag-and-drop, no reordering

**IntentEditor.tsx modification:**

Replace the `mode === 'edit'` placeholder div with:
```tsx
<IntentEditMode
  spec={selectedVersion!}
  onSave={(edited) => void store.saveEdit(edited)}
  onCancel={() => store.setMode('view')}
  saving={saving}
/>
```

### Acceptance Criteria

- [ ] Edit mode renders form pre-filled with current spec values
- [ ] Goal textarea is editable
- [ ] Each list section (constraints, ACs, non-goals) renders existing items as text inputs
- [ ] "X" button on list items removes the item
- [ ] "+ Add" button appends a new empty input to each list
- [ ] "Save" calls `onSave` with correct JSON shape (matching `PUT /tasks/{id}/intent` body)
- [ ] Empty strings are filtered from arrays before save
- [ ] "Save" is disabled when no changes have been made
- [ ] "Cancel" returns to view mode without API call
- [ ] After successful save, right panel returns to view mode showing new version
- [ ] `npm run typecheck` passes

---

## Story 36.11f: Refinement Modal

**Size:** S (3 hours, 1 Ralph loop)
**Dependencies:** 36.11d (needs IntentEditor container to trigger the modal)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/RefinementModal.tsx` | Create | Modal dialog for refinement feedback |
| `frontend/src/components/planning/IntentEditor.tsx` | Modify | Render `<RefinementModal>` when `refineModalOpen` |

### Specific Implementation

**RefinementModal.tsx:**

Props: `{ open: boolean; onSubmit: (feedback: string) => void; onClose: () => void; saving: boolean }`

When `open` is false, render nothing (return null).

When `open` is true:
- **Backdrop:** Fixed overlay (`fixed inset-0 bg-black/50 z-40`) with click-to-close on backdrop
- **Modal panel:** Centered card (`fixed inset-0 flex items-center justify-center z-50`)
  - `bg-gray-900 border border-gray-700 rounded-lg shadow-xl max-w-lg w-full mx-4 p-6`
- **Header:** "Request Refinement" as `<h3>`
- **Description text:** "Describe what should change about the intent specification. The AI will refine the spec based on your feedback."
- **Textarea:** `feedback` state (local useState), 4-6 rows, full width, placeholder "e.g., The acceptance criteria should include error handling for invalid inputs..."
- **Validation:** Submit button disabled when `feedback.trim().length < 10` or `saving` is true
- **Footer buttons:**
  - "Submit Feedback" (amber, `bg-amber-700`) -- calls `onSubmit(feedback.trim())`
  - "Cancel" (gray text) -- calls `onClose()`
- **Keyboard:** Escape key closes modal (same `useEffect` pattern as `EditPanel.tsx`)

**IntentEditor.tsx modification:**

Add after the split pane layout:
```tsx
<RefinementModal
  open={refineModalOpen}
  onSubmit={(feedback) => void store.requestRefine(feedback)}
  onClose={() => store.setRefineModalOpen(false)}
  saving={saving}
/>
```

### Acceptance Criteria

- [ ] Modal renders when `open` is true, nothing when false
- [ ] Backdrop overlay covers full viewport
- [ ] Textarea accepts feedback text
- [ ] Submit button is disabled when feedback is fewer than 10 characters
- [ ] Submit button is disabled when `saving` is true
- [ ] Submitting calls `onSubmit` with trimmed feedback string
- [ ] Cancel closes modal
- [ ] Escape key closes modal
- [ ] Clicking backdrop closes modal
- [ ] After successful refinement, modal closes and new version appears in right panel
- [ ] `npm run typecheck` passes

---

## Story 36.11g: Version Diff View and Component Tests

**Size:** M (3 hours, 1 Ralph loop)
**Dependencies:** 36.11d (needs VersionSelector and IntentSpec), 36.11e and 36.11f (needs edit/refine to be complete for full test coverage)

### Deliverables

| File | Action | What |
|------|--------|------|
| `frontend/src/components/planning/VersionDiff.tsx` | Create | Field-level diff between two spec versions |
| `frontend/src/components/planning/IntentEditor.tsx` | Modify | Add "Compare Versions" toggle to show diff view |
| `frontend/src/components/planning/__tests__/IntentEditor.test.tsx` | Create | Component tests for the full intent editor |

### Specific Implementation

**VersionDiff.tsx:**

Props: `{ versionA: IntentSpecRead; versionB: IntentSpecRead }`

Layout:
- Two-column header showing version labels: "v{A.version} ({A.source})" and "v{B.version} ({B.source})"
- **Goal section:** If goals differ, show old goal with red background (`bg-red-900/30`), new goal with green background (`bg-emerald-900/30`). If identical, show "No change" in gray.
- **List sections** (constraints, ACs, non-goals): For each section:
  - Items in B but not in A: shown with green left border (`border-l-2 border-emerald-500 bg-emerald-900/20`)
  - Items in A but not in B: shown with red left border (`border-l-2 border-red-500 bg-red-900/20`)
  - Items in both: shown plain (no highlight)
  - Comparison is exact string match (no fuzzy matching for MVP)
- **Summary line:** "{N} additions, {M} removals across all sections"

**Diff logic** (pure function, no side effects -- testable independently):
```typescript
function diffLists(a: string[], b: string[]): { added: string[]; removed: string[]; unchanged: string[] }
```
- `added` = items in `b` not in `a` (using `Set` for O(n) lookup)
- `removed` = items in `a` not in `b`
- `unchanged` = items in both

**IntentEditor.tsx modification:**

Add a "Compare Versions" toggle button near the VersionSelector. When active:
- Show a second version dropdown (select the version to compare against)
- Replace the IntentSpec panel with `<VersionDiff versionA={compareVersion} versionB={selectedVersion} />`
- Toggle back to single-version view with the same button

**Component Tests** (`IntentEditor.test.tsx`):

Follow the `TriageQueue.test.tsx` pattern:
- Mock `../../lib/api` with `vi.mock`
- Mock all 5 intent API functions
- Create a `mockIntentSpec` factory function
- Reset `useIntentStore` state in `beforeEach`

Test cases:
1. **Loading state:** Shows spinner when loading
2. **Split pane renders:** Both panels visible after load
3. **IntentSpec sections:** Goal, constraints, ACs, non-goals all render
4. **Source badge:** Correct color for each source type
5. **Version selector:** Shows correct version count and labels
6. **Approve button:** Calls `approveIntent` API function
7. **Reject flow:** Shows reason input, confirm calls `rejectIntent` with reason
8. **Edit mode toggle:** Clicking Edit switches right panel to form
9. **Edit form pre-fill:** Form fields contain current spec values
10. **Edit save:** Save calls `editIntent` with correct shape
11. **Edit cancel:** Returns to view mode without API call
12. **Refinement modal:** Opens on button click, submits feedback
13. **Refinement validation:** Submit disabled when feedback < 10 chars
14. **Diff view:** Shows additions in green, removals in red
15. **Version comparison:** Selecting two versions shows diff

### Acceptance Criteria

- [ ] VersionDiff renders field-level comparison between two specs
- [ ] Added items shown with green indicator; removed with red
- [ ] Unchanged items shown without highlight
- [ ] Goal diff shows old/new when changed
- [ ] "Compare Versions" toggle switches between single view and diff view
- [ ] All 15 test cases pass
- [ ] Tests mock API functions (no real HTTP calls)
- [ ] Tests cover loading, error, view, edit, refine, diff states
- [ ] `npm test` passes with no failures
- [ ] `npm run typecheck` passes

---

## Dependency Graph

```
36.11a (API types + functions)
  |
  +-- 36.11b (Zustand store) ---+
  |                              |
  +-- 36.11c (Display components) --+-- 36.11d (Container + routing + buttons)
                                          |
                                    +-----+------+
                                    |            |
                              36.11e (Edit)  36.11f (Refine modal)
                                    |            |
                                    +-----+------+
                                          |
                                    36.11g (Diff + tests)
```

**Critical path:** 36.11a -> 36.11b -> 36.11d -> 36.11e -> 36.11g (5 stories, 15 hours)
**Parallelizable:** 36.11c can run in parallel with 36.11b. 36.11e can run in parallel with 36.11f.

---

## Capacity Summary

| Story | Title | Size | Est. Hours | Ralph Loops | Day |
|-------|-------|------|-----------|-------------|-----|
| 36.11a | API Types + Functions | S | 2.0 | 1 | Day 1 |
| 36.11b | Intent Zustand Store | S | 2.0 | 1 | Day 1 |
| 36.11c | SourceContext + IntentSpec Display | M | 4.0 | 1 | Day 1-2 |
| 36.11d | IntentEditor Container + Routing | M | 4.0 | 1 | Day 2 |
| 36.11e | Edit Mode Form | M | 4.0 | 1 | Day 3 |
| 36.11f | Refinement Modal | S | 3.0 | 1 | Day 3 |
| 36.11g | Version Diff + All Tests | M | 3.0 | 1 | Day 4 |
| **Total** | | | **22.0** | **7** | |
| **Buffer** | | | **8.0** | | **Day 5** |

**Allocation:** 22 of 30 hours = 73% with 27% buffer (unchanged from original plan).

---

## Compressibility (Ordered)

1. **36.11g VersionDiff component** -- first to defer. The diff view is nice-to-have. Ship without it; the developer selects different versions in the dropdown and reads them manually. Tests for stories 36.11a-36.11f can be written inline with each story instead. **Impact:** No visual diff between versions.

2. **36.11f Refinement Modal** -- second to defer. Edit mode (36.11e) still works. The developer can manually edit the spec instead of requesting AI refinement. **Impact:** No AI-assisted refinement from the dashboard.

3. **36.11e Edit Mode Form** -- third to defer (most aggressive compression). The read-only view with approve/reject (36.11a-36.11d) is the minimum viable intent review. **Impact:** Developer can review and approve/reject but cannot edit the spec from the dashboard. Must reject and re-submit the issue to change intent.

---

## Relationship to Original Stories

| Original Story | Decomposed Into | Scope |
|---------------|-----------------|-------|
| 36.11 (12h, L) | 36.11a + 36.11b + 36.11c + 36.11d | Types, store, display components, container, routing, approve/reject buttons, version selector |
| 36.12 (10h, L) | 36.11e + 36.11f + 36.11g | Edit form, refinement modal, version diff, all component tests |

---

## Notes for Ralph Execution

1. **No react-markdown dependency.** The frontend does not have `react-markdown` installed. Story 36.11c renders issue body as plain preformatted text (`<pre className="whitespace-pre-wrap">`). This is acceptable for MVP. If Markdown rendering is needed later, it is a separate story.

2. **No URL-based routing.** The App.tsx uses tab-based navigation with `useState`, not a router library. Story 36.11d adds the intent editor as a tab or panel view. No `react-router` needed.

3. **Store re-fetches after mutations.** After `saveEdit` and `requestRefine`, the store calls `loadIntent` again to get fresh data from the server. This is simpler and more reliable than client-side optimistic updates for version tracking.

4. **Dark theme constants.** Use the same Tailwind classes as existing components: `bg-gray-900`, `bg-gray-950`, `text-gray-100`, `text-gray-400`, `border-gray-700`, `border-gray-800`. Button colors follow `TriageCard.tsx` patterns exactly.

5. **Test pattern.** All tests follow the `TriageQueue.test.tsx` pattern: `vi.mock('../../lib/api')`, mock factory functions, `useStore.setState()` in `beforeEach`, `render()` + `screen` + `waitFor` assertions.

---

## Meridian Review: PASS (2026-03-21)

**Reviewer:** Meridian (VP of Success)
**Initial Verdict:** CONDITIONAL PASS -- 2 gaps found.
**Final Verdict:** PASS -- both gaps fixed.

### Gaps Found and Fixed

**Gap 1: TaskPacketRead type mismatch.** The frontend `TaskPacketRead` interface was missing `issue_title`, `issue_body`, `scope`, `risk_flags`, and `complexity_index` fields that the backend returns. **Fixed:** Story 36.11a now extends the interface with these optional fields.

**Gap 2: SourceContext data source unspecified.** Story 36.11c referenced vague "enrichment data" without specifying which fields. Story 36.11d received `task: TaskPacketRead` as a prop without specifying who fetches it. **Fixed:** Story 36.11c now references specific fields (`complexity_index.score`, `risk_flags`, `scope.files_affected`) with null fallbacks. Story 36.11d now fetches its own task via `fetchTaskDetail(taskId)` matching the `TaskTimeline` pattern.

### 7 Questions

| # | Question | Verdict |
|---|----------|---------|
| 1 | Story boundaries clean? | PASS |
| 2 | Dependencies correct? | PASS |
| 3 | ACs testable? | PASS |
| 4 | Specific enough for AI agent? | PASS (after fix) |
| 5 | Gaps vs epic ACs? | PASS (after fix) |
| 6 | Compressibility correct? | PASS |
| 7 | Source code assumptions verified? | PASS |
