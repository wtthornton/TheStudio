# Epic Status Tracker

> Consolidated status of all epics as of 2026-03-21.
> Source of truth for epic status is each epic's own file. This tracker is a rollup view.

---

## Summary

| Metric | Value |
|--------|-------|
| Total epics | 39 (0-39) |
| Complete | 36 (Epics 0-26, 28-36) |
| In Progress | 0 |
| Planned | 3 (Epics 37-39 — Pipeline UI Phases 3-5) |
| Milestone | **Pipeline UI Phase 2 complete** (2026-03-21) — Phases 0-2 delivered, Planning Experience live |
| Deferred | 1 (Epic 27) |
| Tests passing | 3,366+ unit (zero failures), 9 E2E pipeline, ~244 integration, 23 P0 harness |
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

## Phase 7 — Real Provider Validation + Cost Model (Complete)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 30 | Real Provider Integration & Validation | **Complete (3 Sprints)** | Sprint 1: eval harness, 6 agent eval suites, Postgres 6/6, GitHub 4/4. Sprint 2: Docker pipeline validation, failure catalog. Sprint 3: Stories 30.12 (Suggest tier, 16 tests), 30.13 (gateway audit, 9/9), 30.14 (approval bypass, 20 tests). All pre-existing test failures resolved. 1783/1783 unit tests passing. |
| 31 | Anthropic Max OAuth Adapter | **Complete (2026-03-19)** | All stories 31.0-31.6 delivered. Research, cost estimation fix, auth mode detection, token refresh, 31 unit tests, Docker validation, deployment docs. Meridian review: PASS (2026-03-20). |
| 32 | Model Routing & Cost Optimization | **Slices 1-5 Complete** | All 18 stories (32.0-32.17) delivered across 5 slices. Cost baselines, feature flags, eval suites, comparison mode, routing rules, cost routing gate, budget controls, admin UI, prompt caching, cache tracking, per-repo/per-day aggregation, cost dashboard, budget utilization widget, Batch API, batch eligibility, batch cost discount. F9 fixed. |

## Phase 8 — Production Deployment & Operational Readiness (Complete, 2026-03-20)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 33 | P0 Deployment Test Harness | **Complete** | All 8 ACs delivered across 2 sprints. Health gate (8 tests), eval preflight guard (8 tests), deployment-mode GitHub/Postgres tests (14 P0 deployed), runner script with cost tracking and results persistence, false-pass validation (7 tests), credential guard. 23 new tests in Sprint 2. |

### Pipeline Wiring (2026-03-20)

| Fix | Status | Impact |
|-----|--------|--------|
| Wire `implement_activity` with real LLM + GitHub push | **Complete** | Critical: LLM generates code, pushed to branch via GitHub Contents API. |
| Wire `verify_activity` with file-existence check | **Complete** | Validates files were pushed to branch. |
| Wire `publish_activity` to real publisher | **Complete** | PR creation works when `github_provider=real`. Branch handling, evidence comment, labels. |
| Add migration auto-run to app lifespan | **Complete** | DB schema created on first deploy when `store_backend=postgres`. |
| Persist intent spec to DB in intent_activity | **Complete** | Publisher can now load intent for evidence comment. |
| Add missing methods to ResilientGitHubClient | **Complete** | `find_pr_by_head`, `create_or_update_file`, `mark_ready_for_review`, `enable_auto_merge`. |
| Fix TaskPacket status transition for publish | **Complete** | Advance through required status chain before publishing. |

### First Real Issue Milestone (2026-03-20)

| Metric | Value |
|--------|-------|
| Issue | [#19 — Add reverse_string to text.py](https://github.com/wtthornton/thestudio-production-test-rig/issues/19) |
| PR | [#20 — Draft PR](https://github.com/wtthornton/thestudio-production-test-rig/pull/20) |
| Pipeline duration | ~2 minutes |
| Loopbacks | 0 verification, 0 QA |
| Cost | ~$0.30 |
| Files generated | `text.py` (function + docstring), `test_text.py` (4 tests) |
| Labels | `agent:done`, `tier:observe` |
| Evidence comment | Full evidence with intent, acceptance criteria, verification |

---

## Phase 9 — Pipeline UI (In Progress)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 34 | Phase 0: SSE PoC + Frontend Scaffolding | **Complete** (2026-03-21) | 14 stories. Dashboard API router, SSE bridge (NATS→EventSource), Vite+React+Zustand+Tailwind, pipeline rail, auth, CI. |
| 35 | Phase 1: Pipeline Visibility | **Complete** (2026-03-21) | 63 stories across 4 slices. Pipeline Rail, TaskPacket Timeline, Gate Inspector, Activity Stream, Loopback arcs, Minimap, error states. |
| 36 | Phase 2: Planning Experience | **Complete** (2026-03-21) | All 4 slices delivered. Slice 1: Triage Queue (6 stories). Slice 2: Intent Review (8 stories). Slice 3: Complexity + Routing (10 stories). Slice 4: Backlog + Tasks (5 stories). 29 stories total. |
| 37 | Phase 3: Interactive Controls | Planned | Trust tier controls, bulk actions, keyboard shortcuts. Epic defined, not started. |
| 38 | Phase 4: GitHub Integration | Planned | Bidirectional sync with GitHub Projects, issue templates. Epic defined, not started. |
| 39 | Phase 5: Analytics & Learning | Planned | Cost analytics, performance trends, model comparison. Epic defined, not started. |

---

## Critical Path

```
Phase 9 — IN PROGRESS (2026-03-21)
  Epic 34 (Phase 0: SSE PoC) — COMPLETE. 14 stories. Dashboard infra.
  Epic 35 (Phase 1: Pipeline Visibility) — COMPLETE. 63 stories. Full dashboard.
  Epic 36 (Phase 2: Planning Experience) — COMPLETE. 29 stories across 4 slices.
    Slice 1 (Triage Queue): COMPLETE (6 stories)
    Slice 2 (Intent Review): COMPLETE (8 stories)
    Slice 3 (Complexity+Routing): COMPLETE (10 stories)
    Slice 4 (Backlog+Tasks): COMPLETE (5 stories)

Phase 8 — COMPLETE (2026-03-20)
  Epic 33 complete (2 sprints, all 8 ACs). P0 deployment test harness delivered.
  All 9 pipeline activities wired to real providers.
  First real GitHub issue → Draft PR: Issue #19 → PR #20 (2 min, 0 loopbacks).
  Implement: LLM generates code + pushes to GitHub via Contents API.
  Verify: File-existence validation on branch.
  Publish: Draft PR with evidence comment, lifecycle labels.

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

## Phase 7 Exit Criteria Status

| Criterion | Status |
|-----------|--------|
| Intent agent valid specs >= 8/10 with real Claude | **Met** — Epic 30 eval suite |
| QA agent catches planted defects >= 7/10 | **Met** — F9 scoring calibrated |
| Primary agent valid output 3/3 simple issues | **Met** — Epic 30 Docker tests |
| Postgres integration 6/6 | **Met** — Epic 30 Sprint 1 |
| GitHub integration 4/4 | **Met** — Epic 30 Sprint 1 |
| Full pipeline processes real GitHub issue into draft PR | **Met** — E2E validation test: 9/9 passing (test_e2e_pipeline_validation.py). Real activities through Temporal workflow, assembler serialization bug fixed. |
| Cost model documented with accurate estimates | **Met** — Epic 32 Slice 1 baselines |
| Deployment runbook enables cold start | **Met** — docs/deployment.md |
| Cost optimization reduces per-issue spend by >= 50% | **Met** — Routing + caching + Batch API (Epic 32 all 5 slices) |

**Verdict:** Phase 7 is **complete**. All exit criteria met. 1,832+ unit tests, 9 E2E pipeline tests, ~244 integration tests. Zero failures.

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
11. ~~**Epic 32 Slice 2**~~ — **Complete** (2026-03-19). Stories 32.6-32.8. Budget controls, admin UI, graceful budget-exceeded.
12. ~~**Epic 32 Slice 1 remaining**~~ — **Complete** (2026-03-19). Stories 32.2-32.5 delivered.
13. ~~**Epic 32 Slice 3**~~ — **Complete** (2026-03-19). Stories 32.9-32.11 delivered. Prompt caching, cache tracking, cache hit rate.
14. ~~**Fix F5**~~ — **Fixed** (2026-03-19). max_tokens already at 4096.
15. ~~**Epic 32 Slice 4**~~ — **Complete** (2026-03-19). Cost Dashboard (Stories 32.12-32.14). 31 new tests.
16. ~~**Epic 32 Slice 5**~~ — **Complete** (2026-03-19). Batch API (Stories 32.15-32.17). 19 new tests.
17. ~~**Fix F9**~~ — **Fixed** (2026-03-19). Calibrated weights + adjusted thresholds for intake/context eval scoring.
18. ~~**Epic 31**~~ — **Complete** (2026-03-19). All 7 stories (31.0-31.6). Research, auth mode detection, token refresh, 23 unit tests, Docker validation, deployment docs.
19. **Epic 27** — Deferred. Do not schedule until demand materializes.
20. ~~**Phase 7 exit**~~ — **Complete** (2026-03-19). Full E2E pipeline validation: 9/9 tests passing. Fixed assembler qa_handoff serialization bug. Real activities through Temporal workflow.
21. ~~**Meridian review Epic 31**~~ — **PASS** (2026-03-20). All 7 questions passed. Formal sign-off.
22. ~~**Deployment blockers fixed**~~ — **Complete** (2026-03-20). Publisher activity wired to real GitHubClient. Migration auto-run on startup. 10 new tests.
23. ~~**Epic 33 Sprint 1**~~ — **Complete** (2026-03-20). Health gate (8 tests), deployment-mode GitHub/Postgres tests (14 P0), runner script, credential guards.
24. ~~**Epic 33 Sprint 2**~~ — **Complete** (2026-03-20). Eval preflight guard (8 tests), results persistence with cost/git/failures, false-pass validation (7 tests), documentation.
25. ~~**Production deployment**~~ — **Complete** (2026-03-20). First real GitHub issue processed: Issue #19 → Draft PR #20. All 9 pipeline stages pass. 2 minutes, 0 loopbacks.
26. **Process harder issues** — Multi-file changes, bug fixes, refactoring tasks.
27. **Onboard second repo** — Test multi-repo support with real issues.
28. **Wire remote verification** — Run ruff/pytest on target repo via GitHub Actions or container.
29. **Execute tier promotion** — When ready for auto-merge with approval gates.
30. ~~**Epic 34 (Phase 0: SSE PoC)**~~ — **Complete** (2026-03-21). 14 stories. SSE bridge, React scaffolding.
31. ~~**Epic 35 (Phase 1: Pipeline Visibility)**~~ — **Complete** (2026-03-21). 63 stories across 4 slices.
32. ~~**Epic 36 (Phase 2: Planning Experience)**~~ — **Complete** (2026-03-21). 29 stories across 4 slices. All frontend + backend delivered by Ralph (22 loops).
