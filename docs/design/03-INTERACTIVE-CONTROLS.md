# 03 — Interactive Controls & Governance Design Specification

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** Trust tier configuration, pipeline steering controls (pause/retry/redirect/abort), budget governance, and the reputation dashboard. Everything that lets the developer control how autonomously the pipeline operates.

---

## 1. Design Philosophy

TheStudio's trust model is its deepest differentiator. No other tool in the market offers graduated autonomy with formal evidence requirements. But trust tiers are meaningless if the developer can't see them, configure them, or understand why a decision was made.

**Goal:** Make trust visible and configurable. Let the developer increase autonomy gradually as the system earns trust, and pull back instantly when something goes wrong.

---

## 2. Feature: Trust Tier Configuration

### 2.1 What It Does

A settings panel where the developer defines rules governing how autonomously the pipeline operates. TheStudio's three trust tiers — **Observe**, **Suggest**, **Execute** — determine what happens at the Publish stage:

- **Observe**: Pipeline runs, produces a report, but creates no PR. Developer reviews the report and decides.
- **Suggest**: Pipeline creates a draft PR with evidence comment. Developer must approve and merge.
- **Execute**: Pipeline creates a PR, approves it, and merges it (if all gates pass and within configured bounds).

### 2.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────┐
│  TRUST CONFIGURATION                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Default Tier: [ Suggest ▼ ]                                   │
│                                                                 │
│  ── RULES ──────────────────────────────────────────────────   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Rule 1                                          Active │   │
│  │                                                         │   │
│  │  When:  Category is [ bug fix ▼ ]                       │   │
│  │  AND    Lines changed < [ 50     ]                      │   │
│  │  AND    All gates pass                                  │   │
│  │  AND    Cost < [ $2.00  ]                               │   │
│  │                                                         │   │
│  │  Then:  Tier = [ Execute ▼ ]                            │   │
│  │                                                         │   │
│  │  ✎ Edit  ⊘ Disable  🗑 Delete                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Rule 2                                          Active │   │
│  │                                                         │   │
│  │  When:  Category is [ feature ▼ ]                       │   │
│  │  AND    Complexity is [ high ▼ ]                        │   │
│  │                                                         │   │
│  │  Then:  Tier = [ Observe ▼ ]                            │   │
│  │                                                         │   │
│  │  ✎ Edit  ⊘ Disable  🗑 Delete                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [ + Add Rule ]                                                │
│                                                                 │
│  ── SAFETY BOUNDS ─────────────────────────────────────────    │
│                                                                 │
│  Maximum auto-merge lines:      [ 200    ]                     │
│  Maximum auto-merge cost:       [ $5.00  ]                     │
│  Maximum loopbacks before hold: [ 2      ]                     │
│  Require developer review for:                                 │
│    ☑ Database migrations                                       │
│    ☑ Security-sensitive files (src/auth/*, .env*)              │
│    ☑ CI/CD configuration                                       │
│    ☐ Test-only changes                                         │
│                                                                 │
│  ── ACTIVE TIER DISPLAY ───────────────────────────────────    │
│                                                                 │
│  Current pipeline behavior:                                    │
│  • Bug fixes < 50 lines, < $2, all gates pass → AUTO MERGE    │
│  • Complex features → REPORT ONLY (no PR)                      │
│  • Everything else → DRAFT PR (developer approves)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Default tier selector** — Dropdown (Observe / Suggest / Execute). Applies when no rule matches.

2. **Rule builder** — Conditional rules with "When... Then..." structure:
   - Conditions: category, complexity, lines changed, cost, specific file paths, loopback count, gate results
   - Each condition is a dropdown/input field on a row
   - "AND" conjunction between conditions (all must match)
   - Action: tier assignment (Observe / Suggest / Execute)
   - Rules are evaluated top-to-bottom; first match wins

3. **Safety bounds** — Hard limits that apply regardless of rules:
   - Max lines for auto-merge
   - Max cost for auto-merge
   - Max loopbacks before pipeline holds for review
   - Mandatory review file patterns (glob patterns for sensitive files)

4. **Active tier display** — A plain-English summary of how the current rules translate to behavior. Auto-generated from the rule set. Helps the developer understand the effective policy.

### 2.3 Interaction Patterns

- "Add Rule" opens an inline form with condition dropdowns and tier selector
- Rules are reorderable by drag (top-to-bottom priority)
- Each rule has Edit, Disable (grays out but preserves), Delete (with confirmation)
- Safety bounds auto-save on change (debounced)
- Changes take effect immediately on new TaskPackets; in-flight packets keep their assigned tier

### 2.4 Trust Tier Badge

Every TaskPacket displays its trust tier as a badge throughout the UI:

```
  🟢 EXECUTE    — Will auto-merge if all gates pass
  🟡 SUGGEST    — Will create draft PR for review
  🔴 OBSERVE    — Will produce report only
```

The badge appears on:
- Triage queue cards
- Backlog board cards
- TaskPacket timeline header
- Pipeline Rail (on active TaskPacket tooltips)
- PR evidence explorer

### 2.5 Inspiration

| Element | Source | Adaptation |
|---------|--------|------------|
| Rule builder UI | GitHub branch protection rules | Condition-based rules with dropdowns |
| Safety bounds | Aperant's per-project settings | Hard limits as guardrails |
| Tier badges | CI status badges | Color-coded trust level |
| Plain-English summary | GitHub Actions permissions summary | Auto-generated policy description |
| Graduated autonomy | Factory AI enterprise controls | Three tiers with conditional rules |

### 2.6 Stories for Epic Decomposition

- S1: Default tier selector (dropdown, persists to DB)
- S2: Rule builder UI (add/edit/delete rules with conditions)
- S3: Rule conditions: category, complexity, lines changed, cost
- S4: Rule conditions: file path patterns, loopback count, gate results
- S5: Rule ordering (drag to reorder, first-match-wins evaluation)
- S6: Safety bounds panel (max lines, max cost, max loopbacks)
- S7: Mandatory review file patterns (glob input)
- S8: Active tier display (auto-generated plain-English summary)
- S9: Trust tier badge on TaskPacket cards (all views)
- S10: Rule evaluation engine (backend: evaluate rules against TaskPacket metadata)
- S11: Audit log entry when tier is assigned or overridden

---

## 3. Feature: Pipeline Steering Controls

### 3.1 What It Does

Lets the developer intervene in the pipeline at any point — pause a TaskPacket, retry a failed stage, redirect to a different stage, or abort entirely. Each action is logged and auditable.

### 3.2 Look and Feel

Steering controls appear in two places:

**1. TaskPacket Timeline (context menu or action bar):**

```
┌──────────────────────────────────────────────────────────────┐
│  TASKPACKET #139 — API Rate Limiting                         │
│  Status: Implement (73%)                                     │
│                                                              │
│  Actions: [ ⏸ Pause ] [ 🔄 Retry Stage ] [ ↩ Redirect ]    │
│           [ ⏹ Abort ] [ 🔒 Hold at Next Gate ]              │
│                                                              │
│  ...timeline content...                                      │
└──────────────────────────────────────────────────────────────┘
```

**2. Pipeline Rail (right-click context menu on a stage node):**

```
  ┌─────────────────────────┐
  │ Stage: Implement        │
  │ ────────────────────    │
  │ ⏸ Pause all in stage    │
  │ 🔄 Retry last failure   │
  │ ⏹ Abort all in stage    │
  │ 🔒 Hold at exit gate    │
  └─────────────────────────┘
```

### 3.3 Actions

| Action | What It Does | Confirmation Required | Reversible |
|--------|-------------|----------------------|------------|
| **Pause** | Freezes the TaskPacket at its current step. Agent stops. Can resume later. | No (instant, low risk) | Yes (Resume button appears) |
| **Resume** | Continues a paused TaskPacket from where it stopped. | No | N/A |
| **Retry Stage** | Re-runs the current or last-failed stage from the beginning. Clears stage artifacts. | Yes ("This will discard current stage progress. Continue?") | No |
| **Redirect** | Sends the TaskPacket to a specific earlier stage (e.g., back to Intent for re-planning). | Yes ("Redirect to [stage]? Stages after [stage] will re-run.") | No |
| **Abort** | Kills the TaskPacket entirely. Records reason. | Yes ("Abort #139? This cannot be undone." + reason text input) | No |
| **Hold at Next Gate** | Lets the current stage finish but pauses before the gate evaluation. Developer reviews, then releases. | No | Yes (Release button appears) |

**Redirect modal:**

```
┌─────────────────────────────────────────────────────────────┐
│  REDIRECT TASKPACKET #139                              ✕    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Current stage: Implement                                   │
│                                                             │
│  Redirect to:                                               │
│  ○ Context    — Re-analyze affected files and context       │
│  ○ Intent     — Re-generate intent specification            │
│  ● Router     — Re-select experts                          │
│  ○ Assembler  — Re-merge expert outputs                    │
│                                                             │
│  Reason (required):                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Wrong experts selected — needs database expert      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ⚠ Stages after Router will re-run. Progress in Implement  │
│    and later stages will be discarded.                      │
│                                                             │
│              [ Cancel ]    [ Redirect ]                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Audit Trail

Every steering action is logged:

```json
{
  "task_id": "139",
  "action": "redirect",
  "from_stage": "implement",
  "to_stage": "router",
  "reason": "Wrong experts selected — needs database expert",
  "timestamp": "2026-03-20T10:55:00Z",
  "actor": "developer"
}
```

Audit entries appear:
- In the TaskPacket timeline as a distinct entry type (🔧 icon, developer action)
- In the Gate Inspector (steering actions are gate-adjacent events)
- In a dedicated "Activity Log" in Settings (all steering actions across all TaskPackets)

### 3.5 Stories for Epic Decomposition

- S1: Pause/Resume actions on TaskPacket timeline
- S2: Retry Stage action with confirmation dialog
- S3: Redirect modal with stage selector and reason input
- S4: Abort action with confirmation and reason
- S5: Hold at Next Gate action
- S6: Pipeline Rail context menu (stage-level actions)
- S7: Audit trail logging (database + UI display)
- S8: Steering action entries in TaskPacket timeline
- S9: Backend: Temporal workflow signal handling for pause/resume/redirect/abort

---

## 4. Feature: Budget & Cost Dashboard

### 4.1 What It Does

Real-time cost tracking across all TaskPackets with budget alerts, projections, and per-model/per-stage breakdowns. Builds on the existing cost dashboard templates in `src/admin/templates/cost_dashboard.html`.

### 4.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────┐
│  COST & BUDGET                                        Period: [ 7d ▼ ] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────┐│
│  │ Total Spend   │ │ Active Now    │ │ Budget Remain │ │ Avg/Task    ││
│  │ $42.80        │ │ $4.20         │ │ $57.20 / $100 │ │ $1.65       ││
│  │ ▲ 12% vs last │ │ 3 tasks      │ │ ████████░░ 57%│ │ ▼ 8% vs last││
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────┘│
│                                                                         │
│  ── SPEND OVER TIME ───────────────────────────────────────────────    │
│                                                                         │
│  $15 ┤                                                                  │
│      │            ╭─╮                                                   │
│  $10 ┤     ╭──╮  │ │  ╭──╮                                            │
│      │  ╭──╮  │  │ │  │  │  ╭──╮                                      │
│   $5 ┤  │  │  │  │ │  │  │  │  │  ╭──╮                               │
│      │  │  │  │  │ │  │  │  │  │  │  │                                │
│   $0 ┼──┴──┴──┴──┴─┴──┴──┴──┴──┴──┴──┤                               │
│      Mon  Tue  Wed  Thu  Fri  Sat  Sun                                 │
│                                                                         │
│      ██ opus-4    ▓▓ sonnet-4    ░░ haiku-4                           │
│                                                                         │
│  ── COST BY PIPELINE STAGE ────────────────────────────────────────    │
│                                                                         │
│  Intake     █░░░░░░░░░░░░░░░░░░░  $0.20  (0.5%)                      │
│  Context    ███░░░░░░░░░░░░░░░░░  $2.10  (4.9%)                      │
│  Intent     █████░░░░░░░░░░░░░░░  $4.80  (11.2%)                     │
│  Router     █░░░░░░░░░░░░░░░░░░░  $0.30  (0.7%)                      │
│  Assembler  ██░░░░░░░░░░░░░░░░░░  $1.40  (3.3%)                      │
│  Implement  ████████████████░░░░  $24.60 (57.5%)                      │
│  Verify     ███░░░░░░░░░░░░░░░░░  $3.20  (7.5%)                      │
│  QA         █████░░░░░░░░░░░░░░░  $5.00  (11.7%)                     │
│  Publish    █░░░░░░░░░░░░░░░░░░░  $1.20  (2.8%)                      │
│                                                                         │
│  ── COST BY MODEL ─────────────────────────────────────────────────    │
│                                                                         │
│  opus-4     ████████████████████  $31.20 (72.9%)   412K tokens        │
│  sonnet-4   ████████░░░░░░░░░░░░  $9.80  (22.9%)   890K tokens       │
│  haiku-4    ██░░░░░░░░░░░░░░░░░░  $1.80  (4.2%)    1.2M tokens       │
│                                                                         │
│  ── BUDGET ALERTS ─────────────────────────────────────────────────    │
│                                                                         │
│  ⚠ Daily spend ($8.40) exceeds daily average ($6.11) by 37%           │
│  ✓ Weekly budget on track (57.2% remaining with 2 days left)          │
│                                                                         │
│  Alert thresholds:                                                     │
│  Daily spend warning:  [ $10.00 ]                                      │
│  Weekly budget cap:    [ $100.00 ]                                     │
│  Per-task warning:     [ $5.00  ]                                      │
│  ☑ Pause pipeline when weekly budget exceeded                          │
│  ☐ Downgrade models when approaching budget (opus → sonnet)            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Summary cards** — Total spend, active cost, budget remaining (with progress bar), average per task. Each card shows trend vs previous period.

2. **Spend over time chart** — Stacked bar chart by day, colored by model. Selectable period (1d, 7d, 30d, custom).

3. **Cost by pipeline stage** — Horizontal bar chart showing where money goes. Implement stage dominates (expected). Helps identify optimization opportunities.

4. **Cost by model** — Horizontal bar chart with both dollar cost and token count per model. Shows cost-efficiency tradeoffs.

5. **Budget alerts** — Current alert status + configurable thresholds. Two automated actions available:
   - Pause pipeline when budget exceeded (hard stop)
   - Model downgrade when approaching budget (cost optimization)

### 4.3 Per-Task Cost View

In addition to the dashboard, every TaskPacket shows cost breakdown:

```
┌──────────────────────────────────┐
│  COST — #139                     │
│                                  │
│  Total: $2.60                    │
│  ── By stage ──                  │
│  Context:    $0.10               │
│  Intent:     $0.30               │
│  Router:     $0.02               │
│  Assembler:  $0.08               │
│  Implement:  $1.80 (in progress) │
│  ── By model ──                  │
│  opus-4:     $2.20 (180K tokens) │
│  sonnet-4:   $0.40 (62K tokens)  │
└──────────────────────────────────┘
```

### 4.4 Data Sources

- Cost data: from `src/admin/model_spend.py` (existing)
- Model pricing: from `src/admin/model_gateway.py` (existing)
- Budget configuration: new settings in PostgreSQL
- Real-time cost: SSE events (`pipeline.cost_update`)

### 4.5 Inspiration

| Element | Source | Adaptation |
|---------|--------|------------|
| Cost analytics dashboard | Codegen's analytics | Stacked bar by model, per-stage breakdown |
| Token tracking | Mission Control (32-panel dashboard) | Per-model token counts alongside cost |
| Budget alerts | Aperant's usage monitor | Configurable thresholds with automated actions |
| Trend indicators | Linear's metrics | ▲/▼ vs previous period |
| Per-task cost | Codegen's per-run cost | Stage + model breakdown per TaskPacket |

### 4.6 Stories for Epic Decomposition

- S1: Summary cards (total spend, active, budget remaining, avg/task)
- S2: Spend over time chart (stacked bar by model)
- S3: Cost by pipeline stage (horizontal bars)
- S4: Cost by model (horizontal bars with token counts)
- S5: Period selector (1d, 7d, 30d, custom)
- S6: Budget alert configuration (thresholds, automated actions)
- S7: Per-task cost breakdown (in TaskPacket detail)
- S8: Real-time cost updates via SSE
- S9: Budget exceeded pipeline pause (backend + UI indicator)
- S10: Model downgrade automation (backend + UI indicator)

---

## 5. Feature: Reputation & Outcome Dashboard

### 5.1 What It Does

Surfaces TheStudio's reputation and outcome systems as a visual dashboard. Shows how well the pipeline is performing over time, which stages/experts/models produce the best results, and where the system is learning or degrading.

### 5.2 Look and Feel

```
┌─────────────────────────────────────────────────────────────────────────┐
│  REPUTATION & OUTCOMES                                Period: [ 30d ▼ ]│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────┐│
│  │ Success Rate  │ │ Avg Loopbacks │ │ PR Merge Rate │ │ Drift Score ││
│  │ 87%           │ │ 0.4 / task    │ │ 72%           │ │ 0.12 (low)  ││
│  │ ▲ 5% vs last  │ │ ▼ 0.1 vs last │ │ ▲ 8% vs last  │ │ stable      ││
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────┘│
│                                                                         │
│  ── EXPERT PERFORMANCE ────────────────────────────────────────────    │
│                                                                         │
│  Expert              Weight    Tasks    Pass Rate    Trend             │
│  ─────────────────────────────────────────────────────────            │
│  Test Expert         0.95      28       96%          ▲ stable         │
│  Auth Expert         0.92      12       91%          ▲ improving      │
│  API Expert          0.88      18       83%          ▼ declining      │
│  Error Handler       0.87      15       87%          → stable         │
│  DB Expert           0.81       8       75%          ▼ declining      │
│                                                                         │
│  ── OUTCOME SIGNALS ───────────────────────────────────────────────    │
│                                                                         │
│  Recent outcomes:                                                      │
│  ✓ #137 Cache fix — PR merged, no post-merge issues        3h ago    │
│  ✓ #135 API docs — PR merged, positive review               1d ago   │
│  ⚠ #133 Logger refactor — PR merged, 1 revert commit        2d ago   │
│  ✗ #130 Search feature — PR closed without merge             3d ago   │
│                                                                         │
│  Learnings captured:                                                   │
│  • Logger refactor: revert was due to missing edge case in             │
│    async context — QA gate didn't catch async behavior                │
│    → Signal: improve QA coverage for async patterns                   │
│  • Search feature: scope was too broad for single TaskPacket          │
│    → Signal: auto-flag tasks with >10 files affected                  │
│                                                                         │
│  ── DRIFT DETECTION ───────────────────────────────────────────────    │
│                                                                         │
│  ✓ Gate pass rates: stable (no significant change)                    │
│  ⚠ API Expert: declining pass rate (83% → 79% over 14d)              │
│    Possible cause: new API patterns not in expert training            │
│  ✓ Cost per task: stable ($1.65 avg, within normal range)            │
│  ✓ Loopback rate: improving (0.5 → 0.4 per task over 14d)           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Summary cards** — Success rate (tasks that produced merged PRs), avg loopbacks, PR merge rate, drift score (composite measure of system stability).

2. **Expert performance table** — Each expert's reputation weight, task count, pass rate, and trend indicator. Sortable by any column. Click an expert to see their full performance history.

3. **Outcome signals** — Recent TaskPacket outcomes (merged, reverted, closed). Each entry shows the outcome and any post-merge signals (reverts, follow-up issues). Learnings extracted from negative outcomes.

4. **Drift detection** — Automated alerts when metrics drift outside normal ranges. Each alert shows the metric, the drift direction, and possible cause.

### 5.3 Data Sources

- Reputation weights: from `src/reputation/` (existing)
- Outcome signals: from `src/outcome/` (existing)
- PR merge status: from GitHub webhook events (PR merged, closed, reverted)
- Drift detection: computed from rolling 14-day windows over reputation data

### 5.4 Stories for Epic Decomposition

- S1: Summary cards (success rate, avg loopbacks, merge rate, drift score)
- S2: Expert performance table with sorting
- S3: Expert detail view (click to see history, tasks, trend chart)
- S4: Outcome signals list (recent outcomes with post-merge events)
- S5: Learnings panel (extracted from negative outcomes)
- S6: Drift detection alerts with possible causes
- S7: Period selector and trend calculations
- S8: Drift score computation (backend)

---

## 6. Feature: Notification System

### 6.1 What It Does

Alerts the developer when attention is needed: gate failures, budget warnings, tasks awaiting review, trust tier escalations, drift alerts.

### 6.2 Look and Feel

**Notification bell (top bar):**

```
  🔔 (3)
  ┌────────────────────────────────────────────┐
  │ NOTIFICATIONS                        Mark all read │
  ├────────────────────────────────────────────┤
  │                                            │
  │ ⚠ #139 gate failed at Verify       2m ago │
  │   pytest: test_concurrent_requests         │
  │   [ View Gate → ]                          │
  │                                            │
  │ ◉ #143 Intent Spec ready for review 5m ago │
  │   [ Review Intent → ]                      │
  │                                            │
  │ 💰 Daily spend warning: $8.40     15m ago  │
  │   Threshold: $10.00                        │
  │   [ View Budget → ]                        │
  │                                            │
  │ ── Earlier ────────────────────────────    │
  │ ✓ #142 PR #289 created             1h ago │
  │ ✓ #137 PR #287 merged              3h ago │
  │                                            │
  └────────────────────────────────────────────┘
```

**Notification types:**

| Type | Icon | Trigger |
|------|------|---------|
| Gate failure | ⚠ | Any gate fails |
| Review needed | ◉ | Intent Spec or PR awaiting developer review |
| Budget warning | 💰 | Spend exceeds threshold |
| Task complete | ✓ | PR created or merged |
| Drift alert | 📉 | Metric drift detected |
| Escalation | 🔴 | Max loopbacks reached, needs human review |
| Trust tier change | 🔒 | Task's trust tier was re-evaluated |

### 6.3 Future: External Notifications

Phase 4+ consideration: push notifications to Slack, Discord, email, or webhook endpoints. Configuration in Settings.

### 6.4 Stories for Epic Decomposition

- S1: Notification bell with unread count
- S2: Notification dropdown panel with categorized entries
- S3: Click-to-navigate from notification to relevant view
- S4: Mark as read (individual and bulk)
- S5: Notification generation from SSE events (gate failures, budget, etc.)
- S6: Notification preferences (which types to show)

---

## 7. Cross-Cutting: Settings Panel

### 7.1 Scope

A unified settings panel for all configuration:

```
Settings
├── Trust Tiers        (Feature 2 above)
├── Budget & Alerts    (Feature 4 above — alert thresholds)
├── Notifications      (Feature 6 — preferences)
├── GitHub Connection   (OAuth, repo selection, Projects sync)
├── Model Gateway      (Model routing, fallback chains, pricing)
├── Pipeline Config    (Stage timeouts, max concurrency, loopback limits)
└── Account            (Auth, API keys, team members — future)
```

Each section is a tab or collapsible panel within Settings. Design follows the same patterns as trust tier configuration: form fields, save on change, immediate effect.

---

## 8. Summary: Story Count by Feature

| Feature | Stories | Priority |
|---------|---------|----------|
| Trust Tier Configuration | 11 | Phase 3 |
| Pipeline Steering Controls | 9 | Phase 3 |
| Budget & Cost Dashboard | 10 | Phase 3 |
| Reputation & Outcome Dashboard | 8 | Phase 5 |
| Notification System | 6 | Phase 3 |
| **Total** | **44** | |

Trust Tiers, Steering, Budget, and Notifications belong to **Phase 3**. Reputation & Outcomes belong to **Phase 5** (requires significant outcome data to be meaningful).
