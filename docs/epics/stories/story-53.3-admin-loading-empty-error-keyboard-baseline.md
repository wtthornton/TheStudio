# Story 53.3 -- Admin loading empty error and keyboard baseline

> **Delivery status:** Partially complete (2026-03-24) — Wave 1 + Wave 2 (settings)  
> **Done:** Global `:focus-visible` outline in `src/admin/templates/base.html` (SG 6); primary CTA on `empty_state.html` aligned to blue-600 (SG 4.3). `workflows.html` / list partials already had explicit loading + empty states. **Wave 2:** `settings_content.html` — per-card `aria-label`, loading text + `role="status"` / `aria-live="polite"`; `data-admin-htmx-section` + `htmx:responseError` handler in `base.html` with Retry (SG 5.3).  
> **Remaining:** Sweep other admin partials (tools, models, metrics, …) for the same HTMX error pattern; normalize `empty_state` usage where still generic.  
> **Doc sync:** Status mirrored in `epic-52-frontend-ui-modernization-master-plan.md`, `epic-52-gap-report-admin-vs-dashboard.md`, `epic-53-admin-ui-canonical-compliance.md`, traceability matrix SG 4.4 / 5.x / 6.x rows.

<!-- docsmcp:start:user-story -->

> **As a** admin operator, **I want** clear state messaging and reliable keyboard navigation, **so that** I can recover from data/system issues without confusion

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that admin workflows fail gracefully and remain operable with keyboard and assistive technologies.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Standardize loading, empty, and error experiences across admin partials and enforce keyboard/focus/table semantics.

See [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/empty_state.html`
- `src/admin/templates/partials/workflows_list.html`
- `src/admin/templates/partials/repos_list.html`
- `src/admin/templates/partials/settings_content.html`
- `src/admin/templates/base.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Normalize empty state component usage for list/table pages (`src/admin/templates/components/empty_state.html`)
- [ ] Add explicit loading and error containers in key partials (`src/admin/templates/partials/workflows_list.html`)
- [ ] Ensure semantic table/header/list structure and focus-visible styles (`src/admin/templates/base.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 5.1] Async partials show explicit loading text with stable layout
- [ ] [SG 5.2] Empty states include plain-language guidance and next action
- [ ] [SG 5.3] Error/warning/success alerts use canonical containers
- [ ] [SG 6.3] Nav and controls are keyboard reachable with visible focus
- [ ] [SG 6.4] Semantic table/header/list markup supports assistive parsing
- [ ] [SG 11] Loading/empty/error + keyboard checklist items pass

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Keyboard-only traversal through workflows/repos/settings pages
2. Screen reader spot-check for table headings and alerts
3. HTMX refresh test verifies loading text and stale-state recovery

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Follow WCAG 2.2 AA baseline for non-text contrast and focus visibility

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 53.1
- Story 53.2

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
