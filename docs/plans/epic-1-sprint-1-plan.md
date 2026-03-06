# Sprint 1 Plan — Epic 1: Full Flow + Experts

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-1-full-flow-experts.md`
**Sprint duration:** 3 weeks
**Team:** 1–2 developers
**Predecessor:** Epic 0 complete (all 9 stories delivered, 42/42 tests passing, full pipe proven)

---

## Sprint Goal

**Objective:** Expert Library stores and serves expert definitions; Router selects expert subsets from intent + risk flags with mandatory coverage enforcement; Intake Agent applies base role + overlays from issue metadata — so that Sprint 2 can build Recruiter, Assembler, and QA Agent against a working routing and expert infrastructure.

**Test:** The sprint goal is met when:
1. Expert Library persists experts with identity, version, class, capability tags, scope, tool policy, trust tier, and lifecycle state; search by class + capability returns correct results; 2 seeded templates exist (Security Review, QA Validation) — 8+ test cases
2. Router selects expert subset from Intent Specification + risk flags + EffectiveRolePolicy; mandatory coverage fires for risk labels (e.g., `risk:auth` → security expert required); consult plan includes rationale and budget; Router invokes Recruiter callback when no eligible expert exists — 10+ test cases
3. Intake Agent selects base role (Developer/Architect/Planner) from issue type and labels; applies overlays from risk labels and issue form fields; produces EffectiveRolePolicy attached to TaskPacket — 8+ test cases
4. All code passes `ruff` lint and `mypy` type check
5. Database migrations run cleanly on existing Epic 0 schema

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. One commit per story minimum. Run `tapps_quick_check` after every file edit.

---

## Retro Actions from Epic 0

| Action | How addressed in this sprint |
|--------|------------------------------|
| Single mega-commit violated small-diffs principle | One commit per story minimum; CI enforces lint per commit |
| mypy errors caught late | Run mypy in the edit loop, not just at the end |
| Docker Compose issues caught late | Validate infra config changes with `tapps_validate_config` |
| Estimate infrastructure as a real story | Migration work is part of story 1.2, not "parallel work" |
| Integration tests against real DB missing | Each story includes integration test cases in DoD |

---

## Capacity and Buffer

- **Commitment:** ~80% of sprint capacity (24 story points of 30 available per 3-week sprint)
- **Buffer:** ~20% for integration issues, Epic 0 bugfixes, and unknowns surfaced during estimation
- **Total planned:** 24 points across 3 stories

---

## Order of Work

### Phase A — Expert Library (week 1)

Story 1.2 has no dependencies on other Epic 1 stories. It unblocks both Router (1.3) and Recruiter (1.4, Sprint 2).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **1.2 Expert Library** | 8 | L | Unblocks 1.3 (Router) and 1.4 (Recruiter). Critical path. No Epic 1 dependencies — only needs Epic 0 Postgres. |

#### Story 1.2 — Expert Library

**Reference:** `thestudioarc/10-expert-library.md`

**Scope:** Postgres schema, async CRUD, search, seeded templates, versioning, lifecycle states.

**Definition of Done:**
- [ ] Migration creates `experts` table: id, version, class (enum: technical, business, partner, qa_validation, security, compliance, service, process_quality), capability_tags (text[]), scope_description, tool_policy (jsonb), trust_tier (enum: shadow, probation, trusted), lifecycle_state (enum: active, deprecated, retired), created_at, updated_at
- [ ] Migration creates `expert_versions` table: expert_id FK, version, definition (jsonb containing scope boundaries, expected outputs, operating procedure, edge cases, failure modes), created_at
- [ ] CRUD: create_expert, get_expert, update_expert_version, deprecate_expert, search_experts(class, capability_tags) — all async SQLAlchemy
- [ ] Search returns experts filtered by class and capability tags, ordered by trust_tier (trusted > probation > shadow), excluding retired
- [ ] Seed script creates 2 vetted templates:
  - **Security Review Expert** — class: security, capability_tags: [auth, secrets, crypto, injection], trust_tier: probation
  - **QA Validation Expert** — class: qa_validation, capability_tags: [intent_validation, acceptance_criteria, defect_classification], trust_tier: probation
- [ ] Versioning: creating a new version of an existing expert increments version, preserves prior versions
- [ ] Deprecation: deprecated experts are discoverable but excluded from Router search results
- [ ] 8+ unit tests covering CRUD, search, versioning, deprecation, seed
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test against Postgres

**Unknowns / risks:**
- Schema may need adjustment when Recruiter (Sprint 2) adds qualification metadata. Mitigation: use jsonb for extensible fields (definition, tool_policy).

---

### Phase B — Intake Agent + Router (weeks 2–3, parallel start)

Stories 1.1 and 1.3 can start in parallel once 1.2 lands (1.3 needs Expert Library; 1.1 has no Epic 1 dependency).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 2 | **1.1 Intake Agent** | 8 | M | No dependency on 1.2. Can start week 2 day 1. Produces EffectiveRolePolicy needed by Router integration tests. |
| 3 | **1.3 Expert Router** | 8 | L | Depends on 1.2 (Expert Library). Critical path for Sprint 2 (Assembler, QA). |

**Parallel work:** If 2 developers, 1.1 and 1.3 run simultaneously in weeks 2–3. If 1 developer, 1.1 first (smaller, no library dependency), then 1.3.

#### Story 1.1 — Intake Agent

**Reference:** `thestudioarc/08-agent-roles.md` (role selection lifecycle, step 1), `thestudioarc/15-system-runtime-flow.md` (Intake Agent responsibilities)

**Scope:** Eligibility contract, base role selection, overlay application, EffectiveRolePolicy computation, rejection handling.

**Definition of Done:**
- [ ] `src/intake/intake_agent.py`: receives GitHub issue event (from webhook handler), evaluates eligibility
- [ ] Eligibility contract documented in module docstring:
  - Eligible: issue has `agent:run` label, repo is registered, repo tier allows automation
  - Reject: missing `agent:run`, unregistered repo, repo paused, issue already has active TaskPacket workflow
- [ ] Base role selection from issue metadata:
  - `type:bug`, `type:feature`, `type:chore` → Developer
  - `type:refactor` → Architect
  - Large ambiguous requests (no type label + large body) → Planner
  - Default (no type label) → Developer
- [ ] Overlay application from labels:
  - `risk:auth` → Security overlay
  - `risk:compliance` → Compliance overlay
  - `risk:billing` → Billing overlay
  - `risk:migration` → Migration overlay
  - `risk:partner-api` → Partner API overlay
  - `risk:infra` → Infra overlay
- [ ] `src/intake/effective_role.py`: EffectiveRolePolicy dataclass — base_role, overlays list, computed fields (mandatory_expert_classes, tool_policy_delta, quality_posture, escalation_triggers)
- [ ] EffectiveRolePolicy attached to TaskPacket (new field or related record)
- [ ] Rejected events produce `IntakeRejection` record: event_id, repo, reason, timestamp — persisted, not silent
- [ ] Refactor: webhook_handler delegates to Intake Agent instead of directly creating TaskPacket
- [ ] 8+ unit tests: eligible issue → role + overlays, rejected issue → rejection record, multiple overlays merge correctly, overlay conflict (more restrictive wins)
- [ ] `ruff` clean, `mypy` clean

**Unknowns / risks:**
- Refactoring webhook_handler changes Epic 0 code. Mitigation: keep the handler thin — it validates and calls Intake Agent. Test both paths.

#### Story 1.3 — Expert Router

**Reference:** `thestudioarc/05-expert-router.md`

**Scope:** Expert selection, mandatory coverage enforcement, consult plan generation, Recruiter callback, budget limits.

**Definition of Done:**
- [ ] `src/routing/router.py`: receives Intent Specification + EffectiveRolePolicy + TaskPacket risk flags
- [ ] Selection algorithm:
  1. Determine required expert classes from EffectiveRolePolicy mandatory_expert_classes + risk flags
  2. Query Expert Library by class + capability tags
  3. Rank candidates by trust_tier (trusted > probation; shadow excluded from auto-selection)
  4. Enforce budget: max experts per consult (configurable, default 3)
- [ ] Mandatory coverage rules:
  - `risk:auth` or Security overlay → security class required
  - `risk:compliance` or Compliance overlay → compliance class required
  - `risk:billing` or Billing overlay → business class required
  - Any risk flag present → qa_validation class required
- [ ] Consult plan output: list of (expert_id, expert_version, class, pattern: parallel|staged), rationale string, budget remaining
- [ ] When no eligible expert exists for a required class: emit `expert_gap_triggered` signal and return a Recruiter callback request (class, capability_tags, reason)
- [ ] `src/routing/consult_plan.py`: ConsultPlan dataclass with validation
- [ ] Signals emitted: `routing_decision_made`, `mandatory_coverage_triggered`, `expert_gap_triggered`
- [ ] 10+ unit tests: selection with multiple candidates, mandatory coverage fires, no-expert → Recruiter callback, budget enforcement, shadow experts excluded, consult plan structure
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test: Router + Expert Library with seeded templates

**Unknowns / risks:**
- Router needs Recruiter for gap-filling, but Recruiter is Sprint 2. Mitigation: Router returns a Recruiter callback request; Sprint 1 tests mock the Recruiter response. Integration with real Recruiter in Sprint 2.

---

## What's Explicitly Out This Sprint

| Item | Why | When |
|------|-----|------|
| 1.4 Recruiter | Depends on 1.2 (Library) + needs Router integration first | Sprint 2 |
| 1.5 Assembler | Depends on Router outputs from 1.3 | Sprint 2 |
| 1.6 QA Agent | Depends on Assembler plan | Sprint 2–3 |
| 1.7 Intent refinement loop | Depends on QA Agent + Assembler | Sprint 3 |
| 1.8 Outcome Ingestor stub | Can be built after QA signals exist | Sprint 3 |
| 1.9 Full evidence comment | Needs expert + QA data | Sprint 3 |
| 1.10 Suggest tier promotion | Needs QA Agent operational | Sprint 3–4 |
| 1.11 Workflow integration | Needs all components | Sprint 4 |
| 1.12 EffectiveRolePolicy enforcement | Partially in 1.1 (computation); enforcement across all components is Sprint 4 |

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 1.2 Expert Library | Epic 0 Postgres + migrations | Complete |
| 1.1 Intake Agent | Epic 0 webhook_handler, TaskPacket | Complete |
| 1.3 Expert Router | 1.2 Expert Library, Epic 0 Intent Spec | 1.2 must land first |

**Cross-dependency risk:** 1.3 is blocked by 1.2. If 1.2 slips, 1.3 starts late. Mitigation: 1.2 is week 1 priority; if it slips into week 2, 1.3 can mock the library interface and integrate later.

---

## Timeline

### 2 developers

| Week | Dev 1 | Dev 2 |
|------|-------|-------|
| 1 | 1.2 Expert Library | Epic 0 bugfixes / Sprint 2 prep (read Recruiter + Assembler docs) |
| 2 | 1.3 Expert Router | 1.1 Intake Agent |
| 3 | 1.3 Router (integration tests) | 1.1 Intake (integration + refactor webhook_handler) |

### 1 developer

| Week | Work |
|------|------|
| 1 | 1.2 Expert Library |
| 2 | 1.1 Intake Agent |
| 3 | 1.3 Expert Router |

---

## Sprint Definition of Done

The sprint is done when:
1. All 3 stories pass their Definition of Done checklists
2. All tests pass (unit + integration)
3. `ruff` and `mypy` clean across all new and modified files
4. Migrations run cleanly on Epic 0 schema
5. `tapps_validate_changed` passes on all modified files
6. One commit per story (minimum), each with passing CI

---

*Sprint 1 plan created by Helm. Awaiting Meridian review before commit.*
