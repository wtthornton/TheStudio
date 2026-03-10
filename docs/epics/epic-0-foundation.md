# Phase 0 — Foundation: Prove the Pipe

<!-- docsmcp:start:metadata -->
**Status:** Complete — All 9 stories implemented with full test coverage (1,558+ unit tests)
**Priority:** P0 - Critical
**Estimated LOE:** ~8-10 weeks (1-2 developers)
**Dependencies:** None (first epic)
**Blocks:** Epic 1 (Full flow + experts), Epic 2 (Learning + multi-repo), Epic 3 (Scale + quality bar), Epic 4 (Platform maturity)
**OKR Link:** Foundation for all OKRs — proves the pipe that quality, performance, and time-to-market are measured against

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:goal -->
## Goal

One registered repo at Observe tier. Issue triggers the full pipeline: TaskPacket creation, Context enrichment (scope + risk flags + Complexity Index v0), Intent Specification (goal, constraints, acceptance criteria, non-goals), Primary Agent implementation (single Developer role), Verification Gate checks with loopback on failure (max 2), and Publisher creates a draft PR with evidence comment and lifecycle labels. End-to-end pipe proven with idempotency, dedupe, and OpenTelemetry tracing.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Every later phase — experts, QA agents, multi-repo, learning loop, Admin UI — depends on this pipe being real and tested. Validating the core architecture before investing in scale eliminates the risk of building on unproven foundations. This is the smallest scope that proves the system works end-to-end, from GitHub issue to draft PR with evidence.

<!-- docsmcp:end:motivation -->

---

## Narrative

TheStudio converts GitHub issues into high-quality pull requests. Before we can route to experts, learn from outcomes, or scale to many repos, we must prove the core pipe: a single issue enters the system, flows through enrichment and intent definition, is implemented by one agent role, passes verification, and emerges as a draft PR with evidence that traces back to the original intent.

Phase 0 is deliberately constrained: one repo, one agent role (Developer), no expert bench, no QA agent. The constraint is the point — we prove the pipe works before adding complexity.

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] 100% of test issues that meet eligibility produce exactly one TaskPacket and one workflow run (no duplicate workflows)
- [ ] 100% of published PRs have an evidence comment containing: TaskPacket ID, intent summary, verification result
- [ ] 100% of published PRs have correct lifecycle labels (agent:in-progress, then agent:queued or agent:done)
- [ ] Verification failure causes a loopback to Primary Agent with evidence; no silent skip (max 2 loopbacks)
- [ ] Ingress dedupe prevents duplicate TaskPackets when the same delivery ID is replayed
- [ ] Publisher idempotency key (TaskPacket ID + intent version) prevents duplicate PRs on retry
- [ ] All workflow spans carry correlation_id via OpenTelemetry and are queryable
- [ ] One runnable diagram or doc matches the as-built flow: Intake -> Context -> Intent -> Primary Agent -> Verification -> Publisher

<!-- docsmcp:end:acceptance-criteria -->

---

## References

- Architecture overview: `thestudioarc/00-overview.md`
- System runtime flow: `thestudioarc/15-system-runtime-flow.md`
- Agent roles: `thestudioarc/08-agent-roles.md`
- Intent layer: `thestudioarc/11-intent-layer.md`
- Verification gate: `thestudioarc/13-verification-gate.md`
- Coding standards: `thestudioarc/20-coding-standards.md`
- Project structure: `thestudioarc/21-project-structure.md`
- Aggressive roadmap (Phase 0): `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 46-73

---

<!-- docsmcp:start:stories -->
## Stories

### 0.1 — Ingress: webhook receive, signature validation, dedupe
**Points:** 8 (L)
Webhook handler receives GitHub issue events, validates webhook signatures, deduplicates by delivery ID + repo, creates TaskPacket, and starts a Temporal workflow with correlation_id. [Full story: stories/story-0.1-ingress.md]

### 0.2 — TaskPacket: minimal schema and persistence
**Points:** 5 (M)
Define the TaskPacket model (repo, issue_id, correlation_id, status, created/updated), database migration, and CRUD operations. Foundation that all downstream components depend on. [Full story: stories/story-0.2-taskpacket.md]

### 0.3 — Context Manager: enrich TaskPacket with scope and risk flags
**Points:** 8 (L)
Enrich TaskPacket with scope analysis and risk flags. Attach 0..n Service Context Packs (stub or one real pack). Compute Complexity Index v0 (low/medium/high from scope + risk). [Full story: stories/story-0.3-context-manager.md]

### 0.4 — Intent Builder: produce Intent Specification
**Points:** 8 (L)
Produce Intent Specification from enriched TaskPacket: goal, constraints, acceptance criteria, non-goals. Persist intent with version. No expert consult yet. [Full story: stories/story-0.4-intent-builder.md]

### 0.5 — Primary Agent: single Developer role implementing from intent
**Points:** 13 (XL)
Single base role (Developer) implements changes from Intent Specification. Produces evidence bundle (test/lint summary). Tool allowlist enforced. No Router or Assembler. [Full story: stories/story-0.5-primary-agent.md]

### 0.6 — Verification Gate: repo-profile checks with loopback
**Points:** 8 (L)
Run repo-profile checks (ruff, pytest). Emit verification_passed / verification_failed to JetStream. Loopback to Primary Agent on failure (max 2 loopbacks for Phase 0). [Full story: stories/story-0.6-verification-gate.md]

### 0.7 — Publisher: draft PR with evidence comment
**Points:** 8 (L)
Create draft PR on GitHub. Add evidence comment (TaskPacket ID, intent summary, verification result). Apply lifecycle labels. Idempotency key = TaskPacket ID + intent version. [Full story: stories/story-0.7-publisher.md]

### 0.8 — Repo Profile: register one repo at Observe tier
**Points:** 5 (M)
Register one repo with tier = Observe. Define required checks and tool allowlist. Configuration persistence. Foundation for tier promotion in Phase 2. [Full story: stories/story-0.8-repo-profile.md]

### 0.9 — Observability: OpenTelemetry tracing with correlation_id
**Points:** 5 (M)
Set up OpenTelemetry. Instrument all flow steps with spans. Propagate correlation_id across Intake, Context, Intent, Agent, Verification, Publisher. [Full story: stories/story-0.9-observability.md]

**Total estimated points:** 68

<!-- docsmcp:end:stories -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **PostgreSQL** as the database for Phase 0 (native UUID, strong constraints, JSON columns for enrichment data)
- **Temporal** for durable workflow orchestration (retry, timeout, correlation)
- **NATS JetStream** for verification/QA signal streaming
- **GitHub API** for webhook ingestion and PR publishing (GitHub App, not PAT — installation token per repo)
- **Claude Agent SDK** with claude-sonnet-4-5 for the Primary Agent Developer role
- **OpenTelemetry** for distributed tracing with correlation_id on all spans
- **Python** as primary language per coding standards (`thestudioarc/20-coding-standards.md`)
- **Idempotency keys** on TaskPacket creation (delivery ID + repo) and PR publishing (TaskPacket ID + intent version)

<!-- docsmcp:end:technical-notes -->

---

## Stakeholders & Roles

- **Epic owner:** Engineering lead
- **Implementation:** 1-2 developers
- **Review:** Meridian (epic and plan review via checklist)
- **Architecture:** Architecture docs in `thestudioarc/` are source of truth

---

## Success Metrics

| Metric | Target | How we read it |
|--------|--------|----------------|
| TaskPacket dedupe accuracy | 100% (no duplicates on replay) | Integration test with replayed delivery IDs |
| PR evidence completeness | 100% (all 3 fields present) | Automated check on PR creation |
| Verification loopback correctness | 100% (no silent skips) | Integration test with failing verification |
| End-to-end latency (issue to draft PR) | Measured, no target yet | OpenTelemetry trace duration |

---

<!-- docsmcp:start:non-goals -->
## Out of Scope / Non-Goals

- No expert bench or expert routing (Phase 1)
- No QA Agent or defect taxonomy (Phase 1)
- No Router or Assembler (Phase 1)
- No multi-repo support (Phase 2)
- No Reputation Engine or learning loop (Phase 2)
- No Admin UI (Phase 2)
- No Execute tier or compliance checker (Phase 2)
- No Service Context Packs beyond stubs (Phase 3)
- No single-pass success target (Phase 3 sets >= 60%)

<!-- docsmcp:end:non-goals -->

---

## Context & Assumptions

- GitHub is the only intake source (webhook events on issues)
- One repo is sufficient to prove the pipe; multi-repo is Phase 2
- Developer role is the only agent role needed for Phase 0
- Manual QA check is acceptable (no QA Agent until Phase 1)
- Observe tier means draft PRs only; no auto-merge
- **Infrastructure provisioned by the implementation team during Sprint 1 setup:**
  - PostgreSQL instance (local Docker or managed — team decides)
  - Temporal server (local Docker for dev, Temporal Cloud for staging)
  - NATS JetStream (local Docker for dev, managed for staging)
  - GitHub App created and installed on the target repo (installation token flow)
  - No external infra team dependency — the 1-2 developers self-provision

---

<!-- docsmcp:start:implementation-order -->
## Implementation Order

```
Sprint 1 (weeks 1-3):
  0.2 TaskPacket schema         (no deps — everything needs this)
  0.8 Repo Profile              (no deps — config foundation)
  0.1 Ingress                   (depends on 0.2)
  0.9 Observability             (parallel — no deps)

Sprint 2 (weeks 4-6):
  0.3 Context Manager           (depends on 0.2)
  0.4 Intent Builder            (depends on 0.3)
  0.6 Verification Gate         (depends on 0.8)

Sprint 3 (weeks 7-9):
  0.5 Primary Agent             (depends on 0.4, 0.6)
  0.7 Publisher                 (depends on 0.5, 0.6)

Week 10: Integration test, diagram validation, buffer
```

<!-- docsmcp:end:implementation-order -->

---

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ingress dedupe wrong -> duplicate TaskPackets or workflows | Medium | High | Tests with replay of same delivery ID; idempotency tests |
| Publisher creates duplicate PRs on retry | Medium | High | Idempotency key and lookup-before-create in place before first publish |
| Temporal workflow timeout misconfigured -> stuck workflows | Low | Medium | Explicit timeout and retry policies; integration test for timeout scenarios |
| Context Manager scope analysis too coarse -> wrong risk flags | Low | Low | Manual review of first 10 enrichments; iterate Complexity Index v0 |
| JetStream signal loss -> verification result not recorded | Low | High | At-least-once delivery; dead-letter queue; integration test for signal flow |

<!-- docsmcp:end:risk-assessment -->

---

*Epic created by Saga. Pending Meridian review before commit.*
