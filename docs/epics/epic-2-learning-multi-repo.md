# Epic 2 — Learning + Multi-Repo

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Phase:** 2 (per `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`)
**Status:** Complete — Complexity Index, Outcome Ingestor, Reputation Engine with tiers/decay/drift, Router uses weights
**Predecessor:** Epic 1 — Full Flow + Experts (complete: 9-step pipeline wired with Router, Assembler, QA Agent, Outcome Ingestor stub, EffectiveRolePolicy, tier promotion to Suggest)
**Timebox:** 10–12 weeks (aggressive)

---

## 1. Title

Learning + Multi-Repo — Close the Learning Loop and Scale to Fleet Operations

---

## 2. Narrative

Epic 1 delivered the full 9-step pipeline: Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish. The system consults domain experts, validates against intent, and emits signals to JetStream. But the signals dead-end in a stub Outcome Ingestor — no normalization, no attribution, no reputation update. The Router selects experts without learning from past outcomes. And the platform operates on a single repo with no administrative visibility.

Epic 2 closes the learning loop and scales to fleet operations. The Outcome Ingestor gains full normalization by Complexity Index, attribution using provenance, and quarantine handling. The Reputation Engine stores weights by expert and context key, computes confidence, manages trust tier transitions, and exposes weights to the Router. The Router consumes these weights for smarter expert selection. A Compliance Checker gates Execute tier promotion — no repo gets full workflow authority without passing compliance rules. The Admin UI provides fleet-wide visibility: health dashboards, repo management, task/workflow consoles, and RBAC-protected controls. Multiple repos are registered, with at least one promoted to Execute tier.

**The business value:** A closed learning loop means the system improves with every task — experts that consistently produce good outcomes gain influence, while underperformers are detected and either improved or demoted. Fleet visibility through Admin UI eliminates log spelunking and database queries for operations. Execute tier demonstrates that the platform can safely run full workflows under compliance governance. Multi-repo proves the architecture scales beyond a single codebase.

**Why now:** The pipe works. Signals flow. But without learning, the system is static — experts are selected without evidence of past performance, and operations have no visibility into what's happening. Every sprint without the learning loop is a sprint of wasted outcome data. The aggressive roadmap demands visible metrics (single-pass success, loopback counts) by Phase 2 end.

---

## 3. References

| Reference | Path |
|-----------|------|
| Aggressive Roadmap — Phase 2 | `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 108–135 |
| Reputation Engine | `thestudioarc/06-reputation-engine.md` |
| Outcome Ingestor (full) | `thestudioarc/12-outcome-ingestor.md` |
| Admin Control UI | `thestudioarc/23-admin-control-ui.md` |
| Architecture Guardrails | `thestudioarc/22-architecture-guardrails.md` |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` |
| Agent Roles & Overlays | `thestudioarc/08-agent-roles.md` |
| Expert Router | `thestudioarc/05-expert-router.md` |
| Expert Library | `thestudioarc/10-expert-library.md` |
| Coding Standards | `thestudioarc/20-coding-standards.md` |
| Epic 1 Complete | `docs/epics/epic-1-full-flow-experts.md` |
| Lessons Learned | `docs/LESSONS_LEARNED.md` |

---

## 4. Acceptance Criteria (High Level)

### AC-1: Complexity Index v1

- [ ] Complexity Index is formally defined with documented dimensions (scope breadth, risk flags, dependency count, lines changed, expert count consulted).
- [ ] Formula/rubric is documented and versioned.
- [ ] Complexity Index is computed by Context Manager and stored on TaskPacket.
- [ ] Index is used by Outcome Ingestor for normalization.
- [ ] At least one report or dashboard uses Complexity Index for fair comparison.

### AC-2: Outcome Ingestor (full)

- [ ] Normalizes signals by Complexity Index v1 — hard tasks don't poison weights.
- [ ] Attributes outcomes to experts using provenance links from Assembler.
- [ ] Produces indicators for Reputation Engine (success, failure, loopback count, defect category, severity).
- [ ] Quarantine: signals missing correlation_id, unknown TaskPacket, invalid category/severity are quarantined with reason.
- [ ] Dead-letter: unparseable signals after N attempts move to dead-letter stream with raw payload.
- [ ] Reopen event handling: issue reopened, regression issue linked, rollback PR linked — all treated as high-signal quality outcomes and classified (intent_gap, implementation_bug, regression, governance_failure).
- [ ] Replay: quarantined events can be corrected and replayed; replay is deterministic.

### AC-3: Reputation Engine

- [ ] Stores weights by expert id + context key (repo, risk class, complexity band).
- [ ] Computes confidence based on sample size and provenance completeness.
- [ ] Handles decay: weights decay over time to prevent stale overconfidence.
- [ ] Trust tier transitions: shadow → probation → trusted, with evidence-based promotion/demotion.
- [ ] Exposes weights and confidence to Router via query API.
- [ ] Emits signals: weight_updated, confidence_updated, trust_tier_changed, drift_detected.
- [ ] Attribution rules enforced: intent_gap doesn't penalize experts; missing coverage is routing/policy failure.

### AC-4: Router — reputation-aware selection

- [ ] Router queries Reputation Engine for expert weights and confidence.
- [ ] Expert selection factors in reputation weights alongside mandatory coverage and budget.
- [ ] High-confidence experts are preferred; low-confidence experts are consulted with caution.
- [ ] Mandatory coverage rules unchanged — reputation adjusts selection within required classes, not across them.
- [ ] Selection rationale includes reputation weight and confidence for traceability.

### AC-5: Compliance Checker

- [ ] Runs before Execute tier promotion; results are persisted.
- [ ] Checks: rulesets configured, required reviewer rules for sensitive paths, branch protections, standard labels/Projects fields, evidence comment format, Publisher idempotency guard, execution plane health, credentials scope.
- [ ] Promotion blocked until all required checks pass.
- [ ] Remediation: checker output includes which checks failed and how to fix.
- [ ] Admin UI shows compliance score and blocks promotion UI until passing.

### AC-6: Execute tier — one repo promoted

- [ ] At least one repo promoted to Execute tier with compliance checker passed.
- [ ] Execute tier behavior: full workflow with human merge default (no auto-merge yet).
- [ ] Execute tier is revocable if compliance drifts below threshold.
- [ ] Tier transition recorded with audit metadata (who, when, compliance score).

### AC-7: Admin UI (core)

- [ ] **Fleet Dashboard:** Global health (Temporal, JetStream, Postgres, Router), queue depth, workflow counts by status (running, stuck, failed), hot alerts.
- [ ] **Repo Management:** Register repos, view/edit Repo Profile, deploy/pause/resume execution plane, disable writes (Publisher freeze), view tier and promotion eligibility, recent outcomes (single-pass rate, loopback counts, QA defects).
- [ ] **Task and Workflow Console:** View active/stuck workflows, timeline of workflow steps, evidence and failure categories, safe rerun controls (context, intent, routing, QA, verification).
- [ ] **RBAC:** Role-based access control for Admin UI actions (view-only vs operator vs admin).
- [ ] **Audit log:** All control actions logged with actor, timestamp, action, target.

### AC-8: Multi-repo — 3+ repos registered

- [ ] At least 3 repos registered with the platform.
- [ ] At least 2 repos in Suggest or Execute tier (not just Observe).
- [ ] Per-repo credential scoping: repo secrets never leak across repos.
- [ ] Fleet Dashboard shows all repos with health, queue, tier, and outcome metrics.

### AC-9: Quarantine operations in Admin UI

- [ ] View quarantined events count by repo and category.
- [ ] Drill-down to failure reason and payload pointer.
- [ ] Replay action with audit log.
- [ ] No silent drops — all quarantined signals are visible and actionable.

### AC-10: Metrics visibility in Admin UI

- [ ] Single-pass success rate by repo (verification + QA pass on first attempt).
- [ ] Verification loopback counts by category (lint, test, type, security).
- [ ] QA defect counts by severity and category.
- [ ] Reopen rate tracking (if data available from GitHub events).
- [ ] All metrics use Complexity Index normalization where applicable.

---

## 5. Constraints & Non-Goals

### Constraints

- **Architecture:** Build to `thestudioarc/` docs. When the build diverges, update the docs or fix the build.
- **Publisher-only writes:** No agent other than Publisher writes to GitHub. Enforced by token scope.
- **Gates fail closed:** Verification, QA, and Compliance Checker gates fail closed.
- **Small diffs:** One commit per story minimum. Prefer small, focused changes.
- **Observability:** All new components emit OpenTelemetry spans with correlation_id.
- **Mypy in the edit loop:** Run mypy during implementation, not just at the end (lesson from Epic 0).
- **Integration tests against real services:** Data-layer stories require integration tests against real PostgreSQL, not just mocked sessions (lesson from Sprint 1).
- **Infra setup is a real story:** Any infrastructure setup (new services, containers, schemas) is estimated and has DoD.

### Non-Goals

- **Model Gateway:** Agents call LLMs directly. Model Gateway routing is Phase 4.
- **Tool Hub (MCP):** No centralized tool gateway. Phase 4.
- **Expert Performance Console (full):** Core Admin UI includes basic metrics; full expert performance drilldown is Phase 3.
- **Evals suite:** Formal evals (intent correctness, routing correctness) are Phase 3.
- **Single-pass success target (60%):** Tracking is Phase 2; the 60% target and remediation are Phase 3.
- **Service Context Packs in production use:** Packs may exist; production use across repos is Phase 3.
- **Auto-merge:** Publisher stops at ready-for-review. Merge is human-driven even in Execute tier.
- **OpenClaw integration:** Optional sidecar is Phase 4.
- **Second execution plane:** Multi-repo uses shared execution plane or minimal per-repo isolation; dedicated multi-plane deployment is Phase 4.

---

## 6. Stakeholders & Roles

| Role | Responsibility |
|------|----------------|
| **Saga** | Epic definition (this document) |
| **Meridian** | Epic review and plan review |
| **Helm** | Sprint planning and order of work |
| **Developer(s)** | Implementation per stories |
| **thestudioarc/** | Source of truth for architecture |

---

## 7. Success Metrics

| Metric | Target | How measured |
|--------|--------|-------------|
| **Reputation weights update after task completion** | 100% of completed tasks (V+QA outcomes) trigger reputation update | Query Reputation Engine for weight_updated signals linked to TaskPackets |
| **Router uses reputation weights** | 100% of expert selections include reputation weight/confidence in selection rationale | Query Router decision logs for reputation fields |
| **Single-pass success rate visible** | Metric displayed in Admin UI by repo | Admin UI dashboard query |
| **V/QA loopback counts visible** | Metric displayed in Admin UI by repo | Admin UI dashboard query |
| **Execute tier promotion with compliance** | At least 1 repo promoted; compliance checker passed | Repo Profile query + compliance checker result |
| **Quarantined signals actionable** | 0 quarantined signals without drill-down and replay path | Admin UI quarantine console audit |
| **Complexity Index in use** | Index documented, stored on TaskPacket, used in at least one normalization path | Schema inspection + Outcome Ingestor code audit |
| **Multi-repo registered** | ≥3 repos registered, ≥2 in Suggest/Execute | Repo Profile query |

---

## 8. Context & Assumptions

### Dependencies

| Dependency | Status | Owner |
|------------|--------|-------|
| Epic 1 codebase (all modules, 355 tests) | Complete | — |
| PostgreSQL, Temporal, NATS JetStream | Running | Infra (Epic 0/1) |
| Outcome Ingestor stub (signal consumption, correlation, persistence) | Complete (Epic 1) | — |
| Expert Library with CRUD, search, trust tiers | Complete (Epic 1) | — |
| Router with expert selection, mandatory coverage | Complete (Epic 1) | — |
| EffectiveRolePolicy computation | Complete (Epic 1) | — |
| Repo Profile with Observe/Suggest tiers | Complete (Epic 1) | — |
| thestudioarc/ docs (06, 12, 22, 23) | Published | — |

### Assumptions

- The existing Outcome Ingestor stub can be extended for full normalization and attribution without rewrite.
- Reputation Engine is a new Platform Plane service with its own Postgres tables; it queries provenance but doesn't modify Agent Plane artifacts.
- Admin UI is a separate web application (FastAPI + React or similar); it talks to Platform Plane services via internal APIs, not direct DB access.
- Compliance Checker runs as a platform job (not an agent); results are persisted and queried by Admin UI.
- The 3+ repos for multi-repo can be test repos or forks; they don't need to be production repos.
- Execute tier "human merge default" means Publisher creates the PR and posts evidence, but a human must approve and merge.

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Attribution wrong → reputation punishes wrong expert | High | Enforce provenance minimum record; intent_gap vs implementation_bug attribution rules in code |
| Compliance Checker too loose → unsafe repos promoted to Execute | High | Checklist from `23-admin-control-ui.md`; manual review of first promotions |
| Compliance Checker too strict → no repos reach Execute in timebox | Medium | Start with essential checks (rulesets, reviewer rules); add nice-to-have checks incrementally |
| Admin UI scope creep → timebox blown | High | Core modules only (Fleet, Repo, Task Console, RBAC, Audit); defer Expert Performance Console full to Phase 3 |
| Multi-repo credential isolation complex | Medium | Use shared execution plane with repo-scoped tokens; defer full per-repo planes to Phase 4 |
| Complexity Index dimensions too fuzzy → unfair normalization | Medium | Start with explicit rubric (scope breadth + risk flags + dependency count); iterate based on observed distributions |

---

## Story Decomposition (Preliminary)

Stories should be broken into vertical slices that deliver testable value. Helm will refine ordering, sizing, and sprint boundaries.

**Requirement (Meridian):** Before any story enters a sprint, Helm must define a per-story Definition of Done with testable criteria that references the specific thestudioarc doc. No story is sprint-ready without this.

| Story ID | Title | Dependencies | Size Estimate |
|----------|-------|-------------|---------------|
| 2.1 | Complexity Index v1 — define dimensions, formula, schema, store on TaskPacket | Epic 1 Context Manager | M |
| 2.2 | Outcome Ingestor full — normalization by Complexity Index, attribution via provenance | 2.1 (Complexity Index), Epic 1 Ingestor stub | L |
| 2.3 | Outcome Ingestor — quarantine, dead-letter, replay | 2.2 (Ingestor full) | M |
| 2.4 | Outcome Ingestor — reopen event handling | 2.2 (Ingestor full) | M |
| 2.5 | Reputation Engine — schema, weight storage, confidence computation | 2.2 (indicators from Ingestor) | L |
| 2.6 | Reputation Engine — trust tier transitions, decay, drift detection | 2.5 (Reputation core) | M |
| 2.7 | Router — consume reputation weights in expert selection | 2.5 (Reputation Engine exposes weights) | M |
| 2.8 | Compliance Checker — rulesets, required reviewers, branch protections | Epic 1 Repo Profile | L |
| 2.9 | Execute tier promotion — compliance gate, tier change, audit metadata | 2.8 (Compliance Checker) | M |
| 2.10 | Admin UI — Fleet Dashboard (health, queues, workflows) | Platform services (Temporal, JetStream, Postgres) | L |
| 2.11 | Admin UI — Repo Management (register, tier, pause, disable writes) | 2.10 (Fleet Dashboard infra) | L |
| 2.12 | Admin UI — Task and Workflow Console (timeline, evidence, safe rerun) | 2.10, 2.11 | L |
| 2.13 | Admin UI — RBAC and audit log | 2.10, 2.11, 2.12 | M |
| 2.14 | Admin UI — Quarantine operations (view, drill-down, replay) | 2.3 (quarantine), 2.10 | M |
| 2.15 | Admin UI — Metrics visibility (single-pass, loopbacks, QA defects) | 2.2 (Ingestor), 2.10 | M |
| 2.16 | Multi-repo — register 3+ repos, per-repo credential scoping | 2.11 (Repo Management) | L |
| 2.17 | Multi-repo — at least 2 repos in Suggest/Execute | 2.16, 2.9 (Execute tier) | M |

---

*Epic created by Saga. Awaiting Meridian review before commit.*
