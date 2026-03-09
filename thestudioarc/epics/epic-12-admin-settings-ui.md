# Epic 12: Admin Settings & Configuration UI

<!-- docsmcp:start:metadata -->
**Status:** Complete
**Priority:** P1 - High
**Estimated LOE:** ~2-3 weeks (1 developer)
**Dependencies:** Epic 4 (Admin UI Foundation) — Complete, Epic 11 (Gateway Enforcement) — Complete
**Owner:** Platform Team
**Reviewers:** Security Lead, Meridian (VP Success)

<!-- docsmcp:end:metadata -->

---

## References

- **OKR:** Operational maturity — reduce MTTR for configuration changes from "redeploy required" to "UI click"
- **Roadmap:** [`thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`](../MERIDIAN-ROADMAP-AGGRESSIVE.md)
- **Architecture:** [`thestudioarc/23-admin-control-ui.md`](../23-admin-control-ui.md) — Admin UI architecture and modules
- **Settings source:** [`src/settings.py`](../../src/settings.py) — current env-var-only configuration
- **Existing Admin UI:** [`src/admin/ui_router.py`](../../src/admin/ui_router.py) — 12 pages, HTMX + Tailwind + Jinja2

---

<!-- docsmcp:start:goal -->
## Goal

Add a Settings page to the Admin UI that allows operators to view, update, and manage API keys, infrastructure connections, feature flags, agent parameters, and secrets — all through a polished, secure web interface with RBAC enforcement and full audit logging.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Today all TheStudio configuration lives in environment variables (`src/settings.py`). Operators must SSH into servers or redeploy containers to change an API key, toggle a feature flag, or tune agent parameters. This creates operational friction, increases mean-time-to-recover, and prevents non-developer operators from managing the platform. A Settings UI closes this gap, making TheStudio self-service and operationally mature.

<!-- docsmcp:end:motivation -->

## Stakeholders

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Team Lead | Scope decisions, story acceptance |
| Security Reviewer | Security Lead | Review encryption design, secret handling, RBAC |
| UX Reviewer | Product/Design | Review UI layout, interaction patterns |
| QA | QA Lead | Integration test plan, E2E validation |

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Settings configurable via UI | 100% of `src/settings.py` fields | Manual audit: every field has a UI control |
| MTTR for API key rotation | < 2 minutes (down from ~15 min redeploy) | Time from "key compromised" to "new key active" |
| Zero plaintext secrets in DB | 100% of sensitive values encrypted | Query: `SELECT count(*) FROM settings WHERE encrypted = false AND key IN (sensitive_keys)` = 0 |
| Audit coverage | 100% of mutations logged | Integration test: every PUT/DELETE produces an audit entry |
| Admin-only enforcement | 0 non-admin access | Test: operator and viewer roles get 403 on all settings endpoints |

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Settings page accessible at /admin/ui/settings with sidebar navigation entry
- [ ] API keys (Anthropic and GitHub) can be viewed (masked) and updated through the UI
- [ ] Infrastructure connection strings (DB / Temporal / NATS) are viewable and editable
- [ ] Feature flags (LLM provider / GitHub provider / store backend) can be toggled
- [ ] Agent parameters (model / max turns / budget / loopbacks) can be tuned
- [ ] Secrets (encryption key / webhook secret) can be rotated with confirmation
- [ ] All settings changes require admin role (RBAC enforced)
- [ ] Every settings change is recorded in the audit log with before/after values
- [ ] Settings are persisted to the database and override environment variable defaults
- [ ] Sensitive values are encrypted at rest using the existing Fernet encryption key
- [ ] Settings changes take effect without container restart (hot reload) for safe settings; restart-required banner for infrastructure settings
- [ ] Validation prevents invalid values (e.g. malformed URLs / negative budgets)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 12.1 -- Settings Data Model & Encrypted Storage

**Points:** 5 | [Full story](stories/story-12.1-settings-data-model.md)

Create the database model for persisted settings with Fernet encryption for sensitive values, migration, and a SettingsService that layers DB values over env var defaults.

**Key tasks:**
- [ ] Create `SettingRow` SQLAlchemy model with key/value/encrypted/category/updated_at/updated_by columns (`src/admin/persistence/pg_settings.py`)
- [ ] Implement Fernet encrypt/decrypt helpers (`src/admin/settings_crypto.py`)
- [ ] Create `SettingsService` with get/set/list/delete and layered config resolution (`src/admin/settings_service.py`)
- [ ] Define `SettingCategory` enum: api_keys, infrastructure, feature_flags, agent_config, secrets (`src/admin/settings_service.py`)
- [ ] Add Alembic migration for settings table (`src/db/migrations/`)
- [ ] Write unit tests for crypto helpers and SettingsService (`tests/admin/test_settings_service.py`)

---

### 12.2 -- Settings API Endpoints

**Points:** 5 | [Full story](stories/story-12.2-settings-api-endpoints.md)

Add CRUD API endpoints under /admin/settings for reading and updating settings, with RBAC enforcement (admin-only), input validation, and audit log integration.

**Key tasks:**
- [ ] Add `MANAGE_SETTINGS` to Permission enum (`src/admin/rbac.py`)
- [ ] Add `SETTINGS_CHANGED` to AuditEventType enum (`src/admin/audit.py`)
- [ ] Implement GET /admin/settings?category= and GET /admin/settings/{key} (`src/admin/router.py`)
- [ ] Implement PUT /admin/settings/{key} with validation (`src/admin/router.py`)
- [ ] Implement DELETE /admin/settings/{key} (`src/admin/router.py`)
- [ ] Write API tests including RBAC denial (`tests/admin/test_settings_api.py`)

---

### 12.3 -- Settings UI Page — Layout & Navigation

**Points:** 3 | [Full story](stories/story-12.3-settings-ui-layout.md)

Add Settings page to the Admin UI sidebar, create the settings.html template with sectioned cards (API Keys, Infrastructure, Feature Flags, Agent Config, Secrets), and wire up HTMX partials.

**Key tasks:**
- [ ] Add Settings link to sidebar in `base.html` (admin-only, like Audit Log)
- [ ] Create `settings.html` full-page template extending base.html
- [ ] Create `settings_content.html` partial with 5 card placeholders using hx-get + hx-trigger=load
- [ ] Add /admin/ui/settings and /admin/ui/partials/settings routes (`src/admin/ui_router.py`)

---

### 12.4 -- API Keys Section — Masked Display & Update

**Points:** 3 | [Full story](stories/story-12.4-api-keys-section.md)

Build the API Keys card with masked display (show last 4 chars), reveal toggle, inline edit with save/cancel, and confirmation dialog for changes. Covers Anthropic API key, GitHub App ID, and GitHub private key path.

**Key tasks:**
- [ ] Create `settings_api_keys.html` partial with masked display, reveal toggle, inline edit form
- [ ] Add confirmation dialog (hx-confirm) before saving
- [ ] Add GET/POST routes for /admin/ui/partials/settings/api-keys (`src/admin/ui_router.py`)

---

### 12.5 -- Infrastructure & Feature Flags Section

**Points:** 3 | [Full story](stories/story-12.5-infrastructure-feature-flags.md)

Build the Infrastructure card (DB URL, Temporal host, NATS URL, OTEL settings) and Feature Flags card (LLM provider toggle, GitHub provider toggle, store backend selector) with validation and live update.

**Key tasks:**
- [ ] Create `settings_infrastructure.html` partial with editable fields and source badges (env vs db)
- [ ] Create `settings_feature_flags.html` partial with Tailwind toggle switches
- [ ] Add URL format validation for connection strings (`src/admin/settings_service.py`)
- [ ] Add GET/POST routes for both partials (`src/admin/ui_router.py`)

---

### 12.6 -- Agent Parameters & Secrets Section

**Points:** 3 | [Full story](stories/story-12.6-agent-params-secrets.md)

Build the Agent Config card (model selector, max turns, budget, loopbacks) and Secrets card (encryption key rotation with double-confirm, webhook secret regeneration) with safety guards.

**Key tasks:**
- [ ] Create `settings_agent_config.html` partial with model dropdown (from ModelRouter.providers) and number inputs
- [ ] Create `settings_secrets.html` partial with rotation controls, safety warnings, and copy-to-clipboard
- [ ] Implement encryption key rotation logic (re-encrypt all stored secrets atomically) (`src/admin/settings_service.py`)
- [ ] Implement webhook secret regeneration with `secrets.token_urlsafe(32)` (`src/admin/settings_service.py`)

---

### 12.7 -- Hot Reload & Settings Propagation

**Points:** 3 | [Full story](stories/story-12.7-hot-reload.md)

Implement a settings reload mechanism so that updated values propagate to running services (ModelRouter, adapters, feature flags) without requiring a container restart. Infrastructure settings (DB URL, Temporal, NATS) show a restart-required banner.

**Key tasks:**
- [ ] Add `SettingsReloadSignal` event and in-process subscriber registry (`src/admin/settings_service.py`)
- [ ] Wire ModelRouter to reload provider configs on signal (`src/admin/model_gateway.py`)
- [ ] Wire feature flag checks to read from SettingsService (`src/settings.py`)
- [ ] Mark infrastructure settings as restart-required; show banner in UI

---

### 12.8 -- Integration Tests & E2E Validation

**Points:** 3 | [Full story](stories/story-12.8-integration-tests.md)

Write integration tests covering: settings CRUD with real DB, encryption round-trip, RBAC enforcement, audit logging, hot reload propagation, UI rendering of all 5 sections, and input validation.

**Key tasks:**
- [ ] Integration test: CRUD through API with PostgreSQL
- [ ] Integration test: encryption round-trip (set encrypted, read decrypted)
- [ ] Integration test: RBAC enforcement (admin allowed, operator/viewer denied)
- [ ] Integration test: audit log entries with correct event type and masked values
- [ ] Integration test: hot reload propagation to ModelRouter
- [ ] Integration test: all 5 UI partials render without errors
- [ ] Integration test: validation rejects invalid values

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Sensitive values must be Fernet-encrypted at rest using `THESTUDIO_ENCRYPTION_KEY`
- Settings service implements a layered config pattern: DB overrides > env vars > defaults
- Use existing RBAC Permission enum — add `MANAGE_SETTINGS` permission for admin-only access
- Audit log entries for settings changes must include setting key and masked before/after values
- HTMX partials pattern matches existing Admin UI architecture (`ui_router.py`)
- Model selector should enumerate providers from `ModelRouter.providers`
- Settings export/import for backup and environment promotion is a future consideration

**Key Dependencies:** fastapi, sqlalchemy[asyncio], asyncpg, pydantic-settings, cryptography (all already in project deps)

### Security Considerations

- **Encryption at rest:** All sensitive settings (API keys, secrets, database URL) are Fernet-encrypted before DB storage. The encryption key itself remains in the environment and is never stored in the DB.
- **Access control:** Settings endpoints and UI are restricted to admin role only via `require_permission(Permission.MANAGE_SETTINGS)`.
- **Audit trail:** Every mutation logs the actor, setting key, timestamp, and masked before/after values. Plaintext secrets never appear in audit logs.
- **Reveal endpoint:** The reveal/unmask API endpoint must be rate-limited and logged separately to detect credential exfiltration attempts.
- **DB compromise scenario:** If the database is compromised, encrypted settings cannot be read without the Fernet key (stored only in environment). This is equivalent security to env-var-only secrets with the added benefit of audit trail and UI management.

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Multi-tenant settings (all settings are global for this epic)
- OAuth/SSO configuration UI
- Automated secret rotation with external vault (e.g. AWS Secrets Manager / HashiCorp Vault)
- Settings versioning or rollback history
- Settings export/import for environment promotion

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

```
12.1 Data Model ──> 12.2 API ──> 12.3 UI Layout ──┬──> 12.4 API Keys Card
                                                    ├──> 12.5 Infra & Flags Card  (parallelizable)
                                                    └──> 12.6 Agent & Secrets Card
                         12.1 + 12.2 ──> 12.7 Hot Reload
                              All ──> 12.8 Integration Tests
```

1. **Story 12.1:** Settings Data Model & Encrypted Storage
2. **Story 12.2:** Settings API Endpoints
3. **Story 12.3:** Settings UI Page — Layout & Navigation
4. **Stories 12.4, 12.5, 12.6:** UI card sections (can be built in parallel)
5. **Story 12.7:** Hot Reload & Settings Propagation
6. **Story 12.8:** Integration Tests & E2E Validation

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Storing API keys in DB introduces a new attack surface vs env-only secrets | Medium | High | Fernet encryption at rest; encryption key stays in env only; admin-only RBAC; reveal endpoint rate-limited and audit-logged |
| Hot reload of infrastructure settings (DB URL) could cause connection pool disruption | Low | High | Infrastructure settings (database_url, temporal_host, nats_url) are marked restart-required; UI shows warning banner; hot reload only applies to safe settings |
| Encryption key rotation requires re-encrypting all stored secrets atomically | Low | Medium | Wrap re-encryption in a single DB transaction; fail-closed (rollback on any error); old key kept in memory until all secrets re-encrypted |
| Accidental exposure of secrets in browser history or logs | Medium | High | POST for all mutations (no secrets in query params); masked display by default; reveal requires separate authenticated request; no secrets in HTML source |

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| `src/admin/persistence/pg_settings.py` | 12.1 | Create |
| `src/admin/settings_crypto.py` | 12.1 | Create |
| `src/admin/settings_service.py` | 12.1, 12.5, 12.6, 12.7 | Create + Extend |
| `src/admin/rbac.py` | 12.2 | Modify (add MANAGE_SETTINGS) |
| `src/admin/audit.py` | 12.2 | Modify (add SETTINGS_CHANGED) |
| `src/admin/router.py` | 12.2 | Modify (add settings endpoints) |
| `src/admin/templates/base.html` | 12.3 | Modify (add sidebar entry) |
| `src/admin/templates/settings.html` | 12.3 | Create |
| `src/admin/templates/partials/settings_content.html` | 12.3 | Create |
| `src/admin/templates/partials/settings_api_keys.html` | 12.4 | Create |
| `src/admin/templates/partials/settings_infrastructure.html` | 12.5, 12.7 | Create |
| `src/admin/templates/partials/settings_feature_flags.html` | 12.5 | Create |
| `src/admin/templates/partials/settings_agent_config.html` | 12.6 | Create |
| `src/admin/templates/partials/settings_secrets.html` | 12.6 | Create |
| `src/admin/ui_router.py` | 12.3, 12.4, 12.5, 12.6 | Modify (add settings routes) |
| `src/admin/model_gateway.py` | 12.7 | Modify (subscribe to reload signal) |
| `src/settings.py` | 12.7 | Modify (wire to SettingsService) |
| `src/db/migrations/` | 12.1 | Create (Alembic migration) |
| `tests/admin/test_settings_service.py` | 12.1 | Create |
| `tests/admin/test_settings_api.py` | 12.2 | Create |
| `tests/admin/test_settings_ui.py` | 12.3 | Create |
| `tests/admin/test_settings_api_keys_ui.py` | 12.4 | Create |
| `tests/admin/test_settings_infra_ui.py` | 12.5 | Create |
| `tests/admin/test_settings_agent_secrets_ui.py` | 12.6 | Create |
| `tests/admin/test_settings_hot_reload.py` | 12.7 | Create |
| `tests/admin/test_settings_integration.py` | 12.8 | Create |

<!-- docsmcp:end:files-affected -->

## Definition of Done (Epic-Level)

- [ ] All 8 stories completed and individually accepted
- [ ] All acceptance criteria verified (manual or automated)
- [ ] Security review completed by Security Lead
- [ ] All settings from `src/settings.py` configurable via UI
- [ ] Audit log covers 100% of settings mutations
- [ ] Integration tests passing in CI
- [ ] No plaintext secrets in database
- [ ] Admin UI documentation updated
