# 02 — Pipeline Visualization Design Specification

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** Real-time visualization of the 9-stage pipeline, TaskPacket flow, gate transitions, live agent activity, and loopback rendering. Everything the developer sees while work is in progress.

---

## 1. Design Philosophy

The pipeline visualization answers three questions at a glance:
1. **Where is my work?** — Which stage is each TaskPacket in right now?
2. **Is it healthy?** — Are gates passing? Any loopbacks? Any stuck tasks?
3. **What's happening?** — What is the agent doing right now, and why?

Progressive disclosure is key: the top-level view is a clean pipeline rail. Click a stage for details. Click a TaskPacket for its timeline. Click a stage in the timeline for the activity log. Each level adds detail without overwhelming the default view.

---

## 2. Feature: Pipeline Rail (Primary View)

### 2.1 What It Does

A horizontal visualization showing all 9 pipeline stages with real-time status. This is the **home screen** of the dashboard — the first thing the developer sees.

### 2.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  PIPELINE                                          5 active · 2 queued · $4.20  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐              │
│  │INTAKE  │──▶│CONTEXT │──▶│ INTENT │──▶│ ROUTER │──▶│ASSEMBLE│              │
│  │        │   │        │   │        │   │        │   │        │              │
│  │  ○ 1   │   │  ● 1   │   │  ◉ 1   │   │  ○ 0   │   │  ○ 0   │              │
│  │  idle  │   │ active │   │ review │   │  idle  │   │  idle  │              │
│  └────────┘   └────────┘   └────────┘   └────────┘   └────────┘              │
│       │                                                    │                    │
│       │            ┌────────────────────────────────────────┘                   │
│       │            │                                                            │
│       │       ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐              │
│       │       │IMPLEMEN│──▶│ VERIFY │──▶│   QA   │──▶│PUBLISH │              │
│       │       │        │   │        │   │        │   │        │              │
│       │       │  ● 2   │   │  ● 1   │   │  ○ 0   │   │  ○ 0   │              │
│       │       │ active │   │ active │   │  idle  │   │  idle  │              │
│       │       └────────┘   └───┬────┘   └────────┘   └────────┘              │
│       │                        │                                               │
│       │                   ╭────┴────╮                                          │
│       │                   │LOOPBACK │ #139 → Implement                        │
│       │                   │ ⚠ 1     │ "test_rate_limit failed"                │
│       │                   ╰─────────╯                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Stage nodes:**
- Fixed 9-node layout (two rows of 4+5 or single scrollable row on wide screens)
- Each node shows: stage name, status icon (○ idle, ● active, ✓ passed, ✗ failed, ◉ awaiting review), count of TaskPackets currently in that stage
- Connecting arrows between stages (solid = normal flow, dashed = no active flow)
- Active stages glow or pulse subtly (CSS animation, paused when off-screen per Aperant's IntersectionObserver pattern)

**Loopback indicators:**
- When a gate fails and triggers a loopback, an arc appears from the failing stage back to the target stage
- Loopback badge shows: count, TaskPacket ID, brief reason
- Color: amber for in-progress loopback, red for repeated loopback (>1 on same packet)

**Header bar:**
- Active count (TaskPackets currently flowing)
- Queued count (in triage, waiting)
- Running cost total (sum of all active TaskPackets)

### 2.3 Interaction Patterns

- **Click stage node** → opens Stage Detail panel (right side)
- **Click TaskPacket count badge** → lists TaskPackets in that stage
- **Click loopback badge** → jumps to TaskPacket timeline at the failure point
- **Hover stage node** → tooltip with avg time in stage, pass rate, current TaskPacket titles
- **Keyboard:** arrow keys navigate between stages, Enter opens detail

### 2.4 Stage Detail Panel (Right Slide-In)

When a stage node is clicked:

```
┌──────────────────────────────────────┐
│  IMPLEMENT STAGE              ✕ close│
├──────────────────────────────────────┤
│                                      │
│  Status: ● Active (2 tasks)         │
│  Avg time: 8.3 min                  │
│  Pass rate: 91% (last 30 days)      │
│                                      │
│  ── Active TaskPackets ────────────  │
│                                      │
│  #139 API rate limiting              │
│  ████████████░░░░ 73%               │
│  Agent: Primary · Model: opus-4     │
│  Cost so far: $1.80                 │
│  [ View Timeline → ]                │
│                                      │
│  #142 Login timeout fix              │
│  ████░░░░░░░░░░░░ 22%              │
│  Agent: Primary · Model: sonnet-4   │
│  Cost so far: $0.40                 │
│  [ View Timeline → ]                │
│                                      │
│  ── Stage Metrics ─────────────────  │
│  Today:    3 passed, 0 failed       │
│  This week: 18 passed, 2 failed     │
│  Avg cost:  $1.40/task              │
│                                      │
└──────────────────────────────────────┘
```

- Active TaskPackets with progress bars and current model/agent info
- Stage-level metrics (pass rate, avg cost, throughput)
- "View Timeline" link to the full TaskPacket timeline view

### 2.5 Real-Time Updates

- Pipeline Rail updates via SSE (Server-Sent Events) from FastAPI
- Events: `stage_enter`, `stage_exit`, `gate_pass`, `gate_fail`, `loopback_start`, `loopback_resolve`
- Animation: TaskPacket "moves" between stages with a brief transition (dot slides along the arrow)
- Loopback arcs animate in when they occur, fade out when resolved

**Data flow:**
```
Temporal workflow activities → NATS JetStream events → FastAPI SSE endpoint → Browser EventSource → React state → Pipeline Rail re-render
```

### 2.6 Inspiration

| Element | Source | Adaptation |
|---------|--------|------------|
| Node-and-arrow pipeline | GitHub Actions workflow graph | 9 fixed nodes instead of dynamic DAG |
| Real-time node status | Temporal UI Compact View | Stage status + TaskPacket count |
| Loopback arcs | Custom (no direct inspiration) | Unique to TheStudio's gate model |
| Stage detail panel | Linear's right-panel detail view | Slide-in panel with metrics |
| Pulse animation | Aperant's PhaseProgressIndicator | IntersectionObserver for performance |

### 2.7 Stories for Epic Decomposition

- S1: Static 9-node pipeline layout with connecting arrows
- S2: Stage node status rendering (idle/active/review icons, TaskPacket counts)
- S3: Stage detail panel (slide-in right) with TaskPacket list
- S4: SSE infrastructure (FastAPI endpoint + NATS bridge)
- S5: Real-time stage status updates via SSE
- S6: TaskPacket transition animation (dot slides between nodes)
- S7: Loopback arc rendering with badge
- S8: Header bar (active/queued counts, running cost)
- S9: Stage metrics (pass rate, avg time, throughput)
- S10: Hover tooltips on all stage nodes
- S11: Keyboard navigation between stages

---

## 3. Feature: TaskPacket Timeline

### 3.1 What It Does

A detailed timeline view for a single TaskPacket showing every stage it has passed through, with duration, gate results, and the ability to drill into any stage.

### 3.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TASKPACKET #139 — API Rate Limiting                                        │
│  Status: Implement (73%)  ·  Total time: 14m  ·  Total cost: $2.60         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ── TIMELINE ───────────────────────────────────────────────────────────    │
│                                                                             │
│  10:42    INTAKE              ██ 12s                                        │
│           ✓ Gate passed       Webhook received, eligibility confirmed       │
│                                                                             │
│  10:42    CONTEXT             ████████ 2m 14s                              │
│           ✓ Gate passed       6 files analyzed, 2 risk flags               │
│                                                                             │
│  10:44    INTENT              ██████████████ 3m 48s                        │
│           ◉ Developer review  Intent spec v2 approved by developer         │
│           ✓ Gate passed       3 constraints, 4 acceptance criteria          │
│                                                                             │
│  10:48    ROUTER              ██ 8s                                        │
│           ✓ Gate passed       3 experts selected (API, Error, Test)        │
│                                                                             │
│  10:48    ASSEMBLER           ████ 1m 02s                                  │
│           ✓ Gate passed       Expert outputs merged, 2 conflicts resolved  │
│                                                                             │
│  10:49    IMPLEMENT           ████████████████████████████░░░░░ 73%        │
│           ● In progress       Primary Agent · opus-4 · $1.80 so far       │
│           │                                                                │
│           ├─ 10:49  Reading src/api/rate_limit.py                         │
│           ├─ 10:50  Implementing RateLimiter class                         │
│           ├─ 10:52  Writing tests/api/test_rate_limit.py                  │
│           ├─ 10:54  Running pytest (3 passed, 1 failed)                   │
│           └─ 10:55  Fixing test_concurrent_requests...                    │
│                                                                             │
│  ·····    VERIFY              ░░░░░░░░░░ (queued)                          │
│  ·····    QA                  ░░░░░░░░░░ (queued)                          │
│  ·····    PUBLISH             ░░░░░░░░░░ (queued)                          │
│                                                                             │
│  ── LOOPBACK HISTORY ──────────────────────────────────────────────────    │
│  (none)                                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Header** — TaskPacket ID, title, current status with progress %, total elapsed time, total cost.

2. **Stage bars** — Vertical timeline with horizontal duration bars per stage. Bar width proportional to time spent. Color-coded: green (passed), blue (in progress), gray (queued), red (failed), amber (loopback).

3. **Gate results** — Inline under each stage bar: pass/fail icon, brief summary. Click to expand full gate evidence.

4. **Activity preview** — For the currently active stage, shows the last 5 activity entries inline (most recent at bottom). This gives a "what's happening now" view without needing the full activity stream.

5. **Loopback history** — If the TaskPacket has looped back, shows each loopback: from stage, to stage, reason, outcome.

6. **Queued stages** — Dashed/gray bars for stages not yet reached. Shows "(queued)" label.

### 3.3 Temporal UI Inspiration

Temporal UI's Timeline View is the primary inspiration:

| Temporal UI Feature | TheStudio Adaptation |
|---------------------|----------------------|
| Duration-based horizontal bars | Stage bars with proportional widths |
| Green/red color coding | Green/blue/gray/red/amber palette |
| Hover for exact timestamps | Click for gate evidence + activity log |
| Child workflow expansion | Stage drill-down to activity stream |
| Real-time liveness | SSE updates append new activity entries |

**Key difference:** Temporal shows individual events (activities, timers). TheStudio groups events into pipeline stages and shows gate transitions as first-class elements.

**Reference:** [Temporal Timeline View](https://temporal.io/blog/lets-visualize-a-workflow), [temporal-flow-web](https://github.com/itaisoudry/temporal-flow-web)

### 3.4 Interaction Patterns

- **Click a completed stage bar** → expands to show full gate evidence (what was checked, what passed, what failed, evidence artifacts)
- **Click the active stage bar** → expands to show the full live activity stream (see Feature 4 below)
- **Click a loopback entry** → jumps to the failure point in the timeline with the gate failure highlighted
- **Hover a stage bar** → tooltip with exact start/end timestamps, model used, cost for that stage
- **Scrubbing** (future enhancement): slider at the bottom to scrub through the timeline like Devin's replay

### 3.5 Stories for Epic Decomposition

- S1: Vertical timeline layout with stage bars (static rendering from TaskPacket data)
- S2: Duration-proportional bar widths with color coding
- S3: Gate result display (pass/fail icon + summary) under each bar
- S4: Active stage activity preview (last 5 entries)
- S5: Click-to-expand gate evidence for completed stages
- S6: Click-to-expand full activity stream for active stage
- S7: Loopback history section
- S8: Real-time SSE updates (new entries append, bar grows)
- S9: Header with status, elapsed time, total cost
- S10: Queued stage rendering (dashed/gray)
- S11: Hover tooltips with timestamps and cost

---

## 4. Feature: Live Agent Activity Stream

### 4.1 What It Does

A real-time feed of structured log entries showing what the agent is doing during the Implement, Verify, or QA stages. Not a raw terminal — a parsed, categorized, human-readable activity stream.

### 4.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────┐
│  ACTIVITY — #139 Implement Stage              ● Live   🔍 Filter│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ▼ CONTEXT GATHERING                              10:49 - 10:50│
│    📄 Read src/api/rate_limit.py                        10:49:12│
│    📄 Read src/api/middleware.py                         10:49:15│
│    🔍 Grep "rate" in src/api/                           10:49:18│
│    📄 Read tests/api/test_middleware.py                  10:49:22│
│                                                                 │
│  ▼ IMPLEMENTATION                                 10:50 - 10:54│
│    ✏️  Edit src/api/rate_limit.py                        10:50:03│
│    │   + class RateLimiter:                                     │
│    │   +     def __init__(self, max_requests: int, ...          │
│    │   ... (12 more lines)                      [ Show full ▼ ] │
│    │                                                            │
│    ✏️  Create src/api/token_bucket.py                    10:51:44│
│    │   New file (47 lines)                      [ Show full ▼ ] │
│    │                                                            │
│    ✏️  Edit src/api/middleware.py                         10:52:30│
│    │   + from .rate_limit import RateLimiter                    │
│    │   ... (3 more lines)                       [ Show full ▼ ] │
│                                                                 │
│  ▼ TESTING                                        10:52 - now  │
│    ✏️  Create tests/api/test_rate_limit.py               10:52:55│
│    │   New file (89 lines)                      [ Show full ▼ ] │
│    │                                                            │
│    🧪 pytest tests/api/test_rate_limit.py                10:53:40│
│    │   3 passed, 1 failed                                       │
│    │   ✗ test_concurrent_requests — AssertionError:             │
│    │     expected 429, got 200                  [ Show full ▼ ] │
│    │                                                            │
│    💭 Agent reasoning:                                   10:54:02│
│    │   "The rate limiter isn't thread-safe. Need to add         │
│    │    a lock around the token bucket check..."                │
│    │                                                            │
│    ✏️  Edit src/api/token_bucket.py                      10:54:15│
│    │   + import threading                                       │
│    │   + self._lock = threading.Lock()                          │
│    │   ... (4 more lines)                       [ Show full ▼ ] │
│    │                                                            │
│    🧪 pytest tests/api/test_rate_limit.py ●              10:55:01│
│    │   Running...                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Entry types and icons:**

| Type | Icon | Description |
|------|------|-------------|
| File read | 📄 | Agent reading a file |
| File edit | ✏️ | Agent modifying or creating a file |
| Search | 🔍 | Agent searching (grep, glob) |
| Test run | 🧪 | Agent running tests |
| Shell command | 💻 | Agent running a shell command |
| Reasoning | 💭 | Agent's thinking/planning text |
| Error | ❌ | Error occurred |
| Success | ✅ | Step completed successfully |
| LLM call | 🤖 | API call to model (shows model name, token count) |

**Subphase grouping:**
- Entries are grouped under collapsible subphases (CONTEXT GATHERING, IMPLEMENTATION, TESTING, etc.)
- Each subphase shows a time range
- Collapse/expand with ▶/▼ toggle

**Detail expansion:**
- File edits show a preview (first 3 lines of diff) with "Show full" to expand
- Test failures show the error message with "Show full" for the stack trace
- All entries have timestamps (HH:MM:SS format, relative to stage start)

### 4.3 Streaming Protocol

Activity entries arrive via SSE as structured JSON chunks:

```typescript
interface ActivityChunk {
  task_id: string;
  stage: 'implement' | 'verify' | 'qa';
  timestamp: string;           // ISO 8601
  type: 'file_read' | 'file_edit' | 'search' | 'test_run' | 'shell' | 'reasoning' | 'error' | 'success' | 'llm_call';
  subphase?: string;           // e.g., "CONTEXT GATHERING"
  content: string;             // Primary display text
  detail?: string;             // Expandable full content
  metadata?: {
    file_path?: string;
    diff_preview?: string;     // First 3 lines of diff
    test_results?: { passed: number; failed: number; errors: string[] };
    model?: string;
    tokens?: { input: number; output: number };
    cost?: number;
  };
}
```

**Reference:** Aperant's `TaskLogStreamChunk` interface — similar structure with type, content, phase, tool metadata. Our adaptation adds subphase grouping and richer metadata.

### 4.4 Performance

- Max 5,000 entries per stream (matches Aperant's limit)
- Virtual scrolling for long streams (only render visible entries)
- Auto-scroll when user is at bottom; preserve position when user scrolls up (Aperant's smart auto-scroll pattern with 100px threshold)
- IntersectionObserver pauses animations when the stream is off-screen
- Entries batch-render (50ms debounce on incoming SSE to avoid per-entry re-renders)

### 4.5 Filter Bar

- Filter by entry type (toggle icons on/off)
- Search within entries (text search across content + detail)
- Show/hide reasoning entries (toggle — some developers find agent thinking noisy)
- Show/hide LLM call entries (toggle — useful for cost debugging)

### 4.6 Stories for Epic Decomposition

- S1: Activity stream container with basic entry rendering
- S2: Entry type icons and formatting (file read, edit, search, test, etc.)
- S3: Subphase grouping with collapsible sections
- S4: Detail expansion (show full diff, stack trace, etc.)
- S5: SSE connection and real-time entry appending
- S6: Smart auto-scroll (preserve position when scrolled up)
- S7: Virtual scrolling for long streams (>500 entries)
- S8: Filter bar (type toggles, text search)
- S9: File edit diff preview (first 3 lines)
- S10: Test result formatting (pass/fail counts, error messages)
- S11: Agent reasoning entries with distinct styling

---

## 5. Feature: Gate Inspector

### 5.1 What It Does

A dedicated view for examining gate transitions across all TaskPackets. Shows what was checked, what passed, what failed, and the evidence behind each decision. Makes the "gates fail closed" principle visible and auditable.

### 5.2 Look and Feel

**Gate Inspector — List View:**

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE INSPECTOR                           Filter: [ All ▼ ]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✓ #142 Intent → Router              10:48    0 issues          │
│    Intent spec approved (developer reviewed)                    │
│                                                                 │
│  ✓ #139 Assembler → Implement        10:48    0 issues          │
│    Expert outputs merged, provenance verified                   │
│                                                                 │
│  ✗ #139 Verify → QA                  10:53    2 issues          │
│    ⚠ test_concurrent_requests failed (AssertionError)          │
│    ⚠ ruff check: 1 warning (unused import)                    │
│    → Loopback to Implement                                     │
│                                                                 │
│  ✓ #137 QA → Publish                 09:32    0 issues          │
│    All acceptance criteria validated                            │
│                                                                 │
│  ✓ #137 Publish → Done               09:33    0 issues          │
│    Draft PR #287 created, evidence comment posted               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Gate Inspector — Detail View (click a gate entry):**

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE: #139 Verify → QA                        FAILED          │
│  Timestamp: 2026-03-20 10:53:22                                │
│  Decision: Loopback to Implement                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ── CHECKS PERFORMED ──────────────────────────────────────    │
│                                                                 │
│  ✓ Ruff lint                                                   │
│    Command: ruff check src/api/rate_limit.py src/api/token_..  │
│    Result: 1 warning (W0611: unused import 'os')               │
│    Severity: warning (non-blocking)                            │
│                                                                 │
│  ✓ Type check                                                  │
│    Command: mypy src/api/rate_limit.py                         │
│    Result: clean                                               │
│                                                                 │
│  ✗ Pytest                                                      │
│    Command: pytest tests/api/test_rate_limit.py -v             │
│    Result: 3 passed, 1 failed                                  │
│    ┌──────────────────────────────────────────────────────┐    │
│    │ FAILED test_concurrent_requests                      │    │
│    │ AssertionError: expected status 429, got 200         │    │
│    │                                                      │    │
│    │ > assert response.status_code == 429                 │    │
│    │ E assert 200 == 429                                  │    │
│    │                                                      │    │
│    │ tests/api/test_rate_limit.py:67: AssertionError      │    │
│    └──────────────────────────────────────────────────────┘    │
│                                                                 │
│  ✓ Security scan                                               │
│    Command: bandit -r src/api/rate_limit.py                    │
│    Result: No issues found                                     │
│                                                                 │
│  ── GATE DECISION ─────────────────────────────────────────    │
│  Rule: All pytest tests must pass (fail-closed)                │
│  Action: Loopback to Implement with defect report              │
│  Defect category: functional_failure                           │
│  Defect detail: test_concurrent_requests assertion failure     │
│                                                                 │
│  ── EVIDENCE ARTIFACT ─────────────────────────────────────    │
│  [ View full verification report → ]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Gate list** — Chronological list of all gate transitions across all TaskPackets. Each entry: pass/fail icon, TaskPacket ID, transition (from → to), timestamp, issue count.

2. **Gate detail** — Expanded view showing: every check performed (lint, type, test, security), results for each check, the gate decision rule that triggered, the action taken, defect categorization (from TheStudio's defect taxonomy), link to full evidence artifact.

3. **Filters** — Filter by: pass/fail, TaskPacket, stage, date range, defect category.

### 5.3 Gate Health Metrics

A summary panel at the top of the Gate Inspector:

```
┌──────────────┬──────────────┬──────────────┬──────────────────┐
│ Pass Rate    │ Avg Issues   │ Top Failure  │ Loopback Rate    │
│ 87% (30d)   │ 0.4/gate     │ pytest (62%) │ 13% of packets   │
│ ▲ 3% vs last│              │              │ ▼ 2% vs last     │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

### 5.4 Inspiration

| Element | Source | Adaptation |
|---------|--------|------------|
| Check result detail | GitHub Actions check run output | Structured per-check results instead of raw logs |
| Gate decision rules | TheStudio's existing gate model | Surfaced in UI with rule explanation |
| Defect taxonomy | TheStudio's QA defect taxonomy | Category badges on failed gates |
| Evidence links | TheStudio's evidence comments | Link to full artifact from gate card |
| Health metrics | Codegen's PR analytics | Pass rate, failure distribution, trends |

### 5.5 Stories for Epic Decomposition

- S1: Gate list view (chronological, all TaskPackets)
- S2: Gate detail view (checks performed, results, decision)
- S3: Test failure rendering (formatted error output, stack traces)
- S4: Filter bar (pass/fail, TaskPacket, stage, date range)
- S5: Gate health metrics summary panel
- S6: Defect category badges and taxonomy display
- S7: Evidence artifact links
- S8: Real-time SSE updates (new gate events appear)

---

## 6. Feature: Loopback Visualization

### 6.1 What It Does

Loopbacks are TheStudio's self-healing mechanism — when a gate fails, the TaskPacket loops back to an earlier stage with a defect report. This feature makes loopbacks visible, traceable, and understandable.

### 6.2 Look and Feel

On the Pipeline Rail (Feature 2), loopbacks appear as animated arcs:

```
                    ╭──── LOOPBACK ────╮
                    │                  │
  IMPLEMENT ──▶ VERIFY ──▶ QA     PUBLISH
                    │
                    ▼
              #139: pytest failure
              "test_concurrent_requests"
              Attempt 1 of 3
```

On the TaskPacket Timeline (Feature 3), loopbacks appear as backward entries:

```
  10:49    IMPLEMENT (attempt 1)    ████████████ 4m
           ✓ Gate passed

  10:53    VERIFY                    ████ 1m
           ✗ Gate failed — pytest: 1 failure
           ↩ Loopback to Implement

  10:54    IMPLEMENT (attempt 2)    ████████░░░░ 62%
           ● In progress — fixing test_concurrent_requests
```

**Visual cues:**
- Loopback arc: dashed amber line with animated "pulse" traveling backward
- Attempt counter: "attempt 1 of 3" (max loopbacks configurable)
- Escalation: if max loopbacks reached, the arc turns red and shows "ESCALATED — needs human review"
- Resolution: when the loopback succeeds, the arc fades to green briefly, then disappears

### 6.3 Stories for Epic Decomposition

- S1: Loopback arc on Pipeline Rail (animated, with badge)
- S2: Loopback entries in TaskPacket Timeline (backward arrows, attempt counter)
- S3: Escalation indicator (max loopbacks reached)
- S4: Loopback resolution animation
- S5: Loopback history panel (all loopbacks for a TaskPacket)

---

## 7. Feature: Active TaskPacket Minimap (Bottom Bar)

### 7.1 What It Does

A persistent bottom bar showing all in-flight TaskPackets as compact cards, visible from any view. Allows quick switching between active tasks.

### 7.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ● #142 Login timeout  │ ● #139 API rate limit │ ◉ #143 Dark mode      │
│   Implement 22%       │   Implement 73%       │   Intent (review)     │
│   $0.40               │   $2.60               │   $0.10               │
└─────────────────────────────────────────────────────────────────────────┘
```

- Fixed to bottom of viewport (always visible)
- Each card: status dot, ID + title (truncated), current stage + progress, cost
- Click card → navigates to that TaskPacket's timeline
- Cards scroll horizontally if more than ~5 active
- Collapsible (click toggle to minimize to just the count)

### 7.3 Stories for Epic Decomposition

- S1: Bottom bar container with horizontal card layout
- S2: TaskPacket mini-cards (status, title, stage, cost)
- S3: Click-to-navigate to TaskPacket timeline
- S4: Horizontal scroll for overflow
- S5: Collapse/expand toggle

---

## 8. Cross-Cutting: Real-Time Infrastructure

### 8.1 SSE Event Architecture

All real-time updates flow through a single SSE endpoint:

```
GET /api/v1/events/stream
Accept: text/event-stream

Events:
  event: pipeline.stage_enter
  data: {"task_id": "142", "stage": "implement", "timestamp": "..."}

  event: pipeline.stage_exit
  data: {"task_id": "142", "stage": "implement", "gate_result": "pass", ...}

  event: pipeline.gate_fail
  data: {"task_id": "139", "stage": "verify", "defect": {...}, "loopback_to": "implement"}

  event: pipeline.activity
  data: {"task_id": "139", "stage": "implement", "type": "file_edit", "content": "...", ...}

  event: pipeline.cost_update
  data: {"task_id": "139", "cost_delta": 0.02, "total_cost": 2.62}
```

### 8.2 Data Flow

```
Temporal Workflow Activities
    → emit events to NATS JetStream (subjects: pipeline.stage.*, pipeline.gate.*, pipeline.activity.*)
    → FastAPI SSE handler subscribes to NATS subjects
    → Filters by active client subscriptions
    → Sends SSE events to connected browsers
    → React components update via EventSource + Zustand store
```

### 8.3 Reconnection

- SSE auto-reconnects on disconnect (browser-native EventSource behavior)
- On reconnect, client sends `Last-Event-ID` header
- Server replays missed events from NATS JetStream (replay by sequence)
- If gap is too large (>1000 events), server sends a `full_state` event instead

---

## 9. Summary: Story Count by Feature

| Feature | Stories | Priority |
|---------|---------|----------|
| Pipeline Rail | 11 | Phase 1 |
| TaskPacket Timeline | 11 | Phase 1 |
| Live Agent Activity Stream | 11 | Phase 1 |
| Gate Inspector | 8 | Phase 1 |
| Loopback Visualization | 5 | Phase 1 |
| Active TaskPacket Minimap | 5 | Phase 1 |
| Real-Time Infrastructure (SSE) | (cross-cutting, in S4/S5 of Pipeline Rail) | Phase 1 |
| **Total** | **51** | |

All features in this document belong to **Phase 1: Pipeline Visibility** of the phasing strategy. This is the foundation — everything else builds on visible pipeline state.
