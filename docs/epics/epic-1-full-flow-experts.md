# Epic 1 — Full Flow + Experts

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Status:** Complete — Router, QA Agent, Assembler, Outcome Ingestor, EffectiveRolePolicy all implemented
**Phase:** 1 (per `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md`)
**Predecessor:** Epic 0 — Foundation (complete: issue → TaskPacket → Context → Intent → Primary Agent → Verification → Publisher → draft PR with evidence)
**Timebox:** 10–12 weeks (aggressive)

---

## 1. Title

Full Flow + Experts — From Single-Role Pipe to Expert-Augmented Delivery with QA Validation

---

## 2. Narrative

Epic 0 proved the pipe: a GitHub issue can travel through intake, context enrichment, intent definition, single-role implementation, deterministic verification, and publication as a draft PR with evidence. But the pipe is narrow — one Developer role, no expert consultation, no QA validation against intent, and no signal consumption for future learning.

Epic 1 widens the pipe into a full runtime flow (steps 1–9 from `15-system-runtime-flow.md`). The system gains the ability to consult domain experts before implementation, assemble their guidance into a single plan with provenance, validate outcomes against intent through a dedicated QA Agent, and consume the resulting signals for future reputation-based routing.

**The business value:** Expert consultation catches domain-specific risks (security, compliance, partner APIs) that a single Developer role misses. QA validation against intent catches intent gaps and implementation bugs before they reach human reviewers. Provenance and signal consumption create the foundation for the learning loop that will close in Phase 2. The repo promotes from Observe to Suggest tier — draft PRs become ready-for-review after verification + QA pass.

**Why now:** The pipe is proven. Every sprint of delay in adding experts means the system ships PRs without domain coverage — the exact failure mode the architecture was designed to prevent. The learning loop (Phase 2) cannot start without signals to consume.

---

## 3. References

| Reference | Path |
|-----------|------|
| Aggressive Roadmap — Phase 1 | `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 76–105 |
| System Overview | `thestudioarc/00-overview.md` |
| Expert Router | `thestudioarc/05-expert-router.md` |
| Expert Recruiter | `thestudioarc/04-expert-recruiter.md` |
| Assembler | `thestudioarc/07-assembler.md` |
| Agent Roles & Overlays | `thestudioarc/08-agent-roles.md` |
| Expert Library | `thestudioarc/10-expert-library.md` |
| Intent Layer | `thestudioarc/11-intent-layer.md` |
| Outcome Ingestor | `thestudioarc/12-outcome-ingestor.md` |
| QA Quality Layer | `thestudioarc/14-qa-quality-layer.md` |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` |
| Coding Standards | `thestudioarc/20-coding-standards.md` |
| Epic 0 Lessons Learned | `docs/LESSONS_LEARNED.md` |

---

## 4. Acceptance Criteria (High Level)

### AC-1: Intake Agent contract

- [ ] Intake Agent has a documented eligibility contract: which events qualify, which are rejected, and why.
- [ ] Intake Agent selects base role from issue type/labels and applies overlays from labels and issue form fields (per `08-agent-roles.md` role selection lifecycle step 1).
- [ ] Rejected events produce a structured rejection record with reason; no silent drops.

### AC-2: Expert Router

- [ ] Router selects expert subset from Intent Specification + risk flags + EffectiveRolePolicy.
- [ ] At least 2 expert classes are routable (Technical, QA/Validation).
- [ ] Mandatory coverage rules fire when risk labels require expert consultation (e.g., `risk:auth` → Security expert).
- [ ] Router produces a consult plan (parallel or staged) with rationale, respecting budget limits.
- [ ] When no eligible expert exists for a required class, Router invokes Recruiter.

### AC-3: Expert Recruiter

- [ ] Recruiter creates experts from vetted templates (at least 2 templates: Security Review, QA Validation).
- [ ] New experts start in shadow or probation tier — never trusted.
- [ ] Recruiter runs qualification harness before registering an expert as eligible.
- [ ] Expert pack includes: scope boundaries, expected outputs, tool allowlist, trust tier.
- [ ] De-duplication: Recruiter prefers version update over new identity.

### AC-4: Expert Library

- [ ] Experts are persisted in Postgres with identity, version, class, capability tags, scope, tool policy, trust tier, lifecycle state.
- [ ] Library supports search by class and capability for Router queries.
- [ ] Versioning: new versions of existing experts are tracked; deprecated experts remain discoverable but ineligible.
- [ ] At least 2 vetted expert templates are seeded (Security Review, QA Validation).

### AC-5: Assembler

- [ ] Assembler merges expert outputs into a single plan with provenance links (expert id, version, decision).
- [ ] Conflicts are resolved using intent constraints as tie-breaker.
- [ ] When intent is ambiguous, Assembler triggers intent refinement with explicit questions.
- [ ] Plan includes: steps, checkpoints, risk list, QA handoff mapping acceptance criteria to validations.
- [ ] Provenance minimum record fields are present (per `07-assembler.md`).

### AC-6: QA Agent

- [ ] QA Agent validates implementation against Intent Specification acceptance criteria.
- [ ] Defects are classified by category (intent_gap, implementation_bug, regression, security, performance, compliance, partner_mismatch, operability) and severity (S0–S3) per `14-qa-quality-layer.md`.
- [ ] `intent_gap` blocks `qa_passed` — no exception.
- [ ] QA emits `qa_passed`, `qa_defect`, or `qa_rework` signals to JetStream.
- [ ] QA failure triggers loopback to Primary Agent with defect list and intent mapping.
- [ ] QA can request intent refinement when acceptance criteria are ambiguous or missing.

### AC-7: Outcome Ingestor (stub)

- [ ] Stub consumes verification and QA signals from JetStream.
- [ ] Signals are correlated to TaskPacket by correlation_id.
- [ ] Consumed signals are persisted for analytics (no reputation update yet — Phase 2).
- [ ] Quarantine: signals missing correlation_id or referencing unknown TaskPackets are quarantined, not dropped.

### AC-8: Evidence comment — full format

- [ ] PR evidence comment includes: TaskPacket id, correlation id, intent version + summary, acceptance criteria checklist, what changed, verification summary, QA result, expert coverage summary, loopback summary.
- [ ] Format matches the standard from `15-system-runtime-flow.md` "Standard Agent Evidence Comment."

### AC-9: Suggest tier promotion

- [ ] Repo promoted from Observe to Suggest tier.
- [ ] Draft PR becomes ready-for-review only after verification + QA pass.
- [ ] Tier change is recorded in Repo Profile and reflected in lifecycle labels.

### AC-10: Provenance and traceability

- [ ] Every workflow produces a provenance minimum record (per `07-assembler.md`): TaskPacket id, correlation_id, repo id/tier, intent version, base role + overlays, experts consulted, plan id, verification outcomes, QA outcomes, Publisher actions.
- [ ] Provenance is stored and queryable.

### AC-11: Intent refinement loop

- [ ] Intent can be refined when QA or Assembler identifies ambiguity.
- [ ] Refinement is versioned — prior intent versions are preserved.
- [ ] Refinement triggers are traceable in provenance.

---

## 5. Constraints & Non-Goals

### Constraints

- **Architecture:** Build to `thestudioarc/` docs. When the build diverges, update the docs or fix the build.
- **Single repo:** Epic 1 operates on the same single repo as Epic 0. Multi-repo is Phase 2.
- **Publisher-only writes:** No agent other than Publisher writes to GitHub. Enforced by token scope, not convention.
- **Gates fail closed:** Verification and QA gates fail closed. No silent skip.
- **Small diffs:** One commit per story minimum. Prefer small, focused PRs (lesson from Epic 0).
- **Observability:** All new components must emit OpenTelemetry spans with correlation_id.

### Non-Goals

- **Reputation Engine:** No reputation weight updates. Outcome Ingestor is a stub that persists signals; reputation scoring is Phase 2.
- **Multi-repo:** No second repo onboarded. Phase 2.
- **Admin UI:** No UI. Phase 2.
- **Execute tier:** Repo stays in Suggest tier. Execute tier requires compliance checker (Phase 2).
- **Model Gateway:** Agents call LLMs directly. Model Gateway routing is Phase 4.
- **Tool Hub (MCP):** No centralized tool gateway. Tools are configured per-agent. Phase 4.
- **Service Context Packs in production use:** Context Manager may attach packs, but production packs for real services are Phase 3.
- **Auto-merge:** Publisher stops at ready-for-review. Merge is human-driven.

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
| **Expert coverage on risk-flagged tasks** | 100% of tasks with risk labels have at least one expert consulted | Query TaskPacket provenance: risk_flags present → expert_consulted count > 0 |
| **QA defect classification** | 100% of QA defects have category + severity | Schema validation on qa_defect signals |
| **Intent gap blocking** | 0 qa_passed signals when intent_gap defects exist | Signal stream audit |
| **Evidence comment completeness** | 100% of PRs have full-format evidence comment | Automated check on PR creation |
| **Signal consumption** | 100% of verification + QA signals consumed by Outcome Ingestor stub | JetStream consumer lag = 0 for consumed subjects |
| **Provenance completeness** | 100% of completed workflows have all minimum record fields | Query provenance store |
| **Suggest tier active** | Repo in Suggest tier; at least 1 PR marked ready-for-review after V+QA pass | Repo Profile query + GitHub PR state |

---

## 8. Context & Assumptions

### Dependencies

| Dependency | Status | Owner |
|------------|--------|-------|
| Epic 0 codebase (all modules) | Complete | — |
| PostgreSQL, Temporal, NATS JetStream | Running | Infra (Epic 0) |
| GitHub App with webhook + PR permissions | Installed | Infra (Epic 0) |
| Claude Agent SDK | Available | External |
| thestudioarc/ docs (05, 07, 08, 10, 11, 12, 14, 15) | Published | — |

### Assumptions

- Expert consultation in Phase 1 uses LLM-based experts (prompt-driven), not human-backed experts. Human-backed experts are Phase 3+.
- The 2 initial expert templates (Security Review, QA Validation) are sufficient for the single test repo. More templates are Phase 3.
- Temporal workflows from Epic 0 can be extended to include Router → Recruiter → Assembler → QA steps without a full workflow rewrite.
- NATS JetStream subjects from Epic 0 (verification signals) are extensible for QA signals with the same consumer pattern.
- The Complexity Index v0 from Epic 0 (low/medium/high) is sufficient for Phase 1 routing. A formal Complexity Index with defined dimensions is Phase 2–3.

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Assembler conflict resolution under-specified → inconsistent plans | High | Explicit conflict rules tested with conflicting expert outputs; intent is the tie-breaker |
| QA taxonomy not enforced → noisy signals | High | Schema validation on qa_defect; category and severity required |
| Expert qualification harness too shallow → low-quality experts | Medium | Start with 2 vetted templates; qualification checks structure, scope, and tool compliance |
| Temporal workflow complexity grows → harder to debug | Medium | One workflow step per new component; observability spans on each; use Temporal UI for visibility |
| Intent refinement loop causes infinite cycles | Medium | Cap refinement to 2 versions per workflow; escalate after cap |

---

## Story Decomposition (Preliminary)

Stories should be broken into vertical slices that deliver testable value. Helm will refine ordering, sizing, and sprint boundaries.

**Requirement (Meridian):** Before any story enters a sprint, Helm must define a per-story Definition of Done with testable criteria that references the specific thestudioarc doc (e.g., story 1.3 DoD references `05-expert-router.md`). No story is sprint-ready without this.

| Story ID | Title | Dependencies | Size Estimate |
|----------|-------|-------------|---------------|
| 1.1 | Intake Agent — eligibility contract, role selection, overlay application | Epic 0 ingress | M |
| 1.2 | Expert Library — Postgres schema, CRUD, search, seeded templates | — | L |
| 1.3 | Expert Router — expert selection from intent + risk flags + mandatory coverage | 1.2 (library), Epic 0 intent | L |
| 1.4 | Expert Recruiter — template-based creation, qualification harness, trust tiers | 1.2 (library) | L |
| 1.5 | Assembler — merge expert outputs, conflict resolution, provenance, QA handoff | 1.3 (router outputs) | L |
| 1.6 | QA Agent — intent validation, defect taxonomy, signal emission, loopback | Epic 0 verification, 1.5 (plan) | L |
| 1.7 | Intent refinement loop — versioned refinement from QA/Assembler triggers | Epic 0 intent, 1.5, 1.6 | M |
| 1.8 | Outcome Ingestor stub — signal consumption, correlation, persistence, quarantine | Epic 0 JetStream, 1.6 (QA signals) | M |
| 1.9 | Evidence comment — full format with expert coverage, QA result, provenance | 1.5, 1.6, Epic 0 publisher | M |
| 1.10 | Suggest tier promotion — tier change, ready-for-review gate, lifecycle labels | 1.6 (QA pass required) | S |
| 1.11 | Workflow integration — extend Temporal workflow to include Router → Assembler → QA steps | 1.1–1.6 | L |
| 1.12 | EffectiveRolePolicy — compute and enforce role + overlays across Router, tools, V, QA, Publisher | 1.1 (roles), 1.3 (router) | M |

---

*Epic created by Saga. Awaiting Meridian review before commit.*
