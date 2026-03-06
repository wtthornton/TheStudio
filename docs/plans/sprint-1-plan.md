# Sprint 1 Plan — Epic 0: Prove the Pipe

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-05
**Epic:** `docs/epics/epic-0-foundation.md`
**Sprint duration:** 3 weeks (weeks 1-3)
**Team:** 1-2 developers (self-provisioning infra)

---

## Sprint Goal

**Objective:** All foundational data models, configuration, ingress endpoint, and observability instrumentation are implemented, tested, and passing CI checks — so that Sprint 2 stories (Context Manager, Intent Builder, Verification Gate) can build on proven schemas, working persistence, and a live webhook endpoint.

**Test:** The sprint goal is met when:
1. TaskPacket CRUD passes all 8 test cases (create, dedupe, get, update, constraint enforcement)
2. Repo Profile CRUD passes all 8 test cases (register, dedupe, get, tier update, secret roundtrip, defaults)
3. Ingress webhook endpoint passes all 8 test cases (valid event -> TaskPacket + workflow, dedupe -> 200, invalid sig -> 401, missing header -> 400)
4. OpenTelemetry SDK initializes, spans emit to console exporter, correlation_id propagates across function calls
5. All code passes `ruff` lint and `mypy` type check
6. Database migrations run cleanly on a fresh PostgreSQL instance

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. No partial credit.

---

## Order of Work

### Phase A — Foundations (week 1)

Stories 0.2 and 0.8 start in parallel on day 1. They have zero dependencies and are the foundation for everything else.

| Order | Story | Points | Size | Assignee | Rationale |
|-------|-------|--------|------|----------|-----------|
| 1 | **0.2 TaskPacket schema** | 5 | M | Dev 1 | Everything downstream reads/writes TaskPackets. Must land first. |
| 2 | **0.8 Repo Profile** | 5 | M | Dev 2 (or Dev 1 after 0.2) | Ingress needs webhook secret; Verification Gate needs required checks; Agent needs tool allowlist. No deps — start immediately. |

**Parallel work:** If 2 developers, 0.2 and 0.8 run simultaneously in week 1. If 1 developer, 0.2 first (2-3 days), then 0.8 (2-3 days).

**Infra setup (week 1, parallel):** PostgreSQL (local Docker), Temporal server (local Docker), NATS JetStream (local Docker), GitHub App created and installed on target repo. This is not a story — it's setup work that unblocks all stories. Budget 1-2 days. Per epic Context & Assumptions: self-provisioned by the implementation team.

### Phase B — Ingress + Observability (weeks 2-3)

| Order | Story | Points | Size | Assignee | Rationale |
|-------|-------|--------|------|----------|-----------|
| 3 | **0.9 Observability** | 5 | M | Dev 2 (or Dev 1 after 0.8) | No deps. Start early so Ingress can import tracing helpers. Parallel with 0.1 if 2 devs. |
| 4 | **0.1 Ingress** | 8 | L | Dev 1 (after 0.2 lands) | Depends on 0.2 (TaskPacket CRUD) and reads from 0.8 (webhook secret). Largest story in sprint — gets the most time. |

**Parallel work:** If 2 developers, 0.9 and 0.1 start simultaneously in week 2 (0.1 can begin once 0.2 is merged). If 1 developer, 0.9 first (2-3 days), then 0.1 (4-5 days).

### Timeline (2 developers)

```
Week 1:  [Dev1: 0.2 TaskPacket]  [Dev2: 0.8 Repo Profile]  [Both: infra setup]
Week 2:  [Dev1: 0.1 Ingress >>>] [Dev2: 0.9 Observability]
Week 3:  [Dev1: 0.1 Ingress >>>] [Dev2: integration + buffer]
```

### Timeline (1 developer)

```
Week 1:  [0.2 TaskPacket] [0.8 Repo Profile] [infra setup]
Week 2:  [0.9 Observability] [0.1 Ingress >>>>>>>>>>>>>>>]
Week 3:  [0.1 Ingress >>>>>>>] [integration + buffer]
```

---

## Dependencies

| Story | Depends on | Dependency type | Status |
|-------|-----------|-----------------|--------|
| 0.2 TaskPacket | None | -- | Ready to start |
| 0.8 Repo Profile | None | -- | Ready to start |
| 0.1 Ingress | 0.2 TaskPacket (CRUD for creating TaskPackets) | Code dependency | Confirmed in story |
| 0.1 Ingress | 0.8 Repo Profile (webhook secret for signature validation) | Code dependency | Confirmed in story |
| 0.1 Ingress | 0.9 Observability (OTel SDK for span emission) | Soft dependency | Can stub initially; integrate when 0.9 lands |
| 0.9 Observability | None | -- | Ready to start |
| All stories | Infra (PostgreSQL, Temporal, NATS, GitHub App) | Environment dependency | Self-provisioned week 1 |

**No external dependencies.** All infrastructure is self-provisioned by the implementation team (per epic Context & Assumptions, Gap D resolution).

---

## Estimation Reasoning

### 0.2 TaskPacket — 5 points (M)
- **Why this size:** Standard CRUD + schema pattern. Pydantic model, SQLAlchemy ORM, one migration, 5 CRUD operations, 8 test cases. Well-understood pattern.
- **What's assumed:** PostgreSQL is available (infra setup week 1). SQLAlchemy 2.0+ with async. Pydantic v2.
- **What's unknown:** Nothing significant — this is a standard data model story.
- **Reference:** Comparable to a typical model+migration+CRUD story.

### 0.8 Repo Profile — 5 points (M)
- **Why this size:** Same CRUD pattern as 0.2, plus webhook secret encryption (Fernet). Slightly more complex model (JSON fields for checks/allowlist, encrypted secret), but well-understood.
- **What's assumed:** Fernet or similar symmetric encryption for secrets at rest. Encryption key from environment variable.
- **What's unknown:** Exact tool allowlist values may evolve as Story 0.5 (Primary Agent) is developed in Sprint 3. Defaults are sufficient for now.
- **Risk:** Low. Secret encryption adds a small task but Fernet is well-documented.

### 0.1 Ingress — 8 points (L)
- **Why this size:** Webhook handler + HMAC signature validation + dedupe + Temporal workflow trigger + OTel span. Multiple integration points (TaskPacket CRUD, Repo Profile, Temporal client, OTel). 8 test cases including integration tests requiring Temporal.
- **What's assumed:** FastAPI for HTTP. Temporal Python SDK. GitHub webhook format is stable and well-documented.
- **What's unknown:** Temporal client setup complexity. If Temporal SDK has friction, this is where it shows up.
- **Risk:** Medium. This is the first story that integrates multiple components (TaskPacket, Repo Profile, Temporal, OTel). Integration test setup for Temporal workflows may take longer than expected.
- **Mitigation:** Start Temporal integration early in week 2. If Temporal client is problematic, stub the workflow trigger and file a follow-up task.

### 0.9 Observability — 5 points (M)
- **Why this size:** OTel SDK setup is well-documented. Span conventions, correlation_id helpers, middleware, exporter config. Most work is boilerplate following OTel Python SDK docs.
- **What's assumed:** Console exporter for dev, OTLP for staging. Temporal tracing interceptor available in Temporal Python SDK.
- **What's unknown:** Temporal trace context propagation may require a custom interceptor. The OTel Temporal integration for Python may be less mature than expected.
- **Risk:** Low-medium. Temporal tracing is the only area with uncertainty. Core OTel setup is straightforward.

---

## Capacity and Buffer

| Item | Points |
|------|--------|
| Sprint 1 committed stories | 23 |
| Team capacity (1-2 devs x 3 weeks) | ~28-30 points |
| Buffer (infra setup, integration, unknowns) | ~5-7 points (~20-25%) |

**Commitment ratio:** 23 / 30 = 77% (within 80% target).

**Buffer allocation:**
- Infra setup (PostgreSQL, Temporal, NATS, GitHub App): 1-2 days
- Integration testing across stories: 1-2 days
- Temporal SDK learning curve: 1 day
- Unknowns / blocked time: 1 day

If capacity is 1 developer: 23 points across 3 weeks is tight but feasible. The stories are M/M/M/L (5+5+5+8). Two M stories can overlap if scope allows, and the L story (Ingress) gets the bulk of weeks 2-3.

---

## What's Out (Not in Sprint 1)

| Story | Points | Sprint | Why not now |
|-------|--------|--------|-------------|
| 0.3 Context Manager | 8 (L) | Sprint 2 | Depends on 0.2 (TaskPacket) — could start Sprint 2 day 1 |
| 0.4 Intent Builder | 8 (L) | Sprint 2 | Depends on 0.3 (Context Manager) |
| 0.6 Verification Gate | 8 (L) | Sprint 2 | Depends on 0.8 (Repo Profile) — could start Sprint 2 day 1 |
| 0.5 Primary Agent | 13 (XL) | Sprint 3 | Depends on 0.4 + 0.6. Must be sub-tasked per Meridian note. |
| 0.7 Publisher | 8 (L) | Sprint 3 | Depends on 0.5 + 0.6 |

---

## Retro Actions

**N/A** — This is Sprint 1. No prior retrospective. Retro will be conducted at end of Sprint 1 and actions will feed into Sprint 2 plan.

---

## Risks and Mitigations (Sprint 1 specific)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Infra setup takes longer than 2 days | Low | Medium | Use Docker Compose for all services. Pre-build compose file as first task. |
| Temporal Python SDK friction | Medium | Medium | Start Temporal integration early week 2. Stub workflow trigger if needed. |
| 0.1 Ingress integration complexity | Medium | Medium | 0.1 is last in order — has most time. Soft-depend on 0.9 (can stub OTel). |
| Single developer bottleneck | Low (if 2 devs) / High (if 1 dev) | Medium | 0.2 and 0.8 have no deps and can parallelize. Critical path is 0.2 -> 0.1. |

---

## Definition of Done (Sprint Level)

The sprint is done when:
1. All 4 stories (0.2, 0.8, 0.1, 0.9) meet their individual Definition of Done
2. All code passes `ruff` lint and `mypy` type check
3. All database migrations run cleanly on fresh PostgreSQL
4. Integration test: Ingress webhook -> TaskPacket created -> Temporal workflow started -> OTel span emitted with correlation_id
5. Infrastructure (PostgreSQL, Temporal, NATS, GitHub App) is running and accessible for Sprint 2 stories

---

## Async-Readability Notes

**For anyone reading this later (human or AI):**

- Sprint 1 builds the data layer (TaskPacket, Repo Profile), the entry point (Ingress), and the instrumentation (Observability).
- After Sprint 1, the system can receive a GitHub webhook, create a TaskPacket, start a Temporal workflow, and emit traced spans — but the workflow does nothing yet (Context Manager, Intent Builder, Agent, Verification, Publisher are Sprint 2-3).
- The critical path is: infra setup -> 0.2 TaskPacket -> 0.1 Ingress. Everything else is parallel.
- If something is blocked, check: (1) is PostgreSQL running? (2) is Temporal running? (3) did 0.2 land?
- Sprint 2 can start immediately on 0.3 (Context Manager) and 0.6 (Verification Gate) once Sprint 1 is done.

---

*Plan created by Helm. Pending Meridian review before commit.*
