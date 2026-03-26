# Fix Plan — TheStudio

## Open epics — active backlog

> **Rollup:** `docs/epics/EPIC-STATUS-TRACKER.md` (2026-03-26). All epics complete except Epic 27 (deferred).

| Epic | Status | Canonical doc |
|------|--------|---------------|
| **27** | Deferred on demand | `docs/epics/` (multi-source webhooks) |

**No open tasks.** All 75 epics (0–75) are complete. Epic 27 is deferred until demand.

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

**Epics 59–74 (Playwright Full-Stack Test Suites):** All 16 epics, 96 stories, 304 pts **complete** (2026-03-26). Per-page test suites for all Admin UI pages: intent, API verification, style guide compliance (§9.13-9.15), interactive elements, WCAG 2.2 AA accessibility, visual snapshot baselines. Delivered by Ralph in 95 commits.

**Epic 75 (Plane-Parity Admin UI):** All 8 stories (75.1–75.8) **complete** (2026-03-25). SVG icon system, sliding detail panel, repo/workflow detail panels, kanban board, command palette (Ctrl+K), dark mode, WCAG 2.2 AA audit. 31 pts. Commits `6822cb1`–`0fe3de1`.

**Epic 58 (Playwright Test Infrastructure):** All 7 stories (58.1–58.7). Shared assertion libs for style guide colors, typography, component recipes, API helpers, interactive elements, WCAG 2.2 AA, visual snapshots.

**Epics 52–57 (Canonical UI):** All stories complete (2026-03-25). 53.1–53.4, 54.1–54.4, 55.1–55.4, 56.1–56.4, 57.1–57.3. 74+ tests.

**Epics 43, 51:** Epic 43 (Ralph SDK, 15 stories, **ops sign-off granted 2026-03-25**), Epic 51 (SDK parity, all hardening tasks).

**Epics 38–39:** Epic 38 (GitHub Phase 4, 27 stories), Epic 39 (Analytics & Learning, 24 stories).

**Sprints 4–10:** Epics 44–50 (Setup Wizard, Contextual Help, Empty States, Product Tours, Scalar API Docs, Unified Navigation, Feature Spotlights).

**Prior phases:** Epics 0–37 (Phases 0–8, Pipeline UI Phases 0–3), per `docs/epics/EPIC-STATUS-TRACKER.md`.

---

## Documentation sync (2026-03-26)

**v0.3.0** — Epics 59–74 Playwright full-stack test suites complete (96 stories, 304 pts, 95 Ralph commits). Style guide updated with §4.5-4.6 (FOUC prevention, extended tokens), §9.13-9.15 (icon system, inspector panel, kanban board), §14.1 expanded (command palette full spec). Epic 43 ops sign-off granted. All 74 non-deferred epics complete.
