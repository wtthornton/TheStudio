# Epic 75: Plane-Parity Admin UI — Interactive Richness & Polish

<!-- docsmcp:start:metadata -->
**Status:** Complete
**Priority:** P1 - High
**Estimated LOE:** ~3-4 weeks (1 developer)
**Dependencies:** Epic 4 (Admin UI Core), Epic 53 (Admin UI Canonical Compliance), Epic 52 (Frontend UI Modernization)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that TheStudio's admin interface evolves from an operational monitoring dashboard into an interactive work-management experience on par with modern tools like Plane.so. The current UI has strong structural bones (dark sidebar, card layout, accessibility) but lacks the interactive richness — detail panels, kanban views, command palette, proper icons, dark mode — that makes a tool feel production-grade and delightful to use daily.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Close the visual and interactive gap between TheStudio's admin UI and Plane.so by adding a sliding detail panel, SVG icon system, kanban/board views, command palette, and dark mode — transforming the admin from a read-only dashboard into an interactive work management surface.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

The admin UI was designed to mirror Plane's clean, modern aesthetic. While the structural foundation is solid (dark sidebar, semantic badges, accessible markup, HTMX-driven updates), user-facing interactivity lags behind. Users cannot click into detail views, drag work items, search via keyboard, or toggle dark mode. These gaps make the UI feel like a monitoring tool rather than the command center it was meant to be. Closing this gap is critical for daily usability and for demonstrating TheStudio as a credible platform product.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [x] Clicking any row/card in repos or workflows opens a right-side sliding detail panel with full item details
- [x] All navigation and UI icons use SVG (Heroicons/Lucide) instead of Unicode symbols
- [x] Workflows page has a toggleable kanban board view with drag-and-drop column reordering
- [x] Ctrl+K opens a command palette with fuzzy search across pages and actions and repos
- [x] Dark mode toggle works across all pages with consistent theming using CSS custom properties
- [x] All new components pass WCAG 2.2 AA accessibility checks
- [x] HTMX integration preserved — no full-page reloads introduced
- [x] Existing Playwright test suite continues to pass

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### [75.1 — SVG Icon System — Replace Unicode with Heroicons](stories/epic-75/story-75.1.md)

**Points:** 3

Replace all Unicode symbol icons in sidebar nav and throughout templates with inline SVG Heroicons. Create a reusable Jinja2 icon macro.

---

### [75.2 — Right-Side Sliding Detail Panel Infrastructure](stories/epic-75/story-75.2.md)

**Points:** 5

Build a reusable sliding panel component that opens from the right edge when a row or card is clicked. Panel supports dynamic content loading via HTMX, keyboard dismiss (Escape), click-outside dismiss, and smooth CSS transitions.

---

### [75.3 — Repo Detail Panel — Click-to-Inspect Repos](stories/epic-75/story-75.3.md)

**Points:** 3

Wire the repos table rows to open the sliding detail panel showing full repo information: config, recent activity, queue status, trust tier history, and quick actions.

---

### [75.4 — Workflow Detail Panel — Click-to-Inspect Workflows](stories/epic-75/story-75.4.md)

**Points:** 3

Wire workflow table rows and kanban cards to open the sliding detail panel showing workflow execution details: status timeline, step outputs, logs, retry actions.

---

### [75.5 — Kanban Board View for Workflows](stories/epic-75/story-75.5.md)

**Points:** 5

Add a toggleable kanban board view to the workflows page. Columns represent workflow states (Queued, Running, Completed, Failed). Cards show workflow summary. Support drag-and-drop reordering within columns using SortableJS.

---

### [75.6 — Command Palette (Ctrl+K)](stories/epic-75/story-75.6.md)

**Points:** 5

Implement a global command palette modal activated by Ctrl+K. Supports fuzzy search across navigation pages, repos, workflows, and common actions. Built with vanilla JS and HTMX for search results.

---

### [75.7 — Dark Mode with CSS Custom Properties](stories/epic-75/story-75.7.md)

**Points:** 5

Implement dark mode using CSS custom properties (design tokens from the style guide). Add a toggle in the header that persists preference to localStorage. Ensure all pages, components, badges, and panels render correctly in both modes.

---

### [75.8 — Accessibility Audit & Fixes for New Components](stories/epic-75/story-75.8.md)

**Points:** 2

Run WCAG 2.2 AA audit on all new components (detail panel, command palette, kanban board, dark mode). Fix any contrast, focus, or ARIA issues. Ensure keyboard-only navigation works end-to-end.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use HTMX for all dynamic content loading — no React/Vue/framework dependencies
- Heroicons (MIT licensed) provides consistent icon set matching Tailwind ecosystem
- SortableJS is lightweight (~10KB) and framework-agnostic for drag-and-drop
- CSS custom properties enable runtime theme switching without Tailwind rebuild
- Command palette follows WAI-ARIA combobox pattern for accessibility
- Detail panel follows WAI-ARIA dialog pattern with focus trap
- All new components must work with existing HTMX polling/refresh patterns

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Full Plane.so feature parity (issues tracking or project management features)
- Mobile-first responsive redesign (read-only mobile support already exists)
- Real-time WebSocket updates (HTMX polling is sufficient for current scale)
- Inline editing of records (this epic is about viewing and navigation richness)
- Custom theming beyond light/dark (no user-configurable color palettes)

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All Unicode icons replaced with SVGs | Unicode in nav | 0 Unicode symbols | Template audit |
| Detail panel open latency | N/A | < 200ms | Browser DevTools |
| Command palette search latency | N/A | < 100ms | Network tab |
| Dark mode contrast compliance | N/A | 100% pages pass | axe-core audit |
| Playwright test regressions | 0 failures | 0 failures | CI |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:stakeholders -->
## Stakeholders

| Role | Person | Responsibility |
|------|--------|----------------|
| Owner | Solo Developer | Implementation and review |
| Meridian | VP of Success | Epic review and approval |

<!-- docsmcp:end:stakeholders -->

<!-- docsmcp:start:references -->
## References

- Epic 4 (Admin UI Core)
- Epic 52 (Frontend UI Modernization Master Plan)
- Epic 53 (Admin UI Canonical Compliance)
- docs/design/07-THESTUDIO-UI-UX-STYLE-GUIDE.md

<!-- docsmcp:end:references -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 75.1: SVG Icon System — Replace Unicode with Heroicons
2. Story 75.2: Right-Side Sliding Detail Panel Infrastructure
3. Story 75.3: Repo Detail Panel — Click-to-Inspect Repos
4. Story 75.4: Workflow Detail Panel — Click-to-Inspect Workflows
5. Story 75.5: Kanban Board View for Workflows
6. Story 75.6: Command Palette (Ctrl+K)
7. Story 75.7: Dark Mode with CSS Custom Properties
8. Story 75.8: Accessibility Audit & Fixes for New Components

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dark mode conversion breaks existing Tailwind color assumptions across 15+ templates | Medium | Medium | Incremental migration; test each page after token conversion |
| SortableJS drag-and-drop conflicts with HTMX swap behavior | Low | Medium | Prototype early; use SortableJS events to trigger HTMX requests manually |
| Command palette search API adds latency if not indexed | Low | Low | Client-side fuzzy search for nav items; HTMX only for entity search |
| Detail panel interferes with existing HTMX polling | Low | Medium | Use separate HTMX target IDs; panel content outside polled containers |

<!-- docsmcp:end:risk-assessment -->

**Total Points:** 31
