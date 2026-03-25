# Story 75.8 -- Accessibility Audit & Fixes for New Components

<!-- docsmcp:start:user-story -->

> **As a** platform operator using assistive technology, **I want** to use the detail panel, command palette, kanban board, and dark mode with keyboard-only navigation and screen readers, **so that** the admin UI remains fully accessible regardless of how I interact with it

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that all new components introduced in this epic meet WCAG 2.2 AA compliance — maintaining TheStudio's existing accessibility standard and ensuring the interactive richness additions don't create barriers for keyboard or screen reader users.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Run a comprehensive WCAG 2.2 AA accessibility audit on all new components introduced in Stories 75.1-75.7. Fix any contrast, focus management, ARIA, or keyboard navigation issues. Ensure the kanban board has keyboard alternatives to drag-and-drop. Validate dark mode contrast ratios. Update Playwright accessibility tests to cover new components.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/detail_panel.html`
- `src/admin/templates/components/command_palette.html`
- `src/admin/templates/partials/workflows_kanban.html`
- `src/admin/templates/base.html`
- `tests/playwright/`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Audit detail panel: verify focus trap works correctly, ARIA dialog pattern is complete, Escape dismisses, focus returns to trigger (`src/admin/templates/components/detail_panel.html`)
- [ ] Audit command palette: verify combobox ARIA pattern, arrow key navigation, screen reader announcement of results (`src/admin/templates/components/command_palette.html`)
- [ ] Audit kanban board: verify keyboard alternatives for drag-and-drop exist (arrow keys or action menu), column headers are properly labelled (`src/admin/templates/partials/workflows_kanban.html`)
- [ ] Run axe-core contrast checks on all pages in both light and dark mode — fix any failures below 4.5:1 ratio (`src/admin/templates/base.html`)
- [ ] Update or create Playwright accessibility test cases for new components (detail panel, command palette, kanban, dark mode) (`tests/playwright/`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Detail panel passes ARIA dialog audit (role='dialog', aria-modal, aria-labelledby, focus trap)
- [ ] Command palette passes ARIA combobox audit (role='combobox', aria-activedescendant, listbox/option)
- [ ] Kanban board has keyboard-accessible card movement (not drag-only)
- [ ] All pages pass axe-core audit in both light and dark modes with zero critical violations
- [ ] Tab order is logical across all new components
- [ ] Screen reader announces panel/palette open/close state changes

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_detail_panel_aria_dialog_audit` -- Detail panel passes ARIA dialog audit
2. `test_ac2_command_palette_aria_combobox_audit` -- Command palette passes ARIA combobox audit
3. `test_ac3_kanban_keyboard_accessible_card_movement` -- Kanban board has keyboard-accessible card movement
4. `test_ac4_all_pages_pass_axe_core_both_modes` -- All pages pass axe-core audit in both light and dark modes
5. `test_ac5_tab_order_logical_new_components` -- Tab order is logical across all new components
6. `test_ac6_screen_reader_announces_state_changes` -- Screen reader announces panel/palette open/close state changes

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use axe-core via @axe-core/playwright for automated accessibility testing
- Focus trap testing: verify Tab from last element wraps to first, Shift+Tab from first wraps to last
- Screen reader testing can be validated through ARIA attribute checks rather than requiring manual SR testing
- Keyboard drag-and-drop alternative: provide a context menu or action buttons (Move to Queued/Running/etc.)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Stories 75.1-75.7 (all components must be built before final audit)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
