# Story 56.3 -- Localization and cross-cultural readiness baseline

<!-- docsmcp:start:user-story -->

> **As a** global user, **I want** locale-aware formats and resilient text layouts, **so that** the product remains understandable and usable across locales

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the UI can present locale-aware values and tolerate translation growth without layout breakage.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Introduce locale formatting helpers and remove brittle fixed-width assumptions across key views.

See [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/lib/api.ts`
- `frontend/src/components/TaskTimeline.tsx`
- `frontend/src/components/analytics/ThroughputChart.tsx`
- `src/admin/templates/partials/metrics_content.html`
- `src/admin/templates/partials/dashboard_content.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create locale-aware date/number/currency format helper utilities (`frontend/src/lib/api.ts`)
- [ ] Apply locale formatting to analytics and timeline displays (`frontend/src/components/TaskTimeline.tsx`)
- [ ] Audit and fix hardcoded text-width assumptions in admin templates (`src/admin/templates/partials/metrics_content.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 9.3D] Date/time/number/currency are locale-aware
- [ ] [SG 9.3D] Layout tolerates translated string expansion
- [ ] [SG 9.3D] Copy and iconography remain culturally neutral
- [ ] [SG 11] Locale/format assumptions are explicit for user-facing values
- [ ] [SG 6.5] Labels remain concise and concrete after localization
- [ ] [SG 1.3] Cross-surface formatting semantics are consistent

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 56](docs/epics/epic-56-cross-surface-2026-capability-modules.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Locale snapshot tests (en-US
2. de-DE
3. ja-JP) for formatted values
4. Manual resize/overflow checks with long translated strings
5. Regression tests for tables and cards after localization adjustments

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Start with i18n-ready formatting layer even before full translation system adoption

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
