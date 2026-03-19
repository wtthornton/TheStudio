# Epic Status Tracker

> Consolidated status of all epics as of 2026-03-18 (evening update).
> Source of truth for epic status is each epic's own file. This tracker is a rollup view.

---

## Summary

| Metric | Value |
|--------|-------|
| Total epics | 33 (0-33) |
| Complete | 31 (including Epic 30 all 3 sprints, Epic 33) |
| In Progress | 1 (Epic 32 — Slice 1 partial, Slice 2 next) |
| Top Priority | Epic 32 Slice 2 (Budget Controls) |
| Deferred | 1 (Epic 27) |
| Tests passing | 1,783 unit (zero failures), 36 integration |
| Eval tests | 20/25 passed with real Claude (~$5/run) |
| Coverage | 84% |

---

## Phase 0 — Foundation

| Epic | Title | Status | Delivered |
|------|-------|--------|-----------|
| 0 | Foundation | Complete | Domain models, async infrastructure, TaskPacket |

## Phase 1 — Full Flow + Experts

| Epic | Title | Status | Delivered |
|------|-------|--------|-----------|
| 1 | Full Flow + Experts | Complete | 9-step pipeline, expert selection, evidence comments |

## Phase 2 — Learning + Multi-Repo

| Epic | Title | Status | Delivered |
|------|-------|--------|-----------|
| 2 | Learning + Multi-Repo | Complete | Multi-repo infrastructure, repo profiles, deduplication |
| 3 | Execute Tier Compliance | Complete | Compliance policy framework, trust tier definitions |
| 4 | Admin UI Core | Complete (9/9 stories) | Fleet dashboard, repo management, workflow monitoring, RBAC, audit |

## Phase 3 — Scale + Quality Bar

| Epic | Title | Status | Delivered |
|------|-------|--------|-----------|
| 5 | Observability & Quality | Complete | Structured logging, OpenTelemetry, correlation IDs |
| 6 | Phase 3 Completion | Complete | Context Manager, Intent Builder, Verification gate, QA scoring |

## Phase 4 — Platform Maturity

| Epic | Title | Status | Delivered |
|------|-------|--------|-----------|
| 7 | Platform Maturity | Complete (2 sprints) | Multi-repo support, lifecycle management, reputation engine |
| 8 | Production Readiness | Complete (2 sprints) | Temporal workflow, activities framework, evidence bundling |
| 9 | Docker Test Rig | Complete | E2E Docker Compose, webhook-to-TaskPacket validation |
| 10 | Docker Test Hardening | Complete | Focused test modules, endpoint validation, smoke tests |
| 11 | Production Hardening Phase 1 | Complete | Compliance checker, repo tier enforcement, endpoint validation |
| 12 | Playwright Admin UI Tests | Complete | 100+ browser tests, XSS fixes, HTMX interaction coverage |
| 13 | Agent Persona Infrastructure | Complete | YAML frontmatter, linter, converter, drift detection |
| 14 | Agent Content Enrichment | Complete | 4 walkthroughs, maturity tracking, catalog generator |

## Phase 5 — Agent Intelligence + Platform Growth (Complete)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 15 | E2E Integration & Real Repo Onboarding | **Complete** | All 7 stories delivered. Mock harness, smoke tests, loopbacks, onboarding guide. |
| 16 | Issue Readiness Gate | Complete | Sprint 17 (16.1-16.4) + Sprint 18 (16.5-16.8) |
| 17 | Poll for Issues (Backup) | Complete | All 8 stories, 2 sprints (2026-03-13) |
| 18 | Production E2E Test Suite | Complete | 5 slices, full contract coverage (2026-03-16) |
| 19 | Critical Gaps Batch 1 | Complete | Gateway wiring, security scans, reputation persistence (Sprint 19) |
| 20 | Critical Gaps Batch 2 | Complete | JetStream consumption, escalation, adversarial detection (Sprint 19) |
| 21 | Human Approval Wait States | Complete | 9 stories, Temporal durable wait, 7-day timeout (2026-03-13) |
| 22 | Execute Tier End-to-End | Complete | 18 stories, auto-merge gating, compliance enforcement |
| 23 | Unified Agent Framework | **Complete** | All 3 sprints delivered. 8/8 agents on AgentRunner. 215+ new tests. |
| 24 | Chat Approval Workflows | **Complete** | All 6 stories, 2 sprints. ReviewContext, chat persistence, API, notification channels (GitHub + Slack), OTel observability, NATS signals, approval metadata in evidence. 56+ new tests. |
| 25 | Container Isolation | **Complete** | All 3 sprints, 7 stories. Container image, lifecycle manager, protocol, activity integration, network isolation, per-tier resource limits, OTel observability. 35+ new tests. |
| 26 | File-Based Expert Packaging | Complete | 6 stories, manifest schema, scanner, registrar (2026-03-16) |
| 27 | Multi-Source Webhooks | **Deferred** | Growth enabler, no current demand. Defer until pulled. 4 Meridian gaps remain — resolve when demand materializes. |

## Phase 6 — Pipeline Intelligence + Portfolio Visibility (Complete)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 28 | Preflight Plan Review Gate | **Complete** | All 4 stories delivered. Preflight agent config, activity, pipeline integration, observability, evidence comment, 46 tests passing. |
| 29 | GitHub Projects v2 + Meridian Portfolio Review | **Complete** | Both sprints delivered. Sprint 1: GraphQL client, status mapping, pipeline sync, compliance checker (63 tests). Sprint 2: Portfolio collector, Meridian review agent, Temporal workflow, Admin UI dashboard, GitHub issue report (60 tests). 123 total tests. |

---

## Cross-Epic Blocking Items (from Meridian Reviews 2026-03-16)

| # | Epic | Blocker | Status |
|---|------|---------|--------|
| 1 | All (24, 25, 27) | All stakeholder roles are "TBD" — need named owners | **Resolved 2026-03-16** — Solo-developer project; primary developer assigned to all roles |
| 2 | 24 | No rejection status in TaskPacket `ALLOWED_TRANSITIONS` | **Resolved 2026-03-16** — REJECTED status added, reject_publish signal wired, POST /reject endpoint live, 11 new tests |
| 3 | 24 | Success metrics lack baselines — measure current approval time and timeout rate first | **Resolved 2026-03-17** — Approval baseline instrumentation added in `operational_targets.py` |
| 4 | 25 | Silent fallback to in-process on Execute tier is a security hole | **Resolved 2026-03-16** — Per-tier fallback policy in settings + isolation_policy.py. Execute tier = deny |
| 5 | 25 | DB-free execution path for container runner — `implement()` requires `AsyncSession` | **Resolved 2026-03-17** — Container runner uses AgentTaskInput (serialized, no DB). Activity wires container mode via isolation_policy. |
| 6 | 27 | `source_name` storage ambiguity — scope JSON vs new column | **Resolved 2026-03-16** — New source_name VARCHAR(100) column + index. Migration 022. Default='github' |
| 7 | 27 | `jsonpath-ng` evaluation unassigned | **Closed** — Epic 27 deferred, no current demand |

## Phase 7 — Real Provider Validation + Cost Model (In Progress)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 30 | Real Provider Integration & Validation | **Complete (3 Sprints)** | Sprint 1: eval harness, 6 agent eval suites, Postgres 6/6, GitHub 4/4. Sprint 2: Docker pipeline validation, failure catalog. Sprint 3: Stories 30.12 (Suggest tier, 16 tests), 30.13 (gateway audit, 9/9), 30.14 (approval bypass, 20 tests). All pre-existing test failures resolved. 1783/1783 unit tests passing. |
| 31 | Anthropic Max OAuth Adapter | **TOP MUST** | Research complete (Story 31.0). Eval tests cost ~$5/run — OAuth/Max integration is critical for sustainable testing and operations. Elevated to top priority 2026-03-18. |
| 32 | Model Routing & Cost Optimization | **Slice 1 Complete** | Cost routing gate in ModelRouter (feature-flagged off). Downgrades expert_routing + assembler to FAST when enabled. Security overlay preserved. Meridian Round 2 approved. Slice 2 planned 2026-03-25. |

---

## Critical Path

```
Phase 6 — COMPLETE (2026-03-18)
  All epics closed. Both Phase 6 epics delivered.

  Epic 28 (Preflight Plan Review Gate) — COMPLETE
    All 4 stories. Lightweight plan quality gate. 46 tests.

  Epic 29 (Projects v2 + Meridian Portfolio Review) — COMPLETE
    All 10 stories, 2 sprints. GraphQL client, pipeline sync,
    compliance checker, portfolio collector, Meridian review agent,
    Temporal workflow, Admin UI dashboard, GitHub issue report.
    123 tests across tests/github/ and tests/meridian/.

Phase 5 — COMPLETE (2026-03-17)
  All epics closed except Epic 27 (deferred, no demand).
```

---

## Phase 5 Exit Criteria Status

| Criterion | Status |
|-----------|--------|
| All 8 pipeline agents share a common AgentRunner framework | **Met** — Epic 23 complete |
| Primary Agent code execution runs in ephemeral containers | **Met** — Epic 25 complete |
| At least one non-GitHub source can trigger the pipeline | **Deferred** — Epic 27 deferred |
| Human reviewers can ask questions via chat before approving | **Met** — Epic 24 complete |
| At least one real repo processes issues end-to-end at Observe tier | **Met** — Epic 15 onboarding guide complete |

**Verdict:** Phase 5 is effectively complete. Epic 27 (multi-source webhooks) is deferred by design — no current demand. All other exit criteria are met.

---

## Recommended Next Actions

1. ~~**Epic 28**~~ — **Complete** (2026-03-17). All 4 stories, 46 tests.
2. ~~**Epic 29 Sprint 1**~~ — **Complete** (2026-03-17). 63 tests.
3. ~~**Epic 29 Sprint 2**~~ — **Complete** (2026-03-18). 60 tests.
4. ~~**Phase 7 planning**~~ — **Complete** (2026-03-18). Epic 30 planned, Meridian reviewed, Sprint 1 approved.
5. ~~**Cost estimation fix (Story 31.1)**~~ — **Complete** (2026-03-18). Split input/output rates in ProviderConfig. 2026 pricing applied.
6. ~~**Epic 30 Sprint 1 Stories 30.1-30.6**~~ — **Complete** (2026-03-18). Eval harness, 6 agent eval suites, Postgres + GitHub integration tests. All passing.
7. ~~**Run Epic 30 integration tests**~~ — **Complete** (2026-03-18). Postgres 6/6, GitHub 4/4, eval 20/25 (5 failures = routing agents needed LLM enable, fixed). ~$5/run, ~47 min.
8. ~~**Epic 32 Slice 1**~~ — **Complete** (2026-03-18). Cost routing gate, comparison eval mode, settings registered, Meridian approved.
9. ~~**Epic 30 Sprint 2**~~ — **Complete** (2026-03-18). Docker pipeline validation, failure catalog.
10. ~~**Epic 30 Sprint 3**~~ — **Complete** (2026-03-19). Stories 30.12-30.14. All pre-existing test failures resolved. 1783/1783 passing.
11. **Epic 32 Slice 2** — Budget controls (Stories 32.6-32.8). Next session priority.
12. **Epic 32 Slice 1 remaining** — Stories 32.3 (comparison eval), 32.4 (routing rules). Complete alongside Slice 2.
13. **Fix F8/F5** — Assembler schema mismatch + max_tokens increase. Quick wins.
14. **Epic 27** — Deferred. Do not schedule until demand materializes.
