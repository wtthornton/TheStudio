# Fix Plan — TheStudio

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
- [ ] 45.3: Mount HelpMenu in HeaderBar, wire HelpPanel toggle. **Files:** modify HeaderBar.tsx, App.tsx.
- [ ] 45.4: Route-aware content loading — create `frontend/src/help/` with 11 `.md` files. HelpPanel renders matching content via `react-markdown` + Vite `?raw` import. **Files:** create 11 .md files; modify HelpPanel.tsx.
- [ ] 45.5: Fuse.js search — index all articles, search bar in panel, click result switches tab. **Files:** modify HelpPanel.tsx.
- [ ] 45.6: Author 11 tab help articles (200-400 words each). **Files:** write 11 .md files in frontend/src/help/.
- [ ] 45.7: Author 4 cross-cutting concept articles (Trust Tiers, Webhooks, Evidence Bundles, Pipeline Stages). **Files:** write 4 .md files.
- [ ] 45.8: Add react-tooltip to React SPA — 30+ tooltips across HeaderBar, PipelineStatus, TrustConfiguration, BudgetDashboard. **Files:** modify ~6 component files.
- [ ] 45.9: Add CSS tooltips to Admin UI — 15+ `data-tooltip` attrs on dashboard, repos, workflow templates. **Files:** modify ~5 template files + add tooltip CSS to base.html.
- [ ] 45.10: Vitest for HelpPanel, HelpMenu, search, route-awareness, tooltip render. **Files:** create __tests__/HelpPanel.test.tsx, __tests__/HelpMenu.test.tsx. **RUN TESTS.**

---

## Sprint 9 — Epic 47: Product Tours (week of 2026-04-21)

> Order: 47.1 → 47.2 → 47.3 → 47.4 → 47.5 → 47.6 → 47.7 → 47.8
> Gate: `cd frontend && npx vitest run` green + 4 tours defined
> TESTS_STATUS: DEFERRED until 47.8

- [ ] 47.1: `npm install react-joyride`. Create `TourProvider.tsx` wrapping App with Joyride context. Dark tooltip styles. **Files:** modify package.json; create frontend/src/components/tours/TourProvider.tsx.
- [ ] 47.2: Create tour registry + `useTourState` hook — localStorage flags, start/complete lifecycle. **Files:** create registry.ts, useTourState.ts.
- [ ] 47.3: Pipeline tour (6 steps) — pipeline rail, stage node, active pulse, gate inspector, activity stream, minimap. Add `data-tour` attrs. **Files:** modify PipelineStatus.tsx, GateInspector.tsx, ActivityStream.tsx, Minimap.tsx; update registry.ts.
- [ ] 47.4: Tour beacon component — pulses on first visit, click starts tour, hidden after completion. **Files:** create TourBeacon.tsx; modify App.tsx to place beacons per-tab.
- [ ] 47.5: Triage tour (5 steps) — queue, card, accept/reject, intent editor, routing preview. **Files:** modify TriageQueue.tsx, IntentEditor.tsx, RoutingPreview.tsx; update registry.ts.
- [ ] 47.6: Analytics tour (5 steps) — period selector, KPIs, throughput, bottleneck, expert table. **Files:** modify Analytics.tsx sub-components; update registry.ts.
- [ ] 47.7: Repo & Trust tour (5 steps) — repo selector, settings, trust tier, tier descriptions, budget. **Files:** modify RepoSettings.tsx, TrustConfiguration.tsx, BudgetDashboard.tsx; update registry.ts.
- [ ] 47.8: Add "Guided Tours" section to HelpMenu (4 replay links) + Vitest. **Files:** modify HelpMenu.tsx; create __tests__/tours.test.tsx. **RUN TESTS.**

---

## Sprint 10 — Epic 50: Feature Spotlights (DEFERRED — after Epics 44+45+48 complete)

> Order: 50.1 → 50.2 → 50.3 → 50.4 → 50.5
> Gate: `cd frontend && npx vitest run` green
> TESTS_STATUS: DEFERRED until 50.5
> BLOCKED BY: Epics 44, 45, 48 must be COMPLETE (they create the UI elements to spotlight)

- [ ] 50.1: `npm install driver.js`. Create `SpotlightProvider.tsx` + `registry.ts`. Version comparison logic. **Files:** modify package.json; create 2 files.
- [ ] 50.2: Inject app version in `vite.config.ts` from pyproject.toml as `VITE_APP_VERSION`. **Files:** modify vite.config.ts.
- [ ] 50.3: Define 2-3 initial spotlight entries targeting help panel, wizard, API tab. **Files:** modify registry.ts; add `data-spotlight` attrs to target components.
- [ ] 50.4: Dark theme CSS for Driver.js popovers. **Files:** modify frontend/src/index.css.
- [ ] 50.5: Vitest: version mismatch fires, same version skips, registry schema validation. **Files:** create __tests__/spotlights.test.tsx. **RUN TESTS.**

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

Epics 0-43 (280+ stories). Epic 27 deferred by design.
Deployment hardening: multi-stage Dockerfile, .dockerignore, vendor/ralph-sdk, migration 049, NATS healthcheck, pg-proxy localhost binding, /health/ralph test coverage.
