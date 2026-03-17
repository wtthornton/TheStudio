# TAPPS Handoff

> Project-wide quality and delivery status as of 2026-03-17.

## Project Status

**Phases 0–5 complete.** Phase 6 (Pipeline Intelligence + Portfolio Visibility) ready to begin.
26 epics delivered. Epic 27 (Multi-Source Webhooks) deferred — no current demand.
Epics 28 and 29 Meridian-reviewed and ready to commit.

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
| 15 | E2E Integration & Real Repo Onboarding | 5 | Complete (all 7 stories, 2026-03-17) |
| 16 | Issue Readiness Gate | 5 | Complete (Sprint 17: 16.1-16.4, Sprint 18: 16.5-16.8) |
| 17 | Poll for Issues (Backup) | 5 | Complete (all 8 stories, 2 sprints) |
| 18 | Production E2E Test Suite | 5 | Complete (5 slices, full contract coverage) |
| 19 | Critical Gaps Batch 1 | 5 | Complete (Sprint 19) |
| 20 | Critical Gaps Batch 2 | 5 | Complete (Sprint 19) |
| 21 | Human Approval Wait States | 5 | Complete (9 stories, 2026-03-13) |
| 22 | Execute Tier End-to-End | 5 | Complete (18 stories, auto-merge gating) |
| 23 | Unified Agent Framework | 5 | Complete (3 sprints, 8/8 agents, 215+ tests, 2026-03-16) |
| 24 | Chat Approval Workflows | 5 | Complete (6 stories, 2 sprints, 56+ tests, 2026-03-17) |
| 25 | Container Isolation | 5 | Complete (7 stories, 3 sprints, 35+ tests, 2026-03-17) |
| 26 | File-Based Expert Packaging | 5 | Complete (6 stories, 2026-03-16) |
| 27 | Multi-Source Webhooks | 5 | **Deferred** — no current demand |
| 28 | Preflight Plan Review Gate | 6 | **Meridian Reviewed — Ready to Commit** |
| 29 | GitHub Projects v2 + Meridian Portfolio Review | 6 | **Meridian Reviewed — Ready to Commit** |

---

## Codebase Metrics (2026-03-17)

| Metric | Value |
|--------|-------|
| Source files (src/) | 150+ |
| Test files (tests/) | 110+ |
| Tests passing | 2,060+ |
| Tests deselected | 14 (integration — require PostgreSQL/Temporal) |
| Coverage | 84% |
| Modules | 22+ (adapters, admin, agent, approval, assembler, compliance, context, db, evals, experts, ingress, intake, intent, models, observability, outcome, publisher, qa, recruiting, repo, reputation, routing, verification, workflow) |

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

- **TAPPS** active with ruff, mypy, bandit, radon, vulture, pip-audit
- **Quality preset:** standard
- **All TAPPS gates:** PASSED on last validation run

---

## Phase 5 Completion Summary (2026-03-17)

**Delivered in final sprint (2026-03-17):**
- **Story 25.7** — Container observability: OTel child spans for container lifecycle, per-line log capture with correlation_id, structured metrics (6 new tests)
- **Story 15.7** — Onboarding guide: 7-section `docs/ONBOARDING.md` (prerequisites, GitHub App, API registration, Admin UI, webhook verification, trust tiers, troubleshooting)
- **Story 24.4** — Notification channel adapter: Abstract base class + GitHub implementation + channel registry (12 new tests)
- **Story 24.5** — Slack notification channel: Block Kit messages with approve/reject buttons, incoming webhook (11 new tests)
- **Story 24.6** — Approval observability: OTel spans on all chat/approval endpoints, ApprovalMetadata in evidence comments, NATS approval signals (12 new tests)

**New files:** `src/approval/channels/` (base, github, slack, registry), test files for channels/slack/observability
**Modified:** `src/agent/container_manager.py`, `src/api/approval.py`, `src/approval/chat_router.py`, `src/observability/conventions.py`, `src/publisher/evidence_comment.py`, `src/settings.py`, `src/workflow/activities.py`

**Phase 5 exit criteria:** 4 of 5 met. Epic 27 deferred by design (no demand).

---

## Next Actions

1. **Begin Phase 6** — Epic 28 (Preflight Plan Review Gate) and Epic 29 (GitHub Projects v2 + Meridian Portfolio Review) are Meridian-reviewed and ready
2. **Epic 28** — 4 stories, 1 sprint. New Preflight persona. Can start immediately.
3. **Epic 29** — 9 stories, 2 sprints. Can parallel with Epic 28.
4. **Set up CI pipeline** (GitHub Actions) for automated test/lint/security on every PR
5. **Improve coverage** on CRUD and signal modules (target: 90%+)
6. **Run integration tests** against real PostgreSQL/Temporal
7. **Enable LLM feature flags** per agent incrementally (Intake first, then Context, etc.)
