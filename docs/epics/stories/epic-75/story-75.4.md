# Story 75.4 -- Workflow Detail Panel — Click-to-Inspect Workflows

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to click a workflow row and see its execution details in a sliding panel, **so that** I can quickly triage workflow status, view step outputs, and see logs without navigating away

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can inspect workflow execution details — status timeline, step outputs, logs — by clicking a workflow row or kanban card, enabling fast triage without page navigation.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Wire workflow table rows (and later kanban cards from Story 75.5) to open the sliding detail panel showing workflow execution details: status timeline with step progression, individual step outputs, execution logs, and retry action buttons.

See [Epic 75](../../epic-75-plane-parity-admin-ui.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/workflow_detail.html`
- `src/admin/routes.py`
- `src/admin/templates/workflows.html`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create workflow detail partial template with sections: header (workflow ID + status), status timeline (step-by-step progression), step outputs, execution log snippet (`src/admin/templates/partials/workflow_detail.html`)
- [ ] Add HTMX endpoint GET /admin/ui/partials/workflow/{workflow_id}/detail that returns the workflow detail partial (`src/admin/routes.py`)
- [ ] Wire workflow table rows with hx-get pointing to workflow detail endpoint, targeting the detail panel (`src/admin/templates/workflows.html`)
- [ ] Add visual status timeline component showing pipeline steps with pass/fail/pending states (`src/admin/templates/partials/workflow_detail.html`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Clicking a workflow row opens the detail panel with that workflow's information
- [ ] Panel shows workflow ID and current status badge in the header
- [ ] Panel displays a visual status timeline showing each pipeline step with its state
- [ ] Panel shows step outputs for completed steps
- [ ] Panel shows recent execution log entries
- [ ] Panel loads in under 200ms (HTMX partial fetch)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 75](../../epic-75-plane-parity-admin-ui.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_clicking_workflow_row_opens_detail_panel` -- Clicking a workflow row opens the detail panel with that workflow's information
2. `test_ac2_panel_shows_workflow_id_status_badge` -- Panel shows workflow ID and current status badge in the header
3. `test_ac3_panel_displays_visual_status_timeline` -- Panel displays a visual status timeline showing each pipeline step with its state
4. `test_ac4_panel_shows_step_outputs` -- Panel shows step outputs for completed steps
5. `test_ac5_panel_shows_execution_log_entries` -- Panel shows recent execution log entries
6. `test_ac6_panel_loads_under_200ms` -- Panel loads in under 200ms (HTMX partial fetch)

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Status timeline maps to the 9-step pipeline: Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish
- Each step should show: name, status (pass/fail/pending/skipped), duration if completed
- Execution logs should show the most recent 20 lines with a "Show more" link

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
