# Story 54.4 -- Dashboard responsive baseline for desktop tablet mobile

<!-- docsmcp:start:user-story -->

> **As a** pipeline user, **I want** responsive behavior that preserves task-critical operations, **so that** I can triage and approve work from any supported device size

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that critical dashboard workflows remain usable across desktop, tablet, and mobile layouts.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Apply responsive breakpoints and density reduction patterns to key pipeline/planning views while preserving semantic consistency.

See [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/TaskTimeline.tsx`
- `frontend/src/components/planning/BacklogBoard.tsx`
- `frontend/src/components/planning/TriageQueue.tsx`
- `frontend/src/App.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Implement table-to-compact-table/card fallback for key lists (`frontend/src/components/TaskTimeline.tsx`)
- [ ] Adjust planning board and triage cards for tablet/mobile touch targets (`frontend/src/components/planning/BacklogBoard.tsx`)
- [ ] Verify command and approval controls remain reachable on small screens (`frontend/src/App.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 9.3C] Critical workflows remain functional on tablet and mobile
- [ ] [SG 1.3] Cross-surface semantic meanings preserved under responsive states
- [ ] [SG 6.3] Keyboard and touch navigation remains practical and focus-visible
- [ ] [SG 11] Responsive behavior defined for any new/updated page
- [ ] [SG 9.2] Avoid chart/layout patterns that reduce operational readability

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Viewport tests at desktop/tablet/mobile breakpoints
2. Manual touch target verification for primary actions
3. Regression snapshots for table->card fallback transitions

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Desktop-first remains primary; mobile supports critical operations not full density parity

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 54.1
- Story 54.2

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Can be developed and delivered independently
- [ ] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
