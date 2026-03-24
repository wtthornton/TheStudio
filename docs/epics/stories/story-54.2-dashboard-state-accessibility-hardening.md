# Story 54.2 -- Dashboard explicit state handling and accessibility hardening

> **Delivery status:** Partially complete (2026-03-24) — Wave 1 + Wave 2 (intent modals)  
> **Done:** `EmptyState.tsx` focus-visible rings; `TriageQueue.tsx` `role="alert"`, Retry passes `selectedRepo`, focus ring; `CreateTaskModal.tsx` `role="dialog"` / `aria-modal` / `aria-labelledby`, `role="alert"` on errors, button `type` + focus rings. **Wave 2:** `RefinementModal.tsx` — same dialog/backdrop pattern, Escape respects `saving`, focus-visible on actions; `IntentEditor.tsx` — reject flow as modal dialog, loading `role="status"`, error `role="alert"`, toolbar `type="button"` + focus-visible rings.  
> **Remaining:** Any other dashboard modals/panels not yet aligned; optional focus trap where product requires strict modal containment.  
> **Doc sync:** Status mirrored in `epic-52-frontend-ui-modernization-master-plan.md`, `epic-52-gap-report-admin-vs-dashboard.md`, `epic-54-dashboard-ui-canonical-compliance.md`, traceability matrix SG 5.x / 6.x rows.

<!-- docsmcp:start:user-story -->

> **As a** pipeline user, **I want** explicit loading, empty, and error states with keyboard support, **so that** I can continue operating during partial failures and async refreshes

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that dashboard workflows remain understandable and accessible under all data/loading/error conditions.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add or normalize missing loading/empty/error states, focus management, and semantic structure across major dashboard components.

See [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/ErrorStates.tsx`
- `frontend/src/components/planning/TriageQueue.tsx`
- `frontend/src/components/planning/IntentEditor.tsx`
- `frontend/src/components/planning/CreateTaskModal.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Standardize empty and error component usage (`frontend/src/components/EmptyState.tsx`)
- [ ] Ensure fallback states in planning and analytics modules (`frontend/src/components/planning/TriageQueue.tsx`)
- [ ] Fix keyboard/focus behavior in modal and panel flows (`frontend/src/components/planning/CreateTaskModal.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 5.1] Loading states are explicit and layout-stable
- [ ] [SG 5.2] Empty states explain missing data and next action
- [ ] [SG 5.3] Error/warning/success semantics use canonical styling and copy
- [ ] [SG 6.3] Keyboard reachability and visible focus are verified
- [ ] [SG 6.4] Semantic structures improve assistive parsing
- [ ] [SG 11] State/accessibility checklist items pass for updated modules

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Keyboard-only flow through triage and intent editor paths
2. Unit tests covering empty/error states for key components
3. Manual focus-not-obscured checks in slide panels/modals

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use reusable state primitives to avoid per-component divergence

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 54.1

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
