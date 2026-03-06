# Story 0.9 -- Observability: OpenTelemetry tracing with correlation_id

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform operator, **I want** OpenTelemetry tracing across all pipeline steps with correlation_id propagation, **so that** every task can be traced end-to-end from ingress to publish and performance issues can be diagnosed

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 1 (weeks 1-3)
**Depends on:** None (parallel with other Sprint 1 stories)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

Observability is a cross-cutting concern that instruments every pipeline step. This story sets up the OpenTelemetry SDK, defines span conventions, and ensures correlation_id is propagated through the entire flow.

**What gets instrumented:**
- `ingress.webhook_receive` — Ingress (Story 0.1)
- `context.enrich` — Context Manager (Story 0.3)
- `intent.build` — Intent Builder (Story 0.4)
- `agent.implement` + `agent.loopback` — Primary Agent (Story 0.5)
- `verification.run` + `verification.check` — Verification Gate (Story 0.6)
- `publisher.publish` — Publisher (Story 0.7)

**correlation_id** is generated at ingress (UUID v4) and propagated via:
1. TaskPacket record (stored as field)
2. OpenTelemetry baggage (for cross-process propagation)
3. Span attributes (for querying)

**Phase 0 export target:** Console exporter for local dev, OTLP exporter for staging/production (e.g., Jaeger, Grafana Tempo).

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Set up OpenTelemetry SDK (`src/observability/tracing.py`)
  - Initialize TracerProvider with configurable exporter (console, OTLP)
  - Configure resource attributes (service.name="thestudio", service.version)
  - Set up propagator (W3C TraceContext + baggage)
- [ ] Define span conventions (`src/observability/conventions.py`)
  - Span name patterns: `{component}.{action}` (e.g., `ingress.webhook_receive`)
  - Standard attributes: correlation_id, taskpacket_id, repo, status, outcome
  - Error recording convention
- [ ] Implement correlation_id propagation (`src/observability/correlation.py`)
  - Generate correlation_id at ingress
  - Store in OTel baggage for cross-process propagation
  - Helper to extract correlation_id from context
  - Helper to add correlation_id to span attributes
- [ ] Implement tracing middleware for HTTP (`src/observability/middleware.py`)
  - Auto-instrument incoming HTTP requests (ingress webhook)
  - Extract trace context from incoming headers
  - Add correlation_id to all child spans
- [ ] Implement Temporal activity tracing (`src/observability/temporal_tracing.py`)
  - Propagate trace context through Temporal workflows and activities
  - Ensure spans link across workflow boundaries
- [ ] Configure exporters (`src/observability/exporters.py`)
  - Console exporter for local development
  - OTLP exporter for staging/production
  - Configuration via environment variables (OTEL_EXPORTER_OTLP_ENDPOINT)
- [ ] Write tests (`tests/test_observability.py`)
  - Unit test: correlation_id generation and extraction
  - Unit test: span creation with standard attributes
  - Integration test: trace propagation across function calls
  - Integration test: baggage propagation

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] OpenTelemetry SDK initialized on application startup
- [ ] Every pipeline step emits a span with the correct name convention
- [ ] correlation_id is present as an attribute on every span in a task's trace
- [ ] Traces are queryable by correlation_id in the configured backend
- [ ] Console exporter works for local development (visible in stdout)
- [ ] OTLP exporter configurable via environment variable
- [ ] Temporal workflow/activity spans are linked in the same trace

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for correlation_id generation and baggage propagation
- [ ] Unit tests for span creation with standard attributes
- [ ] Integration test: end-to-end trace across 2+ components
- [ ] Console exporter verified in local dev
- [ ] Code passes ruff lint and mypy type check

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | SDK initialization | App startup | TracerProvider configured, no errors |
| 2 | Span creation | Call tracer.start_span("ingress.webhook_receive") | Span with correct name and attributes |
| 3 | correlation_id propagation | Set in ingress, read in verification | Same UUID in both spans |
| 4 | Baggage propagation | Set correlation_id in baggage | Extractable in downstream context |
| 5 | Console export | Local dev, emit span | Span visible in stdout |
| 6 | OTLP export | Set OTEL_EXPORTER_OTLP_ENDPOINT | Span sent to configured endpoint |
| 7 | Error recording | Exception during span | Span status=ERROR, exception recorded |
| 8 | Temporal tracing | Workflow -> activity | Both spans in same trace |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **OpenTelemetry Python SDK:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`
- **Auto-instrumentation** available for FastAPI, httpx, SQLAlchemy — consider enabling for HTTP and DB spans
- **Temporal tracing** requires custom interceptor to propagate trace context through workflow/activity boundaries
- **Span naming** follows OTel semantic conventions where applicable, custom `{component}.{action}` pattern for TheStudio-specific spans
- **Architecture references:**
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Observability: correlation_id on all spans)
  - Overview: `thestudioarc/00-overview.md` (OpenTelemetry traces)

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/observability/__init__.py` | Create | Package init |
| `src/observability/tracing.py` | Create | SDK setup and TracerProvider |
| `src/observability/conventions.py` | Create | Span naming and attribute conventions |
| `src/observability/correlation.py` | Create | correlation_id generation and propagation |
| `src/observability/middleware.py` | Create | HTTP tracing middleware |
| `src/observability/temporal_tracing.py` | Create | Temporal trace context propagation |
| `src/observability/exporters.py` | Create | Exporter configuration |
| `tests/test_observability.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **None** — Observability is a cross-cutting concern that can be developed in parallel
- **Consumed by:** All other stories (0.1-0.7) import from `src/observability/`

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No upstream dependencies; can start immediately and in parallel
- [x] **N**egotiable -- Exporter choice, attribute list, auto-instrumentation scope are flexible
- [x] **V**aluable -- Without tracing, debugging production issues is guesswork
- [x] **E**stimable -- 5 points, well-documented OTel SDK setup
- [x] **S**mall -- Completable in 2-3 days
- [x] **T**estable -- 8 test cases with in-memory exporter for verification

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
