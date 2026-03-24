# Epic 55: Cross-Surface AI Prompt-First and Trust Layer

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P0 - Critical
**Estimated LOE:** ~3 weeks
**Dependencies:** Epic 52, Epic 53, Epic 54

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that AI interactions across both frontend surfaces are governed by one prompt-first contract with transparent, auditable, human-controlled execution.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Implement a shared UX contract for AI interactions including intent capture, intent preview, mode controls, evidence display, and explicit human decision points.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Without a shared contract, AI interactions diverge and erode trust, safety, and operational consistency.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] All AI-assisted flows implement 5-step prompt-first sequence
- [ ] Prompt object fields goal/context/constraints/success_criteria/mode are represented in UI and payloads
- [ ] Autonomy dial and intent preview visible before impactful execution
- [ ] Evidence provenance confidence timestamp ownership cues shown for AI outputs
- [ ] Approve/edit/retry/reject and undo/audit actions are always available where feasible

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 55.1 -- Prompt Object and Intent Preview Foundation

**Points:** 8

Create shared frontend contract/components for prompt object capture and preview.

(6 acceptance criteria)

**Tasks:**
- [ ] Define typed prompt object interface
- [ ] Build reusable intent preview component for both surfaces

**Definition of Done:** Prompt Object and Intent Preview Foundation is implemented, tests pass, and documentation is updated.

---

### 55.2 -- Execution Mode and Human Decision Controls

**Points:** 8

Implement consistent mode controls and decision checkpoints.

(6 acceptance criteria)

**Tasks:**
- [ ] Add draft/suggest/execute mode controls with permission checks
- [ ] Standardize approve/edit/retry/reject actions

**Definition of Done:** Execution Mode and Human Decision Controls is implemented, tests pass, and documentation is updated.

---

### 55.3 -- Evidence Transparency and Trust Calibration UI

**Points:** 5

Expose provenance/confidence/timestamp/ownership cues in AI results.

(5 acceptance criteria)

**Tasks:**
- [ ] Add compact trust metadata block
- [ ] Support rationale-on-demand disclosure

**Definition of Done:** Evidence Transparency and Trust Calibration UI is implemented, tests pass, and documentation is updated.

---

### 55.4 -- Audit Trail and Undo Affordances

**Points:** 5

Make AI actions auditable and reversible when technically feasible.

(5 acceptance criteria)

**Tasks:**
- [ ] Render per-action audit timeline entries
- [ ] Add undo/revert affordances for mutable outputs

**Definition of Done:** Audit Trail and Undo Affordances is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Leverage trust-store and existing evidence explorer patterns
- Avoid anthropomorphic copy
- Keep labels subtle and consistent

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Replacing non-AI manual flows with AI-only controls
- Fully autonomous hidden actions

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 5 acceptance criteria met | 0/5 | 5/5 | Checklist review |
| All 4 stories completed | 0/4 | 4/4 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 55.1: Prompt Object and Intent Preview Foundation
2. Story 55.2: Execution Mode and Human Decision Controls
3. Story 55.3: Evidence Transparency and Trust Calibration UI
4. Story 55.4: Audit Trail and Undo Affordances

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| No risks identified | - | - | Consider adding risks during planning |

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| Files will be determined during story refinement | - | - |

<!-- docsmcp:end:files-affected -->
