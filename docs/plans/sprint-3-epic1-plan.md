# Sprint 3 Plan — Epic 1: Full Flow + Experts

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-1-full-flow-experts.md`
**Sprint duration:** 2 weeks
**Team:** 1 developer
**Predecessor:** Sprint 2 Epic 1 (complete — Stories 1.1–1.6 landed, 251 tests passing, ruff/mypy clean)

---

## Sprint Goal

**Objective:** Intent refinement loop enables versioned re-specification from QA/Assembler triggers with a cap of 2 versions per workflow; Outcome Ingestor stub consumes verification + QA signals and persists them with quarantine for bad data; Evidence Comment includes the full-format fields from `15-system-runtime-flow.md` — so that the system produces traceable, auditable PRs with expert coverage, QA results, and loopback history.

**Test:** The sprint goal is met when:
1. Intent refinement produces a new version from QA or Assembler triggers; prior versions preserved; cap at 2 versions per workflow; refinement triggers appear in provenance (6 test cases)
2. Outcome Ingestor consumes verification and QA signal payloads, correlates to TaskPacket by correlation_id, persists for analytics, quarantines signals with missing correlation_id or unknown TaskPacket (8 test cases)
3. Evidence Comment includes all required fields: TaskPacket id, correlation id, intent version + summary, acceptance criteria checklist, what changed, verification summary, QA result, expert coverage summary, loopback summary (6 test cases)
4. All code passes `ruff` lint and `mypy` type check
5. Each story committed individually

**Constraint:** No story is "done" unless its Definition of Done checklist is fully satisfied. No partial credit. Mypy runs in the edit loop (retro action A1).

---

## Order of Work

### Phase A — Sequential (days 1–6)

Stories 1.7 and 1.8 have no dependency on each other. Both depend on Sprint 2 deliverables (already landed).

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 1 | **1.7 Intent Refinement Loop** | 5 | M | Depends on 1.5 Assembler `IntentRefinementRequest` + 1.6 QA `IntentRefinementRequest`. Extends existing `intent_builder.py` and `intent_crud.py`. |
| 2 | **1.8 Outcome Ingestor Stub** | 5 | M | Depends on verification + QA signals (both landed). New module `src/outcome/`. JetStream consumer pattern mirrors existing `signals.py` publishers. |

### Phase B — Evidence Comment (days 7–8)

| Order | Story | Points | Size | Rationale |
|-------|-------|--------|------|-----------|
| 3 | **1.9 Evidence Comment Full Format** | 5 | M | Depends on 1.5 Assembler provenance + 1.6 QA result. Extends existing `evidence_comment.py`. |

### Timeline

```
Days 1-3:  [1.7 Intent Refinement Loop]
Days 4-6:  [1.8 Outcome Ingestor Stub]
Days 7-8:  [1.9 Evidence Comment Full Format]
Days 9-10: [buffer / integration / retro]
```

---

## Story Definitions of Done

### 1.7 Intent Refinement Loop

**Reference:** `thestudioarc/11-intent-layer.md` — Refinement Loop section

**DoD:**
- [ ] `refine_intent()` function accepts refinement trigger (QA or Assembler) and produces a new IntentSpec version
- [ ] Prior intent versions preserved in `intent_spec` table (existing `get_all_versions` CRUD)
- [ ] Version cap: max 2 versions per workflow (version 1 = original, version 2 = refinement). Exceeding cap raises `RefinementCapExceeded`
- [ ] Refinement source tracked: trigger type (qa/assembler), questions, triggering defects/conflicts
- [ ] TaskPacket `intent_version` updated to new version after refinement
- [ ] OTel span `intent.refine` with correlation_id and intent version attributes
- [ ] 6 unit tests: refine from QA trigger, refine from Assembler trigger, prior version preserved, cap at 2, provenance includes refinement source, TaskPacket updated
- [ ] `ruff` clean, `mypy` clean

### 1.8 Outcome Ingestor Stub

**Reference:** `thestudioarc/12-outcome-ingestor.md`

**DoD:**
- [ ] `src/outcome/` module with `ingestor.py`, `models.py`, `__init__.py`
- [ ] Pydantic model `OutcomeSignal`: event type, taskpacket_id, correlation_id, timestamp, payload (JSON)
- [ ] Pydantic model `QuarantinedSignal`: raw payload, quarantine reason, timestamp
- [ ] `ingest_signal()` validates correlation_id present, correlates to TaskPacket, persists signal
- [ ] Quarantine path: missing correlation_id -> quarantine; unknown TaskPacket -> quarantine
- [ ] Consumed signal types: `verification_passed`, `verification_failed`, `verification_exhausted`, `qa_passed`, `qa_defect`, `qa_rework`
- [ ] Signals persisted in-memory list (no DB table — stub for Phase 2)
- [ ] OTel span `outcome.ingest` with correlation_id attribute
- [ ] 8 unit tests: ingest verification_passed, ingest qa_passed, correlate by correlation_id, quarantine missing correlation_id, quarantine unknown TaskPacket, quarantine invalid event, persist for analytics, idempotent handling
- [ ] `ruff` clean, `mypy` clean

### 1.9 Evidence Comment — Full Format

**Reference:** `thestudioarc/15-system-runtime-flow.md` — "Standard Agent Evidence Comment"

**DoD:**
- [ ] `format_full_evidence_comment()` produces markdown with all required fields
- [ ] Required fields: TaskPacket id, correlation_id, intent version + one-paragraph summary, acceptance criteria checklist (checkbox format), what changed, verification result summary, QA result (passed/defects), expert coverage summary (classes consulted, policy triggers), loopback summary (verification loop count + categories, QA loop count + defect categories)
- [ ] Existing `format_evidence_comment()` preserved for backward compatibility
- [ ] Evidence comment marker (`<!-- thestudio-evidence -->`) retained for idempotent updates
- [ ] 6 unit tests: full format includes all fields, QA passed format, QA defect format, expert coverage section, loopback summary section, marker present
- [ ] `ruff` clean, `mypy` clean

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 1.7 Intent Refinement | 1.5 Assembler `IntentRefinementRequest`, 1.6 QA `IntentRefinementRequest` | Landed Sprint 2 |
| 1.7 Intent Refinement | `intent_crud.py` (create_intent, get_all_versions, get_latest_for_taskpacket) | Landed Epic 0 |
| 1.8 Outcome Ingestor | Verification signals format (`verification/signals.py`) | Landed Epic 0 |
| 1.8 Outcome Ingestor | QA signals format (`qa/signals.py`) | Landed Sprint 2 |
| 1.9 Evidence Comment | 1.5 Assembler `ProvenanceRecord`, `AssemblyPlan` | Landed Sprint 2 |
| 1.9 Evidence Comment | 1.6 QA `QAResult` | Landed Sprint 2 |
| 1.9 Evidence Comment | Epic 0 Publisher `evidence_comment.py` | Landed Epic 0 |

**No new external dependencies.** All infrastructure provisioned previously.

---

## Estimation Reasoning

### 1.7 Intent Refinement Loop — 5 points (M)

- **Why this size:** Extends existing intent_builder and intent_crud. Core logic: validate cap, create new version with refinement metadata, update TaskPacket. No new DB table (reuses intent_spec). No new infrastructure.
- **Risk:** Low. All building blocks exist.

### 1.8 Outcome Ingestor Stub — 5 points (M)

- **Why this size:** New module but stub-level complexity. In-memory persistence (no DB migration). Signal parsing follows existing payload format. Quarantine logic is straightforward validation.
- **Risk:** Low. No JetStream consumer wiring (stub receives parsed payloads). Real consumer is Phase 2.

### 1.9 Evidence Comment Full Format — 5 points (M)

- **Why this size:** Extends existing template with 5 new sections. Each section is a simple markdown formatter. No new models — consumes existing QAResult, ProvenanceRecord, AssemblyPlan.
- **Risk:** Low. Pure formatting.

---

## Capacity and Buffer

| Item | Points |
|------|--------|
| Sprint 3 committed stories | 15 |
| Capacity (1 dev x 2 weeks) | ~20 points |
| Buffer | ~5 points (25%) |

---

## Retro Actions Applied

From Sprint 1 retro (docs/LESSONS_LEARNED.md):
- **A1: mypy in edit loop** — run mypy after each file edit, not just at the end
- **A4: one commit per story** — each story gets its own commit
- **No partial credit** — all DoD items must be satisfied before marking done

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Intent version cap edge case with concurrent refinements | Low | Medium | Single-threaded workflow — no concurrency within a TaskPacket |
| Outcome Ingestor scope creep toward real consumer | Medium | Low | Explicitly stub: in-memory store, no JetStream consumer. Real consumer is Phase 2. |
| Evidence comment format diverges from spec | Low | Low | Test against 15-system-runtime-flow.md spec; review output in tests |

---

*Plan created by Helm. Pending Meridian review before commit.*
