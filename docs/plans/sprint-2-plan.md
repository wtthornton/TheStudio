# Sprint 2 Plan — Epic 0: Prove the Pipe

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-05
**Epic:** `docs/epics/epic-0-foundation.md`
**Sprint duration:** 3 weeks (weeks 4-6)
**Team:** 1-2 developers
**Predecessor:** Sprint 1 (complete — TaskPacket, Repo Profile, Ingress, Observability landed)

---

## Sprint Goal

**Objective:** Context Manager enriches TaskPackets with scope, risk flags, and Complexity Index v0; Intent Builder produces versioned Intent Specifications from enriched context; Verification Gate runs repo-profile checks and emits pass/fail signals to JetStream with loopback on failure — so that Sprint 3 stories (Primary Agent, Publisher) can implement against a clear intent and be verified against a deterministic gate.

**Test:** The sprint goal is met when:
1. Context Manager enriches a TaskPacket with scope, risk flags, complexity index, and context pack list; status transitions from "received" to "enriched" (7 test cases)
2. Intent Builder produces an Intent Specification (goal, constraints, acceptance criteria, non-goals) from an enriched TaskPacket; intent is versioned and persisted; status transitions from "enriched" to "intent_built" (8 test cases)
3. Verification Gate runs ruff + pytest checks, emits `verification_passed` / `verification_failed` / `verification_exhausted` signals to JetStream, triggers loopback on failure (max 2), and fails closed on runner error (8 test cases)
4. All code passes `ruff` lint and `mypy` type check
5. Database migrations for new fields run cleanly on existing Sprint 1 schema

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. No partial credit.

---

## Order of Work

### Phase A — Parallel foundations (week 4)

Stories 0.3 and 0.6 start in parallel on day 1. Their Sprint 1 dependencies are satisfied:
- 0.3 depends on 0.2 (TaskPacket) — landed Sprint 1
- 0.6 depends on 0.8 (Repo Profile) — landed Sprint 1

| Order | Story | Points | Size | Assignee | Rationale |
|-------|-------|--------|------|----------|-----------|
| 1 | **0.3 Context Manager** | 8 | L | Dev 1 | Unblocks 0.4 (Intent Builder). Must land before 0.4 can start. Critical path. |
| 2 | **0.6 Verification Gate** | 8 | L | Dev 2 (or Dev 1 after 0.3) | No dependency on 0.3 or 0.4. Can develop with mock inputs. Parallel path. |

**Parallel work:** If 2 developers, 0.3 and 0.6 run simultaneously in week 4. If 1 developer, 0.3 first (critical path — blocks 0.4), then 0.6.

### Phase B — Intent Builder (weeks 5-6)

| Order | Story | Points | Size | Assignee | Rationale |
|-------|-------|--------|------|----------|-----------|
| 3 | **0.4 Intent Builder** | 8 | L | Dev 1 (after 0.3 lands) | Serial dependency on 0.3. Gets weeks 5-6 — ample time for the 8-point story. |

**Dev 2 (if available):** Finishes 0.6 integration tests, helps with 0.4 integration, or starts Sprint 3 prep (reviewing 0.5 Primary Agent story, understanding Claude Agent SDK).

### Timeline (2 developers)

```
Week 4:  [Dev1: 0.3 Context Manager]  [Dev2: 0.6 Verification Gate]
Week 5:  [Dev1: 0.4 Intent Builder]   [Dev2: 0.6 integration + buffer]
Week 6:  [Dev1: 0.4 Intent Builder]   [Dev2: integration + Sprint 3 prep]
```

### Timeline (1 developer)

```
Week 4:  [0.3 Context Manager >>>>>>>>>>>>>>>]
Week 5:  [0.6 Verification Gate >>>>>>>>>>>>>>]
Week 6:  [0.4 Intent Builder >>>>>>>>] [buffer]
```

---

## Dependencies

| Story | Depends on | Dependency type | Status |
|-------|-----------|-----------------|--------|
| 0.3 Context Manager | 0.2 TaskPacket (CRUD + enrichment fields) | Code dependency | Landed Sprint 1 |
| 0.4 Intent Builder | 0.3 Context Manager (enriched TaskPacket) | Code dependency | Sprint 2 — critical path |
| 0.6 Verification Gate | 0.8 Repo Profile (required checks list) | Code dependency | Landed Sprint 1 |
| 0.6 Verification Gate | NATS JetStream (signal emission) | Infra dependency | Provisioned Sprint 1 |
| 0.6 Verification Gate | 0.5 Primary Agent (evidence bundle) | Soft dependency | Not needed — develop with mock inputs |

**Critical path:** 0.3 -> 0.4. The Verification Gate (0.6) is on a parallel path and does not block 0.4.

**No new external dependencies.** All infrastructure (PostgreSQL, Temporal, NATS, GitHub App) was provisioned in Sprint 1.

---

## Estimation Reasoning

### 0.3 Context Manager — 8 points (L)

- **Why this size:** Multiple analysis modules (scope analyzer, risk flagger, complexity scorer, service context pack stub). Keyword-based logic is straightforward but requires good test coverage for edge cases. Adds enrichment fields to TaskPacket model (migration). OTel instrumentation.
- **What's assumed:** TaskPacket CRUD is working (Sprint 1). Keyword-based detection is sufficient for Phase 0 (no ML).
- **What's unknown:** Issue text formats vary. Edge cases in scope analysis (empty body, minimal content, non-English). Thresholds for low/medium/high may need tuning.
- **Risk:** Low-medium. Pure logic — no external service integration.

### 0.4 Intent Builder — 8 points (L)

- **Why this size:** Structured extraction (goal, constraints, criteria, non-goals) from issue + enrichment. Intent versioning and persistence. Risk-flag-to-constraint mapping. New model + migration. OTel instrumentation.
- **What's assumed:** Context Manager output is available (serial dependency). Rule-based extraction is sufficient (no LLM in Phase 0 intent building).
- **What's unknown:** Quality of derived intent from varied issue formats. Whether rule-based goal extraction produces useful intents for Sprint 3's Primary Agent. This is the highest-judgment story in the sprint.
- **Risk:** Medium. The output quality determines whether Sprint 3's Primary Agent can implement effectively. Mitigation: review first 5 intents manually; adjust extraction heuristics before declaring done.

### 0.6 Verification Gate — 8 points (L)

- **Why this size:** Gate orchestrator + 2 check runners (ruff, pytest) + JetStream signal emission + loopback logic + fail-closed behavior. Multiple integration points. 8 test cases including runner crash scenario.
- **What's assumed:** NATS JetStream is running (Sprint 1 infra). Ruff and pytest are available in the execution environment.
- **What's unknown:** JetStream client library behavior for at-least-once delivery. Subprocess timeout and error handling edge cases.
- **Risk:** Medium. JetStream integration is new (Ingress used Temporal, not JetStream directly). Mitigation: spike JetStream publish/consume in first day; if problematic, use in-memory stub and file follow-up.

---

## Capacity and Buffer

| Item | Points |
|------|--------|
| Sprint 2 committed stories | 24 |
| Team capacity (1-2 devs x 3 weeks) | ~28-30 points |
| Buffer (integration, unknowns) | ~4-6 points (~17-20%) |

**Commitment ratio:** 24 / 30 = 80% (at the target ceiling).

**Buffer allocation:**
- JetStream integration learning curve: 1 day
- Intent quality review and heuristic tuning: 1 day
- TaskPacket migration for new fields: 0.5 day
- Integration testing across stories: 1 day
- Sprint 1 retro action items (if any): 0.5 day

**Note:** Sprint 2 is slightly tighter than Sprint 1 (80% vs 77%). All three stories are L (8 points each). If the team hits a blocker, 0.6 can be descoped to "gate logic + mock signals" (defer JetStream integration to Sprint 3 buffer). This is the release valve.

---

## What's Out (Not in Sprint 2)

| Story | Points | Sprint | Why not now |
|-------|--------|--------|-------------|
| 0.5 Primary Agent | 13 (XL) | Sprint 3 | Depends on 0.4 (Intent Builder) + 0.6 (Verification Gate) — both in this sprint |
| 0.7 Publisher | 8 (L) | Sprint 3 | Depends on 0.5 + 0.6 |

After Sprint 2, the remaining Epic 0 work is: 0.5 Primary Agent (13) + 0.7 Publisher (8) = 21 points for Sprint 3 + week 10 integration buffer. This fits the epic's 8-10 week timebox.

---

## Retro Actions from Sprint 1

**Sprint 1 retrospective not yet conducted.** This plan assumes Sprint 1 delivered as planned. If retro surfaces issues, Helm will amend this plan before Sprint 2 starts.

**Recommended retro questions for Sprint 1:**
1. Did infra setup (Docker Compose) take more or less than budgeted?
2. Did Temporal SDK integration cause friction (flagged as medium risk)?
3. Were test patterns established that Sprint 2 should follow?
4. Any tooling or process improvements for Sprint 2?

---

## Risks and Mitigations (Sprint 2 specific)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 0.3 blocks 0.4 (serial dependency) | Medium | High | 0.3 gets top priority and starts day 1. Dev 1 focuses exclusively on 0.3 in week 4. |
| JetStream integration friction in 0.6 | Medium | Medium | Spike on day 1. If problematic, stub signals and integrate in Sprint 3 buffer. |
| Intent quality too low for Sprint 3 agent | Medium | High | Manual review of first 5 generated intents. Tune heuristics before 0.4 is "done." |
| TaskPacket model changes break Sprint 1 code | Low | Medium | Migration must be additive (new nullable columns). Run Sprint 1 tests after migration. |
| 1-developer bottleneck on critical path | Low (2 devs) / High (1 dev) | Medium | 1-dev timeline puts 0.6 in week 5, 0.4 in week 6. Tight but feasible if 0.3 lands on time. |

---

## Definition of Done (Sprint Level)

The sprint is done when:
1. All 3 stories (0.3, 0.4, 0.6) meet their individual Definition of Done
2. All code passes `ruff` lint and `mypy` type check
3. Database migrations (enrichment fields, intent fields) run cleanly on Sprint 1 schema
4. Integration test: TaskPacket created (Sprint 1) -> enriched by Context Manager -> intent built by Intent Builder -> status chain: received -> enriched -> intent_built
5. Integration test: Verification Gate runs checks, emits JetStream signal, triggers loopback on failure, fails closed on error
6. Sprint 1 tests still pass (no regression from model changes)

---

## Async-Readability Notes

**For anyone reading this later (human or AI):**

- Sprint 2 builds the middle of the pipe: enrichment (Context Manager), intent definition (Intent Builder), and verification (Verification Gate).
- After Sprint 2, the system can: receive a webhook (Sprint 1) -> create a TaskPacket (Sprint 1) -> enrich it with scope/risk/complexity (Sprint 2) -> build an Intent Specification (Sprint 2) -> verify code changes against repo checks (Sprint 2). But there is no agent implementing yet (Sprint 3) and no PR publishing yet (Sprint 3).
- The critical path is: 0.3 Context Manager -> 0.4 Intent Builder. The Verification Gate (0.6) is on a parallel path.
- If something is blocked, check: (1) did 0.3 land? (2) is JetStream running? (3) did TaskPacket migration run?
- Sprint 3 starts immediately on 0.5 (Primary Agent) and 0.7 (Publisher) once Sprint 2 is done.

---

*Plan created by Helm. Pending Meridian review before commit.*
