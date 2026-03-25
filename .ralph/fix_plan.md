# Fix Plan — TheStudio

## Open epics — active backlog

> **Rollup:** `docs/epics/EPIC-STATUS-TRACKER.md` (2026-03-25). All non-complete epics from that tracker are listed here so Ralph and humans share one queue.

| Epic | Status | Canonical doc |
|------|--------|---------------|
| **59–74** | Proposed — Per-page Playwright full-stack test suites (16 epics × 6 stories = 96 stories, 304 pts) | `docs/epics/epic-59-dashboard-playwright-suite.md` … `epic-74-*` |
| **27** | Deferred on demand | `docs/epics/` (multi-source webhooks) |

---

## Epics 58–74 — Playwright Full-Stack Test Suites (proposed)

> **Dependency chain:** Epic 58 (infra, COMPLETE) → Epics 59–74 (per-page suites)
> **Total:** 16 remaining epics, 96 stories, 304 points
> **Page inventory:** `docs/PAGES.md`
> **Style guide source of truth:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`

Each page epic has: `.1` Intent, `.2` API verification, `.3` Style guide compliance, `.4` Interactive elements, `.5` Accessibility, `.6` Visual snapshot baseline.

| Epic | Page | Path |
|------|------|------|
| 59 | Fleet Dashboard | `/admin/ui/dashboard` |
| 60 | Repo Management | `/admin/ui/repos` |
| 61 | Workflow Console | `/admin/ui/workflows` |
| 62 | Audit Log | `/admin/ui/audit` |
| 63 | Metrics | `/admin/ui/metrics` |
| 64 | Expert Performance | `/admin/ui/experts` |
| 65 | Tool Hub | `/admin/ui/tools` |
| 66 | Model Gateway | `/admin/ui/models` |
| 67 | Compliance Scorecard | `/admin/ui/compliance` |
| 68 | Quarantine | `/admin/ui/quarantine` |
| 69 | Dead-Letter Inspector | `/admin/ui/dead-letters` |
| 70 | Execution Planes | `/admin/ui/planes` |
| 71 | Settings | `/admin/ui/settings` |
| 72 | Cost Dashboard | `/admin/ui/cost-dashboard` |
| 73 | Portfolio Health | `/admin/ui/portfolio-health` |
| 74 | Detail Pages (Repo/Workflow/Expert) | `/{entity}/{id}` |

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
