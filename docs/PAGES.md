# TheStudio — Complete Page & Route Inventory

Generated: 2026-03-24 | Source: Playwright test rig + route definitions + `docs/URLs.md`

---

## Quick Reference

| Category | Count | Auth | Rendering |
|----------|-------|------|-----------|
| Health endpoints | 3 | None | JSON |
| Admin UI pages | 15 | Basic Auth + X-User-ID | Server-rendered HTML (Jinja2 + HTMX) |
| Admin UI partials | ~35 | Basic Auth + X-User-ID | HTML fragments (HTMX swap) |
| Admin API endpoints | ~40 | Basic Auth + X-User-ID | JSON |
| Dashboard SPA views | ~12 | Session / header | React SPA (client-side routing) |
| Dashboard API endpoints | ~70 | Session / header | JSON |
| Other API endpoints | ~15 | Varies | JSON |
| **Total** | **~190** | | |

---

## 1. Health Endpoints (Unauthenticated)

| Path | Method | Response | Purpose |
|------|--------|----------|---------|
| `/healthz` | GET | `{"status":"ok"}` | Liveness probe (Docker, load balancers) |
| `/readyz` | GET | `{"status":"ready"}` | Readiness probe (DB connectivity) |
| `/health/ralph` | GET | `{"status":"ok", "agent_mode":..., ...}` | Ralph agent runtime readiness |

---

## 2. Admin UI Pages (Server-Rendered)

All pages share a common sidebar navigation shell. Prefix: `/admin/ui`.
Authentication: Caddy Basic Auth (prod) or auto-auth (dev). `X-User-ID` header required.

### 2.1 Core Pages (Tested by Playwright)

| # | Path | Page Title | Purpose | Playwright Coverage |
|---|------|------------|---------|---------------------|
| 1 | `/admin/ui/dashboard` | Fleet Dashboard | System health (Temporal, Postgres), workflow metrics (Running/Stuck/Failed/Queue), repo activity | `test_all_pages.py::TestDashboardIntent`, `test_smoke.py`, `test_htmx_interactions.py` |
| 2 | `/admin/ui/repos` | Repo Management | Register repos, view list with tier/status badges, control processing | `test_all_pages.py::TestReposIntent`, `test_htmx_interactions.py` |
| 3 | `/admin/ui/workflows` | Workflow Console | Pipeline execution state, status filtering, workflow list | `test_all_pages.py::TestWorkflowsIntent` |
| 4 | `/admin/ui/audit` | Audit Log | Governance event log, time-range filtering, actor/target columns | `test_all_pages.py::TestAuditIntent` |
| 5 | `/admin/ui/metrics` | Metrics | Success rates, gate status, loopback breakdown, reopen attribution | `test_all_pages.py::TestMetricsIntent` |
| 6 | `/admin/ui/experts` | Expert Performance | Trust tiers (shadow/probation/trusted), confidence, drift signals | `test_all_pages.py::TestExpertsIntent` |
| 7 | `/admin/ui/tools` | Tool Hub | Tool suite catalog, approval status (observe/suggest/execute), access profiles | `test_all_pages.py::TestToolsIntent` |
| 8 | `/admin/ui/models` | Model Gateway | Model providers, class categories (fast/balanced/strong), routing rules, cost info | `test_all_pages.py::TestModelsIntent` |
| 9 | `/admin/ui/compliance` | Compliance Scorecard | Per-repo pass/fail checks, individual check list, repo selector | `test_all_pages.py::TestComplianceIntent` |
| 10 | `/admin/ui/quarantine` | Quarantine | Failed gate events, failure reason filtering, replay/delete actions | `test_all_pages.py::TestQuarantineIntent` |
| 11 | `/admin/ui/dead-letters` | Dead-Letter Inspector | Unrecoverable events, failure reasons, attempt counts | `test_all_pages.py::TestDeadLettersIntent` |
| 12 | `/admin/ui/planes` | Execution Planes | Worker clusters, health, registration, pause/resume, region info | `test_all_pages.py::TestPlanesIntent` |
| 13 | `/admin/ui/settings` | Settings | Multi-tab config hub (see sub-tabs below) | `test_all_pages.py::TestSettingsIntent`, `test_htmx_interactions.py` |

### 2.2 Settings Sub-Tabs

Settings uses HTMX tab navigation. Each tab loads a partial via `hx-get`.

| Tab ID | Tab Label | Content | Playwright Coverage |
|--------|-----------|---------|---------------------|
| `api-keys` | API Keys | Key names, masked values (`***`), reveal/update controls | `test_all_pages.py::test_settings_tab_loads`, `test_htmx_interactions.py` |
| `infrastructure` | Infrastructure | Connection strings, service addresses, pool config | `test_all_pages.py::test_settings_tab_loads`, `test_htmx_interactions.py` |
| `feature-flags` | Feature Flags | Toggleable flags with descriptions (enabled/disabled) | `test_all_pages.py::test_settings_tab_loads`, `test_htmx_interactions.py` |
| `agent-config` | Agent Config | Model selection, timeout, retries, concurrency | `test_all_pages.py::test_settings_tab_loads`, `test_htmx_interactions.py` |
| `budget-controls` | Budget Controls | Budget limits and utilization | Partial (via partials only) |
| `secrets` | Secrets | Key rotation, webhook secret regeneration | `test_all_pages.py::test_settings_tab_loads`, `test_htmx_interactions.py` |

### 2.3 Additional Pages (Route-Defined, NOT in Playwright Test Rig)

| Path | Page Title | Purpose | Notes |
|------|------------|---------|-------|
| `/admin/ui/cost-dashboard` | Cost Dashboard | Model spend visualization, budget utilization | Has partials: `model-spend`, `cost-dashboard`, `budget-utilization` |
| `/admin/ui/portfolio-health` | Portfolio Health | Cross-repo health overview | Has partial: `portfolio-health` |

### 2.4 Detail Pages (Dynamic Routes)

| Path | Page Title | Purpose | Notes |
|------|------------|---------|-------|
| `/admin/ui/repos/{repo_id}` | Repo Detail | Individual repo config, tier, merge mode, promotion history | Partial: `repo/{repo_id}`, `merge-mode/{repo_id}`, `promotion-history/{repo_id}` |
| `/admin/ui/workflows/{workflow_id}` | Workflow Detail | Individual workflow state, actions (rerun/escalate/send-to-agent) | Partial: `workflow/{workflow_id}` |
| `/admin/ui/experts/{expert_id}` | Expert Detail | Individual expert metrics, drift analysis | Partial: `expert/{expert_id}` |

---

## 3. Admin UI Partials (HTMX Fragments)

Prefix: `/admin/ui/partials`. These are HTML fragments loaded via HTMX `hx-get`/`hx-post` into the page shell.

### 3.1 Page Content Partials (GET)

| Path | Serves |
|------|--------|
| `/admin/ui/partials/dashboard` | Dashboard content |
| `/admin/ui/partials/repos` | Repos list |
| `/admin/ui/partials/repo/{repo_id}` | Repo detail |
| `/admin/ui/partials/workflows` | Workflows list |
| `/admin/ui/partials/workflow/{workflow_id}` | Workflow detail |
| `/admin/ui/partials/audit` | Audit log with filters |
| `/admin/ui/partials/metrics` | Metrics content |
| `/admin/ui/partials/experts` | Experts list |
| `/admin/ui/partials/expert/{expert_id}` | Expert detail |
| `/admin/ui/partials/tools` | Tools list |
| `/admin/ui/partials/models` | Models list |
| `/admin/ui/partials/model-spend` | Model spend data |
| `/admin/ui/partials/cost-dashboard` | Cost dashboard content |
| `/admin/ui/partials/budget-utilization` | Budget utilization |
| `/admin/ui/partials/compliance` | Compliance scorecard |
| `/admin/ui/partials/targets` | Operational targets |
| `/admin/ui/partials/quarantine` | Quarantine list |
| `/admin/ui/partials/quarantine/{id}` | Quarantine detail |
| `/admin/ui/partials/dead-letters` | Dead-letters list |
| `/admin/ui/partials/dead-letter/{id}` | Dead-letter detail |
| `/admin/ui/partials/planes` | Planes list |
| `/admin/ui/partials/merge-mode/{repo_id}` | Merge mode controls |
| `/admin/ui/partials/promotion-history/{repo_id}` | Promotion history |
| `/admin/ui/partials/portfolio-health` | Portfolio health |

### 3.2 Settings Partials (GET + POST)

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/ui/partials/settings` | GET | Settings main |
| `/admin/ui/partials/settings/api-keys` | GET/POST | API key list / create key |
| `/admin/ui/partials/settings/api-keys/reveal/{key}` | GET | Reveal masked key value |
| `/admin/ui/partials/settings/infrastructure` | GET/POST | Infra config |
| `/admin/ui/partials/settings/feature-flags` | GET/POST | Feature flag toggles |
| `/admin/ui/partials/settings/agent-config` | GET/POST | Agent config |
| `/admin/ui/partials/settings/budget-controls` | GET/POST | Budget limits |
| `/admin/ui/partials/settings/secrets` | GET | Secrets display |
| `/admin/ui/partials/settings/secrets/rotate-key` | POST | Rotate encryption key |
| `/admin/ui/partials/settings/secrets/regenerate-webhook` | POST | Regenerate webhook secret |

### 3.3 Action Partials (POST/DELETE)

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/ui/partials/quarantine/{id}/replay` | POST | Replay quarantined message |
| `/admin/ui/partials/quarantine/{id}` | DELETE | Delete quarantined message |
| `/admin/ui/partials/dead-letter/{id}` | DELETE | Delete dead-letter |
| `/admin/ui/partials/planes/register` | POST | Register new execution plane |
| `/admin/ui/partials/planes/{id}/pause` | POST | Pause plane |
| `/admin/ui/partials/planes/{id}/resume` | POST | Resume plane |
| `/admin/ui/partials/merge-mode/{repo_id}` | POST | Update merge mode |

---

## 4. Admin API Endpoints

Prefix: `/admin`. Returns JSON. Same auth as Admin UI.

### 4.1 Health & Metrics

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/health` | GET | Fleet health (Temporal, NATS, DB) |
| `/admin/workflows/metrics` | GET | Workflow metrics overview |
| `/admin/metrics/single-pass` | GET | Single-pass success metrics |
| `/admin/metrics/loopbacks` | GET | Loopback metrics |
| `/admin/metrics/reopen` | GET | Reopen metrics |
| `/admin/metrics/success-gate` | GET | Success gate metrics |
| `/admin/metrics/lead-time` | GET | Lead time metrics |
| `/admin/metrics/cycle-time` | GET | Cycle time metrics |
| `/admin/metrics/reopen-target` | GET | Reopen target metrics |

### 4.2 Repo Management

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/repos` | GET | List all repos |
| `/admin/repos` | POST | Register new repo |
| `/admin/repos/{id}` | GET | Repo detail |
| `/admin/repos/health` | GET | Repo health status |
| `/admin/repos/{id}/profile` | PATCH | Update repo profile |
| `/admin/repos/{id}/tier` | PATCH | Change repo tier |
| `/admin/repos/{id}/pause` | POST | Pause repo |
| `/admin/repos/{id}/resume` | POST | Resume repo |
| `/admin/repos/{id}/writes` | POST | Enable/disable writes |
| `/admin/repos/{id}/compliance` | GET | Get compliance status |
| `/admin/repos/{id}/compliance/evaluate` | POST | Evaluate compliance |

### 4.3 Workflow Console

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/workflows` | GET | List workflows |
| `/admin/workflows/{id}` | GET | Workflow detail |
| `/admin/workflows/{id}/rerun-verification` | POST | Rerun verification |
| `/admin/workflows/{id}/send-to-agent` | POST | Send to agent |
| `/admin/workflows/{id}/escalate` | POST | Escalate workflow |

### 4.4 Audit

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/audit` | GET | Audit log query |

### 4.5 Experts

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/experts` | GET | List all experts |
| `/admin/experts/{id}` | GET | Expert detail |
| `/admin/experts/{id}/drift` | GET | Expert drift analysis |
| `/admin/experts/reload` | POST | Reload expert registry |
| `/admin/experts/registry` | GET | Expert registry |

### 4.6 Settings

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/settings` | GET | Get all settings |
| `/admin/settings/{key}` | GET | Get setting by key |
| `/admin/settings/{key}` | PUT | Update setting |
| `/admin/settings/{key}` | DELETE | Delete setting |

### 4.7 Tool Hub

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/tools/catalog` | GET | List tool suites |
| `/admin/tools/catalog/{suite}` | GET | Get tool suite |
| `/admin/tools/catalog/{suite}/promote` | POST | Promote tool suite |
| `/admin/tools/profiles` | GET | List tool profiles |
| `/admin/tools/check-access` | POST | Check tool access |

### 4.8 Model Gateway

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/models/route` | POST | Route model request |
| `/admin/models/providers` | GET | List model providers |
| `/admin/models/providers/{id}` | PATCH | Update provider |
| `/admin/models/audit` | GET | Model audit trail |
| `/admin/models/budget/{repo_id}` | POST | Set repo budget |

### 4.9 Other Admin

| Path | Method | Purpose |
|------|--------|---------|
| `/admin/poll/run` | POST | Trigger poll run |
| `/admin/verify/{taskpacket_id}` | POST | Trigger verification |

---

## 5. Dashboard SPA (React Frontend)

Entry point: `/dashboard/`. Single-page application with client-side routing via URL query parameters.

| View (Tab) | Query Parameter | Purpose |
|------------|-----------------|---------|
| Pipeline | `?tab=pipeline` | Pipeline stage visualization |
| Triage | `?tab=triage` | Issue triage queue |
| Intent | `?tab=intent` | Intent spec editor |
| Routing | `?tab=routing` | Routing preview |
| Board | `?tab=board` | Backlog board |
| Trust | `?tab=trust` | Trust tier configuration |
| Budget | `?tab=budget` | Budget dashboard |
| Activity | `?tab=activity` | Activity log stream |
| Analytics | `?tab=analytics` | Analytics dashboard |
| Reputation | `?tab=reputation` | Expert reputation scores |
| Repos | `?tab=repos` | Repo management |
| API | `?tab=api` | API reference |

Additional query parameters: `?repo={owner/repo}` (repo context), `?task={task_id}` (focus task).

---

## 6. Dashboard API Endpoints

JSON API powering the React SPA. Mounted at root level.

### 6.1 Tasks
`POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `GET /tasks/{id}/comparison`, `GET /stages/metrics`, `GET /tasks/{id}/evidence`

### 6.2 Gates
`GET /gates`, `GET /gates/{id}`, `GET /gates/metrics`, `GET /tasks/{id}/gates`

### 6.3 Activity
`GET /tasks/{id}/activity`

### 6.4 Planning
`POST /tasks/{id}/accept`, `POST /tasks/{id}/reject`, `PATCH /tasks/{id}`, `GET /tasks/{id}/intent`, `POST /tasks/{id}/intent/approve`, `POST /tasks/{id}/intent/reject`, `PUT /tasks/{id}/intent`, `POST /tasks/{id}/intent/refine`, `GET /tasks/{id}/routing`, `POST /tasks/{id}/routing/approve`, `POST /tasks/{id}/routing/override`

### 6.5 Steering
`POST /tasks/{id}/pause`, `POST /tasks/{id}/resume`, `POST /tasks/{id}/abort`, `POST /tasks/{id}/redirect`, `POST /tasks/{id}/retry`, `GET /steering/audit`, `GET /tasks/{id}/audit`

### 6.6 Trust & Policy
`GET /trust/rules`, `POST /trust/rules`, `GET /trust/rules/{id}`, `PUT /trust/rules/{id}`, `DELETE /trust/rules/{id}`, `GET /trust/safety-bounds`, `PUT /trust/safety-bounds`, `GET /trust/default-tier`, `PUT /trust/default-tier`

### 6.7 Budget
`GET /budget/summary`, `GET /budget/history`, `GET /budget/by-stage`, `GET /budget/by-model`, `GET /budget/config`, `PUT /budget/config`

### 6.8 Analytics
`GET /analytics/throughput`, `GET /analytics/bottlenecks`, `GET /analytics/categories`, `GET /analytics/failures`, `GET /analytics/summary`

### 6.9 Reputation
`GET /reputation/experts`, `GET /reputation/experts/{id}`, `GET /reputation/outcomes`, `GET /reputation/drift`, `GET /reputation/summary`

### 6.10 Auto-Merge
`GET /auto-merge/outcomes`, `GET /auto-merge/rule-health`

### 6.11 GitHub Integration
`GET /github/issues`, `POST /github/import`, `GET /github/repos`, `GET /github/projects/config`, `PUT /github/projects/config`, `POST /github/projects/sync`

### 6.12 PR Actions
`POST /tasks/{id}/pr/approve`, `POST /tasks/{id}/pr/request-changes`

### 6.13 Notifications
`GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/mark-all-read`

### 6.14 Events
`GET /events/stream` (SSE)

### 6.15 Board
`GET /board/preferences`, `POST /board/preferences`

---

## 7. Other Endpoints

| Path | Method | Auth | Purpose |
|------|--------|------|---------|
| `/` | GET | None | 302 redirect to `/dashboard/` or `/admin/ui/` |
| `/docs` | GET | None | OpenAPI documentation (Scalar UI) |
| `/webhook/github` | POST | Webhook signature | GitHub webhook ingress |
| `/repos/register` | POST | API | Register repo (compliance API) |
| `/repos` | GET | API | List repos (compliance API) |
| `/repos/{id}/compliance` | GET | API | Check compliance |
| `/repos/{id}/eligibility/{tier}` | GET | API | Check tier eligibility |
| `/repos/{id}/promote` | POST | API | Promote repo tier |
| `/repos/{id}/demote` | POST | API | Demote repo tier |
| `/api/tasks/{id}/approve` | POST | API | Approve task |
| `/api/tasks/{id}/reject` | POST | API | Reject task |
| `/api/tasks/{id}/review` | GET | API | Review context + chat |
| `/api/tasks/{id}/review/messages` | POST | API | Send chat message |
| `/metrics` | GET | None | Readiness metrics |
| `/calibration` | GET | None | Calibration info |
| `/thresholds` | PUT | API | Update thresholds |
| `/calibrate` | POST | API | Run calibration |

---

## 8. Playwright Test Coverage Map

### Coverage Summary

| Test File | Tests | Scope |
|-----------|-------|-------|
| `test_smoke.py` | 5 | Health check, dashboard loads, console errors, system health, workflow metrics |
| `test_all_pages.py` | ~55 | All 13 core pages: heading, entities, console errors + per-page intent validation |
| `test_htmx_interactions.py` | 5 | Settings tabs, dashboard partials, repos empty state, repo registration, navigation |
| `test_rendering_quality.py` | ~100 | All 13 pages x 8 checks: HTML entities, console errors, NaN/undefined/null, purpose content, interactive elements, empty shell |
| `test_url_docs.py` | 21 | 7 documented URLs x 3 checks: returns 200, delivers purpose, no error content |

### Coverage Gaps

| Page/Route | Status | Notes |
|------------|--------|-------|
| `/admin/ui/cost-dashboard` | **NOT TESTED** | Route exists, no Playwright coverage |
| `/admin/ui/portfolio-health` | **NOT TESTED** | Route exists, no Playwright coverage |
| `/admin/ui/repos/{repo_id}` | **NOT TESTED** | Detail page, requires existing repo data |
| `/admin/ui/workflows/{workflow_id}` | **NOT TESTED** | Detail page, requires existing workflow data |
| `/admin/ui/experts/{expert_id}` | **NOT TESTED** | Detail page, requires existing expert data |
| `/dashboard/` (React SPA) | **NOT TESTED** | Entire React frontend has no Playwright coverage |
| All Dashboard API endpoints | **NOT TESTED** | ~70 JSON endpoints not covered |

### Test Configuration

| Setting | Value | Override |
|---------|-------|---------|
| Default base URL | `http://localhost:9080` | `PLAYWRIGHT_BASE_URL` |
| Default user ID | `admin` | `PLAYWRIGHT_USER_ID` |
| HTTP auth user | From `infra/.env` | `PLAYWRIGHT_HTTP_USER` |
| HTTP auth password | From `infra/.env` | `PLAYWRIGHT_HTTP_PASSWORD` |
| Stack readiness | Auto-skip if `/healthz` unreachable | — |
| pytest marker | `playwright` | `pytest -m playwright` |

---

## 9. Environment URLs

| Environment | Base URL | Admin UI | Health | API Docs |
|-------------|----------|----------|--------|----------|
| Dev (Docker) | `http://localhost:8000` | `http://localhost:8000/admin/ui/` | `http://localhost:8000/healthz` | `http://localhost:8000/docs` |
| Dev (uvicorn) | `http://localhost:8000` | `http://localhost:8000/admin/ui/` | `http://localhost:8000/healthz` | `http://localhost:8000/docs` |
| Prod (HTTP) | `http://localhost:9080` | `http://localhost:9080/admin/ui/` | `http://localhost:9080/healthz` | `http://localhost:9080/docs` |
| Prod (HTTPS) | `https://localhost:9443` | `https://localhost:9443/admin/ui/` | `https://localhost:9443/healthz` | `https://localhost:9443/docs` |
