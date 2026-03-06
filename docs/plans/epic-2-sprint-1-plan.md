# Sprint 1 Plan — Epic 2: Learning + Multi-Repo

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-2-learning-multi-repo.md`
**Sprint duration:** 3 weeks
**Team:** 1–2 developers
**Predecessor:** Epic 1 complete (all 12 stories delivered, 355 tests passing, 9-step pipeline wired)

---

## Sprint Goal

**Objective:** Complexity Index v1 is defined and computed on TaskPackets; Outcome Ingestor normalizes signals by complexity and attributes outcomes to experts via provenance; Reputation Engine stores weights, computes confidence, and exposes them to Router; Router consumes reputation weights in expert selection — so that Sprint 2 can build quarantine/replay operations and Admin UI against a working learning loop.

**Test:** The sprint goal is met when:
1. Complexity Index v1 schema documents dimensions (scope breadth, risk flags, dependency count, lines changed, expert count); Context Manager computes index and stores on TaskPacket — 6+ test cases
2. Outcome Ingestor normalizes verification + QA signals by Complexity Index; attributes outcomes to experts using provenance links; produces indicators for Reputation Engine — 10+ test cases
3. Reputation Engine stores weights by expert id + context key; computes confidence from sample size and provenance completeness; exposes weights via query API — 8+ test cases
4. Router queries Reputation Engine for weights; expert selection includes reputation weight and confidence in rationale; high-confidence experts preferred within required classes — 8+ test cases
5. All code passes `ruff` lint and `mypy` type check
6. Database migrations run cleanly on existing Epic 1 schema

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. One commit per story minimum. Run `tapps_quick_check` after every file edit. Integration tests against real PostgreSQL for all data-layer stories.

---

## Retro Actions from Epic 1

| Action | How addressed in this sprint |
|--------|------------------------------|
| mypy errors caught late (Epic 0) | Run mypy in the edit loop, not just at the end |
| Integration tests against real DB missing | Each story includes integration test cases in DoD |
| Estimate infra as a real story | No new infrastructure in Sprint 1; Reputation Engine tables are part of story 2.5 |
| One commit per story | Enforced in constraint; CI validates each commit |

---

## Capacity and Buffer

- **Commitment:** ~80% of sprint capacity (26 story points of 32 available per 3-week sprint)
- **Buffer:** ~20% for integration issues, Epic 1 bugfixes, and unknowns surfaced during estimation
- **Total planned:** 26 points across 4 stories

---

## Order of Work

### Phase A — Foundation (week 1)

Story 2.1 has no dependencies on other Epic 2 stories. It unblocks Outcome Ingestor (2.2) which needs Complexity Index for normalization.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **2.1 Complexity Index v1** | 5 | M | Unblocks 2.2 (Ingestor normalization). No Epic 2 dependencies — only needs Epic 1 Context Manager and TaskPacket. |

#### Story 2.1 — Complexity Index v1

**Reference:** `thestudioarc/15-system-runtime-flow.md` (Complexity Index), `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 117–118

**Scope:** Define dimensions, formula/rubric, schema, compute in Context Manager, store on TaskPacket.

**Definition of Done:**
- [ ] `docs/architecture/complexity-index-v1.md`: Documented dimensions and formula:
  - **scope_breadth:** number of files likely modified (1=single file, 2=few files, 3=cross-module)
  - **risk_flags:** count of risk labels on the issue (0, 1, 2+)
  - **dependency_count:** number of external dependencies touched (from Context Manager analysis)
  - **lines_estimate:** estimated lines changed (small <50, medium 50–200, large >200)
  - **expert_coverage:** count of expert classes required by EffectiveRolePolicy
  - **Formula:** `complexity_score = scope_breadth * 2 + risk_flags * 3 + dependency_count + (lines_estimate / 50) + expert_coverage`
  - **Bands:** low (0–5), medium (6–12), high (13+)
- [ ] `src/context/complexity.py`: `ComplexityIndex` dataclass with dimensions, score, band
- [ ] `src/context/complexity.py`: `compute_complexity_index(task_packet, context_data, effective_role_policy) -> ComplexityIndex`
- [ ] Migration adds `complexity_index` column (jsonb) to `task_packets` table
- [ ] Context Manager calls `compute_complexity_index` and stores result on TaskPacket
- [ ] 6+ unit tests: compute with varying dimensions, band classification, edge cases (zero flags, max complexity)
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test: full Context Manager flow produces TaskPacket with complexity_index

**Unknowns / risks:**
- Formula may need tuning after observing real distributions. Mitigation: store all dimensions in jsonb so formula can be recomputed without migration.

---

### Phase B — Outcome Ingestor Full (weeks 1–2)

Story 2.2 depends on 2.1 for Complexity Index normalization. It transforms the Epic 1 stub into a full ingestor.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 2 | **2.2 Outcome Ingestor — normalization + attribution** | 8 | L | Core learning loop. Depends on 2.1. Produces indicators for Reputation Engine. |

#### Story 2.2 — Outcome Ingestor (normalization + attribution)

**Reference:** `thestudioarc/12-outcome-ingestor.md`

**Scope:** Extend Epic 1 stub to normalize by Complexity Index, attribute outcomes to experts via provenance, produce indicators for Reputation Engine.

**Definition of Done:**
- [ ] Refactor `src/outcome/ingestor.py` (Epic 1 stub) → full implementation
- [ ] Normalization:
  - Query TaskPacket complexity_index for each consumed signal
  - Adjust raw outcomes by complexity band: high complexity failures count less against experts, high complexity successes count more for experts
  - Normalization formula documented in module docstring
- [ ] Attribution:
  - Query provenance links from Assembler for each TaskPacket
  - Map verification/QA outcomes to contributing experts using provenance
  - Apply attribution rules from `06-reputation-engine.md`:
    - `intent_gap` defects → do NOT penalize experts (intent quality issue)
    - `implementation_bug`, `regression` → may penalize Primary Agent or consulted experts per provenance
    - Missing coverage → routing/policy failure, not expert failure
- [ ] Indicator production:
  - For each completed task, emit `ReputationIndicator` to Reputation Engine:
    - `expert_id`, `expert_version`, `context_key` (repo + risk class + complexity band)
    - `outcome_type`: success, failure, loopback
    - `defect_category`, `defect_severity` (if applicable)
    - `normalized_weight`: complexity-adjusted impact
- [ ] Signals consumed: `verification_passed`, `verification_failed`, `qa_passed`, `qa_defect`, `qa_rework`
- [ ] Signals emitted: `reputation_indicator_produced`
- [ ] Idempotent: duplicate signals do not produce duplicate indicators
- [ ] 10+ unit tests: normalization by complexity, attribution by provenance, intent_gap exclusion, missing coverage exclusion, indicator structure, idempotency
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test: end-to-end signal → indicator flow with real JetStream + Postgres

**Unknowns / risks:**
- Provenance links may be incomplete for some TaskPackets (Epic 1 edge cases). Mitigation: treat missing provenance as "low confidence" and emit indicator with reduced weight.

---

### Phase C — Reputation Engine + Router (weeks 2–3)

Stories 2.5 and 2.7 form the core Reputation Engine and Router integration. 2.5 can start once 2.2 indicator structure is defined. 2.7 depends on 2.5.

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 3 | **2.5 Reputation Engine — core** | 8 | L | Stores weights, computes confidence. Depends on 2.2 indicator format. Unblocks 2.7 (Router). |
| 4 | **2.7 Router — reputation-aware selection** | 5 | M | Depends on 2.5. Closes the learning loop. |

#### Story 2.5 — Reputation Engine (core)

**Reference:** `thestudioarc/06-reputation-engine.md`

**Scope:** Weight storage, confidence computation, query API for Router.

**Definition of Done:**
- [ ] `src/reputation/engine.py`: ReputationEngine service class
- [ ] Migration creates `expert_reputation` table:
  - `expert_id`, `context_key` (composite: repo, risk_class, complexity_band), `weight` (float), `confidence` (float), `sample_count` (int), `last_updated_at`
  - Composite primary key: (expert_id, context_key)
- [ ] Weight update logic:
  - Consume `ReputationIndicator` from Outcome Ingestor
  - Update weight using moving average: `new_weight = (1 - learning_rate) * old_weight + learning_rate * indicator.normalized_weight`
  - Learning rate configurable (default 0.1)
- [ ] Confidence computation:
  - `confidence = min(1.0, sample_count / confidence_threshold)` — low sample size = low confidence
  - `confidence_threshold` configurable (default 10 samples)
  - Provenance completeness factor: reduce confidence if indicator has `low_provenance` flag
- [ ] Query API: `get_expert_weights(expert_ids: list, context_key: str) -> dict[expert_id, (weight, confidence)]`
- [ ] Signals emitted: `weight_updated`, `confidence_updated`
- [ ] 8+ unit tests: weight update, confidence computation, low sample size, provenance penalty, query API
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test: indicator → weight update → query returns updated weight

**Unknowns / risks:**
- Learning rate and confidence threshold may need tuning. Mitigation: make configurable; document defaults in `docs/architecture/complexity-index-v1.md`.

#### Story 2.7 — Router (reputation-aware selection)

**Reference:** `thestudioarc/05-expert-router.md`, `thestudioarc/06-reputation-engine.md`

**Scope:** Router queries Reputation Engine for weights and factors them into expert selection.

**Definition of Done:**
- [ ] Refactor `src/routing/router.py` to query Reputation Engine after Expert Library search
- [ ] Selection algorithm update:
  1. Query Expert Library for candidates (unchanged)
  2. Query Reputation Engine for weights and confidence for candidates
  3. Score candidates: `selection_score = trust_tier_score * (1 + reputation_weight * confidence)`
  4. Rank by selection_score; prefer high-confidence experts within budget
- [ ] Mandatory coverage unchanged: reputation adjusts selection within required classes, not across them
- [ ] Consult plan output update:
  - Include `reputation_weight` and `reputation_confidence` for each selected expert
  - Rationale string includes "selected based on reputation weight X (confidence Y)"
- [ ] Low-confidence handling: experts with confidence < 0.3 are flagged as "probationary selection" in rationale
- [ ] Signals emitted: `routing_decision_made` now includes reputation fields
- [ ] 8+ unit tests: selection with reputation weights, high-confidence preference, low-confidence flag, mandatory coverage unaffected, rationale includes reputation
- [ ] `ruff` clean, `mypy` clean
- [ ] Integration test: full routing flow with Reputation Engine returning weights

**Unknowns / risks:**
- Reputation Engine may return no weights for new experts (no history). Mitigation: treat missing weight as neutral (0.5) with confidence 0.

---

## What's Explicitly Out This Sprint

| Item | Why | When |
|------|-----|------|
| 2.3 Quarantine + dead-letter + replay | Core ingestor must work first | Sprint 2 |
| 2.4 Reopen event handling | Secondary ingestor feature | Sprint 2 |
| 2.6 Trust tier transitions + decay + drift | Reputation core must work first | Sprint 2 |
| 2.8 Compliance Checker | Unrelated to learning loop | Sprint 2–3 |
| 2.9 Execute tier promotion | Depends on Compliance Checker | Sprint 3 |
| 2.10–2.15 Admin UI | Learning loop must close first | Sprint 3–4 |
| 2.16–2.17 Multi-repo | Admin UI + Compliance Checker needed | Sprint 4 |

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 2.1 Complexity Index | Epic 1 Context Manager, TaskPacket | Complete |
| 2.2 Outcome Ingestor | 2.1 Complexity Index, Epic 1 Ingestor stub | 2.1 must land first |
| 2.5 Reputation Engine | 2.2 Indicator format | 2.2 indicator dataclass must be defined |
| 2.7 Router | 2.5 Reputation Engine query API | 2.5 must land first |

**Cross-dependency risk:** 2.7 depends on 2.5, which depends on 2.2. Linear chain. Mitigation: 2.5 can mock indicators to start early; integration test validates real flow.

---

## Timeline

### 2 developers

| Week | Dev 1 | Dev 2 |
|------|-------|-------|
| 1 | 2.1 Complexity Index | 2.2 Outcome Ingestor (start, use 2.1 interface) |
| 2 | 2.5 Reputation Engine (start) | 2.2 Outcome Ingestor (complete) |
| 3 | 2.5 Reputation Engine (complete) | 2.7 Router reputation integration |

### 1 developer

| Week | Work |
|------|------|
| 1 | 2.1 Complexity Index + start 2.2 Outcome Ingestor |
| 2 | 2.2 Outcome Ingestor (complete) + start 2.5 Reputation Engine |
| 3 | 2.5 Reputation Engine (complete) + 2.7 Router |

---

## Sprint Definition of Done

The sprint is done when:
1. All 4 stories pass their Definition of Done checklists
2. All tests pass (unit + integration)
3. `ruff` and `mypy` clean across all new and modified files
4. Migrations run cleanly on Epic 1 schema
5. `tapps_validate_changed` passes on all modified files
6. One commit per story (minimum), each with passing CI
7. Learning loop verified: a completed task produces reputation weight update; Router uses the weight for next selection

---

*Sprint 1 plan created by Helm. Awaiting Meridian review before commit.*
