# Story 56.4 -- Optional artifact-linked collaboration layer

<!-- docsmcp:start:user-story -->

> **As a** collaborating reviewer, **I want** inline comments and mentions linked to artifacts, **so that** handoffs and decisions remain clear and auditable

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that teams can collaborate around specific artifacts with auditable decision context.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add optional comment/mention threads linked to artifacts and include actor/time/change audit metadata.

See [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/pr/EvidenceExplorer.tsx`
- `frontend/src/components/ActivityStream.tsx`
- `frontend/src/stores/notification-store.ts`
- `src/admin/templates/partials/audit_list.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add artifact comment thread component (`frontend/src/components/pr/EvidenceExplorer.tsx`)
- [ ] Add mention and handoff metadata in activity feed (`frontend/src/components/ActivityStream.tsx`)
- [ ] Render admin-side audit trail for collaboration events (`src/admin/templates/partials/audit_list.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 9.3E] Collaboration comments are linked to specific artifacts
- [ ] [SG 9.3E] Mentions and handoffs preserve context
- [ ] [SG 9.3E] Auditability includes who/when/decision change
- [ ] [SG 8.4] Collaboration on AI outputs retains trust metadata context
- [ ] [SG 11] Collaboration behavior is documented when introduced

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. UI tests for artifact-bound comment thread creation/retrieval
2. Audit tests for actor/timestamp/decision-change entries
3. Manual workflow test for comment-based handoff

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Feature-flag collaboration layer by surface to keep optional scope

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 55.4

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
