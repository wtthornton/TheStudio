# Story 55.2 -- Execution mode controls and human decision checkpoints

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** clear draft/suggest/execute controls and decision checkpoints, **so that** I can calibrate autonomy without losing oversight

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that AI autonomy levels are explicit, permission-aware, and always subject to human decision points.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement consistent mode selector and decision controls (approve/edit/retry/reject) across impacted AI flows.

See [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/TrustConfiguration.tsx`
- `frontend/src/components/pr/ReviewerActions.tsx`
- `frontend/src/components/SteeringActionBar.tsx`
- `src/admin/templates/partials/settings_agent_config.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add mode selector UX and permissions display (`frontend/src/components/TrustConfiguration.tsx`)
- [ ] Integrate decision controls in reviewer and steering actions (`frontend/src/components/pr/ReviewerActions.tsx`)
- [ ] Add equivalent admin decision controls for AI-assisted actions (`src/admin/templates/partials/settings_agent_config.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.1] Mode choice appears before execution stage
- [ ] [SG 8.3] Autonomy dial reflects allowed permissions
- [ ] [SG 8.5] High-impact operations require explicit acknowledgment
- [ ] [SG 8.4] Ownership cue indicates user responsibility
- [ ] [SG 9.2] No opaque AI-only control replacement of manual workflows
- [ ] [SG 11] AI transparency and override checklist items pass

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. E2E tests for mode-switching and permission constraints
2. Negative tests for executing without decision checkpoint
3. Manual test for fallback/escalation to manual flow

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Decision controls should remain concise and not overwhelm operator workflows

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

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
