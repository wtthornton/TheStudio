# 04 — GitHub Integration & Analytics Design Specification

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** Deep GitHub integration (bidirectional Projects sync, PR evidence explorer, issue import/triage), operational analytics, and the webhook real-time bridge. Everything that connects TheStudio to the GitHub ecosystem and measures pipeline effectiveness.

---

## 1. Design Philosophy

GitHub is where the developer's team lives. TheStudio should enhance the GitHub experience, not replace it. Bidirectional sync means the developer can use either TheStudio's dashboard or GitHub's native tools — both stay consistent. Evidence should appear on PRs where reviewers already look, and pipeline state should be visible in GitHub Projects where managers already plan.

---

## 2. Feature: Bidirectional GitHub Projects Sync

### 2.1 What It Does

Syncs TheStudio's TaskPackets with a GitHub Projects v2 board so that pipeline state is visible natively in GitHub without requiring access to TheStudio's dashboard.

### 2.2 Sync Model

```
TheStudio TaskPacket                     GitHub Projects v2 Item
───────────────────                      ────────────────────────
task_id                          ←→      Item node ID
title                            ←→      Title
status (pipeline stage group)    ←→      Status field (custom single-select)
trust_tier                        →      Custom field: "Trust Tier"
cost                              →      Custom field: "Cost"
complexity                        →      Custom field: "Complexity"
github_issue_number              ←→      Linked Issue
```

**Direction:**
- **TheStudio → GitHub**: Pipeline stage, trust tier, cost, complexity push to GitHub Projects custom fields
- **GitHub → TheStudio**: Manual status changes on the GitHub board trigger webhook events that TheStudio respects (e.g., dragging a card to "Done" in GitHub triggers abort if task is still in pipeline)
- **Bidirectional**: Title changes, issue linking

### 2.3 Look and Feel — Sync Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│  GITHUB PROJECTS SYNC                          Settings > GitHub│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status: ✓ Connected                           [ Disconnect ]  │
│  Project: TheStudio Pipeline (#4)              [ Change ▼ ]    │
│  Last sync: 2m ago                                             │
│                                                                 │
│  ── FIELD MAPPING ─────────────────────────────────────────    │
│                                                                 │
│  TheStudio Stage Group  →  GitHub Status Field                 │
│  ─────────────────────────────────────────────                 │
│  Triage                 →  [ Triage ▼ ]                        │
│  Planning (Context→Rtr) →  [ Planning ▼ ]                      │
│  Building (Asm→Impl)    →  [ In Progress ▼ ]                  │
│  Verify (Verify→QA)     →  [ Review ▼ ]                       │
│  Done (Publish)         →  [ Done ▼ ]                          │
│  Rejected               →  [ Rejected ▼ ]                      │
│                                                                 │
│  ── CUSTOM FIELDS ─────────────────────────────────────────    │
│                                                                 │
│  ☑ Sync Trust Tier    →  field: "Trust Tier"   [ Create ▼ ]   │
│  ☑ Sync Cost          →  field: "Cost"         [ Create ▼ ]   │
│  ☑ Sync Complexity    →  field: "Complexity"   [ Create ▼ ]   │
│  ☐ Sync Model Used    →  (disabled)                            │
│                                                                 │
│  ── SYNC BEHAVIOR ─────────────────────────────────────────    │
│                                                                 │
│  ☑ Auto-add new TaskPackets to project                         │
│  ☑ Respect GitHub status changes (manual overrides)            │
│  ☐ Auto-close GitHub issues when TaskPacket completes          │
│  ☑ Add pipeline stage comments to linked issues                │
│                                                                 │
│  [ Test Sync ]  [ Force Full Sync ]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 GitHub Projects v2 API Details

The sync uses GitHub's GraphQL API:

**Adding an item:**
```graphql
mutation {
  addProjectV2ItemById(input: {
    projectId: "PVT_xxx"
    contentId: "I_xxx"  # Issue node ID
  }) {
    item { id }
  }
}
```

**Updating a custom field:**
```graphql
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_xxx"
    itemId: "PVTI_xxx"
    fieldId: "PVTF_xxx"
    value: { singleSelectOptionId: "xxx" }
  }) {
    projectV2Item { id }
  }
}
```

**Constraints (from research):**
- Cannot add and update in the same GraphQL call — requires two mutations
- Status field has limitations for programmatic editing in some configurations
- Requires PAT with `project` scope (standard `GITHUB_TOKEN` lacks it)
- View mutations (creating/editing views) are not available in the API
- `projects_v2_item` webhook event fires on item create/edit/delete

**Reference:** [GitHub Projects v2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects), [GraphQL Mutations Reference](https://docs.github.com/en/graphql/reference/mutations)

### 2.5 Stories for Epic Decomposition

- S1: GitHub Projects connection setup (OAuth, project selection)
- S2: Field mapping configuration UI
- S3: Custom field creation/selection for Trust Tier, Cost, Complexity
- S4: TheStudio → GitHub sync (push stage changes to project items)
- S5: GitHub → TheStudio sync (receive project item webhooks)
- S6: Auto-add new TaskPackets to GitHub project
- S7: Sync behavior configuration (checkboxes)
- S8: Test Sync and Force Full Sync actions
- S9: Sync status indicator and error handling

---

## 3. Feature: PR Evidence Explorer

### 3.1 What It Does

When a TaskPacket reaches Publish and a draft PR is created, the PR Evidence Explorer provides a rich view of the PR alongside its pipeline evidence — everything a reviewer needs to understand what was built, why, and how it was validated.

### 3.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PR EVIDENCE — #289 Fix login timeout handling                          │
│  TaskPacket #142 · Draft PR · 3 files changed, +47 -12                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Tabs: [ Evidence ] [ Diff ] [ Intent ] [ Gates ] [ Cost ]            │
│                                                                         │
│  ═══ EVIDENCE TAB (default) ═══════════════════════════════════════    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ## Evidence Comment                                            │   │
│  │                                                                 │   │
│  │  **Task:** Fix login timeout on slow connections (#142)         │   │
│  │  **Intent:** Show timeout message after 5s instead of blank     │   │
│  │  **Trust Tier:** Suggest (draft PR, developer approves)         │   │
│  │                                                                 │   │
│  │  ### What Changed                                               │   │
│  │  - Added `TimeoutHandler` class in `src/auth/timeout.py`       │   │
│  │  - Modified `LoginForm.submit()` to catch `TimeoutError`       │   │
│  │  - Added 3 tests covering timeout, retry, and normal flow      │   │
│  │                                                                 │   │
│  │  ### Validation Results                                         │   │
│  │  | Gate       | Result | Details                      |        │   │
│  │  |------------|--------|------------------------------|        │   │
│  │  | Ruff lint  | ✓ Pass | 0 issues                    |        │   │
│  │  | Type check | ✓ Pass | 0 errors                    |        │   │
│  │  | Pytest     | ✓ Pass | 6 passed, 0 failed          |        │   │
│  │  | Security   | ✓ Pass | No vulnerabilities           |        │   │
│  │  | QA Review  | ✓ Pass | All acceptance criteria met  |        │   │
│  │  |            |        |                              |        │   │
│  │  ### Provenance                                                 │   │
│  │  - Intent Spec: v2 (developer approved at 10:48)               │   │
│  │  - Experts: Auth Expert (0.92), Test Expert (0.95)             │   │
│  │  - Model: opus-4 (Implement), sonnet-4 (Verify)               │   │
│  │  - Total cost: $1.60                                           │   │
│  │  - Loopbacks: 0                                                │   │
│  │  - Pipeline time: 8m 32s                                       │   │
│  │                                                                 │   │
│  │  ---                                                            │   │
│  │  *Generated by TheStudio v0.x · Evidence ID: ev-142-abc123*    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  This evidence comment is also posted on the GitHub PR.                │
│                                                                         │
│  ── REVIEWER ACTIONS ──────────────────────────────────────────────    │
│                                                                         │
│  [ Approve & Merge ]  [ Request Changes ]  [ Close PR ]               │
│  [ View on GitHub → ]                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Tabs:**

1. **Evidence** (default) — The full evidence comment as rendered Markdown. Same content that's posted on the GitHub PR. Shows provenance chain: who/what produced each part.

2. **Diff** — Standard diff viewer showing all file changes. Annotations show which expert produced which change (color-coded by expert).

3. **Intent** — The Intent Specification that was used. Shows the final approved version with constraint checkboxes (all should be checked by this point).

4. **Gates** — Summary of all gate results for this TaskPacket (mirrors the Gate Inspector filtered to this task).

5. **Cost** — Per-stage and per-model cost breakdown for this TaskPacket.

### 3.3 Diff Annotations

In the Diff tab, each hunk is annotated with its source:

```
  src/auth/timeout.py (new file)
  ──────────────────────────────────
  Expert: Auth Expert (weight 0.92)

  + class TimeoutHandler:
  +     """Handle login timeout with user feedback."""
  +
  +     def __init__(self, timeout_seconds: int = 5):
  +         self.timeout_seconds = timeout_seconds
  ...

  tests/auth/test_timeout.py (new file)
  ──────────────────────────────────────
  Expert: Test Expert (weight 0.95)

  + def test_timeout_shows_message():
  ...
```

### 3.4 Reviewer Actions

- **Approve & Merge** — Calls GitHub API to approve and merge the PR. Only available if trust tier is Execute or developer explicitly overrides.
- **Request Changes** — Opens a text input for feedback. Sends feedback as a PR review comment AND creates a loopback signal to the pipeline.
- **Close PR** — Closes without merge. Records reason.
- **View on GitHub** — Opens the PR in a new browser tab.

### 3.5 Stories for Epic Decomposition

- S1: Evidence tab with rendered evidence comment
- S2: Diff tab with standard diff viewer
- S3: Diff annotations (expert attribution per hunk)
- S4: Intent tab (final Intent Specification)
- S5: Gates tab (gate results summary)
- S6: Cost tab (per-stage/per-model breakdown)
- S7: Approve & Merge action (GitHub API call)
- S8: Request Changes action (PR review comment + loopback signal)
- S9: Close PR action
- S10: View on GitHub link

---

## 4. Feature: Issue Import & Triage

### 4.1 What It Does

Beyond webhook-based intake, allows the developer to browse existing GitHub issues and selectively import them into TheStudio's pipeline.

### 4.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────┐
│  IMPORT ISSUES                                    [ Refresh ]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Repository: [ TheStudio ▼ ]   Filter: [ Open ▼ ] [ bug ▼ ]   │
│  Search: [ _______________________________________ ]  🔍       │
│                                                                 │
│  ☐  #150  Add webhook retry logic           bug    2h ago      │
│  ☐  #149  Dashboard shows wrong timezone    bug    5h ago      │
│  ☑  #148  Update README with new API docs   docs   1d ago      │
│  ☐  #147  Support GitLab webhooks           feat   2d ago      │
│  ☑  #146  Fix typo in error message         bug    2d ago      │
│  ☐  #145  Add dark mode to dashboard        feat   3d ago      │
│                                                                 │
│  Selected: 2 issues                                            │
│                                                                 │
│  Import as: ○ Triage (review before pipeline)                  │
│             ● Direct to Pipeline (skip triage)                 │
│                                                                 │
│  [ Cancel ]    [ Import 2 Issues ]                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Browse open issues with label and search filters
- Multi-select with checkboxes (Aperant's bulk selection pattern)
- Import mode: Triage (add to triage queue) or Direct (create TaskPacket and start pipeline immediately)
- Shows which issues are already imported (grayed out with "already in pipeline" label)
- Pagination for repos with many issues

### 4.3 Stories for Epic Decomposition

- S1: Issue list view (fetch from GitHub API, display with labels/age)
- S2: Search and filter controls (status, labels, text search)
- S3: Multi-select with checkboxes
- S4: Import action (create TaskPackets from selected issues)
- S5: Import mode selector (triage vs direct)
- S6: Already-imported detection (grayed out)
- S7: Pagination for large repos

---

## 5. Feature: Operational Analytics Dashboard

### 5.1 What It Does

Aggregate metrics across all pipeline activity. Answers: "How is the pipeline performing overall? Where are the bottlenecks? What's the trend?"

### 5.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS                                         Period: [ 30d ▼ ]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────┐│
│  │ Tasks Done    │ │ Avg Pipeline  │ │ PR Merge Rate │ │ Total Spend ││
│  │ 26            │ │ 11m 22s       │ │ 72%           │ │ $42.80      ││
│  │ ▲ 30% vs last │ │ ▼ 2m vs last  │ │ ▲ 8% vs last  │ │ ▲ 12% vs   ││
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────┘│
│                                                                         │
│  ── THROUGHPUT ────────────────────────────────────────────────────    │
│                                                                         │
│  Tasks/day:                                                            │
│   5 ┤  ╭─╮         ╭─╮                                                │
│   4 ┤  │ │  ╭─╮    │ │  ╭─╮  ╭─╮                                     │
│   3 ┤  │ │  │ │ ╭──╮│ │  │ │  │ │                                     │
│   2 ┤╭─╮│ │  │ │ │  ││ │  │ │  │ │                                    │
│   1 ┤│ ││ │  │ │ │  ││ │  │ │  │ │                                    │
│   0 ┼┴─┴┴─┴──┴─┴─┴──┴┴─┴──┴─┴──┴─┤                                  │
│      W1      W2      W3      W4                                       │
│                                                                         │
│  ── PIPELINE STAGE BOTTLENECKS ────────────────────────────────────    │
│                                                                         │
│  Avg time per stage (across all tasks):                                │
│  Intake     █ 8s                                                       │
│  Context    ████ 1m 45s                                                │
│  Intent     ████████ 3m 20s  ← longest (includes developer review)    │
│  Router     █ 6s                                                       │
│  Assembler  ██ 48s                                                     │
│  Implement  ████████████████ 7m 12s  ← most variable                  │
│  Verify     ███ 1m 10s                                                 │
│  QA         █████ 2m 30s                                               │
│  Publish    █ 12s                                                      │
│                                                                         │
│  ── CATEGORY BREAKDOWN ────────────────────────────────────────────    │
│                                                                         │
│  Bug fixes:     12 tasks · 89% merged · $1.20 avg · 8m avg            │
│  Features:       8 tasks · 62% merged · $2.80 avg · 18m avg           │
│  Refactors:      4 tasks · 75% merged · $1.60 avg · 12m avg           │
│  Docs:           2 tasks · 100% merged · $0.40 avg · 4m avg           │
│                                                                         │
│  ── FAILURE ANALYSIS ──────────────────────────────────────────────    │
│                                                                         │
│  Gate failures by stage:                                               │
│  Verify:   14 failures (62%)  — pytest: 9, ruff: 3, security: 2      │
│  QA:        6 failures (27%)  — acceptance criteria: 4, regression: 2 │
│  Intent:    2 failures  (9%)  — developer rejected spec               │
│  Router:    0 failures  (0%)                                           │
│                                                                         │
│  Most common failure: pytest assertion errors in Verify stage          │
│  Trend: ▼ decreasing (14 → 10 over 30d)                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Summary cards** — Tasks completed, avg pipeline time, PR merge rate, total spend. Each with trend indicator.

2. **Throughput chart** — Tasks per day/week as a bar chart. Shows pipeline capacity and utilization.

3. **Stage bottleneck analysis** — Horizontal bars showing average time per stage. Highlights the longest and most variable stages. Intent is often longest because it includes developer review time.

4. **Category breakdown** — Performance by task category (bug, feature, refactor, docs). Shows task count, merge rate, avg cost, avg time per category. Helps the developer understand where the pipeline works best.

5. **Failure analysis** — Gate failures grouped by stage and failure type. Trend indicator. Most common failure highlighted. Helps identify systematic issues.

### 5.3 Data Sources

- All metrics computed from TaskPacket data in PostgreSQL
- Stage timing from Temporal workflow event history
- Gate failures from verification/QA result records
- PR merge status from GitHub webhook events
- Cost from model_spend records

### 5.4 Inspiration

| Element | Source | Adaptation |
|---------|--------|------------|
| Throughput chart | Codegen PR analytics | Tasks/day instead of PRs/day |
| Bottleneck analysis | Temporal UI timeline aggregation | Per-stage averages across all tasks |
| Category breakdown | Linear's cycle analytics | Grouped by task category |
| Failure analysis | GitHub Actions failure insights | Per-stage, per-type failure breakdown |
| Summary cards | Mission Control dashboard | Four key metrics with trends |

### 5.5 Stories for Epic Decomposition

- S1: Summary cards (tasks done, avg time, merge rate, spend)
- S2: Throughput chart (tasks per day/week)
- S3: Stage bottleneck horizontal bars
- S4: Category breakdown table
- S5: Failure analysis (failures by stage and type)
- S6: Period selector (7d, 30d, 90d, custom)
- S7: Trend calculations (vs previous period)
- S8: Backend: analytics aggregation queries

---

## 6. Feature: Webhook Real-Time Bridge

### 6.1 What It Does

Bridges GitHub webhook events into TheStudio's real-time event stream so that external actions (PR reviews, issue comments, branch pushes) appear in the dashboard immediately.

### 6.2 Architecture

```
GitHub Webhook Events
    → POST /webhook/github (existing: src/ingress/webhook_handler.py)
    → Parse event type and payload
    → Publish to NATS JetStream (subject: github.event.*)
    → FastAPI SSE handler includes github events in the stream
    → Dashboard updates in real-time

Events bridged:
    github.pr.reviewed       → Show review status on PR Evidence Explorer
    github.pr.merged         → Move TaskPacket to Done, update board
    github.pr.closed         → Mark TaskPacket as rejected/closed
    github.issue.commented   → Show comment in triage queue
    github.issue.labeled     → Update triage card labels
    github.check.completed   → Show CI status on Pipeline Rail
```

### 6.3 Stories for Epic Decomposition

- S1: GitHub webhook event parsing (extend existing handler)
- S2: NATS JetStream publishing for GitHub events
- S3: SSE bridge for GitHub events to browser
- S4: PR status updates in PR Evidence Explorer
- S5: Board updates from GitHub events (PR merge → Done)
- S6: Issue comment/label updates in triage queue

---

## 7. Feature: GitHub Issue Pipeline Comments

### 7.1 What It Does

Posts structured status comments on the original GitHub issue as the TaskPacket progresses through the pipeline. Keeps stakeholders informed without needing access to TheStudio.

### 7.2 Comment Template

```markdown
## TheStudio Pipeline Update

**Status:** ✅ Implement (73% complete)
**Trust Tier:** Suggest (draft PR will be created)

### Progress
| Stage | Status | Time |
|-------|--------|------|
| Intake | ✅ Pass | 12s |
| Context | ✅ Pass | 2m 14s |
| Intent | ✅ Approved | 3m 48s |
| Router | ✅ Pass | 8s |
| Assembler | ✅ Pass | 1m 02s |
| **Implement** | **🔄 In Progress** | **5m 30s** |
| Verify | ⏳ Queued | — |
| QA | ⏳ Queued | — |
| Publish | ⏳ Queued | — |

**Cost so far:** $2.60 · **Model:** opus-4

---
*Updated by TheStudio · [View in dashboard →](link)*
```

**Behavior:**
- Comment created when TaskPacket enters Context stage
- Updated (edited, not new comment) at each stage transition
- Final update when PR is created (includes PR link)
- Configurable: can be disabled per-repo in settings
- Uses a single comment (edited in place) to avoid comment spam

### 7.3 Stories for Epic Decomposition

- S1: Pipeline status comment creation on GitHub issue
- S2: Comment update at each stage transition
- S3: Final comment update with PR link
- S4: Comment enable/disable configuration
- S5: Comment template rendering from TaskPacket data

---

## 8. Summary: Story Count by Feature

| Feature | Stories | Priority |
|---------|---------|----------|
| Bidirectional GitHub Projects Sync | 9 | Phase 4 |
| PR Evidence Explorer | 10 | Phase 4 |
| Issue Import & Triage | 7 | Phase 4 |
| Operational Analytics Dashboard | 8 | Phase 5 |
| Webhook Real-Time Bridge | 6 | Phase 4 |
| GitHub Issue Pipeline Comments | 5 | Phase 4 |
| **Total** | **45** | |

GitHub integration features belong to **Phase 4**. Analytics belongs to **Phase 5** (requires sufficient historical data).
