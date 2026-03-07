# Epic 6 Sprint 1 Plan — Phase 3 Completion

**Persona:** Helm (Planner & Dev Manager)
**Date:** 2026-03-06
**Epic:** Epic 6 — Phase 3 Completion
**Stories:** 6.1–6.8

---

## Sprint Goal

**Objective:** Close all remaining Phase 3 deliverables — service context packs, expert class expansion, and single-pass success enforcement.

**Test:** `get_context_packs("repo-alpha")` returns a real pack; 5+ expert classes have seeded instances; `GET /admin/metrics/success-gate` returns pass/fail with threshold check; all new signals emitting.

**Constraint:** All data in-memory. No new DB tables. No external integrations.

---

## Retro Actions (from Epic 5 Sprint 1)

| Action | How addressed |
|--------|--------------|
| Consider `debug_match` mode for eval suites | Deferred — not in scope for this sprint (eval improvement backlog) |
| Batch-update `TemplateResponse` calls to new signature | Story 6.8 includes this as part of UI work |
| Review confidence parameters before Phase 3 completion | Story 6.4 — review during expert seeding, document recommendation |

---

## Order of Work

### Track A: Service Context Packs (6.1–6.3)

| Story | Title | Depends on | Tests (est.) |
|-------|-------|-----------|-------------|
| 6.1 | Context Pack Schema & Registry | — | 8 |
| 6.2 | Two Production Context Packs | 6.1 | 6 |
| 6.3 | Context Pack Signals | 6.1 | 8 |

### Track B: Expert Class Expansion (6.4–6.5)

| Story | Title | Depends on | Tests (est.) |
|-------|-------|-----------|-------------|
| 6.4 | Seed 3 New Expert Classes | — | 10 |
| 6.5 | Expert Routing Integration Verification | 6.4 | 6 |

### Track C: Success Enforcement (6.6–6.8)

| Story | Title | Depends on | Tests (est.) |
|-------|-------|-----------|-------------|
| 6.6 | Single-Pass Success Gate Service | — | 8 |
| 6.7 | Success Gate API & Signal | 6.6 | 6 |
| 6.8 | Admin UI — Success Gate Status | 6.7 | 6 |

**Execution order:** 6.1 → 6.2, 6.3 (parallel) → 6.4 → 6.5 → 6.6 → 6.7 → 6.8

Tracks A and B have no cross-dependencies. Track C depends only on existing MetricsService (Epic 5). All three tracks can start in parallel if needed, but sequential execution is fine given the scope.

---

## Story Details

### Story 6.1: Context Pack Schema & Registry

**Goal:** Replace the stub `ServiceContextPack` with a real schema and registry that maps repos to packs.

**Tasks:**
1. Extend `ServiceContextPack` dataclass with: `repo_patterns: list[str]`, `conventions: list[str]`, `api_patterns: list[str]`, `constraints: list[str]`, `testing_notes: list[str]`.
2. Create `PackRegistry` class with `register(pack)`, `get_packs(repo) -> list[ServiceContextPack]` — matches repo against `repo_patterns` using glob/prefix matching.
3. Update `get_context_packs(repo)` to use the registry instead of returning empty list.
4. Unit tests: registry matching, no-match returns empty, multiple packs for one repo.

**Done when:** `get_context_packs("some-repo")` returns matching packs from the registry.

---

### Story 6.2: Two Production Context Packs

**Goal:** Define 2 real context packs with meaningful content for distinct service domains.

**Tasks:**
1. Define pack 1: "fastapi-service" — conventions for FastAPI services (router patterns, dependency injection, Pydantic models, error handling).
2. Define pack 2: "data-pipeline" — conventions for data processing services (batch vs stream, idempotency, retry patterns, schema evolution).
3. Register both packs in the registry at module load time.
4. Unit tests: both packs load, content sections are non-empty, repo pattern matching works.

**Done when:** Two packs with real content are registered and returned for matching repos.

---

### Story 6.3: Context Pack Signals

**Goal:** Emit `pack_used_by_task` and `pack_missing_detected` signals when context packs are (or aren't) attached.

**Tasks:**
1. Add signal emission to `enrich_taskpacket()` in context_manager.py:
   - If packs found: emit `pack_used_by_task` with pack names.
   - If no packs found: emit `pack_missing_detected` with repo name.
2. Add signal type constants if not already in outcome models.
3. Unit tests: mock signal emission, verify correct signal for packs-found and no-packs scenarios.

**Done when:** Both signals are emitted correctly during task packet enrichment.

---

### Story 6.4: Seed 3 New Expert Classes

**Goal:** Add 3 expert templates to bring total seeded classes from 2 to 5.

**New experts:**
1. **technical-review** (TECHNICAL class) — architecture patterns, code quality, performance, design review.
2. **compliance-check** (COMPLIANCE class) — regulatory requirements, data handling, audit trails, retention policies.
3. **process-quality** (PROCESS_QUALITY class) — release readiness, operational hygiene, runbook completeness, incident response.

**Tasks:**
1. Add 3 `ExpertCreate` entries to `SEED_EXPERTS` in `seed.py`, following existing pattern (capability_tags, scope_description, tool_policy, definition with scope_boundaries/expected_outputs/operating_procedure/edge_cases/failure_modes).
2. Unit tests: seed function creates all 5 experts, idempotent re-seed skips existing.
3. Document confidence parameter observation: current CONFIDENCE_SAMPLE_WEIGHT=0.05 means 10 samples reach 0.22 confidence. Note in retro whether adjustment is needed for Phase 4.

**Done when:** `seed_experts()` creates 5 experts across 5 distinct classes.

---

### Story 6.5: Expert Routing Integration Verification

**Goal:** Verify that all 5 seeded expert classes are discoverable and routable.

**Tasks:**
1. Write integration-style tests that seed all 5 experts and verify:
   - All 5 appear in `ExpertPerformanceService.list_experts()`.
   - Each expert's class is correctly assigned.
   - Filtering by class works for all 5 classes.
2. Verify Expert Performance Console (admin UI) renders all 5 experts.

**Done when:** All 5 experts are visible in API and admin UI with correct class assignments.

---

### Story 6.6: Single-Pass Success Gate Service

**Goal:** Create a service that evaluates whether single-pass success meets the threshold.

**Tasks:**
1. Create `SuccessGateService` in `src/admin/success_gate.py`:
   - `check(threshold=0.60, min_samples=10, window_days=28) -> SuccessGateResult`
   - Uses `MetricsService.get_single_pass()` for the rate.
   - Returns: `met: bool`, `current_rate: float`, `threshold: float`, `sample_count: int`, `window_days: int`, `insufficient_data: bool`.
2. If `sample_count < min_samples`, set `insufficient_data=True` and `met=True` (don't fail on low data).
3. Category breakdown from loopback data for diagnosis when gate fails.
4. Unit tests: gate passes at 60%+, fails below, insufficient data handling.

**Done when:** `SuccessGateService.check()` returns correct pass/fail with threshold comparison.

---

### Story 6.7: Success Gate API & Signal

**Goal:** Expose success gate via API and emit alert signal when threshold is not met.

**Tasks:**
1. Add `GET /admin/metrics/success-gate` endpoint to `router.py`:
   - Returns `SuccessGateResult.to_dict()`.
   - Requires `VIEW_METRICS` permission.
2. Add signal emission: when gate fails (`met=False` and not `insufficient_data`), emit `success_gate_failed` signal with rate and threshold.
3. Unit tests: API returns correct response, signal emitted on failure, no signal on pass or insufficient data.

**Done when:** API endpoint returns gate status; signal fires when threshold breached.

---

### Story 6.8: Admin UI — Success Gate Status

**Goal:** Display success gate status on the Metrics Dashboard.

**Tasks:**
1. Add success gate card to `templates/partials/metrics_content.html`:
   - Green/red indicator for met/not-met.
   - Current rate, threshold, sample count.
   - "Insufficient data" message when below min_samples.
2. Wire up in `ui_router.py` — call `SuccessGateService.check()` and pass to template.
3. Fix `TemplateResponse` deprecation warnings in touched routes (retro action).
4. Unit tests: card renders with correct status, handles insufficient data.

**Done when:** Metrics Dashboard shows success gate status with visual indicator.

---

## Capacity & Buffer

| Item | Estimate |
|------|----------|
| Stories | 8 |
| Estimated tests | ~58 |
| Files to create | ~6 |
| Files to modify | ~8 |
| Buffer | 20% — available for fixture tuning, signal wiring edge cases |

---

## Out of Scope This Sprint

- Dynamic context pack generation from repo analysis
- Expert auto-creation or lifecycle management
- External alerting (email, Slack)
- Complexity Index changes
- Eval suite improvements (debug_match mode)
- TemplateResponse fixes in routes not touched by this sprint

---

*Plan by Helm. Ready for Meridian review.*
