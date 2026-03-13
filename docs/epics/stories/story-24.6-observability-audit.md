# Story 24.6 — Approval Chat Observability + Audit

> **As a** platform operator,
> **I want** full observability and audit trails for approval interactions,
> **so that** compliance requirements are met and operational issues are diagnosable.

**Purpose:** The approval decision has real consequences — especially for Execute-tier repos where approval triggers auto-merge. Without observability and audit, there is no way to answer "who approved this, when, from where, and what information did they have?" This story adds OpenTelemetry spans, structured audit logging, evidence comment enrichment, and NATS JetStream signals for the outcome pipeline.

**Intent:** Instrument all approval chat interactions with spans and structured logs. Enrich the PR evidence comment with approval metadata. Emit NATS JetStream signals for approval outcomes.

**Points:** 5 | **Size:** M
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 2 (Stories 24.4-24.6)
**Depends on:** 24.3 (Chat API endpoints), 24.4 (Notification channels)

---

## Description

This story is cross-cutting. It adds instrumentation to code written in Stories 24.1-24.4 rather than creating new features. The three pillars are:

1. **OpenTelemetry spans** — Every significant operation (context assembly, message send, LLM call, approve, reject) gets a span with taskpacket_id and correlation_id.
2. **Evidence comment enrichment** — The PR evidence comment includes approval metadata: who approved/rejected, from which channel (web, API, Slack), and how many review chat messages preceded the decision.
3. **NATS JetStream signals** — `approval.approved` and `approval.rejected` subjects carry decision metadata for the outcome pipeline to ingest.

## Tasks

- [ ] Add OpenTelemetry spans to `src/approval/chat_router.py`:
  - `approval.review_context.build` span on GET /review (attributes: taskpacket_id, had_existing_chat)
  - `approval.chat.message.user` span on POST /messages — user message receipt (attributes: taskpacket_id, message_length)
  - `approval.chat.message.llm` span on POST /messages — LLM call (attributes: taskpacket_id, model_used, tokens_estimated, duration_ms)
  - `approval.action.approve` span on approve (attributes: taskpacket_id, approved_by, channel, message_count)
  - `approval.action.reject` span on reject (attributes: taskpacket_id, rejected_by, reason_length, channel, message_count)
  - All spans include `correlation_id` from the TaskPacket
- [ ] Add structured logging to approval actions:
  - `logger.info("approval.approved", extra={...})` with taskpacket_id, approved_by, channel, message_count, duration_since_awaiting
  - `logger.info("approval.rejected", extra={...})` with taskpacket_id, rejected_by, reason, channel, message_count
  - `logger.info("approval.timeout", extra={...})` with taskpacket_id, duration
  - `logger.info("approval.chat.message", extra={...})` with taskpacket_id, role, message_length
- [ ] Enrich evidence comment in `src/publisher/evidence_comment.py`:
  - Add optional `ApprovalMetadata` dataclass:
    - `approved_by: str | None`
    - `rejected_by: str | None`
    - `approval_channel: str` (web, api, slack)
    - `review_message_count: int`
    - `decision_time_seconds: int` (time from AWAITING_APPROVAL to decision)
  - Add `approval` parameter to `format_full_evidence_comment()`
  - When approval metadata is present, add section to evidence comment:
    ```
    ### Approval
    | Field | Value |
    |-------|-------|
    | **Decision** | Approved / Rejected |
    | **By** | {user} |
    | **Channel** | {channel} |
    | **Review Messages** | {count} |
    | **Decision Time** | {duration} |
    ```
- [ ] Emit NATS JetStream signals:
  - On approval: publish to `thestudio.approval.approved` with payload:
    - `taskpacket_id`, `approved_by`, `channel`, `review_message_count`, `decision_time_seconds`, `timestamp`
  - On rejection: publish to `thestudio.approval.rejected` with payload:
    - `taskpacket_id`, `rejected_by`, `reason`, `channel`, `review_message_count`, `decision_time_seconds`, `timestamp`
  - Use the existing NATS connection pattern from `src/outcome/` or `src/workflow/activities.py`
- [ ] Add approval settings to `src/settings.py`:
  - `approval_nats_subject_prefix: str = "thestudio.approval"` — subject prefix for approval signals
- [ ] Write tests in `tests/approval/test_observability.py`:
  - Test spans are created for each operation (use in-memory span exporter)
  - Test spans include correct attributes (taskpacket_id, correlation_id)
  - Test evidence comment includes approval section when metadata present
  - Test evidence comment omits approval section when metadata absent (backward compatible)
  - Test NATS signals are published on approval (mock NATS client)
  - Test NATS signals are published on rejection (mock NATS client)
  - Test structured log entries contain expected fields

## Acceptance Criteria

- [ ] All approval chat operations produce OpenTelemetry spans
- [ ] Spans include taskpacket_id and correlation_id
- [ ] Evidence comment includes approval metadata when available
- [ ] Evidence comment is unchanged when no approval metadata (backward compatible)
- [ ] NATS signals published for approval and rejection events
- [ ] Structured logs emitted for all approval actions
- [ ] Unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Approval spans | Approve action | Span with taskpacket_id, approved_by, channel |
| 2 | LLM call span | Chat message exchange | Span with model_used, tokens_estimated, duration_ms |
| 3 | Evidence with approval | format_full_evidence_comment with ApprovalMetadata | Comment includes "### Approval" section |
| 4 | Evidence without approval | format_full_evidence_comment without approval | No "### Approval" section (backward compat) |
| 5 | NATS approved signal | Approval action | Message on thestudio.approval.approved |
| 6 | NATS rejected signal | Rejection action | Message on thestudio.approval.rejected with reason |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/chat_router.py` | Modify — add spans and logging |
| `src/publisher/evidence_comment.py` | Modify — add ApprovalMetadata, approval section |
| `src/settings.py` | Modify — add NATS subject prefix |
| `tests/approval/test_observability.py` | Create |

## Technical Notes

- Use the existing OpenTelemetry tracer pattern: `tracer = trace.get_tracer(__name__)` and `with tracer.start_as_current_span("approval.action.approve") as span:`.
- The evidence comment enrichment must be backward compatible. The `approval` parameter defaults to `None`. When `None`, the approval section is omitted entirely.
- For NATS publishing, follow the pattern in existing signal emission code. If no NATS connection is available (e.g., in test or local dev), log and skip — do not fail the approval action.
- The `decision_time_seconds` is computed from `TaskPacket.updated_at` (when it entered AWAITING_APPROVAL) to the current time. This may require the TaskPacket's status transition timestamp — check if `updated_at` is sufficient or if a dedicated `awaiting_since` field is needed.
- Structured logging uses the project's standard pattern: `logger.info("event.name", extra={...})` with all fields as extra dict entries for structured log parsing.
