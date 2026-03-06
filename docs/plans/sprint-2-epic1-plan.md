# Sprint 2 Plan — Epic 1: Full Flow + Experts

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** `docs/epics/epic-1-full-flow-experts.md`
**Sprint duration:** 2 weeks
**Team:** 1 developer
**Predecessor:** Sprint 1 / Epic 1 (complete — Expert Library 1.2, Intake Agent 1.1, Expert Router 1.3; 208 tests passing, ruff/mypy clean)

---

## Sprint Goal

**Objective:** Expert Recruiter creates experts from templates with qualification and trust tiers; Assembler merges expert outputs into provenance-tracked plans with conflict resolution; QA Agent validates against Intent Specification with defect taxonomy and signal emission — so that the system has a complete expert consultation → assembly → QA validation pipeline.

**Test:** The sprint goal is met when:
1. Expert Recruiter creates experts from templates, runs qualification harness, assigns shadow/probation tier, de-duplicates against library (8 test cases)
2. Assembler merges expert outputs with intent-as-tie-breaker conflict resolution, produces plan with provenance minimum record and QA handoff mapping (10 test cases)
3. QA Agent validates against acceptance criteria, classifies defects by 8-category taxonomy + S0-S3 severity, emits qa_passed/qa_defect/qa_rework signals to JetStream, blocks qa_passed on intent_gap, triggers loopback (10 test cases)
4. All code passes `ruff` lint and `mypy` type check (run in edit loop per retro A1)
5. One commit per story (per retro A4)

**Constraint:** No story is "done" unless its Definition of Done is fully satisfied. No partial credit. Mypy errors must be fixed during implementation, not after.

---

## Order of Work

### Phase A — Recruiter + Assembler (parallel-ready, week 1)

Stories 1.4 and 1.5 can start simultaneously:
- 1.4 depends on 1.2 (Expert Library) — landed Sprint 1
- 1.5 depends on 1.3 (Router outputs) — landed Sprint 1

| Order | Story | Size | Rationale |
|-------|-------|------|-----------|
| 1 | **1.4 Expert Recruiter** | L | Depends on 1.2 only. Template catalog + qualification harness + de-duplication. |
| 2 | **1.5 Assembler** | L | Depends on 1.3 Router outputs. Merge + conflict resolution + provenance + QA handoff. |

### Phase B — QA Agent (week 2)

| Order | Story | Size | Rationale |
|-------|-------|------|-----------|
| 3 | **1.6 QA Agent** | L | Depends on 1.5 (Assembler plan for QA handoff mapping) + Epic 0 Verification (signal patterns). Reuses JetStream signal emission from verification/signals.py. |

### Timeline (1 developer)

```
Week 1:  [1.4 Recruiter >>>>] [1.5 Assembler >>>>>>>>]
Week 2:  [1.6 QA Agent >>>>>>>>>>] [validation + buffer]
```

---

## Dependencies

| Story | Depends on | Status |
|-------|-----------|--------|
| 1.4 Expert Recruiter | 1.2 Expert Library (CRUD, search, seed templates) | Landed Sprint 1 |
| 1.5 Assembler | 1.3 Expert Router (ConsultPlan, ExpertSelection) | Landed Sprint 1 |
| 1.5 Assembler | Intent Specification (Epic 0, src/intent/) | Landed |
| 1.6 QA Agent | 1.5 Assembler (plan + QA handoff mapping) | Sprint 2 |
| 1.6 QA Agent | Epic 0 Verification (JetStream signal pattern) | Landed |
| 1.6 QA Agent | Intent Specification (acceptance criteria) | Landed |

---

## Story Definitions of Done

### 1.4 Expert Recruiter

- [ ] `src/recruiting/recruiter.py` — Recruiter module with template selection, de-duplication, qualification, trust tier assignment
- [ ] Template catalog with at least 2 templates (Security Review, QA Validation)
- [ ] Qualification harness: validates output structure, scope compliance, tool policy compliance
- [ ] De-duplication: prefers version update over new identity
- [ ] New experts start in shadow or probation — never trusted
- [ ] Signals: expert_created, expert_version_created events
- [ ] Tests: 8 unit tests covering create-from-template, qualification pass/fail, de-duplication, trust tier assignment
- [ ] ruff clean, mypy clean
- [ ] Architecture reference: `thestudioarc/04-expert-recruiter.md`

### 1.5 Assembler

- [ ] `src/assembler/assembler.py` — Assembler module
- [ ] Merges expert outputs into single plan with steps + checkpoints
- [ ] Conflict resolution: intent constraints as tie-breaker
- [ ] Intent refinement trigger when intent is ambiguous
- [ ] Provenance minimum record: TaskPacket id, correlation_id, intent version, experts consulted, plan id
- [ ] QA handoff mapping: acceptance criteria → validations
- [ ] Risk list with mitigations
- [ ] Tests: 10 unit tests covering merge, conflict resolution, provenance, QA handoff, intent refinement trigger
- [ ] ruff clean, mypy clean
- [ ] Architecture reference: `thestudioarc/07-assembler.md`

### 1.6 QA Agent

- [ ] `src/qa/qa_agent.py` — QA Agent module
- [ ] Validates against Intent Specification acceptance criteria
- [ ] Defect taxonomy: intent_gap, implementation_bug, regression, security, performance, compliance, partner_mismatch, operability
- [ ] Severity: S0 critical, S1 high, S2 medium, S3 low
- [ ] intent_gap blocks qa_passed — no exception
- [ ] Emits qa_passed, qa_defect, qa_rework signals to JetStream
- [ ] Loopback to Primary Agent on failure with defect list + intent mapping
- [ ] Intent refinement request when acceptance criteria are ambiguous
- [ ] Tests: 10 unit tests covering pass/fail, defect classification, intent_gap blocking, signal emission, loopback, refinement request
- [ ] ruff clean, mypy clean
- [ ] Architecture reference: `thestudioarc/14-qa-quality-layer.md`

---

## Retro Actions Applied

| Action | From | How applied |
|--------|------|-------------|
| A1 mypy in edit loop | Sprint 1 retro | Run mypy after each file edit. Fix type errors immediately. |
| A4 one commit per story | Sprint 1 retro | Commit after each story is test-passing and lint-clean. |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Assembler conflict resolution rules under-specified | High | Explicit test cases with conflicting expert outputs; intent is the tie-breaker |
| QA defect taxonomy not enforced | High | Pydantic model validation on QADefect; category and severity required fields |
| JetStream QA signal subject naming | Low | Follow existing verification/signals.py pattern; same stream structure |

---

*Plan created by Helm. Pending Meridian review.*
