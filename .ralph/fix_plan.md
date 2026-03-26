# Fix Plan — TheStudio

## Open epics — active backlog

> **Rollup:** `docs/epics/EPIC-STATUS-TRACKER.md` (2026-03-25). All non-complete epics from that tracker are listed here so Ralph and humans share one queue.

| Epic | Status | Canonical doc |
|------|--------|---------------|
| **59–74** | Proposed — Per-page Playwright full-stack test suites (16 epics × 6 stories = 96 stories, 304 pts) | `docs/epics/epic-59-dashboard-playwright-suite.md` … `epic-74-*` |
| **27** | Deferred on demand | `docs/epics/` (multi-source webhooks) |

---

## Tier 1 — Playwright Suites: High-Traffic Pages (Epics 59–65)

> **Dependency:** Epic 58 (infra, COMPLETE). Style guide updated with Epic 75 component specs (2026-03-25).
> **Pattern:** Each story creates `tests/playwright/test_{page}_{type}.py` using shared libs from `tests/playwright/lib/`.
> **Gate:** `pytest tests/playwright/` green after each epic's .6 story.
> TESTS_STATUS: DEFERRED until each epic's .6 story

### Epic 59 — Fleet Dashboard (`/admin/ui/dashboard`, 19 pts)

- [x] **59.1:** Page Intent & Semantic Content (3 pts) — Validate system health section shows Temporal/Postgres status, workflow summary shows Running/Stuck/Failed/Queue, repo activity table renders. **File:** `tests/playwright/test_dashboard_intent.py`.
- [x] **59.2:** API Endpoint Verification (3 pts) — All backing endpoints return 200 with valid JSON schema. **File:** `tests/playwright/test_dashboard_api.py`.
- [x] **59.3:** Style Guide Compliance (5 pts) — Colors, typography, spacing, component recipes match style guide §4-9. **File:** `tests/playwright/test_dashboard_style.py`.
- [x] **59.4:** Interactive Elements (3 pts) — Buttons, HTMX swaps, refresh polling, detail panel triggers. **File:** `tests/playwright/test_dashboard_interactions.py`.
- [x] **59.5:** Accessibility WCAG 2.2 AA (3 pts) — Focus indicators, keyboard nav, ARIA roles, contrast ratios via axe-core. **File:** `tests/playwright/test_dashboard_a11y.py`.
- [x] **59.6:** Visual Snapshot Baseline (2 pts) — Capture baseline screenshot, commit to repo. **File:** `tests/playwright/test_dashboard_snapshot.py`. **RUN TESTS.**

### Epic 60 — Repo Management (`/admin/ui/repos`, 19 pts)

- [x] **60.1:** Page Intent & Semantic Content (3 pts) — Repo table renders with name, tier badge, status, queue depth; empty state with CTA. **File:** `tests/playwright/test_repos_intent.py`.
- [x] **60.2:** API Endpoint Verification (3 pts) — Repo list/detail endpoints return 200, valid JSON. **File:** `tests/playwright/test_repos_api.py`.
- [x] **60.3:** Style Guide Compliance (5 pts) — Trust tier badges (§5.2), status badges (§5.1), table recipe (§9.2). **File:** `tests/playwright/test_repos_style.py`.
- [x] **60.4:** Interactive Elements (3 pts) — Row click opens detail panel (§9.14), HTMX loads detail content. **File:** `tests/playwright/test_repos_interactions.py`.
- [x] **60.5:** Accessibility WCAG 2.2 AA (3 pts) — Table headers `scope="col"`, panel ARIA, focus management. **File:** `tests/playwright/test_repos_a11y.py`.
- [x] **60.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_repos_snapshot.py`. **RUN TESTS.**

### Epic 61 — Workflow Console (`/admin/ui/workflows`, 19 pts)

- [x] **61.1:** Page Intent & Semantic Content (3 pts) — Workflow table with ID, repo, status, duration; kanban toggle visible. **File:** `tests/playwright/test_workflows_intent.py`.
- [x] **61.2:** API Endpoint Verification (3 pts) — Workflow list/detail/kanban endpoints return valid data. **File:** `tests/playwright/test_workflows_api.py`.
- [x] **61.3:** Style Guide Compliance (5 pts) — Status badges, kanban column specs (§9.15), card border colors. **File:** `tests/playwright/test_workflows_style.py`.
- [x] **61.4:** Interactive Elements (3 pts) — List/kanban toggle, drag-and-drop, row click opens detail panel, view preference persistence. **File:** `tests/playwright/test_workflows_interactions.py`.
- [x] **61.5:** Accessibility WCAG 2.2 AA (3 pts) — Kanban keyboard reorder (§9.15), drag handle ARIA, panel focus. **File:** `tests/playwright/test_workflows_a11y.py`.
- [x] **61.6:** Visual Snapshot Baseline (2 pts) — Capture both list and kanban views. **File:** `tests/playwright/test_workflows_snapshot.py`. **RUN TESTS.**

### Epic 62 — Audit Log (`/admin/ui/audit`, 19 pts)

- [x] **62.1:** Page Intent & Semantic Content (3 pts) — Event log table with timestamp, actor, action, target columns. **File:** `tests/playwright/test_audit_intent.py`.
- [x] **62.2:** API Endpoint Verification (3 pts) — Audit list endpoint returns 200, valid JSON with pagination. **File:** `tests/playwright/test_audit_api.py`.
- [x] **62.3:** Style Guide Compliance (5 pts) — Table recipe (§9.2), typography, timestamp formatting. **File:** `tests/playwright/test_audit_style.py`.
- [x] **62.4:** Interactive Elements (3 pts) — Time-range filter, pagination, row expansion. **File:** `tests/playwright/test_audit_interactions.py`.
- [x] **62.5:** Accessibility WCAG 2.2 AA (3 pts) — Table semantics, filter ARIA, keyboard pagination. **File:** `tests/playwright/test_audit_a11y.py`.
- [x] **62.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_audit_snapshot.py`. **RUN TESTS.**

### Epic 63 — Metrics (`/admin/ui/metrics`, 19 pts)

- [x] **63.1:** Page Intent & Semantic Content (3 pts) — Success rates, gate status, loopback breakdown display. **File:** `tests/playwright/test_metrics_intent.py`.
- [x] **63.2:** API Endpoint Verification (3 pts) — Metrics endpoints return valid data. **File:** `tests/playwright/test_metrics_api.py`.
- [x] **63.3:** Style Guide Compliance (5 pts) — Card recipe (§9.1), KPI typography, status colors (§5.1). **File:** `tests/playwright/test_metrics_style.py`.
- [x] **63.4:** Interactive Elements (3 pts) — Period selector, chart interactions, metric drill-down. **File:** `tests/playwright/test_metrics_interactions.py`.
- [x] **63.5:** Accessibility WCAG 2.2 AA (3 pts) — Chart alternatives, focus indicators, screen reader support. **File:** `tests/playwright/test_metrics_a11y.py`.
- [x] **63.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_metrics_snapshot.py`. **RUN TESTS.**

### Epic 64 — Expert Performance (`/admin/ui/experts`, 19 pts)

- [x] **64.1:** Page Intent & Semantic Content (3 pts) — Expert table with trust tier, confidence, drift signals. **File:** `tests/playwright/test_experts_intent.py`.
- [x] **64.2:** API Endpoint Verification (3 pts) — Expert list/detail endpoints return valid data. **File:** `tests/playwright/test_experts_api.py`.
- [x] **64.3:** Style Guide Compliance (5 pts) — Trust tier badges (§5.2), table recipe, card layout. **File:** `tests/playwright/test_experts_style.py`.
- [x] **64.4:** Interactive Elements (3 pts) — Row click opens detail, filter/sort controls. **File:** `tests/playwright/test_experts_interactions.py`.
- [x] **64.5:** Accessibility WCAG 2.2 AA (3 pts) — Table headers, badge non-color cues, focus management. **File:** `tests/playwright/test_experts_a11y.py`.
- [x] **64.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_experts_snapshot.py`. **RUN TESTS.**

### Epic 65 — Tool Hub (`/admin/ui/tools`, 19 pts)

- [x] **65.1:** Page Intent & Semantic Content (3 pts) — Tool catalog with approval status badges, profiles. **File:** `tests/playwright/test_tools_intent.py`.
- [x] **65.2:** API Endpoint Verification (3 pts) — Tool list endpoint returns valid data. **File:** `tests/playwright/test_tools_api.py`.
- [x] **65.3:** Style Guide Compliance (5 pts) — Badge recipe (§9.3), card layout, status colors. **File:** `tests/playwright/test_tools_style.py`.
- [x] **65.4:** Interactive Elements (3 pts) — Tool detail expansion, approval actions. **File:** `tests/playwright/test_tools_interactions.py`.
- [x] **65.5:** Accessibility WCAG 2.2 AA (3 pts) — Status badges non-color, keyboard nav, ARIA. **File:** `tests/playwright/test_tools_a11y.py`.
- [x] **65.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_tools_snapshot.py`. **RUN TESTS.**

---

## Tier 2 — Playwright Suites: Lower-Traffic Pages (Epics 66–74)

> Execute after Tier 1 is green. Same 6-story pattern per epic.
> TESTS_STATUS: DEFERRED until each epic's .6 story

### Epic 66 — Model Gateway (`/admin/ui/models`, 19 pts)

- [x] **66.1:** Page Intent & Semantic Content (3 pts) — Model providers, routing rules, cost info. **File:** `tests/playwright/test_models_intent.py`.
- [x] **66.2:** API Endpoint Verification (3 pts) — Model list endpoint returns valid data. **File:** `tests/playwright/test_models_api.py`.
- [x] **66.3:** Style Guide Compliance (5 pts) — Table/card recipes, cost formatting. **File:** `tests/playwright/test_models_style.py`.
- [x] **66.4:** Interactive Elements (3 pts) — Routing rule toggles, provider detail. **File:** `tests/playwright/test_models_interactions.py`.
- [x] **66.5:** Accessibility WCAG 2.2 AA (3 pts) — Table semantics, toggle ARIA, focus. **File:** `tests/playwright/test_models_a11y.py`.
- [x] **66.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_models_snapshot.py`. **RUN TESTS.**

### Epic 67 — Compliance Scorecard (`/admin/ui/compliance`, 19 pts)

- [x] **67.1:** Page Intent & Semantic Content (3 pts) — Per-repo compliance status, check results. **File:** `tests/playwright/test_compliance_intent.py`.
- [ ] **67.2:** API Endpoint Verification (3 pts) — Compliance endpoints return valid data. **File:** `tests/playwright/test_compliance_api.py`.
- [ ] **67.3:** Style Guide Compliance (5 pts) — Status colors (§5.1), badge recipe, scorecard layout. **File:** `tests/playwright/test_compliance_style.py`.
- [ ] **67.4:** Interactive Elements (3 pts) — Repo filter, check detail expansion. **File:** `tests/playwright/test_compliance_interactions.py`.
- [ ] **67.5:** Accessibility WCAG 2.2 AA (3 pts) — Status non-color cues, keyboard nav. **File:** `tests/playwright/test_compliance_a11y.py`.
- [ ] **67.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_compliance_snapshot.py`. **RUN TESTS.**

### Epic 68 — Quarantine (`/admin/ui/quarantine`, 19 pts)

- [ ] **68.1:** Page Intent & Semantic Content (3 pts) — Quarantined events table, failure reasons. **File:** `tests/playwright/test_quarantine_intent.py`.
- [ ] **68.2:** API Endpoint Verification (3 pts) — Quarantine list endpoint. **File:** `tests/playwright/test_quarantine_api.py`.
- [ ] **68.3:** Style Guide Compliance (5 pts) — Error status colors, table recipe, empty state. **File:** `tests/playwright/test_quarantine_style.py`.
- [ ] **68.4:** Interactive Elements (3 pts) — Replay/delete actions, confirmation dialogs. **File:** `tests/playwright/test_quarantine_interactions.py`.
- [ ] **68.5:** Accessibility WCAG 2.2 AA (3 pts) — Action button ARIA, dialog focus trap. **File:** `tests/playwright/test_quarantine_a11y.py`.
- [ ] **68.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_quarantine_snapshot.py`. **RUN TESTS.**

### Epic 69 — Dead-Letter Inspector (`/admin/ui/dead-letters`, 19 pts)

- [ ] **69.1:** Page Intent & Semantic Content (3 pts) — Dead-lettered events, failure reasons, attempt counts. **File:** `tests/playwright/test_dead_letters_intent.py`.
- [ ] **69.2:** API Endpoint Verification (3 pts) — Dead-letter list endpoint. **File:** `tests/playwright/test_dead_letters_api.py`.
- [ ] **69.3:** Style Guide Compliance (5 pts) — Error colors, table recipe, badge usage. **File:** `tests/playwright/test_dead_letters_style.py`.
- [ ] **69.4:** Interactive Elements (3 pts) — Event detail expansion, retry actions. **File:** `tests/playwright/test_dead_letters_interactions.py`.
- [ ] **69.5:** Accessibility WCAG 2.2 AA (3 pts) — Table semantics, action ARIA. **File:** `tests/playwright/test_dead_letters_a11y.py`.
- [ ] **69.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_dead_letters_snapshot.py`. **RUN TESTS.**

### Epic 70 — Execution Planes (`/admin/ui/planes`, 19 pts)

- [ ] **70.1:** Page Intent & Semantic Content (3 pts) — Worker clusters, health, registration status. **File:** `tests/playwright/test_planes_intent.py`.
- [ ] **70.2:** API Endpoint Verification (3 pts) — Planes list endpoint. **File:** `tests/playwright/test_planes_api.py`.
- [ ] **70.3:** Style Guide Compliance (5 pts) — Health status colors, card recipe, badges. **File:** `tests/playwright/test_planes_style.py`.
- [ ] **70.4:** Interactive Elements (3 pts) — Pause/resume actions, registration controls. **File:** `tests/playwright/test_planes_interactions.py`.
- [ ] **70.5:** Accessibility WCAG 2.2 AA (3 pts) — Action button ARIA, status non-color cues. **File:** `tests/playwright/test_planes_a11y.py`.
- [ ] **70.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_planes_snapshot.py`. **RUN TESTS.**

### Epic 71 — Settings (`/admin/ui/settings`, 19 pts)

- [ ] **71.1:** Page Intent & Semantic Content (3 pts) — 6-tab config hub: API keys, infra, flags, agent, budget, secrets. **File:** `tests/playwright/test_settings_intent.py`.
- [ ] **71.2:** API Endpoint Verification (3 pts) — Settings GET/PUT endpoints. **File:** `tests/playwright/test_settings_api.py`.
- [ ] **71.3:** Style Guide Compliance (5 pts) — Form inputs (§9.8), tab navigation, card layout. **File:** `tests/playwright/test_settings_style.py`.
- [ ] **71.4:** Interactive Elements (3 pts) — Tab switching, form submission, validation feedback. **File:** `tests/playwright/test_settings_interactions.py`.
- [ ] **71.5:** Accessibility WCAG 2.2 AA (3 pts) — Tab ARIA (`role="tablist"`), form labels, error messages. **File:** `tests/playwright/test_settings_a11y.py`.
- [ ] **71.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_settings_snapshot.py`. **RUN TESTS.**

### Epic 72 — Cost Dashboard (`/admin/ui/cost-dashboard`, 19 pts)

- [ ] **72.1:** Page Intent & Semantic Content (3 pts) — Model spend, budget utilization, cost breakdown. **File:** `tests/playwright/test_cost_dashboard_intent.py`.
- [ ] **72.2:** API Endpoint Verification (3 pts) — Cost API endpoints. **File:** `tests/playwright/test_cost_dashboard_api.py`.
- [ ] **72.3:** Style Guide Compliance (5 pts) — KPI cards, cost formatting, chart colors. **File:** `tests/playwright/test_cost_dashboard_style.py`.
- [ ] **72.4:** Interactive Elements (3 pts) — Period selector, budget threshold controls. **File:** `tests/playwright/test_cost_dashboard_interactions.py`.
- [ ] **72.5:** Accessibility WCAG 2.2 AA (3 pts) — Chart alternatives, focus indicators. **File:** `tests/playwright/test_cost_dashboard_a11y.py`.
- [ ] **72.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_cost_dashboard_snapshot.py`. **RUN TESTS.**

### Epic 73 — Portfolio Health (`/admin/ui/portfolio-health`, 19 pts)

- [ ] **73.1:** Page Intent & Semantic Content (3 pts) — Cross-repo health overview, risk distribution. **File:** `tests/playwright/test_portfolio_health_intent.py`.
- [ ] **73.2:** API Endpoint Verification (3 pts) — Portfolio health endpoints. **File:** `tests/playwright/test_portfolio_health_api.py`.
- [ ] **73.3:** Style Guide Compliance (5 pts) — Health status colors, card recipe, risk badges. **File:** `tests/playwright/test_portfolio_health_style.py`.
- [ ] **73.4:** Interactive Elements (3 pts) — Repo drill-down, risk filter. **File:** `tests/playwright/test_portfolio_health_interactions.py`.
- [ ] **73.5:** Accessibility WCAG 2.2 AA (3 pts) — Status non-color cues, keyboard nav. **File:** `tests/playwright/test_portfolio_health_a11y.py`.
- [ ] **73.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_portfolio_health_snapshot.py`. **RUN TESTS.**

### Epic 74 — Detail Pages (`/{entity}/{id}`, 19 pts)

> Note: Detail pages require seed data. Tests must create entities first or use fixtures.

- [ ] **74.1:** Page Intent & Semantic Content (3 pts) — Entity detail views for repo, workflow, expert. **File:** `tests/playwright/test_detail_pages_intent.py`.
- [ ] **74.2:** API Endpoint Verification (3 pts) — Detail endpoints return valid entity data. **File:** `tests/playwright/test_detail_pages_api.py`.
- [ ] **74.3:** Style Guide Compliance (5 pts) — Inspector panel specs (§9.14), badge usage, typography. **File:** `tests/playwright/test_detail_pages_style.py`.
- [ ] **74.4:** Interactive Elements (3 pts) — Tier change actions, navigation between entities. **File:** `tests/playwright/test_detail_pages_interactions.py`.
- [ ] **74.5:** Accessibility WCAG 2.2 AA (3 pts) — Panel ARIA, action button labels, focus management. **File:** `tests/playwright/test_detail_pages_a11y.py`.
- [ ] **74.6:** Visual Snapshot Baseline (2 pts) — Capture baseline. **File:** `tests/playwright/test_detail_pages_snapshot.py`. **RUN TESTS.**

---

## Backlog — Needs Epic (Saga → Meridian → Helm)

**P2: Production Monitoring** — alerts for pipeline failures, cost anomalies, API rate limits, health dashboard
**P3: Intake Haiku Fix** — diagnose parsing failures, tune prompt or route to Sonnet
**P3: Agent Intelligence** — LLM issue scoring (E16), adversarial classification (E20), agentic non-Primary agents (E23)
**P3: Approval/Workflow** — GitHub `/approve` command parsing (E21), fleet-wide auto-merge policies (E22)
**P3: Security** — full SAST/DAST pipeline (E19), automated secret rotation (E11)

## Deferred — On Demand

**Epic 27: Multi-Source Webhooks** — 7 stories ready, trigger: non-GitHub source demand

---

## Completed

**Epic 75 (Plane-Parity Admin UI):** All 8 stories (75.1–75.8) **complete** (2026-03-25). SVG icon system, sliding detail panel, repo/workflow detail panels, kanban board, command palette (Ctrl+K), dark mode, WCAG 2.2 AA audit. 31 pts delivered. Commits `6822cb1`–`0fe3de1`.

**Sprints 4–10 (all `[x]`):** Epics **44** (Setup Wizard, 10 stories), **45** (Contextual Help, 10 stories), **46** (Actionable Empty States, 7 stories), **47** (Product Tours, 8 stories), **48** (Scalar API Docs, 6 stories), **49** (Unified Navigation, 6 stories), **50** (Feature Spotlights, 5 stories).

**Epic 58 (Playwright Test Infrastructure):** All 7 stories (58.1–58.7) — shared assertion libs for style guide colors, typography, component recipes, API helpers, interactive elements, WCAG 2.2 AA, visual snapshots.

**Epics 38–39:** Epic 38 (GitHub Phase 4, all 4 slices, 27 stories), Epic 39 (Analytics & Learning, 24 stories).

**Epics 43, 51:** Epic 43 (Ralph SDK, 15 stories, **ops sign-off granted 2026-03-25** — production flip authorized), Epic 51 (SDK parity, all hardening tasks).

**Epics 52–57:** All stories **complete** (2026-03-25). 53.1–53.4, 54.1–54.4, 55.1–55.4, 56.1–56.4, 57.1–57.3. 74+ tests. Commits `315c922` (53.4), `b72738f` (54.3), `1634919` (54.4).

**Prior phases:** Epics **0–37** (Phases 0–8, Pipeline UI Phases 0–3), per `docs/epics/EPIC-STATUS-TRACKER.md`.

**Newly completed (2026-03-25 sync):** Epic 38 (all 4 slices), Epic 39 (all stories), Epic 43 (ops sign-off granted), Epic 51 (all tasks), Epics 52–54 (canonical UI — 53.4, 54.3, 54.4), Epic 58 (all 7 stories), Epic 75 (all 8 stories).

---

## Documentation sync (2026-03-25)

Rolled up canonical UI standard (`docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`), MCP frontend experts brief, Cursor `frontend-style-source-of-truth` rule, `EPIC-STATUS-TRACKER.md`, `TAPPS_HANDOFF.md`, `TAPPS_RUNLOG.md`, and README / AGENTS / Copilot pointers. Epic 75 (Plane-parity admin UI) created, implemented (8 stories, 31 pts), and marked complete — all commits `6822cb1`–`0fe3de1`. fix_plan optimized: collapsed completed sprints 4–10, completed epic sections (38/39/43/51/52-57), and moved Epic 75 to Completed.
