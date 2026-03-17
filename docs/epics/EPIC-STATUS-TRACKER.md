# Epic Status Tracker

> Consolidated status of all epics as of 2026-03-17.
> Source of truth for epic status is each epic's own file. This tracker is a rollup view.

---

## Summary

| Metric | Value |
|--------|-------|
| Total epics | 27 (0-27) |
| Complete | 23 |
| In Progress | 3 (Epics 15, 24, 25) |
| Meridian Reviewed (Conditional Pass) | 1 (Epic 27) |
| Tests passing | 2,028+ |
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

## Phase 5 — Agent Intelligence + Platform Growth (Current)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 15 | E2E Integration & Real Repo Onboarding | **In Progress** | Stories 15.1-15.6 complete (mock harness, smoke tests, loopbacks). |
| 16 | Issue Readiness Gate | Complete | Sprint 17 (16.1-16.4) + Sprint 18 (16.5-16.8) |
| 17 | Poll for Issues (Backup) | Complete | All 8 stories, 2 sprints (2026-03-13) |
| 18 | Production E2E Test Suite | Complete | 5 slices, full contract coverage (2026-03-16) |
| 19 | Critical Gaps Batch 1 | Complete | Gateway wiring, security scans, reputation persistence (Sprint 19) |
| 20 | Critical Gaps Batch 2 | Complete | JetStream consumption, escalation, adversarial detection (Sprint 19) |
| 21 | Human Approval Wait States | Complete | 9 stories, Temporal durable wait, 7-day timeout (2026-03-13) |
| 22 | Execute Tier End-to-End | Complete | 18 stories, auto-merge gating, compliance enforcement |
| 23 | Unified Agent Framework | **Complete** | All 3 sprints delivered. 8/8 agents on AgentRunner. Prompt guard, pipeline budget, context compression. 215+ new tests. |
| 24 | Chat Approval Workflows | **In Progress — Sprint 1 Complete** | Stories 24.1-24.3 done: ReviewContext model, chat persistence, chat API endpoints. 21 new tests. |
| 25 | Container Isolation | **In Progress — Sprint 1+2 Complete** | Stories 25.1-25.6 done: container image, lifecycle manager, protocol, activity integration, network isolation, resource limits. 29 new tests. |
| 26 | File-Based Expert Packaging | Complete | 6 stories, manifest schema, scanner, registrar (2026-03-16) |
| 27 | Multi-Source Webhooks | **Meridian Conditional Pass** | 4 blocking gaps: source_name storage, owners, jsonpath-ng eval, Sprint 1 scope |

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
| 7 | 27 | `jsonpath-ng` evaluation unassigned | **Open** — Evaluate in Epic 27 Sprint 1 |

---

## Critical Path

```
Epic 23 (Agent Framework) — COMPLETE
  All 3 sprints delivered. 8/8 agents on AgentRunner. 215+ new tests.

Epic 25 (Container Isolation) — Sprint 1+2 COMPLETE (2026-03-17)
  Stories 25.1-25.6 done. Container image, lifecycle, protocol, activity
  integration, network isolation, per-tier resource limits. 29 new tests.
  Remaining: Sprint 3 (Story 25.7 — observability).

Epic 15 (Real Repo Trial) — IN PROGRESS (2026-03-17)
  Stories 15.1-15.6 complete (mock harness, smoke tests, loopbacks).
  Remaining: Story 15.7 (real repo trial run).

Epic 24 (Chat Approval) — Sprint 1 COMPLETE (2026-03-17)
  Stories 24.1-24.3 done. ReviewContext model, chat persistence, chat API.
  21 new tests. Approval baselines instrumented.
  Remaining: Sprint 2 (Stories 24.4-24.6 — channels + observability).

Epic 27 (Multi-Source Webhooks) — LOWEST PRIORITY
  Growth enabler, no current demand. Defer until pulled.
```

---

## Recommended Next Actions

1. **Epic 25 Sprint 3** — container observability (Story 25.7, OTel spans for container lifecycle)
2. **Epic 15 Story 15.7** — real repo trial run (final validation)
3. **Epic 24 Sprint 2** — notification channels (GitHub, Slack) + audit observability
4. **Epic 27** — defer until demand materializes
