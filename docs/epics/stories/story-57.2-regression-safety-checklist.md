# Story 57.2 -- Regression Safety Checklist and Test Gates

> **Delivery status:** Complete (2026-03-24) — Reusable regression checklist created at `docs/governance/ui-regression-checklist.md`. All categories defined, pass/fail criteria documented, linked to Epic 57.3 wave gates.
> **Doc sync:** `epic-57-rollout-governance-and-regression-safety.md`, `docs/governance/ui-regression-checklist.md`

<!-- docsmcp:start:user-story -->

> **As a** delivery lead, **I want** a reusable regression safety checklist for UI modernization waves, **so that** no wave ships without verified accessibility, semantic consistency, prompt-first compliance, and state handling

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story defines the regression checklist that gates every UI modernization wave. It ensures that accessibility, semantic consistency, prompt-first compliance, state handling, responsive/i18n readiness, and deferred-pattern guards are verified before shipping.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Create a reusable regression checklist document (`docs/governance/ui-regression-checklist.md`) covering six categories of pass/fail criteria. This checklist is required by Story 57.3 wave gates.

See [Epic 57](docs/epics/epic-57-rollout-governance-and-regression-safety.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/governance/ui-regression-checklist.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [x] Define accessibility regression items (SG 6.1-6.5)
- [x] Define semantic consistency items (SG 3.1-3.3)
- [x] Define prompt-first compliance items (SG 8.1, 8.2, 8.4, 8.6)
- [x] Define state handling items (SG 5.1-5.3)
- [x] Define responsive and i18n items (SG 9.3C, 9.3D)
- [x] Define deferred pattern guard items (SG 9.4)
- [x] Link checklist to 57.3 wave gates

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [x] Checklist covers accessibility (focus-visible, keyboard nav, aria-labels, non-color cues, screen reader semantics)
- [x] Checklist covers semantic consistency (status colors SG 3.1, trust tiers SG 3.2, role badges SG 3.3, cross-surface alignment)
- [x] Checklist covers prompt-first compliance (5-step sequence SG 8.1, prompt fields SG 8.2, evidence/trust SG 8.4, AI labels SG 8.6)
- [x] Checklist covers state handling (loading, empty, error states)
- [x] Checklist covers responsive/i18n and deferred pattern guards

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 57](docs/epics/epic-57-rollout-governance-and-regression-safety.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Checklist document exists and is well-formed markdown
2. All six categories have clear pass/fail items
3. Each item references relevant style guide section
4. Checklist is referenced by Story 57.3 wave gates

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Checklist is a living artifact; update when style guide evolves
- Each wave gate in 57.3 references this checklist as a required gate

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Epic 57
- Story 57.1 (traceability matrix provides requirement inventory)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
