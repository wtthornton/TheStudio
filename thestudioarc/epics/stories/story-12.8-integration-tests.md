# Story 12.8 -- Integration Tests & E2E Validation

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** comprehensive test coverage for the entire settings feature, **so that** we can ship with confidence that settings CRUD, encryption, RBAC, audit, and UI all work correctly

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Write integration tests that exercise the full settings stack: API endpoints with real DB, encryption round-trips, RBAC enforcement with different roles, audit log verification, hot reload propagation to ModelRouter, and UI template rendering for all 5 settings sections.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `tests/admin/test_settings_integration.py`
- `tests/conftest.py` (new fixtures for settings test users)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create test fixtures for admin/operator/viewer users with appropriate roles (`tests/conftest.py`)
- [ ] Integration test: settings CRUD through API with real DB (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: encryption round-trip — set encrypted, read decrypted (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: RBAC enforcement — admin allowed, operator denied, viewer denied (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: audit log entries created with correct event type and masked values (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: hot reload propagation to ModelRouter (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: UI renders all 5 settings card partials without errors (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: validation rejects invalid values with 422 (`tests/admin/test_settings_integration.py`)
- [ ] Integration test: encryption key rotation re-encrypts all secrets (`tests/admin/test_settings_integration.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] All settings CRUD operations work end-to-end with PostgreSQL
- [ ] Encrypted values survive a write-read cycle correctly
- [ ] Non-admin roles receive 403 on all settings endpoints
- [ ] Audit log contains entries for every settings mutation
- [ ] Hot reload test confirms ModelRouter picks up new provider config
- [ ] All 5 UI partials render without errors
- [ ] Invalid input returns 422 with descriptive error messages

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_e2e_create_read_update_delete` — full CRUD lifecycle through API with real async DB session
2. `test_e2e_encryption_roundtrip` — PUT encrypted key, GET returns decrypted value, DB row contains ciphertext
3. `test_e2e_rbac_admin_allowed` — admin user can GET, PUT, DELETE settings
4. `test_e2e_rbac_operator_denied` — operator user gets 403 on PUT and DELETE
5. `test_e2e_rbac_viewer_denied` — viewer user gets 403 on all settings endpoints
6. `test_e2e_audit_log_on_update` — PUT creates audit entry with SETTINGS_CHANGED type
7. `test_e2e_audit_log_masks_secret` — audit entry for API key change contains masked value, not plaintext
8. `test_e2e_hot_reload_model_router` — PUT agent_model, verify ModelRouter.select_model returns new provider
9. `test_e2e_hot_reload_feature_flag` — toggle llm_provider, verify next feature flag read returns new value
10. `test_e2e_ui_api_keys_partial` — GET /admin/ui/partials/settings/api-keys returns 200 with expected HTML
11. `test_e2e_ui_infrastructure_partial` — GET infrastructure partial returns 200
12. `test_e2e_ui_feature_flags_partial` — GET feature flags partial returns 200
13. `test_e2e_ui_agent_config_partial` — GET agent config partial returns 200
14. `test_e2e_ui_secrets_partial` — GET secrets partial returns 200
15. `test_e2e_validation_bad_url` — PUT database_url with "not-a-url" returns 422
16. `test_e2e_validation_negative_budget` — PUT agent_max_budget_usd with -1.0 returns 422
17. `test_e2e_validation_zero_max_turns` — PUT agent_max_turns with 0 returns 422
18. `test_e2e_key_rotation_reencrypts` — rotate encryption key, verify all encrypted settings readable with new key

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `pytest-asyncio` with real async DB session (transaction rollback pattern for isolation)
- Use `httpx.AsyncClient` with the FastAPI test app for API tests
- Create test fixtures for admin/operator/viewer users with appropriate `X-User-ID` headers
- Use a separate test database or wrap each test in a rolled-back transaction
- UI partial tests only verify HTTP 200 and presence of key HTML elements (not visual rendering)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Stories 12.1 through 12.7 (all prior stories must be complete)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on all prior stories (by design — this is the integration layer)
- [x] **N**egotiable -- Test scope and fixtures can be refined
- [x] **V**aluable -- Provides confidence to ship the entire settings feature
- [x] **E**stimable -- 18 test cases across known patterns
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 18 specific test cases defined; meta-testable via CI green/red

<!-- docsmcp:end:invest -->
