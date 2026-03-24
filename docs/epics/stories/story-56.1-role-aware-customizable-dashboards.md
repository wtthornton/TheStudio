# Story 56.1 -- Role-aware customizable dashboards with team-safe reset

<!-- docsmcp:start:user-story -->

> **As a** pipeline user, **I want** saved views and widget customization with reset-to-team-standard, **so that** I can optimize my workflow while preserving team consistency

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that users can personalize dashboard layout without breaking shared operational semantics.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement saved views, widget show/hide and ordering, and one-click reset to team-standard defaults.

See [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/stores/pipeline-store.ts`
- `frontend/src/components/analytics/Analytics.tsx`
- `frontend/src/components/HeaderBar.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement saved view state model and persistence (`frontend/src/stores/pipeline-store.ts`)
- [ ] Add configurable widget layout controls (`frontend/src/components/analytics/Analytics.tsx`)
- [ ] Add reset-to-team-standard control and confirmation (`frontend/src/components/HeaderBar.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 9.3A] User can save named views and customize layout
- [ ] [SG 9.3A] Reset-to-team-standard restores canonical defaults
- [ ] [SG 7.4] Semantic color/status meaning remains unchanged under customization
- [ ] [SG 11] Personalization checklist item passes
- [ ] [SG 9.4] No unbounded no-code semantic drift is introduced
- [ ] [SG 6.1] Non-color cues remain intact after customization

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Unit tests for saved view persistence and reset behavior
2. UI tests verifying widget order/show-hide applies and restores
3. Manual check ensuring semantic mapping unchanged after customization

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Persist per-user in local profile/API once available; include migration-safe defaults

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 54.1

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Can be developed and delivered independently
- [ ] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
