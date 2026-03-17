# Epic 27 — Webhook Triggers for Non-GitHub Input Sources

**Author:** Saga
**Date:** 2026-03-13
**Status:** Meridian Reviewed — Conditional Pass (2026-03-16). Blocker #5 resolved (2026-03-16): source_name stored as dedicated VARCHAR(100) column with index. Migration 022 adds column with 'github' default. Decision: new column over scope JSON for queryability.
**Target Sprint:** Multi-sprint (estimated 2-3 sprints)
**Prerequisites:** None (independent of other active epics). Blocker #5 (source_name storage) — resolved.

---

## 1. Title

Webhook Triggers for Non-GitHub Input Sources — Build a config-driven generic webhook intake layer that translates arbitrary JSON payloads from Jira, Linear, Slack, CI pipelines, and internal tools into TaskPackets, enabling TheStudio to process work from any source without building per-source adapters.

## 2. Narrative

TheStudio has one way in. Every piece of work enters through `POST /webhook/github` — a handler tightly coupled to GitHub's event structure, signature scheme, and payload shape. If a team tracks work in Jira, or triages in Linear, or wants to kick off work from a Slack command, or has an internal tool that identifies refactoring candidates — none of those can feed TheStudio without someone building a full adapter module with bespoke parsing, authentication, and routing logic.

This is a growth bottleneck. The pipeline itself is source-agnostic. TaskPacket does not care whether the work originated from a GitHub issue, a Jira ticket, or a Slack message. It needs a `repo`, an `issue_id`, a `delivery_id`, and a `correlation_id`. Everything downstream — Context, Intent, Router, Assembler, Primary Agent, Verification, QA, Publisher — operates on the TaskPacket, not the source event. The coupling to GitHub exists only in the intake layer.

The fix is a thin, declarative translation layer. Inspired by thepopebot's `TRIGGERS.json` pattern: users define a source configuration that says "when a POST arrives at `/webhook/generic/jira`, the title lives at `$.issue.fields.summary`, the body at `$.issue.fields.description`, the repo is always `acme/backend`, and authentication is an HMAC-SHA256 signature in the `X-Jira-Webhook-Signature` header using the secret in `JIRA_WEBHOOK_SECRET`." The platform does the rest — validates auth, extracts fields via JSONPath, builds a TaskPacketCreate, deduplicates, and triggers the workflow.

This is not a replacement for the GitHub webhook handler. GitHub remains a first-class source with its own dedicated endpoint, event filtering, and signature validation. The generic webhook is for the long tail — sources where the volume or strategic importance does not justify a full adapter, but where the translation from "their payload" to "our TaskPacket" is mechanically simple.

### Why now?

Three forcing functions:

1. **Adoption beyond GitHub-native teams.** Multiple prospective users have asked about Jira and Linear support. Building dedicated adapters for each blocks adoption behind engineering capacity. A generic layer unblocks all of them with configuration, not code.

2. **Internal tooling integration.** TheStudio's own CI pipeline, test infrastructure, and monitoring tools generate actionable signals (flaky test detected, security scan finding, dependency update available). These should be expressible as TaskPackets without writing new webhook handlers for each.

3. **Platform extensibility story.** A config-driven source system makes TheStudio a platform that accepts work, not an app that watches GitHub. This is the architectural shift from "GitHub bot" to "software delivery platform."

## 3. References

| Artifact | Location |
|----------|----------|
| GitHub webhook handler (reference impl) | `src/ingress/webhook_handler.py` |
| Delivery ID deduplication | `src/ingress/dedupe.py` |
| HMAC signature validation | `src/ingress/signature.py` |
| Workflow trigger (Temporal) | `src/ingress/workflow_trigger.py` |
| TaskPacket model | `src/models/taskpacket.py` |
| TaskPacket CRUD | `src/models/taskpacket_crud.py` |
| Repo profile (registered repos) | `src/repo/repo_profile.py` |
| FastAPI app and router registration | `src/app.py` |
| Observability conventions | `src/observability/conventions.py` |
| Poll client (alternative intake path) | `src/ingress/poll/client.py` |
| Architecture overview | `thestudioarc/00-overview.md` |
| Coding standards | `thestudioarc/20-coding-standards.md` |
| SOUL principles | `thestudioarc/SOUL.md` |

## 4. Acceptance Criteria

### Source Configuration

1. **Source config model exists.** `src/ingress/sources/source_config.py` contains Pydantic models: `SourceFieldMapping` (JSONPath expressions for extracting title, body, labels, repo, delivery ID from arbitrary payloads), `SourceAuth` (auth type enum with secret env var reference and header name), `SourceConfig` (name, enabled flag, field mapping, auth, optional JSON Schema for payload validation, description).

2. **Source registry loads from file and database.** `src/ingress/sources/registry.py` loads source configs from YAML files in `config/sources/` and from a `webhook_sources` DB table. File configs are canonical; DB configs supplement. `get_source(name)` returns a config or None. `list_sources()` returns all.

3. **DB migration for webhook_sources exists.** Alembic migration creates the `webhook_sources` table with columns matching `SourceConfig` fields.

### Payload Translation

4. **Translator converts arbitrary payloads to TaskPacketCreate.** `src/ingress/sources/translator.py` uses JSONPath from `SourceFieldMapping` to extract fields from any JSON payload. Missing optional fields get defaults. Missing required fields cause rejection with a clear error. Delivery ID is generated via payload hash when no `delivery_id_path` is configured. Payload is validated against `payload_schema` if configured.

5. **Translation handles real-world payload shapes.** Unit tests demonstrate successful translation of Jira webhook payloads, Linear webhook payloads, Slack event payloads, and plain JSON payloads.

### Generic Webhook Endpoint

6. **`POST /webhook/generic/{source_name}` exists and is registered.** The endpoint accepts arbitrary JSON, looks up the source config, validates auth, validates payload schema, translates to TaskPacketCreate, deduplicates, creates the TaskPacket, and triggers the Temporal workflow.

7. **Endpoint reuses existing infrastructure.** Deduplication uses `dedupe.is_duplicate()`. TaskPacket creation uses `taskpacket_crud.create()`. Workflow trigger uses `workflow_trigger.start_workflow()`. No parallel implementations of existing capabilities.

8. **Unknown source returns 404.** Disabled source returns 403. Auth failure returns 401. Schema validation failure returns 422. Translation failure returns 400. Successful creation returns 201.

### Authentication

9. **Source auth validation exists.** `src/ingress/sources/auth.py` implements API key, HMAC-SHA256, bearer token, and none (pass-through) auth types. API key and bearer use timing-safe comparison. HMAC follows the same pattern as the existing GitHub signature validation.

10. **Secrets are never stored in config files.** Source auth configs reference environment variable names, not secret values. The auth validator reads the actual secret from the environment at validation time.

### Administration

11. **Admin CRUD endpoints exist.** `GET /admin/sources`, `POST /admin/sources`, `PUT /admin/sources/{name}`, `DELETE /admin/sources/{name}` manage DB-stored sources. File-based sources cannot be deleted via API. All require ADMIN role.

12. **Test endpoint exists.** `POST /admin/sources/{name}/test` accepts a sample payload, runs it through auth validation and translation, and returns the resulting TaskPacketCreate preview without actually creating a TaskPacket or triggering a workflow.

### Observability

13. **OpenTelemetry spans cover the generic webhook flow.** Spans: `ingress.generic.receive`, `ingress.generic.auth`, `ingress.generic.translate`, `ingress.generic.trigger`. Attributes include source_name, auth_type, delivery_id, repo, and outcome.

14. **Source origin is recorded on TaskPacket.** The TaskPacket metadata includes `source_name` so downstream pipeline stages and audit logs know where the work originated. GitHub webhooks record `source_name = "github"`.

15. **NATS JetStream signal emitted.** `source.webhook.received` signal is published on successful generic webhook processing.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSONPath library introduces a new dependency with security surface | Medium | Medium | Evaluate `jsonpath-ng` (mature, MIT). Pin version. TAPPS dependency scan before merge |
| Payload translation is too rigid for real-world webhook shapes | Medium | High — sources can't actually be configured | Test with actual Jira, Linear, Slack payloads. Provide fallback extractors and default values |
| Secrets management via env vars does not scale to many sources | Low | Medium — operational friction | Env vars are Phase 1. DB-encrypted secrets with key rotation is a follow-up |
| Generic endpoint becomes a spam vector | Medium | Medium — noise in pipeline | Auth is mandatory for production sources. Rate limiting via existing SlowAPI. Admin must explicitly create and enable sources |
| JSONPath expressions in YAML configs are error-prone for users | Medium | Low — bad config, not bad code | Test endpoint validates mapping before any real traffic. YAML examples for common sources ship in `config/sources/examples/` |
| DB-stored source configs create a second source of truth alongside files | Low | Medium — config drift | File configs are canonical and win on conflict. DB supplements. Clear documentation |

## 5. Constraints & Non-Goals

### Constraints

- **GitHub webhook handler is unchanged.** `POST /webhook/github` remains the dedicated endpoint for GitHub events. This epic adds a parallel generic path, not a replacement.
- **No changes to pipeline stages.** Everything downstream of TaskPacket creation is unaffected. The pipeline does not know or care about source origin beyond metadata.
- **No changes to TaskPacket schema.** `source_name` is stored in the existing JSON `scope` or a new metadata field. The core TaskPacket columns (repo, issue_id, delivery_id, correlation_id, status) are unchanged.
- **Secrets via environment variables only.** No secrets stored in YAML files or database. Source auth configs reference env var names. Encrypted DB-stored secrets are out of scope.
- **Sources must map to registered repos.** The `repo` extracted from a payload (or fixed in config) must match a repo in the `repo_profile` table. Unregistered repos are rejected.
- **Python 3.12+, existing test infrastructure.** New dependency allowed only for JSONPath evaluation (evaluate `jsonpath-ng`).
- **All existing tests must pass.** No regressions in GitHub webhook handling or any pipeline behavior.

### Non-Goals

- **Not building dedicated adapters for Jira, Linear, or Slack.** The generic webhook handles all sources through config. If a source later needs deep integration (bidirectional sync, issue creation from TheStudio back to Jira), that is a separate epic per source.
- **Not supporting bidirectional communication.** This epic is intake-only. Publishing results back to non-GitHub sources (e.g., updating a Jira ticket when a PR is created) is future work.
- **Not supporting streaming or SSE sources.** This is webhook (HTTP POST) only. Polling, websocket, or event stream sources are out of scope.
- **Not building a UI for source configuration.** Admin API endpoints are sufficient for Phase 1. A UI (in the existing admin panel at `/admin/ui/`) is a follow-up.
- **Not implementing payload transformation beyond field extraction.** The translator extracts fields via JSONPath. Complex transformations (conditional logic, computed fields, multi-step transforms) are out of scope. If a source's payload cannot be mapped with JSONPath alone, it needs a dedicated adapter.
- **Not supporting GraphQL webhook payloads or non-JSON content types.** JSON only.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts scope, reviews AC completion |
| Tech Lead | Backend Engineer (TBD — assign before sprint start) | Owns implementation of all 7 stories |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, tests with real webhook payloads from external tools |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plans |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sources configurable without code | At least 3 source configs (Jira, Linear, plain webhook) ship as examples | Count of YAML files in `config/sources/examples/` |
| Generic webhook processes successfully | 100% of valid test payloads produce a TaskPacket | Integration test pass rate |
| Auth rejection rate for invalid requests | 100% of unauthenticated/misauthenticated requests rejected | Unit test coverage + structured log audit |
| Zero regression on GitHub webhook | All existing ingress tests pass unchanged | CI green on merge |
| Time to add a new source | < 30 minutes from "I have the payload shape" to "source is configured and tested" | Manual validation with test endpoint |
| Admin API functional | All CRUD operations work, test endpoint returns valid previews | Integration test coverage |
| Observability coverage | Every generic webhook request has a trace with all 4 spans | Trace export verification in tests |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/ingress/sources/source_config.py` | **New file** — Pydantic models for source configuration |
| `src/ingress/sources/registry.py` | **New file** — Source registry (file + DB loader) |
| `src/ingress/sources/translator.py` | **New file** — JSONPath-based payload translator |
| `src/ingress/sources/auth.py` | **New file** — Source auth validation (API key, HMAC, bearer, none) |
| `src/ingress/sources/__init__.py` | **New file** — Package init |
| `src/ingress/generic_webhook.py` | **New file** — `POST /webhook/generic/{source_name}` endpoint |
| `src/admin/source_router.py` | **New file** — Admin CRUD + test endpoints for sources |
| `src/app.py` | **Modified** — Register generic webhook and admin source routers |
| `src/observability/conventions.py` | **Modified** — Add generic webhook span names and attributes |
| `src/models/taskpacket.py` | **Modified** — Add `source_name` to metadata (minor, JSON field or new column) |
| `config/sources/examples/` | **New directory** — Example YAML configs for Jira, Linear, Slack, plain webhook |
| `alembic/versions/` | **New migration** — `webhook_sources` table |
| `tests/ingress/sources/` | **New directory** — All unit tests for source config, registry, translator, auth |
| `tests/ingress/test_generic_webhook.py` | **New file** — Endpoint integration tests |
| `tests/admin/test_source_admin.py` | **New file** — Admin API tests |

### Assumptions

1. **JSONPath is sufficient for field extraction.** Real-world webhook payloads from Jira, Linear, and Slack have their key fields (title, body, ID) at known, stable paths in the JSON. If a source restructures its payload, the JSONPath expressions in the config need updating — this is expected maintenance, not a design flaw.

2. **`jsonpath-ng` is the right library.** It is mature (MIT, well-maintained), supports the full JSONPath spec, and has no native extensions. If evaluation reveals concerns, `jsonpath2` or a minimal custom parser are alternatives.

3. **One source config per source name.** There is no multi-tenant mapping (e.g., "jira-team-a" and "jira-team-b" can be separate sources, but not dynamically routed from one endpoint). Multi-tenant source routing is future work.

4. **All sources map to exactly one repo or extract it from the payload.** The field mapping supports either a fixed `repo` string or a `repo_path` JSONPath. There is no multi-repo fan-out from a single webhook event.

5. **Payload validation via JSON Schema is optional but recommended.** Sources that provide a `payload_schema` get validation before translation. Sources without it accept any JSON and rely on the translator to handle missing fields gracefully.

6. **The `webhook_sources` DB table uses the same PostgreSQL instance as other tables.** No separate config database.

7. **Rate limiting on the generic endpoint uses the existing SlowAPI configuration.** No per-source rate limits in Phase 1.

### Dependencies

- **Upstream:** None. This epic is independent and can start immediately.
- **Downstream unblocks:** Jira integration epic, Linear integration epic, internal tooling integration, CI-triggered work. Any future source-specific deep integration builds on the generic webhook as its intake path.

---

## Story Map

Stories are ordered by vertical slices. Sprint 1 delivers a working end-to-end generic webhook with file-based config. Sprint 2 adds DB-backed sources, admin API, and observability.

### Sprint 1: Core Generic Webhook (End-to-End Value)

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 27.1 | **Source Definition Model** | S | Foundation — all other stories depend on this | `src/ingress/sources/source_config.py` |
| 27.5 | **Source Auth Validation** | M | Security — must exist before endpoint | `src/ingress/sources/auth.py` |
| 27.3 | **Payload Translator** | M | Core capability — JSONPath extraction | `src/ingress/sources/translator.py` |
| 27.4 | **Generic Webhook Endpoint** | L | End-to-end flow — the deliverable | `src/ingress/generic_webhook.py`, `src/app.py` |

### Sprint 2: Registry, Admin, Observability

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 27.2 | **Source Registry (File + DB)** | M | Config management + DB persistence | `src/ingress/sources/registry.py`, migration |
| 27.6 | **Admin API for Source Management** | M | Operational capability | `src/admin/source_router.py`, `src/app.py` |
| 27.7 | **Observability and Audit Trail** | M | Production readiness | `src/observability/conventions.py`, `src/models/taskpacket.py` |

---

## Meridian Review Status

**Round 1: Conditional Pass (2026-03-16)**

**Verdict:** 5/7 questions PASS, 2 GAP/CONDITIONAL. Clean architectural vision with strong non-goals. Most AI-implementable of the three reviewed epics.

| # | Question | Verdict |
|---|----------|---------|
| 1 | Goal specific enough to test? | PASS |
| 2 | AC testable at epic scale? | PASS (one minor gap) |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified with owners/dates? | GAP |
| 5 | Success metrics measurable? | PASS (one gap on "time to add source") |
| 6 | AI agent can implement without guessing? | CONDITIONAL (source_name storage ambiguity) |
| 7 | Narrative compelling? | PASS |

**Must fix before commit:**

| # | Issue | Resolution |
|---|-------|------------|
| 1 | AC #14 ambiguous: `source_name` storage is "scope JSON or new metadata field." Current TaskPacket model has no `source_name` or `metadata` field. Must decide: scope JSON column or new column with migration. "Or" is not a specification. | Open |
| 2 | All stakeholder roles TBD. No named owners or assignment dates. | Open |
| 3 | `jsonpath-ng` evaluation unassigned. AC #4 assumes it exists. If evaluation fails, translation layer needs redesign. Assign a person with a decision date. | Open |
| 4 | Explicitly state Sprint 1 is file-config-only (no DB table, no DB registry). Story map implies this but ACs do not make it airtight. | Open |

**Recommended (not blocking):**

| # | Recommendation |
|---|----------------|
| 1 | Story numbering does not match execution order (Sprint 1: 27.1, 27.5, 27.3, 27.4). Renumber to match execution order. |
| 2 | "Time to add a new source < 30 minutes" needs a concrete usability validation protocol with a named tester and date. |
| 3 | Identify source for real-world Jira/Linear/Slack test payloads. Someone needs tool access to capture actual payloads. |
