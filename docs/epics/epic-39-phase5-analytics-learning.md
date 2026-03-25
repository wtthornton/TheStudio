# Epic 39: Phase 5 -- Analytics & Learning Dashboards

> **Status:** **COMPLETE** (2026-03-25) — All stories 39.0a–39.21 delivered. Meridian Round 2 PASS (2026-03-22).
> **Epic Owner:** Primary Developer
> **Duration:** 5-6 weeks (backend + frontend, solo developer; +1 week for prerequisite data stories)
> **Created:** 2026-03-20
> **Meridian Review:** Round 1: CONDITIONAL PASS → Round 2: **PASS** (2026-03-22)

---

## 1. Title

**Pipeline Performance Becomes Visible: Developers See What Works, What Fails, and What Drifts**

---

## 2. Narrative

TheStudio has been running a 9-stage pipeline through Phases 0-4, processing tasks, producing PRs, and accumulating data. Gate results, stage timings, expert weights, outcome signals, cost records, and loopback counts are all persisted in PostgreSQL. But none of it is surfaced to the developer in aggregate form.

Right now, the only way to understand pipeline health is to inspect individual TaskPackets. There is no throughput chart. No bottleneck analysis. No view that shows which experts are declining in performance or which task categories produce the highest merge rates. The reputation and outcome systems (`src/reputation/`, `src/outcome/`) compute weights and detect drift, but their outputs are invisible -- they influence routing decisions silently, and the developer has no way to know whether the system is learning or degrading.

This matters because trust is the product. A developer who cannot see that bug fixes merge at 89% while features merge at 62% cannot calibrate their expectations. A developer who cannot see that the API Expert's pass rate dropped from 88% to 79% over two weeks cannot intervene before bad routing compounds into bad PRs. A developer who cannot see that the Verify stage averages 7 minutes while Intent averages 3 minutes (plus developer review time) cannot make informed decisions about where to invest pipeline optimization effort.

This is the final phase of the Pipeline UI initiative. It depends on all prior phases: Phase 0's SSE infrastructure for real-time updates, Phase 1's stage timing data and gate evidence persistence, Phase 3's cost tracking infrastructure, and Phase 4's GitHub integration for PR merge status. It also requires sufficient historical data to be meaningful -- charts with two data points teach nothing.

**MVP:** A throughput chart (tasks per day/week) and a stage bottleneck analysis (avg time per stage as horizontal bars). These two views alone answer the two most important operational questions: "How much work is the pipeline doing?" and "Where does time go?"

**Full scope:** Category breakdown, failure analysis by stage and type, expert performance table, outcome signal feed, drift detection alerts, and trend calculations across all metrics.

---

## 3. References

| Artifact | Location |
|----------|----------|
| Master UI vision (Phase 5 scope) | `docs/design/00-PIPELINE-UI-VISION.md` Section 8 |
| Operational Analytics design | `docs/design/04-GITHUB-INTEGRATION-ANALYTICS.md` Section 5 |
| Reputation & Outcome Dashboard design | `docs/design/03-INTERACTIVE-CONTROLS.md` Section 5 |
| Backend requirements (B-5.1 through B-5.8) | `docs/design/06-BACKEND-REQUIREMENTS.md` Section 3, Phase 5 |
| Technology architecture | `docs/design/05-TECHNOLOGY-ARCHITECTURE.md` |
| Reputation system (weights API: `get_all_weights()`, `query_weights()`, `get_weight()`) | `src/reputation/engine.py` |
| Outcome system (signals, quarantine) | `src/outcome/` |
| Model spend tracking | `src/admin/model_spend.py` |
| Stage timing data (Phase 1 dependency) | `src/models/taskpacket.py` (stage timestamps from B-1.12) |
| Gate evidence persistence (Phase 1) | Gate results in PostgreSQL (from B-1.6) |
| Codegen analytics (competitor reference) | [Codegen 3.0 Analytics](https://docs.codegen.com/capabilities/analytics) |
| Temporal UI timeline aggregation (inspiration) | [Temporal UI](https://temporal.io/blog/the-dark-magic-of-workflow-exploration) |

---

## 4. Acceptance Criteria

### AC 1: Throughput Chart

A time-series bar chart displays completed tasks per day or per week for a configurable period (7d, 30d, 90d, custom). The chart loads in under 2 seconds for 90 days of data. The period selector persists across page navigations. The throughput endpoint (`GET /api/v1/dashboard/analytics/throughput`) returns JSON with date buckets and task counts.

### AC 2: Stage Bottleneck Analysis

Horizontal bars display the average time spent in each of the 9 pipeline stages, computed across all completed tasks in the selected period. The longest stage is visually highlighted. The most variable stage (highest standard deviation) is annotated. Data comes from `GET /api/v1/dashboard/analytics/bottlenecks`. A developer can identify the slowest stage within 3 seconds of viewing the dashboard.

### AC 3: Category Breakdown

A table shows task count, merge rate, average cost, and average pipeline time grouped by task category (bug, feature, refactor, docs, other). Each row is derived from `GET /api/v1/dashboard/analytics/categories`. Categories with fewer than 3 tasks in the period display a "low sample" indicator.

### AC 4: Failure Analysis

Gate failures are displayed grouped by stage, then by failure type (pytest, ruff, security, acceptance criteria, etc.). A trend indicator shows whether failures are increasing or decreasing vs. the previous equivalent period. The most common failure type is highlighted. Data comes from `GET /api/v1/dashboard/analytics/failures`.

### AC 5: Expert Performance Table

A sortable table displays each expert's reputation weight, task count, gate pass rate, and trend (improving / stable / declining). Clicking an expert row opens a detail view showing their task history and a trend chart of their weight over time. Data comes from `GET /api/v1/dashboard/reputation/experts`.

### AC 6: Outcome Signals Feed

A chronological feed displays recent TaskPacket outcomes: merged, reverted, closed without merge. Each entry shows the outcome type, post-merge signals (revert commits, follow-up issues), and extracted learnings from negative outcomes. Data comes from `GET /api/v1/dashboard/reputation/outcomes`.

### AC 7: Drift Detection Alerts

An alert panel displays metrics that have drifted outside normal ranges over a rolling 14-day window. Each alert names the metric, the drift direction, the magnitude, and a possible cause. The composite drift score (low / moderate / high) is displayed as a summary card. Data comes from `GET /api/v1/dashboard/reputation/drift`. The drift score computation (B-5.8) considers gate pass rates, expert weight trends, cost trends, and loopback rates.

### AC 8: Summary Cards with Trends

Four summary cards appear at the top of the Operational Analytics view (tasks completed, avg pipeline time, PR merge rate, total spend) and four at the top of the Reputation & Outcomes view (success rate, avg loopbacks, PR merge rate, drift score). Each card shows the metric value and a trend indicator (up/down/stable) compared to the previous equivalent period.

---

## 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Insufficient historical data makes charts meaningless | High (early adoption) | Medium | Add "insufficient data" empty states; require minimum 10 completed tasks before rendering trend lines; show raw counts even with sparse data |
| R2 | Aggregation queries slow on large datasets | Medium | High | Use materialized views or pre-aggregated tables; add database indexes on task completion timestamp and stage; test with 10,000+ synthetic TaskPackets |
| R3 | Drift detection false positives erode trust | Medium | Medium | Require minimum 20 tasks in the 14-day window before alerting; use configurable sensitivity thresholds; clearly label alerts as "possible" not "confirmed" |
| R4 | Phase 1-4 dependencies not met (missing stage timestamps, gate evidence) | Low | High | Verify prerequisite data exists before building queries; add fallback "data not available" states; validate B-1.12 (stage timing) and B-1.6 (gate evidence) are complete |

---

## 5. Constraints & Non-Goals

### Constraints

- **Solo developer execution.** Backend and frontend run in series, not parallel. Budget 2-3 weeks backend, 2 weeks frontend.
- **Phase dependency chain.** This epic cannot begin until Phase 1 backend (B-1.6 gate evidence, B-1.12 stage timing) is complete. Phase 4 (GitHub PR merge status) is required for merge rate calculations.
- **Data volume.** Aggregation queries must handle up to 10,000 TaskPackets without exceeding 2 seconds response time. No caching layer is introduced in this phase -- optimize with indexes and query design.
- **Existing admin panel untouched.** The analytics dashboards live at `/dashboard/analytics` and `/dashboard/reputation` in the React SPA. The Jinja admin panel at `/admin/*` is not modified.
- **Frontend stack.** React + Vite + Zustand + Tailwind, consistent with Phase 0-4. Chart library: use whatever was established in Phase 3 (cost dashboard charts).

### Non-Goals

- **Predictive analytics.** No ML-based forecasting, no "predicted merge probability" scores. This phase is descriptive, not predictive.
- **Custom report builder.** No drag-and-drop report creation or saved custom views. Fixed dashboard layouts only.
- **Export to CSV/PDF.** No data export functionality. Developers who need raw data can query the API directly.
- **Real-time streaming analytics.** Charts update on page load or manual refresh. No live-updating charts via SSE (too expensive for aggregation queries).
- **Multi-repo analytics.** All metrics are scoped to the single connected repository. Cross-repo comparison is out of scope per the master vision doc.
- **Alerting integrations.** Drift detection alerts appear in the dashboard only. No Slack/Discord/email push for drift alerts (deferred per master vision).

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|---------------|
| Epic Owner | Primary Developer | Backend queries, frontend components, end-to-end delivery |
| Design | Design specs (docs/design/03, 04) | Wireframes and component specs are complete; no further design input needed |
| QA | Automated (pytest + Playwright) | Backend: unit tests for aggregation queries with synthetic data. Frontend: Playwright tests for chart rendering and interaction |
| Meridian Review | Meridian persona | Epic review before commit; sprint review at slice boundaries |
| Dependency | Phase 1-4 delivery | Stage timing data (B-1.12), gate evidence (B-1.6), cost data (model_spend), PR merge status (GitHub webhooks) |

---

## 7. Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Bottleneck identification | Developer identifies slowest pipeline stage within 3 seconds of viewing analytics | Playwright timing test: page load to visible bottleneck highlight |
| Category insight | Developer can compare merge rates across task categories from a single view | AC 3 implemented; no navigation required to compare categories |
| Drift awareness | Declining expert performance visible on dashboard load when the 14-day rolling window shows >10% decline | Drift detection computed on API request; verified with synthetic data showing >10% weight decline |
| Dashboard load time | All analytics views render in under 2 seconds with 90 days of data | Automated performance test with 10,000 synthetic TaskPackets |
| API response time | All aggregation endpoints respond in under 1 second for 10,000 TaskPackets | pytest benchmark with synthetic data |
| Zero regressions | All pre-existing tests pass after epic delivery | `pytest` full suite green |

---

## 8. Context & Assumptions

### Business Rules

- **Period calculation.** "Previous period" for trend comparison means the period of equal length immediately preceding the selected period. A 30d view compares days 1-30 against days 31-60.
- **Task "completion."** A task is "completed" when it reaches PUBLISHED, REJECTED, or FAILED terminal status. Tasks still in-flight are excluded from aggregation but included in "active" counts.
- **Expert weight source.** Expert weights come from `src/reputation/engine.py` (functions: `get_all_weights()`, `query_weights()`, `get_weight()`). The dashboard reads but never writes weights -- the reputation system is the sole authority.
- **Drift window.** 14-day rolling window is hardcoded for MVP. Configurable windows are a post-MVP enhancement.
- **Category taxonomy.** Task categories (bug, feature, refactor, docs) are derived from GitHub issue labels at intake time. Tasks without labels are categorized as "other."

### Dependencies

| Dependency | Source | Required For |
|------------|--------|-------------|
| Stage timing per TaskPacket (start/end per stage) | B-1.12 (Phase 1) | Bottleneck analysis, avg pipeline time |
| Gate evidence in PostgreSQL | B-1.6 (Phase 1) | Failure analysis by type |
| Cost records (ModelCallAudit) | Existing (`src/admin/model_spend.py`) | Total spend metric, cost trends |
| PR merge status from GitHub | Phase 4 (Epic 38 webhook bridge, or prerequisite story 39.0b) | Merge rate calculations |
| Expert reputation weights | Existing (`src/reputation/engine.py`) | Expert performance table |
| Outcome signals in PostgreSQL | **PREREQUISITE** (currently in-memory only in `src/outcome/ingestor.py`) | Outcome feed, learnings |
| React SPA scaffold | Phase 0 | Dashboard shell, routing, component library |
| Chart library | Phase 3 (cost dashboard) | Consistent charting across dashboard |

### Systems Affected

- **PostgreSQL:** New aggregation queries (read-only) plus 3 prerequisite schema changes: (a) `completed_at` column on `TaskPacketRow`, (b) outcome signal table, (c) `pr_merge_status` field. New indexes on `task_packets.completed_at`, `gate_results.stage`, `gate_results.created_at`.
- **FastAPI:** 7 new GET endpoints under `/api/v1/dashboard/analytics/` and `/api/v1/dashboard/reputation/`.
- **React SPA:** 2 new tab views (`analytics`, `reputation` added to `Tab` union in `frontend/src/App.tsx`), ~12-15 new components at `frontend/src/components/`.
- **Reputation module:** Read-only access. No changes to weight computation or drift detection logic -- the dashboard surfaces existing computations.
- **Outcome module:** Read-only access. No changes to signal ingestion or quarantine logic.

---

## Story Map

### MVP Designation

| Slice | MVP? | Rationale |
|-------|------|-----------|
| Slice 1: Operational Analytics | **MVP** (stories 39.1, 39.2, 39.5, 39.6, 39.7) | Core metrics — throughput and bottlenecks answer the two most important questions |
| Slice 1: Full | Full (stories 39.3, 39.4, 39.8, 39.9, 39.10, 39.11) | Deeper analysis — category breakdown and failure analysis |
| Slice 2: Reputation & Outcomes | Full | Learning — requires accumulated data to be meaningful |

---

### Slice 0: Data Prerequisites (Must complete before Slices 1-2)

> **Goal:** Add missing schema columns and tables that Slices 1-2 depend on.

| # | Story | Type | Est. | Files to Modify/Create |
|---|-------|------|------|----------------------|
| 39.0a | Add `completed_at` timestamp column to `TaskPacketRow` — set on transition to terminal status (PUBLISHED, REJECTED, FAILED, ABORTED). Alembic migration + backfill from `updated_at` for existing terminal TaskPackets. | Backend | S | `src/models/taskpacket.py`, `src/models/taskpacket_crud.py`, migration |
| 39.0b | Add `pr_merge_status` field to `TaskPacketRow` — enum (open, merged, closed), nullable. Updated by Epic 38 webhook bridge (Story 38.24) or by a new polling activity. If Epic 38 is not yet complete, add a manual update endpoint. Migration. | Backend | S | `src/models/taskpacket.py`, migration |
| 39.0c | Persist outcome signals to PostgreSQL — create `OutcomeSignalRow` table (id, task_id, signal_type, payload JSON, created_at). Migrate `src/outcome/ingestor.py` from in-memory list to DB persistence. Preserve existing in-memory API as a cache layer. | Backend | M | `src/outcome/ingestor.py`, `src/outcome/models.py` (new), migration |

### Slice 1: Operational Analytics (Backend + Frontend)

> **Goal:** Answer "How is the pipeline performing overall?" with throughput, bottlenecks, categories, and failures.
> **Why first:** These are the MVP deliverables. Throughput and bottleneck data is available as soon as Phase 1 stage timing exists. No dependency on reputation or outcome systems.

| # | Story | Type | Depends On | Est. | Files to Modify/Create |
|---|-------|------|-----------|------|----------------------|
| 39.1 | `GET /api/v1/dashboard/analytics/throughput` -- Tasks per day/week time series with period parameter | Backend | B-1.12 | M | `src/dashboard/analytics_router.py` (create), `src/dashboard/analytics_queries.py` (create) |
| 39.2 | `GET /api/v1/dashboard/analytics/bottlenecks` -- Avg time per stage aggregation with stddev, highlight annotations | Backend | B-1.12 | S | `src/dashboard/analytics_queries.py` |
| 39.3 | `GET /api/v1/dashboard/analytics/categories` -- Performance by task category (count, merge rate, avg cost, avg time) | Backend | B-1.12 | S | `src/dashboard/analytics_queries.py` |
| 39.4 | `GET /api/v1/dashboard/analytics/failures` -- Gate failures by stage and type with trend indicator | Backend | B-1.6 | M | `src/dashboard/analytics_queries.py` |
| 39.5 | Operational Analytics summary cards (tasks done, avg time, merge rate, spend) with trend calculation | Backend | 39.1-39.4 | S | `src/dashboard/analytics_queries.py` |
| 39.6 | Throughput chart component (bar chart, period selector, responsive) | Frontend | 39.1 | M | `frontend/src/components/analytics/Analytics.tsx` (create), `frontend/src/components/analytics/ThroughputChart.tsx` (create) |
| 39.7 | Stage bottleneck horizontal bar component (highlight longest, annotate most variable) | Frontend | 39.2 | M | `frontend/src/components/analytics/BottleneckBars.tsx` (create) |
| 39.8 | Category breakdown table component | Frontend | 39.3 | S | `frontend/src/components/analytics/CategoryBreakdown.tsx` (create) |
| 39.9 | Failure analysis component (grouped by stage, trend indicators) | Frontend | 39.4 | M | `frontend/src/components/analytics/FailureAnalysis.tsx` (create) |
| 39.10 | Summary cards row component with trend indicators | Frontend | 39.5 | S | `frontend/src/components/analytics/SummaryCards.tsx` (create) |
| 39.11 | Period selector component (7d, 30d, 90d, custom) shared across analytics views | Frontend | -- | S | `frontend/src/components/analytics/PeriodSelector.tsx` (create) |

### Slice 2: Reputation & Outcomes (Backend + Frontend)

> **Goal:** Answer "Is the pipeline learning or degrading?" with expert performance, outcomes, and drift.
> **Why second:** Requires the reputation and outcome subsystems to have accumulated meaningful data. More specialized than Slice 1 -- useful after the developer understands basic throughput.

| # | Story | Type | Depends On | Est. | Files to Modify/Create |
|---|-------|------|-----------|------|----------------------|
| 39.12 | `GET /api/v1/dashboard/reputation/experts` -- Expert performance table (weight, task count, pass rate, trend) | Backend | -- | M | `src/dashboard/reputation_router.py` (create), `src/dashboard/reputation_queries.py` (create) |
| 39.13 | `GET /api/v1/dashboard/reputation/outcomes` -- Recent outcomes with post-merge signals and learnings | Backend | -- | M | `src/dashboard/reputation_queries.py` |
| 39.14 | `GET /api/v1/dashboard/reputation/drift` -- Drift detection alerts (14-day rolling window) | Backend | -- | M | `src/dashboard/reputation_queries.py` |
| 39.15 | Drift score computation: composite metric from gate pass rates, expert weights, cost trends, loopback rates | Backend | 39.14 | M | `src/dashboard/reputation_queries.py` |
| 39.16 | Reputation summary cards (success rate, avg loopbacks, merge rate, drift score) with trends | Backend | 39.12-39.15 | S | `src/dashboard/reputation_queries.py` |
| 39.17 | Expert performance table component (sortable columns, click-to-expand detail) | Frontend | 39.12 | M | `frontend/src/components/reputation/Reputation.tsx` (create), `frontend/src/components/analytics/ExpertTable.tsx` (create) |
| 39.18 | Expert detail view (task history list, weight trend chart) | Frontend | 39.12 | M | `frontend/src/components/analytics/ExpertDetail.tsx` (create) |
| 39.19 | Outcome signals feed component (chronological, outcome badges, learnings) | Frontend | 39.13 | M | `frontend/src/components/analytics/OutcomeFeed.tsx` (create) |
| 39.20 | Drift detection alerts panel (metric, direction, magnitude, possible cause) | Frontend | 39.14, 39.15 | M | `frontend/src/components/analytics/DriftAlerts.tsx` (create) |
| 39.21 | Reputation summary cards row | Frontend | 39.16 | S | Reuse `frontend/src/components/analytics/SummaryCards.tsx` from Slice 1 with reputation data shape |

**Total: 24 stories** (3 in Slice 0, 11 in Slice 1, 10 in Slice 2)

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS (2026-03-22)

**Verdict: CONDITIONAL PASS — 5 blockers found.**

| # | Question | Verdict |
|---|----------|---------|
| 1 | Scope bounded? | **CONDITIONAL PASS** — Missing data prerequisites add ~1 week |
| 2 | ACs testable? | **PASS** |
| 3 | Non-goals explicit? | **PASS** |
| 4 | Dependencies identified? | **CONDITIONAL PASS** — 4 missing data dependencies |
| 5 | Metrics measurable? | **CONDITIONAL PASS** — Drift metric implies push detection |
| 6 | Story map risk-ordered? | **PASS** |
| 7 | AI agent can implement? | **CONDITIONAL PASS** — Frontend paths wrong, weights.py doesn't exist |

### Blockers Found and Fixed

1. ~~**`src/reputation/weights.py` does not exist**~~ **FIXED:** Updated to `src/reputation/engine.py` with specific function names
2. ~~**`completed_at` column missing**~~ **FIXED:** Added prerequisite Story 39.0a
3. ~~**Outcome signals in-memory only**~~ **FIXED:** Added prerequisite Story 39.0c
4. ~~**PR merge status not persisted**~~ **FIXED:** Added prerequisite Story 39.0b
5. ~~**Frontend paths wrong (`src/dashboard/ui/`)**~~ **FIXED:** All paths updated to `frontend/src/components/`
6. ~~**Drift metric unmeasurable**~~ **FIXED:** Rephrased to "visible on dashboard load"

### Round 2: PASS (2026-03-22)

All 5 blockers resolved. Duration adjusted to 5-6 weeks (+1 week for Slice 0 prerequisites). Epic approved for sprint planning after Epic 38 MVP completes.
