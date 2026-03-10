# Epic 12 — Playwright Admin UI Tests & Rendering Fixes

**Author:** Saga
**Date:** 2026-03-10
**Status:** Draft — Meridian Round 1 conditional pass, fixes applied, awaiting Round 2

---

## 1. Title

See What Users See — Add Playwright browser tests for every Admin UI page, fix HTML rendering bugs, and eliminate XSS risks in inline HTML so the UI is tested the way a real operator uses it.

## 2. Narrative

TheStudio's Admin UI has 17 full pages, 25 HTMX partials, and 13 action endpoints. The existing test suite validates these through FastAPI's `TestClient` — effectively checking that HTTP responses return 200 and contain expected HTML substrings. This catches template rendering errors and RBAC logic but misses everything a real browser does: JavaScript execution, HTMX swap behavior, CSS rendering, entity decoding, and user interaction flows.

The gap is already visible. The Repos page displays the literal text `&#9744;` instead of a checkbox symbol because the `empty_state` Jinja2 macro passes an HTML entity as a default parameter string, which Jinja2's autoescape double-encodes. This bug exists in the shipped production stack and no existing test catches it — because no test renders HTML through a browser engine.

Beyond the visible bug, a code review of `ui_router.py` reveals 6+ instances of inline HTML built with f-strings where user-sourced data (tier names, reasons, API key values) is interpolated without escaping. These are XSS vulnerabilities that unit tests don't exercise because they don't execute JavaScript.

This epic adds Playwright as the browser testing framework, creates test coverage for every Admin UI page, fixes the known rendering and security bugs, and establishes patterns for ongoing UI test maintenance.

**Roadmap linkage:** The Admin UI is the operator's primary interface. As TheStudio moves toward processing real workloads (Epic 11 prerequisite met), operators will rely on this UI for repo management, workflow monitoring, and incident response. Untested UI pages are a liability.

## 3. References

- Admin UI router: `src/admin/ui_router.py` (~1500 lines, 58 endpoints)
- Templates: `src/admin/templates/` (18 pages, 25 partials, 2 components)
- Existing HTTP tests: `tests/unit/test_admin_ui.py` (602 lines), `tests/unit/test_ui_router_epic10.py` (345 lines)
- Docker smoke tests: `tests/docker/test_api_smoke.py`
- Empty state component: `src/admin/templates/components/empty_state.html`
- Base template: `src/admin/templates/base.html`
- Epic 11 (Production Hardening): `docs/epics/epic-11-production-hardening-phase1.md`

## 4. Acceptance Criteria

**AC-1: Playwright is installed and configured.**
`pyproject.toml` includes `playwright` as a dev dependency. A `tests/playwright/conftest.py` provides fixtures for browser launch, page navigation, and authentication (dev-mode auto-auth). `pytest tests/playwright/` runs all browser tests. CI optionally runs Playwright tests (may be a separate job due to browser download).

**AC-2: Every Admin UI page has at least one Playwright test.**
All 17 pages have a test that navigates to the page, waits for content to load (including HTMX partials), and asserts key elements are visible. Pages: Dashboard, Repos, Repo Detail, Workflows, Workflow Detail, Audit, Metrics, Experts, Expert Detail, Tools, Models, Compliance, Quarantine, Dead Letters, Planes, Settings (with all 5 sub-tabs).

**AC-3: The `&#9744;` rendering bug is fixed.**
The empty state component renders a visible icon (emoji or SVG), not literal HTML entity text. A Playwright test for the empty Repos page asserts that no `&#` text appears in the visible page content.

**AC-4: All inline HTML in `ui_router.py` is escaped or moved to templates.**
No f-string in `ui_router.py` interpolates user-sourced data into `HTMLResponse` without escaping. Either: (a) move inline HTML to Jinja2 templates (preferred), or (b) use `markupsafe.escape()` on all interpolated values.

**AC-5: HTMX interactions are tested for critical flows.**
At minimum: (a) Register a repo and see it appear in the list, (b) Navigate between settings sub-tabs via HTMX, (c) Empty state → populated state transition after data creation.

**AC-6: No visible HTML entities, broken layouts, or JavaScript errors.**
A Playwright test visits every page and asserts: no `&#` literal text in visible content, no console errors, page title/heading matches expected text.

**Note:** Story 12.7 (CI Integration) is stretch/optional. The epic is complete when AC-1 through AC-6 pass locally. CI integration is a follow-up improvement, not a gate for epic closure.

**Target:** Sprint following current work. Estimated 3 days of effort.

## 4b. Top Risks

1. **Playwright + Docker Compose complexity.** Browser tests need a running stack. Options: (a) run against the prod stack on localhost, (b) run against a test stack started in conftest. The Docker smoke tests already solve this pattern — reuse their approach.

2. **Test flakiness.** Browser tests are inherently flakier than HTTP tests. Mitigation: use Playwright's built-in `expect` with auto-retry, avoid hard `sleep()` calls, use `page.wait_for_selector()` for HTMX content.

3. **CI browser installation.** Playwright requires browser binaries. Mitigation: use `playwright install chromium` in CI setup step. Mark Playwright tests with a pytest marker so they can be skipped in lightweight CI runs.

4. **Scope creep into visual regression testing.** This epic covers functional browser tests, not pixel-perfect screenshot comparison. Visual regression is a separate concern.

## 5. Constraints & Non-Goals

### Constraints
- Playwright tests run against the deployed Docker stack (same as `tests/docker/`).
- Tests must work with `THESTUDIO_LLM_PROVIDER=mock` (dev-mode auto-auth).
- No changes to the existing httpx-based test suite — Playwright supplements, not replaces.
- Browser: Chromium only (Playwright default). No cross-browser testing in Phase 1.

### Non-Goals
- **No visual regression / screenshot comparison.** Functional tests only.
- **No performance testing.** Page load benchmarks are out of scope.
- **No accessibility testing.** a11y audits (axe-core, Lighthouse) are future work.
- **No mobile/responsive testing.** Desktop viewport only.
- **No end-to-end pipeline tests through the UI.** The webhook/pipeline flow is tested via HTTP. Playwright tests cover the admin UI only.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Engineering Lead | Scope decisions, priority calls |
| Tech Lead | Backend Engineer | Playwright setup, test architecture |
| QA | Meridian (review) | Test coverage validation |
| Reviewer | Meridian | Epic and plan review before commit |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pages with Playwright coverage | 17/17 (100%) | `pytest tests/playwright/ --co -q` count |
| HTML entity rendering bugs | 0 visible in any page | Playwright scan for `&#` in `textContent` |
| XSS-vulnerable inline HTML | 0 unescaped interpolations | Playwright test injects `<script>` via test data + grep gate: `grep -Pn 'HTMLResponse\(f' ui_router.py` returns 0 f-string interpolations with DB/user data |
| Console errors across all pages | 0 | Playwright `page.on("console")` listener |
| Test suite runtime | Under 2 minutes | `pytest tests/playwright/ --durations=0` |

## 8. Context & Assumptions

### Assumptions
- The production Docker stack is running locally (Epic 11 delivered this).
- Dev-mode auto-auth is active (`LLM_PROVIDER=mock`), so no login flow is needed.
- The Admin UI uses HTMX for all interactivity — no custom JavaScript to test beyond HTMX behavior.
- Tailwind CSS is loaded from CDN — no build step for styles.
- Playwright's Python bindings (`playwright[pytest]`) are mature and well-documented.

### Dependencies
- **Epic 11 (Status: Complete).** Production stack is deployed and running.
- **Port access.** Tests need HTTP access to the app on port 8000 (or through Caddy on 443). The port-forward pattern established during Epic 11 deployment works.
- **Playwright browser binaries.** Must be installed (`playwright install chromium`). ~150 MB download.

### Systems Affected
- `pyproject.toml` — add Playwright dev dependency
- `tests/playwright/` — new directory, all Playwright test files
- `src/admin/templates/components/empty_state.html` — fix entity rendering
- `src/admin/ui_router.py` — fix XSS in inline HTML
- `.github/workflows/ci.yml` — optionally add Playwright CI job

---

## Story Map

### Story 12.1: Playwright Setup & First Smoke Test

**As a** developer,
**I want** Playwright configured with fixtures and a working smoke test,
**so that** subsequent stories can focus on page coverage without setup overhead.

**Details:**
- Add `playwright` to `pyproject.toml` `[project.optional-dependencies] dev`
- Create `tests/playwright/conftest.py` with:
  - `browser` fixture (session-scoped, launches Chromium)
  - `page` fixture (function-scoped, new page per test)
  - `base_url` fixture (configurable, defaults to `http://localhost:8000`)
  - `console_errors` fixture (captures JS console errors per page)
- Create `tests/playwright/test_smoke.py` with:
  - `test_healthz_returns_ok` — navigate to `/healthz`, assert "ok" in page
  - `test_admin_dashboard_loads` — navigate to `/admin/ui/dashboard`, assert page title
  - `test_no_console_errors_on_dashboard` — assert zero JS errors
- Add `playwright` pytest marker to `pyproject.toml` for selective runs

**Acceptance Criteria:**
- `pytest tests/playwright/test_smoke.py -v` passes
- `pytest -m playwright` runs only Playwright tests
- `pytest -m "not playwright"` skips them

**Files to create/modify:**
- `pyproject.toml` — add dependency + marker
- `tests/playwright/__init__.py` — new
- `tests/playwright/conftest.py` — new
- `tests/playwright/test_smoke.py` — new

---

### Story 12.2: Fix Empty State HTML Entity Rendering

**As an** operator viewing an empty Repos page,
**I want** to see an icon (not literal `&#9744;` text),
**so that** the UI looks professional and functional.

**Details:**
- Root cause: `empty_state.html` macro default `icon="&#9744;"` is a string that Jinja2 autoescapes to `&amp;#9744;`.
- Fix option A (preferred): Replace HTML entity with Unicode emoji (e.g., `icon="☐"` or `icon="📋"`) which doesn't need HTML decoding.
- Fix option B: Use `{{ icon | safe }}` in the template (but this bypasses escaping for all icon values — less safe).
- Fix option C: Use a named icon system with CSS/SVG instead of text entities.
- Audit all other `empty_state` usages across partials to ensure they all render correctly.

**Acceptance Criteria:**
- Navigate to `/admin/ui/repos` with no repos registered — icon displays as a visible symbol, not `&#9744;` text
- A Playwright test asserts `&#` does not appear in the visible text of the empty state
- No other pages show literal HTML entity text

**Files to modify:**
- `src/admin/templates/components/empty_state.html`
- Possibly other partials that call `empty_state()` with custom icons

---

### Story 12.3: Fix XSS in Inline HTML (ui_router.py)

**As a** security-conscious platform operator,
**I want** all user-sourced data properly escaped in HTML responses,
**so that** malicious input cannot execute scripts in the admin UI.

**Details:**
Audit and fix all `HTMLResponse(f'...')` patterns in `ui_router.py` where interpolated values come from database or user input:

1. **Merge mode control** (lines ~901-950): `repo_id` from URL path, `mode.value` from DB — low risk but should escape
2. **Promotion history** (lines ~1043-1066): `t["from_tier"]`, `t["to_tier"]`, `t["triggered_by"]`, `t["reason"]` from DB — **must escape**
3. **API key reveal** (line ~1162): `sv.value` from settings store — **must escape** (could contain `<script>`)
4. **Error messages** (lines ~318, 420, 645): Hard-coded strings — safe but inconsistent style

Fix approach:
- Import `markupsafe.escape` (already a dependency via Jinja2)
- Wrap all interpolated DB/user values with `escape()`
- Consider moving complex inline HTML (promotion history table, merge mode control) to Jinja2 templates for consistency

**Acceptance Criteria:**
- `grep -n 'HTMLResponse.*f["\x27]' src/admin/ui_router.py` shows no unescaped user data interpolation
- Existing unit tests still pass
- A Playwright test with a repo containing `<script>alert(1)</script>` in its name does not trigger an alert

**Files to modify:**
- `src/admin/ui_router.py`

---

### Story 12.4: Full Page Navigation Tests

**As a** developer,
**I want** a Playwright test that visits every Admin UI page and verifies it loads,
**so that** broken pages are caught before release.

**Details:**
Create `tests/playwright/test_all_pages.py` that:
- Navigates to each of the 17 main pages
- Waits for HTMX content to load (wait for `htmx:afterSwap` or a content selector)
- Asserts: page returns 200, heading text matches expected, no `&#` in visible text, no JS console errors
- Parameterize with `@pytest.mark.parametrize` for clean reporting

Pages to cover:
| Page | URL | Expected heading |
|------|-----|-----------------|
| Dashboard | `/admin/ui/dashboard` | "Dashboard" |
| Repos | `/admin/ui/repos` | "Repo Management" |
| Workflows | `/admin/ui/workflows` | "Workflows" |
| Audit | `/admin/ui/audit` | "Audit Log" |
| Metrics | `/admin/ui/metrics` | "Metrics" |
| Experts | `/admin/ui/experts` | "Expert" |
| Tools | `/admin/ui/tools` | "Tool" |
| Models | `/admin/ui/models` | "Model" |
| Compliance | `/admin/ui/compliance` | "Compliance" |
| Quarantine | `/admin/ui/quarantine` | "Quarantine" |
| Dead Letters | `/admin/ui/dead-letters` | "Dead Letter" |
| Planes | `/admin/ui/planes` | "Plane" |
| Settings | `/admin/ui/settings` | "Settings" |
| Repo Detail | `/admin/ui/repos/{repo_id}` | repo name (requires test data) |
| Workflow Detail | `/admin/ui/workflows/{workflow_id}` | workflow ID (requires test data) |
| Expert Detail | `/admin/ui/experts/{expert_id}` | expert name (requires test data) |
| Settings: API Keys | `/admin/ui/settings` → tab | "API Keys" |
| Settings: Infrastructure | `/admin/ui/settings` → tab | "Infrastructure" |

Detail pages and settings sub-tabs require test data fixtures (register a repo, create a workflow entry).

**Acceptance Criteria:**
- All 17 pages pass navigation + heading + no-entity + no-error checks
- Test report shows per-page pass/fail
- Runtime under 60 seconds for all page tests

**Files to create:**
- `tests/playwright/test_all_pages.py`

---

### Story 12.5: HTMX Interaction Tests

**As a** developer,
**I want** Playwright tests that verify HTMX-driven interactions work correctly,
**so that** dynamic UI behavior is tested with a real browser engine.

**Details:**
Test these critical HTMX flows:
1. **Register a repo** → navigate to Repos page → click "Register Repo" → fill form → submit → see repo in list
2. **Settings tab navigation** → navigate to Settings → click each sub-tab (API Keys, Infrastructure, Feature Flags, Agent Config, Secrets) → verify content swaps correctly
3. **Empty state → populated state** → start with empty repos → register one → empty state disappears, repo row appears
4. **Partial refresh** → dashboard loads, HTMX partials swap in content without full page reload

For each flow, assert:
- No full page reload (check `htmx:beforeRequest` event fires)
- Content updates in the expected target element
- No console errors during interaction

**Acceptance Criteria:**
- At least 3 HTMX interaction tests pass against the running stack
- Tests clean up after themselves (delete test repos)
- No flaky tests (use Playwright auto-retry, not sleep)

**Files to create:**
- `tests/playwright/test_htmx_interactions.py`

---

### Story 12.6: Console Error & Entity Scan Across All Pages

**As a** developer,
**I want** an automated scan that visits every page and reports console errors and broken HTML entities,
**so that** rendering issues don't ship undetected.

**Details:**
Create `tests/playwright/test_rendering_quality.py` that:
- Visits every page (reuse parameterized list from 12.4)
- Collects all `console.error` and `console.warn` messages
- Scans `page.text_content("body")` for literal `&#` patterns (entities that weren't decoded)
- Scans for common rendering issues: `undefined`, `null`, `NaN` in visible text
- Optionally: check that all nav links are valid (no 404s)

**Acceptance Criteria:**
- Zero `&#` patterns in visible text across all pages
- Zero `console.error` messages across all pages
- `console.warn` messages are logged but don't fail the test (informational)
- Test produces a clear report listing any issues found

**Files to create:**
- `tests/playwright/test_rendering_quality.py`

---

### Story 12.7: CI Integration (Optional / Stretch)

**As a** developer,
**I want** Playwright tests to run in CI,
**so that** UI regressions are caught before merge.

**Details:**
- Add a `playwright` job to `.github/workflows/ci.yml`
- Job: starts the Docker stack, installs Playwright browsers, runs `pytest tests/playwright/`
- Mark as `continue-on-error: true` initially (non-blocking) until tests are stable
- Use `playwright install --with-deps chromium` for CI environment

**Acceptance Criteria:**
- CI job runs Playwright tests on PR (non-blocking)
- Job completes in under 5 minutes
- Test results visible in PR checks

**Files to modify:**
- `.github/workflows/ci.yml`

---

## Story Dependency Map

```
12.1 (Setup) ──→ 12.4 (All Pages) ──→ 12.6 (Scan)
    │                                       │
    ├──→ 12.2 (Entity Fix) ────────────────┘
    │
    ├──→ 12.3 (XSS Fix) ──→ 12.5 (HTMX Tests)
    │
    └──→ 12.7 (CI, stretch)
```

- 12.1 must come first (framework setup)
- 12.2 and 12.3 are independent bug fixes that can run in parallel with 12.1
- 12.4 and 12.5 depend on 12.1 (need fixtures)
- 12.6 depends on 12.2 being fixed (otherwise the entity scan test would fail)
- 12.7 depends on all others being stable

---

## Meridian Review Status

### Round 1: Conditional Pass (2026-03-10)

**Verdict: Conditional Pass** — 2 gaps identified and fixed:

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Q4: No target date, Story 12.7 scope ambiguous | Fixed: Added target timeline, explicitly marked 12.7 as stretch/optional in AC section |
| 2 | Q5: XSS metric uses "code review" (not automated) | Fixed: Replaced with Playwright injection test + grep gate |
| 3 | Recommended: Story 12.4 page table incomplete (13/17 URLs) | Fixed: Added detail pages + settings sub-tabs to table |

### Round 2: Pending
