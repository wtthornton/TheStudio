# TAPPS Handoff

> Project-wide quality and delivery status as of 2026-03-16.

## Project Status

**Phases 0–4 complete.** Phase 5 (Agent Intelligence + Platform Growth) in progress.
Epic 23 (Unified Agent Framework) Sprint 1 delivered. Three epics awaiting Meridian review.

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
| 23 | Unified Agent Framework | 5 | **In Progress** — Sprint 1: 10/10 stories done, hardening 1.11-1.13 remain |
| 24 | Chat Approval Workflows | 5 | **Draft** — awaiting Meridian review |
| 25 | Container Isolation | 5 | **Draft** — awaiting Meridian review |
| 26 | File-Based Expert Packaging | 5 | Complete (6 stories, 2026-03-16) |
| 27 | Multi-Source Webhooks | 5 | **Draft** — awaiting Meridian review |

---

## Codebase Metrics (2026-03-16)

| Metric | Value |
|--------|-------|
| Source files (src/) | 150+ |
| Test files (tests/) | 88 |
| Tests passing | 1,756 |
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

### Epic 23 — Unified Agent Framework (In Progress)
- **Sprint 1 delivered:** AgentRunner base class, AgentConfig/AgentContext/AgentResult dataclasses, LLM completion + agentic modes, output parsing, budget enforcement, audit logging, observability spans, feature flags per agent
- **Primary Agent refactored:** Now uses AgentRunner framework (Story 1.8)
- **Integration tested:** 11 tests proving Primary Agent through AgentRunner (Story 1.10)
- **Test count:** 57 agent tests (31 framework + 15 gateway + 11 integration)
- **Remaining:** Hardening stories 1.11-1.13, then Sprint 2 (convert Intake + Context agents)

### Epics Awaiting Meridian Review
- **Epic 24** — Chat Approval Workflows (6 stories, depends on Epic 21/22 ✓)
- **Epic 25** — Container Isolation for Primary Agent (7 stories, security-critical)
- **Epic 27** — Multi-Source Webhooks (7 stories, independent)

### Epic 15 — Not Yet Executed
- Revised after Meridian Round 1, but never scheduled for a sprint
- Integration test harness + real repo onboarding guide
- Should be prioritized as a validation milestone

---

## Next Actions

1. **Execute Epic 23 hardening stories (1.11-1.13)** — error handling, retry logic, edge cases
2. **Schedule Epic 23 Sprint 2** — convert Intake Agent and Context Manager to AgentRunner
3. **Submit Epics 24, 25, 27 for Meridian review** — unblock future sprint planning
4. **Schedule Epic 15** — real repo Observe-tier trial to validate full pipeline
5. **Set up CI pipeline** (GitHub Actions) for automated test/lint/security on every PR
6. **Improve coverage** on CRUD and signal modules (target: 90%+)
7. **Fix 7 test warnings** (unawaited AsyncMock coroutines)
8. **Run integration tests** against real PostgreSQL/Temporal
