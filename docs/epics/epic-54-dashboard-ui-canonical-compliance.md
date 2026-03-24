# Epic 54: Pipeline App Canonical UI Compliance

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P0 - Critical
**Estimated LOE:** ~4-5 weeks
**Dependencies:** Epic 52, Epic 53

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that all /dashboard/* workflows become semantically consistent, prompt-first where AI is involved, and operationally reliable across devices.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Bring React dashboard views into strict conformance with canonical cross-surface semantics while preserving the dark-first dashboard shell.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Pipeline app components have strong coverage but uneven adherence to standardized state semantics, accessibility details, and prompt-first interaction flow.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Dashboard pages preserve dark-first shell but adopt canonical semantic meanings
- [ ] Prompt-first sequence enforced in AI-assisted planning and control flows
- [ ] Loading/empty/error states explicit across all primary dashboard modules
- [ ] Keyboard/focus and non-color status cues pass accessibility checks
- [ ] No command/action bypasses human decision points for high-impact operations

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 54.1 -- Dashboard Semantic Consistency Pass

**Points:** 8

Normalize status colors/labels/tokens and action affordances across dashboard modules.

(6 acceptance criteria)

**Tasks:**
- [ ] Audit and normalize status chips/cards across components
- [ ] Align trust-tier and role mappings

**Definition of Done:** Dashboard Semantic Consistency Pass is implemented, tests pass, and documentation is updated.

---

### 54.2 -- Dashboard State and Accessibility Hardening

**Points:** 8

Enforce explicit loading/empty/error and keyboard focus standards.

(6 acceptance criteria)

**Tasks:**
- [ ] Add missing empty/error states
- [ ] Fix focus traversal and visibility in dialogs/panels

**Definition of Done:** Dashboard State and Accessibility Hardening is implemented, tests pass, and documentation is updated.

---

### 54.3 -- Prompt-First Planning and Control Flows

**Points:** 8

Retrofit planning and steering interactions to 5-step prompt-first flow.

(7 acceptance criteria)

**Tasks:**
- [ ] Introduce intent preview and mode selection in planning flows
- [ ] Add decision checkpoints and retry/edit/reject paths

**Definition of Done:** Prompt-First Planning and Control Flows is implemented, tests pass, and documentation is updated.

---

### 54.4 -- Dashboard Responsive Baseline Alignment

**Points:** 5

Guarantee primary workflows function at desktop/tablet/mobile breakpoints.

(5 acceptance criteria)

**Tasks:**
- [ ] Implement table-to-card fallback patterns
- [ ] Validate critical approve/triage actions on small screens

**Definition of Done:** Dashboard Responsive Baseline Alignment is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Keep dashboard shell visually distinct from admin
- Use shared semantics not shared shell
- Preserve existing Zustand store architecture

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- AR/VR patterns
- Gauge/radial-heavy operational defaults
- Unbounded no-code UX editors

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

1. Story 54.1: Dashboard Semantic Consistency Pass
2. Story 54.2: Dashboard State and Accessibility Hardening
3. Story 54.3: Prompt-First Planning and Control Flows
4. Story 54.4: Dashboard Responsive Baseline Alignment

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
