# Epic 4 Sprint 2 Plan — Admin UI Frontend

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** Epic 4 — Admin UI Core
**Sprint Duration:** 2-3 weeks
**Capacity:** 80% commitment, 20% buffer for unknowns

---

## Sprint Goal (Testable)

**Objective:** A working Admin UI served from FastAPI renders all core modules (Fleet Dashboard, Repo Management, Workflow Console) with RBAC-enforced views and audit-logged actions. An operator can monitor fleet health, manage repos, and inspect workflows from a browser without database access or log spelunking.

**Test:** A human can:
1. Open the Admin UI in a browser and see the Fleet Dashboard with live health and workflow metrics
2. Navigate to Repo Management, view registered repos, register a new repo, change tier, pause/resume
3. Navigate to Workflow Console, filter workflows by status/repo, view timeline and evidence for a workflow
4. Trigger safe rerun, send-to-agent, or escalate from the Workflow Console
5. See different UI capabilities based on role (Viewer sees read-only; Operator sees action buttons; Admin sees everything)
6. See audit log of all actions performed in the session

**Constraint:** No new backend API work this sprint (Sprint 1 APIs are the backend). Frontend only. If an API gap is found, log it and work around it — do not expand scope.

---

## Tech Stack Decision

**Framework:** FastAPI + Jinja2 + HTMX + Tailwind CSS

**Rationale (from framework spike):**
- Python-native: no Node/npm/TypeScript toolchain, no separate build artifact
- Co-deployed with FastAPI backend as a single application
- HTMX handles interactivity (partial page swaps, polling, form submissions) with zero custom JS
- Tailwind CSS via CDN for styling (no build step needed for internal tool)
- Real-time dashboard refresh via HTMX polling (`hx-trigger="every 5s"`)
- Team velocity: Python developers write Jinja2 templates in the same codebase

**Key patterns:**
- Server-side rendering: FastAPI endpoints return HTML fragments for HTMX swaps
- RBAC enforcement: existing middleware checks role before rendering action controls
- Audit logging: existing audit service logs all POST/PATCH/DELETE actions
- No client-side state management needed

---

## Order of Work

Priority order (first to last). Cross-cutting concerns first (retro action item #2).

| Order | Story ID | Title | Depends On | Size | Status |
|-------|----------|-------|------------|------|--------|
| 1 | 4.10 | UI Foundation — Layout, Templates, Static Assets | Sprint 1 APIs | M | Complete |
| 2 | 4.11 | Fleet Dashboard View | 4.10 | M | Complete |
| 3 | 4.12 | Repo Management Views | 4.10, 4.11 | L | Complete |
| 4 | 4.13 | Workflow Console Views | 4.10, 4.11 | L | Complete |
| 5 | 4.14 | Audit Log View | 4.10 | S | Complete |
| 6 | 4.15 | RBAC-Aware UI Rendering | 4.10, 4.12, 4.13 | M | Complete |
| 7 | 4.16 | Integration Smoke Tests | 4.11-4.15 | M | Complete |

**Explicitly out of Sprint 2:**
- Expert Performance Console (Phase 3 deliverable)
- Policy and Guardrails Console (Phase 4 deliverable)
- Model Spend dashboards (Phase 4 deliverable)
- Quarantine operations UI (Phase 4 deliverable)
- WebSocket/SSE real-time push (polling is sufficient for now)

---

## Story Definitions of Done

### 4.10: UI Foundation — Layout, Templates, Static Assets

**Reference:** `thestudioarc/23-admin-control-ui.md` (all mockups share common layout)

**Acceptance Criteria:**
- [ ] Jinja2 template engine configured in FastAPI app
- [ ] Base layout template with: navigation sidebar, header with current user/role, content area, flash messages
- [ ] Navigation links: Dashboard, Repos, Workflows, Audit Log
- [ ] Static files served: HTMX (from CDN or vendored), Tailwind CSS (CDN)
- [ ] Reusable template components: status badge (OK/DEGRADED/DOWN), tier badge (OBS/SUGG/EXEC), data table, empty state
- [ ] `GET /admin/ui/` redirects to dashboard
- [ ] All pages render without JS errors
- [ ] Dark/light mode not required (light only is fine for internal tool)

**Estimation reasoning:** Medium. Jinja2 setup is straightforward. Main work is designing the base layout and reusable components. Risk: getting the navigation and layout right on first pass.

---

### 4.11: Fleet Dashboard View

**Reference:** `thestudioarc/23-admin-control-ui.md` (Fleet Dashboard mockup, lines 63-78)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/dashboard` renders Fleet Dashboard
- [ ] Global health section: Temporal, JetStream, Postgres, Router with status badges (calls `GET /admin/health`)
- [ ] Workflow summary: running, stuck, failed counts, queue depth (calls `GET /admin/workflows/metrics`)
- [ ] Repos table: repo name, tier, status, queue, running, stuck, 24h pass rate (from metrics endpoint)
- [ ] Hot alerts section: repos with elevated failure rates or stuck workflows
- [ ] Auto-refresh: health and metrics poll every 5 seconds via HTMX `hx-trigger="every 5s"`
- [ ] `checked_at` timestamp visible so operator knows data freshness

**Estimation reasoning:** Medium. Calls two existing API endpoints. Main work is layout and HTMX polling setup. Template is a direct translation of the ASCII mockup.

---

### 4.12: Repo Management Views

**Reference:** `thestudioarc/23-admin-control-ui.md` (Repo Management mockup, lines 80-100)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/repos` renders repo list with: name, tier, status, health, actions
- [ ] `GET /admin/ui/repos/{id}` renders repo detail with full profile
- [ ] Register form: owner, repo, installation_id, default_branch — submits via HTMX POST
- [ ] Profile edit form: language, build_commands, required_checks, risk_paths — submits via HTMX PATCH
- [ ] Action buttons: Change Tier (with confirmation dialog), Pause, Resume, Toggle Writes, Delete (with confirmation)
- [ ] All actions use HTMX `hx-confirm` for destructive operations
- [ ] Success/error flash messages after each action
- [ ] Duplicate registration shows 409 error inline

**Estimation reasoning:** Large. Multiple views (list, detail, forms). Most complex HTMX interaction patterns. Risk: form validation UX without JS.

---

### 4.13: Workflow Console Views

**Reference:** `thestudioarc/23-admin-control-ui.md` (Task and Workflow Console mockup, lines 102-122)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/workflows` renders workflow list with filters: repo, status, limit
- [ ] Filter controls use HTMX to swap table content without full page reload
- [ ] `GET /admin/ui/workflows/{id}` renders workflow detail with:
  - Status, step, attempt count, complexity
  - Timeline: ordered steps with timestamps, status badges, failure reasons
  - Evidence section: lint errors, test output
  - Retry info: next_retry_time, time_in_current_step
  - Escalation info: trigger, owner, human_wait_state
- [ ] Action buttons: Rerun Verification, Send to Agent, Escalate (with confirmation)
- [ ] Actions submit via HTMX POST with inline result feedback

**Estimation reasoning:** Large. Timeline view is the most complex UI component. Workflow detail has many data sections. Risk: rendering timeline clearly with server-side HTML.

---

### 4.14: Audit Log View

**Reference:** `thestudioarc/23-admin-control-ui.md` (Operational Rules, lines 143-148)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/audit` renders audit log table
- [ ] Filter controls: event_type (dropdown), actor (text), target_id (text), hours (dropdown: 1h, 6h, 24h, 7d)
- [ ] Filters apply via HTMX without full page reload
- [ ] Each row shows: timestamp, actor, event_type, target, details (expandable)
- [ ] Pagination: limit/offset with next/prev controls
- [ ] Details column expandable to show full JSON payload

**Estimation reasoning:** Small. Single table view with filters. Reuses data table component from 4.10. Simplest UI module.

---

### 4.15: RBAC-Aware UI Rendering

**Reference:** Story 4.8 RBAC definitions

**Acceptance Criteria:**
- [ ] UI reads current user role from session/header (X-User-ID -> role lookup)
- [ ] Action buttons are hidden or disabled based on role:
  - Viewer: no action buttons rendered, view-only
  - Operator: pause/resume, rerun, send-to-agent, escalate buttons visible
  - Admin: all buttons visible (register, tier change, toggle writes, delete, audit log)
- [ ] Attempting a forbidden action via URL manipulation returns 403 page
- [ ] Role indicator shown in header (e.g., "Logged in as: admin@studio (Admin)")
- [ ] Jinja2 context processor provides `current_role` to all templates

**Estimation reasoning:** Medium. Cross-cutting concern that touches all templates. Main work is the context processor and conditional rendering in each template.

---

### 4.16: Integration Smoke Tests

**Reference:** Sprint 1 Retro action item #3

**Acceptance Criteria:**
- [ ] Test suite using httpx/TestClient that renders each UI page and checks for 200 status
- [ ] Tests verify key content is present (page titles, table headers, navigation links)
- [ ] Tests verify RBAC: Viewer cannot see action buttons; Admin can
- [ ] Tests verify HTMX attributes are present on interactive elements
- [ ] At least one end-to-end flow: render repo list -> click register -> submit form -> verify repo appears
- [ ] Tests run with `pytest` using the same test infrastructure as Sprint 1

**Estimation reasoning:** Medium. Not full E2E browser tests (no Playwright needed for internal tool). httpx TestClient + HTML assertion is sufficient.

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Sprint 1 APIs (4.1-4.9) | Complete | All backend endpoints ready |
| Jinja2 | Available | Part of FastAPI ecosystem, likely already installed |
| HTMX | Available | CDN or vendored JS file (~15KB) |
| Tailwind CSS | Available | CDN for development; optional build step for production |
| thestudioarc/23-admin-control-ui.md | Published | ASCII mockups define the target UI |

No external team dependencies. All dependencies are internal and available.

---

## Cross-Cutting Concerns (Retro Action Item)

Identified early per Sprint 1 retro:
1. **Base layout and navigation** — Story 4.10, built first
2. **RBAC context processor** — Story 4.15, but the `current_role` mechanism designed in 4.10
3. **Flash messages for action feedback** — Built into base layout in 4.10
4. **Error pages (403, 404, 500)** — Built in 4.10
5. **HTMX polling pattern** — Established in 4.11, reused in 4.12-4.13

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HTMX complexity ceiling (timeline view) | Medium | Medium | Spike timeline rendering in 4.13 early; fall back to full-page render if fragment swaps are too complex |
| Form validation UX without JS | Low | Low | Server-side validation with error messages in response fragments; HTMX swaps error state inline |
| API gaps discovered during UI work | Low | Medium | Log gaps, work around with stubs; do not expand Sprint 2 scope |
| Tailwind CDN dependency | Low | Low | Vendor Tailwind CSS if CDN is not acceptable for deployment |

---

## Capacity and Buffer

- **Total stories:** 7
- **Large:** 2 (4.12 Repo Management, 4.13 Workflow Console)
- **Medium:** 4 (4.10 Foundation, 4.11 Dashboard, 4.15 RBAC UI, 4.16 Tests)
- **Small:** 1 (4.14 Audit Log)
- **Buffer:** 20%

If timeline is at risk, consider deferring:
- 4.16 (Integration Smoke Tests) — UI still works, tests come in Sprint 3
- 4.14 (Audit Log View) — Operators can query via API; UI view is nice-to-have

---

## Sprint Rituals

- **Daily standup:** 15 min, focus on blockers
- **Mid-sprint check:** After Story 4.12, assess HTMX pattern viability for remaining stories
- **Sprint review:** Demo full UI flow in browser (dashboard -> repos -> workflows -> audit)
- **Retro:** Action items for Sprint 3 or next epic

---

*Plan created by Helm. Awaiting Meridian review before sprint start.*
