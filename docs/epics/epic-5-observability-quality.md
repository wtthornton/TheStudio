# Epic 5 — Observability & Quality Measurement

**Persona:** Saga (Epic Creator)
**Date:** 2026-03-06
**Status:** Complete — Eval suite, metrics, expert performance, reopen tracking implemented
**Phase:** 3 (Scale + Quality Bar)
**Reference:** `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` Phase 3

---

## 1. Narrative

Phase 2 closed the learning loop — the Outcome Ingestor normalizes, the Reputation Engine weights, and the Router selects. Phase 3 asks: **are we getting better?**

This epic delivers the measurement layer: an eval suite that checks intent, routing, verification, and QA quality against labeled data; an Admin UI metrics dashboard that surfaces single-pass success, loopbacks, QA defects, and reopen rate; and the tracking infrastructure for reopen attribution.

Without this, the system operates blind. With it, operators and the system itself can answer: "What's our quality bar, and where does it fail?"

---

## 2. References

- Roadmap Phase 3: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` lines 138-163
- Evals specification: `thestudioarc/EVALS.md`
- Admin UI mockups (Metrics & Trends): `thestudioarc/23-admin-control-ui.md` lines 52-58
- Expert taxonomy: `thestudioarc/02-expert-taxonomy.md`
- Outcome Ingestor: `src/outcome/ingestor.py`
- Reputation Engine: `src/reputation/engine.py`

---

## 3. Acceptance Criteria

### Eval Suite
- [ ] `src/evals/` module exists with first eval suite
- [ ] Intent correctness eval: compare Intent Specification goal + acceptance criteria against source issue; score match/mismatch
- [ ] Routing correctness eval: for tasks with risk flags, verify required expert classes were consulted
- [ ] Verification friction eval: measure iterations-to-green and time-to-green per workflow, normalized by complexity
- [ ] QA defect mapping eval: map QA defects to acceptance criteria; identify intent_gap vs implementation_bug
- [ ] Eval runner: `python -m src.evals.runner` executes all evals against labeled dataset and produces JSON report
- [ ] At least 10 labeled eval cases (fixtures) for initial suite
- [ ] Eval results include pass/fail per case, aggregate scores, and category breakdown

### Metrics & Trends Dashboard (Admin UI)
- [ ] `GET /admin/ui/metrics` renders Metrics & Trends page
- [ ] Single-pass success rate: percentage of workflows completing verification + QA on first attempt, rolling 7d and 30d
- [ ] Verification loopbacks by category: lint, test, security, other — count and trend
- [ ] QA defects by severity and category: bar chart data or table
- [ ] Reopen rate: percentage of merged PRs reopened within 30 days
- [ ] All metrics filterable by repo
- [ ] Metrics partial auto-refreshes via HTMX

### Reopen Rate Tracking
- [ ] `src/outcome/reopen.py` enhanced: capture reopen events, link to original TaskPacket
- [ ] Attribution: classify reopen cause as intent_gap, implementation_bug, or regression
- [ ] Reopen events stored in database with attribution
- [ ] `GET /admin/metrics/reopen` API returns reopen rate and attribution breakdown
- [ ] Visible in Admin UI metrics dashboard

### Expert Performance Console (Admin UI)
- [ ] `GET /admin/ui/experts` renders Expert Performance page
- [ ] Shows: expert name, class, trust tier, confidence, weight by repo/context
- [ ] Drift indicator: improving/stable/declining per expert
- [ ] Filterable by repo, expert class, trust tier
- [ ] Links to detailed expert history

---

## 4. Constraints & Non-Goals

**Constraints:**
- Eval suite runs offline against labeled data — not inline in the workflow
- Metrics are computed from existing signal stream and Outcome Ingestor data
- No new Temporal workflow changes — this epic reads existing data

**Non-Goals:**
- Automated eval-driven retraining or expert parameter tuning (Phase 4)
- Model spend dashboards (Phase 4)
- Policy & Guardrails Console (Phase 4)
- Service Context Pack creation or expert expansion (separate epic)
- Single-pass success target enforcement (>=60%) — this epic measures; enforcement is a follow-up

---

## 5. Stakeholders

| Role | Interest |
|------|----------|
| Operators | Need visible metrics to assess system health beyond uptime |
| Meridian (VP Success) | Needs single-pass success and reopen rate for quality bar decisions |
| Router/Reputation Engine | Consumes eval results to validate weight accuracy |
| Helm (Planner) | Uses metrics for sprint retro and improvement priorities |

---

## 6. Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| Eval suite exists and runs | 4 eval types, 10+ cases | `python -m src.evals.runner` exits 0 |
| Metrics dashboard renders | All 4 metric categories visible | Admin UI test |
| Reopen tracking operational | Events captured and attributed | Integration test |
| Expert Performance Console renders | Weight/confidence/drift visible | Admin UI test |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Labeled eval data insufficient | Medium | High | Start with 10 cases covering happy path + known failure modes; expand as production data grows |
| Reopen webhook not in ingress | Medium | Medium | Check if issue reopen events are captured by existing webhook handler; extend if needed before Sprint 1 |
| Metrics computation too slow on large datasets | Low | Medium | Use materialized aggregates or caching; metrics are read-heavy, compute-light |

---

## 8. Context & Assumptions

- Outcome Ingestor, Reputation Engine, and signal stream are operational (Phase 2 complete)
- Admin UI framework (HTMX + Jinja2) is established and proven (Epic 4 Sprint 2)
- Expert classes are defined (8 classes exist) but only 2 are seeded — this epic does not expand the expert bench
- Labeled eval data must be manually created for the initial suite; future evals can use production data
- Reopen events require webhook handling for issue reopen events (may need ingress extension)

---

*Epic created by Saga. Awaiting Meridian review before planning.*
