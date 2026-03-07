# Epic 8 Sprint 1 — Test Health & End-to-End Smoke Test

**Date:** 2026-03-07
**Sprint:** Epic 8 Sprint 1
**Tracks:** A (Test Health) + D (End-to-End Smoke Test)
**Status:** Planned — awaiting Meridian review

---

## Sprint Goal

**Objective:** All tests pass with zero warnings that indicate breakage, and a single end-to-end smoke test proves the full intake-to-publish flow works in-memory.

**Verification:** `pytest tests/` returns 0 failures, 0 errors. `pytest tests/e2e/test_smoke.py` passes. TemplateResponse deprecation warnings are eliminated.

**Constraint:** No new external dependencies. No breaking changes to existing APIs.

---

## What's Out This Sprint

- Real provider adapters (Track B) — Sprint 2
- Persistence adapters (Track C) — Sprint 2
- Docker Compose and CI config (Track E) — Sprint 2
- OpenClaw, Temporal, JetStream — non-goal

---

## Stories

### Story 8.1: Fix TemplateResponse Deprecation Warnings
**Track:** A | **Size:** S | **AC:** 2

Fix all `TemplateResponse(name, {"request": request})` calls to use `TemplateResponse(request, name)` pattern. 22 warnings eliminated.

- AC 1: All UI routes use the non-deprecated TemplateResponse signature.
- AC 2: `pytest tests/unit/test_platform_ui.py` produces 0 deprecation warnings.

### Story 8.2: Fix Integration Test DB Dependency
**Track:** A | **Size:** M | **AC:** 2

The 8 integration test errors require a running PostgreSQL. Add a `pytest.mark.integration` marker and skip them when no DB is available. Document how to run them with a real DB.

- AC 1: `pytest tests/unit/` runs without errors (integration tests excluded by default).
- AC 2: `pytest tests/integration/ -m integration` is the documented way to run DB tests.

### Story 8.3: End-to-End Smoke Test — Intake to Evidence
**Track:** D | **Size:** L | **AC:** 4

Create `tests/e2e/test_smoke.py` that exercises the full flow using in-memory stores and mocked external calls.

- AC 1: Test sends a mock webhook payload through the intake agent.
- AC 2: Test asserts TaskPacket created with correct status transitions.
- AC 3: Test asserts intent built and verification ran.
- AC 4: Test asserts publisher produces a draft PR call with evidence comment containing TaskPacket ID.

### Story 8.4: Test Coverage Report
**Track:** A | **Size:** S | **AC:** 2

Add pytest-cov configuration and generate a coverage report. Establish a baseline.

- AC 1: `pytest --cov=src tests/unit/` produces a coverage report.
- AC 2: Coverage baseline documented in sprint progress doc.

---

## Order of Work

1. **8.1** (TemplateResponse) — quick fix, clears warning noise
2. **8.2** (Integration markers) — clears error noise
3. **8.3** (Smoke test) — main deliverable, proves full flow
4. **8.4** (Coverage report) — captures baseline

Stories 8.1 and 8.2 are independent and can be parallelized.
Story 8.3 depends on 8.1+8.2 being done (clean test output).
Story 8.4 depends on 8.3 (coverage includes smoke test).

---

## Capacity & Buffer

4 stories, 80% commitment. Story 8.3 (smoke test) is the riskiest — may need to stub multiple layers. Buffer allows for discovery during smoke test integration.

---

## Retro Actions

First sprint post-roadmap. No prior retro actions. Establishing baseline.

---

## Dependencies

- No external dependencies. All in-memory, all mocked.
- pytest-cov package needed for Story 8.4 (pip install).
