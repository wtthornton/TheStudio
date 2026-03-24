# Story 54.3 -- Dashboard prompt-first planning and steering flow retrofit

<!-- docsmcp:start:user-story -->

> **As a** pipeline user, **I want** intent preview and mode control before AI actions, **so that** I remain in control of AI-assisted execution decisions

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that AI-assisted planning and steering flows in the dashboard follow the required prompt-first intent model.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Retrofit planning and steering components to enforce the five-step prompt-first sequence and explicit human decision points.

See [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/planning/IntentEditor.tsx`
- `frontend/src/components/SteeringActionBar.tsx`
- `frontend/src/components/planning/RoutingPreview.tsx`
- `frontend/src/stores/intent-store.ts`
- `frontend/src/stores/steering-store.ts`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add prompt object capture and intent preview in intent editor flows (`frontend/src/components/planning/IntentEditor.tsx`)
- [ ] Add mode selector and guarded execution controls in steering actions (`frontend/src/components/SteeringActionBar.tsx`)
- [ ] Expose approve/edit/retry/reject decisions in triage/routing flows (`frontend/src/components/planning/RoutingPreview.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.1] Prompt-first 5-step sequence is enforced for AI-assisted planning/steering
- [ ] [SG 8.2] Prompt object fields are captured or editable in flow
- [ ] [SG 8.3] Autonomy mode is explicit and changeable when permissions allow
- [ ] [SG 8.4] Evidence/provenance and ownership cues shown before commitment
- [ ] [SG 8.5] High-impact actions require confirmation and risk summary
- [ ] [SG 9.2] No hidden autonomous actions

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Scenario tests for draft/suggest/execute transitions
2. Negative tests for bypass attempts on high-impact execute actions
3. Manual UX walkthrough confirms decision checkpoints

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Reuse shared prompt object model from Epic 55

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 54.2
- Story 55.1

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
