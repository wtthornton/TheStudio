# TAPPS-MCP Frontend Expert Update Brief (TheStudio)

## Purpose

This document is the handoff brief for TappsMCP to create/update project business experts and memory so frontend decisions consistently follow TheStudio's canonical UI/UX standard.

Use this as the authoritative input when running:

- `tapps_manage_experts(action="add"| "auto_generate" | "validate")`
- `tapps_memory(action="save"| "save_bulk")`
- `tapps_consult_expert(domain="<expert-domain>")` in frontend implementation/review flows

---

## Canonical Style Source of Truth

TheStudio frontend standard is:

- `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`

It is referenced from:

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/frontend-style-source-of-truth.mdc`

If any other style guidance conflicts, this style guide wins.

---

## Frontend Surfaces and Model

### Surface A: Admin Console

- Route family: `/admin/ui/*`
- Stack: server-rendered templates + HTMX partials
- Current shell: dark sidebar + light content area
- Current theme reality: no user dark mode toggle

### Surface B: Pipeline App

- Route family: `/dashboard/*`
- Stack: React SPA + Tailwind utilities
- Dark-first shell model

### Cross-surface invariants

- Status color semantics must match
- Explicit loading/empty/error states required
- Keyboard accessibility and visible focus required
- No color-only state communication

---

## 2026 AI-First UX Standards to Enforce

### Prompt-first flow (required)

Every AI-assisted UI flow must implement:

1. Intent capture
2. Intent preview
3. Execution mode choice (`draft` / `suggest` / `execute`)
4. Evidence-backed output
5. Human decision point (approve/edit/retry/reject)

### Prompt object contract

- `goal`
- `context`
- `constraints`
- `success_criteria`
- `mode`

### Agentic control set

- Intent preview
- Autonomy dial
- Rationale on demand
- Action audit + undo
- Escalation path

### Trust calibration signals

- Confidence indicator
- Provenance/evidence affordance
- Last-updated timestamp
- Ownership cue ("you are responsible for final action")

---

## 2026 Capability Modules Added

Business experts should enforce these modules:

1. Customizable dashboards (saved views, role-aware layout, reset-to-team-standard)
2. Unified search and command palette (`Ctrl/Cmd+K`)
3. Responsive behavior across desktop/tablet/mobile
4. Localization and cross-cultural readiness (formats, string expansion, neutral copy)
5. Collaboration layer (comments/mentions tied to artifacts; auditable by actor/time/change)

Deferred by default:

- AR/VR interface standards
- Gauge/radial-heavy operational dashboards
- Unbounded no-code UI editing that breaks shared semantics

---

## Recommended Business Experts (Project-Level)

These experts should exist in `.tapps-mcp/experts.yaml` and validate cleanly:

1. `expert-frontend-style-governance` (`user-experience`)
2. `expert-prompt-first-ux` (`user-experience`)
3. `expert-admin-ui-patterns` (`user-experience`)

Useful existing project-specific experts (already defined):

- `expert-intent-specification`
- `expert-agent-roles-routing`
- `expert-verification-qa`
- `expert-workflow-orchestration`
- `expert-epic-planning`
- `expert-publisher-github`

---

## Project Memory Entries to Save (High Priority)

Save these as `tier=architectural` or `tier=pattern` in `tapps_memory`:

1. Frontend style source of truth path and precedence rule.
2. Prompt-first AI flow contract (5-step sequence above).
3. Admin vs Pipeline surface distinction and constraints.
4. Capability modules (dashboard personalization, command palette, responsive, localization, collaboration).
5. Deferred patterns list (AR/VR, radial-heavy operations, unbounded no-code semantics drift).

---

## Suggested Execution Order for TappsMCP

1. Validate project experts config (`tapps_manage_experts(action="list")` then `validate`)
2. Add missing business experts (if not present)
3. Save architectural/pattern memory entries listed above
4. Run a sample consult for each relevant domain:
   - `user-experience`
   - `accessibility`
   - `api-design-integration` (for prompt object contracts)
5. Confirm experts + memory retrieval before production usage

---

## External Research References Used

- [NN/g: Dashboards and preattentive processing](https://www.nngroup.com/articles/dashboards-preattentive/)
- [Atlassian Design: Data visualization color](https://atlassian.design/foundations/color-new/data-visualization-color/)
- [Observable: Seven tips for better dashboards](https://observablehq.com/blog/seven-ways-design-better-dashboards)
- [Google Cloud: UX considerations for generative AI apps and agents](https://cloud.google.com/blog/products/ai-machine-learning/how-to-build-a-genai-application)
- [Microsoft Learn: UX guidance for generative AI applications](https://learn.microsoft.com/en-us/microsoft-cloud/dev/copilot/isv/ux-guidance)
- [IBM Carbon for AI: transparency and explainability guidance](https://carbondesignsystem.com/guidelines/carbon-for-ai)
- [The Frontend Company: UI trends in 2026 for SaaS (market scan)](https://www.thefrontendcompany.com/posts/ui-trends)

---

## Acceptance Criteria for "Done"

- `tapps_manage_experts(action="list")` succeeds with no schema errors.
- All required project experts appear and are queryable.
- Memory search for frontend style topics returns canonical entries.
- Frontend implementation/review flows can ask TAPPS experts and receive project-aligned guidance.
