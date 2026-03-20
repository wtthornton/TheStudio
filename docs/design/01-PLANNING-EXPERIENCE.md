# 01 — Planning Experience Design Specification

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** Everything the developer sees and does before a TaskPacket enters the Implement stage. Covers issue intake, context review, Intent Specification editing, risk assessment, expert routing, and backlog management.

---

## 1. Design Philosophy

Planning is where developer trust is built. If the developer is confident the system understood what to build, why it matters, and how to validate it — they'll let the pipeline run autonomously. If planning feels like a black box, they'll micromanage every stage.

**Goal:** The planning experience should feel like reviewing a junior developer's design doc — structured, editable, with clear risk flags — not like submitting a form and hoping for the best.

---

## 2. Feature: Issue Intake & Triage

### 2.1 What It Does

Receives GitHub issues (via existing webhook handler) and presents them in a triage queue where the developer can review, enrich, and release them into the pipeline — or reject them.

### 2.2 Look and Feel

**Triage Queue View:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TRIAGE QUEUE                                    3 pending  ▼   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #142  Fix login timeout on slow connections      2m ago  │   │
│  │ bug · auth · reported by @user123                        │   │
│  │ ────────────────────────────────────────────────────────  │   │
│  │ "When the server takes >5s to respond, the login         │   │
│  │  form shows a blank screen instead of a timeout..."      │   │
│  │                                                          │   │
│  │  Complexity: ●○○ Low    Risk: ●○○ Low    Est: $0.40     │   │
│  │                                                          │   │
│  │  [ Accept & Plan ]   [ Edit Before Accept ]   [ Reject ] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #143  Add dark mode support                      5m ago  │   │
│  │ feature · ui · reported by @designer                     │   │
│  │ ...                                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Card elements:**
- Issue number, title, age
- Labels (mapped to category: bug, feature, refactor, docs)
- Reporter with GitHub avatar
- Truncated description (expandable)
- Quick complexity/risk/cost indicators (from Context stage pre-scan)
- Three action buttons: Accept & Plan, Edit Before Accept, Reject

**Interaction patterns:**
- Click card → expands inline with full issue body (rendered Markdown)
- "Accept & Plan" → creates TaskPacket, sends through Context → Intent
- "Edit Before Accept" → opens side panel with editable fields (title, description, constraints, acceptance criteria)
- "Reject" → archives with reason (dropdown: duplicate, out of scope, needs info, won't fix)
- Keyboard: `j/k` navigate, `a` accept, `e` edit, `r` reject (following Linear's keyboard model)

**Sorting and filtering:**
- Sort by: newest, oldest, priority (if labeled), estimated complexity
- Filter by: label, reporter, repository (future multi-repo), unread

### 2.3 Data Flow

```
GitHub webhook → src/ingress/webhook_handler.py → TaskPacket created (status: triage)
    → Context stage runs pre-scan (lightweight: file impact, complexity hint, cost estimate)
    → Triage Queue displays enriched card
    → Developer action → TaskPacket released to full Context → Intent pipeline
```

### 2.4 Structured Issue Forms

For repositories that opt in, provide GitHub Issue Form templates (YAML) that produce machine-readable input:

```yaml
# .github/ISSUE_TEMPLATE/thestudio-task.yml
name: TheStudio Task
description: Submit a task for AI delivery
body:
  - type: input
    id: goal
    attributes:
      label: Goal
      description: What should be accomplished?
  - type: textarea
    id: acceptance_criteria
    attributes:
      label: Acceptance Criteria
      description: How do we know it's done?
  - type: dropdown
    id: category
    attributes:
      label: Category
      options: [bug fix, feature, refactor, documentation]
  - type: dropdown
    id: priority
    attributes:
      label: Priority
      options: [critical, high, medium, low]
```

When a structured issue arrives, the triage card auto-populates fields from the form, reducing manual enrichment.

**Reference:** [IssueOps Documentation](https://issue-ops.github.io/docs/), [GitHub Issue Forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues/syntax-for-githubs-form-schema)

### 2.5 Stories for Epic Decomposition

- S1: Triage queue view with card list (read-only, from existing webhook data)
- S2: Accept/reject actions that update TaskPacket status
- S3: Edit-before-accept side panel with editable fields
- S4: Pre-scan enrichment (complexity hint, file impact, cost estimate)
- S5: Keyboard navigation (j/k/a/e/r)
- S6: Structured issue form templates (optional per-repo)
- S7: Sorting and filtering controls

---

## 3. Feature: Intent Specification Editor

### 3.1 What It Does

After Context stage completes and Intent Builder generates a draft Intent Specification, the developer reviews and optionally edits it before the pipeline proceeds. This is the **most important planning artifact** — it defines what "correct" means.

### 3.2 Look and Feel

**Split-pane layout:**
```
┌──────────────────────────┬──────────────────────────────────────┐
│  SOURCE CONTEXT          │  INTENT SPECIFICATION                │
│                          │                                      │
│  Issue #142              │  ## Goal                             │
│  ──────────              │  Fix login timeout handling for      │
│  Fix login timeout on    │  connections exceeding 5 seconds.    │
│  slow connections.       │                                      │
│                          │  ## Constraints                      │
│  When the server takes   │  ☑ Must show timeout message after   │
│  >5s to respond, the     │    5s (not blank screen)             │
│  login form shows a      │  ☑ Must preserve entered credentials │
│  blank screen instead    │    across retry                      │
│  of a timeout message.   │  ☐ Should support configurable       │
│                          │    timeout duration                  │
│  ────────────────────    │                                      │
│  Context Enrichment      │  ## Acceptance Criteria              │
│  ──────────────────      │  1. Login form shows "Connection     │
│                          │     timed out" after 5s              │
│  Files affected:         │  2. Retry button re-submits with     │
│  • src/auth/login.py     │     preserved credentials            │
│  • src/auth/timeout.py   │  3. No blank screen state exists     │
│  • tests/auth/           │                                      │
│                          │  ## Validation Strategy              │
│  Related PRs:            │  • Unit test: timeout triggers       │
│  • #138 (auth refactor)  │    message display                   │
│                          │  • Integration test: slow server     │
│  Complexity: Medium      │    simulation with 6s delay          │
│  Risk flags: none        │  • Regression: existing login flow   │
│                          │    unaffected                        │
│                          │                                      │
│                          │  ┌────────────────────────────────┐  │
│                          │  │  v2 (current)  ← v1 (initial)  │  │
│                          │  └────────────────────────────────┘  │
│                          │                                      │
│                          │  [ Approve & Continue ]  [ Edit ]    │
│                          │  [ Request Refinement ]  [ Reject ]  │
└──────────────────────────┴──────────────────────────────────────┘
```

**Left panel — Source Context:**
- Original issue body (rendered Markdown)
- Context enrichment results: affected files, related PRs/commits, complexity score, risk flags
- Collapsible sections for each context source
- Read-only (this is reference material)

**Right panel — Intent Specification:**
- Rendered Markdown with inline editing (click to edit any section)
- Checkboxes on constraints (developer can check/uncheck to include/exclude)
- Version selector at bottom (see how the spec evolved across refinement cycles)
- Four action buttons:
  - **Approve & Continue** → releases to Router stage
  - **Edit** → switches to full Markdown editor mode
  - **Request Refinement** → sends back to Intent Builder with developer feedback (text input modal)
  - **Reject** → aborts the TaskPacket with reason

**Edit mode:**
- Full Markdown editor (Monaco or CodeMirror) replacing the right panel
- Live preview toggle (side-by-side or tabbed)
- Template sections pre-populated (Goal, Constraints, Acceptance Criteria, Validation Strategy)
- Save creates a new version (version history preserved)

**Version history:**
- Dropdown showing v1, v2, v3... with timestamps and source (auto-generated, developer-edited, refinement)
- Diff view between any two versions (inline diff, not side-by-side, to save space)

### 3.3 Interaction Patterns

- Inline editing: click any section header or paragraph to enter edit mode for that section
- Constraint checkboxes: toggle individual constraints without entering full edit mode
- Cmd+Enter: approve and continue (primary keyboard shortcut)
- Esc: cancel edit, return to rendered view
- Tab: cycle through sections
- Developer edits are tracked with `edited_by: developer` metadata on the spec version

### 3.4 Data Flow

```
Context stage → enrichment data → Left panel
Intent Builder → draft spec (Markdown) → Right panel
Developer approval → TaskPacket.intent_spec updated → Router stage
Developer refinement request → Intent Builder re-runs with feedback → new version
Developer edit → spec updated directly → Router stage
```

### 3.5 Copilot Workspace Comparison

GitHub's Copilot Workspace (now Coding Agent) pioneered the "Specification → Plan → Implement" flow with developer review at each step. Key differences:

| | Copilot Workspace | TheStudio Intent Editor |
|---|---|---|
| Spec format | Freeform AI summary | Structured (Goal, Constraints, Acceptance Criteria, Validation Strategy) |
| Editability | Full rewrite or accept | Section-level inline editing + constraint toggles |
| Versioning | None (edit in place) | Full version history with diffs |
| Context | Repo scan summary | Enriched context (files, PRs, complexity, risk) |
| Refinement loop | Manual edit only | "Request Refinement" sends feedback to Intent Builder |

**Reference:** [Copilot Workspace - GitHub Next](https://githubnext.com/projects/copilot-workspace), [Devin Interactive Planning](https://docs.devin.ai/work-with-devin/interactive-planning)

### 3.6 Stories for Epic Decomposition

- S1: Split-pane layout with source context (left) and rendered intent spec (right)
- S2: Approve & Continue action that releases TaskPacket to Router
- S3: Inline section editing (click-to-edit on any section)
- S4: Constraint checkboxes for include/exclude
- S5: Full Markdown editor mode with live preview
- S6: Request Refinement flow (feedback modal → Intent Builder re-run)
- S7: Version history dropdown with diff view
- S8: Reject action with reason
- S9: Keyboard shortcuts (Cmd+Enter approve, Esc cancel, Tab cycle)

---

## 4. Feature: Complexity & Risk Dashboard

### 4.1 What It Does

After Context stage completes, displays a visual risk assessment to help the developer decide whether to proceed, adjust scope, or add constraints before execution.

### 4.2 Look and Feel

**Dashboard layout (appears as a tab or section within the TaskPacket detail view):**

```
┌─────────────────────────────────────────────────────────────────┐
│  COMPLEXITY & RISK ASSESSMENT         TaskPacket #142           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Overall: ████████░░ Medium (6.2/10)     Est. Cost: $1.20-2.40 │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  FILES AFFECTED   │  │  DEPENDENCY DEPTH │  │  TEST GAPS   │  │
│  │                   │  │                   │  │              │  │
│  │  src/auth/        │  │  login.py         │  │  ⚠ timeout   │  │
│  │  ██████ 3 files   │  │  ├─ session.py    │  │    handler   │  │
│  │                   │  │  ├─ middleware.py  │  │    0% covered│  │
│  │  tests/auth/      │  │  └─ db/users.py   │  │              │  │
│  │  ████ 2 files     │  │                   │  │  ✓ login.py  │  │
│  │                   │  │  Depth: 3         │  │    87% covered│  │
│  │  Total: 5 files   │  │  Cross-module: No │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FILE IMPACT HEATMAP                                     │   │
│  │                                                          │   │
│  │  src/                                                    │   │
│  │  ├── auth/                                               │   │
│  │  │   ├── login.py          ██████████ HIGH (core change) │   │
│  │  │   ├── timeout.py        ████████░░ MEDIUM (new file)  │   │
│  │  │   └── session.py        ████░░░░░░ LOW (import only)  │   │
│  │  ├── middleware/                                          │   │
│  │  │   └── auth_middleware.py ██░░░░░░░░ MINIMAL (type ref)│   │
│  │  └── tests/auth/                                         │   │
│  │      ├── test_login.py     ████████░░ MEDIUM (new tests) │   │
│  │      └── test_timeout.py   ██████████ HIGH (new file)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  RISK FLAGS                                              │   │
│  │  ✓ No cross-module dependencies                         │   │
│  │  ✓ No database migrations required                      │   │
│  │  ⚠ One file has 0% test coverage (timeout.py is new)    │   │
│  │  ✓ No recent conflicts in affected files                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  HISTORICAL COMPARISON                                   │   │
│  │  Similar tasks (auth, bug fix, medium complexity):       │   │
│  │  • Avg stages: 9 (full pipeline)   • Avg cost: $1.80    │   │
│  │  • Avg loopbacks: 0.3              • Success rate: 89%  │   │
│  │  • Avg time: 12 min                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Overall score bar** — Single horizontal bar, color-coded (green/amber/red), with numeric score and cost estimate range.

2. **Three metric cards** — Files Affected (count + directory breakdown), Dependency Depth (tree visualization), Test Gaps (coverage flags per affected file).

3. **File Impact Heatmap** — Tree view of affected files with horizontal intensity bars. Color gradient from green (minimal) to red (high impact). Each file shows the reason for its impact level.

4. **Risk Flags** — Checklist of pass/fail risk indicators. Green checkmarks for non-issues, amber warnings for risks. Each flag is clickable for explanation.

5. **Historical Comparison** — Stats from past similar tasks (same category, similar complexity). Shows avg stages, cost, loopbacks, success rate, time. Only shown if sufficient historical data exists (>5 similar tasks).

### 4.3 Interaction Patterns

- Hover any file in the heatmap → tooltip shows why it was flagged (import analysis, diff prediction)
- Click a risk flag → expands with full explanation and mitigation suggestion
- Click historical comparison → shows the individual past tasks that were compared
- The entire dashboard is read-only (informational); the action is on the Intent Editor

### 4.4 Data Sources

- File impact: from Context stage (`src/context/`) file analysis
- Dependency depth: from import graph analysis
- Test coverage: from existing test coverage data (if available) or heuristic
- Risk flags: from Context stage risk assessment
- Historical data: from Outcome pipeline (`src/outcome/`) + PostgreSQL

### 4.5 Inspiration

- **Aperant's `complexity_assessor.md`** — AI-based complexity scoring with structured output
- **Codegen's analytics dashboard** — Per-task cost projections with historical comparison
- **Factory AI's Knowledge Droid** — Research phase that surfaces relevant context before coding
- **GitHub Copilot Workspace** — Repo scan summary shown before planning

### 4.6 Stories for Epic Decomposition

- S1: Overall complexity score bar with cost estimate
- S2: Three metric cards (files affected, dependency depth, test gaps)
- S3: File impact heatmap tree view
- S4: Risk flags checklist with expand-for-detail
- S5: Historical comparison panel (requires outcome data aggregation)
- S6: Hover tooltips on all interactive elements

---

## 5. Feature: Expert Routing Preview

### 5.1 What It Does

After the Router stage selects experts, shows the developer which expert roles will work on the task and why — before Assembler begins.

### 5.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────┐
│  EXPERT ROUTING                          TaskPacket #142        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│          ┌─────────────┐                                        │
│          │  Intent Spec │                                       │
│          │  #142        │                                       │
│          └──────┬───────┘                                       │
│                 │                                                │
│       ┌─────────┼─────────┐                                     │
│       │         │         │                                     │
│  ┌────▼───┐ ┌──▼─────┐ ┌─▼──────┐                             │
│  │ Auth   │ │ Error  │ │ Test   │                              │
│  │ Expert │ │ Handle │ │ Expert │                              │
│  │        │ │ Expert │ │        │                              │
│  │ ●MAND. │ │ ●AUTO  │ │ ●MAND. │                             │
│  └────────┘ └────────┘ └────────┘                              │
│                                                                 │
│  ─── Expert Details ─────────────────────────────────────────   │
│                                                                 │
│  Auth Expert                                          MANDATORY │
│  Mandate: Authentication and session management                 │
│  Files:   src/auth/login.py, src/auth/timeout.py               │
│  Reason:  Task directly modifies auth login flow                │
│  Weight:  0.92 (reputation score)                               │
│                                                                 │
│  Error Handling Expert                                     AUTO │
│  Mandate: Error states, timeout handling, user feedback         │
│  Files:   src/auth/timeout.py                                  │
│  Reason:  Task involves timeout error handling                  │
│  Weight:  0.87 (reputation score)                               │
│                                                                 │
│  Test Expert                                          MANDATORY │
│  Mandate: Test creation and coverage                            │
│  Files:   tests/auth/test_login.py, tests/auth/test_timeout.py │
│  Reason:  Mandatory coverage — every task gets test expert      │
│  Weight:  0.95 (reputation score)                               │
│                                                                 │
│  [ Approve Routing ]  [ Add Expert ▼ ]  [ Remove Expert ]      │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Network diagram** — Intent Spec at top, expert nodes branching below. Lines show routing. Node badges: MANDATORY (required by routing rules), AUTO (selected by AI analysis).

2. **Expert detail cards** — For each expert: role name, mandate description, assigned files, reason for selection, reputation weight. Sorted by weight (highest first).

3. **Override controls** — "Add Expert" dropdown (choose from available expert roles), "Remove Expert" (click on any AUTO expert to remove, MANDATORY experts can't be removed). "Approve Routing" releases to Assembler.

### 5.3 Interaction Patterns

- Hover expert node in diagram → highlights assigned files in the detail cards
- Click expert node → scrolls to its detail card
- "Add Expert" dropdown shows all available expert roles not already selected, with relevance scores
- Removing an AUTO expert requires confirmation ("This may reduce coverage of error handling. Continue?")
- MANDATORY experts show a lock icon and tooltip explaining why they can't be removed

### 5.4 Stories for Epic Decomposition

- S1: Expert list view with detail cards (read-only)
- S2: Network diagram visualization (Intent → Experts)
- S3: Approve Routing action
- S4: Add Expert override with role dropdown
- S5: Remove Expert override with confirmation
- S6: Reputation weight display per expert

---

## 6. Feature: Roadmap & Backlog Board

### 6.1 What It Does

A multi-view board showing all work (past, present, planned) organized by pipeline stage, priority, or timeline. This is the "big picture" planning view.

### 6.2 Look and Feel — Kanban View (Primary)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BACKLOG              View: [ Kanban ▼ ]  Filter: [ All ▼ ]  + New    │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ TRIAGE   │ PLANNING │ BUILDING │ VERIFY   │ DONE     │ REJECTED        │
│ (3)      │ (2)      │ (1)      │ (0)      │ (12)     │ (2)             │
├──────────┼──────────┼──────────┼──────────┼──────────┼─────────────────┤
│          │          │          │          │          │                 │
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │          │ ┌──────┐ │ ┌──────┐       │
│ │ #145 │ │ │ #142 │ │ │ #139 │ │          │ │ #137 │ │ │ #140 │       │
│ │ Dark │ │ │ Login│ │ │ API  │ │          │ │ Cache│ │ │ Dupl.│       │
│ │ mode │ │ │ time │ │ │ rate │ │          │ │ fix  │ │ │      │       │
│ │      │ │ │ out  │ │ │ limit│ │          │ │      │ │ └──────┘       │
│ │ feat │ │ │      │ │ │      │ │          │ │ $0.80│ │                 │
│ │ med  │ │ │ bug  │ │ │ feat │ │          │ │ ✓ 9/9│ │                 │
│ └──────┘ │ │ low  │ │ │ high │ │          │ └──────┘ │                 │
│          │ │ $1.80│ │ │ $3.20│ │          │          │                 │
│ ┌──────┐ │ └──────┘ │ │ ██▓░ │ │          │ ┌──────┐ │                 │
│ │ #144 │ │          │ │ Impl │ │          │ │ #136 │ │                 │
│ │ ...  │ │ ┌──────┐ │ └──────┘ │          │ │ ...  │ │                 │
│ └──────┘ │ │ #143 │ │          │          │ └──────┘ │                 │
│          │ │ ...  │ │          │          │          │                 │
│          │ └──────┘ │          │          │          │                 │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

**Column mapping:**
- **Triage** = TaskPackets in triage status (pre-pipeline)
- **Planning** = Intake through Router stages (Context, Intent, Router)
- **Building** = Assembler through Implement stages
- **Verify** = Verification + QA stages
- **Done** = Published (PR created)
- **Rejected** = Developer rejected at any stage

**Card elements:**
- Issue number + truncated title
- Category badge (bug, feature, refactor) with color
- Complexity indicator (low/med/high)
- Cost (estimated for planning, actual for done)
- Mini progress bar for building stage (shows sub-stage)
- Gates passed indicator for done (e.g., "✓ 9/9")

**Drag-and-drop:**
- Drag between columns to manually change status (e.g., move from Triage to Planning to fast-track)
- Cannot drag backward past current pipeline stage (prevents inconsistency)
- Drag to Rejected to abort
- Uses @dnd-kit library for keyboard accessibility

### 6.3 Look and Feel — Priority Matrix View

```
┌─────────────────────────────────────────────────────────────────┐
│  BACKLOG              View: [ Priority Matrix ▼ ]               │
├─────────────────────────────────┬───────────────────────────────┤
│  HIGH IMPACT                    │  HIGH IMPACT                  │
│  LOW EFFORT                     │  HIGH EFFORT                  │
│  ─────────── DO FIRST ───────── │  ────────── PLAN CAREFULLY ── │
│                                 │                               │
│  • #142 Login timeout (bug)     │  • #143 Dark mode (feature)   │
│  • #146 Fix typo in API (docs)  │  • #139 API rate limit (feat) │
│                                 │                               │
├─────────────────────────────────┼───────────────────────────────┤
│  LOW IMPACT                     │  LOW IMPACT                   │
│  LOW EFFORT                     │  HIGH EFFORT                  │
│  ─────────── DO LATER ───────── │  ────────── RECONSIDER ────── │
│                                 │                               │
│  • #148 Update README (docs)    │  • #144 Rewrite logger (refac)│
│                                 │                               │
└─────────────────────────────────┴───────────────────────────────┘
```

- Four quadrants based on impact × effort
- Cards are draggable between quadrants to re-prioritize
- Impact and effort derived from Context stage analysis (developer can override)

### 6.4 Look and Feel — Timeline View

```
┌─────────────────────────────────────────────────────────────────┐
│  BACKLOG              View: [ Timeline ▼ ]                      │
├─────────────────────────────────────────────────────────────────┤
│        Today        +1d          +2d          +3d               │
│  ──────┼────────────┼────────────┼────────────┼─────────        │
│                                                                 │
│  #142  ████████████░░░░░░                                       │
│        Planning ──────▶ Building                                │
│                                                                 │
│  #139       ░░░░░░░████████████████████████████░░░░░░           │
│             Planning ──────▶ Building ──────▶ Verify            │
│                                                                 │
│  #143                    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │
│                          Queued (estimated)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- Gantt-style horizontal bars per TaskPacket
- Color segments for each pipeline stage
- Solid = completed/in-progress, dashed = estimated
- Shows queuing (tasks waiting for pipeline capacity)

### 6.5 GitHub Projects Sync

The board syncs bidirectionally with GitHub Projects v2:

- TheStudio board state → GitHub Projects custom fields (stage, cost, trust tier)
- GitHub Projects status changes → TheStudio board updates
- Sync uses GitHub GraphQL API (`addProjectV2ItemById`, `updateProjectV2ItemFieldValue`)
- Developer can use either UI; both stay consistent

**Reference:** [GitHub Projects v2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects), [Plane GitHub Integration](https://docs.plane.so/integrations/github)

### 6.6 Inspiration Sources

| Feature | Inspired By | Adaptation |
|---------|-------------|------------|
| Kanban with pipeline columns | Aperant (5 columns), Mission Control (6 columns) | 6 columns mapped to pipeline stage groups |
| Priority matrix | Aperant's 4-view roadmap (must/should/could/wont) | 2×2 impact×effort quadrants |
| Timeline/Gantt | Plane's Gantt charts | Pipeline-stage-colored segments |
| Drag-and-drop | Aperant uses @dnd-kit | Same library, with pipeline-aware constraints |
| Column preferences | Aperant (width, collapse, lock per column) | Adopt directly |
| Card design | Linear (minimal, fast) | Issue number, title, category, progress |

### 6.7 Stories for Epic Decomposition

- S1: Kanban view with 6 columns and card rendering
- S2: Card detail expansion (click to see full info)
- S3: Drag-and-drop between columns with @dnd-kit
- S4: Pipeline-aware drag constraints (no backward moves)
- S5: Priority matrix view
- S6: Timeline/Gantt view with stage-colored bars
- S7: View switcher (Kanban / Priority / Timeline)
- S8: Filtering and sorting controls
- S9: Column preferences (width, collapse, lock)
- S10: GitHub Projects v2 bidirectional sync
- S11: "New Task" button (manual task creation without GitHub issue)

---

## 7. Feature: Manual Task Creation

### 7.1 What It Does

Allows creating a TaskPacket directly from the dashboard without a GitHub issue. Useful for testing, demos, and internal tasks.

### 7.2 Look and Feel

Modal dialog with form fields:

```
┌─────────────────────────────────────────────────────────────┐
│  CREATE TASK                                           ✕    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Title *                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Fix login timeout on slow connections               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Description *                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ When the server takes >5s to respond, the login     │   │
│  │ form shows a blank screen instead of a timeout...   │   │
│  │                                                     │   │
│  │                                          Markdown ✓ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Category        Priority        Repository                │
│  [ Bug fix ▼ ]   [ Medium ▼ ]    [ TheStudio ▼ ]          │
│                                                             │
│  Acceptance Criteria (optional)                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ + Add criterion                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ☐ Skip triage (send directly to Context stage)            │
│  ☐ Create GitHub issue (sync back to repository)           │
│                                                             │
│              [ Cancel ]    [ Create Task ]                  │
└─────────────────────────────────────────────────────────────┘
```

- Markdown-enabled description field
- Optional acceptance criteria (add/remove list items)
- "Skip triage" checkbox to fast-track into the pipeline
- "Create GitHub issue" checkbox to back-sync to the repo
- Draft persistence to localStorage (restored on reopen)

**Reference:** Aperant's `TaskCreationWizard.tsx` — draft persistence, branch selection, image attachments. We simplify (no branch selection, no model configuration at this stage) but keep the draft persistence pattern.

### 7.3 Stories for Epic Decomposition

- S1: Modal with title + description + category + priority fields
- S2: Markdown editor for description
- S3: Acceptance criteria list (add/remove)
- S4: Skip triage and create GitHub issue checkboxes
- S5: Draft persistence to localStorage
- S6: Form validation and submission

---

## 8. Cross-Cutting Concerns

### Accessibility
- All forms meet WCAG 2.1 AA
- Keyboard navigation throughout (j/k, tab, enter, esc)
- Screen reader labels on all interactive elements
- High contrast mode support (follows system preference)

### Performance
- Triage queue: virtual scroll if >50 items
- Board: virtual columns if >100 cards
- Intent editor: debounced saves (500ms)
- Heatmap: lazy-render off-screen nodes

### Responsiveness
- Desktop-first (min-width: 1024px for full layout)
- Tablet: stack split-pane vertically, collapse board columns
- Mobile: not a target (pipeline management is a desktop activity)

---

## 9. Summary: Story Count by Feature

| Feature | Stories | Priority |
|---------|---------|----------|
| Issue Intake & Triage | 7 | Phase 2 |
| Intent Specification Editor | 9 | Phase 2 |
| Complexity & Risk Dashboard | 6 | Phase 2 |
| Expert Routing Preview | 6 | Phase 2 |
| Roadmap & Backlog Board | 11 | Phase 2 |
| Manual Task Creation | 6 | Phase 2 |
| **Total** | **45** | |

All features in this document belong to **Phase 2: Planning Experience** of the phasing strategy defined in the master vision document.
