# Epic Status Tracker

> Consolidated status of all epics as of 2026-03-16 (end of session).
> Source of truth for epic status is each epic's own file. This tracker is a rollup view.

---

## Summary

| Metric | Value |
|--------|-------|
| Total epics | 27 (0-27) |
| Complete | 22 |
| In Progress | 1 (Epic 23) |
| Meridian Reviewed (Conditional Pass) | 3 (Epics 24, 25, 27) |
| Ready to Execute | 1 (Epic 15) |
| Tests passing | 1,798+ |
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
| 15 | E2E Integration & Real Repo Onboarding | **Ready to Execute** | 2 Meridian rounds passed. Session plan created. |
| 16 | Issue Readiness Gate | Complete | Sprint 17 (16.1-16.4) + Sprint 18 (16.5-16.8) |
| 17 | Poll for Issues (Backup) | Complete | All 8 stories, 2 sprints (2026-03-13) |
| 18 | Production E2E Test Suite | Complete | 5 slices, full contract coverage (2026-03-16) |
| 19 | Critical Gaps Batch 1 | Complete | Gateway wiring, security scans, reputation persistence (Sprint 19) |
| 20 | Critical Gaps Batch 2 | Complete | JetStream consumption, escalation, adversarial detection (Sprint 19) |
| 21 | Human Approval Wait States | Complete | 9 stories, Temporal durable wait, 7-day timeout (2026-03-13) |
| 22 | Execute Tier End-to-End | Complete | 18 stories, auto-merge gating, compliance enforcement |
| 23 | Unified Agent Framework | **In Progress** | Sprint 1: 10/10 done. Sprint 2: Intake + Context configs done (42 tests), Intent + Router next. Hardening 1.11-1.13 remain. |
| 24 | Chat Approval Workflows | **Meridian Conditional Pass** | 5 blocking gaps: rejection status, baselines, owners, reject signal, evidence edge case |
| 25 | Container Isolation | **Meridian Conditional Pass** | 4 blocking gaps: Execute fallback policy, owners, dates, Epic 22 dep |
| 26 | File-Based Expert Packaging | Complete | 6 stories, manifest schema, scanner, registrar (2026-03-16) |
| 27 | Multi-Source Webhooks | **Meridian Conditional Pass** | 4 blocking gaps: source_name storage, owners, jsonpath-ng eval, Sprint 1 scope |

---

## Cross-Epic Blocking Items (from Meridian Reviews 2026-03-16)

These must be resolved before Epics 24, 25, 27 can be committed:

| # | Epic | Blocker | Owner |
|---|------|---------|-------|
| 1 | All (24, 25, 27) | All stakeholder roles are "TBD" — need named owners | TBD |
| 2 | 24 | No rejection status in TaskPacket `ALLOWED_TRANSITIONS` — design decision required | TBD |
| 3 | 24 | Success metrics lack baselines — measure current approval time and timeout rate first | TBD |
| 4 | 25 | Silent fallback to in-process on Execute tier is a security hole — need per-tier fallback policy | TBD |
| 5 | 25 | DB-free execution path for container runner — `implement()` requires `AsyncSession` | TBD |
| 6 | 27 | `source_name` storage ambiguity — scope JSON vs new column, migration decision required | TBD |
| 7 | 27 | `jsonpath-ng` evaluation unassigned — load-bearing dependency masquerading as risk | TBD |

---

## Critical Path

```
Epic 23 (Agent Framework) — IN PROGRESS
  Sprint 1 ---- DONE (10/10 stories)
  Sprint 2 ---- Intake + Context configs DONE; Intent + Router next
  Hardening --- 1.11-1.13 (prompt guard, pipeline budget, context compression)
  Sprint 3 ---- Recruiter + Assembler + QA conversions

Epic 15 (Real Repo Trial) — READY TO EXECUTE
  Session plan created, Meridian approved (2 rounds)
  Start with Story 15.1: mock provider harness

Epic 25 (Container Isolation) — FIX BLOCKERS, THEN EXECUTE
  Highest infrastructure priority after Epic 23
  Critical for safe Execute tier on untrusted repos

Epic 24 (Chat Approval) — FIX BLOCKERS, THEN EXECUTE
  UX improvement for Execute tier reviewers

Epic 27 (Multi-Source Webhooks) — LOWEST PRIORITY
  Growth enabler, no current demand
```

---

## Recommended Next Actions

1. **Continue Epic 23 Sprint 2** — convert Intent Builder + Router agents to AgentRunner
2. **Start Epic 15 Story 15.1** — mock provider harness (unblocks Stories 15.2-15.5)
3. **Fix cross-epic blockers** on Epics 24, 25, 27 — then re-review
4. **Epic 23 hardening** (Stories 1.11-1.13) — prompt guard, pipeline budget, context compression
5. **Epic 25 Sprint 1** — container runner foundation (after blockers fixed)
