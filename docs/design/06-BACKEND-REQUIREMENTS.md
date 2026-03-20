# 06 — Backend Requirements for Dashboard Frontend

**Parent:** [00-PIPELINE-UI-VISION.md](00-PIPELINE-UI-VISION.md)
**Status:** Design Draft
**Date:** 2026-03-20
**Scope:** All backend work required to power the dashboard frontend. This document tracks infrastructure, API endpoints, event emission, and data model changes that the frontend design docs (01-05) depend on but do not implement.

---

## 1. Why This Document Exists

Meridian review identified that the frontend design docs assume ~50-70 backend stories that were neither tracked nor phased. The frontend can't render what the backend doesn't emit. This document closes that gap.

---

## 2. Current State Audit

| Component | Current State | Source |
|-----------|--------------|--------|
| **NATS JetStream** | Active. Two streams: `THESTUDIO_VERIFICATION` (3 events) and `THESTUDIO_QA` (3 events). Only verification/QA gate results are published. | `src/verification/signals.py`, `src/qa/signals.py` |
| **Temporal Signals** | 3 signal handlers: `approve_publish`, `reject_publish`, `readiness_cleared`. No pause/resume/redirect/abort. | `src/workflow/pipeline.py:254-277` |
| **TaskPacket Status** | 13-value StrEnum: RECEIVED → ENRICHED → CLARIFICATION_REQUESTED → HUMAN_REVIEW_REQUIRED → INTENT_BUILT → IN_PROGRESS → VERIFICATION_PASSED/FAILED → AWAITING_APPROVAL → PUBLISHED/REJECTED/FAILED. No "triage" status. | `src/models/taskpacket.py:22-82` |
| **SSE/Streaming** | Not implemented. All UI updates use HTMX polling with full-page GET requests. | None |
| **Agent Activity Events** | Not implemented. Agent framework tracks cost via `PipelineBudget` but emits no structured activity events. | `src/agent/framework.py` |
| **Trust Tiers** | Implemented as SHADOW/PROBATION/TRUSTED with hardcoded thresholds. `compute_tier()` uses weight/confidence/sample_count. No conditional rule engine. | `src/reputation/tiers.py:93-134` |
| **Webhook Path** | `POST /webhook/github` (NOT `/api/v1/webhooks/github`). Validates `X-Hub-Signature-256`. | `src/ingress/webhook_handler.py:81` |
| **Cost Tracking** | `ModelCallAudit` per LLM call, `SpendReport` aggregation, `TierBudgetUtilization` per tier. `PipelineBudget` enforces per-workflow limits. | `src/admin/model_spend.py`, `src/admin/model_gateway.py` |
| **Dashboard API** | No dedicated API. Admin UI serves HTML via Jinja2 templates. Cost dashboard, budget utilization, metrics, and workflows all server-rendered. | `src/admin/ui_router.py` |
| **GitHub Projects** | Implemented and feature-flagged. `ProjectsV2Client` with GraphQL, field mapping, status sync in workflow activity. Flag: `projects_v2_enabled`. | `src/github/projects_client.py`, `src/github/projects_mapping.py` |

---

## 3. Required Backend Work — By Phase

### Phase 0: Frontend Scaffolding + SSE Proof-of-Concept

**Goal:** Prove the SSE-over-NATS bridge works end-to-end before committing to full Phase 1.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-0.1 | Create `src/dashboard/` package with FastAPI router mounted at `/api/v1/dashboard/` | — | S |
| B-0.2 | Implement SSE endpoint (`GET /api/v1/dashboard/events/stream`) using `StreamingResponse` with NATS JetStream subscription | B-0.1 | M |
| B-0.3 | Add `Last-Event-ID` reconnection support with NATS sequence replay | B-0.2 | M |
| B-0.4 | Emit `pipeline.stage.enter` and `pipeline.stage.exit` events from Temporal workflow activities (instrument `src/workflow/activities.py`) | B-0.2 | M |
| B-0.5 | Emit `pipeline.gate.pass` and `pipeline.gate.fail` events (extend existing verification/QA signal emission) | B-0.4 | S |
| B-0.6 | Create minimal test page that connects to SSE and displays stage events in real-time | B-0.2, B-0.4 | S |
| B-0.7 | Add auth token support on SSE endpoint (query parameter, matching existing admin auth) | B-0.2 | S |

**Estimated effort:** 7 stories, ~2 weeks for a solo developer.

### Phase 1: Pipeline Visibility Backend

**Goal:** Power the Pipeline Rail, TaskPacket Timeline, Activity Stream, and Gate Inspector.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-1.1 | `GET /api/v1/dashboard/tasks` — List TaskPackets with pagination, filtering (status, date range, category) | B-0.1 | M |
| B-1.2 | `GET /api/v1/dashboard/tasks/:id` — TaskPacket detail (current status, all stage timestamps, cost breakdown) | B-1.1 | S |
| B-1.3 | `GET /api/v1/dashboard/tasks/:id/gates` — Gate results for a specific TaskPacket | B-1.1 | S |
| B-1.4 | `GET /api/v1/dashboard/gates` — List all gate events (paginated, filterable by pass/fail, stage, task, date) | B-0.1 | M |
| B-1.5 | `GET /api/v1/dashboard/gates/:id` — Gate detail with full evidence (check results, commands, output) | B-1.4 | S |
| B-1.6 | Store gate evidence artifacts in PostgreSQL (currently only in NATS + Temporal history) | B-1.4 | L |
| B-1.7 | Emit `pipeline.activity` events from agent framework — structured tool call events (file_read, file_edit, search, test_run, shell, reasoning) | B-0.4 | L |
| B-1.8 | Add `ActivityEntry` model to PostgreSQL for activity log persistence (last 5000 per task) | B-1.7 | M |
| B-1.9 | Emit `pipeline.cost_update` events from `PipelineBudget` on each model call completion | B-0.4 | S |
| B-1.10 | `GET /api/v1/dashboard/tasks/:id/activity` — Paginated activity log for a TaskPacket | B-1.8 | M |
| B-1.11 | Emit `pipeline.loopback.start` and `pipeline.loopback.resolve` events from workflow loopback logic | B-0.4 | S |
| B-1.12 | Add stage timing data to TaskPacket model (start/end timestamp per stage) | — | M |
| B-1.13 | Pipeline stage metrics aggregation query (pass rate, avg time, throughput by stage) | B-1.12 | M |
| B-1.14 | Gate health metrics aggregation query (pass rate, top failure type, loopback rate) | B-1.6 | M |

**Estimated effort:** 14 stories, ~4-5 weeks.

### Phase 2: Planning Experience Backend

**Goal:** Power the Triage Queue, Intent Editor, Complexity Dashboard, Expert Routing Preview, and Backlog Board.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-2.1 | Add `TRIAGE` status to TaskPacket status enum with transition rules | — | S |
| B-2.2 | Make webhook handler create TaskPackets in TRIAGE status (instead of immediately starting workflow) when triage mode enabled | B-2.1 | M |
| B-2.3 | `POST /api/v1/dashboard/tasks` — Create TaskPacket manually (without GitHub issue) | B-0.1 | M |
| B-2.4 | `POST /api/v1/dashboard/tasks/:id/accept` — Accept from triage, start Temporal workflow | B-2.1 | M |
| B-2.5 | `POST /api/v1/dashboard/tasks/:id/reject` — Reject with reason, update status | B-2.1 | S |
| B-2.6 | `PATCH /api/v1/dashboard/tasks/:id` — Edit TaskPacket metadata (title, description, category, priority) before pipeline start | B-0.1 | S |
| B-2.7 | Context stage pre-scan: lightweight file impact + complexity hint + cost estimate (new lightweight activity or extracted from existing Context stage) | — | L |
| B-2.8 | `GET /api/v1/dashboard/tasks/:id/intent` — Return Intent Specification with version history | B-0.1 | M |
| B-2.9 | `PUT /api/v1/dashboard/tasks/:id/intent` — Developer edits Intent Spec (creates new version) | B-2.8 | M |
| B-2.10 | `POST /api/v1/dashboard/tasks/:id/intent/approve` — Approve intent, send Temporal signal to continue to Router | B-2.8 | M |
| B-2.11 | `POST /api/v1/dashboard/tasks/:id/intent/refine` — Send refinement feedback to Intent Builder (re-run with developer notes) | B-2.10 | M |
| B-2.12 | Intent Spec version storage in PostgreSQL (versions, timestamps, source: auto/developer/refinement) | B-2.8 | M |
| B-2.13 | Add Temporal workflow wait point after Intent stage (pause for developer review before Router) | B-2.10 | L |
| B-2.14 | `GET /api/v1/dashboard/tasks/:id/routing` — Return expert routing results (experts selected, reasons, weights) | B-0.1 | M |
| B-2.15 | `POST /api/v1/dashboard/tasks/:id/routing/approve` — Approve routing, continue to Assembler | B-2.14 | S |
| B-2.16 | `POST /api/v1/dashboard/tasks/:id/routing/override` — Add/remove experts from routing | B-2.14 | M |
| B-2.17 | Historical comparison query: similar tasks by category + complexity, avg cost/time/loopbacks/success rate | B-1.12 | M |
| B-2.18 | Board state persistence in PostgreSQL (column preferences, card ordering) | — | M |

**Estimated effort:** 18 stories, ~5-6 weeks.

### Phase 3: Interactive Controls Backend

**Goal:** Power Trust Tier Configuration, Pipeline Steering, Budget Governance, Notifications.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-3.1 | Trust tier rule model in PostgreSQL (conditions, tier assignment, priority order) | — | M |
| B-3.2 | Trust tier rule evaluation engine (evaluate rules against TaskPacket metadata at pipeline start) | B-3.1 | L |
| B-3.3 | `GET /PUT /api/v1/dashboard/trust/rules` — CRUD for trust tier rules | B-3.1 | M |
| B-3.4 | `GET /PUT /api/v1/dashboard/trust/safety-bounds` — Safety bounds configuration (max lines, max cost, mandatory review patterns) | B-3.1 | S |
| B-3.5 | Map design trust tiers (Observe/Suggest/Execute) to codebase tiers (shadow/probation/trusted) — reconcile or extend | B-3.1 | M |
| B-3.6 | Add Temporal signal: `pause_task` — freeze workflow at current step | — | L |
| B-3.7 | Add Temporal signal: `resume_task` — continue paused workflow | B-3.6 | M |
| B-3.8 | Add Temporal signal: `redirect_task(target_stage, reason)` — cancel current stage, restart from target | B-3.6 | L |
| B-3.9 | Add Temporal signal: `abort_task(reason)` — terminate workflow with reason | — | M |
| B-3.10 | `POST /api/v1/dashboard/tasks/:id/pause` — Send pause signal to Temporal | B-3.6 | S |
| B-3.11 | `POST /api/v1/dashboard/tasks/:id/resume` — Send resume signal | B-3.7 | S |
| B-3.12 | `POST /api/v1/dashboard/tasks/:id/redirect` — Send redirect signal | B-3.8 | S |
| B-3.13 | `POST /api/v1/dashboard/tasks/:id/abort` — Send abort signal | B-3.9 | S |
| B-3.14 | Steering action audit log (persist all steering actions to PostgreSQL) | B-3.10 | M |
| B-3.15 | `GET /PUT /api/v1/dashboard/budget/config` — Budget threshold configuration (daily warning, weekly cap, per-task warning) | — | S |
| B-3.16 | Budget exceeded pipeline pause (check budget after each cost event, pause if exceeded) | B-3.6, B-3.15 | M |
| B-3.17 | Model downgrade automation (switch opus → sonnet when approaching budget threshold) | B-3.15 | M |
| B-3.18 | `GET /api/v1/dashboard/budget/summary` — Current period summary (total spend, active, remaining, avg/task) | — | S |
| B-3.19 | `GET /api/v1/dashboard/budget/history` — Time series spend data (by day, model-segmented) | — | M |
| B-3.20 | `GET /api/v1/dashboard/budget/by-stage` and `/by-model` — Breakdown queries | — | S |
| B-3.21 | Notification model in PostgreSQL (type, message, task_id, read status, timestamp) | — | M |
| B-3.22 | Notification generation from SSE events (gate failures, budget warnings, review needed) | B-3.21, B-0.2 | M |
| B-3.23 | `GET /api/v1/dashboard/notifications` — List notifications (paginated, unread count) | B-3.21 | S |
| B-3.24 | `PATCH /api/v1/dashboard/notifications/:id/read` — Mark as read | B-3.23 | S |

**Estimated effort:** 24 stories, ~7-8 weeks.

### Phase 4: GitHub Integration Backend

**Goal:** Power bidirectional GitHub Projects sync, PR Evidence Explorer, Issue Import, Pipeline Comments.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-4.1 | Enable and configure existing `ProjectsV2Client` (currently feature-flagged off) | — | S |
| B-4.2 | Extend project field mapping for new custom fields (Trust Tier, Cost, Complexity) | B-4.1 | M |
| B-4.3 | GitHub → TheStudio sync: subscribe to `projects_v2_item` webhook events and update TaskPacket status | B-4.1 | M |
| B-4.4 | `GET /PUT /api/v1/dashboard/github/projects/config` — Projects sync configuration | B-4.1 | S |
| B-4.5 | `POST /api/v1/dashboard/github/projects/sync` — Force full sync | B-4.1 | M |
| B-4.6 | `GET /api/v1/dashboard/github/issues` — List repo issues from GitHub API (cached, paginated) | — | M |
| B-4.7 | `POST /api/v1/dashboard/github/import` — Batch import issues as TaskPackets | B-4.6, B-2.1 | M |
| B-4.8 | GitHub issue pipeline comment: create/update structured status comment on linked issue at each stage transition | B-0.4 | M |
| B-4.9 | `POST /api/v1/dashboard/tasks/:id/pr/approve` — Approve and merge PR via GitHub API | — | M |
| B-4.10 | `POST /api/v1/dashboard/tasks/:id/pr/request-changes` — Post PR review comment + create loopback signal | — | M |
| B-4.11 | Bridge GitHub webhook events to NATS (github.pr.*, github.issue.*) for SSE propagation | B-0.2 | M |
| B-4.12 | Evidence comment generation as structured JSON (for dashboard rendering, in addition to existing Markdown) | — | M |

**Estimated effort:** 12 stories, ~3-4 weeks.

### Phase 5: Analytics & Learning Backend

**Goal:** Power Operational Analytics, Reputation Dashboard, Outcome Tracking.

| # | Story | Depends On | Est. |
|---|-------|-----------|------|
| B-5.1 | `GET /api/v1/dashboard/analytics/throughput` — Tasks per day/week time series | B-1.12 | M |
| B-5.2 | `GET /api/v1/dashboard/analytics/bottlenecks` — Avg time per stage aggregation | B-1.12 | S |
| B-5.3 | `GET /api/v1/dashboard/analytics/categories` — Performance by task category | B-1.12 | S |
| B-5.4 | `GET /api/v1/dashboard/analytics/failures` — Gate failure analysis by stage and type | B-1.6 | M |
| B-5.5 | `GET /api/v1/dashboard/reputation/experts` — Expert performance table (weight, tasks, pass rate, trend) | — | M |
| B-5.6 | `GET /api/v1/dashboard/reputation/outcomes` — Recent outcomes with post-merge signals | — | M |
| B-5.7 | `GET /api/v1/dashboard/reputation/drift` — Drift detection alerts (rolling 14-day windows) | — | M |
| B-5.8 | Drift score computation: composite metric from gate pass rates, expert weights, cost trends | B-5.7 | M |

**Estimated effort:** 8 stories, ~2-3 weeks.

---

## 4. Summary

| Phase | Backend Stories | Estimated Effort | Blocks Frontend Phase |
|-------|----------------|------------------|-----------------------|
| Phase 0 (SSE PoC) | 7 | ~2 weeks | Phase 0 frontend scaffolding |
| Phase 1 | 14 | ~4-5 weeks | Phase 1 pipeline visualization |
| Phase 2 | 18 | ~5-6 weeks | Phase 2 planning experience |
| Phase 3 | 24 | ~7-8 weeks | Phase 3 interactive controls |
| Phase 4 | 12 | ~3-4 weeks | Phase 4 GitHub integration |
| Phase 5 | 8 | ~2-3 weeks | Phase 5 analytics |
| **Total** | **83** | **~23-28 weeks** | |

**Combined total (frontend + backend):** ~185 frontend + 83 backend = **268 stories**.

**For a solo developer, backend and frontend for each phase run in series, not parallel.** This means each phase's calendar time is roughly: backend stories + frontend stories. Plan accordingly.

---

## 5. Key Dependencies Between Backend and Frontend

```
Backend Phase 0 (SSE/NATS bridge)
    └─→ Frontend Phase 0 (scaffolding)
         └─→ Backend Phase 1 (API + events)
              └─→ Frontend Phase 1 (pipeline viz)
                   └─→ Backend Phase 2 (triage + intent + routing APIs)
                        └─→ Frontend Phase 2 (planning)
                             └─→ Backend Phase 3 (steering + trust + budget)
                                  └─→ Frontend Phase 3 (controls)
                                       └─→ Backend Phase 4 (GitHub APIs)
                                            └─→ Frontend Phase 4 (integration)
                                                 └─→ Backend Phase 5 (analytics queries)
                                                      └─→ Frontend Phase 5 (dashboards)
```

Backend and frontend within the same phase can overlap partially (API endpoints can be built while UI components are being designed), but the SSE infrastructure (Phase 0) is a hard prerequisite for everything.

---

## 6. Reconciliation: Design Tiers vs Codebase Tiers

The design docs use **Observe / Suggest / Execute** (Publisher behavior). The codebase uses **Shadow / Probation / Trusted** (expert reputation). These are different concepts:

| Design Tier | Purpose | Codebase Equivalent |
|-------------|---------|---------------------|
| Observe | Pipeline runs, report only, no PR | New — not in codebase |
| Suggest | Draft PR created, developer approves | Maps to `AWAITING_APPROVAL` flow |
| Execute | PR auto-merged if gates pass | New — requires auto-merge logic |

| Codebase Tier | Purpose | Design Equivalent |
|---------------|---------|-------------------|
| Shadow | Expert with low confidence | Not surfaced in design |
| Probation | Expert with moderate track record | Not surfaced in design |
| Trusted | Expert with high confidence | Not surfaced in design |

**Resolution needed in B-3.5:** The design's trust tiers (Observe/Suggest/Execute) govern Publisher behavior and are task-level. The codebase's tiers (Shadow/Probation/Trusted) govern expert selection and are expert-level. Both are needed. The task-level trust tier is a new concept that must be added to the TaskPacket model alongside the existing expert-level reputation tiers.
