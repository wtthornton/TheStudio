# Story 12.7 -- Hot Reload & Settings Propagation

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** settings changes to take effect immediately without restarting the application, **so that** I can change configuration in production without downtime

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Implement a settings reload mechanism. When a setting is updated via the API, the SettingsService publishes a reload signal. Consumers (ModelRouter, feature flag checks, adapter configs) subscribe to this signal and refresh their state. For safety, infrastructure settings (DB URL, Temporal host, NATS URL) are marked as restart-required and show a warning banner instead of hot-reloading.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/settings_service.py`
- `src/admin/model_gateway.py`
- `src/settings.py`
- `src/admin/templates/partials/settings_infrastructure.html`
- `tests/admin/test_settings_hot_reload.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `SettingsReloadSignal` event and in-process subscriber registry to SettingsService (`src/admin/settings_service.py`)
- [ ] Define `RESTART_REQUIRED_KEYS` frozenset (database_url, temporal_host, nats_url) (`src/admin/settings_service.py`)
- [ ] Wire ModelRouter to subscribe and reload provider configs on signal (`src/admin/model_gateway.py`)
- [ ] Wire feature flag checks to read from SettingsService instead of env-only (`src/settings.py`)
- [ ] Show restart-required warning banner in infrastructure partial when infra settings have pending changes (`src/admin/templates/partials/settings_infrastructure.html`)
- [ ] Add generation counter to SettingsService to prevent stale-read race conditions (`src/admin/settings_service.py`)
- [ ] Write tests for hot reload propagation (`tests/admin/test_settings_hot_reload.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Changing `agent_model` via UI immediately affects next `ModelRouter.select_model()` call
- [ ] Toggling `llm_provider` flag takes effect without restart
- [ ] Changing `database_url` shows a restart-required warning banner instead of hot-reloading
- [ ] Settings reload does not interrupt in-flight requests
- [ ] Reload signal is logged for observability
- [ ] Generation counter increments on each reload to prevent stale reads

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_reload_signal_fires_on_set` — calling `SettingsService.set()` triggers reload signal
2. `test_model_router_picks_up_new_model` — change agent_model, verify ModelRouter returns updated provider
3. `test_feature_flag_toggle_takes_effect` — toggle llm_provider, verify next read returns new value
4. `test_restart_required_setting_not_hot_reloaded` — change database_url, verify connection pool is NOT recreated
5. `test_restart_required_banner_shown` — change database_url, verify UI partial contains warning banner HTML
6. `test_reload_does_not_interrupt_inflight` — start a mock request, trigger reload mid-flight, verify request completes
7. `test_generation_counter_increments` — verify counter increases on each set() call
8. `test_subscriber_receives_changed_key` — subscriber callback receives the key that changed
9. `test_multiple_subscribers_all_notified` — register 3 subscribers, verify all called on reload
10. `test_reload_signal_logged` — verify reload event appears in application log

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use a simple in-process callback registry (list of callables); no need for external pub/sub
- Infrastructure settings that require restart: `database_url`, `temporal_host`, `nats_url`
- Safe-to-hot-reload: all feature flags, agent params, API keys, OTEL settings
- Generation counter: `int` incremented atomically on each `set()` call; consumers compare their last-seen generation to decide if refresh is needed
- Warning banner: yellow Tailwind alert with message "This setting requires a restart to take effect. Current value will be used until the next restart."

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.1 (Settings Data Model — SettingsService to extend)
- Story 12.2 (Settings API — triggers reload on mutation)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed after 12.1/12.2 without needing UI stories
- [x] **N**egotiable -- Which settings are restart-required can be adjusted
- [x] **V**aluable -- Eliminates restart requirement for most configuration changes
- [x] **E**stimable -- Signal pattern + 3 subscriber integrations + tests
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 10 specific test cases defined

<!-- docsmcp:end:invest -->
