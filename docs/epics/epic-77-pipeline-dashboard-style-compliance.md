# Epic 77: Pipeline Dashboard Style Guide Compliance

> **Status:** COMPLETE (all 9 stories delivered, 2026-03-26)
> **Epic Owner:** Primary Developer
> **Priority:** P0 -- Critical (visual inconsistency undermines trust in a product whose entire value proposition is trustworthy automation)
> **Estimated LoE:** 3-4 weeks (9 stories, 2 slices)
> **Dependencies:** Epic 76 (Pipeline Dashboard Playwright Suite) provides the validation tests; Epic 54 (Dashboard UI Canonical Compliance) is COMPLETE and provides the semantic baseline. **Note:** Stories 77.1-77.8 can proceed independently of Epic 76. Only Story 77.9 (validation pass) requires Epic 76 to be complete.
> **Capacity:** Solo developer, 30 hours/week
> **Created:** 2026-03-26

---

## 1. Title

**Pipeline Dashboard Style Guide Compliance -- Design Token Foundation, Color Standardization, and Component Recipe Alignment Across All React Components**

---

## 2. Narrative

The Pipeline Dashboard is the primary operational interface for TheStudio. Operators spend hours in this surface triaging issues, reviewing intent specifications, monitoring pipeline progress, and configuring trust tiers. Every inconsistent color, every badge that uses the wrong palette, every button that speaks a different visual language erodes operator confidence in the system.

Right now the dashboard has a credibility problem. BudgetDashboard buttons are indigo. TrustConfiguration buttons are violet. TriageCard buttons are emerald. The style guide says blue. Status badges use opaque `bg-emerald-900 text-emerald-300` instead of the guide's translucent `rgba(22, 163, 74, 0.2) text-green-500` dark-mode palette. There are zero CSS custom properties implementing the three-tier token architecture mandated by Section 4 of the style guide. The `tailwind.config.ts` has no `theme.extend` mapping semantic tokens to utility classes. No component carries `data-component`, `data-status`, or `data-tier` attributes for Playwright test targeting.

Epic 54 established the semantic foundation -- dialog patterns, focus management, accessibility baselines, and prompt-first flows. This epic is the color and token layer that sits on top of that foundation. Without it, the dashboard fails visual regression tests (Epic 76), confuses operators with inconsistent interaction cues, and makes future theming or white-labeling impossible.

The fix is mechanical but pervasive. We create the token CSS file once, wire it into Tailwind once, then systematically replace hardcoded color classes across every affected component. No new features. No new APIs. Pure alignment to the standard we already wrote.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Standard | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` Section 4 (Design Token Architecture) | Three-tier token system: primitive, semantic, component |
| Standard | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` Section 5 (Color System) | Status colors, trust tier mapping, interactive colors |
| Standard | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` Section 6 (Typography Scale) | Font stack: Inter + JetBrains Mono |
| Standard | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` Section 9 (Component Recipes) | Cards (9.1), Tables (9.2), Badges (9.3), Buttons (9.4), Modals (9.6), Empty States (9.11), Error States (9.12) |
| Predecessor | `docs/epics/epic-54-dashboard-ui-canonical-compliance.md` | COMPLETE -- semantic consistency, focus management, prompt-first flows |
| Dependency | Epic 76 (Pipeline Dashboard Playwright Suite) | Provides the test suite that measures compliance; must exist before this epic starts |
| Source | `frontend/src/index.css` | Current CSS: no design tokens, only animation utilities |
| Source | `frontend/src/App.css` | Empty file (all styles via Tailwind utilities) |
| Gap analysis | Grep: `indigo-600\|violet-700\|emerald-700` across `frontend/src/` | 24 non-blue primary button instances across 13 files |
| Gap analysis | Grep: `bg-emerald-900\|bg-emerald-800\|text-emerald-300` across `frontend/src/` | 16 dark-palette badge violations across 13 files |
| Gap analysis | Grep: `data-component\|data-status\|data-tier` across `frontend/src/` | 0 matches -- no semantic test attributes exist |

---

## 4. Acceptance Criteria

### AC1: Design Token CSS File Exists and Is Imported

A file `frontend/src/theme.css` exists containing all primitive tokens (Section 4.1), semantic tokens for light and dark themes (Section 4.2), component tokens (Section 4.3), and extended token categories (Section 4.6) from the style guide. This file is imported in `frontend/src/index.css` before any other styles. The `:root` and `[data-theme="dark"]` selectors define the complete token set.

**Testable:** Open `frontend/src/theme.css`. It contains `--primitive-gray-*`, `--primitive-blue-*`, `--color-bg-primary`, `--color-interactive-primary`, `--card-bg`, `--sidebar-bg`, `--state-hover-overlay`, `--motion-duration-normal`, and all other tokens from Sections 4.1-4.6. Open `frontend/src/index.css`. Its first import is `./theme.css`.

### AC2: Tailwind v4 Theme Maps Semantic Tokens

The project uses **Tailwind v4.2.2** with CSS-first configuration (`@tailwindcss/vite` plugin, `@import "tailwindcss"` in `index.css`). There is no `tailwind.config.ts` — Tailwind v4 uses `@theme` directives in CSS instead of JavaScript config files.

The `frontend/src/theme.css` file (or `index.css`) contains `@theme` blocks mapping semantic token names to CSS custom properties as specified in Section 4.4. At minimum: `--color-surface`, `--color-elevated`, `--color-primary`, `--color-destructive`, and all status color mappings.

**Testable:** Open `frontend/src/theme.css` or `frontend/src/index.css`. A `@theme` block exists with entries like `--color-surface: var(--color-bg-surface)`. Running `npx vite build` produces no CSS errors. Components can use classes like `bg-[var(--color-bg-surface)]` or custom theme utilities.

### AC3: All Primary Buttons Use Blue, Not Indigo/Violet/Emerald

Every primary action button in the React SPA uses `bg-blue-600 text-white hover:bg-blue-700` (light) or `bg-blue-500 text-white hover:bg-blue-600` (dark), per Section 9.4. Zero instances of `bg-indigo-600`, `bg-violet-700`, or `bg-emerald-700` used as primary button colors remain.

**Testable:** `grep -r "bg-indigo-600\|bg-violet-700\|bg-emerald-700" frontend/src/components/` returns zero matches for primary button contexts. Playwright visual regression tests from Epic 76 pass for button color assertions.

### AC4: Status Badges Use Guide's rgba Dark Palette

All status badges in dark mode use the translucent rgba background pattern from Section 5.1: success = `rgba(22, 163, 74, 0.2) / text-green-500`, warning = `rgba(234, 179, 8, 0.2) / text-yellow-500`, error = `rgba(239, 68, 68, 0.2) / text-red-500`, info = `rgba(59, 130, 246, 0.2) / text-blue-500`, neutral = `bg-gray-800 / text-gray-400`. No opaque `bg-emerald-900`, `bg-emerald-800`, or similar overrides remain.

**Testable:** `grep -r "bg-emerald-900\|bg-emerald-800\|text-emerald-300" frontend/src/components/` returns zero matches in badge contexts. Playwright badge color assertions from Epic 76 pass.

### AC5: Semantic Data Attributes Present on All Components

Every top-level React component renders a `data-component` attribute with its name (e.g., `data-component="BudgetDashboard"`). Status-bearing elements render `data-status` with the current status value (e.g., `data-status="success"`). Trust-tier indicators render `data-tier` with the tier value (e.g., `data-tier="EXECUTE"`).

**Testable:** Playwright can locate every major component via `[data-component="..."]`. Playwright can filter status badges via `[data-status="..."]`. Playwright can target trust tier badges via `[data-tier="..."]`. At least 20 components carry `data-component`, at least 5 status contexts carry `data-status`, at least 3 trust-tier contexts carry `data-tier`.

### AC6: Font Stack Explicitly Declared

The `--font-sans` and `--font-mono` CSS custom properties from Section 6.1 are defined in `theme.css` and applied to the root element. The Tailwind config maps `fontFamily.sans` and `fontFamily.mono` to these tokens.

**Testable:** Open `theme.css`. `--font-sans` includes `'Inter'` as first entry. `--font-mono` includes `'JetBrains Mono'` as first entry. The `<body>` or `<html>` element has `font-family` resolving to Inter.

### AC7: Epic 76 Playwright Style Tests Pass

All style-related Playwright tests from Epic 76 pass green. This is the integration gate: the tokens, buttons, badges, data attributes, and typography changes produce a dashboard that meets the style guide's requirements as verified by automated visual and structural tests.

**Testable:** Run `npx playwright test tests/playwright/style-compliance/` (or equivalent Epic 76 test path). All tests pass. Zero failures.

---

## 4b. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Tailwind v4 CSS-first config uses `@theme` directives, not `tailwind.config.ts` | **Confirmed** (not a risk — a fact) | High -- token mapping approach must use v4 patterns | Project uses Tailwind v4.2.2 (`@tailwindcss/vite`). Story 77.1 uses `@theme` in CSS, not `theme.extend.colors` in JS. Style guide Section 4.4 examples show v3 syntax — adapt to v4 `@theme` equivalent. |
| R2 | Replacing emerald/violet colors breaks visual context operators have learned | Low | Medium -- operator confusion | Changes align with documented standard; colors shift to blue which is a universally recognized "primary action" color |
| R3 | Epic 76 tests don't exist yet when this epic starts | High | High -- no way to measure compliance | Hard dependency: Epic 76 must land first. Story 77.9 (validation pass) runs last |
| R4 | Adding `data-*` attributes inflates DOM and may conflict with existing `data-testid` | Low | Low -- attributes are additive | `data-component`/`data-status`/`data-tier` are semantically distinct from `data-testid`; both coexist |

---

## 5. Constraints & Non-Goals

### Constraints
- The dashboard is dark-first. All token work must validate against the `[data-theme="dark"]` selectors as the primary experience.
- No component behavior changes. This epic is purely visual alignment -- no new features, no new API calls, no new state management.
- The existing `data-testid` attributes must be preserved. `data-component`/`data-status`/`data-tier` are additive, not replacements.
- All changes must pass existing Vitest unit tests. If a test asserts a specific CSS class (e.g., `bg-indigo-600`), the test must be updated in the same story that changes the class.
- Inter and JetBrains Mono fonts are declared via CSS `@import` or `<link>`; they are not bundled. If the fonts fail to load, the fallback stack must remain functional.

### Non-Goals
- **Theme switcher UI** -- The style guide defines the token system and FOUC prevention script, but building a visible light/dark toggle is out of scope. That is a separate epic.
- **Navigation migration** -- The style guide notes that the dashboard should migrate from horizontal tabs to sidebar navigation. That is Epic 49 scope, not this epic.
- **Admin Console (HTMX) alignment** -- This epic covers only the React SPA (`frontend/src/`). The Jinja2/HTMX admin surface has its own compliance path.
- **New component creation** -- We modify existing components, not create new ones. If a recipe from Section 9 has no existing implementation, it is out of scope.
- **Performance optimization** -- Adding CSS custom properties may marginally affect paint time. We do not optimize for this unless a measurable regression appears.
- **Responsive layout changes** -- Section 8.6 responsive behavior is separate scope. This epic touches colors, tokens, and attributes, not layout breakpoints.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Token architecture, component updates, test validation |
| Style Guide Owner | Primary Developer | Authoritative reference for all visual decisions |
| Meridian (Review) | Persona | Epic review, acceptance criteria validation |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Non-blue primary button instances | 0 remaining | `grep -rE "bg-(indigo\|violet\|emerald)-[67]00" frontend/src/components/ \| grep -v "//\|trust\|tier"` returns 0 for primary button contexts |
| Opaque dark-mode badge instances | 0 remaining | `grep -rE "bg-emerald-[89]00\|text-emerald-300" frontend/src/components/` returns 0 |
| CSS custom properties defined | >= 60 tokens in `theme.css` | `grep -c "^  --" frontend/src/theme.css` >= 60 |
| Components with `data-component` | >= 20 | `grep -r "data-component" frontend/src/components/ \| wc -l` >= 20 |
| Tailwind semantic color mappings | >= 10 entries | Count entries in `theme.extend.colors` block |
| Epic 76 style test pass rate | 100% | Playwright test run: 0 failures |
| Vitest regression | 0 new failures | `npx vitest run` passes with no regressions |

---

## 8. Context & Assumptions

### Business Rules
- The style guide (`docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`) is the single source of truth. Section 1.1 states: "If any other document, component library, or template conflicts with this guide, this guide wins."
- Trust tier colors (purple for EXECUTE, blue for SUGGEST, gray for OBSERVE) are domain-specific and must not be confused with primary button blue. Trust tier badges use the palette from Section 5.2, not the interactive color from Section 5.4.
- The EXECUTE tier uses purple (`bg-purple-100 text-purple-800` light / `purple-500/20 text-purple-500` dark). This is not the same as `bg-violet-700` currently used for TrustConfiguration buttons. The buttons are primary actions and should be blue; the tier badges should be purple.

### Dependencies
- **Epic 76 (Pipeline Dashboard Playwright Suite):** Must exist before Story 77.9. Stories 77.1-77.8 can be developed independently but are only validated by Epic 76 tests.
- **Tailwind CSS version:** The frontend uses Tailwind. The token integration approach (Section 4.4) assumes `theme.extend.colors` in a JavaScript/TypeScript config. If the project uses Tailwind v4's CSS-first config, the approach must adapt accordingly. Story 77.1 verifies this before proceeding.
- **Font CDN:** Inter and JetBrains Mono must be loadable. If the project is deployed in an air-gapped environment, fonts must be self-hosted. This epic assumes CDN availability.

### Systems Affected
- `frontend/src/theme.css` -- NEW file, design token definitions
- `frontend/src/index.css` -- Modified to import `theme.css`
- `frontend/tailwind.config.ts` -- NEW or modified, semantic token mapping
- 25+ React components in `frontend/src/components/` -- Color class replacements and `data-*` attribute additions
- 5-10 Vitest test files -- Updated class assertions where tests check specific color classes

### Assumptions
- The React SPA is the only surface affected. HTMX admin templates are excluded.
- Epic 54 semantic work (focus management, dialog patterns, prompt-first) is stable and will not be disrupted by color-only changes.
- Operators have not built muscle memory around specific non-standard colors (indigo/violet/emerald). Shifting to standard blue will not cause confusion.
- The dashboard is currently dark-mode only (no theme toggle). All changes must look correct in dark mode. Light-mode token definitions are included for future use but are not actively tested.

---

## Story Map

### Slice 1: Foundation (must land first -- all other stories depend on this)

| Story | Title | Points | Files to Create/Modify |
|-------|-------|--------|----------------------|
| 77.1 | Design token foundation -- Create `theme.css` with CSS custom properties and wire Tailwind v4 `@theme` | 5 | **Create:** `frontend/src/theme.css` **Modify:** `frontend/src/index.css` (add `@import "./theme.css"` and `@theme` block for custom utilities). **Note:** Project uses Tailwind v4.2.2 with CSS-first config (`@tailwindcss/vite`). There is no `tailwind.config.ts` — use `@theme` directives in CSS instead of `theme.extend.colors` in JS. |
| 77.2 | Primary button color standardization -- Replace indigo/violet/emerald with blue across all components | 5 | **Modify:** `frontend/src/components/BudgetDashboard.tsx`, `frontend/src/components/TrustConfiguration.tsx`, `frontend/src/components/planning/TriageCard.tsx`, `frontend/src/components/planning/IntentEditor.tsx`, `frontend/src/components/planning/RoutingPreview.tsx`, `frontend/src/components/SteeringActionBar.tsx`, `frontend/src/components/ai/DecisionControls.tsx`, `frontend/src/components/collaboration/CommentThread.tsx`, `frontend/src/components/dashboard/DashboardCustomizer.tsx`, `frontend/src/components/planning/EditPanel.tsx`, `frontend/src/components/planning/IntentEditMode.tsx`, `frontend/src/components/planning/TriageAcceptModal.tsx` |
| 77.3 | Status badge color alignment -- Update badges to use guide's rgba dark palette | 3 | **Modify:** `frontend/src/components/ActivityStream.tsx`, `frontend/src/components/GateInspector.tsx`, `frontend/src/components/ErrorStates.tsx`, `frontend/src/components/ai/AuditTimeline.tsx`, `frontend/src/components/ai/DecisionControls.tsx`, `frontend/src/components/ai/TrustMetadata.tsx`, `frontend/src/components/SteeringActionBar.tsx`, `frontend/src/components/planning/IntentSpec.tsx`, `frontend/src/components/planning/MetricCard.tsx`, `frontend/src/components/planning/TriageCard.tsx`, `frontend/src/components/planning/VersionDiff.tsx`, `frontend/src/components/wizard/LLMProviderStep.tsx`, `frontend/src/components/wizard/TestIssueStep.tsx` |

### Slice 2: Instrumentation and Polish

| Story | Title | Points | Files to Create/Modify |
|-------|-------|--------|----------------------|
| 77.4 | Data attribute instrumentation -- Add `data-component`, `data-status`, `data-tier` to all React components | 5 | **Modify:** All major component files in `frontend/src/components/` (20+ files). Each file gets a `data-component` on its root element. Status-bearing elements get `data-status`. Trust-tier elements get `data-tier`. |
| 77.5 | Typography alignment -- Add explicit font-family declarations and verify heading scale | 2 | **Modify:** `frontend/src/theme.css` (add `--font-sans`, `--font-mono`), `frontend/src/index.css` (apply font-family to body), `frontend/tailwind.config.ts` (map `fontFamily`) |
| 77.6 | Card/table/modal recipe alignment -- Verify and fix component recipes against Sections 9.1, 9.2, 9.6 | 3 | **Modify:** `frontend/src/components/planning/BacklogBoard.tsx` (card recipe), `frontend/src/components/reputation/Reputation.tsx` (table recipe), `frontend/src/components/github/ImportModal.tsx` (modal recipe), `frontend/src/components/planning/CreateTaskModal.tsx`, `frontend/src/components/planning/RefinementModal.tsx` |
| 77.7 | Focus ring and accessibility color fixes -- Ensure focus-visible uses `--color-focus-ring`, touch targets meet 44px | 2 | **Modify:** Components from 77.2 and 77.3 with non-standard focus rings (e.g., `focus-visible:ring-emerald-500`, `focus-visible:ring-violet-400`, `focus:border-indigo-500`, `focus:border-violet-500`). Replace with `focus-visible:ring-blue-500` or token-based equivalent. **Explicit additional files:** `frontend/src/components/HelpPanel.tsx`, `frontend/src/components/SteeringActivityLog.tsx` (both have focus ring violations not covered by 77.2/77.3). |
| 77.8 | Empty state and error state alignment -- Verify against Section 9.11 and 9.12 recipes | 2 | **Modify:** `frontend/src/components/EmptyState.tsx`, `frontend/src/components/ErrorStates.tsx`. Verify heading, description, CTA structure matches recipe. Fix any color deviations. |
| 77.9 | Validation pass -- Run Epic 76 Playwright style tests, fix remaining failures | 3 | **Modify:** Any files that fail Epic 76 tests. This is the catch-all integration story. Expected: mostly clean if 77.1-77.8 are done correctly. |

### Story Dependency Graph

```
77.1 (tokens) ──┬──> 77.2 (buttons)  ──┐
                ├──> 77.3 (badges)   ──┤
                ├──> 77.5 (typography) ─┤
                └──> 77.6 (recipes)  ──┤
                                       ├──> 77.7 (focus rings)
77.4 (data attrs) ─────────────────────┤
                                       ├──> 77.8 (empty/error)
                                       └──> 77.9 (validation)
```

Story 77.1 must land first. Stories 77.2, 77.3, 77.4, 77.5, 77.6 can be parallelized. Stories 77.7 and 77.8 depend on the color work being done. Story 77.9 is always last.

### Ralph Sizing Notes

- **77.1** (5 pts): Creates 1 new file (~200 lines of CSS tokens), modifies `index.css` (add import + `@theme` block for Tailwind v4). Reads style guide sections 4.1-4.6 for reference. No `tailwind.config.ts` needed — Tailwind v4 uses CSS-first config. One Ralph loop.
- **77.2** (5 pts): Touches 12 files but each change is a mechanical find-and-replace of color classes. May require 2 Ralph loops (6 files each) to stay under the 5-file edit limit.
- **77.3** (3 pts): Touches 11 files but changes are identical pattern: replace opaque bg with rgba pattern. One Ralph loop with batch replace.
- **77.4** (5 pts): Touches 20+ files but each change is adding 1 attribute to a root `<div>`. Split into 2 Ralph loops: components A-L, then M-Z.
- **77.5** (2 pts): Modifies 3 files. One Ralph loop.
- **77.6** (3 pts): Modifies 5 files, requires reading style guide recipes for comparison. One Ralph loop.
- **77.7** (2 pts): Modifies files already touched in 77.2/77.3. Focused grep-and-fix. One Ralph loop.
- **77.8** (2 pts): Modifies 2 files. One Ralph loop.
- **77.9** (3 pts): Run tests, fix failures. May require 1-2 Ralph loops depending on failure count.

**Total: 30 story points across 9 stories.**

---

## Meridian Review Status

**Round 1: APPROVED WITH CONDITIONS (2026-03-26)**

| # | Question | Result |
|---|----------|--------|
| 1 | Goal testable and unambiguous? | PASS |
| 2 | Acceptance criteria verifiable? | PASS |
| 3 | Dependencies identified and realistic? | GAP (fixed) |
| 4 | Non-goals explicit? | PASS |
| 5 | Stories right-sized for execution? | PASS (minor gaps fixed) |
| 6 | Scope bounded? | PASS |
| 7 | Connects to measurable outcome? | PASS |

**Red flags found and resolved:**
1. **Tailwind v4 incompatibility (BLOCKING):** Epic assumed v3 `tailwind.config.ts` / `theme.extend.colors`. Project uses Tailwind v4.2.2 with CSS-first config. **Fixed:** Rewrote AC2, Story 77.1, Risk R1, and Ralph sizing to use `@theme` directives in CSS.
2. **Missing wizard component files:** `wizard/LLMProviderStep.tsx` and `wizard/TestIssueStep.tsx` had badge violations but were not in Story 77.3. **Fixed:** Added to Story 77.3 file list.
3. **Focus ring file list incomplete:** `HelpPanel.tsx` and `SteeringActivityLog.tsx` had focus ring violations not covered by 77.2/77.3. **Fixed:** Added explicitly to Story 77.7.
4. **Dependency contradiction:** Line 7 said "must land first" but line 157 said "can develop independently." **Fixed:** Clarified that 77.1-77.8 proceed independently; only 77.9 requires Epic 76.
