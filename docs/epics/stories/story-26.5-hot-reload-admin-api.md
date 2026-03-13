# Story 26.5 — Hot Reload and Admin API

> **As a** platform operator,
> **I want** an admin endpoint to reload experts from disk and a list endpoint to see all registered experts,
> **so that** I can add or modify experts without restarting the application.

**Purpose:** Without hot reload, every expert change requires an application restart. The reload endpoint makes expert iteration fast (edit file, hit endpoint, verify). The list endpoint provides visibility into what is registered and where it came from.

**Intent:** Add `POST /admin/experts/reload` that re-scans expert directories and syncs to the database, returning a summary of changes. Add `GET /admin/experts` that lists all registered experts with source path, version hash, and lifecycle state. Optionally add a file watcher using `watchdog` that auto-reloads on file change in dev mode.

**Points:** 5 | **Size:** M
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.5-26.6)
**Depends on:** Story 26.2 (Scanner), Story 26.3 (Registrar)

---

## Description

Two new admin endpoints enable runtime expert management:

1. **`POST /admin/experts/reload`** — Triggers a full re-scan of the `experts/` directory and syncs changes to the database. Returns a `SyncResult` as JSON. Accepts an optional query parameter `deactivate_removed=true` to deprecate experts whose directories have been removed.

2. **`GET /admin/experts`** — Returns a list of all registered experts with metadata including source path (from `definition._source_path`), version hash (from `definition._version_hash`), lifecycle state, current version, and capability tags.

Optionally, a file watcher using the `watchdog` library auto-triggers reload when files change in the `experts/` directory. This is enabled only when `EXPERT_WATCH_ENABLED=true` (dev mode).

## Tasks

- [ ] Add reload endpoint to `src/admin/router.py`:
  - `POST /admin/experts/reload`
  - Query parameter: `deactivate_removed: bool = False`
  - Calls `scan_expert_directories(base_path)` then `sync_experts(session, scanned, deactivate_removed)`
  - Returns JSON: `{"created": [...], "updated": [...], "unchanged": [...], "deactivated": [...], "scan_errors": [...]}`
  - `base_path` resolved the same way as in `app.py` lifespan (from settings or computed)
- [ ] Add list endpoint to `src/admin/router.py`:
  - `GET /admin/experts`
  - Query parameters: `class: ExpertClass | None = None`, `lifecycle: LifecycleState | None = None`
  - Calls `search_experts(session, expert_class=class, include_deprecated=True)` if lifecycle filter includes deprecated
  - Returns JSON list of expert summaries:
    ```json
    {
      "id": "uuid",
      "name": "security-review",
      "expert_class": "security",
      "capability_tags": ["auth", "secrets"],
      "trust_tier": "probation",
      "lifecycle_state": "active",
      "current_version": 2,
      "source_path": "/path/to/experts/security-reviewer/EXPERT.md",
      "version_hash": "abc123...",
      "updated_at": "2026-03-13T..."
    }
    ```
  - Extract `source_path` and `version_hash` from `definition._source_path` and `definition._version_hash`
- [ ] Define `ExpertSummary` Pydantic response model in `src/admin/router.py` or a new `src/admin/expert_schemas.py`
- [ ] Extract `base_path` resolution into a shared utility:
  - Create `src/experts/config.py` with `get_experts_base_path() -> Path`
  - Default: `Path(project_root) / "experts"`
  - Overridable via `EXPERTS_BASE_PATH` environment variable
  - Used by both `app.py` lifespan and admin endpoints
- [ ] (Optional) Add file watcher:
  - Create `src/experts/watcher.py`
  - Use `watchdog` library to watch `experts/` directory for `.md`, `.yaml`, `.json` changes
  - On change: debounce 2 seconds, then call scan + sync
  - Start watcher in `app.py` lifespan only when `EXPERT_WATCH_ENABLED=true` env var
  - Stop watcher on shutdown
  - Log all reload triggers
- [ ] Create `tests/admin/test_expert_admin.py`:
  - Test: reload endpoint returns correct SyncResult for new expert
  - Test: reload endpoint returns correct SyncResult for changed expert
  - Test: reload endpoint with `deactivate_removed=true` deprecates missing expert
  - Test: list endpoint returns all experts with source path and hash
  - Test: list endpoint filters by class
  - Test: list endpoint filters by lifecycle state
  - Test: reload endpoint handles scan errors gracefully (returns errors in response)

## Acceptance Criteria

- [ ] `POST /admin/experts/reload` re-scans and syncs experts, returns summary
- [ ] `GET /admin/experts` returns all experts with source path and version hash
- [ ] Reload endpoint accepts `deactivate_removed` query parameter
- [ ] List endpoint supports filtering by class and lifecycle state
- [ ] Base path is configurable via environment variable
- [ ] File watcher (if implemented) auto-reloads on file change with debounce
- [ ] All unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Reload new expert | Add `experts/new/EXPERT.md`, call POST reload | `{"created": ["new"], ...}` |
| 2 | Reload changed expert | Modify EXPERT.md, call POST reload | `{"updated": ["changed"], ...}` |
| 3 | Reload with deactivate | Remove directory, call POST reload with `deactivate_removed=true` | `{"deactivated": ["removed"], ...}` |
| 4 | List all experts | GET /admin/experts | JSON array with all experts, source_path populated |
| 5 | List filtered by class | GET /admin/experts?class=security | Only security experts returned |
| 6 | Scan errors in response | Invalid EXPERT.md in one directory | `{"scan_errors": [{"directory": "...", "error": "..."}]}` |

## Files Affected

| File | Action |
|------|--------|
| `src/admin/router.py` | Modify (add two endpoints) |
| `src/admin/expert_schemas.py` | Create (response models) |
| `src/experts/config.py` | Create (base path resolution) |
| `src/experts/watcher.py` | Create (optional — file watcher) |
| `src/app.py` | Modify (use `get_experts_base_path()`, optionally start watcher) |
| `tests/admin/test_expert_admin.py` | Create |

## Technical Notes

- The reload endpoint requires an async database session. Use the same `Depends(get_async_session)` pattern as other admin endpoints.
- The file watcher is optional and should be behind a feature flag. It is a dev convenience, not a production requirement. If `watchdog` is not installed, the watcher should be silently disabled.
- The list endpoint extracts metadata from the `definition` JSON field. If `_source_path` or `_version_hash` are missing (legacy experts), the fields should be `null` in the response.
- Both endpoints should require admin permissions via the existing `require_permission()` decorator pattern used in `src/admin/router.py`.
- The `EXPERTS_BASE_PATH` env var allows testing with a different directory and supports containerized deployments where the project root may differ.
