# TheStudio UI/UX Style Guide

**Status:** Active Standard  
**Primary Scope:** `http://localhost:9080/admin/ui/dashboard` and all `/admin/ui/*` pages (HTMX Admin Console)  
**Secondary Scope:** `/dashboard/` React pipeline app (separate visual system)  
**Last Verified Against Live UI:** 2026-03-24  
**Owners:** Product + Frontend

---

## 1) Purpose

This is the formal style guide for TheStudio admin experience. It has two goals:

1. Capture **exactly what is live now** on `/admin/ui/dashboard` and related admin pages.
2. Define **modern quality guardrails** so new UI remains current without breaking existing consistency.

This document is the **single source of truth** for frontend style and interaction standards in this repository.

---

## 1.1 Source-of-Truth Contract

1. If any other doc conflicts with this guide, this guide wins.
2. New frontend work must reference this guide before introducing patterns.
3. Changes to visual/interaction patterns must update this guide in the same PR.
4. This guide is standalone and applies to all frontend surfaces, with per-surface variants below.

---

## 1.2 Site-Wide Applicability Matrix

### Surface A: Admin Console (`/admin/ui/*`)

- Stack: server-rendered templates + HTMX partial refresh.
- Theme model: light content area + dark sidebar (current production standard).
- This is the primary verified implementation in this guide.

### Surface B: Pipeline App (`/dashboard/*`)

- Stack: React SPA + Tailwind utility classes.
- Theme model: dark-first operational canvas.
- Must still obey global semantics in this guide (status colors, state handling, accessibility), while keeping its own shell pattern.

### Cross-Surface Rules (mandatory)

- Status color meaning is universal across all UIs.
- Loading/empty/error states are always explicit.
- Keyboard navigation and visible focus are always required.
- No page may rely on color alone to convey state.

---

## 1.3 Theme Support Policy

- **Current production reality:** no user-facing dark mode toggle exists in Admin Console.
- Therefore, dark mode is **not** a required acceptance criterion for `/admin/ui/*` today.
- Future dark mode work must be introduced as a dedicated enhancement with explicit token definitions, contrast checks, and migration plan.

## 2) Verified Current UI (Admin Console)

The live `/admin/ui/dashboard` UI is **not** the dark React pipeline SPA.  
It is a Tailwind + HTMX, light-content-layout admin console with a dark sidebar.

### 2.1 Shell and Layout

- App shell: `flex min-h-screen`
- Global page canvas: `bg-gray-50 text-gray-900`
- Sidebar: fixed-width dark rail (`w-56 bg-gray-900 text-gray-100`)
- Main area: light content canvas with white header and white cards
- Header bar: `bg-white border-b border-gray-200 px-6 py-4`
- Main content padding: `p-6`

### 2.2 Navigation Pattern

- Sidebar is icon+label vertical nav with text symbols (for example: `■`, `▶`, `⚙`).
- Selected item style: `bg-gray-800 text-white`.
- Unselected item style: `text-gray-300` with `hover:bg-gray-800`.
- Cross-app link to React pipeline dashboard is visually emphasized in indigo (`bg-indigo-800`).

### 2.3 Surface and Card Pattern

Primary card recipe used across dashboard and metrics:

- `bg-white rounded-lg border border-gray-200`
- Standard card spacing: `p-4` or `p-6`
- Section spacing: `mb-6`

### 2.4 Typography and Density

- Page title: `text-xl font-semibold`
- Section title: `text-sm font-semibold text-gray-500 uppercase tracking-wide`
- KPI number: `text-2xl` to `text-3xl` with bold weight
- Metadata and helper text: `text-xs text-gray-400|500`
- Operational target density: compact but readable, with `gap-4` grids

---

## 3) Semantic Color Standard (Current Production)

### 3.1 Status and Severity

- **Success / OK / Healthy:** green (`bg-green-100 text-green-800`, KPI `text-green-600`)
- **Warning / Degraded / Stuck:** yellow (`bg-yellow-100 text-yellow-800`, KPI `text-yellow-600`)
- **Error / Failed / Unhealthy:** red (`bg-red-100 text-red-800`, KPI `text-red-600`)
- **In progress / Running / Info:** blue (`bg-blue-100 text-blue-800`, links `text-blue-600`)
- **Neutral / Unknown:** gray (`bg-gray-100 text-gray-700`)

### 3.2 Trust Tier Mapping

- `EXECUTE`: purple
- `SUGGEST`: blue
- `OBSERVE`: gray

### 3.3 Role Mapping

- `ADMIN`: red tint badge
- `OPERATOR`: yellow tint badge
- fallback/other role: blue tint badge

Color meaning must be consistent across dashboard, workflows, repos, and metrics pages.

---

## 4) Component Recipes

### 4.1 Tables

- Outer container: white card + `overflow-hidden`
- Header row: `bg-gray-50`, uppercase `text-xs text-gray-500`
- Body rows: `divide-y divide-gray-100`
- Row hover: `hover:bg-gray-50`
- Numeric columns right-aligned for scan speed

### 4.2 Badges

- Use compact pills: `inline-block px-2 py-0.5 rounded text-xs font-semibold`
- Badge text should be short and uppercase where operationally useful (`OK`, `PASSING`, `FAILING`)

### 4.3 Buttons and Links

- Primary button: blue fill (`bg-blue-600 text-white hover:bg-blue-700`)
- Secondary action button: gray fill (`bg-gray-600 text-white hover:bg-gray-700`)
- Destructive action: red text or red button style
- Data/resource links: blue text link with underline on hover

### 4.4 Loading and Refresh

- HTMX periodic refresh for dashboard summary (`load, every 5s`).
- Loading placeholders are text-based (`Loading dashboard...`) with optional `htmx-indicator`.
- Header status area shows recency (`Updated <time>`).

---

## 5) State Design Rules

### 5.1 Loading

- Always show explicit loading text for async partials.
- Keep layout stable while loading to reduce visual jumps.

### 5.2 Empty

- Empty table/list rows must provide plain-language guidance (`No repos registered`, `No data available`).
- Empty copy should state what is missing and, where possible, next action.

### 5.3 Error and Alert

- Error alerts use red-tint container (`bg-red-50 border-red-200 text-red-800`).
- Warning alerts use yellow-tint container.
- Success/info confirmations use green-tint container.

---

## 6) Accessibility and Interaction Baseline

The admin console must follow these non-negotiables:

1. Do not rely on color alone for meaning; keep labels (`OK`, `FAILED`, `STUCK`, etc.).
2. Preserve text contrast against white and dark surfaces.
3. Keep nav and controls keyboard reachable.
4. Use semantic HTML table/header/list structure for assistive parsing.
5. Keep labels concise and concrete for operational decisions.

---

## 7) Modernization Guardrails (2025-2026 Standards)

The following standards are required for new UI work and progressive upgrades:

1. **Overview first, details on demand:** top section must expose key KPIs immediately.
2. **Use quantitative encodings that read fast:** prefer bars/lines/position over pie/gauge-heavy views for operational decisions.
3. **Limit chart color cardinality:** generally 5-6 distinguishable categories max before grouping.
4. **Consistent color semantics across views:** the same color should mean the same state everywhere.
5. **Do not place text directly on low-contrast chart fills.**
6. **Add non-color cues in visualizations:** labels, icons, separators, or shape/position differences.
7. **Support high-density workflows without clutter:** prioritize the 3-4 most critical metrics.
8. **AI transparency by default:** clearly mark AI-generated or AI-recommended output.
9. **Human override always available:** users must be able to edit, reject, or revert AI output.
10. **Trust calibration cues:** pair confidence + evidence + outcome history to prevent overtrust.

### Planned but Not Yet Standardized

- Optional user dark mode toggle for Admin Console.
- Reduced motion preference support.
- Tokenized theming across both surfaces.
- Production asset pipeline for Tailwind (replace CDN usage).

---

## 8) AI-First 2026 Design Layer (Prompt-First)

This section defines the required AI-first interaction model for all new frontend AI features.

### 8.1 Prompt-First Design Intent (Required)

Every AI-assisted flow must begin with explicit user intent capture before execution.

Use this interaction sequence:

1. **Intent capture:** user prompt/instruction (freeform or guided fields).
2. **Intent preview:** system restates what it will do (scope, constraints, assumptions).
3. **Execution mode choice:** user confirms mode (`draft`, `suggest`, or `execute` when allowed).
4. **Evidence-backed output:** results include source/citation/evidence affordances where applicable.
5. **Human decision point:** approve, edit, retry, or reject.

If an experience skips steps 2-5, it is not compliant with this guide.

### 8.2 Prompt Object Standard

For consistency, prompt-driven actions should preserve these fields in UI and payload design:

- `goal`: what outcome user wants
- `context`: relevant repo/task/environment context
- `constraints`: non-goals, policy bounds, budget/time constraints
- `success_criteria`: how user defines acceptable result
- `mode`: draft/suggest/execute

UI should expose these directly or infer them with editable defaults.

### 8.3 Agentic UX Controls (Required for AI Actions)

- **Intent Preview:** show planned action and impacted surface.
- **Autonomy Dial:** explicit mode indicator and switch when permissions allow.
- **Rationale on demand:** concise why/how summary; full detail behind disclosure.
- **Action Audit + Undo:** show what changed and enable reversal when technically feasible.
- **Escalation path:** easy handoff to human/manual flow when confidence is low.

### 8.4 Trust and Safety Signals

For AI outputs and recommendations, provide:

- confidence indicator (qualitative is acceptable)
- provenance/evidence link or source summary
- last-updated timestamp
- ownership cue ("You are responsible for final action")

Never present AI output as guaranteed fact without verification affordances.

### 8.5 Appropriate Friction Points

For high-impact actions (publish, delete, execute, compliance-affecting changes):

- add explicit confirmation
- show concise risk summary
- require final user acknowledgment before irreversible operations

### 8.6 AI Labeling Rule

Any AI-generated or AI-transformed content should be visibly marked in-context.
Labeling should be subtle, consistent, and non-decorative.

---

## 9) 2026 Front-Runner Patterns and Anti-Patterns

### 9.1 Patterns to Prefer

1. **Overview -> filter -> detail-on-demand** navigation hierarchy.
2. **Big-number operational KPIs** paired with drill-down evidence.
3. **Consistent semantics across coordinated views** (same color means same state).
4. **Prompt iteration loops** (`revise`, `regenerate`, `compare variants`).
5. **Inline feedback capture** attached to specific AI outputs.
6. **Revert-to-previous result** to reduce fear of exploration.

### 9.2 Anti-Patterns to Avoid

1. Hidden autonomous actions without user preview.
2. Anthropomorphic copy that overstates AI understanding ("I know", "I feel").
3. Color-only status communication.
4. Chart choices that slow quantitative reading for operational use (heavy gauge/pie reliance).
5. "Magic output" without source, rationale, or correction path.
6. Replacing existing workflow controls with opaque AI-only controls.

### 9.3 Capability Modules to Add (2026-forward)

These modules are approved additions to keep TheStudio at the front of 2026 UX while preserving operational clarity.

#### A) Customizable Dashboards (role-aware personalization)

- Support per-user saved views (for example: "Ops Default", "Cost Review", "Exec Snapshot").
- Allow controlled widget ordering and show/hide, with safe defaults.
- Keep a one-click **Reset to Team Standard** option to avoid drift.
- Preserve global semantic rules (status colors, KPI naming, state patterns) even when layout is customized.

#### B) Unified Search and Command Palette

- Provide a global command entry point (`Ctrl+K` / `Cmd+K`) across frontend surfaces.
- Must support:
  - navigate to pages/entities
  - run common actions
  - recent items/history recall
- Commands with side effects must show a confirmation/risk summary before execution.

#### C) Responsive Cross-Platform Experience

- Desktop-first remains primary, but all new pages must support tablet and mobile layouts.
- Use progressive reduction of density: table -> compact table -> card/list where needed.
- Keep touch targets and spacing practical on small screens.
- Critical workflows (status checks, approvals, triage actions) must remain functional on mobile.

#### D) Cross-Cultural and Localization Readiness

- Support locale-aware date/time/number/currency formatting.
- Avoid hard-coded text widths; allow string expansion for translation.
- Keep iconography and copy culturally neutral in global contexts.
- Ensure forms, tables, and prompts remain understandable when localized.

#### E) Collaboration Layer (optional by surface)

- Where multi-user workflows exist, support inline comments/mentions and handoff context.
- Keep collaboration objects tied to an artifact (task, workflow, evidence item).
- Preserve auditability: who commented, when, and what decision changed.

### 9.4 Patterns Explicitly Deferred

The following are not default standards at this time:

- AR/VR interface patterns (exploratory only).
- Heavy radial/gauge-first analytics in operational views.
- Unbounded no-code UI editing that breaks shared operational semantics.

---

## 10) Guidance and Onboarding UX Standards

This section is mandatory for all in-product guidance patterns:

- setup wizards
- inline help and tooltips
- help panels
- product tours
- feature spotlights ("what changed")

### 10.1 Pattern Selection Rules

Use the right guidance mechanism for the right job:

1. **Setup Wizard:** first-run or major reconfiguration flow with required validation.
2. **Help Panel:** on-demand conceptual and task guidance.
3. **Inline Tooltip:** short definition or clarification only (single concept, one to two lines).
4. **Product Tour:** guided walkthrough of a workflow or screen area.
5. **Feature Spotlight:** version-specific announcement of new/changed UI.

Do not use tooltips as mini-doc pages. Do not use tours for release notes.

### 10.2 Interaction and Layering Rules

- Only one primary guidance layer may be active at a time (wizard, tour, or spotlight).
- Guidance must always provide a clear dismiss path and replay path.
- Guidance overlays must never block critical emergency controls.
- If target elements are absent (empty state, permissions), guidance must skip gracefully.

### 10.3 UX Budget and Fatigue Controls

- Tours should be concise (generally 5-7 steps).
- Spotlights should be concise (generally 1-3 highlights per version).
- Auto-launch guidance should be limited to first-run or meaningful version change.
- Repeated interruption patterns are prohibited.

### 10.4 Persistence and Lifecycle Conventions

- Persist completion/dismissal state per guidance type and scope.
- Use explicit key naming by feature and version.
- Support replay from a stable entry point (Help menu/settings).
- Reset behavior must be explicit (for example: version bump, manual reset, role change).

### 10.5 Accessibility Requirements for Guidance

- Full keyboard navigation support for all guidance types.
- `Escape` closes current guidance layer when safe.
- Focus management:
  - trap focus for modal/tour contexts
  - return focus to invoking element on close
- Screen-reader-friendly labels and progress context for multi-step guidance.

### 10.6 Content Governance for Help and Tours

- Guidance content must use operational, concise language.
- Help/tour copy must be versioned with the product.
- Changes to guidance behavior/copy must be updated in this style guide when pattern-level behavior changes.
- Ownership for updates should be explicit in epic/story acceptance criteria.

### 10.7 Measurement Standards

Guidance epics should include outcome metrics, not only coverage counts:

- time-to-first-value
- wizard step completion/drop-off
- replay/help usage
- support ticket deflection where measurable

Coverage metrics (count of tooltips, count of tours) are useful but secondary.

---

## 11) Implementation Notes

- Existing admin pages currently load Tailwind via CDN and HTMX from CDN.
- For long-term modernization, prefer local build pipeline for CSS assets in production environments.
- Keep Admin Console and React Pipeline Dashboard style systems intentionally distinct unless an explicit unification project is approved.

---

## 12) PR Compliance Checklist

- [ ] Uses Admin Console shell correctly (dark sidebar + light content canvas).
- [ ] Reuses standard white card + gray border surfaces.
- [ ] Uses status colors according to semantic mapping.
- [ ] Preserves loading, empty, and error states.
- [ ] Keeps tables readable (header hierarchy, numeric alignment, row hover).
- [ ] Maintains keyboard-accessible navigation and controls.
- [ ] Keeps copy concise and action-oriented.
- [ ] Updates this style guide when introducing a new reusable pattern.
- [ ] For AI features, uses prompt-first intent flow with preview + user decision point.
- [ ] For AI outputs, includes transparency marker and correction/override path.
- [ ] If a page adds personalization, it includes team-default reset and preserves semantic consistency.
- [ ] If a page introduces fast actions, it supports command palette patterns or documents why excluded.
- [ ] If a page is new, responsive behavior is defined for desktop/tablet/mobile.
- [ ] Locale/format assumptions are explicit (dates, numbers, currency) for user-facing values.

---

## 13) Verification and Sources

### 13.1 Live UI verification

- Verified against authenticated live page at `http://localhost:9080/admin/ui/dashboard`.

### 13.2 Code source of truth

- `src/admin/templates/base.html`
- `src/admin/templates/dashboard.html`
- `src/admin/templates/partials/dashboard_content.html`
- `src/admin/templates/components/status_badge.html`
- `src/admin/templates/partials/metrics_content.html`

### 13.3 External research references

- [NN/g: Dashboards and preattentive processing](https://www.nngroup.com/articles/dashboards-preattentive/)
- [Atlassian Design: Data visualization color](https://atlassian.design/foundations/color-new/data-visualization-color/)
- [Observable: Seven tips for better dashboards](https://observablehq.com/blog/seven-ways-design-better-dashboards)
- [Google Cloud: UX considerations for generative AI apps and agents](https://cloud.google.com/blog/products/ai-machine-learning/how-to-build-a-genai-application)
- [Microsoft Learn: UX guidance for generative AI applications](https://learn.microsoft.com/en-us/microsoft-cloud/dev/copilot/isv/ux-guidance)
- [IBM Carbon for AI: transparency and explainability guidance](https://carbondesignsystem.com/guidelines/carbon-for-ai)
- [The Frontend Company: UI trends in 2026 for SaaS (market scan)](https://www.thefrontendcompany.com/posts/ui-trends)

If implementation diverges from this guide, update this document in the same change.
