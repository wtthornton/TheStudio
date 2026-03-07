# Epic 4 Sprint 1 Plan — Admin UI Backend APIs

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** Epic 4 — Admin UI Core
**Sprint Duration:** 2–3 weeks
**Capacity:** 80% commitment, 20% buffer for unknowns

---

## Sprint Goal (Testable)

**Objective:** All Admin UI backend APIs are complete and pass integration tests. Repo registry is database-backed. RBAC and audit log are enforced at API level.

**Test:** A human or script can:
1. Query fleet health (Temporal, JetStream, Postgres, Router status)
2. Query workflow metrics (running, stuck, queue depth by repo)
3. Register a new repo, update profile, change tier, pause, disable writes
4. List and inspect workflows with timeline and evidence
5. Trigger safe rerun on a workflow
6. Fail to perform admin actions without proper role (403)
7. Query audit log for all admin actions performed

**Constraint:** No frontend work this sprint. APIs are the deliverable. UI is Sprint 2.

---

## Order of Work

Priority order (first → last). Work items depend on predecessors completing.

| Order | Story ID | Title | Depends On | Size | Status |
|-------|----------|-------|------------|------|--------|
| 1 | 4.1 | Repo Registry Database Persistence | Epic 3 | M | ✅ Complete |
| 2 | 4.2 | Fleet Dashboard API — System Health | 4.1 | M | ✅ Complete |
| 3 | 4.3 | Fleet Dashboard API — Workflow Metrics | 4.2 | M | ✅ Complete |
| 4 | 4.4 | Repo Management API — List, Register, Update | 4.1 | M | ⏳ Next |
| 5 | 4.5 | Repo Management API — Tier, Pause, Writes | 4.4 | M | ⏳ Pending |
| 6 | 4.6 | Workflow Console API — List, Detail, Timeline | 4.3 | L | ⏳ Pending |
| 7 | 4.7 | Workflow Console API — Safe Rerun | 4.6 | M | ⏳ Pending |
| 8 | 4.8 | RBAC — Role Definitions, API Enforcement | 4.4 | M | ⏳ Pending |
| 9 | 4.9 | Audit Log — Schema, Logging, Query API | 4.8 | M | ⏳ Pending |

**Explicitly out of Sprint 1:** Stories 4.10–4.14 (Frontend, Deployment). These are Sprint 2.

---

## Story Definitions of Done

### 4.1: Repo Registry Database Persistence ✅ COMPLETE

**Reference:** `thestudioarc/23-admin-control-ui.md` (Repo Registry and Controls)

**Acceptance Criteria:**
- [x] `repos` table created with migration: id (UUID), owner, repo, full_name, tier, installation_id, default_branch, created_at, updated_at, deleted_at (soft delete)
- [x] Existing in-memory registry functions (`register_repo`, `get_repo`, `list_repos`, etc.) replaced with database operations
- [x] Repo Profile fields stored in `repos` table or linked `repo_profiles` table: language, build_commands, required_checks, risk_paths
- [x] Migration is idempotent and can run on existing database
- [x] All existing tests pass with database-backed registry
- [x] New tests: create, read, update, soft-delete repo via database

**Estimation reasoning:** Medium. Schema is straightforward. Main risk is ensuring migration works with existing Epic 3 data. Unknown: whether to keep `repo_profiles` separate or inline.

**Implementation:** `src/repo/repository.py`, `src/repo/repo_profile.py` — completed prior to Sprint 1

---

### 4.2: Fleet Dashboard API — System Health ✅ COMPLETE

**Reference:** `thestudioarc/23-admin-control-ui.md` (Fleet Dashboard mockup, lines 63–78)

**Acceptance Criteria:**
- [x] `GET /admin/health` returns status for: Temporal, JetStream, Postgres, Router
- [x] Each service status is: OK, DEGRADED, or DOWN
- [x] Health check is fast (< 2s total)
- [x] Health check failures are logged with details
- [x] Response includes `checked_at` timestamp

**Estimation reasoning:** Medium. Temporal and Postgres health checks are standard. JetStream health check needs investigation (ping vs connection test). Router health is self-check (always OK if responding).

**Implementation:** `src/admin/health.py`, `src/admin/router.py` — completed prior to Story 4.3

---

### 4.3: Fleet Dashboard API — Workflow Metrics ✅ COMPLETE

**Reference:** `thestudioarc/23-admin-control-ui.md` (Fleet Dashboard mockup, lines 63–78)

**Acceptance Criteria:**
- [x] `GET /admin/workflows/metrics` returns aggregate: running, stuck, failed, queue_depth
- [x] `GET /admin/workflows/metrics?repo_id={id}` returns per-repo metrics
- [x] "Stuck" defined as: workflow in active state > configurable threshold (default: 2 hours)
- [x] Queue depth queried from Temporal task queue
- [x] Response includes 24h pass rate by repo (workflows completing verification + QA on first attempt)
- [x] Hot alerts included: repos with elevated failure rates, workflows stuck beyond threshold

**Estimation reasoning:** Medium. Main unknown is Temporal visibility API for queue depth and workflow duration. Need to spike query patterns early.

**Implementation:** `src/admin/workflow_metrics.py`, `src/admin/router.py` — completed 2026-03-06

---

### 4.4: Repo Management API — List, Register, Update

**Reference:** `thestudioarc/23-admin-control-ui.md` (Repo Management mockup, lines 80–100)

**Acceptance Criteria:**
- [ ] `GET /admin/repos` returns all registered repos with: id, owner, repo, tier, status, installation_id, health
- [ ] `POST /admin/repos` registers a new repo (owner, repo, installation_id, default_branch) — starts at Observe tier
- [ ] `GET /admin/repos/{id}` returns repo detail with full Repo Profile
- [ ] `PATCH /admin/repos/{id}/profile` updates Repo Profile (language, build_commands, required_checks, risk_paths)
- [ ] Registration emits `repo_registered` audit event
- [ ] Profile update emits `repo_profile_updated` audit event
- [ ] Duplicate registration returns 409 Conflict

**Estimation reasoning:** Medium. Uses database from 4.1. Main work is wiring endpoints and validation.

---

### 4.5: Repo Management API — Tier, Pause, Writes

**Reference:** `thestudioarc/23-admin-control-ui.md` (Repo Management mockup, lines 80–100)

**Acceptance Criteria:**
- [ ] `POST /admin/repos/{id}/tier` changes tier (Observe / Suggest / Execute)
- [ ] Execute tier change blocked unless compliance check passes (uses existing `compliance_checker`)
- [ ] `POST /admin/repos/{id}/pause` pauses repo (stops accepting new tasks)
- [ ] `POST /admin/repos/{id}/resume` resumes paused repo
- [ ] `POST /admin/repos/{id}/disable-writes` sets Publisher freeze
- [ ] `POST /admin/repos/{id}/enable-writes` clears Publisher freeze
- [ ] Each action emits audit event with before/after state
- [ ] Soft delete: `DELETE /admin/repos/{id}` sets `deleted_at`, retains record

**Estimation reasoning:** Medium. Builds on existing promotion API from Epic 3. Pause/resume requires integration with ingress (reject new tasks for paused repos). Unknown: exact pause semantics for in-flight workflows.

---

### 4.6: Workflow Console API — List, Detail, Timeline

**Reference:** `thestudioarc/23-admin-control-ui.md` (Task and Workflow Console mockup, lines 102–122)

**Acceptance Criteria:**
- [ ] `GET /admin/workflows` returns list with filters: repo_id, status (running/stuck/paused/completed/failed), age (> N hours)
- [ ] `GET /admin/workflows/{id}` returns workflow detail: TaskPacket ID, issue ref, status, current step, attempt count, complexity
- [ ] Timeline view: ordered list of steps with timestamps and outcomes (Context, Intent, Experts, Plan, Implement, Verify, QA, Publish)
- [ ] Each step includes: status (ok/failed/pending), failure_reason, evidence (lint errors, test output)
- [ ] Retry info: next_retry_time, time_in_current_step, attempt_count_for_step
- [ ] Escalation info: trigger, owner, human_wait_state

**Estimation reasoning:** Large. Requires querying Temporal workflow history for timeline and step details. Main risk is Temporal visibility API complexity. This is the most complex story in the sprint.

---

### 4.7: Workflow Console API — Safe Rerun

**Reference:** `thestudioarc/23-admin-control-ui.md` (Safe Reruns and Idempotency, lines 217–231)

**Acceptance Criteria:**
- [ ] `POST /admin/workflows/{id}/rerun-verification` triggers verification rerun from current state
- [ ] `POST /admin/workflows/{id}/send-to-agent` sends workflow back to Primary Agent for fix
- [ ] `POST /admin/workflows/{id}/escalate` marks workflow for human escalation
- [ ] Rerun respects idempotency (same TaskPacket ID, same idempotency keys)
- [ ] Rerun emits audit event with actor and reason
- [ ] Unsafe reruns (e.g., re-publish without idempotency check) are blocked with 400 error

**Estimation reasoning:** Medium. Uses existing workflow signal mechanisms. Main risk is ensuring idempotency is preserved. Unknown: exact Temporal signal patterns for rerun.

---

### 4.8: RBAC — Role Definitions, API Enforcement

**Reference:** `thestudioarc/22-architecture-guardrails.md` (security section)

**Acceptance Criteria:**
- [ ] Three roles defined: Admin (all actions), Operator (view + limited actions), Viewer (read-only)
- [ ] Role assignments stored in database (`user_roles` table: user_id, role, granted_at, granted_by)
- [ ] API middleware checks role before allowing action
- [ ] Unauthorized actions return 403 Forbidden with clear message
- [ ] Role definitions documented in code and README
- [ ] Test: Admin can do everything; Operator can view and rerun but not delete; Viewer can only read

| Role | View | Register | Update Profile | Change Tier | Pause/Writes | Rerun | Delete |
|------|------|----------|----------------|-------------|--------------|-------|--------|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Operator | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ |
| Viewer | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Estimation reasoning:** Medium. Schema is simple. Main work is middleware integration across all admin endpoints.

---

### 4.9: Audit Log — Schema, Logging, Query API

**Reference:** `thestudioarc/23-admin-control-ui.md` (Operational Rules, lines 143–148)

**Acceptance Criteria:**
- [ ] `admin_audit_log` table created: id, actor, action, target_type, target_id, before_state (JSON), after_state (JSON), reason, correlation_id, timestamp
- [ ] All admin actions (stories 4.4–4.8) log to audit table
- [ ] Audit log is append-only (no UPDATE or DELETE allowed)
- [ ] `GET /admin/audit` returns log with filters: actor, action, target_type, target_id, date_range
- [ ] Audit entries include correlation_id for traceability
- [ ] Test: perform admin actions, verify all appear in audit log

**Estimation reasoning:** Medium. Straightforward schema and logging. Main work is ensuring every action logs consistently.

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Epic 3 codebase | Complete | Compliance checker, promotion API, tier transitions |
| PostgreSQL | Running | Database for repos, audit log, RBAC |
| Temporal | Running | Workflow visibility, queue depth, signals |
| JetStream | Running | Health check target |
| thestudioarc/23-admin-control-ui.md | Published | Architecture reference |

No external team dependencies. All dependencies are internal and complete.

---

## Retro Actions Applied (from Epic 3)

| Lesson | How Applied |
|--------|-------------|
| mypy in the edit loop | Each story DoD includes "mypy passes" implicitly; run mypy after each file edit |
| One commit per story | Commit discipline: complete story → single commit with story ID in message |
| Sprint DoD is the bar | Test criteria explicit in each story DoD; no partial credit |
| Architecture docs as source of truth | Each story references specific `thestudioarc/` doc section |

---

## Capacity and Buffer

- **Total stories:** 9
- **Large:** 1 (4.6 — Workflow Console detail/timeline)
- **Medium:** 8
- **Buffer:** 20% (approximately 2 story-points worth of slack)
- **Risk items:** 4.3 and 4.6 depend on Temporal visibility API; spike early if unknown

If timeline is at risk, consider deferring:
- 4.7 (Safe Rerun) to Sprint 2 — operators can view but not rerun
- 4.9 (Audit Log query API) — logging still happens, query API deferred

---

## Sprint Rituals

- **Daily standup:** 15 min, focus on blockers
- **Mid-sprint check:** After story 4.5, assess Temporal API progress
- **Sprint review:** Demo all APIs via curl/httpie
- **Retro:** Action items for Sprint 2

---

*Plan created by Helm. Awaiting Meridian review before sprint start.*
