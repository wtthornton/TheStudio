# TAPPS Handoff

> Project-wide quality and delivery status as of 2026-03-16.

## Project Status

**Phases 0–4 complete.** Phase 5 (Agent Intelligence + Platform Growth) in progress.
Epic 23 (Unified Agent Framework) **complete** — all 3 sprints delivered, 8/8 agents on AgentRunner. Three epics awaiting Meridian review.

---

## Delivery Summary

| Epic | Title | Phase | Status |
|------|-------|-------|--------|
| 0 | Foundation | 0 | Complete |
| 1 | Full Flow + Experts | 1 | Complete |
| 2 | Learning + Multi-repo | 2 | Complete |
| 3 | Execute Tier Compliance | 2 | Complete |
| 4 | Admin UI Core | 2 | Complete (9/9 stories) |
| 5 | Observability & Quality | 3 | Complete |
| 6 | Phase 3 Completion | 3 | Complete |
| 7 | Platform Maturity | 4 | Complete (2 sprints) |
| 8 | Production Readiness | 4 | Complete (2 sprints) |
| 9 | Docker Test Rig | 4 | Complete |
| 10 | Docker Test Hardening | 4 | Complete |
| 11 | Production Hardening Phase 1 | 4 | Complete |
| 12 | Playwright Admin UI Tests | 4 | Complete |
| 13 | Agent Persona Infrastructure | 4 | Complete |
| 14 | Agent Content Enrichment | 4 | Complete |
| 15 | E2E Integration & Real Repo Onboarding | 5 | **Draft** — revised after Meridian Round 1, not yet executed |
| 16 | Issue Readiness Gate | 5 | Complete (Sprint 17: 16.1-16.4, Sprint 18: 16.5-16.8) |
| 17 | Poll for Issues (Backup) | 5 | Complete (all 8 stories, 2 sprints) |
| 18 | Production E2E Test Suite | 5 | Complete (5 slices, full contract coverage) |
| 19 | Critical Gaps Batch 1 | 5 | Complete (Sprint 19) |
| 20 | Critical Gaps Batch 2 | 5 | Complete (Sprint 19) |
| 21 | Human Approval Wait States | 5 | Complete (9 stories, 2026-03-13) |
| 22 | Execute Tier End-to-End | 5 | Complete (18 stories, auto-merge gating) |
| 23 | Unified Agent Framework | 5 | Complete (3 sprints, 8/8 agents, 215+ tests, 2026-03-16) |
| 24 | Chat Approval Workflows | 5 | **Draft** — awaiting Meridian review |
| 25 | Container Isolation | 5 | **Draft** — awaiting Meridian review |
| 26 | File-Based Expert Packaging | 5 | Complete (6 stories, 2026-03-16) |
| 27 | Multi-Source Webhooks | 5 | **Draft** — awaiting Meridian review |

---

## Codebase Metrics (2026-03-16)

| Metric | Value |
|--------|-------|
| Source files (src/) | 150+ |
| Test files (tests/) | 110+ |
| Tests passing | 1,970+ |
| Tests deselected | 14 (integration — require PostgreSQL/Temporal) |
| Test warnings | 7 (unawaited coroutine mocks) |
| Coverage | 84% |
| Modules | 22 (adapters, admin, agent, assembler, compliance, context, db, evals, experts, ingress, intake, intent, models, observability, outcome, publisher, qa, recruiting, repo, reputation, routing, verification, workflow) |

---

## Coverage Gaps (< 50%)

| File | Coverage | Reason |
|------|----------|--------|
| src/models/taskpacket_crud.py | 18% | DB CRUD — needs integration tests |
| src/repo/repo_profile_crud.py | 24% | DB CRUD — needs integration tests |
| src/intent/intent_crud.py | 30% | DB CRUD — needs integration tests |
| src/verification/gate.py | 39% | Subprocess runners not mocked |
| src/verification/signals.py | 41% | JetStream publish paths |
| src/publisher/github_client.py | 43% | External API calls |
| src/observability/tracing.py | 47% | OpenTelemetry setup |
| src/qa/signals.py | 48% | JetStream publish paths |

---

## Quality Pipeline

- **TAPPS v1.8.0** active with ruff, mypy, bandit, radon, vulture, pip-audit
- **Quality preset:** standard
- **All TAPPS gates:** PASSED on last validation run

---

## Active Work

### Epic 23 — Unified Agent Framework (Complete, 2026-03-16)
- **Sprint 1:** AgentRunner base class, AgentConfig/AgentContext/AgentResult, LLM completion + agentic modes, output parsing, budget enforcement, audit logging, observability spans, feature flags per agent, Primary Agent refactored (Stories 1.1-1.10)
- **Sprint 2:** Intake, Context, Intent, Router agent configs and activity conversions with tests (Stories 2.1-2.12)
- **Sprint 3:** Recruiter, Assembler, QA agent configs and activity conversions, full pipeline integration test (39 tests), epic documentation (Stories 3.1-3.11)
- **Hardening:** Prompt injection guard (41 tests), pipeline budget (18 tests), context compression (10 tests) (Stories 1.11-1.13)
- **Test count:** 215+ new tests across all Epic 23 modules
- **Architecture gaps closed:** V7 (invariants), V8 (shadow consulting), V9 (staged consults), D3 (LLM intent extraction)

### Epics Awaiting Meridian Review
- **Epic 24** — Chat Approval Workflows (conditional pass, 5 blocking gaps)
- **Epic 25** — Container Isolation (conditional pass, 4 blocking gaps)
- **Epic 27** — Multi-Source Webhooks (conditional pass, 4 blocking gaps)

### Epic 15 — Not Yet Executed
- Revised after Meridian Round 1, but never scheduled for a sprint
- Integration test harness + real repo onboarding guide
- Should be prioritized as a validation milestone

---

## Next Actions

1. **Fix cross-epic blockers** (rejection status, baselines, owners, per-tier policy) then re-review Epics 24, 25, 27
2. **Schedule Epic 15** — real repo Observe-tier trial to validate full pipeline
3. **Begin Epic 24 (Chat Approval) or Epic 25 (Container Isolation)** after blocker resolution
4. **Set up CI pipeline** (GitHub Actions) for automated test/lint/security on every PR
5. **Improve coverage** on CRUD and signal modules (target: 90%+)
6. **Fix 7 test warnings** (unawaited AsyncMock coroutines)
7. **Run integration tests** against real PostgreSQL/Temporal
8. **Enable LLM feature flags** per agent incrementally (Intake first, then Context, etc.)
