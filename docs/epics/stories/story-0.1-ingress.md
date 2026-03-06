# Story 0.1 -- Ingress: webhook receive, signature validation, dedupe

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** to receive GitHub issue webhook events, validate webhook signatures, and deduplicate by delivery ID + repo, **so that** every eligible issue enters the system exactly once and triggers a traceable workflow

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 1 (weeks 1-3)
**Depends on:** Story 0.2 (TaskPacket schema and CRUD)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Ingress component is the front door of TheStudio. It receives HTTP POST requests from GitHub webhooks when issue events occur, validates that the request actually came from GitHub (HMAC-SHA256 signature check), and ensures each event is processed exactly once (dedupe by delivery ID + repo).

On a valid new event:
1. Create a TaskPacket via Story 0.2 CRUD
2. Start a Temporal workflow with a correlation_id that follows the task through the entire pipeline
3. Return 201 Created

On a duplicate event (same delivery ID + repo already exists):
1. Return 200 OK without creating a new TaskPacket or workflow

On an invalid signature:
1. Return 401 Unauthorized without any side effects

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create HTTP endpoint for GitHub webhook POST (`src/ingress/webhook_handler.py`)
  - FastAPI or similar ASGI framework
  - Accept `application/json` content type
  - Read raw body for signature validation before parsing
- [ ] Implement webhook signature validation — HMAC-SHA256 (`src/ingress/signature.py`)
  - Read `X-Hub-Signature-256` header
  - Compare HMAC digest against repo's shared secret
  - Constant-time comparison to prevent timing attacks
- [ ] Implement delivery ID + repo dedupe check (`src/ingress/dedupe.py`)
  - Read `X-GitHub-Delivery` header
  - Query TaskPacket store for existing (delivery_id, repo) combination
  - Return early with 200 if duplicate
- [ ] Create TaskPacket on valid new event (`src/ingress/webhook_handler.py`)
  - Call TaskPacket CRUD (Story 0.2) to create record
  - Generate correlation_id (UUID v4)
  - Set initial status to "received"
- [ ] Start Temporal workflow with correlation_id (`src/ingress/workflow_trigger.py`)
  - Initialize Temporal client
  - Start workflow with TaskPacket ID and correlation_id
  - Use TaskPacket ID as workflow ID for idempotency
- [ ] Add OpenTelemetry span for ingress step (`src/ingress/webhook_handler.py`)
  - Span name: `ingress.webhook_receive`
  - Attributes: correlation_id, repo, delivery_id, outcome (created/duplicate/rejected)
- [ ] Write tests (`tests/test_ingress.py`)
  - Unit tests for signature validation
  - Unit tests for dedupe logic
  - Integration tests for full webhook flow

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Webhook endpoint accepts POST from GitHub and returns 200 or 201
- [ ] Invalid HMAC signature returns 401 and creates no TaskPacket
- [ ] Duplicate delivery ID + repo returns 200 and creates no new TaskPacket or workflow
- [ ] Valid new event creates exactly one TaskPacket with status "received"
- [ ] Valid new event starts exactly one Temporal workflow with matching correlation_id
- [ ] Temporal workflow ID equals TaskPacket ID (idempotency guarantee)
- [ ] OpenTelemetry span is emitted for every ingress request with correlation_id attribute
- [ ] Missing `X-GitHub-Delivery` header returns 400 Bad Request

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for signature validation (valid, invalid, missing header)
- [ ] Unit tests for dedupe (new event, duplicate event)
- [ ] Integration test: full webhook -> TaskPacket -> Temporal workflow
- [ ] Integration test: replay same delivery ID -> no duplicate
- [ ] Code passes ruff lint and mypy type check
- [ ] No hardcoded secrets (webhook secret from config/env)
- [ ] PR with evidence comment submitted

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Valid new webhook | POST with valid signature + new delivery ID | 201, TaskPacket created, workflow started |
| 2 | Duplicate webhook | POST with valid signature + existing delivery ID | 200, no new TaskPacket, no new workflow |
| 3 | Invalid signature | POST with wrong HMAC | 401, no TaskPacket |
| 4 | Missing delivery ID | POST with valid signature, no X-GitHub-Delivery | 400, no TaskPacket |
| 5 | Missing signature | POST with no X-Hub-Signature-256 header | 401, no TaskPacket |
| 6 | Non-issue event | POST with valid signature, event type = "push" | 200, no TaskPacket (not eligible) |
| 7 | OTel tracing | Any POST | Span emitted with correlation_id and outcome |
| 8 | Temporal idempotency | Start workflow with same TaskPacket ID twice | Second call is no-op (Temporal guarantees) |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **GitHub webhook headers:**
  - `X-Hub-Signature-256`: HMAC-SHA256 of the request body using the repo's webhook secret
  - `X-GitHub-Delivery`: Unique delivery ID (GUID) for each event
  - `X-GitHub-Event`: Event type (we filter for `issues`)
- **Signature validation:** Use `hmac.compare_digest()` for constant-time comparison (prevents timing attacks)
- **Temporal workflow ID:** Use TaskPacket ID as workflow ID — Temporal guarantees at-most-once start per workflow ID, giving us free idempotency
- **Correlation ID:** Generated as UUID v4 at ingress time, propagated through every downstream component via OpenTelemetry baggage and TaskPacket record
- **Architecture references:**
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 1: Intake)
  - Coding standards: `thestudioarc/20-coding-standards.md`

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/ingress/__init__.py` | Create | Package init |
| `src/ingress/webhook_handler.py` | Create | HTTP endpoint, request handling, orchestration |
| `src/ingress/signature.py` | Create | HMAC-SHA256 signature validation |
| `src/ingress/dedupe.py` | Create | Delivery ID + repo dedupe check |
| `src/ingress/workflow_trigger.py` | Create | Temporal workflow start |
| `tests/test_ingress.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.2 (TaskPacket):** Ingress creates TaskPackets — needs the model and CRUD operations
- **Story 0.9 (Observability):** OTel setup must be available for span emission (can be parallelized if OTel SDK is initialized independently)

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed once TaskPacket CRUD exists (Story 0.2)
- [x] **N**egotiable -- Implementation details (framework choice, error format) are flexible
- [x] **V**aluable -- Without ingress, nothing enters the system
- [x] **E**stimable -- 8 points, well-understood webhook pattern
- [x] **S**mall -- Completable within one sprint (webhook + validation + dedupe + tests)
- [x] **T**estable -- 8 test cases with clear pass/fail criteria

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
