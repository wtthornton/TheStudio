# Story 53.4 -- Admin AI prompt-first trust cues for assisted actions

<!-- docsmcp:start:user-story -->

> **As a** admin operator, **I want** AI actions to preview intent and expose trust cues, **so that** I can confidently approve, edit, or reject system recommendations

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that AI-assisted admin actions are transparent, controllable, and aligned with prompt-first intent standards.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement prompt-first interaction sequence in admin AI-assisted surfaces with intent preview, mode, evidence, ownership cues, and human decision points.

See [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/tools_content.html`
- `src/admin/templates/partials/settings_agent_config.html`
- `src/admin/templates/partials/workflow_detail_content.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add intent capture/preview affordances for admin AI-assisted operations (`src/admin/templates/partials/tools_content.html`)
- [ ] Add execution mode selector and decision controls (`src/admin/templates/partials/settings_agent_config.html`)
- [ ] Expose confidence/evidence/timestamp/ownership metadata block (`src/admin/templates/partials/workflow_detail_content.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.1] AI-assisted flow enforces 5-step prompt-first sequence
- [ ] [SG 8.2] Prompt fields goal/context/constraints/success_criteria/mode are visible or editable
- [ ] [SG 8.3] Intent preview and autonomy dial are shown before execution
- [ ] [SG 8.4] Confidence/provenance/last-updated/ownership cues are present
- [ ] [SG 8.5] High-impact actions require explicit confirmation and risk summary
- [ ] [SG 8.6] AI-generated/transformed content is visibly labeled

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Manual test of AI-assisted admin flow with approve/edit/retry/reject paths
2. Negative test ensures no execute action bypasses confirmation for high-impact operation
3. Audit trail entry created for each confirmed AI action

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Keep friction proportional; only high-impact actions require hard confirmation

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 53.2
- Story 53.3

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
