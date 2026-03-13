# Sprint Roadmap: Epics 15–22 Prioritized Execution Plan

**Planned by:** Helm
**Date:** 2026-03-12
**Status:** Meridian R1 PASS — Committable (4 gaps fixed)
**Scope:** All open epics (15, 16, 17, 18, 19, 20, 21, 22)
**Capacity:** Single developer, 80% commitment per sprint (8 effective days / 10 available)

---

## Executive Summary

8 open epics. 4 sprints to reach Execute tier (Epic 22). The critical path runs:

```
Sprint 18: Epic 15 (E2E integration) + Epic 19 streams B+C
Sprint 19: Epic 19 stream A + Epic 20 (parallel safety nets)
Sprint 20: Epic 21 (human approval wait states)
Sprint 21: Epic 22 (Execute tier end-to-end)
-- Deferred --
Sprint 22+: Epic 17 (poll intake) + Epic 18 (test suite expansion)
```

Epic 16 (Issue Readiness Gate) already has Sprint 17 plan committed. Work begins 2026-03-17.

---

## Sprint 17 (2026-03-17 → 2026-03-28) — ALREADY PLANNED

**Epic:** 16 — Issue Readiness Gate (Stories 16.1–16.4)
**Plan:** `docs/epics/epic-16-sprint-17-plan.md`
**Goal:** Deliver readiness scoring engine + pipeline integration + clarification comment output.

| Story | Estimate | Confidence |
|-------|----------|------------|
| 16.1: Data model + config | 1 day | 90% |
| 16.2: Scoring engine | 2 days | 80% |
| 16.3: Pipeline integration | 2 days | 70% |
| 16.4: Clarification comment | 1 day | 90% |
| Buffer | 2 days | — |
| **Total** | **8 days** | |

No changes to this plan. Proceed as documented.

**Sprint 17 → Sprint 18 relationship:** Sprint 18 is **independent of Sprint 17**. Epic 16 (readiness gate) inserts a new activity between Context and Intent in the Temporal workflow, guarded by a feature flag that defaults to off. Sprint 18's work (integration tests, security runner, reputation DB) does not touch the workflow insertion point or the readiness module. Sprint 19's Story 20.10, which modifies `src/ingress/webhook_handler.py`, must be rebased on any Sprint 17 changes to that file — but Sprint 17 does not modify `webhook_handler.py` (it adds `readiness_gate_enabled` to `PipelineInput`, resolved by the caller). No blocking dependency exists.

---

## Sprint 18 (2026-03-31 → 2026-04-11) — E2E Integration + Security/Reputation

### Sprint Goal (Testable)

**Objective:** Complete Epic 15 (E2E integration tests with realistic mock providers) AND deliver Epic 19 Streams B+C (security scan runner + reputation persistence). By sprint end:
1. `pytest tests/integration/test_full_pipeline.py` passes with all 9 stages connected and realistic data.
2. `pytest tests/integration/test_pipeline_workflow.py` includes `TestRealisticPipeline` class with data-fidelity assertions.
3. Loopback tests verify gate-fails-closed with realistic mock data.
4. Evidence comment validation covers all 7 required sections with pipeline-produced data.
5. Pipeline latency baseline documented in `docs/pipeline-latency-baseline.md`.
6. Onboarding guide in `docs/ONBOARDING.md` covers all 7 sections including GitHub App setup and tier explanation.
7. `src/verification/runners/security_runner.py` exists, runs `bandit`, and is wired into the verification gate.
8. Reputation engine reads/writes to PostgreSQL; weights survive application restart.
9. `ruff check` and `mypy` pass on all new/modified files.
10. All existing tests pass (zero regressions).

**Test:** After all stories complete:
- `pytest tests/integration/ -v` — all integration tests pass
- `pytest tests/verification/test_security_runner.py` — security runner tests pass
- `pytest tests/reputation/test_engine_persistence.py` — persistence roundtrip + restart survival tests pass
- `pytest` (full suite) — zero regressions

### Why This Pairing

Epic 15 (integration tests) and Epic 19 Streams B+C (security runner, reputation DB) are **independent work streams** with no code overlap. Epic 15 touches `tests/integration/` and `docs/`. Stream B touches `src/verification/runners/`. Stream C touches `src/reputation/`. No conflicts. Stream A (gateway wiring) is deferred to Sprint 19 because it touches `src/agent/primary_agent.py`, which overlaps with Epic 20's escalation work — batching them reduces merge conflicts.

### Ordered Backlog

#### Days 1–3: Epic 15 (Stories 15.1–15.3)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 1 | **15.1: Mock Provider Harness** | Create `tests/integration/conftest.py` with shared fixtures; create `tests/integration/mock_providers.py` with realistic mock activities | `tests/integration/conftest.py`, `tests/integration/mock_providers.py` |
| 2 | **15.2: Full Pipeline Smoke** | Create `test_full_pipeline.py` — single test wiring all 9 stages with mock providers, asserting each stage produces valid output | `tests/integration/test_full_pipeline.py` |
| 3 | **15.3: Loopback Tests** | Extend `test_pipeline_workflow.py` with realistic-data loopback tests — verification retry, exhaustion, QA retry | `tests/integration/test_pipeline_workflow.py` |

#### Days 3–5: Epic 19 Stream B (Security Runner) — Interleaved with Epic 15

**Single-developer note:** "Parallel" means interleaved, not concurrent. Day 3 completes Story 15.3 (loopback tests) first, then begins Story B1 (security runner). Days 4–5 alternate between streams based on natural stopping points. The day assignments below show the primary focus for each day — the developer works one story at a time, sequentially, but may switch streams between stories within a day.

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 3 | **B1: Security runner** | Implement `run_security_scan()` following `ruff_runner.py` pattern | `src/verification/runners/security_runner.py` |
| 4 | **B2: Wire into gate** | Add `"security"` to `_RUNNERS` map in gate.py | `src/verification/gate.py` |
| 4 | **B3: Add bandit dep** | Add bandit to pyproject.toml dev extras | `pyproject.toml` |
| 4 | **B4: Security runner tests** | Pass/fail, missing binary, timeout, gate dispatch | `tests/verification/test_security_runner.py`, `tests/verification/test_gate_security.py` |

#### Days 4–6: Epic 15 (Stories 15.4–15.5)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 5 | **15.4: Evidence Comment Validation** | Extend `test_evidence_validation.py` with `format_full_evidence_comment` tests using pipeline-produced data | `tests/integration/test_evidence_validation.py` |
| 5 | **15.5: Temporal Data-Fidelity Test** | Add `TestRealisticPipeline` class to `test_pipeline_workflow.py` using mock providers | `tests/integration/test_pipeline_workflow.py` |

#### Days 5–7: Epic 19 Stream C (Reputation Persistence)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 5 | **C1: SQLAlchemy model** | ORM model for `expert_reputation`; migration 019 if schema gap exists | `src/reputation/db_models.py`, `src/db/migrations/019_reputation_weight_history.py` |
| 6 | **C2+C3: DB write + read paths** | Write-through to DB; cache-first reads with DB fallback | `src/reputation/engine.py` |
| 6 | **C4: Drift history from DB** | JSONB weight history; load on cache miss | `src/reputation/engine.py`, `src/reputation/db_models.py` |
| 7 | **C5+C6: AsyncSession + Tests** | Wire async sessions; roundtrip, restart, drift, concurrent update tests | `src/reputation/engine.py`, `tests/reputation/test_engine_persistence.py` |

#### Days 7–8: Epic 15 (Stories 15.6–15.7) + Buffer

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 7 | **15.6: Latency Baseline** | Add timing instrumentation; create baseline doc | `tests/integration/test_full_pipeline.py`, `docs/pipeline-latency-baseline.md` |
| 8 | **15.7: Onboarding Guide** | Extend `docs/ONBOARDING.md` with 7 sections | `docs/ONBOARDING.md` |

### Estimation Summary

| Work Stream | Stories | Days | Confidence |
|-------------|---------|------|------------|
| Epic 15 (E2E integration) | 15.1–15.7 | 5 | 80% |
| Epic 19 Stream B (security runner) | B1–B4 | 1.5 | 85% |
| Epic 19 Stream C (reputation DB) | C1–C6 | 2.5 | 75% |
| Buffer | — | 1 | — |
| **Total** | **17 stories** | **10 days** | |

### Risk: Stream C (Reputation DB)

Reputation persistence is the highest-risk stream. The migration 008 schema may diverge from current models. The async write-through cache pattern is new to this codebase. Mitigation: compare schema before writing code; keep the in-memory engine as fallback.

---

## Sprint 19 (2026-04-14 → 2026-04-25) — Gateway Wiring + Pipeline Safety Nets

### Sprint Goal (Testable)

**Objective:** Complete Epic 19 Stream A (wire Model Gateway into Primary Agent) AND deliver Epic 20 (JetStream consumption, escalation triggers, adversarial input detection). By sprint end:
1. `primary_agent.implement()` calls `ModelRouter.select_model()` — zero direct `settings.agent_model` references in agent call paths.
2. Budget check runs before every agent invocation; spend recorded after.
3. `ModelCallAudit` records created for every agent call.
4. Fallback chain activates on provider failure.
5. JetStream consumer subscribes to verification + QA streams with durable subscriptions.
6. `EscalationRequest` model exists; Router and Assembler emit escalations for high-risk conflicts.
7. `detect_suspicious_patterns()` blocks adversarial input at intake.
8. All existing tests pass.

### Ordered Backlog

#### Days 1–3: Epic 19 Stream A (Gateway Wiring)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 1 | **A1: Gateway-aware DeveloperRoleConfig** | Refactor `implement()` and `handle_loopback()` to call `ModelRouter.select_model()` | `src/agent/primary_agent.py`, `src/agent/developer_role.py` |
| 2 | **A2+A3: Budget check + spend recording** | `check_budget()` before `_run_agent()`; `record_spend()` after | `src/agent/primary_agent.py` |
| 2 | **A4: Audit records** | Create `ModelCallAudit` per invocation | `src/agent/primary_agent.py` |
| 3 | **A5: Fallback on failure** | Try/except with `select_with_fallback()` retry | `src/agent/primary_agent.py` |
| 3 | **A6: Gateway wiring tests** | Routing context, budget blocks, spend recorded, audit exists, fallback | `tests/agent/test_primary_agent_gateway.py` |

#### Days 3–5: Epic 20 Slice 1+2 (Foundation + Core Integration)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 3 | **20.1: EscalationRequest model** | Dataclass with severity, risk domain, source | `src/models/escalation.py` |
| 4 | **20.2: Adversarial pattern detector** | `detect_suspicious_patterns()` with configurable pattern list | `src/intake/adversarial.py` |
| 4 | **20.3: JetStream consumer** | `start_signal_consumer()` with durable subscriptions | `src/outcome/consumer.py` |
| 5 | **20.4: Router escalation** | `escalations` field on `ConsultPlan`; governance conflict detection | `src/routing/router.py` |
| 5 | **20.5: Assembler escalation** | `escalations` field on `AssemblyPlan`; high-risk unresolved conflict detection | `src/assembler/assembler.py` |

#### Days 6–7: Epic 20 Slice 2+3 (Integration + Wiring)

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 6 | **20.6: Intake adversarial integration** | Add `issue_title`/`issue_body` params to `evaluate_eligibility()` | `src/intake/intake_agent.py` |
| 6 | **20.7: Escalation handler** | `handle_escalation()` with structured logging + pause signal | `src/routing/escalation.py` |
| 7 | **20.8: Compliance adversarial wrapper** | Thin wrapper on `detect_suspicious_patterns()` | `src/compliance/checker.py` |
| 7 | **20.9: Wire consumer to app startup** | FastAPI lifespan start/stop | `src/app.py` |

#### Days 8–10: Epic 20 Slice 4 + Buffer

| Day | Story | Work | Files |
|-----|-------|------|-------|
| 8 | **20.10: Update intake callers** | Pass `issue_title`/`issue_body` through workflow + webhook handler | `src/workflow/activities.py`, `src/ingress/webhook_handler.py` |
| 8 | **20.11: Integration test: signal path** | Emit verification signal → consumer → `get_signals()` | `tests/test_integration/test_signal_path.py` |
| 9 | **20.12: Documentation update** | Mark C1, C3, C4, C5, C7, C8 as IMPLEMENTED in mapping doc | `docs/architecture-vs-implementation-mapping.md` |
| 9-10 | **Buffer** | Integration testing, edge cases, regressions | — |

### Estimation Summary

| Work Stream | Stories | Days | Confidence | Key Risk |
|-------------|---------|------|------------|----------|
| Epic 19 Stream A (gateway) | A1–A6 | 3 | 80% | `DeveloperRoleConfig` construction order — must create config after gateway selection |
| Epic 20 20.1–20.2 (foundation) | 2 | 1 | 90% | Pure data model + pattern matching — low risk |
| Epic 20 20.3 (JetStream consumer) | 1 | 1 | 65% | New infrastructure pattern — durable subscriptions, ack/nack semantics, graceful shutdown |
| Epic 20 20.4 (Router escalation) | 1 | 0.5 | 70% | Non-trivial conditional logic — must detect conflicting governance rules across `EffectiveRolePolicy` mandatory expert classes with contradictory `intent_constraints`. Requires understanding the intersection of risk flags, confidence scores, and budget exhaustion |
| Epic 20 20.5 (Assembler escalation) | 1 | 0.5 | 80% | Simpler than 20.4 — detection keyed on `resolved_by="unresolved"` + risk domain match |
| Epic 20 20.6–20.8 (intake + handler + compliance) | 3 | 1.5 | 85% | Straightforward integration — parameter additions with defaults |
| Epic 20 20.9–20.12 (wiring + tests + docs) | 4 | 1.5 | 80% | Consumer startup is standard FastAPI lifespan; integration test needs NATS |
| Buffer | — | 2 | — | Primary consumer: 20.3 or 20.4 overrun |
| **Total** | **18 stories** | **10 days** | |

### Risks

**JetStream Consumer (20.3):** New infrastructure pattern. Durable subscriptions, ack/nack semantics, and graceful shutdown are all first-time patterns in this codebase. Integration test requires running NATS — unit tests with mocked JetStream provide fallback coverage. `pytest.mark.integration` and clean skip when NATS unavailable.

**Router Escalation (20.4):** The governance conflict detection requires evaluating `EffectiveRolePolicy` mandatory expert classes for contradictory `intent_constraints`. This is not a simple field check — it requires set intersection logic across expert class requirements. If the conditional complexity exceeds the 0.5-day estimate, buffer absorbs the overrun.

---

## Sprint 20 (2026-04-28 → 2026-05-09) — Human Approval Wait States

### Sprint Goal (Testable)

**Objective:** Deliver Epic 21 — Temporal workflow pause between QA and Publish for Suggest/Execute tiers. By sprint end:
1. Spike document exists in `docs/spikes/spike-temporal-signals-and-timers.md` with proven patterns.
2. `TaskPacketStatus` includes `AWAITING_APPROVAL` and `AWAITING_APPROVAL_EXPIRED` with correct transitions.
3. Suggest/Execute tier workflows enter a durable wait state after QA pass.
4. `approve_publish` signal resumes the workflow and proceeds to Publish.
5. 7-day timeout triggers escalation — workflow does NOT publish.
6. `POST /api/tasks/{taskpacket_id}/approve` endpoint returns correct status codes (200/404/409).
7. Temporal time-skipping tests validate 7-day timeout in under 30 seconds.
8. Observe tier workflows are completely unchanged.

### Ordered Backlog

| Day | Story | Work | Estimate |
|-----|-------|------|----------|
| 1–2 | **Story 0: Spike** | Temporal signals, wait_condition, timers, time-skipping tests; documented findings | S (2 days) |
| 3 | **Story 1: TaskPacket status extension** | Add `AWAITING_APPROVAL` + `AWAITING_APPROVAL_EXPIRED`; transitions; migration | S (0.5 day) |
| 3–4 | **Story 2: Signal handler + wait condition** | `@workflow.signal` for `approve_publish`; `workflow.wait_condition` with 7-day timeout; tier-based branching | M (2 days) |
| 5 | **Story 3: Approval request activity** | `post_approval_request_activity` — post summary comment before entering wait | M (1 day) |
| 6 | **Story 4: Timeout escalation activity** | `escalate_timeout_activity` — apply label, post comment, transition status | M (1 day) |
| 7 | **Story 5: Approval API endpoint** | `POST /api/tasks/{id}/approve` with workflow signal + status validation | M (1 day) |
| 8 | **Story 6: Time-skipping integration tests** | Temporal WorkflowEnvironment tests: timeout, approval, observe-skip, double-signal | M (1 day) |
| 9 | **Story 7: Unit tests** | API endpoint tests + edge cases | S (0.5 day) |
| 9 | **Story 8: Documentation** | Update architecture mapping, workflow docstrings | S (0.5 day) |
| 10 | **Buffer** | Integration testing, regression fixes | — |

### Estimation Summary

| Story | Estimate | Confidence |
|-------|----------|------------|
| Story 0 (Spike) | 2 days | 70% — new Temporal patterns |
| Stories 1–4 (Core) | 4.5 days | 75% |
| Stories 5–8 (API + Tests + Docs) | 2.5 days | 85% |
| Buffer | 1 day | — |
| **Total** | **10 days** | |

### Risk: Temporal SDK Compatibility

The spike may reveal that the current `temporalio` SDK version doesn't support `workflow.wait_condition` with timeout. Mitigation: upgrade SDK if needed (low risk — Temporal Python SDK is mature). Spike must complete before Story 2 begins.

---

## Sprint 21 (2026-05-12 → 2026-05-23) — Execute Tier End-to-End

### Sprint Goal (Testable)

**Objective:** Deliver Epic 22 — Enable autonomous PR workflow for Execute tier repos. By sprint end:
1. Publisher differentiates Execute from Suggest tier: `_should_mark_ready()` handles `RepoTier.EXECUTE`.
2. `GitHubClient.enable_auto_merge()` calls GitHub GraphQL `enablePullRequestAutoMerge` mutation.
3. `EXECUTE_TIER_POLICY` compliance check gates promotion to Execute tier.
4. Auto-merge only fires after human approval signal (Epic 21 integration).
5. Admin UI shows merge mode toggle, auto-merge badge, and Execute policy in compliance scorecard.
6. `RepoProfileRow` includes `merge_method` column (squash/merge/rebase).
7. All existing tests pass.

### Ordered Backlog

| Days | Slice | Stories | Work |
|------|-------|---------|------|
| 1–2 | **Slice 1: Publisher behavior** | 22.1–22.4 | Execute tier branching, tier label, `auto_merge_enabled` field, unit tests |
| 3–4 | **Slice 2: GitHub auto-merge** | 22.5–22.8 | GraphQL `enable_auto_merge()`, `merge_method` migration, Publisher wiring, integration tests |
| 5–6 | **Slice 3: Compliance gate** | 22.9–22.12 | `EXECUTE_TIER_POLICY` check, promotion eligibility, unit tests |
| 7–8 | **Slice 4: Approval integration** | 22.13–22.15 | Wire auto-merge to require approval signal, feature flag, integration test |
| 9 | **Slice 5: Admin UI** | 22.16–22.18 | Merge mode toggle, badge, scorecard, span attributes |
| 10 | **Buffer** | — | Regression testing, polish |

### Estimation Summary

| Slice | Stories | Days | Confidence |
|-------|---------|------|------------|
| Slice 1 (Publisher) | 4 | 2 | 85% |
| Slice 2 (GraphQL) | 4 | 2 | 75% — new GraphQL integration |
| Slice 3 (Compliance) | 4 | 2 | 85% |
| Slice 4 (Approval) | 3 | 2 | 80% — gate: Epic 21 Stories 1–6 merged to master with CI green; `approve_publish` signal handler and 7-day timeout verified by `tests/workflow/test_approval_wait.py` passing |
| Slice 5 (Admin UI) | 3 | 1 | 85% |
| Buffer | — | 1 | — |
| **Total** | **18 stories** | **10 days** | |

### Hard Prerequisite

**Slice 4 (Stories 22.13–22.15) MUST NOT begin until Epic 21 Stories 1–6 are merged.** Slices 1–3 can proceed in parallel with Epic 21 if Sprint 20 runs long.

---

## Deferred: Sprints 22+ — Epic 17 (Poll Intake) + Epic 18 (Test Suite Expansion)

### Epic 17 — Poll for Issues as Backup to Webhooks

**Priority:** Low. Webhooks work. Polling is a resilience backup.
**Estimated effort:** 1 sprint (10 days)
**Key work:** GitHub API poll client, synthetic delivery IDs, scheduler, Admin UI config, rate-limit backoff.
**Prerequisite:** Epic 16 (complete) — poll client reuses intake pipeline.
**Status:** Meridian review pending. Review before scheduling.

### Epic 18 — Production E2E Test Suite Expansion

**Priority:** Low. Refactors monolithic test rig; not blocking new features.
**Estimated effort:** 1 sprint (10 days)
**Key work:** Split test rig into 5 modules, webhook signature validation, contract alignment mapping.
**Prerequisite:** Epic 17 (poll intake exists for testing).
**Status:** Meridian review pending. Review before scheduling.

---

## Dependency Graph

```
Sprint 17:  Epic 16 ──────────────────────────────────────────┐
Sprint 18:  Epic 15 ─┬─ Epic 19 B (security) ────────────────┤
                      └─ Epic 19 C (reputation DB) ──────────┤
Sprint 19:  Epic 19 A (gateway) ─┬─ Epic 20 (safety nets) ──┤
                                  │                           │
Sprint 20:  ──────────── Epic 21 (human approval) ───────────┤
                                                              │
Sprint 21:  ──────────── Epic 22 (Execute tier) ◄─────────────┘
                                                   (blocks on Epic 21)

Deferred:   Epic 17 (poll intake) → Epic 18 (test expansion)
```

---

## Architecture Gaps Closed Per Sprint

| Sprint | Gaps Closed | Mapping Reference |
|--------|------------|-------------------|
| 17 | — (new feature, not a gap) | — |
| 18 | C4 (security scan), C7 (reputation persistence) | Lines 429, 432 |
| 19 | C1 (gateway wiring), C3 (JetStream), C5 (escalation), C8 (adversarial) | Lines 426, 428, 430, 433 |
| 20 | C6 (human approval wait states) | Line 431 |
| 21 | C2 (Execute tier end-to-end) | Line 427 |

**After Sprint 21: All 8 critical gaps (C1–C8) are closed.**

---

## Retro Actions

**Prior sprints:** Lessons from Epic 15 Meridian reviews applied across all plans:
1. Every story names existing files it extends — no duplication of existing tests.
2. All pytest markers match existing convention (no `@pytest.mark.integration` unless external services required).
3. File paths cross-checked between story details and acceptance criteria.
4. Sprint goals are testable with specific `pytest` commands and `ruff`/`mypy` verification.

---

## Risk Register

| Risk | Sprint | Likelihood | Impact | Mitigation |
|------|--------|-----------|--------|------------|
| Sprint 18 overrun from 3 concurrent streams | 18 | Medium | Drops onboarding guide (15.7) to Sprint 19 | 15.7 is documentation only, safe to defer |
| Temporal spike reveals SDK limitations | 20 | Low | Delays Sprint 20 by 1-2 days | Upgrade SDK; time-skipping is well-documented in Temporal docs |
| GitHub GraphQL auto-merge mutation requires new App permissions | 21 | Medium | Blocks Slice 2 | Verify permissions before sprint start (operational prerequisite) |
| Epic 21 not stable when Sprint 21 begins | 21 | Low | Slice 4 blocked | Slices 1-3 independent; Slice 4 can shift to Sprint 22 |
| Merge conflicts between Epic 19A and Epic 20 (shared agent/routing code) | 19 | Medium | Rework wasted | Batch them in same sprint; order gateway first |

---

## Definition of Done — Full Roadmap

- [ ] All 8 critical gaps (C1–C8) closed in `docs/architecture-vs-implementation-mapping.md`
- [ ] Execute tier repos can auto-merge PRs after all gates pass + human approval
- [ ] All existing tests pass (zero regressions across all sprints)
- [ ] `ruff check .` and `mypy src/` clean on all new code
- [ ] Each sprint's testable goal verified before moving to next sprint

---

## Meridian Review Status

### Round 1: Conditional PASS — 4 gaps fixed

**Date:** 2026-03-12
**Verdict:** Conditional PASS — all 4 must-fix items addressed

| # | Gap | Resolution |
|---|-----|------------|
| 1 | Sprint 17 → Sprint 18 dependency not stated | Added explicit relationship section: Sprint 18 is independent; no blocking dependency; Sprint 19 Story 20.10 rebase note added |
| 2 | Sprint 19 missing per-story confidence reasoning | Added per-story confidence with risk explanations for 20.3 (JetStream, 65%) and 20.4 (Router escalation, 70%) |
| 3 | "Epic 21 being stable" undefined for Sprint 21 Slice 4 | Replaced with concrete gate: "Epic 21 Stories 1–6 merged to master with CI green; `approve_publish` signal handler verified by passing tests" |
| 4 | Single-developer "parallel" execution unclear in Sprint 18 | Added clarification: "parallel" means interleaved, not concurrent; developer works one story at a time, switching between streams at natural stopping points |

**Non-blocking observations noted:**
- Epic 20 → Epic 21 escalation handler reuse question: answer in Sprint 20 detailed plan
- GitHub App permission verification: assign owner and deadline when Sprint 21 plan is detailed
- Epic 15 Story 15.3 internal file reference inconsistency: clean up in epic, roadmap uses correct reference

**Cross-reference checks:** All story counts match (17/18/9/18), file references consistent, Epic 21→22 hard dependency correctly reproduced, all 8 gaps (C1–C8) traceable to epic acceptance criteria. PASS.
