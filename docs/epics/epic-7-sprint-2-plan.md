# Epic 7 Sprint 2 Plan — Platform Maturity Admin UI

> Helm — Planner & Dev Manager | Created: 2026-03-07

---

## Sprint Goal

**Objective:** Admin UI pages for Tool Hub, Model Gateway, Compliance Scorecard, and Operational Targets are implemented with HTMX partials and tested.

**Test:** Navigating to `/admin/ui/tools`, `/admin/ui/models`, `/admin/ui/compliance`, and `/admin/ui/targets` renders data from the Sprint 1 services. All new tests pass.

**Constraint:** Follow existing HTMX + Jinja2 + Tailwind pattern. Full page + partial for each console. No new JS frameworks.

---

## Retro Actions from Sprint 1

| Action | How addressed |
|--------|---------------|
| Auth override pattern (dependency_overrides vs patch) | Use `get_current_user_role` override consistently in all UI tests |
| TemplateResponse deprecation | Deferred again — functional but warnings persist. Tackle in Epic 8 cleanup. |

---

## Stories

### Story 7.10 — Tool Hub Console UI
- Full page: `/admin/ui/tools` with sidebar nav entry
- Partial: `/admin/ui/partials/tools` renders catalog with suites, tools, approval status
- Shows 3 standard suites with tool count, approval badge (observe/suggest/execute)
- Access check form: role + tier + suite + tool -> allowed/denied result
- Tests: page renders, partial shows suites, access check form works
- **Estimate:** Medium

### Story 7.11 — Model Gateway Console UI
- Full page: `/admin/ui/models` with sidebar nav entry
- Partial: `/admin/ui/partials/models` renders providers, routing rules summary, budget status
- Shows 3 providers with class, cost, enabled status
- Routing simulator: step dropdown -> shows resolved class
- Tests: page renders, partial shows providers, routing simulator works
- **Estimate:** Medium

### Story 7.12 — Compliance Scorecard UI
- Full page: `/admin/ui/compliance` with sidebar nav entry
- Partial: `/admin/ui/partials/compliance` renders scorecard for a repo
- Shows 7 checks with pass/fail badges and remediation details
- Overall pass/fail banner
- Tests: page renders, partial shows 7 checks, pass/fail states
- **Estimate:** Small-Medium

### Story 7.13 — Operational Targets Dashboard UI
- Extend metrics partial to include lead time, cycle time, and reopen target cards
- Lead time card: P50/P95/P99 with insufficient data handling
- Cycle time card: P50/P95/P99 with insufficient data handling
- Reopen target card: current rate vs 5% target with MEETING/NOT MEETING badge
- Tests: metrics partial renders target cards, insufficient data handling
- **Estimate:** Small-Medium

### Story 7.14 — Navigation & Integration
- Add sidebar nav entries: Tools, Models, Compliance (after Experts, before Audit)
- Update base.html navigation
- Tests: navigation links present in rendered pages
- **Estimate:** Small

---

## Order of Work

```
7.14 (nav update) -> 7.10 + 7.11 + 7.12 + 7.13 (all parallel after nav)
```

7.14 is done first since all UI stories need the nav entries. Then 7.10-7.13 are independent.

---

## What's Out This Sprint

- Quarantine Operations UI (no quarantine service exists yet)
- Merge Mode Controls (minimal value without real repos)
- Policy & Guardrails Console (can be a future sprint — compliance scorecard covers the core need)

---

## Capacity & Buffer

- 5 stories, all UI work
- Story 7.13 is the buffer candidate (extends existing partial vs new page)
