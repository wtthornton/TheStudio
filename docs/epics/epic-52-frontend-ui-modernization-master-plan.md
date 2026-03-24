# Epic 52: Frontend UI Modernization Master Plan

> **Status:** In execution (waves 1–2 complete, wave 3 complete, 2026-03-24)
> **Owner:** Product + Frontend
> **Scope:** `/admin/ui/*` and `/dashboard/*`
> **Canonical Standard:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
> **Depends On:** Existing epics and current frontend surfaces
> **Blocks:** Epics 53, 54, 55, 56, 57 rollout execution
> **Traceability:** `docs/epics/epic-52-traceability-matrix-style-guide-mapping.md` (living matrix)

### Execution log (last updated 2026-03-24)

| Story | Status | Notes |
|-------|--------|--------|
| 53.1 | **Completed** | Admin shell/nav conformance (SG 2.1–2.2 + 6) — commit `b9bde1c` |
| 53.2 | **Completed** | `status_badge.html` (SG 3.1–3.2), `role_badge` macro + dark variant; `base.html` nav uses `role_badge` (SG 3.3 admin); `writes_disabled` → yellow |
| 53.3 | **Completed** | Admin empty_state sweep + scope="col" SR/WCAG compliance — commit `394fb11`. HTMX shells, `aria-label`, loading `role="status"` / `aria-live`, `data-admin-htmx-section` + global `htmx:responseError` Retry. |
| 54.1 | **Completed** | `STATUS_COLORS`, trust-tier UI, `StageNode` `aria-label` (dashboard user-role chip still N/A for SG 3.3) |
| 54.2 | **Completed** | Modals/panels: `EmptyState`, `TriageQueue`, `CreateTaskModal`, `RefinementModal`, `IntentEditor`, `ImportModal`, `StageDetailPanel`, `EditPanel` — dialog semantics, focus traps, focus-visible, aria-labels. |
| 55.1–55.4 | **Completed** | AI prompt-first components: PromptObject, IntentPreview, ExecutionModeSelector, DecisionControls, TrustMetadata, AuditTimeline (39 tests) |
| 56.1–56.4 | **Completed** | 2026 capability modules: CommandPalette, DashboardCustomizer, locale helpers, CommentThread, ChangeHistory (35 tests) |
| 57.1 | **Completed** | Traceability matrix operational; all SG rows linked to implementing stories with evidence |
| 57.2 | **Completed** | Regression safety checklist (21 items, 6 categories) — `docs/governance/ui-regression-checklist.md` |
| 57.3 | **Completed** | Phased rollout plan with 3 waves, entry/exit criteria, rollback triggers — `docs/governance/rollout-plan.md` |

---

## 1) Purpose and Intent

This plan exists to modernize all frontend surfaces to the canonical UI/UX standard with prompt-first AI interaction as a hard requirement, not an optional enhancement. The objective is to produce implementation-ready epics/stories, sequence them safely, and avoid semantic drift between admin and dashboard surfaces.

---

## 2) Scope Split by Surface

### A. Admin Console (`/admin/ui/*`, HTMX + templates)

Primary files/surfaces:

- `src/admin/templates/base.html`
- `src/admin/templates/dashboard.html`
- `src/admin/templates/repos.html`
- `src/admin/templates/workflows.html`
- `src/admin/templates/metrics.html`
- `src/admin/templates/settings.html`
- `src/admin/templates/partials/*.html`
- `src/admin/templates/components/status_badge.html`
- `src/admin/templates/components/empty_state.html`

Modernization objectives:

- Enforce canonical shell/navigation/card/table/state semantics.
- Standardize status/trust/role mappings with non-color cues.
- Add explicit loading/empty/error behavior across partial refresh surfaces.
- Add prompt-first AI controls and trust metadata where AI-assisted flows exist.

### B. Pipeline App (`/dashboard/*`, React + Tailwind)

Primary files/surfaces:

- `frontend/src/App.tsx`
- `frontend/src/components/**/*`
- `frontend/src/stores/**/*`
- `frontend/src/hooks/**/*`
- `frontend/src/lib/**/*`

Modernization objectives:

- Preserve dark-first shell but align all cross-surface semantics.
- Enforce prompt-first flow in planning, steering, and reviewer interactions.
- Normalize state handling + keyboard/focus accessibility.
- Add 2026 modules: command palette, responsive support, localization readiness, optional collaboration, customizable views.

---

## 3) Mandatory Standards (Non-Negotiable)

All modernization stories must satisfy these constraints:

1. Prompt-first sequence for AI actions: intent capture -> intent preview -> mode choice -> evidence-backed output -> human decision point.
2. Trust/transparency cues for AI output: confidence, provenance/evidence, last-updated, ownership cue.
3. Human override always available: approve/edit/retry/reject and undo/revert where feasible.
4. Cross-surface semantic consistency: status colors + labels + meaning do not drift by page/surface.
5. Explicit loading/empty/error states and keyboard/focus baseline on all touched pages/components.

Deferred by policy and excluded from this plan:

- AR/VR interface patterns
- radial/gauge-heavy operational defaults
- unbounded no-code customization that breaks shared semantics

---

## 4) Epic Breakdown

1. `docs/epics/epic-53-admin-ui-canonical-compliance.md`
2. `docs/epics/epic-54-dashboard-ui-canonical-compliance.md`
3. `docs/epics/epic-55-cross-surface-ai-prompt-first-and-trust-layer.md`
4. `docs/epics/epic-56-cross-surface-2026-capability-modules.md`
5. `docs/epics/epic-57-rollout-governance-and-regression-safety.md`

Story files are under `docs/epics/stories/` for each epic.

---

## 5) Dependency Graph and Sequencing

### Critical path

1. Epic 53 + Epic 54 start in parallel
2. Epic 55 starts once foundational semantic/state convergence is underway
3. Epic 56 starts after Epic 55 foundation (`prompt object`, `decision controls`) is in place
4. Epic 57 runs continuously as governance layer, with final release gates at each wave

### Story-level dependency highlights

- `story-55.1` is a dependency for `story-54.3`.
- `story-55.2` and `story-55.3` gate `story-55.4`.
- `story-54.4` gates `story-56.2` and supports `story-56.3`.
- `story-57.1` gates `story-57.2` and `story-57.3`.

---

## 6) Rollout Strategy (Wave-Based)

### Wave 1: Quick Wins (Sprint 1)

- 53.1, 53.2, 54.1, 54.2, 57.1
- Goal: immediate semantic consistency and state/accessibility stability.
- Exit criteria: style-guide checklist coverage visibly improved on core pages.

### Wave 2: Medium Effort (Sprint 2)

- 53.3, 53.4, 54.3, 54.4, 55.1, 55.2, 57.2
- Goal: prompt-first behavior and reliable cross-device operational flows.
- Exit criteria: no high-impact AI action without preview, mode, decision gate.

### Wave 3: High-Impact Cross-Cutting (Sprint 3+)

- 55.3, 55.4, 56.1, 56.2, 56.3, 56.4, 57.3
- Goal: trust calibration, command velocity, localization readiness, collaboration context.
- Exit criteria: all mandatory style-guide sections mapped and closed in matrix.

---

## 7) Release Gates and Rollback Triggers

Each wave requires:

- traceability rows updated
- regression checklist pass
- explicit verification of prompt-first and trust controls (where AI exists)

Rollback triggers:

- semantic status regression across surfaces
- inaccessible keyboard/focus regressions on critical actions
- high-impact action path bypassing human confirmation/decision
- command palette executing side effects without confirmation

---

## 8) Prioritized Execution Order

### Quick wins

- Normalize shell/status/state semantics on highest-traffic pages.
- Close obvious accessibility gaps (focus visibility, keyboard reachability).
- Land traceability matrix early to control drift.

### Medium effort

- Retrofit prompt-first flow in planning/steering/admin AI actions.
- Add responsive density adaptation for core task/triage/approval workflows.
- Establish regression checklist and gate discipline.

### High-impact cross-cutting

- Shared trust metadata/audit/undo across surfaces.
- Command palette with guarded side-effect commands.
- Customizable dashboards + localization + collaboration layer.

---

## 9) Links

- Canonical style guide: `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
- Frontend expert brief: `docs/TAPPS_MCP_FRONTEND_EXPERTS_BRIEF.md`
- Pipeline vision: `docs/design/00-PIPELINE-UI-VISION.md`
- Traceability matrix: `docs/epics/epic-52-traceability-matrix-style-guide-mapping.md`
- Gap report: `docs/epics/epic-52-gap-report-admin-vs-dashboard.md`
