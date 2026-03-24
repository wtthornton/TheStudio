# Story 53.1 -- Admin shell and navigation conformance across all /admin/ui pages

<!-- docsmcp:start:user-story -->

> **As a** admin operator, **I want** a consistent shell and navigation pattern, **so that** I can move between admin pages without relearning layout behavior

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that every admin page shares the same canonical shell, navigation hierarchy, and density pattern from the style guide.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Normalize base template and page wrappers to canonical admin shell and nav styles, including selected/unselected behavior and cross-link emphasis.

See [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/base.html`
- `src/admin/templates/dashboard.html`
- `src/admin/templates/repos.html`
- `src/admin/templates/workflows.html`
- `src/admin/templates/settings.html`
- `src/admin/templates/metrics.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Normalize app shell classes and header container (`src/admin/templates/base.html`)
- [ ] Align dashboard and page wrappers to canonical spacing and card rhythm (`src/admin/templates/dashboard.html`)
- [ ] Apply shell alignment across metrics/settings/repos/workflows pages (`src/admin/templates/metrics.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 2.1] Admin pages use dark-sidebar + light-content shell consistently
- [ ] [SG 2.2] Selected and unselected nav states match canonical classes and contrast
- [ ] [SG 2.4] Header/title/section density follows canonical typography and spacing
- [ ] [SG 11] PR checklist shell/card/navigation items are demonstrably satisfied
- [ ] [SG 1.1] Any pattern divergence updates style guide in same change

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Visual diff across dashboard/repos/workflows/settings pages
2. Keyboard tab traversal verifies nav reachability and visible focus
3. Playwright smoke for selected nav state persistence

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Do not introduce admin dark mode toggle; keep current production shell model

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Epic 53

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
