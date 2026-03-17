# Epic Status Tracker

> Consolidated status of all epics as of 2026-03-17.
> Source of truth for epic status is each epic's own file. This tracker is a rollup view.

---

## Summary

| Metric | Value |
|--------|-------|
| Total epics | 29 (0-29) |
| Complete | 26 |
| Meridian Reviewed (Conditional Pass) | 1 (Epic 27) |
| Meridian Reviewed (Ready to Commit) | 2 (Epics 28, 29) |
| Tests passing | 2,060+ |
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
| 27 | Multi-Source Webhooks | **Meridian Conditional Pass** | 4 blocking gaps: source_name storage, owners, jsonpath-ng eval, Sprint 1 scope |

## Phase 6 — Pipeline Intelligence + Portfolio Visibility (Planned)

| Epic | Title | Status | Notes |
|------|-------|--------|-------|
| 28 | Preflight Plan Review Gate | **Meridian Reviewed — Ready to Commit** | Lightweight per-TaskPacket plan quality gate (new persona: Preflight). 4 stories, 1 sprint. All Meridian gaps resolved. |
| 29 | GitHub Projects v2 + Meridian Portfolio Review | **Meridian Reviewed — Ready to Commit** | Projects v2 sync + periodic Meridian health review. 9 stories, 2 sprints. All Meridian gaps resolved. |

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

---

## Critical Path

```
Phase 5 — COMPLETE (2026-03-17)
  All epics closed except Epic 27 (deferred, no demand).

  Epic 15 (Real Repo Trial) — COMPLETE
    All 7 stories delivered. Onboarding guide enriched with 7 sections.

  Epic 24 (Chat Approval) — COMPLETE
    All 6 stories, 2 sprints. Notification channels (GitHub + Slack),
    OTel spans, NATS signals, approval metadata in evidence comments.
    56+ new tests.

  Epic 25 (Container Isolation) — COMPLETE
    All 7 stories, 3 sprints. Container lifecycle with full OTel observability,
    log capture with correlation_id, structured metrics. 35+ new tests.

  Epic 27 (Multi-Source Webhooks) — DEFERRED
    Growth enabler, no current demand. Defer until pulled.
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

1. **Epic 28** — Preflight plan review gate (Meridian-reviewed, ready to commit)
2. **Epic 29** — GitHub Projects v2 + Meridian portfolio review (can parallel with Epic 28)
3. **Epic 27** — defer until demand materializes
