# Story 12.5 -- Infrastructure & Feature Flags Section

<!-- docsmcp:start:user-story -->

> **As a** platform operator, **I want** to view and edit infrastructure connections and toggle feature flags from the UI, **so that** I can reconfigure connections and switch providers without redeploying

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Build two UI cards: Infrastructure (database_url, temporal_host, temporal_namespace, temporal_task_queue, nats_url, otel_service_name, otel_exporter, otel_otlp_endpoint) and Feature Flags (llm_provider toggle between mock/anthropic, github_provider toggle between mock/real, store_backend selector for memory/postgres). Include URL validation and toggle switches.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `src/admin/templates/partials/settings_infrastructure.html`
- `src/admin/templates/partials/settings_feature_flags.html`
- `src/admin/ui_router.py`
- `src/admin/settings_service.py`
- `tests/admin/test_settings_infra_ui.py`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `settings_infrastructure.html` partial with editable fields and source badges (`src/admin/templates/partials/settings_infrastructure.html`)
- [ ] Create `settings_feature_flags.html` partial with Tailwind toggle switches (`src/admin/templates/partials/settings_feature_flags.html`)
- [ ] Add GET/POST routes for infrastructure partial (`src/admin/ui_router.py`)
- [ ] Add GET/POST routes for feature flags partial (`src/admin/ui_router.py`)
- [ ] Add URL format validation for connection strings in SettingsService (`src/admin/settings_service.py`)
- [ ] Write tests for infrastructure and feature flag UI (`tests/admin/test_settings_infra_ui.py`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Infrastructure card shows all connection settings with current values
- [ ] Database URL is masked (it contains credentials) with reveal toggle
- [ ] Temporal and NATS URLs validate as proper host:port or URL format
- [ ] Feature Flags card shows toggle switches for each provider flag
- [ ] Toggle switches update immediately via HTMX with visual feedback
- [ ] Invalid URL values show inline validation error without submitting
- [ ] Current source (db override vs env default) is indicated per setting with a badge

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_infrastructure_card_shows_all_fields` — partial contains inputs for all 8 infrastructure settings
2. `test_infrastructure_database_url_masked` — database_url displays masked (contains password)
3. `test_infrastructure_source_badge_env` — unoverridden setting shows "env" badge
4. `test_infrastructure_source_badge_db` — overridden setting shows "db" badge
5. `test_infrastructure_valid_url_accepted` — POST with valid postgresql+asyncpg URL succeeds
6. `test_infrastructure_invalid_url_rejected` — POST with "not-a-url" returns inline error
7. `test_infrastructure_temporal_host_validates` — host:port format accepted, random string rejected
8. `test_feature_flags_shows_toggles` — partial contains toggle switches for llm_provider, github_provider, store_backend
9. `test_feature_flags_toggle_updates` — toggling llm_provider from mock to anthropic persists and re-renders
10. `test_feature_flags_store_backend_selector` — dropdown with memory/postgres options renders correctly

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use Tailwind toggle switch component for feature flags (checkbox styled as switch)
- `database_url` should be treated as sensitive (contains password) — same masking as API keys
- Validate URLs with `urllib.parse.urlparse` before accepting
- Show env vs db source with a small colored badge next to each field: blue="env" green="db"
- Infrastructure settings should show a warning that changes require restart (wired in Story 12.7)

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 12.3 (Settings UI Layout — provides card container)
- Story 12.2 (Settings API — provides data endpoints)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Self-contained cards; parallelizable with 12.4 and 12.6
- [x] **N**egotiable -- Toggle vs dropdown, validation strictness can be adjusted
- [x] **V**aluable -- Enables provider switching and connection reconfiguration via UI
- [x] **E**stimable -- 2 templates + 4 routes + validation logic + tests
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 10 specific test cases defined

<!-- docsmcp:end:invest -->
