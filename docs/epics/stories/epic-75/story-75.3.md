# Story 75.3 -- Repo Detail Panel — Click-to-Inspect Repos

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to click a repo row and see its full details in a sliding panel, **so that** I can inspect repo configuration, activity, and status without leaving the repos list

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can quickly inspect full repository details — config, activity, queue depth, trust tier — by clicking a row in the repos table, without navigating away from the repos list.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Wire the repos table rows to open the sliding detail panel (from Story 75.2) showing comprehensive repo information: repository config, recent workflow activity, current queue status, trust tier with history, and quick action buttons.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/repo_detail.html`
- `src/admin/routes.py`
- `src/admin/templates/repos.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create repo detail partial template with sections: header (name + status badge), config summary, recent activity list, queue status, trust tier badge with history (`src/admin/templates/partials/repo_detail.html`)
- [ ] Add HTMX endpoint GET /admin/ui/partials/repo/{repo_id}/detail that returns the repo detail partial (`src/admin/routes.py`)
- [ ] Wire repos table rows with hx-get pointing to repo detail endpoint, targeting the detail panel content area (`src/admin/templates/repos.html`)
- [ ] Style repo detail sections with consistent card layout, badges, and typography matching the existing admin design system (`src/admin/templates/partials/repo_detail.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Clicking a repo row opens the detail panel with that repo's information
- [ ] Panel shows repo name and current status badge in the header
- [ ] Panel displays trust tier with badge and tier history if available
- [ ] Panel shows recent workflow activity (last 5 runs with status)
- [ ] Panel shows current queue depth
- [ ] Panel loads in under 200ms (HTMX partial fetch)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_clicking_repo_row_opens_detail_panel` -- Clicking a repo row opens the detail panel with that repo's information
2. `test_ac2_panel_shows_repo_name_status_badge` -- Panel shows repo name and current status badge in the header
3. `test_ac3_panel_displays_trust_tier_badge_history` -- Panel displays trust tier with badge and tier history if available
4. `test_ac4_panel_shows_recent_workflow_activity` -- Panel shows recent workflow activity (last 5 runs with status)
5. `test_ac5_panel_shows_current_queue_depth` -- Panel shows current queue depth
6. `test_ac6_panel_loads_under_200ms` -- Panel loads in under 200ms (HTMX partial fetch)

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Repo detail endpoint should reuse existing repo data fetching logic from the repos page
- Trust tier history can be rendered as a simple timeline with dates and tier changes
- Queue depth should show both current count and trend indicator if data is available

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 75.2 (detail panel infrastructure)

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
