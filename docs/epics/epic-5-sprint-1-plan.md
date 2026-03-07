# Epic 5 Sprint 1 Plan — Eval Suite & Metrics APIs

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** Epic 5 — Observability & Quality Measurement
**Sprint Duration:** 2-3 weeks
**Capacity:** 80% commitment, 20% buffer for unknowns

---

## Sprint Goal (Testable)

**Objective:** A runnable eval suite validates intent, routing, verification, and QA quality against labeled fixtures. Metrics APIs expose single-pass success, loopback counts, QA defects, and reopen rate. The Expert Performance Console and Metrics Dashboard are rendered in the Admin UI.

**Test:** A human or script can:
1. Run `python -m src.evals.runner` and see pass/fail results for 4 eval types across 10+ cases
2. Query `GET /admin/metrics/single-pass` and see success rate by repo (7d and 30d)
3. Query `GET /admin/metrics/loopbacks` and see loopback counts by category
4. Query `GET /admin/metrics/reopen` and see reopen rate with attribution breakdown
5. Open `/admin/ui/metrics` in a browser and see all metrics with repo filter
6. Open `/admin/ui/experts` in a browser and see expert weights, confidence, drift by repo

**Constraint:** No changes to Temporal workflows or runtime execution. This sprint reads existing data only.

---

## Order of Work

| Order | Story ID | Title | Depends On | Size | Status |
|-------|----------|-------|------------|------|--------|
| 1 | 5.1 | Eval Framework & Intent Correctness Eval | — | M | Complete |
| 2 | 5.2 | Routing Correctness & Verification Friction Evals | 5.1 | M | Complete |
| 3 | 5.3 | QA Defect Mapping Eval & Eval Runner | 5.1, 5.2 | M | Complete |
| 4 | 5.4 | Metrics APIs — Single-Pass & Loopbacks | — | M | Complete |
| 5 | 5.5 | Metrics APIs — Reopen Rate & Attribution | 5.4 | M | Complete |
| 6 | 5.6 | Expert Performance API | — | M | Complete |
| 7 | 5.7 | Admin UI — Metrics Dashboard | 5.4, 5.5 | M | Complete |
| 8 | 5.8 | Admin UI — Expert Performance Console | 5.6 | M | Complete |

**Explicitly out of Sprint 1:**
- Reopen webhook ingress extension (spike in Sprint 2 if needed)
- Automated eval scheduling (manual run is sufficient)
- Single-pass success target enforcement (measurement first)
- Service Context Pack creation
- Expert bench expansion

---

## Story Definitions of Done

### 5.1: Eval Framework & Intent Correctness Eval

**Reference:** `thestudioarc/EVALS.md` (intent correctness)

**Acceptance Criteria:**
- [ ] `src/evals/` module created with `__init__.py`, `framework.py`, `runner.py`
- [ ] `EvalCase` dataclass: id, eval_type, input_data, expected_output, metadata
- [ ] `EvalResult` dataclass: case_id, eval_type, passed, score, details, failure_reason
- [ ] `EvalSuite` base class with `run(cases) -> list[EvalResult]`
- [ ] `IntentCorrectnessEval`: compares Intent Specification (goal, acceptance criteria) against source issue text; scores semantic match
- [ ] At least 3 labeled fixtures: one clear match, one partial match, one clear mismatch
- [ ] Tests verify eval framework and intent correctness scoring

**Estimation reasoning:** Medium. Framework is a straightforward dataclass + runner pattern. Intent correctness scoring is the main design decision (keyword overlap vs semantic similarity). Start with keyword/structure matching; upgrade later.

---

### 5.2: Routing Correctness & Verification Friction Evals

**Reference:** `thestudioarc/EVALS.md` (routing, verification)

**Acceptance Criteria:**
- [ ] `RoutingCorrectnessEval`: given task with risk flags, checks if required expert classes were consulted
- [ ] Input: risk_flags, consulted_expert_classes, mandatory_coverage_rules
- [ ] Output: pass if all required classes covered, fail with missing classes listed
- [ ] `VerificationFrictionEval`: measures iterations-to-green and time-to-green
- [ ] Input: workflow timeline entries (verify steps with attempt counts and durations)
- [ ] Output: friction_score (normalized by complexity band), iterations, total_time_ms
- [ ] At least 3 fixtures per eval type
- [ ] Tests verify both evals

**Estimation reasoning:** Medium. Routing eval is deterministic (set comparison). Verification friction is a formula over timeline data (straightforward).

---

### 5.3: QA Defect Mapping Eval & Eval Runner

**Reference:** `thestudioarc/EVALS.md` (QA defect mapping)

**Acceptance Criteria:**
- [ ] `QADefectMappingEval`: maps QA defects to acceptance criteria
- [ ] Input: acceptance_criteria list, qa_defects list (with category, severity)
- [ ] Output: mapped defects (which criterion each defect relates to), unmapped defects, coverage_score
- [ ] Classifies unmapped defects as intent_gap (criterion missing) vs implementation_bug (criterion present but failed)
- [ ] `EvalRunner`: loads all eval suites, runs against fixtures directory, produces aggregate JSON report
- [ ] `python -m src.evals.runner` is the entry point
- [ ] Report includes: total_cases, passed, failed, score_by_eval_type
- [ ] At least 4 fixtures for QA eval
- [ ] 10+ total fixtures across all 4 eval types

**Estimation reasoning:** Medium. QA mapping is the most interesting eval — requires matching defect text to criteria. Start with keyword matching. Runner is straightforward aggregation.

---

### 5.4: Metrics APIs — Single-Pass & Loopbacks

**Reference:** `thestudioarc/23-admin-control-ui.md` (Metrics and Trends, lines 52-58)

**Acceptance Criteria:**
- [ ] `src/admin/metrics.py` module with `MetricsService` class
- [ ] `GET /admin/metrics/single-pass` returns single-pass success rate:
  - Overall and per-repo
  - Rolling 7-day and 30-day windows
  - Computed from Outcome Ingestor data (workflows where verification + QA passed on first attempt)
- [ ] `GET /admin/metrics/loopbacks` returns verification loopback breakdown:
  - By category: lint, test, security, other
  - Count and percentage
  - Per-repo filter
- [ ] Tests with mock data

**Estimation reasoning:** Medium. Queries existing outcome/signal data. Main work is the aggregation logic and time-window computation.

---

### 5.5: Metrics APIs — Reopen Rate & Attribution

**Reference:** `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` Phase 3 (reopen rate)

**Acceptance Criteria:**
- [ ] `GET /admin/metrics/reopen` returns reopen rate:
  - Percentage of merged PRs reopened within 30 days
  - Attribution breakdown: intent_gap, implementation_bug, regression, unknown
  - Per-repo filter
- [ ] Reopen events read from `src/outcome/reopen.py` existing data
- [ ] If no reopen data exists yet, API returns zeros with a note
- [ ] Tests with mock reopen data

**Estimation reasoning:** Medium. Reopen module exists (`src/outcome/reopen.py`). Main work is aggregation and attribution breakdown. Risk: reopen data may be sparse; API must handle empty state gracefully.

---

### 5.6: Expert Performance API

**Reference:** `thestudioarc/23-admin-control-ui.md` (Expert Performance Console, lines 124-141)

**Acceptance Criteria:**
- [ ] `GET /admin/experts` returns list of experts with: name, class, trust_tier, confidence, weight
- [ ] `GET /admin/experts/{id}` returns expert detail with per-repo breakdown:
  - Repo, consults, avg_loops, qa_defects, net_impact
- [ ] `GET /admin/experts/{id}/drift` returns drift data: trend (improving/stable/declining), change_pct
- [ ] Uses existing Reputation Engine `query_weights()` and drift detection
- [ ] Tests with mock reputation data

**Estimation reasoning:** Medium. Wraps existing Reputation Engine APIs. Main work is the endpoint definitions and response shaping.

---

### 5.7: Admin UI — Metrics Dashboard

**Reference:** `thestudioarc/23-admin-control-ui.md` (Metrics and Trends)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/metrics` renders Metrics & Trends page
- [ ] Single-pass success card with 7d and 30d values
- [ ] Loopback breakdown table (category, count, percentage)
- [ ] QA defect summary (by severity)
- [ ] Reopen rate card with attribution breakdown
- [ ] Repo filter dropdown that reloads metrics via HTMX
- [ ] Navigation link added to sidebar (between Workflows and Audit)
- [ ] RBAC: Viewer+ can see metrics
- [ ] Tests verify page renders with key content

**Estimation reasoning:** Medium. Follows established HTMX + Jinja2 patterns from Sprint 2. Calls metrics APIs via services, renders partials.

---

### 5.8: Admin UI — Expert Performance Console

**Reference:** `thestudioarc/23-admin-control-ui.md` (Expert Performance Console)

**Acceptance Criteria:**
- [ ] `GET /admin/ui/experts` renders Expert Performance page
- [ ] Expert list table: name, class, trust_tier, confidence, weight, drift_indicator
- [ ] Filterable by repo, expert class, trust tier via HTMX
- [ ] `GET /admin/ui/experts/{id}` renders expert detail with per-repo breakdown
- [ ] Drift indicator: color-coded (green=improving, gray=stable, red=declining)
- [ ] Navigation link added to sidebar
- [ ] RBAC: Viewer+ can see experts
- [ ] Tests verify page renders

**Estimation reasoning:** Medium. Same pattern as repos and workflows views. Data from Expert Performance API (5.6).

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Outcome Ingestor | Complete | Source for single-pass and loopback data |
| Reputation Engine | Complete | Source for expert weights, confidence, drift |
| Reopen module | Complete | `src/outcome/reopen.py` exists |
| Admin UI framework | Complete | HTMX + Jinja2 patterns proven in Epic 4 Sprint 2 |
| Signal stream data | Assumed | Metrics require historical signal data to be meaningful |

No external team dependencies.

---

## Retro Actions Applied (from Sprint 2)

| Lesson | How Applied |
|--------|-------------|
| TemplateResponse deprecation | Will use new `TemplateResponse(request, name)` signature for new templates |
| Cross-cutting concerns first | Eval framework (5.1) built before specific evals (5.2-5.3); Metrics service (5.4) before UI (5.7) |
| CDN dependency noted | No change — same approach, documented |

---

## Capacity and Buffer

- **Total stories:** 8
- **Large:** 0
- **Medium:** 8
- **Buffer:** 20%

If timeline is at risk, consider deferring:
- 5.8 (Expert Performance Console) — experts can be queried via API
- 5.5 (Reopen Rate) — if reopen data is sparse, defer to Sprint 2

---

## Sprint Rituals

- **Daily standup:** 15 min, focus on blockers
- **Mid-sprint check:** After story 5.3, assess eval fixture quality and coverage
- **Sprint review:** Demo eval runner + metrics dashboard + expert console in browser
- **Retro:** Action items for Sprint 2 or next epic

---

*Plan created by Helm. Awaiting Meridian review before sprint start.*
