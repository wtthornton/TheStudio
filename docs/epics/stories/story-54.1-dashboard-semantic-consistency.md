# Story 54.1 -- Dashboard semantic consistency across status and trust indicators

> **Delivery status:** Completed (2026-03-24) — Wave 1  
> **Evidence:** `frontend/src/lib/constants.ts` (`STATUS_COLORS` → SG 3.1), `TrustConfiguration.tsx` + `TrustTierStep.tsx` trust-tier colors → SG 3.2 (observe gray / suggest blue / execute purple), `StageNode.tsx` status text in `aria-label`.  
> **SG 3.3 (role cues):** No dashboard user-role chip in-product yet; traceability matrix marks dashboard role UI as out of scope for this story. Admin role badges: see story 53.2 / `role_badge` in `base.html`.

<!-- docsmcp:start:user-story -->

> **As a** pipeline user, **I want** consistent status/trust semantics across dashboard views, **so that** I can make fast decisions without semantic drift between pages

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that dashboard users can interpret operational state consistently across modules.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Audit and normalize status chips/cards/alerts in dashboard components to canonical cross-surface semantics, including trust and role mappings.

See [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/PipelineStatus.tsx`
- `frontend/src/components/StageNode.tsx`
- `frontend/src/components/TrustConfiguration.tsx`
- `frontend/src/components/GateInspector.tsx`
- `frontend/src/components/analytics/SummaryCards.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Normalize pipeline and stage status indicators (`frontend/src/components/PipelineStatus.tsx`)
- [ ] Align trust/role visual mappings in trust configuration (`frontend/src/components/TrustConfiguration.tsx`)
- [ ] Normalize analytics and gate semantic colors/labels (`frontend/src/components/GateInspector.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 3.1] Canonical semantic status mapping used in all dashboard modules
- [ ] [SG 3.2] Trust-tier visual mapping is consistent with standard
- [ ] [SG 3.3] Role cues use canonical mapping where shown
- [ ] [SG 1.3] Cross-surface status semantics match admin meanings
- [ ] [SG 6.1] Status includes non-color labels/icons
- [ ] [SG 11] Semantic checklist items pass for dashboard pages

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 54](docs/epics/epic-54-dashboard-ui-canonical-compliance.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Component tests for status badge variants in core modules
2. Visual regression of stage/gate/trust components
3. Manual scan for color-only status communication

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Preserve dashboard dark-first shell while changing semantic tokens only

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Epic 54

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
