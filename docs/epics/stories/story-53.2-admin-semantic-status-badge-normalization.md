# Story 53.2 -- Admin semantic status and badge normalization

> **Delivery status:** Completed (2026-03-24) — Wave 1; admin nav wiring 2026-03-24  
> **Evidence:** `src/admin/templates/components/status_badge.html` — `role="status"`, tier `aria-label`, repo `writes_disabled` → warning yellow (SG 3.1), `role_badge(role, variant='light'|'dark')` (SG 3.3). `src/admin/templates/base.html` — current user role rendered via `role_badge(..., variant='dark')` in the sidebar footer.

<!-- docsmcp:start:user-story -->

> **As a** admin operator, **I want** uniform status colors and labels, **so that** I can interpret health and risk instantly without page-specific legend knowledge

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that status/severity meaning is consistent and unambiguous across all admin pages.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Map all status outputs in admin templates to canonical semantic mapping and non-color cues, including trust-tier and role badge rules.

See [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/status_badge.html`
- `src/admin/templates/partials/dashboard_content.html`
- `src/admin/templates/partials/metrics_content.html`
- `src/admin/templates/partials/compliance_content.html`
- `src/admin/templates/partials/portfolio_health_content.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Normalize shared status badge component variants (`src/admin/templates/components/status_badge.html`)
- [ ] Update dashboard partials to canonical semantic mappings (`src/admin/templates/partials/dashboard_content.html`)
- [ ] Update metrics/compliance/portfolio health status displays (`src/admin/templates/partials/metrics_content.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 3.1] Success/warning/error/in-progress/neutral colors follow canonical mapping
- [ ] [SG 3.2] Trust tier mapping EXECUTE/SUGGEST/OBSERVE matches canonical colors
- [ ] [SG 3.3] Role badge mapping ADMIN/OPERATOR/fallback follows canonical rules
- [ ] [SG 6.1] Status always includes text label and does not rely on color alone
- [ ] [SG 11] Semantic color checklist item passes for updated pages

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 53](docs/epics/epic-53-admin-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Template snapshot tests for status badge variants
2. Manual accessibility check for non-color cues and readable labels
3. Regression test of trust-tier and role chips in admin pages

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Prefer single source component over page-local badge logic

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 53.1

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
