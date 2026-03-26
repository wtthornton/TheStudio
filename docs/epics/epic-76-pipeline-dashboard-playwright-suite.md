# Epic 76 -- Pipeline Dashboard: Playwright Full-Stack Test Suite

**Status:** COMPLETE (all 14 stories delivered, 2026-03-26)
**Priority:** P1 -- High
**Estimated LoE:** ~8-10 days (1 developer, autonomous Ralph loops)
**Dependencies:** Epic 58 (Playwright Test Infrastructure -- COMPLETE)

---

## 1. Title

**Complete Playwright Coverage for React Pipeline Dashboard -- 12 Tabs, 6 Test Types Each**

## 2. Narrative

The React Pipeline Dashboard at `/dashboard/` is now the primary operator interface.
It serves 12 tabbed views covering the full lifecycle -- pipeline visualization,
triage, intent review, routing, backlog management, trust configuration, budget
tracking, activity logs, analytics, reputation, repository settings, and API
reference. Together, these tabs are where operators spend 90%+ of their time.

Despite this criticality, the dashboard has **zero Playwright test coverage**.

The Admin UI (`/admin/ui/*`) has complete coverage: every page gets 6 test files
(intent, API, style, interactions, accessibility, snapshot) using the shared
assertion library built in Epic 58. Epics 59-75 delivered this coverage
systematically. The React dashboard has no equivalent.

This means:
- Regressions in the React frontend are invisible until a human notices them.
- Style guide violations accumulate silently.
- Accessibility gaps go undetected.
- Visual drift between tabs has no baseline to compare against.

This epic replicates the proven 6-file pattern for all 12 dashboard tabs, producing
72 test files plus infrastructure. Style tests are **expected to fail initially** --
the failures become the roadmap for Epic 77 (style compliance remediation).

## 3. References

- **Style guide:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` (canonical)
- **Test library:** `tests/playwright/lib/` -- `style_assertions.py`, `component_validators.py`, `typography_assertions.py`, `interaction_helpers.py`, `accessibility_helpers.py`, `snapshot_helpers.py`
- **Admin UI test pattern:** `tests/playwright/test_dashboard_*.py` (Epic 59), `tests/playwright/test_repos_*.py` (Epic 60), etc.
- **Cross-page compliance:** `tests/playwright/test_style_guide_compliance.py`
- **Frontend source:** `frontend/src/App.tsx` (tab routing), `frontend/src/components/` (tab components)
- **Dashboard API:** `src/dashboard/router.py` (aggregates 15 sub-routers under `/api/v1/dashboard/`)
- **Tab list:** `frontend/src/App.tsx` lines 59-76, `VALID_TABS` array

## 4. Acceptance Criteria

- [ ] All 12 dashboard tabs have intent tests validating that each tab renders its core semantic content (headings, data regions, empty states)
- [ ] All 12 dashboard tabs have API tests verifying their backing `/api/v1/dashboard/*` endpoints return 200 with valid JSON
- [ ] All 12 dashboard tabs have style tests using `style_assertions.py`, `component_validators.py`, and `typography_assertions.py` against the live rendered DOM
- [ ] All 12 dashboard tabs have interaction tests validating buttons, tab switching, modals, form submissions, and navigation
- [ ] All 12 dashboard tabs have accessibility tests for WCAG 2.2 AA (focus indicators, ARIA landmarks, keyboard navigation, touch targets)
- [ ] All 12 dashboard tabs have visual snapshot baselines captured and committed to `tests/playwright/snapshots/pipeline-dashboard/`
- [ ] A cross-tab parametrized compliance test suite covers typography, spacing, and component recipes across all 12 tabs in a single file
- [ ] Conftest additions provide `dashboard_navigate(page, base_url, tab)` helper and `DASHBOARD_TABS` registry
- [ ] Zero console errors during test execution (captured via `console_errors` fixture)
- [ ] All 72+ test files follow the naming convention `tests/playwright/pipeline_dashboard/test_pd_{tab}_{type}.py`
- [ ] Tests run successfully against the Docker Compose stack (port 9080)

### 4b. Top Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SPA tab routing differs from Admin UI server-rendered pages | Tests navigate to `/dashboard/?tab=pipeline` not `/admin/ui/pipeline` -- selectors need query-param awareness | Story 76.1 builds tab navigation helper that handles SPA routing |
| React components may lack data-testid attributes | Selectors must fall back to semantic queries (role, text, ARIA) | Document fallback strategy in conftest; flag missing testids for future sprint |
| Style tests will fail (expected) | Large xfail count may obscure real failures | Use `pytest.mark.xfail(reason="Style guide compliance -- Epic 77")` so passes are visible |
| SSE connection required for pipeline tab data | Tests may time out waiting for SSE events | Mock SSE or test against static DOM after initial load |

## 5. Constraints & Non-Goals

### Constraints
- Tests MUST use the existing `tests/playwright/lib/` helpers -- no parallel assertion libraries
- Tests MUST run against the Docker Compose stack, not a dev server
- SPA navigation: all tabs share the same base URL `/dashboard/` with `?tab=` query parameter
- The `navigate()` helper from conftest expects a 200 response from the SPA catch-all route
- Authentication: uses the same `browser_context_args` fixture (X-User-ID header + optional Caddy basic auth)

### Non-Goals
- **NOT** fixing style guide violations found by the tests (that is Epic 77)
- **NOT** adding data-testid attributes to React components (separate story/epic)
- **NOT** testing the Setup Wizard overlay (separate concern, has its own Vitest coverage)
- **NOT** testing SSE real-time updates (covered by Vitest unit tests in `frontend/src/`)
- **NOT** covering the `/admin/ui/*` pages (already covered by Epics 59-75)

## 6. Stakeholders & Roles

| Role | Who |
|------|-----|
| Epic Owner | Solo developer |
| Implementer | Ralph (autonomous AI agent loops) |
| QA / Review | Meridian review on epic, Playwright CI on implementation |
| External | None |

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Tab test coverage | 12/12 tabs with all 6 test types |
| Total test files created | 74 (72 tab tests + conftest + cross-tab compliance) |
| Intent + API + interaction + a11y tests passing | 100% pass rate |
| Style tests | Documented xfail count feeds Epic 77 backlog |
| Snapshot baselines captured | 12 (one per tab) |
| Console errors across all tabs | 0 |

## 8. Context & Assumptions

### Business Rules
- The dashboard is a React SPA served from `frontend/dist/` via FastAPI static mount
- Tab routing is client-side: URL stays at `/dashboard/` with `?tab=` query parameter
- The SPA catch-all at `/dashboard/{rest_of_path:path}` always returns `index.html`
- API endpoints live under `/api/v1/dashboard/` with 15 sub-routers (events, tasks, gates, activity, planning, board, steering, trust, budget, notification, github, pr, analytics, reputation, auto_merge)

### Dependencies
- Docker Compose stack must be running (healthz check at port 9080)
- `frontend/dist/` must be built (`cd frontend && npm run build`)
- `infra/.env` must have `ADMIN_PASSWORD` in plaintext for Caddy auth

### Systems Affected
- `tests/playwright/` -- new subdirectory `pipeline_dashboard/` with 72+ test files
- `tests/playwright/conftest.py` -- new fixtures for SPA tab navigation
- `tests/playwright/snapshots/pipeline-dashboard/` -- new snapshot directory

### Assumptions
- React components render meaningful text content discoverable via `page.locator("body").inner_text()` or semantic selectors
- Tabs that require a selected task (intent, routing) will show an empty state when no task is selected -- tests validate the empty state
- API endpoints return valid JSON even when the database has no data (empty lists, default objects)
- The `?tab=` parameter is reliably synced to the URL by the React `useEffect` in `App.tsx`

---

## Stories

### File Layout Convention

All test files live under `tests/playwright/pipeline_dashboard/` with the naming pattern:
```
test_pd_{tab}_{type}.py
```
where `{tab}` is one of the 12 tab slugs and `{type}` is one of: `intent`, `api`, `style`, `interactions`, `a11y`, `snapshot`.

### Story Map

| # | Story | Points | Files to Create | Ralph Sub-tasks |
|---|-------|--------|-----------------|-----------------|
| 76.1 | **Test Infrastructure -- SPA conftest & tab helpers** | 3 | `tests/playwright/pipeline_dashboard/__init__.py`, `tests/playwright/pipeline_dashboard/conftest.py` | 1 loop |
| 76.2 | **Pipeline tab tests** (6 files) | 5 | `test_pd_pipeline_intent.py`, `test_pd_pipeline_api.py`, `test_pd_pipeline_style.py`, `test_pd_pipeline_interactions.py`, `test_pd_pipeline_a11y.py`, `test_pd_pipeline_snapshot.py` | 3 loops (2 files each) |
| 76.3 | **Triage tab tests** (6 files) | 5 | `test_pd_triage_intent.py`, `test_pd_triage_api.py`, `test_pd_triage_style.py`, `test_pd_triage_interactions.py`, `test_pd_triage_a11y.py`, `test_pd_triage_snapshot.py` | 3 loops |
| 76.4 | **Intent Review tab tests** (6 files) | 5 | `test_pd_intent_intent.py`, `test_pd_intent_api.py`, `test_pd_intent_style.py`, `test_pd_intent_interactions.py`, `test_pd_intent_a11y.py`, `test_pd_intent_snapshot.py` | 3 loops |
| 76.5 | **Routing Review tab tests** (6 files) | 5 | `test_pd_routing_intent.py`, `test_pd_routing_api.py`, `test_pd_routing_style.py`, `test_pd_routing_interactions.py`, `test_pd_routing_a11y.py`, `test_pd_routing_snapshot.py` | 3 loops |
| 76.6 | **Backlog Board tab tests** (6 files) | 5 | `test_pd_board_intent.py`, `test_pd_board_api.py`, `test_pd_board_style.py`, `test_pd_board_interactions.py`, `test_pd_board_a11y.py`, `test_pd_board_snapshot.py` | 3 loops |
| 76.7 | **Trust Tiers tab tests** (6 files) | 5 | `test_pd_trust_intent.py`, `test_pd_trust_api.py`, `test_pd_trust_style.py`, `test_pd_trust_interactions.py`, `test_pd_trust_a11y.py`, `test_pd_trust_snapshot.py` | 3 loops |
| 76.8 | **Budget tab tests** (6 files) | 5 | `test_pd_budget_intent.py`, `test_pd_budget_api.py`, `test_pd_budget_style.py`, `test_pd_budget_interactions.py`, `test_pd_budget_a11y.py`, `test_pd_budget_snapshot.py` | 3 loops |
| 76.9 | **Activity Log tab tests** (6 files) | 5 | `test_pd_activity_intent.py`, `test_pd_activity_api.py`, `test_pd_activity_style.py`, `test_pd_activity_interactions.py`, `test_pd_activity_a11y.py`, `test_pd_activity_snapshot.py` | 3 loops |
| 76.10 | **Analytics tab tests** (6 files) | 5 | `test_pd_analytics_intent.py`, `test_pd_analytics_api.py`, `test_pd_analytics_style.py`, `test_pd_analytics_interactions.py`, `test_pd_analytics_a11y.py`, `test_pd_analytics_snapshot.py` | 3 loops |
| 76.11 | **Reputation tab tests** (6 files) | 5 | `test_pd_reputation_intent.py`, `test_pd_reputation_api.py`, `test_pd_reputation_style.py`, `test_pd_reputation_interactions.py`, `test_pd_reputation_a11y.py`, `test_pd_reputation_snapshot.py` | 3 loops |
| 76.12 | **Repos tab tests** (6 files) | 5 | `test_pd_repos_intent.py`, `test_pd_repos_api.py`, `test_pd_repos_style.py`, `test_pd_repos_interactions.py`, `test_pd_repos_a11y.py`, `test_pd_repos_snapshot.py` | 3 loops |
| 76.13 | **API Reference tab tests** (6 files) | 5 | `test_pd_api_intent.py`, `test_pd_api_api.py`, `test_pd_api_style.py`, `test_pd_api_interactions.py`, `test_pd_api_a11y.py`, `test_pd_api_snapshot.py` | 3 loops |
| 76.14 | **Cross-tab style compliance** (parametrized) | 5 | `tests/playwright/pipeline_dashboard/test_pd_cross_tab_compliance.py` | 2 loops |

**Total:** 73 points | 74 files (1 `__init__.py` + 1 conftest + 72 test files)

### Vertical Slice Order (Risk-Reduction Priority)

1. **Slice 1 (Foundation):** Story 76.1 -- infrastructure must land first; all other stories depend on it
2. **Slice 2 (Highest-traffic tabs):** Stories 76.2 (Pipeline), 76.3 (Triage) -- the two most-used tabs
3. **Slice 3 (Planning tabs):** Stories 76.4 (Intent), 76.5 (Routing), 76.6 (Board) -- tabs with empty-state complexity
4. **Slice 4 (Configuration tabs):** Stories 76.7 (Trust), 76.8 (Budget) -- settings pages with forms
5. **Slice 5 (Monitoring tabs):** Stories 76.9 (Activity), 76.10 (Analytics) -- data-heavy views
6. **Slice 6 (Reference tabs):** Stories 76.11 (Reputation), 76.12 (Repos), 76.13 (API) -- lower-risk tabs
7. **Slice 7 (Cross-cutting):** Story 76.14 -- runs after all tab tests are in place

### Ralph Loop Sizing

Each story produces 6 test files. Ralph should split each story into 3 sub-tasks of 2 files each:
- Sub-task A: intent + api (semantic content and endpoint verification)
- Sub-task B: style + interactions (visual compliance and behavior)
- Sub-task C: a11y + snapshot (accessibility and visual baseline)

Each sub-task reads 3-5 reference files (existing admin test, lib helper, component source) and creates 2 files. Well within Ralph's 15-minute loop budget.

---

## Story Details

### 76.1 -- Test Infrastructure: SPA conftest & tab helpers

**Goal:** Provide reusable fixtures and helpers for navigating the React SPA dashboard tabs.

**Files to create:**
- `tests/playwright/pipeline_dashboard/__init__.py` (empty, marks as package)
- `tests/playwright/pipeline_dashboard/conftest.py`

**Conftest must provide:**
```python
DASHBOARD_URL = "/dashboard/"

DASHBOARD_TABS = {
    "pipeline": {"label": "Pipeline", "query": "?tab=pipeline"},
    "triage": {"label": "Triage", "query": "?tab=triage"},
    "intent": {"label": "Intent Review", "query": "?tab=intent"},
    "routing": {"label": "Routing Review", "query": "?tab=routing"},
    "board": {"label": "Backlog", "query": "?tab=board"},
    "trust": {"label": "Trust Tiers", "query": "?tab=trust"},
    "budget": {"label": "Budget", "query": "?tab=budget"},
    "activity": {"label": "Activity Log", "query": "?tab=activity"},
    "analytics": {"label": "Analytics", "query": "?tab=analytics"},
    "reputation": {"label": "Reputation", "query": "?tab=reputation"},
    "repos": {"label": "Repos", "query": "?tab=repos"},
    "api": {"label": "API", "query": "?tab=api"},
}

def dashboard_navigate(page, base_url: str, tab: str) -> None:
    """Navigate to a dashboard tab. Handles SPA routing."""
    url = f"{base_url}{DASHBOARD_URL}{DASHBOARD_TABS[tab]['query']}"
    navigate(page, url)
    # Wait for tab content to render
    page.wait_for_timeout(500)
```

**Key design decisions:**
- Imports `navigate` from the root conftest (no duplication)
- Adds a short wait after navigation because React SPA needs time to hydrate tab content
- Provides `DASHBOARD_TABS` registry so parametrized tests can iterate all tabs
- Re-exports `console_errors` fixture from root conftest

### 76.2 -- Pipeline Tab Tests

**What it tests:** The `pipeline` tab renders PipelineStatus (stage cards), EventLog, GateInspector, Minimap, LoopbackOverlay, and the empty pipeline state.

**Intent tests verify:** Stage names (Intake, Context, Intent, Router, Assembler, Implement, Verify, QA, Publish) appear in body text; either pipeline rail or empty-pipeline-rail renders; event log and gate inspector sections present.

**API endpoints tested:** `GET /api/v1/dashboard/events/stream` (SSE), `GET /api/v1/dashboard/tasks`, `GET /api/v1/dashboard/gates`.

**Style tests verify:** Cards use style guide token colors, typography follows heading scale, stage cards use correct status colors.

**Interaction tests verify:** Stage card click opens StageDetailPanel, task click opens TaskTimeline, Minimap task dots are clickable, tab buttons switch views.

**A11y tests verify:** ARIA landmarks (nav, main), keyboard navigation between stage cards, focus visible on interactive elements, touch targets >= 44px.

**Snapshot:** Captures pipeline tab in default (empty) state.

### 76.3 -- Triage Tab Tests

**What it tests:** The `triage` tab renders TriageQueue with incoming issues, accept/reject actions, and priority sorting.

**Intent tests verify:** "Triage" heading or queue heading present; issue cards show title, repo, priority; empty state shown when queue is empty.

**API endpoints tested:** `GET /api/v1/dashboard/tasks?status=triaging`, `POST /api/v1/dashboard/tasks/{id}/triage`.

**Style tests verify:** Priority badges use correct status colors, card components follow style guide recipes, button colors match primary/destructive variants.

**Interaction tests verify:** Accept button triggers triage action, reject/snooze actions available, card click expands details.

**A11y tests verify:** Form labels on triage actions, focus management after accept/reject, list semantics on queue items.

**Snapshot:** Captures triage tab in empty-queue state.

### 76.4 -- Intent Review Tab Tests

**What it tests:** The `intent` tab shows IntentEditor when a task is selected, or an EmptyState with "No Task Selected" heading when none is selected.

**Intent tests verify:** Empty state shows "No Task Selected" heading with description text and action buttons ("Go to Pipeline", "Open Backlog"); data-testid="intent-no-task-state" present.

**API endpoints tested:** `GET /api/v1/dashboard/planning/intent/{task_id}`.

**Style tests verify:** Empty state component follows style guide recipe (validate_empty_state), action buttons use correct colors.

**Interaction tests verify:** "Go to Pipeline" button switches to pipeline tab, "Open Backlog" button switches to board tab.

**A11y tests verify:** Empty state has appropriate heading hierarchy, action buttons have accessible names, focus order is logical.

**Snapshot:** Captures intent tab in empty state (no task selected).

### 76.5 -- Routing Review Tab Tests

**What it tests:** The `routing` tab shows RoutingPreview when a task is selected, or an EmptyState with "No Task Selected" heading.

**Intent tests verify:** Empty state shows "No Task Selected" heading; description mentions "expert routing"; action buttons present; data-testid="routing-no-task-state".

**API endpoints tested:** `GET /api/v1/dashboard/planning/routing/{task_id}`.

**Style tests verify:** Empty state follows style guide, expert cards (when visible) use component recipes.

**Interaction tests verify:** "Go to Pipeline" and "Open Backlog" navigation buttons work.

**A11y tests verify:** Same pattern as intent tab empty state.

**Snapshot:** Captures routing tab in empty state.

### 76.6 -- Backlog Board Tab Tests

**What it tests:** The `board` tab renders BacklogBoard with columns (e.g., Queued, In Progress, Done), task cards, and column counts.

**Intent tests verify:** Board heading present; column headers render; task cards show title and status; empty board state handled.

**API endpoints tested:** `GET /api/v1/dashboard/board/preferences`, `GET /api/v1/dashboard/tasks`.

**Style tests verify:** Board columns use card recipe, task cards follow badge and typography standards, column headers use heading scale.

**Interaction tests verify:** Task card click navigates to pipeline tab with task selected, drag-and-drop columns (if implemented), create-task action.

**A11y tests verify:** Column regions have ARIA labels, card list uses appropriate list semantics, keyboard navigation between columns.

**Snapshot:** Captures board tab in default state.

### 76.7 -- Trust Tiers Tab Tests

**What it tests:** The `trust` tab renders TrustConfiguration with tier rules (Observe, Suggest, Execute), promotion/demotion controls.

**Intent tests verify:** "Trust" or "Trust Tiers" heading present; tier names (Observe, Suggest, Execute) displayed; rule configuration visible or empty state.

**API endpoints tested:** `GET /api/v1/dashboard/trust/rules`, `GET /api/v1/dashboard/trust/safety-bounds`, `GET /api/v1/dashboard/trust/default-tier`.

**Style tests verify:** Trust tier badges use the correct tier colors from style guide (assert_trust_tier_colors), form inputs follow recipe.

**Interaction tests verify:** Rule creation/edit forms submit correctly, tier toggle/select works, save button triggers API call.

**A11y tests verify:** Form labels and descriptions, fieldset grouping for rule sets, focus management on form submit.

**Snapshot:** Captures trust tab in default state.

### 76.8 -- Budget Tab Tests

**What it tests:** The `budget` tab renders BudgetDashboard with cost tracking, model spend, budget caps, and alerts.

**Intent tests verify:** "Budget" heading present; cost figures or empty state displayed; model spend breakdown visible.

**API endpoints tested:** `GET /api/v1/dashboard/budget/summary`, `GET /api/v1/dashboard/budget/history`, `GET /api/v1/dashboard/budget/by-stage`, `GET /api/v1/dashboard/budget/by-model`, `GET /api/v1/dashboard/budget/config`.

**Style tests verify:** Cost figures use monospace font, budget bars use status colors (green/yellow/red for under/near/over budget), cards follow recipe.

**Interaction tests verify:** Period selector (if present) changes displayed data, budget cap edit form works.

**A11y tests verify:** Data tables have proper headers, cost figures have accessible labels, status colors have text alternatives.

**Snapshot:** Captures budget tab in default state.

### 76.9 -- Activity Log Tab Tests

**What it tests:** The `activity` tab renders SteeringActivityLog with timestamped entries of steering actions (pause, resume, reprioritize, etc.).

**Intent tests verify:** "Activity" or "Steering Activity" heading present; log entries show timestamp, action type, actor; empty state when no activity.

**API endpoints tested:** `GET /api/v1/dashboard/steering/audit`.

**Implementation note:** The `activity` tab is rendered by the else-fallthrough in `App.tsx` (line ~429), not by an explicit `activeTab === 'activity'` conditional. This is intentional — do not flag it as a bug.

**Style tests verify:** Log entries use consistent typography, timestamps use monospace, action type badges use semantic colors.

**Interaction tests verify:** Log entries are scrollable, filter/search (if present) narrows results, pagination works.

**A11y tests verify:** Log list uses proper list or table semantics, timestamps have datetime attributes, scroll region is keyboard-accessible.

**Snapshot:** Captures activity tab in default state.

### 76.10 -- Analytics Tab Tests

**What it tests:** The `analytics` tab renders the Analytics dashboard with throughput charts, bottleneck bars, category breakdown, failure analysis, and summary cards.

**Intent tests verify:** "Analytics" heading present; summary cards render (throughput, success rate, avg cycle time); chart containers present; period selector visible.

**API endpoints tested:** `GET /api/v1/dashboard/analytics/summary`, `GET /api/v1/dashboard/analytics/throughput`, `GET /api/v1/dashboard/analytics/bottlenecks`.

**Style tests verify:** Summary cards follow card recipe, chart containers have proper dimensions, period selector buttons use correct styles.

**Interaction tests verify:** Period selector changes time range, chart tooltips appear on hover (if applicable), navigation link to pipeline tab works.

**A11y tests verify:** Charts have alt text or ARIA descriptions, summary cards have heading hierarchy, period selector has accessible labels.

**Snapshot:** Captures analytics tab in default state.

### 76.11 -- Reputation Tab Tests

**What it tests:** The `reputation` tab renders the Reputation dashboard with expert performance scores, drift alerts, and outcome feed.

**Intent tests verify:** "Reputation" heading present; expert list or empty state renders; summary cards show aggregate scores.

**API endpoints tested:** `GET /api/v1/dashboard/reputation/summary`, `GET /api/v1/dashboard/reputation/experts`.

**Style tests verify:** Score indicators use status colors, expert cards follow component recipe, drift alert badges use warning colors.

**Interaction tests verify:** Expert row click opens detail view, sort/filter controls work, outcome feed scrolls.

**A11y tests verify:** Data tables have proper headers and scope, score indicators have text labels not just color, list navigation works with keyboard.

**Snapshot:** Captures reputation tab in default state.

### 76.12 -- Repos Tab Tests

**What it tests:** The `repos` tab renders RepoSettings with registered repository list, configuration forms, and health indicators.

**Intent tests verify:** "Repos" or "Repository" heading present; repo list shows name and status; configuration section visible; empty state for no repos.

**API endpoints tested:** `GET /admin/repos` (repo list), `GET /admin/repos/{repoId}` (repo detail), `GET /admin/repos/health` (fleet health).

**Style tests verify:** Repo cards follow component recipe, status badges use semantic colors, form inputs follow style guide.

**Interaction tests verify:** Repo card click opens config form, save/edit form submission, tour beacon visible.

**A11y tests verify:** Form accessibility (labels, required fields, error messages), list semantics, focus management after form actions.

**Snapshot:** Captures repos tab in default state.

### 76.13 -- API Reference Tab Tests

**What it tests:** The `api` tab renders ApiReference with OpenAPI specification viewer, endpoint list, and HTTP method badges.

**Intent tests verify:** "HTTP API" or "API" heading present; endpoint list renders; HTTP methods (GET, POST, PUT, DELETE) shown; OpenAPI spec displayed.

**API endpoints tested:** `GET /openapi.json` (the OpenAPI spec itself).

**Style tests verify:** HTTP method badges use correct colors (GET=green, POST=blue, DELETE=red), endpoint paths use monospace, headings follow scale.

**Interaction tests verify:** Endpoint accordion/expand works, copy-to-clipboard (if present), search/filter endpoints.

**A11y tests verify:** Endpoint list has proper heading hierarchy, code blocks are accessible, method badges have accessible text.

**Snapshot:** Captures API tab in default state.

### 76.14 -- Cross-Tab Style Compliance (Parametrized)

**Goal:** A single parametrized test file that validates style guide compliance across all 12 dashboard tabs, analogous to `test_style_guide_compliance.py` for admin pages.

**File:** `tests/playwright/pipeline_dashboard/test_pd_cross_tab_compliance.py`

**Tests parametrized over all 12 tabs:**
- Typography: heading scale, font families, font weights
- Spacing: 4px grid compliance on cards and containers
- Component recipes: validate_card, validate_button, validate_badge on first matching element
- Colors: dark theme token compliance on backgrounds and text
- Focus rings: assert_focus_ring_color on first interactive element

**Marked with:** `pytest.mark.xfail(reason="Style guide compliance baseline -- Epic 77 remediation")` where appropriate.

---

## Meridian Review Status

**Round 1: CONDITIONAL PASS (2026-03-26)**

Verdict: 6/7 questions PASS. One gap required fixes (6 incorrect API endpoint paths).

| # | Question | Result |
|---|----------|--------|
| 1 | Goal testable and unambiguous? | PASS |
| 2 | Acceptance criteria verifiable? | PASS |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified? | PASS (minor: no target dates) |
| 5 | Success metrics measurable? | PASS |
| 6 | Agent-implementable without guessing? | GAP -- 6 incorrect API endpoints |
| 7 | Narrative compelling? | PASS |

**Fixes applied:**
- Corrected `board/columns` to `board/preferences`
- Corrected `trust/config` to `trust/rules`, `trust/safety-bounds`, `trust/default-tier`
- Corrected `budget/spend` to full endpoint list (`summary`, `history`, `by-stage`, `by-model`, `config`)
- Corrected `activity/log` and `steering/actions` to `steering/audit`
- Corrected `repos` tab endpoints to `GET /admin/repos`, `/admin/repos/{repoId}`, `/admin/repos/health`
- Added implementation note about activity tab fallthrough rendering in App.tsx
- Confirmed Epic 77 is drafted (dependency consumer of xfail results exists)
