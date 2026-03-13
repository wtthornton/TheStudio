# Story 27.2 — Source Registry (File + DB)

> **As a** platform operator,
> **I want** source configurations loaded from YAML files and a database table,
> **so that** I can ship default sources in version control and add custom sources at runtime without redeploying.

**Purpose:** Without a registry, the generic webhook endpoint has no way to look up how to handle a given source. The registry provides the lookup layer that connects incoming requests to their configuration, with file-based configs for version-controlled defaults and DB configs for runtime flexibility.

**Intent:** Create `src/ingress/sources/registry.py` that loads `SourceConfig` objects from YAML files in `config/sources/` and from a `webhook_sources` PostgreSQL table. File configs are canonical (win on name conflict). Provide `get_source(name)` and `list_sources()` as the public API.

**Points:** 5 | **Size:** M
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 2 (Stories 27.2, 27.6, 27.7)
**Depends on:** Story 27.1 (Source Definition Model)

---

## Description

The registry is a two-layer config loader. Layer 1 reads YAML files from disk at startup. Layer 2 queries the database for runtime-added sources. On name conflict, file wins — this prevents a rogue DB entry from overriding a vetted, version-controlled config.

### Design decisions:

- **YAML format matches SourceConfig fields.** Each file in `config/sources/` is one source. Filename is `{source_name}.yaml`.
- **File configs reload on call (no caching in Phase 1).** This keeps the implementation simple. Caching with file-watch invalidation is a follow-up if performance matters.
- **DB table mirrors SourceConfig structure.** Columns: `name` (PK), `enabled`, `description`, `field_mapping` (JSONB), `auth` (JSONB), `payload_schema` (JSONB, nullable), `created_at`, `updated_at`.
- **Merge strategy:** `list_sources()` returns file sources + DB sources where names don't overlap. `get_source(name)` checks files first, DB second.

## Tasks

- [ ] Create Alembic migration for `webhook_sources` table:
  - `name: VARCHAR(64)` — primary key
  - `enabled: BOOLEAN` — default True
  - `description: TEXT` — default empty
  - `field_mapping: JSONB` — not null
  - `auth: JSONB` — not null
  - `payload_schema: JSONB` — nullable
  - `created_at: TIMESTAMP WITH TIME ZONE` — server default now()
  - `updated_at: TIMESTAMP WITH TIME ZONE` — server default now(), on update now()
- [ ] Create SQLAlchemy model `WebhookSourceRow` in `src/ingress/sources/registry.py` (or separate `models.py` if preferred)
- [ ] Create `src/ingress/sources/registry.py`:
  - `load_file_sources(config_dir: str = "config/sources") -> dict[str, SourceConfig]`
    - Reads all `.yaml` / `.yml` files in the directory
    - Parses each into `SourceConfig`
    - Logs warnings for invalid files (does not crash)
    - Returns dict keyed by source name
  - `async load_db_sources(session: AsyncSession) -> dict[str, SourceConfig]`
    - Queries `webhook_sources` table
    - Converts rows to `SourceConfig` instances
    - Returns dict keyed by source name
  - `async get_source(session: AsyncSession, name: str) -> SourceConfig | None`
    - Check file sources first
    - If not found, check DB
    - Return None if neither has it
  - `async list_sources(session: AsyncSession) -> list[SourceConfig]`
    - Merge file and DB sources (file wins on conflict)
    - Return sorted by name
  - `async create_db_source(session: AsyncSession, config: SourceConfig) -> WebhookSourceRow`
  - `async update_db_source(session: AsyncSession, name: str, config: SourceConfig) -> WebhookSourceRow | None`
  - `async delete_db_source(session: AsyncSession, name: str) -> bool`
  - `is_file_source(name: str) -> bool` — checks if a source is file-based (used by admin API to prevent deletion)
- [ ] Create example YAML files in `config/sources/examples/`:
  - `jira.yaml` — Jira webhook config
  - `linear.yaml` — Linear webhook config
  - `slack.yaml` — Slack event config
  - `plain.yaml` — Plain JSON webhook config
- [ ] Write tests in `tests/ingress/sources/test_registry.py`:
  - Load from file directory (happy path)
  - Load from file with invalid YAML (logged, not crashed)
  - Load from DB
  - Merge: file wins on name conflict
  - `get_source` returns file source when both exist
  - `get_source` returns DB source when only DB has it
  - `get_source` returns None for unknown name
  - CRUD operations on DB sources

## Acceptance Criteria

- [ ] YAML files in `config/sources/` are loaded as `SourceConfig` instances
- [ ] DB table `webhook_sources` exists with correct schema
- [ ] File sources take priority over DB sources on name conflict
- [ ] Invalid YAML files are logged and skipped, not fatal
- [ ] `get_source()` and `list_sources()` return correct merged results
- [ ] DB CRUD operations work (create, update, delete)
- [ ] `is_file_source()` correctly identifies file-based sources
- [ ] All tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Load 2 YAML files | `config/sources/` with jira.yaml, linear.yaml | 2 SourceConfig instances |
| 2 | Invalid YAML | Malformed file in directory | Warning logged, file skipped, other files load |
| 3 | DB source | Row in webhook_sources | SourceConfig instance |
| 4 | Name conflict | File "jira" + DB "jira" | File version returned |
| 5 | DB-only source | DB "custom-ci", no file | DB version returned |
| 6 | Unknown source | get_source("nonexistent") | None |
| 7 | Create DB source | Valid SourceConfig | Row created, returned |
| 8 | Delete file source attempt | is_file_source("jira") | True (admin API blocks delete) |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/sources/registry.py` | Create |
| `config/sources/examples/jira.yaml` | Create |
| `config/sources/examples/linear.yaml` | Create |
| `config/sources/examples/slack.yaml` | Create |
| `config/sources/examples/plain.yaml` | Create |
| `alembic/versions/*_add_webhook_sources.py` | Create |
| `tests/ingress/sources/test_registry.py` | Create |

## Technical Notes

- Use `pyyaml` (already a project dependency via other tools) for YAML parsing
- JSONB columns for `field_mapping` and `auth` store the Pydantic model's `.model_dump()` output
- The file config directory `config/sources/` is the production path; `config/sources/examples/` contains reference configs that are not auto-loaded (different directory)
- For tests, use `tmp_path` fixture to create temporary YAML files rather than relying on actual `config/sources/`
