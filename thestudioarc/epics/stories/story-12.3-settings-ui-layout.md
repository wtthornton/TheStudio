# Story 12.3 -- Settings UI Page — Layout & Navigation

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** a Settings page in the Admin Console with organized sections, **so that** I can navigate to settings and see all configurable parameters grouped logically

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Add a Settings entry to the Admin UI sidebar navigation in `base.html`. Create the `settings.html` full-page template with five sectioned cards (API Keys, Infrastructure, Feature Flags, Agent Config, Secrets). Each card loads its content via HTMX partials. Only visible to admin role users.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/base.html`
- `src/admin/templates/settings.html`
- `src/admin/templates/partials/settings_content.html`
- `src/admin/ui_router.py`
- `tests/admin/test_settings_ui.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add Settings link to sidebar in `base.html` (admin-only, same pattern as Audit Log) (`src/admin/templates/base.html`)
- [ ] Create `settings.html` full-page template extending `base.html` with page_title "Settings" (`src/admin/templates/settings.html`)
- [ ] Create `settings_content.html` partial with 5 card containers, each using `hx-get` and `hx-trigger="load"` (`src/admin/templates/partials/settings_content.html`)
- [ ] Add `/admin/ui/settings` full page route to `ui_router.py` with admin role check (`src/admin/ui_router.py`)
- [ ] Add `/admin/ui/partials/settings` partial route to `ui_router.py` (`src/admin/ui_router.py`)
- [ ] Write render tests for settings page and partial (`tests/admin/test_settings_ui.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Settings link appears in sidebar for admin users only
- [ ] Settings page renders at /admin/ui/settings with correct `active_page` highlight
- [ ] Page shows 5 card sections with HTMX loading indicators
- [ ] HTMX partials load content for each section on page load
- [ ] Non-admin users do not see the Settings sidebar entry

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_settings_page_renders_for_admin` — admin user gets 200 with settings.html content
2. `test_settings_page_hidden_from_operator` — operator user does not see Settings in sidebar HTML
3. `test_settings_page_hidden_from_viewer` — viewer user does not see Settings in sidebar HTML
4. `test_settings_partial_renders_five_cards` — partial response contains 5 card container divs
5. `test_settings_sidebar_active_highlight` — active_page="settings" produces correct CSS class
6. `test_settings_cards_have_htmx_triggers` — each card div contains hx-get and hx-trigger="load"

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Follow existing `base.html` sidebar pattern — see Audit Log entry for admin-only Jinja2 conditional
- Use HTMX `hx-get` with `hx-trigger="load"` for each card section
- Match existing Tailwind card styling from dashboard and other admin pages
- Each card should have a loading spinner (htmx-indicator pattern already in base.html CSS)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.2 (Settings API Endpoints — needed for partials to call)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Only depends on 12.2 for data; UI layout can be stubbed
- [x] **N**egotiable -- Card layout and grouping can be adjusted
- [x] **V**aluable -- Provides the navigation entry point for all settings management
- [x] **E**stimable -- Template + 2 routes + 1 test file
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 6 specific test cases defined

<!-- docsmcp:end:invest -->
