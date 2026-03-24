# Story 57.2 -- Cross-surface regression safety checklist and quality gates

<!-- docsmcp:start:user-story -->

> **As a** qa lead, **I want** repeatable UI regression checklist and gate criteria, **so that** release risk is controlled per rollout wave

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that modernization can move fast without regressions in semantics, accessibility, or trust controls.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Define reusable regression checklist and gate criteria across admin and dashboard surfaces for every modernization wave.

See [Epic 57](docs/epics/epic-57-rollout-governance-and-regression-safety.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/epics/epic-57-rollout-governance-and-regression-safety.md`
- `docs/epics/epic-52-frontend-ui-modernization-master-plan.md`
- `docs/epics/stories/story-54.2-dashboard-state-accessibility-hardening.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define regression checklist covering semantics, states, accessibility, prompt-first and trust cues (`docs/epics/epic-57-rollout-governance-and-regression-safety.md`)
- [ ] Add checklist references to all modernization stories (`docs/epics/stories/story-53.1-admin-shell-navigation-conformance.md`)
- [ ] Attach test expectations to rollout wave criteria (`docs/epics/epic-52-frontend-ui-modernization-master-plan.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 1.3] Cross-surface semantic consistency validated in regression gate
- [ ] [SG 5.x] Loading/empty/error states validated for changed pages
- [ ] [SG 6.x] Keyboard/focus/non-color cues validated for changed controls
- [ ] [SG 8.x] Prompt-first and trust controls validated where AI features exist
- [ ] [SG 11] PR checklist alignment enforced for each wave

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 57](docs/epics/epic-57-rollout-governance-and-regression-safety.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Checklist dry run against one admin and one dashboard story
2. Regression gate review catches intentionally injected semantic mismatch
3. Sign-off workflow documents pass/fail and remediation actions

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Keep checklist concise enough for sprint use but strict enough for quality gate

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 57.1

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
