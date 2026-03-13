# Story 27.1 — Source Definition Model

> **As a** platform developer,
> **I want** Pydantic models that define a webhook source's field mappings, authentication, and validation schema,
> **so that** source configurations can be validated at load time and shared across the registry, translator, and auth modules.

**Purpose:** Every other story in this epic depends on a well-defined source config model. Without it, the translator doesn't know where to find fields, the auth module doesn't know what to validate, and the registry doesn't know what shape to expect from YAML files or DB rows.

**Intent:** Create `src/ingress/sources/source_config.py` with three Pydantic models: `SourceFieldMapping` for JSONPath-based field extraction, `SourceAuth` for auth type and secret reference, and `SourceConfig` as the top-level container. All fields must have clear types, defaults where appropriate, and validation rules.

**Points:** 3 | **Size:** S
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 1 (Stories 27.1, 27.5, 27.3, 27.4)
**Depends on:** None

---

## Description

The source definition model is the schema contract that all other modules consume. It must be strict enough to catch misconfiguration at load time (missing required fields, invalid auth types, malformed JSONPath) but flexible enough to handle the variety of real-world webhook payloads.

### Key design decisions:

- **JSONPath for field extraction.** `title_path`, `body_path`, `labels_path`, `repo_path`, and `delivery_id_path` are JSONPath expressions (e.g., `$.issue.fields.summary`). The translator evaluates these against the incoming payload.
- **Fixed repo as alternative to repo_path.** Some sources always target the same repo. `repo` (fixed string) and `repo_path` (JSONPath) are mutually exclusive — exactly one must be set.
- **Auth types as an enum.** `api_key`, `hmac_sha256`, `bearer`, `none`. The `none` type is for trusted internal sources only.
- **Secrets by reference, not value.** `secret_env_var` is the name of an environment variable (e.g., `JIRA_WEBHOOK_SECRET`), never the secret itself.
- **Optional JSON Schema for payload validation.** `payload_schema` is a dict conforming to JSON Schema draft 2020-12. When present, the translator validates the payload before extracting fields.

## Tasks

- [ ] Create `src/ingress/sources/__init__.py` (empty package init)
- [ ] Create `src/ingress/sources/source_config.py`:
  - `SourceAuthType` enum: `api_key`, `hmac_sha256`, `bearer`, `none`
  - `SourceAuth` model:
    - `type: SourceAuthType`
    - `secret_env_var: str | None = None` (required unless type is `none`)
    - `header_name: str = "Authorization"` (which header carries the credential)
    - Validator: if type is not `none`, `secret_env_var` must be set
  - `SourceFieldMapping` model:
    - `title_path: str` (JSONPath, required)
    - `body_path: str` (JSONPath, required)
    - `labels_path: str | None = None` (JSONPath, optional — defaults to empty list)
    - `repo: str | None = None` (fixed repo, e.g., `"acme/backend"`)
    - `repo_path: str | None = None` (JSONPath to extract repo from payload)
    - `delivery_id_path: str | None = None` (JSONPath — if absent, translator generates from payload hash)
    - Validator: exactly one of `repo` or `repo_path` must be set
  - `SourceConfig` model:
    - `name: str` (unique identifier, URL-safe, e.g., `"jira"`, `"linear"`, `"internal-ci"`)
    - `enabled: bool = True`
    - `description: str = ""`
    - `field_mapping: SourceFieldMapping`
    - `auth: SourceAuth`
    - `payload_schema: dict | None = None` (JSON Schema for validation)
    - Validator: `name` must be alphanumeric + hyphens, 1-64 chars
- [ ] Create example config dicts (as module-level constants or a separate examples file) for:
  - Jira: `title_path = "$.issue.fields.summary"`, `body_path = "$.issue.fields.description"`, `labels_path = "$.issue.fields.labels[*].name"`, `repo = "acme/backend"`, auth = `hmac_sha256`
  - Linear: `title_path = "$.data.title"`, `body_path = "$.data.description"`, `delivery_id_path = "$.data.id"`, `repo_path = "$.data.team.key"`, auth = `bearer`
  - Slack: `title_path = "$.event.text"`, `body_path = "$.event.text"`, `repo = "acme/backend"`, auth = `api_key`
  - Plain webhook: `title_path = "$.title"`, `body_path = "$.body"`, `repo_path = "$.repo"`, auth = `none`
- [ ] Write tests in `tests/ingress/sources/test_source_config.py`:
  - Valid SourceConfig creation
  - Rejection when neither `repo` nor `repo_path` is set
  - Rejection when both `repo` and `repo_path` are set
  - Rejection when auth type requires secret but `secret_env_var` is missing
  - Rejection when `name` contains invalid characters
  - Validation of each example config dict

## Acceptance Criteria

- [ ] `SourceConfig`, `SourceFieldMapping`, `SourceAuth`, and `SourceAuthType` are importable from `src.ingress.sources.source_config`
- [ ] Exactly one of `repo` or `repo_path` must be set (validation error otherwise)
- [ ] Auth types other than `none` require `secret_env_var`
- [ ] Source name validation rejects non-URL-safe characters
- [ ] Example configs for Jira, Linear, Slack, and plain webhook all validate successfully
- [ ] All tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Valid Jira config | Example Jira dict | SourceConfig instance, no errors |
| 2 | Valid Linear config | Example Linear dict | SourceConfig instance, no errors |
| 3 | Valid plain webhook | Example plain dict with auth=none | SourceConfig instance, no errors |
| 4 | Missing repo and repo_path | field_mapping with neither set | ValidationError |
| 5 | Both repo and repo_path set | field_mapping with both set | ValidationError |
| 6 | HMAC auth without secret | auth type=hmac_sha256, no secret_env_var | ValidationError |
| 7 | None auth with secret | auth type=none, secret_env_var set | Valid (secret is ignored) |
| 8 | Invalid source name | name="jira spaces!!" | ValidationError |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/sources/__init__.py` | Create |
| `src/ingress/sources/source_config.py` | Create |
| `tests/ingress/sources/__init__.py` | Create |
| `tests/ingress/sources/test_source_config.py` | Create |

## Technical Notes

- Use `pydantic.field_validator` or `model_validator` for cross-field validation (repo vs repo_path, auth type vs secret)
- JSONPath expressions are stored as strings here. Validation that they are syntactically valid JSONPath is deferred to the translator (Story 27.3) when `jsonpath-ng` is available
- The `payload_schema` dict is not validated as JSON Schema at model creation time — it is validated at translation time using `jsonschema.validate()`
