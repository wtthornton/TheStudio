# Sprint 4 Plan — Epic 1: Full Flow + Experts (Final Sprint)

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-1-full-flow-experts.md`
**Sprint duration:** 2 weeks
**Predecessor:** Sprint 3 (complete — Intent Refinement Loop 1.7, Outcome Ingestor Stub 1.8, Evidence Comment Full Format 1.9 landed; 274 tests passing, ruff/mypy clean)

---

## Sprint Goal

**Objective:** Complete Epic 1 by delivering Suggest Tier Promotion (1.10), EffectiveRolePolicy enforcement (1.12), and Temporal Workflow Integration (1.11) — so that the full 9-step runtime flow from GitHub issue to ready-for-review PR with expert consultation, QA validation, and provenance is complete, and the repo promotes from Observe to Suggest tier.

**Test:** The sprint goal is met when:
1. Repo can be promoted from Observe to Suggest tier via `promote_to_suggest()`
2. Tier change is recorded in Repo Profile with audit timestamp and reason
3. Draft PR becomes ready-for-review only after verification + QA pass (Suggest tier gate)
4. Tier labels (`tier:observe`, `tier:suggest`) are reconciled on PRs by Publisher
5. EffectiveRolePolicy is consumed by Router (mandatory coverage), Verification (check strictness), QA (validation strictness), and Publisher (draft vs ready-for-review)
6. Tool allowlists are derived from EffectiveRolePolicy base role
7. Expert eligibility in Router respects policy constraints
8. Temporal workflow defines all 9 runtime steps as activities with timeout/retry per the policy table in `15-system-runtime-flow.md`
9. Workflow wires: Intake → Context → Intent → Router → Assembler → Primary Agent → Verification → QA → Publisher
10. Each activity has timeout and retry config matching the architecture table
11. All code passes `ruff` lint and `mypy` type check
12. All existing tests pass (no regression)

**Constraint:** One commit per story. No partial credit. mypy in the edit loop.

---

## Order of Work

### Phase A — Foundation (1.10 + 1.12)

Stories 1.10 and 1.12 have no mutual dependency and can be developed in parallel.

| Order | Story | Size | Rationale |
|-------|-------|------|-----------|
| 1 | **1.10 Suggest Tier Promotion** | S | Smallest story, unblocks Publisher tier gate behavior |
| 2 | **1.12 EffectiveRolePolicy** | M | Extends existing frozen dataclass; consumed by 1.11 workflow |

### Phase B — Integration (1.11)

Story 1.11 depends on all prior stories (1.1–1.10, 1.12) for the full activity chain.

| Order | Story | Size | Rationale |
|-------|-------|------|-----------|
| 3 | **1.11 Workflow Integration** | L | Wires all 9 steps; depends on everything else being landed |

---

## Story Definitions of Done

### Story 1.10 — Suggest Tier Promotion

**References:** `thestudioarc/15-system-runtime-flow.md` (tier promotion, repo lifecycle), `thestudioarc/08-agent-roles.md`

**DoD:**
- [ ] `promote_to_suggest()` function validates preconditions: verification + QA must have passed
- [ ] Tier change recorded in Repo Profile (Observe → Suggest) with audit metadata
- [ ] Publisher uses `mark_ready_for_review()` on GitHub API when tier is Suggest and V+QA passed
- [ ] Publisher keeps PR as draft when tier is Observe (existing behavior preserved)
- [ ] Tier labels (`tier:suggest`, `tier:observe`) reconciled on PR by Publisher
- [ ] Unit tests: promotion preconditions, tier gate in Publisher, label reconciliation
- [ ] ruff + mypy clean

### Story 1.12 — EffectiveRolePolicy Enforcement

**References:** `thestudioarc/08-agent-roles.md` (EffectiveRolePolicy drives enforcement at Router, tools, V, QA, Publisher)

**DoD:**
- [ ] `EffectiveRolePolicy` extended with: `tool_allowlist`, `verification_strictness`, `qa_strictness`, `publishing_posture` (draft_only vs ready_after_gate)
- [ ] `compute()` derives these fields from base role + overlays
- [ ] Router consumes policy for mandatory coverage and budget limits
- [ ] Verification Gate consumes policy for check strictness
- [ ] QA Agent consumes policy for validation strictness
- [ ] Publisher consumes policy for draft vs ready-for-review posture
- [ ] Unit tests: policy computation, downstream consumption of all 4 enforcement points
- [ ] ruff + mypy clean

### Story 1.11 — Workflow Integration

**References:** `thestudioarc/15-system-runtime-flow.md` (runtime steps, retry/timeout policy table)

**DoD:**
- [ ] `TheStudioPipelineWorkflow` defined as Temporal workflow with 9 activities
- [ ] Activity functions wrap existing module calls (intake, context, intent, router, assembler, primary agent, verification, QA, publisher)
- [ ] Each activity has timeout and retry config per the policy table
- [ ] Workflow handles loopback: verification failure → retry Primary Agent; QA failure → retry implementation
- [ ] Workflow respects max loopback caps (2 for verification, 2 for QA)
- [ ] Workflow fails closed on exhaustion (no silent skip)
- [ ] Activity inputs/outputs use serializable dataclasses
- [ ] Unit tests: workflow step sequencing, loopback logic, timeout config
- [ ] ruff + mypy clean

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 1.10 | 1.6 QA pass required | Landed Sprint 2 |
| 1.10 | Publisher (0.7) | Landed Sprint 3 (Epic 0) |
| 1.12 | 1.1 Intake roles | Landed Sprint 1 |
| 1.12 | 1.3 Router | Landed Sprint 1 |
| 1.11 | 1.1–1.10, 1.12 | All landed or landing this sprint |

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Temporal workflow definition requires running Temporal server | Medium | Low | Unit test with mocked activities; workflow logic is testable without server |
| EffectiveRolePolicy changes break existing tests | Low | Medium | Extend, don't replace; add new fields with defaults |
| GitHub API `mark_ready_for_review` requires GraphQL | Medium | Low | Implement via GraphQL mutation; httpx supports it |

---

*Plan created by Helm. Awaiting Meridian review.*
