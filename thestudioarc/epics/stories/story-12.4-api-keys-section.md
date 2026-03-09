# Story 12.4 -- API Keys Section — Masked Display & Update

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to view and update API keys through the UI with masked display for security, **so that** I can rotate API keys without server access while keeping secrets hidden from shoulder-surfers

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Build the API Keys card UI component showing Anthropic API Key, GitHub App ID, and GitHub Private Key Path. Keys display masked (last 4 chars visible). Each has an Edit button that reveals an inline form with save/cancel. Saving triggers a confirmation dialog. Updates flow through the settings API with HTMX swap.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/settings_api_keys.html`
- `src/admin/ui_router.py`
- `tests/admin/test_settings_api_keys_ui.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `settings_api_keys.html` partial with masked display for each key (`src/admin/templates/partials/settings_api_keys.html`)
- [ ] Add inline edit form with save/cancel buttons using HTMX (`src/admin/templates/partials/settings_api_keys.html`)
- [ ] Add reveal/hide toggle for masked values (`src/admin/templates/partials/settings_api_keys.html`)
- [ ] Add confirmation dialog before saving API key changes using `hx-confirm` (`src/admin/templates/partials/settings_api_keys.html`)
- [ ] Add `/admin/ui/partials/settings/api-keys` GET route (`src/admin/ui_router.py`)
- [ ] Add `/admin/ui/partials/settings/api-keys` POST route for updates (`src/admin/ui_router.py`)
- [ ] Add `/admin/ui/partials/settings/api-keys/reveal/{key}` GET route for unmasked value (`src/admin/ui_router.py`)
- [ ] Write UI rendering and update tests (`tests/admin/test_settings_api_keys_ui.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] API Keys card shows Anthropic API Key / GitHub App ID / GitHub Private Key Path
- [ ] Values display masked by default showing only last 4 characters
- [ ] Reveal toggle shows full value (fetched from API) and hides again
- [ ] Edit button opens inline form with current value pre-filled (masked)
- [ ] Save button shows confirmation dialog before submitting
- [ ] Successful save shows green flash message and re-renders the card
- [ ] Cancel button restores the masked display without changes

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_api_keys_card_renders_three_keys` — partial contains fields for anthropic_api_key, github_app_id, github_private_key_path
2. `test_api_keys_masked_by_default` — response HTML shows asterisks with only last 4 chars visible
3. `test_api_keys_reveal_returns_full_value` — GET reveal endpoint returns unmasked value for admin
4. `test_api_keys_reveal_denied_for_non_admin` — GET reveal returns 403 for non-admin
5. `test_api_keys_edit_form_renders` — clicking edit shows input field with save/cancel buttons
6. `test_api_keys_save_with_confirmation` — POST updates the key and re-renders card with success message
7. `test_api_keys_cancel_restores_display` — cancel returns to masked display without mutation
8. `test_api_keys_empty_value_shows_not_set` — key with no value shows "Not configured" badge

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `hx-confirm="Are you sure you want to update this API key?"` for the confirmation dialog
- Use `hx-swap="outerHTML"` on the card div for seamless update after save
- Mask helper: `"*" * max(len(value) - 4, 4) + value[-4:]` or "Not configured" if empty
- Reveal toggle should fetch the real value via a separate authenticated GET endpoint (logged for security)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.3 (Settings UI Layout — provides the page and card container)
- Story 12.2 (Settings API — provides the data endpoints)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- One self-contained card; parallelizable with 12.5 and 12.6
- [x] **N**egotiable -- Mask format and confirmation UX can be refined
- [x] **V**aluable -- Directly enables API key rotation without SSH
- [x] **E**stimable -- 1 template + 3 routes + tests
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 8 specific test cases defined

<!-- docsmcp:end:invest -->
