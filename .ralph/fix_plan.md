# Fix Plan — TheStudio

## Open epics — active backlog

> **Rollup:** `docs/epics/EPIC-STATUS-TRACKER.md` (2026-03-24). All non-complete epics from that tracker are listed here so Ralph and humans share one queue.

| Epic | Status | Canonical doc |
|------|--------|---------------|
| **51** | In progress — vendor parity + evaluation backlog | `docs/epics/epic-51-ralph-vendored-sdk-parity.md`, `docs/handoffs/ralph-epic-51-next-agent-prompt.md`, `docs/ralph-sdk-upgrade-evaluation.md` |
| **38** | MVP done (38.1–38.12); **Slices 3–4 open** | `docs/epics/epic-38-phase4-github-integration.md` |
| **39** | Approved — not started | `docs/epics/epic-39-phase5-analytics-learning.md` |
| **43** | **Integration delivered** in tree (43.1–43.15); **default `THESTUDIO_AGENT_MODE=ralph`** and primary-agent *rollout* still **gated on Epic 51** + ops | `docs/epics/epic-43-ralph-sdk-integration.md` |
| **52–57** | Canonical UI modernization (52 master; 53–57 child tracks) | `docs/epics/epic-52-frontend-ui-modernization-master-plan.md`, `epic-53-admin-ui-canonical-compliance.md`, `epic-54-dashboard-ui-canonical-compliance.md`, `epic-55-cross-surface-ai-prompt-first-and-trust-layer.md`, `epic-56-cross-surface-2026-capability-modules.md`, `epic-57-rollout-governance-and-regression-safety.md` |
| **27** | Deferred on demand | `docs/epics/` (multi-source webhooks — see tracker) |

### Epic 51 — Ralph vendored SDK parity (remaining)

> P0/P1 stories **51.1–51.6** shipped per `docs/handoffs/ralph-epic-51-next-agent-prompt.md`. **Parsing tests** for `TESTS_STATUS: DEFERRED` live in `tests/unit/test_ralph_parsing_tests_status.py` (**done**). **Still open:** evaluation doc gaps + cancel/git hardening below. **Gate:** `docs/ralph-sdk-upgrade-evaluation.md`. **Verify:** handoff “Verification (local)” block.

- [x] **51-eval:** Close open gaps in `docs/ralph-sdk-upgrade-evaluation.md` — prioritize §1.5 dynamic model routing, §1.8 prompt cache split, §1.9 metrics JSONL, §1.10 session lifecycle / Continue-As-New, §1.7 error categorization (P2), §2.3 ProgressSnapshot / heartbeat (P2).
- [x] **51-cancel:** Cancel hardening — `CancelResult.partial_output` (stream/buffer), optional grace wait inside SDK (`docs/ralph-sdk-upgrade-evaluation.md` §2.2).
- [x] **51-git:** Harden `files_changed` / stall when `git` missing or repo dirty; add/adjust unit tests.
- [x] **51-tests:** `tests/unit/test_ralph_parsing_tests_status.py` — DEFERRED / case-insensitive / JSON / JSONL coverage for `tests_status` parsing.

### Epic 38 — Phase 4 GitHub integration (Slice 3: Projects sync)

> **Done in tree:** 38.1–38.12. Order below follows epic story map.

- [x] **38.13:** Enable `ProjectsV2Client` — remove feature-flag guard when `projects_v2_enabled=True`; validate token scopes.
- [x] **38.14:** Extend field mapping — Cost + Complexity fields; `create_custom_field()` GraphQL; auto-create on first sync.
- [x] **38.15:** GitHub→TheStudio sync — `projects_v2_item` webhooks; update TaskPacket; skip self-triggered events.
- [x] **38.16:** `GET`/`PUT` `/api/v1/dashboard/github/projects/config` — project selection, field mapping, behaviors.
- [x] **38.17:** `POST .../projects/sync` — force full sync of active TaskPackets.
- [x] **38.18:** Projects sync configuration UI — `ProjectsSyncConfig.tsx`.
- [x] **38.19:** Feedback loop guard — `thestudio-sync` mutation id; skip own webhooks.
- [x] **38.20:** Integration test — stage push, manual GitHub status update, self-trigger skip.

### Epic 38 — Phase 4 (Slice 4: Pipeline comments + webhook bridge)

- [x] **38.21:** Pipeline comment template + idempotent marker (`pipeline_comment.py`).
- [x] **38.22:** Pipeline comment Temporal activity — create/edit comment; final update with PR link.
- [x] **38.23:** `pipeline_comments_enabled` flag + per-repo config.
- [x] **38.24:** Webhook bridge — PR/issue events → NATS `github.event.*`.
- [x] **38.25:** SSE — extend `src/dashboard/events.py` for `github.event.*` / stream subjects.
- [x] **38.26:** Dashboard consumers — PR Evidence + triage real-time updates (`useGitHubEvents.ts`).
- [x] **38.27:** Integration test — comments + NATS publish.

### Epic 39 — Phase 5 analytics & learning

> **Slice 0** before Slices 1–2 per epic. **Depends:** Phase 1 timing/gate data; Phase 4 helps `pr_merge_status` (39.0b).

- [x] **39.0a:** `completed_at` on `TaskPacketRow` + migration + backfill.
- [x] **39.0b:** `pr_merge_status` field + migration; wire to Epic 38 webhook or polling fallback.
- [x] **39.0c:** Persist outcome signals to PostgreSQL (`OutcomeSignalRow`, migrate ingestor).
- [ ] **39.1–39.5:** Operational analytics APIs — throughput, bottlenecks, categories, failures, summary cards (`analytics_router` / `analytics_queries`).
- [ ] **39.6–39.11:** Operational analytics UI — charts, tables, period selector, summary row.
- [ ] **39.12–39.16:** Reputation & drift APIs — experts, outcomes, drift, composite drift score, summary cards.
- [ ] **39.17–39.21:** Reputation UI — expert table/detail, outcome feed, drift alerts, reuse summary cards.

### Epic 43 — Ralph SDK as primary agent

> **Implementation status (2026-03-24):** Stories **43.1–43.15** are **implemented in tree** (vendor `ralph-sdk`, `ralph_bridge.py`, `agent_mode`, `PostgresStateBackend`, activity heartbeat, cost audit, `/health/ralph`, OTel attrs, `test_ralph_*` / `test_ralph_e2e`). **Operational:** keep **`THESTUDIO_AGENT_MODE=legacy`** for production until **Epic 51** exit criteria + ops sign-off; use `ralph` in dev/staging to validate. Canonical spec: `docs/epics/epic-43-ralph-sdk-integration.md`.

#### Slice 1 — Ralph replaces PrimaryAgentRunner (flag-gated)

- [x] **43.1:** `ralph-sdk @ file:./vendor/ralph-sdk` in `pyproject.toml` + vendor layout.
- [x] **43.2:** `src/agent/ralph_bridge.py` — CLI probe, `taskpacket_to_ralph_input`, `ralph_result_to_evidence`, `build_ralph_config`, loopback context.
- [x] **43.3:** `THESTUDIO_AGENT_MODE` (`legacy` / `ralph` / `container`) + precedence vs `THESTUDIO_AGENT_ISOLATION` in `src/settings.py`.
- [x] **43.4:** `implement()` / `handle_loopback()` Ralph dispatch in `src/agent/primary_agent.py`.
- [x] **43.5:** Unit tests — `tests/unit/test_ralph_bridge.py`, `tests/unit/test_primary_agent_ralph.py`.

#### Slice 2 — PostgresStateBackend

- [x] **43.6:** Migration `048_ralph_agent_state.py` — `ralph_agent_state` table.
- [x] **43.7:** `src/agent/ralph_state.py` — `PostgresStateBackend` (12 protocol methods).
- [x] **43.8:** Wire postgres vs `NullStateBackend` via `ralph_state_backend` + session TTL in primary agent.
- [x] **43.9:** `tests/integration/test_ralph_state.py`.

#### Slice 3 — Cost + Temporal activity

- [x] **43.10:** Cost / audit / budget hooks after Ralph in `primary_agent` (see Story 43.10 comments).
- [x] **43.11:** `_implement_ralph_with_heartbeat` in `src/workflow/activities.py` (30 s heartbeat, timeout, cancel).
- [x] **43.12:** `tests/unit/test_ralph_cost_and_heartbeat.py` (cost recording + heartbeat + timeout/cancel).

#### Slice 4 — Validation + observability

- [x] **43.13:** `GET /health/ralph` on main app + startup warning when `agent_mode=ralph` but CLI missing (`src/app.py`).
- [x] **43.14:** OTel — `SPAN_RALPH_RUN` / `SPAN_RALPH_ITERATION` + `ATTR_RALPH_*` in `src/observability/conventions.py`; `primary_agent` wraps Ralph `run()` with **`SPAN_RALPH_RUN`** and sets cost/token/backend attrs. *(Separate per-iteration / circuit-breaker spans from the epic text are not duplicated in TheStudio — SDK subprocess may own fine-grained spans.)*
- [x] **43.15:** `tests/integration/test_ralph_e2e.py` — implement + loopback path with mocked `RalphAgent.run`.

### Epics 52–57 — Canonical UI / style guide

> Execution log: `docs/epics/epic-52-frontend-ui-modernization-master-plan.md` (last updated 2026-03-24).

- [ ] **53.1:** Admin shell/nav conformance — **not started** (epic 52 log).
- [x] **53.2:** Status / role badges, `base.html` nav — **complete** (epic 52 log).
- [ ] **53.3:** Admin HTMX — **partial** — remaining partials, `empty_state` sweep, formal keyboard/SR AC (`epic-53-admin-ui-canonical-compliance.md`).
- [x] **54.1:** Dashboard `STATUS_COLORS`, trust-tier UI, `StageNode` `aria-label` — **complete** (epic 52 log).
- [ ] **54.2:** Pipeline app — **partial** — remaining modals/panels, SG §11 sign-off, optional focus traps (`epic-54-dashboard-ui-canonical-compliance.md`).
- [ ] **55:** Cross-surface AI prompt-first + trust — **not started** — `epic-55-cross-surface-ai-prompt-first-and-trust-layer.md`.
- [ ] **56:** 2026 capability modules — **not started** — `epic-56-cross-surface-2026-capability-modules.md`.
- [ ] **57.1:** Rollout governance matrix — **in progress** (`epic-57-rollout-governance-and-regression-safety.md`).
- [ ] **57.2:** Full regression / AC closure — **pending** 53.3 + 54.2 sweeps per epic 52 log.

### Deferred (no sprint checkbox — pull when demand exists)

- **Epic 27:** Multi-source webhooks — see `docs/epics/EPIC-STATUS-TRACKER.md` and epic files under `docs/epics/`.

---

## Sprint 4 — Epic 46: Actionable Empty States (week of 2026-03-24)

> Order: 46.1 → 46.2 → 46.3 → 46.4 → 46.5 → 46.6 → 46.7
> Gate: `cd frontend && npx vitest run` green + manual visual audit
> TESTS_STATUS: Ran `pytest tests/unit/test_admin_ui.py`; `cd frontend && npx vitest run` green after 46.7 + 48.5

- [x] 46.1: Create `frontend/src/components/EmptyState.tsx` — reusable base component with icon/illustration slot, heading, description, primary CTA button (onClick or href), optional secondary link. Dark theme styling. **Files:** create EmptyState.tsx.
- [x] 46.2: Pipeline + Triage empty states — replace `EmptyPipelineRail` in `ErrorStates.tsx` with EmptyState showing pipeline wireframe SVG + "Import an Issue" CTA opening ImportModal. Replace Triage placeholder with "Configure webhook" CTA. **Files:** modify ErrorStates.tsx, TriageQueue.tsx.
- [x] 46.3: Planning tab empty states — Intent Review, Routing Review, Backlog empty states with explanations and CTAs linking to Pipeline tab. **Files:** modify IntentEditor.tsx, RoutingPreview.tsx, BacklogBoard.tsx.
- [x] 46.4: Configuration tab empty states — Trust Tiers, Budget, Repos with CTAs to registration/settings. **Files:** modify TrustConfiguration.tsx, BudgetDashboard.tsx, RepoSettings.tsx.
- [x] 46.5: Analytics + monitoring empty states + header hint — Analytics, Activity Log, Reputation. Header KPI onboarding hint when all zero. Vitest for all empty states. **Files:** modify Analytics.tsx, SteeringActivityLog.tsx, HeaderBar.tsx; create __tests__/EmptyState.test.tsx. **RUN TESTS.**
- [x] 46.6: Extend `empty_state.html` Jinja2 partial — add `cta_text`, `cta_url`, `cta_icon` parameters. **Files:** modify src/admin/templates/components/empty_state.html.
- [x] 46.7: Update Admin UI pages — repos, workflows, quarantine, dead-letters with specific CTAs. **Files:** modify repos.html, workflows.html, quarantine.html, dead-letters.html. **RUN TESTS.**

---

## Sprint 5 — Epic 48: Scalar API Docs (week of 2026-03-24, parallel with 46)

> Order: 48.1 → 48.2a → 48.2b → 48.3 → 48.4 → 48.5
> Gate: `/docs` renders Scalar, `cd frontend && npx vitest run` green
> TESTS_STATUS: `cd frontend && npx vitest run` green (48.5)

- [x] 48.1: Install `scalar-fastapi`, replace Swagger UI mount in `src/app.py`. Verify `/docs` renders Scalar. **Files:** modify pyproject.toml, src/app.py.
- [x] 48.2a: Add tags/descriptions to core routes — `src/app.py` (health), `src/ingress/webhook_handler.py` (webhooks), `src/admin/router.py` (admin top-level). ~15 routes. **Files:** modify app.py, webhook_handler.py, router.py.
- [x] 48.2b: Add tags/descriptions to admin sub-routers — `src/admin/repos_router.py`, `src/admin/workflow_router.py`, `src/admin/settings_router.py`. ~20 routes. **Files:** modify 3 router files.
  - *Implemented in `src/admin/router.py` only (no separate repos/workflow/settings router modules in this repo).*
- [x] 48.3: Install `@scalar/api-reference`. Create `frontend/src/components/ApiReference.tsx` with dark theme. **Files:** modify frontend/package.json; create ApiReference.tsx.
  - *React: `@scalar/api-reference-react` (official React wrapper for Scalar reference).*
- [x] 48.4: Add "API" tab to `frontend/src/App.tsx`. Render ApiReference pointing at `/openapi.json`. **Files:** modify App.tsx.
- [x] 48.5: Verify "Try It" against live endpoints. Vitest for ApiReference mount. **Files:** create __tests__/ApiReference.test.tsx. **RUN TESTS.**

---

## Sprint 6 — Epic 44: Setup Wizard (week of 2026-03-31)

> Order: 44.1 → 44.2 → 44.3 → 44.4 → 44.5 → 44.6 → 44.7 → 44.8 → 44.9 → 44.10
> Gate: `cd frontend && npx vitest run` green + manual walkthrough on clean localStorage
> TESTS_STATUS: DEFERRED until 44.10

- [x] 44.1: `npm install react-use-wizard`. Create `frontend/src/components/wizard/WizardShell.tsx` — step navigation, progress bar, skip button. **Files:** modify package.json; create WizardShell.tsx.
- [x] 44.2: Wizard gate in `App.tsx` — check localStorage flag, render WizardShell overlay when falsy, completion callback. **Files:** modify App.tsx.
- [x] 44.3: `HealthCheckStep.tsx` — calls `/healthz` + `/readyz`, green/red status, enables Next on both green. **Files:** create HealthCheckStep.tsx.
- [x] 44.4: `RepoRegistrationStep.tsx` — form (owner/repo/installation_id), POST `/admin/repos`, handles 201/409. **Files:** create RepoRegistrationStep.tsx.
- [x] 44.5: `WebhookConfigStep.tsx` — displays webhook URL, copy button, manual checkbox. **Files:** create WebhookConfigStep.tsx.
- [x] 44.6: `TrustTierStep.tsx` — Observe/Suggest/Execute dropdown, PATCH profile. **Files:** create TrustTierStep.tsx.
- [x] 44.7: `LLMProviderStep.tsx` — GET `/admin/health`, shows Anthropic key status. **Files:** create LLMProviderStep.tsx.
- [x] 44.8: `TestIssueStep.tsx` — trigger test issue, poll for TaskPacket, success animation. **Files:** create TestIssueStep.tsx.
- [x] 44.9: Skip flow + incomplete banner — skip link sets flag, banner in HeaderBar with resume link. **Files:** modify HeaderBar.tsx; create IncompleteBanner.tsx.
- [x] 44.10: Re-launch menu item + Vitest tests for all wizard components and gate logic. **Files:** create __tests__/WizardShell.test.tsx; modify HelpMenu (if Epic 45 done) or App.tsx. **RUN TESTS.**

---

## Sprint 7 — Epic 49: Unified Navigation (week of 2026-04-07)

> Order: 49.1 → 49.2 → 49.3 → 49.4 → 49.5 → 49.6
> Gate: `cd frontend && npx vitest run` green + manual cross-navigation test
> TESTS_STATUS: DEFERRED until 49.6

- [x] 49.1: Create `AppSwitcher.tsx` dropdown in HeaderBar — "Pipeline Dashboard" (current) + "Admin Console" link to `/admin/ui/`. **Files:** create AppSwitcher.tsx; modify HeaderBar.tsx.
- [x] 49.2: Add "Pipeline Dashboard" link to `base.html` sidebar. **Files:** modify src/admin/templates/base.html.
- [x] 49.3: URL query parameter handling in App.tsx — parse `?tab=` and `?repo=` on mount, `replaceState` on tab change. **Files:** modify App.tsx.
- [x] 49.4: Deep links from SPA to Admin — repo names link to `/admin/ui/repos/{id}`, Settings link to `/admin/ui/settings`. **Files:** modify RepoSettings.tsx, HeaderBar.tsx (or HelpMenu).
- [x] 49.5: Deep links from Admin to SPA — "View Pipeline" on workflow rows links to `/dashboard/?tab=pipeline&repo={repo}`. **Files:** modify src/admin/templates/workflows.html, repos.html.
- [x] 49.6: Vitest for URL param parsing, AppSwitcher render, link hrefs. **Files:** create __tests__/AppSwitcher.test.tsx, __tests__/url-params.test.ts. **RUN TESTS.**

---

## Sprint 8 — Epic 45: Contextual Help (week of 2026-04-14)

> Order: 45.1 → 45.2 → 45.3 → 45.4 → 45.5 → 45.6 → 45.7 → 45.8 → 45.9 → 45.10
> Gate: `cd frontend && npx vitest run` green + 11 help files exist + 30+ tooltips
> TESTS_STATUS: DEFERRED until 45.10

- [x] 45.1: `npm install react-tooltip react-markdown fuse.js`. Create `HelpPanel.tsx` — slide-in/out, close button, Escape handler. **Files:** modify package.json; create frontend/src/components/help/HelpPanel.tsx.
- [x] 45.2: Create `HelpMenu.tsx` — dropdown with items: Help Panel, Setup Wizard, Guided Tours, API Docs. **Owns the shared help menu for Epics 44, 47, 50.** **Files:** create frontend/src/components/help/HelpMenu.tsx.
- [x] 45.3: Mount HelpMenu in HeaderBar, wire HelpPanel toggle. **Files:** modify HeaderBar.tsx, App.tsx.
- [x] 45.4: Route-aware content loading — create `frontend/src/help/` with 11 `.md` files. HelpPanel renders matching content via `react-markdown` + Vite `?raw` import. **Files:** create 11 .md files; modify HelpPanel.tsx.
- [x] 45.5: Fuse.js search — index all articles, search bar in panel, click result switches tab. **Files:** modify HelpPanel.tsx.
- [x] 45.6: Author 11 tab help articles (200-400 words each). **Files:** write 11 .md files in frontend/src/help/.
- [x] 45.7: Author 4 cross-cutting concept articles (Trust Tiers, Webhooks, Evidence Bundles, Pipeline Stages). **Files:** write 4 .md files.
- [x] 45.8: Add react-tooltip to React SPA — 30+ tooltips across HeaderBar, PipelineStatus, TrustConfiguration, BudgetDashboard. **Files:** modify ~6 component files.
- [x] 45.9: Add CSS tooltips to Admin UI — 15+ `data-tooltip` attrs on dashboard, repos, workflow templates. **Files:** modify ~5 template files + add tooltip CSS to base.html.
- [x] 45.10: Vitest for HelpPanel, HelpMenu, search, route-awareness, tooltip render. **Files:** create __tests__/HelpPanel.test.tsx, __tests__/HelpMenu.test.tsx. **RUN TESTS.**

---

## Sprint 9 — Epic 47: Product Tours (week of 2026-04-21)

> Order: 47.1 → 47.2 → 47.3 → 47.4 → 47.5 → 47.6 → 47.7 → 47.8
> Gate: `cd frontend && npx vitest run` green + 4 tours defined
> TESTS_STATUS: DEFERRED until 47.8

- [x] 47.1: `npm install react-joyride`. Create `TourProvider.tsx` wrapping App with Joyride context. Dark tooltip styles. **Files:** modify package.json; create frontend/src/components/tours/TourProvider.tsx.
- [x] 47.2: Create tour registry + `useTourState` hook — localStorage flags, start/complete lifecycle. **Files:** create registry.ts, useTourState.ts.
- [x] 47.3: Pipeline tour (6 steps) — pipeline rail, stage node, active pulse, gate inspector, activity stream, minimap. Add `data-tour` attrs. **Files:** modify PipelineStatus.tsx, GateInspector.tsx, ActivityStream.tsx, Minimap.tsx; update registry.ts.
- [x] 47.4: Tour beacon component — pulses on first visit, click starts tour, hidden after completion. **Files:** create TourBeacon.tsx; modify App.tsx to place beacons per-tab.
- [x] 47.5: Triage tour (5 steps) — queue, card, accept/reject, intent editor, routing preview. **Files:** modify TriageQueue.tsx, IntentEditor.tsx, RoutingPreview.tsx; update registry.ts.
- [x] 47.6: Analytics tour (5 steps) — period selector, KPIs, throughput, bottleneck, expert table. **Files:** modify Analytics.tsx sub-components; update registry.ts.
- [x] 47.7: Repo & Trust tour (5 steps) — repo selector, settings, trust tier, tier descriptions, budget. **Files:** modify RepoSettings.tsx, TrustConfiguration.tsx, BudgetDashboard.tsx; update registry.ts.
- [x] 47.8: Add "Guided Tours" section to HelpMenu (4 replay links) + Vitest. **Files:** modify HelpMenu.tsx; create __tests__/tours.test.tsx. **RUN TESTS.**

---

## Sprint 10 — Epic 50: Feature Spotlights *(complete — was deferred until Epics 44+45+48)*

> Order: 50.1 → 50.2 → 50.3 → 50.4 → 50.5
> Gate: `cd frontend && npx vitest run` green
> TESTS_STATUS: Ran with 50.5
> Originally BLOCKED BY: Epics 44, 45, 48 (now complete)

- [x] 50.1: `npm install driver.js`. Create `SpotlightProvider.tsx` + `registry.ts`. Version comparison logic. **Files:** modify package.json; create 2 files.
- [x] 50.2: Inject app version in `vite.config.ts` from pyproject.toml as `VITE_APP_VERSION`. **Files:** modify vite.config.ts.
- [x] 50.3: Define 2-3 initial spotlight entries targeting help panel, wizard, API tab. **Files:** modify registry.ts; add `data-spotlight` attrs to target components.
- [x] 50.4: Dark theme CSS for Driver.js popovers. **Files:** modify frontend/src/index.css.
- [x] 50.5: Vitest: version mismatch fires, same version skips, registry schema validation. **Files:** create __tests__/spotlights.test.tsx. **RUN TESTS.**

---

## Backlog — Needs Epic (Saga → Meridian → Helm)

**P2: Production Monitoring** — alerts for pipeline failures, cost anomalies, API rate limits, health dashboard
**P3: Intake Haiku Fix** — diagnose parsing failures, tune prompt or route to Sonnet
**P3: Agent Intelligence** — LLM issue scoring (E16), adversarial classification (E20), agentic non-Primary agents (E23)
**P3: Approval/Workflow** — GitHub `/approve` command parsing (E21), fleet-wide auto-merge policies (E22)
**P3: Security** — full SAST/DAST pipeline (E19), automated secret rotation (E11)
**P3: Testing** — a11y audits (E12), Playwright detail page tests (E12)

## Deferred — On Demand

**Epic 27: Multi-Source Webhooks** — 7 stories ready, trigger: non-GitHub source demand

## Completed

**Sprints in this file (below):** Epics **44, 45, 46, 47, 48, 49, 50** — all checklist items marked `[x]`.

**Other closed work (not duplicated as tasks here):** Epics **0–37**, **28–29**, **30–33**, **34–37** (pipeline UI phases 0–3), per `docs/epics/EPIC-STATUS-TRACKER.md`.

**Still open:** See **Open epics** at top — **38** (slices 3–4), **39**, **51** (vendor parity + eval backlog), **52–57** (53.1 / 53.3 / 54.2 / 55–57 partial or not started). **Epic 43** stories **43.1–43.15** are **done in code**; **Ralph as default in prod** remains **gated on Epic 51** + ops. **Epic 27** is **deferred** (not scheduled).

Deployment hardening (reference): multi-stage Dockerfile, `.dockerignore`, `vendor/ralph-sdk`, migrations **048** (`ralph_agent_state`) + **049**, NATS healthcheck, pg-proxy localhost binding, `/health/ralph` coverage.

---

## Documentation sync (2026-03-24)

Rolled up canonical UI standard (`docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`), MCP frontend experts brief, Cursor `frontend-style-source-of-truth` rule, `EPIC-STATUS-TRACKER.md`, `TAPPS_HANDOFF.md`, `TAPPS_RUNLOG.md`, Story **53.3** header, and README / AGENTS / Copilot pointers. Local `.tapps-brain/` excluded via `.gitignore`.
