# Story 55.1 -- Shared prompt object and intent preview foundation

<!-- docsmcp:start:user-story -->

> **As a** product engineer, **I want** a reusable prompt object + preview foundation, **so that** AI flows stay consistent and easier to test across surfaces

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that both frontend surfaces use one prompt object contract and one intent preview pattern for AI interactions.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Define typed prompt object contract and reusable intent preview component patterns for admin and dashboard surfaces.

See [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/lib/constants.ts`
- `frontend/src/components/planning/IntentSpec.tsx`
- `frontend/src/components/planning/IntentEditor.tsx`
- `src/admin/templates/partials/tools_content.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define prompt object type and validation helpers (`frontend/src/lib/constants.ts`)
- [ ] Implement reusable intent preview component for dashboard (`frontend/src/components/planning/IntentSpec.tsx`)
- [ ] Add admin-side intent preview partial pattern (`src/admin/templates/partials/tools_content.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.2] Prompt object includes goal/context/constraints/success_criteria/mode
- [ ] [SG 8.1] Intent preview step present before execution
- [ ] [SG 8.3] Impacted surface and planned action shown in preview
- [ ] [SG 1.3] Preview semantics consistent across admin and dashboard
- [ ] [SG 11] AI prompt-first checklist item passes where integrated
- [ ] [SG 9.1] Prompt iteration loop supports revise/regenerate

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Unit tests for prompt object shape validation
2. UI tests verifying preview rendering from both surfaces
3. Manual test of revise/regenerate loop preserving prompt fields

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Prefer typed contracts in frontend and compatible payload shape in APIs

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Epic 55

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
