# Story 12.2 -- Settings API Endpoints

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** REST API endpoints to read and update platform settings, **so that** the Settings UI (and future CLI/automation) can manage configuration programmatically

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Add API endpoints under /admin/settings for listing settings by category, getting a single setting, updating a setting, and deleting a setting. All endpoints require admin role via existing RBAC middleware. Every mutation is audit-logged with the setting key and masked before/after values.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/router.py`
- `src/admin/rbac.py`
- `src/admin/audit.py`
- `tests/admin/test_settings_api.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `MANAGE_SETTINGS` to Permission enum in rbac.py (`src/admin/rbac.py`)
- [ ] Add `MANAGE_SETTINGS` to admin role's permission set in `ROLE_PERMISSIONS` (`src/admin/rbac.py`)
- [ ] Create Pydantic request/response models for settings CRUD (`src/admin/router.py`)
- [ ] Implement GET /admin/settings?category= endpoint (`src/admin/router.py`)
- [ ] Implement GET /admin/settings/{key} endpoint with source indicator (`src/admin/router.py`)
- [ ] Implement PUT /admin/settings/{key} endpoint with per-type validation (`src/admin/router.py`)
- [ ] Implement DELETE /admin/settings/{key} endpoint (`src/admin/router.py`)
- [ ] Add audit log entries for all settings mutations (`src/admin/router.py`)
- [ ] Add `SETTINGS_CHANGED` to AuditEventType enum (`src/admin/audit.py`)
- [ ] Write API tests for all endpoints including RBAC denial (`tests/admin/test_settings_api.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] GET /admin/settings?category=api_keys returns masked sensitive values
- [ ] GET /admin/settings/{key} returns the setting with source indicator (db or env)
- [ ] PUT /admin/settings/{key} validates input and persists the change
- [ ] DELETE /admin/settings/{key} removes the DB override (falls back to env)
- [ ] Non-admin users receive 403 on all settings endpoints
- [ ] Every PUT/DELETE creates an audit log entry with SETTINGS_CHANGED event type
- [ ] Invalid values (malformed URLs or negative numbers) return 422 with clear error message

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_list_settings_by_category` — GET with category filter returns only that category's settings
2. `test_list_settings_masks_sensitive` — sensitive values in list response show only last 4 chars
3. `test_get_setting_returns_source_db` — setting overridden in DB shows source="db"
4. `test_get_setting_returns_source_env` — setting from env only shows source="env"
5. `test_get_setting_not_found` — unknown key returns 404
6. `test_update_setting_success` — PUT with valid value returns 200 and persists
7. `test_update_setting_validation_failure_url` — PUT with malformed URL returns 422
8. `test_update_setting_validation_failure_negative` — PUT with negative budget returns 422
9. `test_delete_setting_falls_back` — DELETE removes DB override, GET returns env default
10. `test_rbac_denies_operator` — operator role gets 403 on PUT
11. `test_rbac_denies_viewer` — viewer role gets 403 on GET
12. `test_rbac_allows_admin` — admin role gets 200 on all endpoints
13. `test_audit_log_created_on_update` — PUT creates audit entry with SETTINGS_CHANGED type
14. `test_audit_log_created_on_delete` — DELETE creates audit entry
15. `test_audit_log_masks_sensitive_values` — audit entry for API key change shows masked before/after

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Follow existing `router.py` patterns for endpoint structure and dependency injection
- Use `require_permission(Permission.MANAGE_SETTINGS)` dependency on all endpoints
- Validation should use Pydantic validators per setting type (URL for db_url, positive float for budget, etc.)
- Mask sensitive values in responses: show only last 4 characters prepended with asterisks
- Response model should include `source: Literal["db", "env", "default"]` field

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.1 (Settings Data Model & SettingsService)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Only depends on 12.1 (data model)
- [x] **N**egotiable -- Endpoint paths and response shapes can be refined
- [x] **V**aluable -- Enables UI and future CLI/automation access to settings
- [x] **E**stimable -- Standard CRUD pattern with known scope
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 15 specific test cases defined

<!-- docsmcp:end:invest -->
