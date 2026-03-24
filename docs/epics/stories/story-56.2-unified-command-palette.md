# Story 56.2 -- Unified command palette across frontend surfaces

<!-- docsmcp:start:user-story -->

> **As a** power user, **I want** global Ctrl/Cmd+K command palette, **so that** I can move and act quickly without hunting through menus

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that users can navigate and execute common actions quickly via one consistent command palette.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement global command palette with page navigation, recent history, and guarded side-effect actions.

See [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/App.tsx`
- `frontend/src/help/index.ts`
- `frontend/src/components/SteeringActionBar.tsx`
- `src/admin/templates/base.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add global keyboard handler and palette container (`frontend/src/App.tsx`)
- [ ] Implement command registry and recent history (`frontend/src/help/index.ts`)
- [ ] Add guarded confirm flow for side-effect commands (`frontend/src/components/SteeringActionBar.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 9.3B] Ctrl/Cmd+K opens command palette globally
- [ ] [SG 9.3B] Palette supports navigate/action/recent history
- [ ] [SG 8.5] Side-effect commands show confirmation and risk summary
- [ ] [SG 6.3] Palette is keyboard navigable with visible focus
- [ ] [SG 11] Fast-action command pattern item passes
- [ ] [SG 9.2] No hidden autonomous command execution

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Keyboard integration test for Ctrl/Cmd+K open/close and selection
2. Command execution tests for navigation and guarded side-effects
3. Accessibility test for focus trap and ARIA roles in palette

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Admin surface may start with navigation-only command set in first increment

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 54.4

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
