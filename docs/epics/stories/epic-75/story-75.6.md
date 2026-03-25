# Story 75.6 -- Command Palette (Ctrl+K)

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to press Ctrl+K and search across pages, repos, workflows, and actions from a single search modal, **so that** I can navigate and act faster without clicking through sidebar menus

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that power users can navigate the admin UI, search for entities, and trigger actions entirely from the keyboard — matching the Ctrl+K command palette pattern found in Plane.so, VS Code, and other modern tools.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Implement a global command palette modal activated by Ctrl+K (Cmd+K on Mac). The palette provides fuzzy search across navigation pages (client-side) and entities like repos and workflows (via HTMX API calls). Results are categorized (Pages, Repos, Workflows, Actions) and navigable via arrow keys with Enter to select.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/command_palette.html`
- `src/admin/templates/base.html`
- `src/admin/routes.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create command palette modal component with search input, categorized results list, and close button (`src/admin/templates/components/command_palette.html`)
- [ ] Add global keyboard listener in base.html: Ctrl+K / Cmd+K opens palette, Escape closes it (`src/admin/templates/base.html`)
- [ ] Implement client-side fuzzy search for navigation items (all sidebar links with labels) (`src/admin/templates/components/command_palette.html`)
- [ ] Create search API endpoint GET /admin/api/search?q= that returns matching repos and workflows as JSON (`src/admin/routes.py`)
- [ ] Add keyboard navigation within results: arrow up/down to highlight, Enter to navigate, typed text filters results (`src/admin/templates/components/command_palette.html`)
- [ ] Add ARIA combobox pattern: role='combobox' on input, role='listbox' on results, role='option' on items, aria-activedescendant tracking (`src/admin/templates/components/command_palette.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Ctrl+K (Cmd+K on Mac) opens the command palette modal from any page
- [ ] Typing filters results with fuzzy matching across pages and entities
- [ ] Results are grouped by category: Pages / Repos / Workflows / Actions
- [ ] Arrow keys navigate between results with visual highlight
- [ ] Enter key navigates to the selected result
- [ ] Escape closes the palette and returns focus to previous element
- [ ] Search API responds in under 100ms for entity queries
- [ ] Palette follows WAI-ARIA combobox pattern for screen reader accessibility

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_ctrlk_opens_command_palette_from_any_page` -- Ctrl+K (Cmd+K on Mac) opens the command palette modal from any page
2. `test_ac2_typing_filters_results_fuzzy_matching` -- Typing filters results with fuzzy matching across pages and entities
3. `test_ac3_results_grouped_by_category` -- Results are grouped by category: Pages / Repos / Workflows / Actions
4. `test_ac4_arrow_keys_navigate_results` -- Arrow keys navigate between results with visual highlight
5. `test_ac5_enter_navigates_to_selected_result` -- Enter key navigates to the selected result
6. `test_ac6_escape_closes_palette_returns_focus` -- Escape closes the palette and returns focus to previous element
7. `test_ac7_search_api_responds_under_100ms` -- Search API responds in under 100ms for entity queries
8. `test_ac8_palette_follows_aria_combobox_pattern` -- Palette follows WAI-ARIA combobox pattern for screen reader accessibility

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Client-side fuzzy search for nav items avoids API latency for the most common use case
- Use HTMX hx-trigger='keyup changed delay:150ms' for debounced entity search
- Fuzzy matching algorithm: simple substring match is sufficient for MVP — upgrade to Fuse.js if needed
- Palette should render above all other content (z-index: 50) with backdrop overlay

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 75.1 (icon macro for search and close icons)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [ ] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
