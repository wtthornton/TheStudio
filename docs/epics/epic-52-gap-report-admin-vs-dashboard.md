# Epic 52: Gap Report (Current vs Required)

> Baseline references:
> - `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
> - `docs/TAPPS_MCP_FRONTEND_EXPERTS_BRIEF.md`
> - `docs/design/00-PIPELINE-UI-VISION.md`

---

## 1) Summary

This report identifies major frontend compliance gaps by surface and maps them to modernization stories. Existing implementation already aligns with parts of the canonical standard, but significant work remains on prompt-first AI flow consistency, cross-surface semantics, and 2026 modules.

---

## 2) Admin Console Gaps (`/admin/ui/*`)

| Area | Current State | Required State | Gap Severity | Story Coverage |
|---|---|---|---|---|
| Shell/layout consistency | Core shell exists; variation across pages/partials | Uniform canonical shell/nav/card rhythm on all pages | Medium | 53.1 |
| Status semantics | Status badges exist but page-level variance remains | Canonical SG 3 mapping + non-color labels everywhere | High | 53.2 |
| Loading/empty/error | Partial coverage; uneven explicit handling | Explicit SG 5 states on all async/list/detail surfaces | High | 53.3 |
| Keyboard/focus baseline | Mixed compliance | Keyboard reachable controls + visible focus + semantic structures | High | 53.3 |
| Prompt-first AI flow | Present in places, not systematized | Full SG 8 prompt-first + trust cues + decision points | High | 53.4, 55.x |
| Trust metadata | Inconsistent display of confidence/evidence/ownership | Standard trust metadata block on AI outputs | Medium | 53.4, 55.3 |

---

## 3) Pipeline App Gaps (`/dashboard/*`)

| Area | Current State | Required State | Gap Severity | Story Coverage |
|---|---|---|---|---|
| Semantic consistency | Strong but not fully normalized across modules | Universal SG semantic mapping with no drift | High | 54.1 |
| State handling | Many modules good; gaps remain by component | Explicit SG 5 states across all key modules | High | 54.2 |
| Accessibility baseline | Partial coverage and test depth variance | SG 6 keyboard/focus/non-color baseline end-to-end | High | 54.2, 57.2 |
| Prompt-first planning/steering | Intent tooling exists; step sequence not always enforced | Mandatory SG 8 sequence + decision checkpoints | High | 54.3, 55.1, 55.2 |
| Responsive support | Desktop-first strong; mobile/tablet uneven | Critical flows usable across desktop/tablet/mobile | Medium | 54.4 |
| Command palette | No complete global implementation | `Ctrl/Cmd+K` across surfaces with guarded actions | High | 56.2 |
| Localization readiness | Limited locale handling and expansion tolerance | Locale-aware formatting + resilient layout | Medium | 56.3 |
| Collaboration layer | Minimal artifact-linked collaboration in UI | Optional auditable comments/mentions per artifact | Medium | 56.4 |

---

## 4) Cross-Surface Gaps

| Cross-Cutting Requirement | Gap | Severity | Coverage |
|---|---|---|---|
| Prompt object contract (`goal/context/constraints/success_criteria/mode`) | No single reusable contract across both surfaces | High | 55.1 |
| Human override and audit/undo | Inconsistent action governance by module | High | 55.2, 55.4 |
| Trust calibration cues | Uneven confidence/provenance/ownership/timestamp display | High | 55.3 |
| Traceability and compliance operations | No single requirement-to-story matrix in active operations | Medium | 57.1 |
| Regression gate discipline | No single cross-surface checklist enforced per wave | Medium | 57.2 |

---

## 5) Prioritized Execution Order

### Quick wins (highest immediate value)

1. 53.2 Admin semantic status normalization
2. 54.1 Dashboard semantic consistency pass
3. 53.3 + 54.2 explicit state/accessibility hardening
4. 57.1 traceability matrix operations

### Medium effort

1. 53.4 admin prompt-first trust cues
2. 54.3 dashboard prompt-first retrofit
3. 54.4 responsive baseline alignment
4. 55.1 + 55.2 shared prompt object + mode/decision controls

### High-impact cross-cutting

1. 55.3 evidence transparency metadata
2. 55.4 audit/undo affordances
3. 56.2 command palette
4. 56.1 customizable dashboards with reset guard
5. 56.3 localization readiness
6. 56.4 optional collaboration layer

---

## 6) Rollout Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Semantic regressions while modernizing multiple pages/components | Wave-gated rollout + regression checklist + traceability updates |
| Prompt-first inconsistencies between admin and dashboard | Shared contract stories (55.1/55.2) before broad feature expansion |
| Accessibility regressions from UI refactors | Keyboard/focus/non-color checks in each wave gate |
| Scope creep into deferred patterns | Explicit non-goals in epic/story definitions and wave review |

---

## 7) Done Criteria for Gap Closure

A gap row is considered closed only when:

1. corresponding story is complete
2. traceability matrix row status is `Verified`
3. wave regression checklist passes
4. no deferred-pattern violation is introduced

