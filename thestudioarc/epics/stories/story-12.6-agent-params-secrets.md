# Story 12.6 -- Agent Parameters & Secrets Section

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to tune agent parameters and rotate secrets through the UI, **so that** I can adjust agent behavior and rotate credentials without downtime

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Build two UI cards: Agent Config (agent_model dropdown populated from ModelRouter providers, agent_max_turns number input, agent_max_budget_usd currency input, agent_max_loopbacks number input) and Secrets (encryption_key rotation with double-confirmation, webhook_secret regeneration with copy-to-clipboard). Secrets card includes safety warnings.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/settings_agent_config.html`
- `src/admin/templates/partials/settings_secrets.html`
- `src/admin/ui_router.py`
- `src/admin/settings_service.py`
- `tests/admin/test_settings_agent_secrets_ui.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `settings_agent_config.html` partial with model dropdown and number inputs (`src/admin/templates/partials/settings_agent_config.html`)
- [ ] Create `settings_secrets.html` partial with rotation controls and safety warnings (`src/admin/templates/partials/settings_secrets.html`)
- [ ] Add GET/POST routes for agent config partial (`src/admin/ui_router.py`)
- [ ] Add GET/POST routes for secrets partial (rotation endpoints) (`src/admin/ui_router.py`)
- [ ] Implement encryption key rotation logic (re-encrypt all stored secrets in a single transaction) (`src/admin/settings_service.py`)
- [ ] Implement webhook secret regeneration with `secrets.token_urlsafe(32)` (`src/admin/settings_service.py`)
- [ ] Write tests for agent config and secrets UI (`tests/admin/test_settings_agent_secrets_ui.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Agent Config card shows model dropdown populated from available providers
- [ ] Max turns / budget / loopbacks have number inputs with min/max validation
- [ ] Budget input validates as positive float with max cap
- [ ] Secrets card shows encryption key status (set/not set) without revealing value
- [ ] Encryption key rotation requires typing "ROTATE" to confirm
- [ ] Webhook secret regeneration shows the new secret once with copy button, then masks it
- [ ] All changes are audit-logged

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_agent_config_model_dropdown_populated` — dropdown contains options from ModelRouter.providers (haiku, sonnet, opus)
2. `test_agent_config_max_turns_validates_range` — accepts 1-100, rejects 0 and 101
3. `test_agent_config_budget_validates_positive` — accepts 0.01-100.0, rejects negative and zero
4. `test_agent_config_loopbacks_validates_range` — accepts 0-10, rejects negative
5. `test_agent_config_save_persists` — POST with valid values updates settings and re-renders
6. `test_secrets_encryption_key_status_shown` — card shows "Configured" badge without revealing key
7. `test_secrets_rotation_requires_confirmation` — POST without "ROTATE" confirmation text is rejected
8. `test_secrets_rotation_reencrypts_all` — after rotation, all encrypted settings are re-encrypted with new key
9. `test_secrets_rotation_atomic` — if re-encryption fails mid-way, transaction rolls back (no partial re-encryption)
10. `test_secrets_webhook_regenerate` — POST generates new secret, response contains the plaintext once
11. `test_secrets_webhook_copy_button` — response HTML contains clipboard copy button
12. `test_secrets_changes_audit_logged` — rotation and regeneration create audit entries

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Model dropdown should call `ModelRouter.providers` to enumerate options dynamically
- Encryption key rotation must re-encrypt all existing encrypted settings atomically in a single DB transaction; fail-closed on any error
- Use `secrets.token_urlsafe(32)` for webhook secret generation
- Copy-to-clipboard uses `navigator.clipboard.writeText()` with fallback to a `<textarea>` select-and-copy
- Confirmation for rotation: require user to type "ROTATE" in an input field (not just a confirm dialog) for extra safety

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.3 (Settings UI Layout — provides card container)
- Story 12.1 (Settings Data Model — needed for re-encryption logic)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Self-contained cards; parallelizable with 12.4 and 12.5
- [x] **N**egotiable -- Confirmation UX and validation ranges can be adjusted
- [x] **V**aluable -- Enables agent tuning and credential rotation without downtime
- [x] **E**stimable -- 2 templates + 4 routes + 2 service methods + tests
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 12 specific test cases defined

<!-- docsmcp:end:invest -->
