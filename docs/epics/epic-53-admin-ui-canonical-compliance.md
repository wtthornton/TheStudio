# Epic 53: Admin Console Canonical UI Compliance

<!-- docsmcp:start:metadata -->
**Status:** In execution (stories 53.1–53.3 complete; 53.4 not started)
**Priority:** P0 - Critical
**Estimated LOE:** ~3-4 weeks
**Dependencies:** Epic 52

<!-- docsmcp:end:metadata -->

## Delivery status (rollup, 2026-03-24)

| Story | Status | Pointer |
|-------|--------|--------|
| 53.1 | **Complete** | Admin shell/nav conformance (SG 2.1–2.2 + 6) — commit `b9bde1c` |
| 53.2 | **Complete** | `stories/story-53.2-admin-semantic-status-badge-normalization.md` |
| 53.3 | **Complete** | Admin empty_state sweep + scope="col" SR/WCAG compliance — commit `394fb11`, `stories/story-53.3-admin-loading-empty-error-keyboard-baseline.md` |
| 53.4 | Not done | — |

Master plan: `epic-52-frontend-ui-modernization-master-plan.md`.

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that all /admin/ui/* experiences conform to the canonical style guide and prompt-first trust model where applicable, reducing operator confusion and ensuring predictable, testable behavior.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Bring every Admin Console template and partial into compliance with the canonical UI/UX standard, including semantic status mapping, explicit state handling, accessibility baselines, and AI transparency/human override patterns.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Admin templates currently vary in semantics and interaction quality, creating inconsistent operations and higher cognitive load.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] All admin pages align with style guide shell/card/table/button patterns
- [ ] All admin statuses use canonical semantic color mapping with non-color labels
- [ ] All admin pages have explicit loading/empty/error states
- [ ] Keyboard navigation and visible focus verified across admin controls
- [ ] AI-assisted admin flows enforce prompt-first sequence and override points
- [ ] No deferred patterns introduced by default

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 53.1 -- Admin Shell and Navigation Conformance

**Points:** 5

Normalize base shell/nav/header patterns across admin templates.

(5 acceptance criteria)

**Tasks:**
- [ ] Align base layout classes in base.html and page templates
- [ ] Standardize navigation states and link emphasis rules

**Definition of Done:** Admin Shell and Navigation Conformance is implemented, tests pass, and documentation is updated.

---

### 53.2 -- Admin Semantic States and Status Badges

**Points:** 5

Unify status/severity semantics and text cues.

(5 acceptance criteria)

**Tasks:**
- [ ] Refactor status badge component usage
- [ ] Map page-specific statuses to canonical tokens

**Definition of Done:** Admin Semantic States and Status Badges is implemented, tests pass, and documentation is updated.

---

### 53.3 -- Admin Loading Empty Error and Accessibility Baseline

**Points:** 8

Make all async/list/detail states explicit and keyboard/focus compliant.

(6 acceptance criteria)

**Tasks:**
- [ ] Add/normalize empty and error components
- [ ] Audit focus indicators and semantic table markup

**Definition of Done:** Admin Loading Empty Error and Accessibility Baseline is implemented, tests pass, and documentation is updated.

---

### 53.4 -- Admin AI Prompt-First and Trust Cues

**Points:** 8

Apply prompt-first flow and trust cues to AI-assisted admin surfaces.

(6 acceptance criteria)

**Tasks:**
- [ ] Add intent preview/mode decision UI
- [ ] Expose evidence/timestamps/ownership and override actions

**Definition of Done:** Admin AI Prompt-First and Trust Cues is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Keep admin light-content + dark-sidebar shell
- Do not introduce admin dark-mode toggle in this epic
- Preserve HTMX partial refresh behavior while improving state UX

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- AR/VR patterns
- Radial-heavy analytics defaults
- Unbounded no-code customization

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 6 acceptance criteria met | 0/6 | 6/6 | Checklist review |
| All 4 stories completed | 0/4 | 4/4 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 53.1: Admin Shell and Navigation Conformance
2. Story 53.2: Admin Semantic States and Status Badges
3. Story 53.3: Admin Loading Empty Error and Accessibility Baseline
4. Story 53.4: Admin AI Prompt-First and Trust Cues

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
