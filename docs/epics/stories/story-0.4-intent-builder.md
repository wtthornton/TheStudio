# Story 0.4 -- Intent Builder: produce Intent Specification

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** to produce an Intent Specification (goal, constraints, acceptance criteria, non-goals) from the enriched TaskPacket, **so that** the Primary Agent has a clear, versioned definition of correctness to implement against

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 2 (weeks 4-6)
**Depends on:** Story 0.3 (Context Manager)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Intent Builder defines "what correctness means" for a given task. It reads the enriched TaskPacket (scope, risk flags, complexity index) and the original GitHub issue, then produces an Intent Specification:

- **Goal:** One clear statement of what the implementation must achieve
- **Constraints:** Technical or process boundaries (e.g., "must not break existing API", "must include tests")
- **Acceptance criteria:** Testable conditions that define "done" (derived from issue content + risk flags)
- **Non-goals:** What the implementation must NOT do (derived from scope boundaries)

The Intent Specification is versioned (v1, v2, ...) because it may be refined after verification failure loopbacks. In Phase 0, no expert consultation occurs — intent is built purely from issue content and context enrichment.

After intent is built, TaskPacket status moves from "enriched" to "intent_built".

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define Intent Specification model (`src/intent/intent_spec.py`)
  - Fields: id, taskpacket_id, version, goal, constraints (list), acceptance_criteria (list), non_goals (list), created_at
  - Pydantic model for validation
  - Persistence (same DB as TaskPacket)
- [ ] Implement Intent Builder (`src/intent/intent_builder.py`)
  - Read enriched TaskPacket + GitHub issue content
  - Extract goal from issue title + first paragraph
  - Derive constraints from risk flags (e.g., risk_security -> "must not expose credentials")
  - Derive acceptance criteria from issue body checkboxes or requirements
  - Derive non-goals from explicit "out of scope" mentions or complexity boundaries
  - Create Intent Specification v1
- [ ] Implement intent versioning (`src/intent/intent_spec.py`)
  - Version increments on refinement (for loopback scenarios)
  - Previous versions preserved for provenance
- [ ] Update TaskPacket with intent reference (`src/models/taskpacket.py`)
  - Add `intent_spec_id` and `intent_version` fields
  - Status transition: enriched -> intent_built
- [ ] Add OpenTelemetry span (`src/intent/intent_builder.py`)
  - Span name: `intent.build`
  - Attributes: correlation_id, intent_version, constraint_count, criteria_count
- [ ] Write tests (`tests/test_intent_builder.py`)
  - Unit tests for goal extraction
  - Unit tests for constraint derivation from risk flags
  - Unit tests for acceptance criteria parsing
  - Integration test for full intent build flow

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Intent Specification is created with goal, constraints, acceptance_criteria, and non_goals
- [ ] Goal is derived from the issue title and body (not empty, not generic)
- [ ] Constraints include at least one entry when risk flags are present
- [ ] Acceptance criteria include at least one testable condition
- [ ] Intent is versioned (starts at v1)
- [ ] Intent is persisted and linked to TaskPacket via intent_spec_id
- [ ] TaskPacket status transitions from "enriched" to "intent_built"
- [ ] Previous intent versions are preserved when a new version is created

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for goal extraction (clear title, vague title, title-only issue)
- [ ] Unit tests for constraint derivation (each risk flag maps to constraint)
- [ ] Unit tests for acceptance criteria parsing (checkboxes, requirements list, none found)
- [ ] Integration test: enriched TaskPacket -> Intent Specification v1
- [ ] Integration test: intent versioning (v1 -> v2 on refinement)
- [ ] Code passes ruff lint and mypy type check

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Clear issue | Issue with title + checklist in body | Goal from title, criteria from checklist |
| 2 | Vague issue | Issue with "improve performance" | Goal extracted, generic constraint added |
| 3 | Security risk flags | Enriched with risk_security=true | Constraint: "must not expose credentials" |
| 4 | Multiple risk flags | risk_security + risk_breaking | Multiple constraints derived |
| 5 | No risk flags | Simple fix, no risks | Minimal constraints (standard: include tests) |
| 6 | Version increment | Refinement after loopback | Version goes from 1 to 2, v1 preserved |
| 7 | Status transition | TaskPacket status=enriched | After build: status=intent_built |
| 8 | Non-goals extraction | Issue mentions "out of scope: mobile" | non_goals includes "mobile" |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Intent is the definition of correctness.** This is a core SOUL.md principle. The Intent Specification must be specific enough that Verification and QA can pass/fail against it.
- **No expert consultation in Phase 0.** Intent is built from issue + context only. Phase 1 adds expert input via Router/Assembler.
- **Goal extraction** uses simple NLP: issue title as primary goal, first paragraph of body as elaboration. Not ML-based.
- **Constraint derivation** is rule-based: each risk flag maps to one or more constraints via a config dict.
- **Architecture references:**
  - Intent Layer: `thestudioarc/11-intent-layer.md`
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 3)
  - SOUL.md: "Intent is the definition of correctness"

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/intent/__init__.py` | Create | Package init |
| `src/intent/intent_spec.py` | Create | Intent Specification model + persistence |
| `src/intent/intent_builder.py` | Create | Build intent from enriched TaskPacket |
| `src/models/taskpacket.py` | Modify | Add intent_spec_id, intent_version fields |
| `tests/test_intent_builder.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.3 (Context Manager):** Intent Builder reads enriched TaskPacket (scope, risk flags)
- **Blocked by:** Must complete before Story 0.5 (Primary Agent) can implement from intent

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Depends only on Context Manager output (Story 0.3)
- [x] **N**egotiable -- Goal extraction heuristics, constraint mapping rules are flexible
- [x] **V**aluable -- Without intent, the Primary Agent has no definition of correctness
- [x] **E**stimable -- 8 points, structured extraction + versioning
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 8 test cases with deterministic rule-based logic

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
