# Epic 6: Phase 3 Completion — Service Context Packs, Expert Expansion & Success Enforcement

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Phase:** 3 (Scale + Quality Bar)
**Depends on:** Epic 5 (Eval Suite & Metrics APIs — complete)

---

## 1. Title

Phase 3 Completion: Service Context Packs, Expert Class Expansion, and Single-Pass Success Enforcement

---

## 2. Narrative

TheStudio's Phase 3 goal is a stable quality bar: five or more expert classes in use, service context packs enriching task packets, and single-pass success enforced at >=60%.

After Epic 5 delivered the eval suite, metrics APIs, and admin dashboards, three deliverables remain:

1. **Service Context Packs are stubs.** The `get_context_packs()` function returns an empty list. No packs exist. The Context Manager calls it but gets nothing. Without packs, task packets lack service-specific knowledge — experts make decisions without domain context.

2. **Only 2 of 8 expert classes are seeded.** The enum defines 8 classes but only `security` and `qa_validation` have concrete experts. Phase 3 requires at least 5 classes in active use.

3. **Single-pass success rate is measured but not enforced.** The metrics API computes the rate, but there is no gate, no threshold check, no alerting when it drops below 60%.

This epic closes these gaps to complete Phase 3.

---

## 3. References

- Aggressive Roadmap Phase 3: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` (lines 138-163)
- Expert Taxonomy: `thestudioarc/02-expert-taxonomy.md`
- Context Manager: `src/context/context_manager.py`
- Service Context Pack stub: `src/context/service_context_pack.py`
- Expert seed: `src/experts/seed.py`
- ExpertClass enum: `src/experts/expert.py`
- Metrics service: `src/admin/metrics.py`
- Outcome signals: `src/outcome/ingestor.py`
- Epic 5 retro: `docs/epics/epic-5-sprint-1-retro.md`

---

## 4. Acceptance Criteria

### Service Context Packs
- AC-1: At least 2 Service Context Packs defined with real content (API patterns, conventions, constraints for distinct services/repos).
- AC-2: `get_context_packs(repo)` returns matching packs for configured repos instead of an empty list.
- AC-3: Context Manager attaches pack data to TaskPacket enrichment when packs are available.
- AC-4: Signal `pack_used_by_task` emitted when a pack is attached to a task packet.
- AC-5: Signal `pack_missing_detected` emitted when a repo has no matching context pack.
- AC-6: Pack schema includes: name, version, repo patterns, content sections (conventions, api_patterns, constraints, testing_notes).

### Expert Class Expansion
- AC-7: At least 5 expert classes have seeded expert instances (currently 2: security, qa_validation; need 3+ more).
- AC-8: Each new expert has: class assignment, domain keywords, capability description, and initial weight.
- AC-9: New experts are discoverable via the Expert Performance Console (admin UI).
- AC-10: Expert routing considers all seeded classes during consult selection.

### Single-Pass Success Enforcement
- AC-11: A configurable success threshold (default 60%) is defined and checked.
- AC-12: An API endpoint reports whether the threshold is currently met (pass/fail with current rate).
- AC-13: When the rate drops below threshold, an alert signal is emitted with category breakdown.
- AC-14: Admin UI Metrics Dashboard displays threshold status (met/not met) with visual indicator.
- AC-15: Rolling 4-week window used for enforcement (matching roadmap specification).

---

## 5. Constraints & Non-Goals

### Constraints
- All data remains in-memory (no new database tables in this epic).
- Expert seeding uses the existing `seed.py` pattern — no external data sources.
- Context packs are static definitions (JSON or Python dataclasses), not dynamically generated.
- Signals use the existing `SignalEvent` / `ingest_signal()` pipeline.

### Non-Goals
- Dynamic context pack generation from repository analysis.
- Expert auto-creation or machine learning-based expert discovery.
- External alerting integrations (email, Slack, PagerDuty) — signal emission is sufficient.
- Expert retirement or lifecycle management.
- Complexity Index work (separate epic if needed).

---

## 6. Stakeholders & Roles

| Role | Persona/Agent |
|------|---------------|
| Epic owner | Saga |
| Sprint planning | Helm |
| Review & challenge | Meridian |
| Implementation | Execution agents (from 08-agent-roles.md) |
| Quality gate | TAPPS pipeline |

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Expert classes with seeded instances | >= 5 of 8 |
| Service Context Packs in use | >= 2 |
| Context pack signals emitting | pack_used_by_task and pack_missing_detected both functional |
| Single-pass threshold enforcement | Gate active at 60% with 4-week rolling window |
| Phase 3 deliverable completion | 7/7 (closing remaining 3) |
| Test coverage for new code | All new modules have unit tests |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Static context pack content may lack depth, providing little value to experts | Experts make same decisions with or without packs — no measurable improvement | Start with 2 well-researched packs for repos with known recurring issues; validate by checking if expert routing changes when packs are present |
| Routing ambiguity with 5+ expert classes — multiple classes may match a single task | Over-consultation, slower workflows, conflicting advice | Each expert has scoped domain keywords; routing selects top-N by relevance score, not all matches; existing routing tests cover this |
| 60% threshold triggers false alerts on low sample counts (e.g. 2 of 3 tasks fail = 33%) | Alert fatigue, distrust of enforcement mechanism | Require minimum sample count (e.g. 10 workflows in the 4-week window) before enforcement activates; report "insufficient data" below threshold |

---

## 9. Context & Assumptions

### What exists
- `ServiceContextPack` dataclass and `get_context_packs()` stub exist — need real implementation.
- `ExpertClass` enum has 8 values — only 2 seeded. The `seed_experts()` function and `ExpertLibrary` are ready for more.
- `MetricsService.get_single_pass()` computes the rate — enforcement logic needs to wrap it.
- Context Manager already calls `get_context_packs()` and would attach results if any were returned.
- Signal ingestion pipeline (`ingest_signal()`) can accept new signal types.

### Assumptions
- Static context packs (defined in code) are sufficient for Phase 3. Dynamic pack generation is Phase 4+.
- Expert seeding with reasonable domain keywords provides enough routing signal. Real-world tuning happens post-Phase 3.
- The 60% threshold may need adjustment after observation — the enforcement mechanism matters more than the exact number.
- In-memory stores continue to be acceptable for Phase 3 (persistence is a Phase 4 concern).

### Dependencies
- No external dependencies. All work builds on existing modules.
- Epic 5's eval suite and metrics APIs are complete and stable.

---

*Epic created by Saga. Ready for Meridian review.*
