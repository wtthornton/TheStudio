# Story 75.5 -- Kanban Board View for Workflows

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to toggle between list and kanban views on the workflows page, seeing workflow cards organized by status columns, **so that** I can quickly see the distribution of workflows across states and identify bottlenecks at a glance

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can visualize workflow distribution across states in a spatial kanban layout — the signature Plane.so interaction pattern — enabling faster situational awareness than a flat table.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a toggleable kanban board view to the workflows page. Columns represent workflow states (Queued, Running, Completed, Failed). Each card shows a workflow summary (ID, repo, duration, status). Support drag-and-drop card movement between columns using SortableJS. Persist the user's view preference (list vs kanban) in localStorage.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/workflows_kanban.html`
- `src/admin/templates/workflows.html`
- `src/admin/templates/base.html`
- `src/admin/routes.py`
- `src/admin/templates/components/workflow_card.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create kanban board partial template with flex column layout: Queued, Running, Completed, Failed columns with card counts in headers (`src/admin/templates/partials/workflows_kanban.html`)
- [ ] Add view toggle buttons (list icon / kanban icon) to workflows page header, wired to show/hide the appropriate view (`src/admin/templates/workflows.html`)
- [ ] Add SortableJS CDN script to base.html and initialize drag-and-drop on kanban columns (`src/admin/templates/base.html`)
- [ ] Create HTMX endpoint that returns workflow data grouped by status for kanban rendering (`src/admin/routes.py`)
- [ ] Create workflow card component for kanban items showing: workflow ID, repo name, duration, status badge (`src/admin/templates/components/workflow_card.html`)
- [ ] Persist view preference (list/kanban) in localStorage, restore on page load (`src/admin/templates/workflows.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] View toggle switches between list table and kanban board without page reload
- [ ] Kanban shows 4 columns: Queued / Running / Completed / Failed with card counts
- [ ] Each workflow card displays workflow ID, repo name, duration, and status badge
- [ ] Cards can be dragged between columns (visual feedback during drag)
- [ ] View preference persists in localStorage across page refreshes
- [ ] Kanban cards are clickable to open the detail panel (integrates with Story 75.4)
- [ ] Keyboard alternative exists for drag-and-drop (move card via arrow keys or context menu)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_view_toggle_switches_list_kanban_no_reload` -- View toggle switches between list table and kanban board without page reload
2. `test_ac2_kanban_shows_4_columns_with_card_counts` -- Kanban shows 4 columns: Queued / Running / Completed / Failed with card counts
3. `test_ac3_workflow_card_displays_id_repo_duration_badge` -- Each workflow card displays workflow ID, repo name, duration, and status badge
4. `test_ac4_cards_draggable_between_columns` -- Cards can be dragged between columns (visual feedback during drag)
5. `test_ac5_view_preference_persists_localstorage` -- View preference persists in localStorage across page refreshes
6. `test_ac6_kanban_cards_clickable_open_detail_panel` -- Kanban cards are clickable to open the detail panel
7. `test_ac7_keyboard_alternative_for_drag_drop` -- Keyboard alternative exists for drag-and-drop

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- SortableJS v1.15 CDN (~10KB gzip) is framework-agnostic and works with HTMX
- On card drop, use SortableJS onEnd callback to trigger HTMX request for status update
- Column headers should show card count that updates dynamically on drag
- Use CSS grid or flexbox for column layout — columns should have min-width and scroll independently

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 75.2 (detail panel for card click)
- Story 75.4 (workflow detail content for panel)

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
