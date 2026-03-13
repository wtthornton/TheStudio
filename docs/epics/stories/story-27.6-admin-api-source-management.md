# Story 27.6 — Admin API for Source Management

> **As a** platform administrator,
> **I want** REST endpoints to list, create, update, delete, and test webhook sources,
> **so that** I can manage sources at runtime without editing config files or redeploying.

**Purpose:** File-based configs handle the "ships with the codebase" use case. But operators need to add, modify, and remove sources without a deployment cycle. This story provides the admin API for runtime source management, plus a test endpoint that validates a payload against a source's mapping without side effects.

**Intent:** Create `src/admin/source_router.py` with CRUD endpoints for DB-backed sources and a test endpoint that dry-runs translation. All endpoints require ADMIN role. File-based sources are read-only via the API (visible in list, not deletable).

**Points:** 5 | **Size:** M
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 2 (Stories 27.2, 27.6, 27.7)
**Depends on:** Story 27.1, Story 27.2, Story 27.3

---

## Description

The admin API follows the patterns established in `src/admin/router.py` (existing admin routes). All endpoints live under `/admin/sources` and require the ADMIN role. The test endpoint is particularly valuable — it lets operators validate their source config and payload mapping before routing real traffic.

### Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/sources` | List all sources (file + DB), indicate origin |
| GET | `/admin/sources/{name}` | Get a single source config |
| POST | `/admin/sources` | Create a new DB-backed source |
| PUT | `/admin/sources/{name}` | Update a DB-backed source |
| DELETE | `/admin/sources/{name}` | Delete a DB-backed source (file sources return 403) |
| POST | `/admin/sources/{name}/test` | Dry-run: validate auth config and translate a test payload |

### Response models:

- `SourceResponse` — `SourceConfig` fields + `origin: "file" | "db"` + `created_at` + `updated_at`
- `SourceTestRequest` — `payload: dict` + `headers: dict[str, str]` (optional, for auth testing)
- `SourceTestResponse` — `auth_valid: bool` + `translation_result: dict | None` + `errors: list[str]`

## Tasks

- [ ] Create `src/admin/source_router.py`:
  - `source_admin_router = APIRouter(prefix="/admin/sources", tags=["sources"])`
  - All routes depend on ADMIN role (reuse existing auth dependency from `src/admin/router.py`)
  - `GET /` — `list_sources_endpoint(session)`
    - Call `registry.list_sources(session)`
    - Annotate each with `origin: "file" | "db"` using `registry.is_file_source()`
    - Return list of `SourceResponse`
  - `GET /{name}` — `get_source_endpoint(name, session)`
    - Call `registry.get_source(session, name)`
    - 404 if not found
    - Return `SourceResponse`
  - `POST /` — `create_source_endpoint(config: SourceConfig, session)`
    - Validate SourceConfig (Pydantic does this)
    - Check name doesn't conflict with file source (`registry.is_file_source()`)
    - Check name doesn't already exist in DB
    - Call `registry.create_db_source(session, config)`
    - Return 201 with `SourceResponse`
    - 409 if name already exists
  - `PUT /{name}` — `update_source_endpoint(name, config: SourceConfig, session)`
    - 403 if file source (cannot update file sources via API)
    - 404 if not found in DB
    - Call `registry.update_db_source(session, name, config)`
    - Return 200 with `SourceResponse`
  - `DELETE /{name}` — `delete_source_endpoint(name, session)`
    - 403 if file source (cannot delete file sources via API)
    - 404 if not found in DB
    - Call `registry.delete_db_source(session, name)`
    - Return 204
  - `POST /{name}/test` — `test_source_endpoint(name, body: SourceTestRequest, session)`
    - Look up source config
    - 404 if not found
    - If `headers` provided: run `validate_source_auth()` and report result
    - Run `translate_payload()` with test payload
    - Return `SourceTestResponse` with auth result, translated TaskPacketCreate preview, and any errors
    - Does NOT create a TaskPacket or trigger a workflow
- [ ] Register `source_admin_router` in `src/app.py`
- [ ] Write tests in `tests/admin/test_source_admin.py`:
  - List sources (file + DB combined)
  - Get single source
  - Create DB source (happy path)
  - Create with conflicting file source name (409)
  - Create with duplicate DB name (409)
  - Update DB source (happy path)
  - Update file source (403)
  - Delete DB source (happy path)
  - Delete file source (403)
  - Delete unknown source (404)
  - Test endpoint with valid payload (returns preview)
  - Test endpoint with invalid payload (returns errors)
  - Test endpoint with auth headers (validates auth)
  - All endpoints require ADMIN role (401 without)

## Acceptance Criteria

- [ ] `GET /admin/sources` returns all sources with origin annotation
- [ ] `POST /admin/sources` creates a DB source, returns 201
- [ ] `POST /admin/sources` returns 409 on name conflict (file or DB)
- [ ] `PUT /admin/sources/{name}` updates DB source, returns 403 for file source
- [ ] `DELETE /admin/sources/{name}` deletes DB source, returns 403 for file source
- [ ] `POST /admin/sources/{name}/test` returns translation preview without side effects
- [ ] Test endpoint reports auth validation result when headers provided
- [ ] All endpoints require ADMIN role
- [ ] All tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | List all | 2 file + 1 DB source | 3 sources, origins correct |
| 2 | Get file source | name="jira" (file) | 200, origin="file" |
| 3 | Get DB source | name="custom-ci" (DB) | 200, origin="db" |
| 4 | Create valid | POST with valid SourceConfig | 201, source created |
| 5 | Create duplicate | POST with name="jira" (file exists) | 409 |
| 6 | Update DB | PUT with updated config | 200, config updated |
| 7 | Update file | PUT name="jira" | 403 |
| 8 | Delete DB | DELETE name="custom-ci" | 204 |
| 9 | Delete file | DELETE name="jira" | 403 |
| 10 | Test valid | POST test with valid Jira payload | 200, translation preview |
| 11 | Test invalid | POST test with payload missing title | 200, errors=["title: not found"] |
| 12 | No admin role | Any endpoint without ADMIN | 401 |

## Files Affected

| File | Action |
|------|--------|
| `src/admin/source_router.py` | Create |
| `src/app.py` | Modify (register source_admin_router) |
| `tests/admin/test_source_admin.py` | Create |

## Technical Notes

- Follow the pattern in `src/admin/router.py` for auth dependency injection. The existing `require_admin` dependency should be reusable.
- The test endpoint is intentionally separate from the create endpoint. Operators should be able to test a config before committing to it. The test endpoint also works for file-based sources (test your YAML mapping without going live).
- Response models should use Pydantic `model_config = {"from_attributes": True}` for SQLAlchemy compatibility.
- The test endpoint's auth validation requires the operator to provide sample headers. If headers are omitted, auth validation is skipped in the test (only translation is tested).
