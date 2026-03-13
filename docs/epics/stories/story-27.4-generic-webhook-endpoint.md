# Story 27.4 — Generic Webhook Endpoint

> **As a** platform operator,
> **I want** a single HTTP endpoint that accepts webhooks from any configured source and feeds them into the pipeline,
> **so that** new input sources can be added through configuration instead of code.

**Purpose:** This is the story that delivers end-to-end value. It wires together the source config (27.1), auth validation (27.5), and payload translator (27.3) into a working FastAPI endpoint that creates TaskPackets and triggers workflows — the same outcome as the GitHub webhook handler, but for any source.

**Intent:** Create `src/ingress/generic_webhook.py` with `POST /webhook/generic/{source_name}`. The endpoint looks up the source config, validates auth, validates the payload schema, translates the payload to a TaskPacketCreate, checks for duplicates, creates the TaskPacket, and starts the Temporal workflow. Register the route in `src/app.py`.

**Points:** 8 | **Size:** L
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 1 (Stories 27.1, 27.5, 27.3, 27.4)
**Depends on:** Story 27.1, Story 27.3, Story 27.5

---

## Description

This endpoint mirrors the flow of `src/ingress/webhook_handler.py` but replaces GitHub-specific logic with config-driven behavior. It reuses the existing infrastructure (dedupe, TaskPacket CRUD, workflow trigger) rather than reimplementing it.

### Request flow:

1. **Source lookup.** Read `source_name` from the URL path. Call `get_source(session, source_name)`. If None, return 404. If disabled, return 403.
2. **Auth validation.** Call `validate_source_auth(source, request)`. On failure, return 401.
3. **Payload read.** Read request body as JSON. On parse failure, return 400.
4. **Schema validation.** If `payload_schema` is configured, validate. On failure, return 422.
5. **Translation.** Call `translate_payload(source, payload)`. On `TranslationError`, return 400 with error details.
6. **Repo check.** Verify the extracted repo exists in `repo_profile`. If not, return 404 ("Repository not registered").
7. **Dedupe.** Call `is_duplicate(session, delivery_id, repo)`. If duplicate, return 200 ("Duplicate delivery").
8. **TaskPacket creation.** Generate correlation_id. Create TaskPacket via `create_taskpacket(session, task_data)`.
9. **Workflow trigger.** Call `start_workflow(taskpacket_id, correlation_id)`. On failure, return 201 ("TaskPacket created, workflow pending").
10. **Success.** Return 201 ("TaskPacket created, workflow started").

### Status codes:

| Code | Meaning |
|------|---------|
| 201 | TaskPacket created (workflow started or pending) |
| 200 | Duplicate delivery, already processed |
| 400 | Bad request (missing body, translation failure) |
| 401 | Auth failure |
| 403 | Source is disabled |
| 404 | Unknown source or unregistered repo |
| 422 | Payload schema validation failure |

## Tasks

- [ ] Create `src/ingress/generic_webhook.py`:
  - `generic_router = APIRouter()`
  - `@generic_router.post("/webhook/generic/{source_name}")`
  - `async def generic_webhook(source_name: str, request: Request, session: AsyncSession = Depends(get_session)) -> Response`
  - Implement the 10-step flow described above
  - Use structured logging with `source_name`, `delivery_id`, `repo`, `correlation_id`
  - All error responses include a `detail` field for debugging
- [ ] Register `generic_router` in `src/app.py`:
  - `from src.ingress.generic_webhook import generic_router`
  - `app.include_router(generic_router)`
- [ ] In Sprint 1, source lookup uses file-based registry only (Story 27.2 adds DB):
  - `get_source()` in Sprint 1 can be a simpler file-only loader
  - OR implement the full registry (27.2) first and use it here
  - Decision: use `load_file_sources()` directly until 27.2 is done, then swap to `get_source()`
- [ ] Write tests in `tests/ingress/test_generic_webhook.py`:
  - Full happy path: valid source, valid auth, valid payload, TaskPacket created, workflow started
  - Unknown source returns 404
  - Disabled source returns 403
  - Auth failure returns 401
  - Invalid JSON body returns 400
  - Schema validation failure returns 422
  - Translation failure (missing required field) returns 400
  - Unregistered repo returns 404
  - Duplicate delivery returns 200
  - Workflow start failure returns 201 (TaskPacket still created)
  - Verify `is_duplicate()` is called with correct delivery_id and repo
  - Verify `create_taskpacket()` is called with correct TaskPacketCreate
  - Verify `start_workflow()` is called with correct taskpacket_id and correlation_id

## Acceptance Criteria

- [ ] `POST /webhook/generic/{source_name}` is registered and reachable
- [ ] Unknown source returns 404
- [ ] Disabled source returns 403
- [ ] Auth failure returns 401 (tested with each auth type)
- [ ] Valid payload creates a TaskPacket and triggers a workflow (201)
- [ ] Duplicate delivery is detected and returns 200
- [ ] Unregistered repo returns 404
- [ ] Schema validation failure returns 422
- [ ] Translation failure returns 400 with field-level error detail
- [ ] Workflow start failure does not lose the TaskPacket (201 returned)
- [ ] Existing GitHub webhook tests still pass (no regression)
- [ ] All new tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Happy path | Valid source "jira", valid HMAC, valid payload | 201, TaskPacket created |
| 2 | Unknown source | source_name="nonexistent" | 404, "Source not found" |
| 3 | Disabled source | source_name="jira", enabled=False | 403, "Source disabled" |
| 4 | Bad API key | source_name="slack", wrong X-API-Key | 401, "Authentication failed" |
| 5 | Bad HMAC | source_name="jira", wrong signature | 401, "Authentication failed" |
| 6 | Invalid JSON | Content-Type application/json, body is not JSON | 400 |
| 7 | Schema fail | Payload missing field required by JSON Schema | 422, schema error details |
| 8 | Missing title | Payload where title_path matches nothing | 400, "title: field not found" |
| 9 | Unregistered repo | Payload extracts repo="unknown/repo" | 404, "Repository not registered" |
| 10 | Duplicate | Same delivery_id + repo already exists | 200, "Duplicate delivery" |
| 11 | Workflow fail | start_workflow raises Exception | 201, "TaskPacket created, workflow pending" |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/generic_webhook.py` | Create |
| `src/app.py` | Modify (register generic_router) |
| `tests/ingress/test_generic_webhook.py` | Create |

## Technical Notes

- The endpoint reads the raw body once for auth (HMAC needs bytes) and once for JSON parsing. Use `request.body()` for raw bytes, then `json.loads()` for parsing (not `request.json()` which re-reads). Store both in local variables.
- Rate limiting is inherited from the app-level SlowAPI config (60/minute default). Per-source rate limits are a future enhancement.
- The endpoint does NOT emit OpenTelemetry spans — that is Story 27.7. In Sprint 1, structured logging provides the audit trail.
- For Sprint 1, if Story 27.2 is not yet complete, the endpoint can use a simplified `load_file_sources()` call. The interface is the same either way: `get_source(name) -> SourceConfig | None`.
