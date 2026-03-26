# Sprint Plan: Epics 76, 77, 78 -- Pipeline Dashboard Test Suite, Style Compliance, Design Token Unification

**Planned by:** Helm
**Date:** 2026-03-26
**Status:** DRAFT -- Pending Meridian Review
**Epics:**
- Epic 76: Pipeline Dashboard Playwright Full-Stack Test Suite (P1, 73 pts, 14 stories)
- Epic 77: Pipeline Dashboard Style Guide Compliance (P0, 30 pts, 9 stories)
- Epic 78: Design Token Unification (P2, 28 pts, 8 stories)

**Total Duration:** 4 sprints across 8 weeks (Sprint 4 is Epic 78 only, contingent on capacity)
**Capacity:** Single developer, 30 hours per week (5 days x 6 productive hours)
**Executor:** Ralph (autonomous AI agent loops)

---

## Executive Summary

Three epics that form a test-then-fix-then-unify chain:

1. **Epic 76** writes Playwright tests for 12 dashboard tabs (tests will reveal style failures)
2. **Epic 77** fixes the style violations those tests expose (and adds design tokens to React)
3. **Epic 78** extends that token system to the Admin UI so both surfaces share one file

The critical insight: **Epics 76 and 77 can be interleaved.** Epic 77 Stories 77.1-77.8 do NOT depend on Epic 76. Only Story 77.9 (validation pass) requires Epic 76 tests to exist. This means we can run Epic 76 test-writing and Epic 77 style-fixing in parallel across sprints, saving ~2 weeks vs sequential execution.

Epic 78 is P2. It is planned in Sprint 4 but is explicitly compressible -- if Sprints 1-3 overrun, Sprint 4 defers to a follow-on engagement.

---

## Work Stream Architecture

```
Sprint 1 (Weeks 1-2): Epic 76 Foundation + High-Traffic Tabs + Epic 77 Token Foundation
    |
    v  -- Gate: 76.1 conftest works, 76.2-76.3 tests pass, 77.1 theme.css imported --
    |
Sprint 2 (Weeks 3-4): Epic 76 Planning+Config Tabs + Epic 77 Color Standardization
    |
    v  -- Gate: 8/12 tabs tested, button/badge/typography aligned --
    |
Sprint 3 (Weeks 5-6): Epic 76 Remaining Tabs + Cross-Tab + Epic 77 Polish + Validation
    |
    v  -- Gate: 12/12 tabs tested, all Epic 76 style tests passing, Epic 77 DONE --
    |
Sprint 4 (Weeks 7-8): Epic 78 Token Unification [CONTINGENT -- P2]
    |
    v  -- Gate: shared tokens.css consumed by both surfaces, Playwright green --
```

**Rationale for this sequence:**
1. Epic 76.1 (test infrastructure) must land first -- every other 76.x story imports its conftest fixtures. Starting here de-risks the SPA navigation pattern before committing to 72 test files.
2. Epic 77.1 (token foundation) is independent of Epic 76 and takes ~1 Ralph loop. Landing it in Sprint 1 unlocks all of 77.2-77.6 for Sprint 2 with zero idle time.
3. High-traffic tabs (Pipeline, Triage) go first in Epic 76 because regressions there have the highest operator impact. If we run out of time, the most critical tabs already have coverage.
4. Epic 77 color fixes (77.2-77.3) are scheduled after the corresponding tabs have tests, so fixes can be immediately verified -- but this is a bonus, not a hard dependency.
5. Epic 78 is planned last because it depends on Epic 77 for React integration (78.2), and its Admin UI migration (78.3-78.8) is lower priority than getting dashboard tests and style compliance shipped.

---

## Sprint 1: Foundation + High-Traffic Coverage

**Sprint Duration:** 2 weeks (2026-03-27 to 2026-04-09)
**Capacity:** 60 hours total, 75% allocation = 45 hours available, 15 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Establish the Playwright test infrastructure for the React Pipeline Dashboard, deliver complete 6-file test suites for the 2 highest-traffic tabs (Pipeline, Triage), and create the design token CSS foundation for Epic 77.

**Test:** After all stories are complete:

1. `pytest tests/playwright/pipeline_dashboard/ --co` collects tests from at least 13 files (1 conftest + 12 test files for 2 tabs)
2. `pytest tests/playwright/pipeline_dashboard/test_pd_pipeline_intent.py` passes -- Pipeline tab renders stage names (Intake through Publish) or empty state
3. `pytest tests/playwright/pipeline_dashboard/test_pd_triage_intent.py` passes -- Triage tab renders queue heading or empty state
4. All intent, API, interaction, a11y, and snapshot tests for Pipeline and Triage tabs pass (style tests may xfail -- that is expected)
5. `frontend/src/theme.css` exists and is imported as the first line of `frontend/src/index.css`
6. `grep -c "^  --" frontend/src/theme.css` returns >= 60 (token count)
7. `npx vite build` succeeds with no CSS errors after theme.css integration
8. Zero console errors captured across Pipeline and Triage tab test runs

**Constraint:** 2 weeks. Ralph executes stories. Each tab story splits into 3 sub-tasks (intent+api, style+interactions, a11y+snapshot). Epic 77.1 is a single Ralph loop. No style fixes in this sprint -- Epic 76 style tests use `pytest.mark.xfail` for known failures.

### Ordered Work Items

| Order | Story | Epic | Points | Est. Hours | Ralph Loops | Dependency |
|-------|-------|------|--------|------------|-------------|------------|
| 1 | 76.1 -- Test Infrastructure (SPA conftest + tab helpers) | 76 | 3 | 3h | 1 | None -- foundation |
| 2 | 77.1 -- Design token foundation (theme.css + @theme wiring) | 77 | 5 | 4h | 1 | None -- independent track |
| 3 | 76.2 -- Pipeline tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 4 | 76.3 -- Triage tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 5 | 76.4 -- Intent Review tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 6 | 76.5 -- Routing Review tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 7 | 76.6 -- Backlog Board tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| | | **Totals** | **33** | **37h** | **17** | |

**Capacity utilization:** 37h / 60h = 62%

### What's In / What's Out

**In:** 7 stories (2 foundation + 5 tab test suites = 30 test files + 2 infra files + 1 CSS file)

**Out (deferred to Sprint 2):**
- 76.7-76.13 (remaining 7 tab test suites)
- 76.14 (cross-tab compliance -- needs all tabs first)
- 77.2-77.9 (need 77.1 to land first; color work benefits from having more tests available)

**Compressible stories (cut if Sprint 1 runs long):**
1. **76.6** (Backlog Board) -- lowest traffic of the 5 tab stories; can slide to Sprint 2
2. **76.5** (Routing Review) -- similar empty-state pattern to Intent Review; redundant learning

### Estimation Notes

| Story | Confidence | Key Unknown | Assumption |
|-------|-----------|-------------|------------|
| 76.1 | High | SPA query-param navigation may need different wait strategy than server-rendered pages | 500ms wait after navigation is sufficient; if not, add `wait_for_selector` on tab content |
| 77.1 | High | Tailwind v4 @theme directive syntax differs from v3 theme.extend | Style guide Section 4.4 examples need adaptation to CSS-first config; Ralph reads Tailwind v4 docs |
| 76.2 | Medium | SSE connection for pipeline data may cause test timeouts | Tests validate DOM after initial load, not SSE stream; mock SSE if needed |
| 76.3 | Medium | Triage tab may require task data to render meaningful content | Empty-state validation is the primary path; populated state is bonus |
| 76.4-76.6 | High | Empty-state tabs have simpler DOM but still need 6 test types each | Pattern established by 76.2-76.3 applies; Ralph reuses templates |

### Internal Dependencies (Story-to-Story)

```
76.1 (conftest) ──> 76.2 (pipeline) ──> 76.3 (triage) ──> 76.4 (intent) ──> 76.5 (routing) ──> 76.6 (board)
                                                                                                        |
77.1 (tokens)  ─────────────────────────────────────────────────────── [independent, no dependency] ─────|
```

- **76.1 has no dependencies** -- creates the test package and conftest
- **77.1 has no dependencies** -- creates theme.css and wires it into index.css; does not depend on any Epic 76 work
- **76.2-76.6 depend only on 76.1** -- each tab test suite imports from the pipeline_dashboard conftest
- **76.2-76.6 are independent of each other** -- can be executed in any order after 76.1, but sequenced by traffic priority for risk reduction
- **77.1 is independent of all 76.x** -- runs on a separate track

**Critical path:** 76.1 --> 76.2 (highest-risk: first SPA tab test, establishes pattern)

---

## Sprint 2: Configuration Tabs + Color Standardization

**Sprint Duration:** 2 weeks (2026-04-10 to 2026-04-23)
**Capacity:** 60 hours total, 75% allocation = 45 hours available, 15 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Complete Playwright test suites for 5 more dashboard tabs (Trust, Budget, Activity, Analytics, Reputation), bringing coverage to 9/12 tabs. Simultaneously, standardize all primary button colors and status badge colors across the React dashboard to match the style guide.

**Test:** After all stories are complete:

1. `pytest tests/playwright/pipeline_dashboard/ --co` collects tests from at least 55 files (1 conftest + 54 test files for 9 tabs)
2. All intent, API, interaction, a11y, and snapshot tests for Trust, Budget, Activity, Analytics, and Reputation tabs pass
3. `grep -rE "bg-(indigo|violet|emerald)-[67]00" frontend/src/components/` returns 0 matches in primary button contexts
4. `grep -rE "bg-emerald-[89]00|text-emerald-300" frontend/src/components/` returns 0 matches
5. At least 20 React components carry `data-component` attributes (discoverable via `grep -r "data-component" frontend/src/components/ | wc -l`)
6. `npx vitest run` passes with no regressions from color class changes
7. Previously-xfailed style tests for button colors now pass (for tabs where 77.2 fixes apply)

**Constraint:** 2 weeks. No new features, no new APIs. Epic 77 stories are purely visual alignment -- no behavior changes. Ralph handles sub-tasks. Each Epic 76 tab story splits into 3 sub-tasks of 2 files each.

### Ordered Work Items

| Order | Story | Epic | Points | Est. Hours | Ralph Loops | Dependency |
|-------|-------|------|--------|------------|-------------|------------|
| 1 | 76.7 -- Trust Tiers tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 (Sprint 1) |
| 2 | 76.8 -- Budget tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 3 | 77.2 -- Primary button color standardization (12 files) | 77 | 5 | 4h | 2 | 77.1 (Sprint 1) |
| 4 | 77.3 -- Status badge color alignment (13 files) | 77 | 3 | 3h | 1 | 77.1 |
| 5 | 77.4 -- Data attribute instrumentation (20+ files) | 77 | 5 | 5h | 2 | None (independent) |
| 6 | 76.9 -- Activity Log tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 7 | 76.10 -- Analytics tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 8 | 76.11 -- Reputation tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| | | **Totals** | **38** | **42h** | **20** | |

**Capacity utilization:** 42h / 60h = 70%

### What's In / What's Out

**In:** 8 stories (5 tab test suites + 3 style compliance stories = 30 test files + style fixes across ~45 component files)

**Out (deferred to Sprint 3):**
- 76.12-76.13 (Repos, API Reference -- final 2 tabs)
- 76.14 (cross-tab compliance -- needs all 12 tabs)
- 77.5-77.9 (typography, recipes, focus rings, empty states, validation)

**Compressible stories (cut if Sprint 2 runs long):**
1. **76.11** (Reputation tab) -- lower traffic; can slide to Sprint 3
2. **77.4** (data attributes) -- additive instrumentation; not blocking any other story in Sprint 2

### Sequencing Rationale

- **76.7-76.8 first:** Trust and Budget are configuration tabs with form interactions -- higher complexity than monitoring tabs, so tackle them while energy is fresh
- **77.2-77.3 mid-sprint:** Button and badge color fixes are mechanical find-and-replace work. Placing them after the first 2 tab test suites means Ralph has established the Sprint 2 rhythm. These fixes also immediately improve style test pass rates for previously-written tabs
- **77.4 after color fixes:** Data attributes are independent of colors but benefit from the files being fresh in Ralph's context (many overlap with 77.2/77.3 touched files)
- **76.9-76.11 last:** Monitoring tabs (Activity, Analytics, Reputation) are data-heavy views with simpler interaction patterns. Lower risk; can absorb schedule compression

### Estimation Notes

| Story | Confidence | Key Unknown | Assumption |
|-------|-----------|-------------|------------|
| 77.2 | High | Some button color classes may be in conditional Tailwind strings (template literals) | Ralph greps for patterns, not just static strings; conditional classes are updated inline |
| 77.3 | High | Badge components may compose colors from props, not static classes | If color comes from a prop mapping object, update the mapping object once |
| 77.4 | Medium | 20+ files need `data-component` -- may exceed Ralph's 5-file edit limit per loop | Split into 2 loops: components A-L, then M-Z (as noted in epic) |
| 76.9 | Medium | Activity tab renders via else-fallthrough in App.tsx, not explicit conditional | Test navigates via ?tab=activity; DOM content is what matters, not routing mechanism |

---

## Sprint 3: Final Tabs + Cross-Tab Compliance + Epic 77 Completion

**Sprint Duration:** 2 weeks (2026-04-24 to 2026-05-07)
**Capacity:** 60 hours total, 77% allocation = 46 hours available, 14 hours buffer

### Sprint Goal (Testable Format)

**Objective:** Complete Playwright coverage for all 12 dashboard tabs plus cross-tab compliance suite (Epic 76 DONE). Complete all remaining Epic 77 style fixes and run the full validation pass (Epic 77 DONE).

**Test:** After all stories are complete:

1. `pytest tests/playwright/pipeline_dashboard/ --co` collects tests from 74 files (1 conftest + 72 tab tests + 1 cross-tab compliance)
2. All 72 tab test files pass (intent, API, interaction, a11y, snapshot types). Style tests that were xfailed are now passing after Epic 77 fixes
3. `pytest tests/playwright/pipeline_dashboard/test_pd_cross_tab_compliance.py` passes for all 12 tabs x 5 compliance dimensions (typography, spacing, recipes, colors, focus rings)
4. `grep -c "^  --" frontend/src/theme.css` >= 60 tokens
5. `grep -rE "bg-(indigo|violet|emerald)-[67]00" frontend/src/components/` returns 0
6. `grep -rE "bg-emerald-[89]00|text-emerald-300" frontend/src/components/` returns 0
7. `grep -r "data-component" frontend/src/components/ | wc -l` >= 20
8. `npx vitest run` passes -- no regressions from any Epic 77 changes
9. Full Playwright suite (Admin + Dashboard) passes: 0 failures
10. Epic 76 and Epic 77 can both be marked COMPLETE

**Constraint:** 2 weeks. This sprint has the highest story count but the stories are smaller (2-3 pts each). The cross-tab compliance test (76.14) runs last because it parametrizes over all 12 tabs. Story 77.9 (validation pass) is the final story because it catches anything 77.1-77.8 missed.

### Ordered Work Items

| Order | Story | Epic | Points | Est. Hours | Ralph Loops | Dependency |
|-------|-------|------|--------|------------|-------------|------------|
| 1 | 76.12 -- Repos tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 (Sprint 1) |
| 2 | 76.13 -- API Reference tab tests (6 files) | 76 | 5 | 6h | 3 | 76.1 |
| 3 | 77.5 -- Typography alignment (3 files) | 77 | 2 | 2h | 1 | 77.1 (Sprint 1) |
| 4 | 77.6 -- Card/table/modal recipe alignment (5 files) | 77 | 3 | 3h | 1 | 77.1 |
| 5 | 77.7 -- Focus ring and accessibility color fixes | 77 | 2 | 2h | 1 | 77.2, 77.3 (Sprint 2) |
| 6 | 77.8 -- Empty state and error state alignment (2 files) | 77 | 2 | 2h | 1 | 77.1 |
| 7 | 76.14 -- Cross-tab style compliance (parametrized) | 76 | 5 | 5h | 2 | All 76.2-76.13 |
| 8 | 77.9 -- Validation pass (run Epic 76 tests, fix failures) | 77 | 3 | 4h | 1-2 | All 76.x, all 77.1-77.8 |
| | | **Totals** | **27** | **30h** | **13-14** | |

**Capacity utilization:** 30h / 60h = 50%

The lower utilization is intentional. Sprint 3 has two high-uncertainty stories (76.14 cross-tab compliance and 77.9 validation pass) that may reveal cascading failures requiring rework. The 50% allocation provides a 30-hour buffer for:
- Fixing xfail tests that should now pass but don't
- Addressing integration issues between Epic 76 tests and Epic 77 fixes
- Rework from any Sprint 1-2 stories that need adjustment

### What's In / What's Out

**In:** 8 stories (2 tab test suites + cross-tab compliance + 4 style stories + validation = Epic 76 COMPLETE + Epic 77 COMPLETE)

**Out (deferred to Sprint 4 or follow-on):**
- Epic 78 entirely (planned for Sprint 4 if Sprints 1-3 deliver on schedule)

**Compressible stories (cut if Sprint 3 runs long):**
1. **77.6** (card/table/modal recipes) -- polish work; if buttons, badges, and tokens are correct, recipe alignment is cosmetic
2. **77.8** (empty/error state alignment) -- affects only 2 files; can merge into 77.9 validation pass if time is short

### Sequencing Rationale

- **76.12-76.13 first:** Complete all 12 tab test suites before attempting cross-tab compliance
- **77.5-77.8 mid-sprint:** These are small polish stories (2-3 pts each) that can be interleaved while Ralph processes tab tests. They must complete before 77.9
- **76.14 after all tab tests:** Cross-tab parametrized test iterates over all 12 tabs -- requires all tab conftest entries and tab content to be testable
- **77.9 absolutely last:** The validation pass runs Epic 76 tests against the Epic 77 fixed codebase. Everything else must be done first. If failures emerge, the 30-hour buffer covers rework

---

## Sprint 4: Epic 78 -- Design Token Unification [CONTINGENT]

**Sprint Duration:** 2 weeks (2026-05-08 to 2026-05-21)
**Capacity:** 60 hours total, 73% allocation = 44 hours available, 16 hours buffer
**Prerequisite:** Sprints 1-3 complete. Epic 76 DONE. Epic 77 DONE.
**Go/No-Go Decision:** 2026-05-07. If Sprints 1-3 have overrun by more than 1 week, defer Epic 78 to a separate engagement.

### Sprint Goal (Testable Format)

**Objective:** Create a single shared `static/css/tokens.css` file consumed by both the React Pipeline Dashboard and the HTMX Admin Console. Migrate all Admin UI hardcoded color references to semantic tokens. Both surfaces render pixel-identical to their current appearance.

**Test:** After all stories are complete:

1. `static/css/tokens.css` exists and contains all Section 4.1-4.4 tokens from the style guide
2. `src/admin/templates/base.html` loads `tokens.css` via `<link>` tag; the inline `--ts-*` style block is removed
3. `frontend/src/index.css` imports `tokens.css` (or the shared CSS custom properties are available)
4. `grep -cE "bg-gray-|text-gray-|border-gray-" src/admin/templates/{*.html,components/*.html,partials/*.html}` returns 0 for page and component templates (partials may retain status-badge macro classes)
5. Full Playwright test suite passes: 0 regressions across all Admin + Dashboard tests
6. `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` contains a "For Developers" subsection with Jinja2 and React token usage examples

**Constraint:** 2 weeks. Visual identity must not change -- this is a refactor, not a redesign. Tailwind CDN stays for Admin UI. No new CSS dependencies. Playwright tests are the regression gate after each batch.

### Ordered Work Items

| Order | Story | Points | Est. Hours | Ralph Loops | Dependency |
|-------|-------|--------|------------|-------------|------------|
| 1 | 78.1 -- Create shared token CSS file + static mount | 3 | 4h | 1 | None (foundation) |
| 2 | 78.2 -- Integrate tokens into React frontend | 2 | 2h | 1 | 78.1 + Epic 77 DONE |
| 3 | 78.3 -- Integrate tokens into Admin UI base template | 3 | 4h | 1 | 78.1 |
| 4 | 78.4 -- Admin migration batch 1 (Dashboard, Repos, Workflows, Audit) | 5 | 6h | 2 | 78.3 |
| 5 | 78.5 -- Admin migration batch 2 (Metrics, Experts, Tools, Models) | 5 | 6h | 2 | 78.3 |
| 6 | 78.6 -- Admin migration batch 3 (Compliance, Quarantine, DLQ, Planes, Settings, Cost, Portfolio) | 5 | 7h | 2-3 | 78.3 |
| 7 | 78.7 -- Component template migration + cross-surface validation | 3 | 4h | 1 | 78.4-78.6 |
| 8 | 78.8 -- Token documentation in style guide | 2 | 2h | 1 | 78.1-78.7 |
| | | **28** | **35h** | **11-12** | |

**Capacity utilization:** 35h / 60h = 58%

The low utilization is intentional for a P2 epic. Each Admin migration batch (78.4-78.6) touches 10-15 template files and must pass Playwright regression after each batch. If the Tailwind CDN does not correctly resolve `bg-[var(--color-bg-surface)]` syntax, the fallback strategy (inline `style` attributes) adds 50-100% time to each batch. The buffer covers this risk.

### Compressible stories (cut if Sprint 4 runs long):
1. **78.8** (documentation) -- important but not load-bearing; can be a follow-on task
2. **78.6** (batch 3) -- largest batch, covers lower-traffic Admin pages; can be deferred to a Sprint 5

---

## Cross-Sprint Dependency Graph

```
SPRINT 1                    SPRINT 2                    SPRINT 3                    SPRINT 4
--------                    --------                    --------                    --------

76.1 (conftest) ──> 76.2 ─> 76.7 ──> 76.8              76.12 ─> 76.13
                    76.3     76.9 ──> 76.10 ─> 76.11              |
                    76.4                                           v
                    76.5                                    76.14 (cross-tab)
                    76.6                                           |
                                                                   v
77.1 (tokens) ────> ────────> 77.2 (buttons) ──┐         77.5 (typo) ──┐
                              77.3 (badges)  ──┤         77.6 (recipes)─┤
                              77.4 (data-*)  ──┤         77.7 (focus) ──┤        78.1 (shared CSS)
                                               │         77.8 (empty) ──┤         |    |
                                               │                        │         v    v
                                               └────────────────────────┤  78.2 (React)  78.3 (Admin)
                                                                        │              |
                                                                        v              v
                                                                 77.9 (validate)  78.4 -> 78.5 -> 78.6
                                                                                       |
                                                                                       v
                                                                                 78.7 -> 78.8

LEGEND:
  ──>  dependency (must complete before)
  76.x = Epic 76 (Playwright tests)
  77.x = Epic 77 (Style compliance)
  78.x = Epic 78 (Token unification)
```

### Critical Path

The longest dependency chain determines the minimum delivery time:

```
76.1 --> 76.2 --> ... --> 76.13 --> 76.14 --> 77.9 (validation)
                                                |
                                                v
                                          EPIC 76+77 DONE
                                                |
                                                v
                                         78.1 --> 78.3 --> 78.6 --> 78.7 --> 78.8
                                                                              |
                                                                              v
                                                                        EPIC 78 DONE
```

**Critical path length:** 76.1 + 12 tab stories + 76.14 + 77.9 + 78.1 + 78.3 + 78.6 + 78.7 + 78.8 = ~20 stories

**Key acceleration:** 77.1-77.8 run on a parallel track, not the critical path. They must finish before 77.9 but do not block any Epic 76 story.

---

## Velocity and Capacity Summary

| Sprint | Stories | Points | Est. Hours | Capacity | Utilization | Buffer |
|--------|---------|--------|------------|----------|-------------|--------|
| Sprint 1 (Wk 1-2) | 7 | 33 | 37h | 60h | 62% | 23h |
| Sprint 2 (Wk 3-4) | 8 | 38 | 42h | 60h | 70% | 18h |
| Sprint 3 (Wk 5-6) | 8 | 27 | 30h | 60h | 50% | 30h |
| Sprint 4 (Wk 7-8) | 8 | 28 | 35h | 60h | 58% | 25h |
| **Total** | **31** | **126** | **144h** | **240h** | **60%** | **96h** |

### Why 60% average utilization (not 75-80%)?

Three reasons:

1. **These are Playwright test epics, not feature epics.** Test-writing against a running SPA has higher variance than writing production code. Tests may fail due to environment issues (Docker stack, SSE connections, React hydration timing), not code bugs. Each failure requires diagnosis before Ralph can proceed.

2. **Epic 76 style tests are expected to xfail initially.** As Epic 77 fixes land, those xfails must be converted to passing tests. The conversion is not free -- each xfail removal is a verify-and-update cycle.

3. **Epic 78 carries Tailwind CDN risk.** If `bg-[var(--color-bg-surface)]` does not resolve correctly in the CDN runtime, every Admin template migration takes 2x longer with inline style fallbacks.

The buffer is real work capacity, not slack. Historical sprints at 77-83% allocation were feature epics with lower environmental uncertainty.

---

## External Dependencies

| Dependency | Status | Sprint Impact | Mitigation |
|-----------|--------|---------------|------------|
| Docker Compose stack running (port 9080) | Required for all Playwright tests | All sprints | Pre-sprint: verify `docker compose up` and healthz check pass |
| `frontend/dist/` built | Required for dashboard tests | All sprints | Pre-sprint: run `cd frontend && npm run build` |
| `infra/.env` with `ADMIN_PASSWORD` plaintext | Required for Caddy auth in tests | All sprints | Verify exists before Sprint 1 starts (known issue from memory) |
| Epic 58 Playwright infra (COMPLETE) | Required -- test helpers in `tests/playwright/lib/` | Sprint 1 | Confirmed complete |
| Epic 54 Dashboard UI compliance (COMPLETE) | Semantic baseline for Epic 77 | Sprint 2 | Confirmed complete |
| No `static/` mount in `src/app.py` | Must be created in Story 78.1 | Sprint 4 | Explicit task, not assumption |

---

## Risk Register

| # | Risk | Likelihood | Impact | Sprint | Mitigation |
|---|------|-----------|--------|--------|------------|
| R1 | SPA query-param navigation fails in Playwright (React hydration timing) | Medium | High (blocks all 76.x) | Sprint 1 | 76.1 is the de-risking story; if navigation fails, increase wait or add `wait_for_selector` before committing to 72 test files |
| R2 | SSE connection causes test timeouts on Pipeline tab | Medium | Medium (blocks 76.2) | Sprint 1 | Test against static DOM after initial load; mock SSE endpoint if needed |
| R3 | Epic 77 color changes break existing Vitest tests that assert specific CSS classes | High | Low (easy fix) | Sprint 2 | Each 77.x story updates Vitest assertions in the same commit as the color change |
| R4 | Cross-tab compliance test (76.14) reveals systemic failures across all 12 tabs | Medium | Medium | Sprint 3 | 30h buffer in Sprint 3 specifically allocated for this; parametrized xfails reduce noise |
| R5 | Tailwind CDN does not resolve `var()` in utility classes for Admin templates | Medium | High (doubles 78.4-78.6 effort) | Sprint 4 | Fallback: use inline `style` attributes; Sprint 4 has 25h buffer for this |
| R6 | Epic 78 Story 78.2 blocked if Epic 77 not complete | Low | Medium | Sprint 4 | Epic 77 completes in Sprint 3; if Sprint 3 slips, 78.2 defers and 78.3-78.8 proceed independently |

---

## Definition of Done (Per Sprint)

Each sprint is DONE when:

1. All "In" stories have passing tests (or documented xfails with Epic 77 remediation tags)
2. `ruff check .` is clean (no new lint violations)
3. `npx vitest run` passes (no frontend test regressions)
4. All new test files follow naming convention `test_pd_{tab}_{type}.py`
5. Zero console errors captured during Playwright test execution
6. Sprint goal "Test" criteria all pass
7. Changes committed and pushed to master

## Meridian Review Checkpoint

**This plan requires Meridian review before execution begins.**

Meridian should validate:
1. Is the interleaving of Epics 76 and 77 sound, given that 77.1-77.8 do not depend on 76?
2. Is 62% utilization in Sprint 1 justified, or should more 76.x stories be pulled in?
3. Is the 30-hour buffer in Sprint 3 excessive for the validation-pass risk?
4. Is the Sprint 4 go/no-go gate (2026-05-07) the right decision point for Epic 78?
5. Are the compressible story choices correct (would cutting a different story be safer)?
6. Does the cross-sprint dependency graph accurately reflect the epic dependency notes?
7. Is the Tailwind CDN risk (R5) adequately mitigated, or should a spike be added to Sprint 3?
