# Story 12.1 -- Settings Data Model & Encrypted Storage

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** settings persisted in the database with encryption for sensitive values, **so that** configuration survives container restarts and secrets are protected at rest

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Create a SQLAlchemy model for key-value settings storage where sensitive values (API keys, secrets) are Fernet-encrypted at rest. Build a SettingsService that implements a layered config pattern: DB values override environment variable defaults from `src/settings.py`. Include an Alembic migration for the settings table.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/persistence/pg_settings.py`
- `src/admin/settings_crypto.py`
- `src/admin/settings_service.py`
- `src/db/migrations/` (new Alembic migration)
- `tests/admin/test_settings_service.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `SettingRow` SQLAlchemy model (key, value, encrypted bool, category, updated_at, updated_by) (`src/admin/persistence/pg_settings.py`)
- [ ] Implement Fernet encrypt/decrypt helpers using `THESTUDIO_ENCRYPTION_KEY` (`src/admin/settings_crypto.py`)
- [ ] Create `SettingsService` with get/set/list/delete methods and layered config resolution (`src/admin/settings_service.py`)
- [ ] Define `SettingCategory` enum (api_keys, infrastructure, feature_flags, agent_config, secrets) (`src/admin/settings_service.py`)
- [ ] Define `SENSITIVE_KEYS` registry constant listing which settings keys require encryption (`src/admin/settings_service.py`)
- [ ] Add Alembic migration for settings table (`src/db/migrations/`)
- [ ] Write unit tests for crypto helpers and SettingsService (`tests/admin/test_settings_service.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Settings table created with key/value/encrypted/category/updated_at/updated_by columns
- [ ] Sensitive values are Fernet-encrypted before storage and decrypted on read
- [ ] `SettingsService.get()` returns DB value if present, else falls back to env var default
- [ ] `SettingsService.set()` persists to DB and records who made the change
- [ ] `SettingsService.list()` returns all settings in a category with masked sensitive values
- [ ] Alembic migration runs cleanly up and down

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_encrypt_decrypt_roundtrip` — verify Fernet encrypt then decrypt returns original value
2. `test_encrypt_uses_fernet_key` — verify encryption uses `THESTUDIO_ENCRYPTION_KEY`, not a hardcoded key
3. `test_get_returns_db_override` — set a value in DB, verify `get()` returns it over env default
4. `test_get_falls_back_to_env_default` — no DB value, verify `get()` returns env var value
5. `test_get_nonexistent_key_returns_none` — unknown key with no env default returns None
6. `test_set_persists_and_encrypts_sensitive` — set a sensitive key, verify DB row has encrypted=True and value is ciphertext
7. `test_set_non_sensitive_stores_plaintext` — set a non-sensitive key, verify DB row has encrypted=False
8. `test_list_masks_sensitive_values` — list api_keys category, verify sensitive values show only last 4 chars
9. `test_list_shows_non_sensitive_in_full` — list feature_flags category, verify full values returned
10. `test_delete_removes_setting` — delete a key, verify `get()` falls back to env default
11. `test_set_records_updated_by` — verify `updated_by` column is populated with the actor
12. `test_migration_up_down` — run migration up, verify table exists; run down, verify table dropped

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `cryptography.fernet.Fernet` with `THESTUDIO_ENCRYPTION_KEY` as the key
- Store category as a PostgreSQL enum type
- Layer pattern: `SettingsService` wraps `Settings` (pydantic-settings) and checks DB first
- Mark which settings keys are sensitive in a `SENSITIVE_KEYS` frozenset constant
- Follow existing persistence pattern in `src/admin/persistence/pg_compliance.py`

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- `cryptography` package (already in project deps)
- `src/db/connection.py` (async session factory)
- `src/settings.py` (env var defaults to fall back to)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No upstream story dependency; can be developed first
- [x] **N**egotiable -- Column schema and encryption approach can be refined
- [x] **V**aluable -- Enables all downstream stories (API, UI, hot reload)
- [x] **E**stimable -- Well-scoped: 1 model, 1 service, 1 migration, 1 test file
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 12 specific test cases defined

<!-- docsmcp:end:invest -->
