# Story 27.3 — Payload Translator

> **As a** platform developer,
> **I want** a translator that extracts fields from arbitrary JSON payloads using JSONPath expressions from a source config,
> **so that** any webhook payload can be normalized into a TaskPacketCreate without writing source-specific parsing code.

**Purpose:** The translator is the core capability of the generic webhook system. It bridges the gap between "what the source sends" and "what the pipeline needs" using declarative JSONPath mappings instead of per-source code. Without it, every new source requires a new parser.

**Intent:** Create `src/ingress/sources/translator.py` with `translate_payload(source: SourceConfig, payload: dict) -> TaskPacketCreate`. Uses JSONPath expressions from `SourceFieldMapping` to extract title, body, labels, repo, and delivery ID. Handles missing fields, type coercion, delivery ID generation, and optional JSON Schema validation.

**Points:** 5 | **Size:** M
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 1 (Stories 27.1, 27.5, 27.3, 27.4)
**Depends on:** Story 27.1 (Source Definition Model)

---

## Description

The translator takes a raw JSON payload and a `SourceConfig`, then produces a `TaskPacketCreate` by evaluating JSONPath expressions against the payload. It must handle the messy reality of real-world webhooks: missing fields, unexpected types, nested arrays, and payloads that don't quite match the expected shape.

### Design decisions:

- **`jsonpath-ng` for JSONPath evaluation.** Mature, MIT-licensed, supports the full JSONPath spec including wildcards, recursive descent, and array slicing.
- **Missing required fields raise `TranslationError`.** Title and repo (or repo_path result) are required. Body defaults to empty string if missing.
- **Labels coercion.** If `labels_path` extracts a string, wrap it in a list. If it extracts nothing, default to empty list.
- **Delivery ID generation.** If `delivery_id_path` is not configured or extracts nothing, generate a deterministic delivery ID by hashing the payload (SHA-256 of canonical JSON). This ensures deduplication works even for sources that don't provide a unique event ID.
- **JSON Schema validation runs first.** If `payload_schema` is configured, validate the payload before extracting fields. Schema validation failures raise `TranslationError` with details.
- **issue_id defaults to 0.** Non-GitHub sources may not have a numeric issue ID. The field defaults to 0 and can be overridden via an `issue_id_path` JSONPath if the source has one.

## Tasks

- [ ] Add `jsonpath-ng` to project dependencies in `pyproject.toml`
- [ ] Create `src/ingress/sources/translator.py`:
  - `class TranslationError(Exception)` — raised on extraction failures
    - `source_name: str`
    - `field: str` — which field failed
    - `detail: str` — human-readable error
  - `def _extract(payload: dict, jsonpath_expr: str) -> Any | None`
    - Parse and evaluate JSONPath expression against payload
    - Return first match value, or None if no match
    - Cache compiled JSONPath expressions (module-level LRU cache)
  - `def _extract_list(payload: dict, jsonpath_expr: str) -> list[str]`
    - Extract all matches as a flat list of strings
    - Handles: single string (wrap in list), list of strings (return as-is), non-string (str() coerce), no match (empty list)
  - `def _generate_delivery_id(payload: dict) -> str`
    - Canonical JSON serialization (sorted keys, no whitespace)
    - SHA-256 hash, hex digest
    - Prefix with `generic-` to distinguish from GitHub delivery IDs
  - `def _validate_schema(payload: dict, schema: dict, source_name: str) -> None`
    - Validate payload against JSON Schema using `jsonschema.validate()`
    - On failure, raise `TranslationError` with schema violation details
  - `def translate_payload(source: SourceConfig, payload: dict) -> TaskPacketCreate`
    - Validate schema if `payload_schema` is configured
    - Extract title via `title_path` — required, raise TranslationError if missing
    - Extract body via `body_path` — default to empty string
    - Extract labels via `labels_path` — default to empty list
    - Extract repo via `repo` (fixed) or `repo_path` (JSONPath) — required
    - Extract delivery_id via `delivery_id_path` or generate from payload hash
    - Extract issue_id via `issue_id_path` if configured, else default to 0
    - Generate correlation_id (uuid4)
    - Return `TaskPacketCreate(repo=repo, issue_id=issue_id, delivery_id=delivery_id, correlation_id=correlation_id)`
    - Note: title, body, labels are not in TaskPacketCreate today. Store them in a returned metadata dict alongside the TaskPacketCreate, or propose a minor extension. See Technical Notes.
- [ ] Write tests in `tests/ingress/sources/test_translator.py`:
  - Jira payload translation
  - Linear payload translation
  - Slack event payload translation
  - Plain JSON payload translation
  - Missing required field (title) raises TranslationError
  - Missing optional field (labels) defaults to empty list
  - Labels as string coerced to list
  - Delivery ID generation when no delivery_id_path
  - Delivery ID extraction when delivery_id_path configured
  - Same payload produces same generated delivery ID (deterministic)
  - JSON Schema validation pass
  - JSON Schema validation fail raises TranslationError
  - Invalid JSONPath expression raises TranslationError

## Acceptance Criteria

- [ ] `translate_payload()` extracts all fields from a Jira webhook payload using JSONPath
- [ ] `translate_payload()` extracts all fields from a Linear webhook payload using JSONPath
- [ ] `translate_payload()` handles Slack event payloads (title and body from same field)
- [ ] Missing title raises `TranslationError` with source name and field name
- [ ] Missing body defaults to empty string (not an error)
- [ ] Labels extracted as list regardless of source format (string, list, absent)
- [ ] Delivery ID is deterministic when generated from payload hash
- [ ] JSON Schema validation blocks translation on schema mismatch
- [ ] All tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Jira payload | `{"issue": {"fields": {"summary": "Fix login", "description": "Users can't...", "labels": [{"name": "bug"}]}}}` | TaskPacketCreate with repo from config, delivery_id from hash |
| 2 | Linear payload | `{"data": {"id": "LIN-123", "title": "Add pagination", "description": "...", "team": {"key": "acme/api"}}}` | TaskPacketCreate with repo="acme/api", delivery_id="LIN-123" |
| 3 | Slack event | `{"event": {"text": "Fix the auth bug"}, "event_id": "Ev123"}` | TaskPacketCreate with title=body="Fix the auth bug" |
| 4 | Missing title | `{"body": "some text"}` with title_path="$.title" | TranslationError(field="title") |
| 5 | Missing body | `{"title": "Fix it"}` with body_path="$.body" | TaskPacketCreate with body="" |
| 6 | String labels | Labels path extracts "bug" (string not list) | labels=["bug"] |
| 7 | No delivery_id_path | Payload without ID field, no path configured | delivery_id="generic-{sha256}" |
| 8 | Schema validation fail | Payload missing required schema field | TranslationError with schema details |
| 9 | Duplicate payload | Same payload translated twice | Same delivery_id both times |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/sources/translator.py` | Create |
| `pyproject.toml` | Modify (add jsonpath-ng dependency) |
| `tests/ingress/sources/test_translator.py` | Create |

## Technical Notes

- **TaskPacketCreate gap:** The current `TaskPacketCreate` model only has `repo`, `issue_id`, `delivery_id`, and `correlation_id`. It does not have `title`, `body`, or `labels`. The generic webhook needs to pass these to the pipeline somehow. Options:
  1. Add optional `title`, `body`, `labels` fields to `TaskPacketCreate` (simplest, minimal change)
  2. Return a `TranslationResult(taskpacket_create: TaskPacketCreate, metadata: dict)` and store metadata separately
  3. Store title/body/labels in TaskPacket's `scope` JSON field during creation
  - Recommend option 1: add optional fields to `TaskPacketCreate`. The Intake activity already reads issue title/body from GitHub; for generic sources, it reads them from the TaskPacket instead. This is a minor, backward-compatible change to `src/models/taskpacket.py`.
- **JSONPath caching:** Compile JSONPath expressions once using `functools.lru_cache` on the expression string. This avoids re-parsing on every field extraction.
- **`jsonschema` is already available** via transitive dependencies (FastAPI uses it for OpenAPI). Verify before adding explicit dependency.
