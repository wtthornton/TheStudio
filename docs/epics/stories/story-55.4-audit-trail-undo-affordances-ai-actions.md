# Story 55.4 -- Audit trail and undo affordances for AI actions

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** clear action history and undo options, **so that** I can safely experiment and recover from poor AI output

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that AI actions are auditable and reversible where feasible, reducing overtrust and fear of exploration.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement action audit entries and undo/revert affordances for AI-assisted operations across surfaces.

See [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/SteeringActivityLog.tsx`
- `frontend/src/components/pr/ReviewerActions.tsx`
- `frontend/src/stores/steering-store.ts`
- `src/admin/templates/partials/audit_list.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add action audit timeline for steering and review events (`frontend/src/components/SteeringActivityLog.tsx`)
- [ ] Expose revert action where mutable outputs exist (`frontend/src/components/pr/ReviewerActions.tsx`)
- [ ] Render admin-side action audit entries (`src/admin/templates/partials/audit_list.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.3] Action audit is available for AI actions
- [ ] [SG 8.3] Undo/revert action available where technically feasible
- [ ] [SG 8.5] Irreversible actions require final acknowledgment
- [ ] [SG 9.1] Revert-to-previous-result loop is supported
- [ ] [SG 11] Transparency and correction/override checklist items pass

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Audit log event tests for approve/edit/reject/retry actions
2. Manual test of undo/revert in supported flows
3. Negative test for irreversible action requiring explicit acknowledgment

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Where undo is impossible
- provide explicit rationale and safer fallback path

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 55.2
- Story 55.3

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
