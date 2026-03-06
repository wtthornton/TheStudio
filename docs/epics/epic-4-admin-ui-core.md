# Epic 4 — Admin UI Core: Fleet Visibility and Repo Management

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Phase:** 2 (per `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`)
**Predecessor:** Epic 3 — Execute Tier + Compliance Checker (complete: compliance checker, promotion API, tier transitions audit trail, 3+ repos registered)
**Timebox:** 4–6 weeks (focused)

---

## 1. Title

Admin UI Core — Fleet Visibility and Repo Management for Operational Control

---

## 2. Narrative

Epic 3 delivered Execute tier with compliance governance. The platform now has repos at multiple tiers, compliance results persisted, tier transitions audited, and full workflows running. But operators are flying blind. To see health, queue depth, or stuck workflows requires direct database access. To manage repos — register, pause, disable writes — requires API calls with no visibility layer.

Epic 4 delivers Admin UI Core: the minimum viable control surface for operating the platform at scale. This includes Fleet Dashboard (system health, queue depth, active workflows by repo), Repo Management (register, set tier, pause, disable writes), and Task and Workflow Console (timeline view, evidence trail, safe rerun controls). RBAC and audit logging ensure all admin actions are authorized and traceable.

**The business value:** Without Admin UI, the platform cannot be operated safely at scale. Operators cannot see what's happening, cannot respond to stuck workflows, and cannot onboard or manage repos without developer intervention. Admin UI Core is the prerequisite for trusting the system with production workflows across multiple repos.

**Why now:** Execute tier is live. Compliance checker works. Multi-repo is registered. The learning loop is closed. What's missing is the ability to *observe and operate* the system. Every sprint without Admin UI is a sprint where operators depend on database queries and log spelunking. The aggressive roadmap demands "Admin UI core (fleet, repo, task console)" by Phase 2 end.

**Meridian verdict:** Admin UI Core is blocking. Execute tier is live but we can't observe the system or manage repos without DB access. Scaling to more repos without operational visibility is reckless. Phase 3 (evals, complexity index) is premature until we can observe what's happening.

---

## 3. References

| Reference | Path |
|-----------|------|
| Admin Control UI — Full Spec | `thestudioarc/23-admin-control-ui.md` |
| Aggressive Roadmap — Phase 2 | `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 108–135 (Admin UI core: fleet, repo, task console, RBAC) |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` (workflow states, retry/timeout) |
| Architecture Guardrails | `thestudioarc/22-architecture-guardrails.md` (security, compliance) |
| Repo Profile | `thestudioarc/04-repo-profile.md` |
| Publisher | `thestudioarc/16-publisher-github-app.md` |
| Epic 3 Complete | `docs/epics/epic-3-execute-tier-compliance.md` |

---

## 4. Acceptance Criteria (High Level)

### AC-1: Fleet Dashboard

- [ ] Dashboard shows global system health: Temporal, JetStream, Postgres, Router status (OK / DEGRADED / DOWN).
- [ ] Dashboard shows aggregate workflow metrics: running, stuck (> configurable threshold), failed, queue depth.
- [ ] Dashboard shows per-repo summary: repo name, tier, status, queue depth, running workflows, stuck count, 24h pass rate.
- [ ] Hot alerts surface: repos with elevated verification failures, workflows stuck beyond threshold, compliance drift.
- [ ] Dashboard refreshes at configurable interval (default: 30s) or on-demand.

### AC-2: Repo Management

- [ ] Operators can list all registered repos with tier, status, health, and installation info.
- [ ] Operators can register a new repo (owner, repo, installation_id, default_branch) — starts at Observe tier.
- [ ] Operators can view/edit Repo Profile: language, build commands, required checks, risk paths.
- [ ] Operators can set tier (Observe / Suggest / Execute) — Execute requires compliance check pass.
- [ ] Operators can pause repo (stop accepting new tasks; in-flight drain or freeze).
- [ ] Operators can disable writes (Publisher freeze) independently of pause.
- [ ] Operators can delete registration (soft-delete; retain audit trail).
- [ ] All repo management actions emit audit events with actor, action, timestamp, before/after state.

### AC-3: Task and Workflow Console

- [ ] Operators can list active workflows (running, paused, stuck) filtered by repo, status, and age.
- [ ] Operators can view workflow detail: TaskPacket ID, issue reference, status, current step, attempt count, complexity.
- [ ] Timeline view shows workflow steps with timestamps: Context built, Intent created, Experts consulted, Plan assembled, Implementation, Verification (attempts), QA, Publish.
- [ ] Evidence trail: for each step, show outcome (ok/failed), failure reason, evidence (lint errors, test failures).
- [ ] Safe rerun controls: Rerun Verification, Send to Agent for Fix, Escalate to Human.
- [ ] Escalation visibility: show escalation trigger, owner, and human wait state.
- [ ] Workflow detail includes retry info: next retry time, time in current step, attempt count for step.

### AC-4: RBAC for Admin Actions

- [ ] Admin actions (tier change, pause, disable writes, delete, rerun) require authenticated user.
- [ ] Role-based access: Admin (all actions), Operator (view + limited actions), Viewer (read-only).
- [ ] RBAC checks are enforced at API level, not just UI.
- [ ] RBAC config is stored in a persistent config (not hardcoded).

### AC-5: Audit Log for Admin Actions

- [ ] All admin actions are logged to `admin_audit_log` table: actor, action, target (repo/workflow), timestamp, before_state, after_state, reason (optional).
- [ ] Audit log is queryable via API with filters: actor, action type, target, date range.
- [ ] Audit log is append-only (no deletions or modifications).
- [ ] Audit log entries link to correlation_id where applicable.

### AC-6: UI Technology and Deployment

- [ ] Admin UI is a separate frontend application (React or similar) consuming backend APIs.
- [ ] Admin UI is deployable as a static site or containerized app.
- [ ] Admin UI supports basic auth or OAuth for authentication (integration with existing auth system).
- [ ] Admin UI has responsive layout for desktop use (mobile optimization is non-goal).

---

## 5. Constraints & Non-Goals

### Constraints

- **Architecture:** Build to `thestudioarc/23-admin-control-ui.md` and referenced docs. When the build diverges, update the docs or fix the build.
- **Backend first:** API endpoints must be complete and tested before UI development. UI consumes APIs.
- **RBAC enforced at API:** UI hides unauthorized actions, but API enforces access control.
- **Audit everything:** No admin action without audit log entry.
- **Small diffs:** One commit per story. Prefer focused changes.
- **Mypy in the edit loop:** Run mypy during implementation, not just at the end.
- **Observability:** All API endpoints emit OpenTelemetry spans with correlation_id.

### Non-Goals

- **Expert Performance Console:** Expert weights, confidence, drift by repo/context. That's Phase 3.
- **Metrics and Trends Dashboard:** Historical graphs, single-pass success trends, cycle time. Phase 3.
- **Policy and Guardrails Console:** Mandatory coverage triggers, violations, policy blocks. Phase 4.
- **Model Spend Dashboard:** Cost by repo, step, provider. Phase 4.
- **Quarantine Operations UI:** View/replay quarantined events. Phase 4.
- **Tool Hub Governance:** Approved catalogs, tool profiles. Phase 4.
- **Provider Controls:** Disable provider per repo, force conservative routing. Phase 4.
- **Ingress Dedupe Visibility:** Deduped webhook events. Phase 4.
- **Merge Mode Controls:** Auto-merge settings. Phase 4.
- **Mobile-optimized UI:** Admin UI is desktop-focused.
- **Real-time WebSocket updates:** Polling is sufficient for MVP. WebSocket is a later enhancement.

---

## 6. Stakeholders & Roles

| Role | Responsibility |
|------|----------------|
| **Saga** | Epic definition (this document) |
| **Meridian** | Epic review and plan review |
| **Helm** | Sprint planning and order of work |
| **Developer(s)** | Implementation per stories |
| **thestudioarc/** | Source of truth for architecture |
| **Operators** | Primary users of Admin UI |

---

## 7. Success Metrics

| Metric | Target | How measured |
|--------|--------|-------------|
| **Fleet Dashboard shows health** | All 4 services visible (Temporal, JetStream, Postgres, Router) | Manual verification |
| **Per-repo status visible** | All registered repos shown with tier, queue, workflows | Dashboard inspection |
| **Repo management actions work** | Register, set tier, pause, disable writes succeed via UI | Functional test |
| **Stuck workflows identifiable** | Workflows > threshold duration visible and actionable | Workflow Console test |
| **Safe rerun works** | Rerun Verification triggers workflow retry | Functional test |
| **RBAC enforces access** | Unauthorized actions rejected at API (403) | API test |
| **Audit log captures all actions** | 100% of admin actions logged with actor, action, target | Audit log query |
| **Admin UI deployable** | UI runs in container or as static site with backend | Deployment test |

---

## 8. Context & Assumptions

### Dependencies

| Dependency | Status | Owner |
|------------|--------|-------|
| Epic 3 codebase (compliance checker, promotion API, audit trail) | Complete | — |
| PostgreSQL, Temporal, NATS JetStream | Running | Infra (Epic 0/1) |
| Repo Profile with Observe/Suggest/Execute tiers | Complete (Epic 1, 3) | — |
| Compliance results persisted (`compliance_results` table) | Complete (Epic 3) | — |
| Tier transitions audit trail (`tier_transitions` table) | Complete (Epic 3) | — |
| Workflow state in Temporal | Complete (Epic 0/1) | — |
| thestudioarc/23-admin-control-ui.md | Published | — |

### Assumptions

- Backend APIs can query Temporal for workflow status, queue depth, and step details.
- JetStream and Postgres health can be checked via simple ping/connection queries.
- The existing in-memory repo registry will be migrated to database persistence as part of this epic.
- Frontend can be developed in parallel with backend APIs once API contracts are defined.
- RBAC can use simple role assignment initially (user → roles mapping) without complex permission hierarchies.
- Audit log schema is straightforward (actor, action, target, timestamp, before/after JSON).

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frontend technology choice delays | Medium | Start with backend API; use simple React app; no complex framework |
| Temporal query API complexity | Medium | Spike Temporal visibility API early; document query patterns |
| RBAC scope creep | Medium | Define 3 roles (Admin, Operator, Viewer) only; defer fine-grained permissions |
| Audit log volume | Low | Index on timestamp and actor; consider retention policy for Phase 4 |
| Safe rerun idempotency | Medium | Rerun uses same idempotency mechanisms as original workflow; test carefully |
| Repo registry database migration | Medium | Add migration story; test with existing in-memory data; backward compatible |

---

## Story Decomposition (Preliminary)

Stories should be broken into vertical slices that deliver testable value. Helm will refine ordering, sizing, and sprint boundaries.

**Requirement (Meridian):** Before any story enters a sprint, Helm must define a per-story Definition of Done with testable criteria that references the specific thestudioarc doc. No story is sprint-ready without this.

| Story ID | Title | Dependencies | Size Estimate |
|----------|-------|-------------|---------------|
| 4.1 | Repo Registry Database Persistence | Epic 3 codebase, Postgres | M |
| 4.2 | Fleet Dashboard API — system health endpoints | 4.1, Temporal/JetStream/Postgres | M |
| 4.3 | Fleet Dashboard API — workflow and queue metrics | 4.2, Temporal visibility | M |
| 4.4 | Repo Management API — list, register, update profile | 4.1 | M |
| 4.5 | Repo Management API — tier change, pause, disable writes | 4.4, compliance checker | M |
| 4.6 | Task and Workflow Console API — list, detail, timeline | 4.3 | L |
| 4.7 | Task and Workflow Console API — safe rerun controls | 4.6 | M |
| 4.8 | RBAC — role definitions, API enforcement | 4.4 | M |
| 4.9 | Audit Log — schema, logging, query API | 4.8 | M |
| 4.10 | Admin UI Frontend — Fleet Dashboard | 4.2, 4.3 | M |
| 4.11 | Admin UI Frontend — Repo Management | 4.4, 4.5 | M |
| 4.12 | Admin UI Frontend — Workflow Console | 4.6, 4.7 | L |
| 4.13 | Admin UI Frontend — Auth, RBAC integration | 4.8 | S |
| 4.14 | Admin UI Deployment — container, static build | 4.10–4.13 | S |

**Total:** 14 stories, ~2 sprints (4–6 weeks)

---

## Sprint Recommendation

Given the scope (14 stories, backend + frontend), this epic should be split into two sprints:

**Sprint 1: Backend APIs + Database (2–3 weeks)**
- 4.1: Repo registry database persistence
- 4.2: Fleet Dashboard API — health
- 4.3: Fleet Dashboard API — workflow metrics
- 4.4: Repo Management API — list, register, update
- 4.5: Repo Management API — tier, pause, writes
- 4.6: Workflow Console API — list, detail, timeline
- 4.7: Workflow Console API — safe rerun
- 4.8: RBAC — role definitions, API enforcement
- 4.9: Audit Log — schema, logging, query

**Sprint 1 Goal (testable):** All Admin UI backend APIs are complete and pass integration tests. Repo registry is database-backed. RBAC and audit log are enforced. A human or script can perform all admin operations via API.

**Sprint 2: Frontend + Deployment (2–3 weeks)**
- 4.10: Fleet Dashboard UI
- 4.11: Repo Management UI
- 4.12: Workflow Console UI
- 4.13: Auth and RBAC integration
- 4.14: Deployment

**Sprint 2 Goal (testable):** Admin UI is deployed and operators can view fleet health, manage repos, and inspect/rerun workflows through a web interface with RBAC enforced.

---

*Epic created by Saga. Awaiting Meridian review before commit.*
