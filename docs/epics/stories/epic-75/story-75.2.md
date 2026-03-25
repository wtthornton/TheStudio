# Story 75.2 -- Right-Side Sliding Detail Panel Infrastructure

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to click on any item in a list or table and see its details in a sliding panel from the right side without leaving the current page, **so that** I can inspect details in context without losing my place in the list view

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that a reusable sliding panel component is available for any page to show contextual detail views, matching Plane.so's inspector panel pattern and enabling click-to-inspect workflows across the admin UI.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Build a reusable sliding detail panel component that opens from the right edge of the viewport. The panel loads content dynamically via HTMX, supports keyboard dismiss (Escape), click-outside-to-close, smooth CSS slide transitions, and proper ARIA dialog semantics with focus trapping.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/components/detail_panel.html`
- `src/admin/templates/base.html`
- `src/admin/routes.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create detail_panel.html Jinja2 component with slide-in/out CSS transitions (transform: translateX), backdrop overlay, and configurable width (`src/admin/templates/components/detail_panel.html`)
- [ ] Add panel open/close JavaScript to base.html: listen for HTMX triggers, manage panel state, handle transitions (`src/admin/templates/base.html`)
- [ ] Create base panel API endpoint pattern in admin routes that returns partial HTML for panel content (`src/admin/routes.py`)
- [ ] Implement keyboard handling: Escape to close, Tab trap within panel (first/last focusable element cycle) (`src/admin/templates/base.html`)
- [ ] Add ARIA attributes: role='dialog', aria-modal='true', aria-labelledby for panel title, focus management on open/close (`src/admin/templates/components/detail_panel.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Panel slides in from the right with a smooth CSS transition (300ms ease-out)
- [ ] Panel loads content dynamically via HTMX hx-get without full page reload
- [ ] Pressing Escape closes the panel and returns focus to the trigger element
- [ ] Clicking the backdrop overlay closes the panel
- [ ] Tab key cycles through focusable elements within the panel (focus trap)
- [ ] Panel has role='dialog' and aria-modal='true' with proper labelling
- [ ] Panel works at viewport widths from 768px to 1920px+ (responsive width)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. Open panel via click — verify slide animation completes and content loads
2. Press Escape — verify panel closes and focus returns to trigger
3. Click backdrop — verify panel closes
4. Tab through panel — verify focus stays trapped within panel
5. Screen reader announces panel as dialog with title
6. Panel content loads via HTMX — verify no full page reload in network tab

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use CSS transform: translateX(100%) for hidden state and translateX(0) for visible
- HTMX integration: use hx-target to point at panel content container
- Focus trap: track first and last focusable elements and redirect Tab/Shift+Tab
- Store last focused element before panel open to restore on close

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 75.1 (icon macro needed for close button icon)

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
