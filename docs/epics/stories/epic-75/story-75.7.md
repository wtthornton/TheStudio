# Story 75.7 -- Dark Mode with CSS Custom Properties

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to toggle between light and dark mode in the admin UI, **so that** I can use the tool comfortably in low-light environments and match my system preference

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the admin UI supports dark mode — a baseline expectation for any modern developer tool — using CSS custom properties that align with the design token system defined in the style guide.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement dark mode across all admin pages using CSS custom properties (design tokens). Add a theme toggle in the header that persists preference to localStorage. Support system preference detection via prefers-color-scheme media query. Convert hardcoded Tailwind color classes to use CSS custom properties so theme switching works at runtime without rebuilding CSS.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/base.html`
- `src/admin/templates/partials/dashboard_content.html`
- `src/admin/templates/components/status_badge.html`
- `src/admin/templates/components/empty_state.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define CSS custom property token system in base.html style block: --color-bg-primary, --color-text-primary, --color-border, --color-surface, etc. with light and dark values (`src/admin/templates/base.html`)
- [ ] Create dark mode toggle button in the header bar with sun/moon icon (from Story 75.1 icon macro) (`src/admin/templates/base.html`)
- [ ] Convert Tailwind color classes in base.html (sidebar, header, content area) to use CSS custom properties (`src/admin/templates/base.html`)
- [ ] Convert Tailwind color classes in dashboard_content.html (cards, badges, tables, alerts) to use CSS custom properties (`src/admin/templates/partials/dashboard_content.html`)
- [ ] Convert component templates (status_badge, empty_state, detail_panel, command_palette) to use CSS custom properties (`src/admin/templates/components/`)
- [ ] Add prefers-color-scheme media query for automatic system preference detection with manual override (`src/admin/templates/base.html`)
- [ ] Test all 15+ admin pages in dark mode and fix contrast issues to meet WCAG 4.5:1 ratio (`src/admin/templates/`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Theme toggle in header switches between light and dark mode instantly
- [ ] Dark mode preference persists in localStorage across sessions
- [ ] System preference (prefers-color-scheme: dark) is respected on first visit
- [ ] All text meets WCAG 2.2 AA contrast ratio (4.5:1) in both modes
- [ ] Sidebar renders correctly in dark mode (already dark — should remain consistent)
- [ ] All cards, surfaces, tables, and badges render correctly in dark mode
- [ ] Status badge colors remain distinguishable in dark mode
- [ ] Flash messages remain readable in dark mode

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_theme_toggle_switches_light_dark_instantly` -- Theme toggle in header switches between light and dark mode instantly
2. `test_ac2_dark_mode_persists_localstorage` -- Dark mode preference persists in localStorage across sessions
3. `test_ac3_system_preference_respected_first_visit` -- System preference (prefers-color-scheme: dark) is respected on first visit
4. `test_ac4_text_meets_wcag_contrast_ratio_both_modes` -- All text meets WCAG 2.2 AA contrast ratio (4.5:1) in both modes
5. `test_ac5_sidebar_renders_correctly_dark_mode` -- Sidebar renders correctly in dark mode
6. `test_ac6_cards_surfaces_tables_badges_dark_mode` -- All cards, surfaces, tables, and badges render correctly in dark mode
7. `test_ac7_status_badge_colors_distinguishable_dark_mode` -- Status badge colors remain distinguishable in dark mode
8. `test_ac8_flash_messages_readable_dark_mode` -- Flash messages remain readable in dark mode

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Token naming convention: --color-{purpose}-{variant} (e.g. --color-bg-primary, --color-text-secondary)
- Apply dark theme via data-theme='dark' attribute on html element — allows JS toggle without media query conflicts
- Reference docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md for defined but unimplemented token values
- Sidebar is already dark (bg-gray-900) — in dark mode the content area darkens to match rather than sidebar lightening

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 75.1 (icon macro for sun/moon toggle icon)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
