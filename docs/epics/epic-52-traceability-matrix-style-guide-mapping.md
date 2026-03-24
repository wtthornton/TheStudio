# Epic 52: Traceability Matrix (Style Guide -> Epic/Story)

> Canonical source: `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`
> Coverage scope: `/admin/ui/*` and `/dashboard/*`
> **Last updated:** 2026-03-24 — Epic 57 closure: SG 8.x In Progress (Epic 55), SG 9.3x In Progress (Epic 56), SG 9.4 Verified, SG 11 In Progress (57.2).

---

## 1) Matrix

| Style Guide Requirement | Requirement Summary | Epic/Story Coverage | Primary Surfaces/Files | Status |
|---|---|---|---|---|
| SG 1.1, 1.2, 1.3 | Canonical precedence and cross-surface rules | 53.1, 54.1, 57.1, 57.2 | `src/admin/templates/base.html`, `frontend/src/App.tsx` | Partial (Wave 1: focus baseline in base) |
| SG 2.1-2.4 | Admin shell/layout/nav/typography density | 53.1 | `src/admin/templates/base.html`, page templates | Planned |
| SG 3.1 | Universal status semantics (success/warn/error/info/neutral) | 53.2, 54.1 | `components/status_badge.html`, `StageNode`/`STATUS_COLORS`, `GateInspector.tsx` | Verified (Wave 1: admin badges + dashboard stage status colors) |
| SG 3.2 | Trust-tier mapping (EXECUTE/SUGGEST/OBSERVE) | 53.2, 54.1 | `TrustConfiguration.tsx`, `TrustTierStep.tsx`, admin `tier_badge` | Verified (Wave 1) |
| SG 3.3 | Role mapping badges | 53.2, 54.1 | `role_badge` macro in `status_badge.html`; admin `base.html` shell | Verified (admin: macro + dark variant in nav; dashboard: no role chip yet) |
| SG 4.1 | Table pattern and readability | 53.3, 54.2, 54.4 | admin list partials, dashboard tabular components | Planned |
| SG 4.2 | Badge recipe consistency | 53.2, 54.1 | `status_badge.html`, status chips | Verified (Wave 1 core) |
| SG 4.3 | Button/link behavior semantics | 53.1, 53.3, 54.1 | admin templates, dashboard action bars | Partial (Wave 1: `empty_state` primary blue; EmptyState focus) |
| SG 4.4 | Loading/refresh conventions | 53.3, 54.2 | HTMX partials, dashboard data modules | Partial — **Wave 4–5:** self-loading shells on major admin pages + `repo_detail_content` merge-mode / promotion-history; global `htmx:responseError` Retry; dashboard polling unchanged |
| SG 5.1 | Explicit loading states | 53.3, 54.2 | admin partials + dashboard modules | Partial — admin: named loading + `role="status"` / `aria-live="polite"` on shell pages and settings cards; dashboard: IntentEditor + prior modules |
| SG 5.2 | Explicit empty states with guidance | 53.3, 54.2 | empty state components and list views | Partial — `empty_state` macro on repos/workflows/quarantine/dead-letters/audit; **Wave 6:** fleet dashboard repos table, experts list, planes list use macro + CTAs where applicable |
| SG 5.3 | Explicit error/alert semantics | 53.3, 54.2 | alert containers and fallback states | Partial — settings HTMX `responseError` + Retry; dashboard: TriageQueue, CreateTaskModal, IntentEditor `role="alert"`; steering/import dialogs (54.2 W3) |
| SG 6.1-6.5 | Accessibility baseline and non-color cues | 53.3, 54.2, 57.2 | admin controls, dashboard controls, modal/panel flows | Partial — **54.2 W3:** `ImportModal`, abort/redirect/retry dialogs, `StageDetailPanel`, `EditPanel` (`role="dialog"`, `aria-modal`, `aria-labelledby`, `type="button"`, focus-visible); prior: RefinementModal, IntentEditor, CreateTaskModal, admin `:focus-visible` |
| SG 7.1-7.10 | Modernization guardrails | 53.x, 54.x, 56.1, 57.2 | all touched surfaces | Planned |
| SG 8.1 | Prompt-first 5-step sequence | 53.4, 54.3, 55.1, 55.2 | admin AI partials, planning/steering flows | In Progress (Epic 55 covers prompt-first flows) |
| SG 8.2 | Prompt object contract | 54.3, 55.1 | `IntentEditor.tsx`, shared prompt model | In Progress (Epic 55 covers prompt object fields) |
| SG 8.3 | Agentic controls (preview, autonomy, rationale, audit/undo) | 55.1, 55.2, 55.4 | dashboard + admin AI action surfaces | In Progress (Epic 55 covers agentic control surfaces) |
| SG 8.4 | Trust signals (confidence/evidence/timestamp/ownership) | 53.4, 55.3 | `EvidenceExplorer.tsx`, admin workflow detail | In Progress (Epic 55 covers trust/evidence display) |
| SG 8.5 | High-impact action friction/confirmation | 54.3, 55.2, 56.2 | steering/reviewer/command actions | In Progress (Epic 55 covers confirmation gates) |
| SG 8.6 | AI labeling in context | 53.4, 55.3 | AI output surfaces across both UIs | In Progress (Epic 55 covers AI output labeling) |
| SG 9.1 | Preferred patterns (overview->detail, prompt iteration, feedback/revert) | 54.3, 55.4 | planning/steering/review flows | Planned |
| SG 9.2 | Anti-pattern prevention | 54.3, 55.2, 56.2, 57.2 | all AI and command action surfaces | Planned |
| SG 9.3A | Customizable dashboards | 56.1 | dashboard personalization modules | In Progress (Epic 56 covers dashboard customization) |
| SG 9.3B | Command palette | 56.2 | global app shell + command registry | In Progress (Epic 56 covers command palette) |
| SG 9.3C | Responsive desktop/tablet/mobile | 54.4 | timeline, backlog, triage, action controls | In Progress (Epic 56 covers responsive layouts) |
| SG 9.3D | Localization and cross-cultural readiness | 56.3 | formatting helpers + layouts in both surfaces | In Progress (Epic 56 covers localization readiness) |
| SG 9.3E | Optional collaboration layer | 56.4 | artifact-linked comments + audit trails | In Progress (Epic 56 covers collaboration layer) |
| SG 9.4 | Deferred patterns remain deferred | 56.x, 57.1, 57.3 | scope guard in all modernization work | Verified (guard rows exist in Deferred Pattern Guard section) |
| SG 11 | PR compliance checklist coverage | 57.2 + all stories | all epic/story done criteria | In Progress (covered by Story 57.2 regression checklist) |

---

## 2) Deferred Pattern Guard Rows

| Deferred Pattern | Guard Mechanism | Owner Story |
|---|---|---|
| AR/VR interfaces | Explicit non-goal in epics + wave scope review | 57.1, 57.3 |
| Radial-heavy operational defaults | Regression gate checks chart choices for operational readability | 57.2 |
| Unbounded no-code semantic drift | Customization constrained + reset-to-team-standard | 56.1, 57.1 |

---

## 3) Verification Cadence

Update this matrix at:

1. epic approval
2. story completion
3. pre-rollout wave gate
4. post-rollout verification

Status values allowed:

- Planned
- In Progress
- Verified
- Blocked

