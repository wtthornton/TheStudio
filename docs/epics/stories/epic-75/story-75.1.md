# Story 75.1 -- SVG Icon System — Replace Unicode with Heroicons

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to see clean, professional SVG icons throughout the admin navigation and UI components, **so that** the interface looks polished and icons render consistently across all browsers and screen sizes

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the admin UI uses professional, scalable SVG icons instead of Unicode symbols, bringing visual polish in line with modern tools like Plane.so and ensuring consistent rendering across browsers and platforms.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Replace all Unicode symbol icons (▶ ★ ⚙ ☠ ◇ ● $ etc.) in the sidebar navigation, dashboard cards, status badges, and all other templates with inline SVG icons from the Heroicons library. Create a reusable Jinja2 macro that renders icons by name, supporting size and color variants.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/icon.html`
- `src/admin/templates/base.html`
- `src/admin/templates/partials/dashboard_content.html`
- `src/admin/templates/components/status_badge.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create Jinja2 icon macro in components/icon.html that accepts icon name, size (sm/md/lg), and optional CSS class. Include inline SVG definitions for all needed icons. (`src/admin/templates/components/icon.html`)
- [ ] Replace all Unicode nav icons in base.html sidebar (▶ for Pipeline, ► for Dashboard, etc.) with icon macro calls using appropriate Heroicons (`src/admin/templates/base.html`)
- [ ] Replace Unicode icons in dashboard_content.html cards and metric displays (`src/admin/templates/partials/dashboard_content.html`)
- [ ] Update status_badge.html to optionally include SVG status icons (checkmark, warning, x-circle) (`src/admin/templates/components/status_badge.html`)
- [ ] Audit all remaining page templates for Unicode icon usage and replace with macro calls (`src/admin/templates/`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Icon macro renders SVG icons by name with configurable size (16px/20px/24px)
- [ ] All sidebar navigation items use SVG icons instead of Unicode symbols
- [ ] Dashboard cards use SVG icons for section headers and status indicators
- [ ] Status badges optionally display SVG icons alongside text labels
- [ ] Zero Unicode symbol characters remain in navigation or icon positions across all templates

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_icon_macro_renders_svg_icons_by_name_configurable_size` -- Icon macro renders SVG icons by name with configurable size (16px/20px/24px)
2. `test_ac2_all_sidebar_navigation_items_use_svg_icons` -- All sidebar navigation items use SVG icons instead of Unicode symbols
3. `test_ac3_dashboard_cards_use_svg_icons_section_headers` -- Dashboard cards use SVG icons for section headers and status indicators
4. `test_ac4_status_badges_optionally_display_svg_icons` -- Status badges optionally display SVG icons alongside text labels
5. `test_ac5_zero_unicode_symbol_characters_remain` -- Zero Unicode symbol characters remain in navigation or icon positions across all templates

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use Heroicons v2 outline set (24px) for navigation and solid set (20px) for inline indicators
- Inline SVG avoids external sprite sheet HTTP requests
- Macro should support aria-hidden='true' by default since icons are decorative alongside text labels

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None (first story in the epic)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
