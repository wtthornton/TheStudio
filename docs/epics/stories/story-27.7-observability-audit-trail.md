# Story 27.7 — Observability and Audit Trail

> **As a** platform operator,
> **I want** every generic webhook request traced, logged, and attributed to its source,
> **so that** I can debug failures, audit source activity, and monitor the health of non-GitHub intake paths.

**Purpose:** The GitHub webhook handler already has observability (span `ingress.webhook_receive`, structured logging, correlation ID). The generic webhook needs the same treatment — plus source attribution so operators can answer "where did this work come from?" at any point in the pipeline.

**Intent:** Add OpenTelemetry spans for generic webhook processing, structured logging for all outcomes (including rejections), source_name metadata on TaskPackets, and a NATS JetStream signal for webhook receipt. This is the production-readiness story — without it, the generic webhook is a black box.

**Points:** 5 | **Size:** M
**Epic:** 27 — Webhook Triggers for Non-GitHub Input Sources
**Sprint:** 2 (Stories 27.2, 27.6, 27.7)
**Depends on:** Story 27.4 (Generic Webhook Endpoint)

---

## Description

This story adds four observability layers to the generic webhook flow:

1. **OpenTelemetry spans** — structured trace data for each processing step
2. **Structured logging** — human-readable audit trail for all outcomes
3. **Source attribution** — `source_name` recorded on TaskPacket metadata
4. **JetStream signal** — event notification for downstream consumers

### Spans:

| Span Name | Parent | Attributes |
|-----------|--------|------------|
| `ingress.generic.receive` | Root | source_name, correlation_id |
| `ingress.generic.auth` | receive | source_name, auth_type, outcome |
| `ingress.generic.translate` | receive | source_name, delivery_id, repo, outcome |
| `ingress.generic.trigger` | receive | source_name, taskpacket_id, workflow_run_id, outcome |

### Log events:

Every request produces at least one structured log entry with:
- `source_name`
- `auth_type`
- `delivery_id` (if extracted)
- `repo` (if extracted)
- `correlation_id` (if generated)
- `outcome` (created, duplicate, auth_failed, translation_failed, disabled, not_found, schema_failed, workflow_failed)

Rejections (auth failure, unknown source, disabled source) are logged at WARNING level. Successful processing is logged at INFO level.

### Source attribution:

Add `source_name` to the TaskPacket so downstream pipeline stages know the origin. Options:
1. New column `source_name: VARCHAR(64)` on `taskpacket` table
2. Store in existing `scope` JSON field under `scope.source_name`

Recommendation: option 1 (explicit column) for queryability. Add an Alembic migration. Default value for existing rows: `"github"`.

### JetStream signal:

Publish `source.webhook.received` to NATS JetStream with payload:
```json
{
  "source_name": "jira",
  "delivery_id": "...",
  "repo": "acme/backend",
  "taskpacket_id": "...",
  "correlation_id": "...",
  "timestamp": "..."
}
```

This follows the existing signal pattern in `src/outcome/signals.py`.

## Tasks

- [ ] Add span name constants to `src/observability/conventions.py`:
  - `SPAN_INGRESS_GENERIC_RECEIVE = "ingress.generic.receive"`
  - `SPAN_INGRESS_GENERIC_AUTH = "ingress.generic.auth"`
  - `SPAN_INGRESS_GENERIC_TRANSLATE = "ingress.generic.translate"`
  - `SPAN_INGRESS_GENERIC_TRIGGER = "ingress.generic.trigger"`
  - `ATTR_SOURCE_NAME = "thestudio.source_name"`
  - `ATTR_AUTH_TYPE = "thestudio.auth_type"`
- [ ] Add spans to `src/ingress/generic_webhook.py`:
  - Wrap entire handler in `SPAN_INGRESS_GENERIC_RECEIVE`
  - Wrap auth validation in `SPAN_INGRESS_GENERIC_AUTH`
  - Wrap translation in `SPAN_INGRESS_GENERIC_TRANSLATE`
  - Wrap workflow trigger in `SPAN_INGRESS_GENERIC_TRIGGER`
  - Set attributes on each span
- [ ] Add structured logging to `src/ingress/generic_webhook.py`:
  - Log at INFO for successful processing
  - Log at WARNING for rejections (auth, disabled, not found, etc.)
  - Include source_name, delivery_id, repo, correlation_id, outcome in `extra`
- [ ] Create Alembic migration to add `source_name` column to `taskpacket` table:
  - `source_name: VARCHAR(64), nullable=True, default=None`
  - Backfill existing rows with `"github"`
- [ ] Update `TaskPacketRow` in `src/models/taskpacket.py`:
  - Add `source_name: Mapped[str | None]` column
- [ ] Update `TaskPacketCreate` and `TaskPacketRead` in `src/models/taskpacket.py`:
  - Add `source_name: str | None = None` field
- [ ] Update `src/ingress/webhook_handler.py` to set `source_name="github"` on TaskPacketCreate
- [ ] Update `src/ingress/generic_webhook.py` to set `source_name=source_name` on TaskPacketCreate
- [ ] Add JetStream signal emission to `src/ingress/generic_webhook.py`:
  - After successful TaskPacket creation
  - Subject: `source.webhook.received`
  - Payload: source_name, delivery_id, repo, taskpacket_id, correlation_id, timestamp
  - Follow pattern from `src/outcome/signals.py`
  - Failure to publish signal must not fail the webhook (log and continue)
- [ ] Write tests in `tests/ingress/sources/test_observability.py`:
  - Verify spans are created with correct names and attributes
  - Verify structured log entries for each outcome type
  - Verify source_name is set on TaskPacket
  - Verify JetStream signal is published
  - Verify signal publish failure does not break the webhook

## Acceptance Criteria

- [ ] Four span names are defined in `src/observability/conventions.py`
- [ ] Generic webhook handler creates spans for receive, auth, translate, and trigger
- [ ] All spans include `source_name` attribute
- [ ] Auth span includes `auth_type` and `outcome` attributes
- [ ] Translate span includes `delivery_id` and `repo` attributes
- [ ] Trigger span includes `taskpacket_id` attribute
- [ ] Every webhook request (including rejections) produces a structured log entry
- [ ] `source_name` column exists on taskpacket table
- [ ] Generic webhook sets `source_name` on TaskPacketCreate
- [ ] GitHub webhook sets `source_name = "github"` on TaskPacketCreate
- [ ] `source.webhook.received` signal published to JetStream on success
- [ ] Signal publish failure is logged but does not fail the webhook
- [ ] All existing tests pass (no regression from TaskPacket schema change)
- [ ] All new tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Spans on success | Valid webhook request | 4 spans with correct names and attributes |
| 2 | Spans on auth failure | Invalid auth | receive + auth spans (auth has outcome=failed) |
| 3 | Spans on translation failure | Bad payload | receive + auth + translate spans |
| 4 | Log on success | Valid request | INFO log with source_name, delivery_id, repo, outcome=created |
| 5 | Log on auth failure | Invalid auth | WARNING log with source_name, outcome=auth_failed |
| 6 | Source name on TaskPacket | Generic webhook creates TP | TaskPacket.source_name = "jira" |
| 7 | Source name for GitHub | GitHub webhook creates TP | TaskPacket.source_name = "github" |
| 8 | JetStream signal | Successful creation | Signal published with correct payload |
| 9 | Signal failure | JetStream unavailable | Webhook returns 201, signal failure logged |

## Files Affected

| File | Action |
|------|--------|
| `src/observability/conventions.py` | Modify (add span names, attributes) |
| `src/ingress/generic_webhook.py` | Modify (add spans, logging, signal) |
| `src/ingress/webhook_handler.py` | Modify (set source_name="github") |
| `src/models/taskpacket.py` | Modify (add source_name column and fields) |
| `alembic/versions/*_add_source_name.py` | Create |
| `tests/ingress/sources/test_observability.py` | Create |

## Technical Notes

- The span hierarchy (receive as parent, others as children) provides a natural trace waterfall in Jaeger/Grafana. Each child span's duration shows where time is spent.
- `source_name` on TaskPacket is nullable to avoid breaking existing code that creates TaskPackets without it. The GitHub webhook handler is updated to set it explicitly, and the migration backfills existing rows.
- The JetStream signal follows the fire-and-forget pattern used in `src/outcome/signals.py`. Wrap the publish in a try/except, log on failure, do not re-raise. The webhook's job is to create the TaskPacket and start the workflow — signal emission is best-effort.
- Structured logging uses the project's existing `extra` dict pattern (see `webhook_handler.py` for reference).
