# Epic 78: Unified Design Token System Across All Frontend Surfaces

**Status:** Proposed
**Priority:** P2 -- Nice to Have
**Estimated LoE:** 4-6 weeks (8 stories, single developer)
**Dependencies:** Epic 77 (Pipeline Dashboard Style Guide Compliance), Epic 53 (Admin UI Canonical Compliance -- COMPLETE)

---

## 1. Narrative

TheStudio has two frontend surfaces that are supposed to look and feel like one product. They do not.

The style guide (`docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md`) defines a clean three-tier token architecture -- primitive, semantic, and component tokens as CSS custom properties. The guide even specifies the exact variable names, values for both light and dark themes, and the Tailwind `theme.extend` integration pattern. But neither surface actually implements this system:

**Admin Console** (`/admin/ui/*`, 20 templates + 7 components + 32 partials): Has a partial token system introduced in Epic 75 (`--ts-bg`, `--ts-surface`, etc.) that uses non-standard names and covers only a fraction of the style guide's semantic tier. The remaining 590 occurrences of hardcoded Tailwind classes (`bg-gray-800`, `text-gray-300`, `border-gray-700`) and inline hex colors bypass the token system entirely. The `--ts-*` prefix does not match the `--color-*` prefix defined in the style guide.

**Pipeline Dashboard** (`/dashboard/*`, React SPA): Uses `@tailwindcss/vite` with no `tailwind.config` file at all -- meaning no token integration exists. CSS custom properties from the style guide are not imported or referenced. Epic 77 will bring the React side into style-guide compliance, but each surface will still have its own independent color definitions.

The result: changing a brand color, adding a new status semantic, or shipping a third surface means hunting through two codebases with different naming conventions. Dark mode inconsistencies compound with every template added. The style guide promises a token system that does not exist in code.

This epic creates the single shared token CSS file that the style guide has always implied, wires both surfaces to consume it, and migrates the Admin UI's 590+ hardcoded color references to use semantic tokens.

---

## 2. References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| UI/UX Style Guide | `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` | Sections 4.1-4.6 define the full token architecture |
| Admin base template | `src/admin/templates/base.html` | Current `--ts-*` partial tokens (lines 17-52) |
| React entry CSS | `frontend/src/index.css` | No token imports currently |
| Vite config | `frontend/vite.config.ts` | Uses `@tailwindcss/vite` plugin, no tailwind.config |
| Epic 53 (Complete) | `docs/epics/epic-53-admin-ui-canonical-compliance.md` | Brought Admin UI shell/nav/badges to compliance |
| Epic 77 (Dep) | Backlog | Pipeline Dashboard style guide compliance (React side) |
| Playwright test suite | `tests/playwright/` | 100+ test files covering Admin UI pages |
| Admin templates | `src/admin/templates/` | 20 page templates, 7 components, 32 partials |

---

## 3. Acceptance Criteria

- [ ] A single `static/css/tokens.css` file exists containing all three token tiers (primitive, semantic, component) from the style guide Section 4.1-4.4, with both light and dark theme definitions
- [ ] Token variable names match the style guide exactly (`--primitive-*`, `--color-*`, `--sidebar-*`, `--card-*`, `--state-*`, `--motion-*`) -- no `--ts-*` prefix divergence
- [ ] The Admin Console base template (`base.html`) loads `tokens.css` and the `--ts-*` inline token block is removed
- [ ] All 20 Admin UI page templates and their partials reference semantic tokens instead of hardcoded Tailwind color classes or hex values for backgrounds, text, borders, and interactive states
- [ ] The React frontend imports `tokens.css` in `frontend/src/index.css` and (if Epic 77 creates a Tailwind config) extends Tailwind colors to reference the shared CSS custom properties
- [ ] Both surfaces render identically to their current appearance -- this is a refactor, not a redesign
- [ ] All existing Playwright tests pass without modification (visual regression gate)
- [ ] The style guide's "for developers" section documents how to use tokens in both Jinja2 templates and React components

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tailwind CDN class specificity conflicts with CSS custom properties | Medium | High | Apply tokens via Tailwind's `@apply` or use `style` attributes for token references; test each page incrementally |
| Dark mode visual regressions from token value mismatches | Medium | Medium | Run Playwright snapshot tests after each batch migration; compare side-by-side |
| Epic 77 changes Tailwind config in a way that conflicts with token integration | Low | Medium | Coordinate: Epic 77 must complete before Story 78.2 begins |
| Admin templates use Jinja2 conditionals that construct class strings dynamically | Medium | Medium | Audit `{% if %}` blocks that build Tailwind classes; replace with CSS custom property + data-attribute patterns |

---

## 4. Constraints & Non-Goals

### Constraints

- **Token names must match the style guide verbatim.** The style guide (Section 4.1-4.4) is the specification. This epic implements it -- it does not redefine it.
- **Visual identity must not change.** The hex values in `tokens.css` must produce pixel-identical results to current hardcoded values. This is a refactoring epic, not a redesign.
- **Tailwind CDN stays for Admin UI.** The Admin Console uses `cdn.tailwindcss.com` loaded at runtime. Tokens must work alongside this, not replace the CDN approach. Utility classes for layout (`flex`, `p-4`, `rounded-lg`) remain as Tailwind classes -- only color/theme values migrate to tokens.
- **No new dependencies.** No CSS preprocessors, no PostCSS plugins, no build step for Admin UI.
- **Playwright tests are the regression gate.** Every batch of template migrations must pass the full existing test suite before the next batch begins.

### Non-Goals

- **Redesigning the style guide** -- We implement what Section 4 already defines. Any gaps or improvements to the token spec itself are a separate effort.
- **Migrating Admin UI away from Tailwind CDN** -- The CDN approach stays. We add token-based colors alongside layout utilities.
- **Adding new themes beyond light/dark** -- The two-theme system defined in the style guide is what we implement.
- **Changing the React build pipeline** -- Vite + `@tailwindcss/vite` stays as-is.
- **Migrating layout, spacing, or typography classes** -- Only color/background/border values move to tokens in this epic. Layout utilities (`flex`, `grid`, `p-4`, `w-56`, `text-sm`) remain as Tailwind classes.
- **Third-party library overrides** -- The Driver.js spotlight overrides in `index.css` and similar third-party styling keep their hardcoded values (those components own their own color contracts).

---

## 5. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Solo developer | All implementation, testing, and delivery |
| Design Authority | Style Guide (`07-THESTUDIO-UI-UX-STYLE-GUIDE.md`) | Token names, values, and tier structure are defined by this document |
| QA Gate | Playwright test suite | Visual regression and functional regression gate |
| Review | Meridian | Epic review before commit; story-level review at batch boundaries |

---

## 6. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Hardcoded color references in Admin templates | ~654 across 57 files | 0 in page/component templates (partials may retain status-badge Tailwind classes via macros; `tokens.css` definitions excluded from count) | `grep -c` for `bg-gray-`, `text-gray-`, `border-gray-`, `bg-white`, hex colors in `src/admin/templates/` |
| Token coverage (style guide Section 4 properties defined in code) | ~15 `--ts-*` tokens in `base.html` | 100% of style guide Section 4.1-4.4 tokens present in `tokens.css` | Diff `tokens.css` variables against style guide spec |
| Shared token file count | 0 (tokens inline in base.html) | 1 (`static/css/tokens.css`) consumed by both surfaces | File exists and is imported by both `base.html` and `frontend/src/index.css` |
| Playwright test pass rate after migration | 100% | 100% (no regressions) | Full Playwright suite run |
| Time to add a new semantic color | Manual edit in 2+ locations with different naming | Single addition to `tokens.css`, both surfaces pick it up | Developer workflow audit |

---

## 7. Context & Assumptions

### Business Rules

- The style guide is the single source of truth for visual standards (Section 1.1 Source-of-Truth Contract).
- Admin Console is the reference implementation (Section 3.2). After this epic, it will also be the reference for token usage.
- Dark mode is a first-class experience (Section 2.2). Token definitions must cover both themes completely.

### Dependencies

- **Epic 77 must be complete before Story 78.2.** The React side's Tailwind configuration and style-guide compliance work must land first so that Story 78.2 can integrate tokens into whatever Tailwind config Epic 77 establishes. **Epic 77 is currently "Proposed — Pending Review" (as of 2026-03-26) and estimates 3-4 weeks.** If Epic 77 is not sprint-committed by 2026-04-10, Story 78.2 should be deferred to a follow-on epic to avoid blocking the Admin UI migration (Stories 78.3-78.8 can proceed independently).
- **Epic 53 is complete.** Admin UI shell, navigation, badges, empty states, and accessibility baselines are already canonical.
- **Static file mount:** There is currently no `static/` directory mount in `src/app.py`. Only `frontend/dist/` is mounted. Story 78.1 must add a static mount for `static/css/` — this is a new infrastructure change, not a trivial assumption.

### Systems Affected

| System | Impact |
|--------|--------|
| `static/css/tokens.css` (NEW) | New shared CSS file serving design tokens to both surfaces |
| `src/admin/templates/base.html` | Remove inline `--ts-*` block, add `<link>` to `tokens.css` |
| `src/admin/templates/*.html` (20 pages) | Replace hardcoded color classes with token references |
| `src/admin/templates/components/*.html` (7 files) | Replace hardcoded color classes with token references |
| `src/admin/templates/partials/*.html` (32 files) | Replace hardcoded color classes with token references |
| `frontend/src/index.css` | Add `@import` for shared tokens |
| `frontend/tailwind.config.*` or equivalent | Extend colors to reference CSS custom properties (if config exists post-Epic 77) |
| `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` | Add "For Developers" implementation reference |

### Assumptions

- The Tailwind CDN runtime (`cdn.tailwindcss.com`) correctly resolves utility classes that use CSS custom property values (e.g., `bg-[var(--color-bg-surface)]`). If it does not, the fallback strategy is to use inline `style` attributes for token-based colors in Admin templates.
- FastAPI's static file serving does NOT currently mount a `static/` directory (only `frontend/dist/`). Story 78.1 creates this mount — it is a concrete task, not an assumption.
- The existing `--ts-*` tokens in `base.html` map 1:1 to style guide semantic tokens (verified: they do, with different names).
- Epic 77 will not fundamentally change the React project's CSS architecture (Vite + `@tailwindcss/vite` plugin stays).

---

## Story Map

Stories are ordered as vertical slices: foundation first, then surface integrations, then validation.

| # | Story | Points | Files to Create/Modify |
|---|-------|--------|----------------------|
| 78.1 | **Create shared token CSS file** -- Extract all primitive (4.1), semantic (4.2), component (4.3), and extended (4.6) tokens from the style guide into `static/css/tokens.css`. Include `:root` light defaults and `[data-theme="dark"]` overrides. Mount `static/` in FastAPI if not already mounted. | 3 | **Create:** `static/css/tokens.css` **Modify:** `src/app.py` (mount static if needed) |
| 78.2 | **Integrate tokens into React frontend** -- Import `tokens.css` in `frontend/src/index.css`. If Epic 77 created a `tailwind.config`, extend its color theme to reference CSS custom properties per style guide Section 4.4. Verify the React dashboard renders identically. | 2 | **Modify:** `frontend/src/index.css`, `frontend/tailwind.config.*` (if exists) |
| 78.3 | **Integrate tokens into Admin UI base template** -- Update `base.html` to load `tokens.css` via `<link>`. Remove the inline `--ts-*` `<style>` block (lines 17-52). Update all token references from `--ts-*` to `--color-*` names. Replace hardcoded Tailwind color classes with token-based equivalents. **Theme selector decision:** The Admin UI currently uses `.dark` class toggling via `classList.add('dark')` (line 10 of `base.html`), but the style guide specifies `[data-theme="dark"]` selectors. `tokens.css` MUST include **both** selector patterns (`.dark { }` AND `[data-theme="dark"] { }`) so both surfaces work. The Admin UI's FOUC prevention script stays as-is (class-based). A future epic may migrate Admin UI to `data-theme` but that is out of scope here. | 3 | **Modify:** `src/admin/templates/base.html` |
| 78.4 | **Admin page migration batch 1: Dashboard, Repos, Workflows, Audit** -- Replace hardcoded color classes in these 4 page templates and their partials with semantic token references. Run Playwright tests for these 4 pages after migration. | 5 | **Modify:** `src/admin/templates/dashboard.html`, `repos.html`, `repo_detail.html`, `workflows.html`, `workflow_detail.html`, `audit.html`, `partials/dashboard_content.html`, `partials/repos_list.html`, `partials/workflows_list.html`, `partials/workflows_kanban.html`, `partials/audit_list.html`, `partials/repo_detail.html`, `partials/repo_detail_content.html`, `partials/workflow_detail.html`, `partials/workflow_detail_content.html` |
| 78.5 | **Admin page migration batch 2: Metrics, Experts, Tools, Models** -- Replace hardcoded color classes in these 4 page templates and their partials. Run Playwright tests for these 4 pages. | 5 | **Modify:** `src/admin/templates/metrics.html`, `experts.html`, `expert_detail.html`, `tools.html`, `models.html`, `partials/metrics_content.html`, `partials/experts_list.html`, `partials/expert_detail_content.html`, `partials/tools_content.html`, `partials/models_content.html`, `partials/model_spend_content.html` |
| 78.6 | **Admin page migration batch 3: Compliance, Quarantine, Dead Letters, Planes, Settings, Cost Dashboard, Portfolio Health** -- Replace hardcoded color classes in remaining page templates and their partials. Includes detail panels, settings sub-tabs, and error template. Run Playwright tests for all remaining pages. | 5 | **Modify:** `src/admin/templates/compliance.html`, `quarantine.html`, `dead_letters.html`, `planes.html`, `settings.html`, `cost_dashboard.html`, `portfolio_health.html`, `error.html`, `partials/compliance_content.html`, `partials/quarantine_content.html`, `partials/quarantine_detail.html`, `partials/dead_letters_content.html`, `partials/dead_letter_detail.html`, `partials/planes_content.html`, `partials/settings_content.html`, `partials/settings_*.html` (6 files), `partials/cost_dashboard_content.html`, `partials/budget_utilization_content.html`, `partials/portfolio_health_content.html`, `partials/targets_content.html` |
| 78.7 | **Component template migration and cross-surface validation** -- Migrate shared component templates (`status_badge.html`, `empty_state.html`, `workflow_card.html`, `command_palette.html`, `ai_trust.html`, `detail_panel.html`, `icon.html`). Run the FULL Playwright test suite (all Admin + Dashboard tests). Verify both surfaces use the same `tokens.css` file. | 3 | **Modify:** `src/admin/templates/components/status_badge.html`, `empty_state.html`, `workflow_card.html`, `command_palette.html`, `ai_trust.html`, `detail_panel.html` |
| 78.8 | **Token documentation** -- Update style guide Section 4 to reference `static/css/tokens.css` as the canonical implementation. Add a "For Developers" subsection showing: (a) how to use tokens in Jinja2 templates with examples, (b) how to use tokens in React with examples, (c) how to add a new token. | 2 | **Modify:** `docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md` |

**Total: 28 points across 8 stories**

### Slice Order Rationale

- **Slice 1 (Stories 78.1-78.3):** Foundation. Create the shared file, wire both surfaces. Zero visual change, but both surfaces now have access to the token system.
- **Slice 2 (Stories 78.4-78.6):** Migration. Three batches of Admin template updates, ordered by traffic/importance. Each batch is independently testable via Playwright.
- **Slice 3 (Stories 78.7-78.8):** Validation and documentation. Shared components migrate last because they affect all pages. Full cross-surface validation. Documentation closes the loop.

---

## Meridian Review Status

**Round 1: APPROVED WITH CONDITIONS (2026-03-26)**

| # | Question | Result |
|---|----------|--------|
| 1 | Goal testable and unambiguous? | PASS |
| 2 | Acceptance criteria verifiable? | PASS |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified? | GAP (fixed) |
| 5 | Success metrics measurable? | PASS |
| 6 | Agent-implementable without guessing? | GAP (fixed) |
| 7 | Narrative compelling? | PASS |

**Conditions resolved:**
1. **Theme selector conflict (BLOCKING):** Admin UI uses `.dark` class; style guide specifies `[data-theme="dark"]`. **Fixed:** Story 78.3 now explicitly states `tokens.css` must include BOTH selectors. Admin UI keeps class-based toggling. Migration to `data-theme` is out of scope.
2. **Dependency gap:** Epic 77 has no date/status commitment. **Fixed:** Added deadline — if Epic 77 not sprint-committed by 2026-04-10, Story 78.2 defers to follow-on epic.
3. **Missing detail templates:** `expert_detail.html`, `repo_detail.html`, `workflow_detail.html` were not in story map. **Fixed:** Added to Stories 78.4 and 78.5.
4. **Static mount assumption:** No `static/` mount exists in `src/app.py`. **Fixed:** Promoted from assumption to explicit task in Story 78.1.
5. **File count correction:** Updated from ~590/56 to ~654/57.
