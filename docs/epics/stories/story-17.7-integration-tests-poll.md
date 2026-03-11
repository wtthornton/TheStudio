# Story 17.7 — Integration Tests for Poll Path

> **As a** developer maintaining the pipeline,
> **I want** integration tests for the poll intake path,
> **so that** I can verify end-to-end behavior and dedupe.

**Purpose:** Without integration tests, regressions in the poll path could go undetected. This story delivers end-to-end coverage so we can verify happy path, 304, dedupe, PR filtering, and feature-flag behavior.

**Intent:** Five scenarios with mocked GitHub API: (1) new issue → TaskPacket + workflow, (2) 304 → no work, (3) duplicate → one TaskPacket, (4) issue+PR → only issue processed, (5) flag off → scheduler idle. Tests run without real tokens or API.

**Points:** 5 | **Size:** M  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** C (Stories 17.6–17.8)  
**Depends on:** Stories 17.1–17.3, 17.6

---

## Description

Integration tests verify that the poll path discovers issues, creates TaskPackets, starts workflows, and dedupes correctly. Use mocked GitHub API (respx, httpx, or similar) to avoid real API calls.

## Tasks

- [ ] Create `tests/integration/test_poll_intake.py`:
  1. **Happy path:** Mock 200 with 1 new issue → feed creates TaskPacket → workflow started
  2. **304 path:** Mock 304 → no TaskPackets created, no workflow
  3. **Dedupe path:** Same issue polled twice (same updated_at) → one TaskPacket only
  4. **PR filtered:** Mock 200 with 1 issue + 1 PR → only 1 TaskPacket
  5. **Feature flag off:** Scheduler does not run when disabled
- [ ] Use test database and mocked GitHub client
- [ ] Ensure no real GitHub API calls or tokens

## Acceptance Criteria

- [ ] All 5 scenarios pass
- [ ] Tests run without real GitHub API or tokens
- [ ] Existing integration tests still pass

## Test Cases

| # | Scenario | Mock | Expected |
|---|----------|------|----------|
| 1 | Happy path | 200, 1 issue | 1 TaskPacket, 1 workflow |
| 2 | 304 | 304 | 0 TaskPackets |
| 3 | Dedupe | Same issue twice | 1 TaskPacket total |
| 4 | PR filter | 1 issue + 1 PR | 1 TaskPacket (PR ignored) |
| 5 | Flag off | N/A | Scheduler not started |

## Files Affected

| File | Action |
|------|--------|
| `tests/integration/test_poll_intake.py` | Create |
