# Story 55.3 -- Evidence transparency and trust calibration metadata

<!-- docsmcp:start:user-story -->

> **As a** reviewer, **I want** transparent trust metadata for AI outputs, **so that** I can verify and challenge AI output before final action

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that users can calibrate trust in AI output through visible confidence, evidence, recency, and ownership cues.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add compact trust metadata blocks and rationale-on-demand affordances across AI output surfaces.

See [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `frontend/src/components/pr/EvidenceExplorer.tsx`
- `frontend/src/components/planning/RoutingPreview.tsx`
- `frontend/src/components/SteeringActivityLog.tsx`
- `src/admin/templates/partials/workflow_detail_content.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add trust metadata to evidence explorer outputs (`frontend/src/components/pr/EvidenceExplorer.tsx`)
- [ ] Expose confidence/provenance labels in planning results (`frontend/src/components/planning/RoutingPreview.tsx`)
- [ ] Expose metadata in admin workflow detail outputs (`src/admin/templates/partials/workflow_detail_content.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] [SG 8.4] Confidence indicator is present for AI outputs
- [ ] [SG 8.4] Provenance/evidence link or summary is present
- [ ] [SG 8.4] Last-updated timestamp and ownership cue are present
- [ ] [SG 8.6] AI-generated/transformed content is visibly labeled
- [ ] [SG 9.2] No magic output without correction path

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 55](docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. UI tests asserting trust metadata render in AI output components
2. Manual validation that ownership cue appears near confirm actions
3. Regression tests for evidence links and timestamp formatting

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Keep metadata compact with disclosure pattern for detailed rationale

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 55.1
- Story 55.2

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
