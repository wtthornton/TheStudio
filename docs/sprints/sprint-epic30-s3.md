# Sprint Plan: Epic 30 Sprint 3 -- Feature Flag Activation & Deployment

**Planned by:** Helm
**Date:** 2026-03-19
**Status:** COMMITTED (Meridian review: COMMITTABLE, 2026-03-19, 7/7 PASS)
**Sprint Duration:** 1 week (5 working days, 2026-03-19 to 2026-03-25)
**Capacity:** Single developer, 30 hours total (5 days x 6 productive hours), 80% allocation = 24 hours, 6 hours buffer

---

## Sprint Goal (Testable Format)

**Objective:** Fix the three blocking/should-fix bugs from the failure catalog (F7, F8, F9), re-run the routing eval to confirm quality gates pass, then deliver the deployment runbook and begin Suggest tier validation -- proving that the deployed Docker stack can process issues at both Observe and Suggest trust tiers with all feature flags activated.

**Test:** After all work items are complete:

1. F8 fix: `AssemblerAgentOutput.qa_handoff[].criterion` accepts both `str` and `list[str]` without validation errors. Assembler eval parse rate > 0% (was 0/7).
2. F7 fix: Router eval produces non-zero quality scores (template variables resolve in eval context).
3. F9 fix: Intake and context eval pass rates > 0% with calibrated scoring thresholds.
4. Routing eval re-run (4 cost + 4 quality tests): >= 6/8 pass (cost tests: 4/4, quality: >= 2/4). API cost ~$0.35.
5. `docs/DEPLOYMENT.md` exists with: every `THESTUDIO_*` env var documented, GitHub App setup, Postgres migration, Temporal/NATS config, Docker Compose instructions, feature flag activation order, rollback procedures.
6. All existing tests pass (`pytest` green, `ruff check .` clean).

**Constraint:** 5 working days. Bug fixes are surgical (specific files identified in failure catalog). Deployment runbook is documentation, not code. Suggest tier validation (Story 30.12) is compressible if time runs short. Total API spend for re-runs must stay under $2.

---

## What's In / What's Out

**In this sprint (6 work items, ~24 estimated hours):**

1. Bug fix: F8 -- Assembler qa_handoff schema mismatch (10 min)
2. Bug fix: F7 -- Router template variable injection (15 min)
3. Bug fix: F9 -- Eval scoring calibration for intake/context (30 min)
4. Re-run routing eval to confirm fixes (~$0.35, 30 min)
5. Story 30.11: Deployment Runbook (~8 hours)
6. Story 30.9: Enable Projects v2 + Meridian Portfolio (~4 hours)

**Compressible (may defer if time runs short):**
7. Story 30.10: Enable Preflight + Container Isolation (~4 hours)
8. Story 30.12: Suggest Tier Validation (~6 hours)

**Out of scope:**
- Epic 32 Slice 2 (budget controls) -- next sprint
- Epic 33 (P0 test harness) -- needs Meridian gaps resolved first
- Story 31.1 (cost estimation fix) -- deferred; actual costs are known from baselines
- Story 31.6 (OAuth documentation) -- low priority, TOS blocks production use
- Prompt engineering beyond what bug fixes require
- CI/CD pipeline changes

---

## Dependency Review

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| Docker prod stack running | Required for 30.9, 30.10, 30.12 | Cannot test feature flags | Bug fixes and deployment runbook work without Docker |
| `THESTUDIO_ANTHROPIC_API_KEY` | Required for eval re-run | Cannot validate quality fixes | Bug fix code changes can be verified by unit tests alone |
| GitHub App on test repo | Required for 30.12 | Cannot test Suggest tier | Defer 30.12 to Sprint 4 |
| Postgres (Docker) | Required for 30.9 | Cannot test Projects v2 persistence | Health check before starting |

### Internal Dependencies (Item-to-Item)

```
F8 fix --> F7 fix --> F9 fix --> Eval re-run
                                      |
Story 30.11 (parallel) ------->  30.9 --> 30.10 --> 30.12
```

- **F8, F7, F9 fixes** have no dependencies on each other but must all complete before the eval re-run
- **Story 30.11 (deployment runbook)** can be written in parallel with bug fixes
- **Story 30.9** depends on a running Docker stack and deployment runbook familiarity
- **Story 30.10** depends on 30.9 (feature flags must work individually before combining)
- **Story 30.12** depends on 30.9 + 30.10 (full feature stack must be active)

**Critical path:** Bug fixes --> Eval re-run (Day 1) | 30.11 in parallel (Day 1-3) | 30.9 (Day 3-4) | 30.10/30.12 if time permits (Day 4-5)

---

## Ordered Work Items

### Day 1: Bug Fixes + Eval Re-run (2 hours)

#### Item 1: Fix F8 -- Assembler qa_handoff Schema Mismatch
**Estimate:** 10 minutes
**File:** `src/assembler/assembler_config.py` (or wherever `AssemblerAgentOutput` is defined)
**Change:** Change `criterion: list[str]` to `criterion: str | list[str]` with a Pydantic validator that coerces `str` to `list[str]`.
**Done when:** Assembler eval no longer produces 7/7 parse failures.

#### Item 2: Fix F7 -- Router Template Variable Injection
**Estimate:** 15 minutes
**File:** `src/eval/routing_eval.py`
**Change:** Fix `router_context_builder` to inject `base_role`, `overlays`, `risk_flags`, `required_classes` into `context.extra` matching the exact template variable names in the router agent's system prompt.
**Done when:** Router eval produces non-zero quality scores.

#### Item 3: Fix F9 -- Eval Scoring Calibration
**Estimate:** 30 minutes
**Files:** `src/eval/scoring.py`, possibly `src/eval/intake_eval.py`, `src/eval/context_eval.py`
**Change:** Review intake/context scoring functions. These agents don't produce "goals" or "constraints" -- they produce classifications and enrichment. Adjust pass thresholds or create agent-specific scoring dimensions.
**Done when:** Intake and context eval pass rates > 0%.

#### Item 4: Re-run Routing Eval
**Estimate:** 30 minutes (mostly waiting for API responses)
**Cost:** ~$0.35
**Done when:** >= 6/8 tests pass. All 4 cost tests pass. At least 2/4 quality tests pass. Results saved to `docs/eval-results/`.

### Day 1-3: Deployment Runbook (Parallel with Bug Fixes)

#### Item 5: Story 30.11 -- Deployment Runbook
**Estimate:** 8 hours (13 story points, L size)
**File to create:** `docs/DEPLOYMENT.md`
**Rationale for sequence:** This is pure documentation -- no code dependencies, no API costs. Can be written in parallel with everything else. Produces the single most valuable artifact for future deployability.

**Key sections:**
1. Prerequisites (Python 3.12+, Docker, GitHub App)
2. Environment variables (every `THESTUDIO_*` variable)
3. Secrets management (Fernet key generation, API key storage, GitHub App private key)
4. GitHub App setup (permissions, webhook config, installation)
5. Postgres setup (migration, connection string, backup/restore)
6. Temporal setup (server, namespace, task queue)
7. NATS setup (JetStream, streams, consumers)
8. Docker Compose (prod vs dev, port mappings, volumes)
9. Feature flags (activation order, validation per flag)
10. Monitoring (OTEL, key metrics)
11. Rollback procedures (feature flags, database, containers)

**Estimation reasoning:** 8 hours is generous for documentation, but this runbook must be comprehensive enough for a cold start. Much of the content requires auditing `src/settings.py` (80+ settings), `infra/docker-compose.prod.yml`, and 6+ service configurations. Writing accurate, tested instructions takes longer than writing code.

**Unknowns:** Temporal and NATS setup steps may need verification against the running Docker stack. If services aren't configured yet, document "TODO: verify" placeholders.

**Done when:** Every `THESTUDIO_*` env var is documented. Every service has start/verify/rollback steps. Feature flag activation order is specified.

### Day 3-4: Feature Flag Activation

#### Item 6: Story 30.9 -- Enable Projects v2 + Meridian Portfolio
**Estimate:** 4 hours (5 story points, M size)
**Rationale for sequence:** Lower-risk feature flags (read-only operations). Tests that project board sync works when flags are flipped.

**Key tasks:**
- Set `projects_v2_enabled=True` with valid owner/number/token
- Verify project board updates on TaskPacket status transitions
- Set `meridian_portfolio_enabled=True` and `meridian_portfolio_github_issue=True`
- Verify portfolio health report posts to configured repo issue
- Verify Admin UI dashboard shows real data from Postgres

**Estimation reasoning:** Primarily configuration and manual verification. The code already exists; this is flip-and-verify.

**Done when:** Board updates on status change. Health report posts successfully. Admin dashboard renders real data.

### Day 4-5: Compressible Items

#### Item 7 (Compressible): Story 30.10 -- Enable Preflight + Container Isolation
**Estimate:** 4 hours (5 story points, M size)
**Rationale for compressibility:** Higher risk than 30.9 (Docker daemon required, container lifecycle). Deferring loses preflight and container validation but does not block Suggest tier.

#### Item 8 (Compressible): Story 30.12 -- Suggest Tier Validation
**Estimate:** 6 hours (8 story points, M-L size)
**Rationale for compressibility:** Most expensive and dependent on everything else working. Requires real GitHub operations, approval workflow, chat approval flow. If deferred, the deployment runbook and feature flag work still deliver Sprint 3's core value.

---

## Capacity Summary

| Item | Estimate | Day | Cumulative |
|------|----------|-----|------------|
| F8 bug fix | 0.2h | Day 1 | 0.2h |
| F7 bug fix | 0.3h | Day 1 | 0.5h |
| F9 bug fix | 0.5h | Day 1 | 1.0h |
| Eval re-run | 0.5h | Day 1 | 1.5h |
| 30.11 Deployment Runbook | 8.0h | Day 1-3 | 9.5h |
| 30.9 Projects v2 + Portfolio | 4.0h | Day 3-4 | 13.5h |
| **Committed total** | **13.5h** | | **45% of 30h capacity** |
| 30.10 Preflight + Container (compress.) | 4.0h | Day 4 | 17.5h |
| 30.12 Suggest Tier (compressible) | 6.0h | Day 4-5 | 23.5h |
| **Full total** | **23.5h** | | **78% of 30h capacity** |
| **Buffer** | **6.5h** | | **22%** |

**Allocation rationale:** 80% target allocation with 20% buffer. The committed core (bug fixes + runbook + Projects v2) is only 45% of capacity, leaving significant room for the compressible stories. This conservative commitment reflects:
- Feature flag activation on a production Docker stack has unknown failure modes
- The deployment runbook requires auditing ~80 settings and multiple service configurations
- Suggest tier validation (30.12) involves the most complex integration path in the project

---

## Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | F8 fix breaks existing assembler tests | Low | Medium | Run full test suite after change; validator is additive (accepts more types, not fewer) |
| 2 | Eval re-run still fails quality tests after F7/F8/F9 fixes | Medium | Low | Quality test failures are eval calibration issues, not production blockers. Document results and iterate in next sprint. |
| 3 | Projects v2 API has changed since Epic 29 was built | Low | Medium | Epic 29 tests validated the API contract. If 401/404, check token permissions first. |
| 4 | Docker stack needs rebuild for new feature flags | Medium | Low | Budget time for `docker compose up --build` (F1 lesson learned). |
| 5 | Suggest tier approval workflow has untested edge cases | Medium | Medium | Story 30.12 is compressible. If approval flow breaks, document in failure catalog and defer fix. |
| 6 | Deployment runbook is incomplete for Temporal/NATS (less-documented services) | Medium | Low | Mark sections as "TODO: verify" and complete in Sprint 4. Runbook is living document. |

---

## Compressible Stories (What Gets Cut If Time Runs Short)

1. **Story 30.12 (Suggest Tier Validation) -- first to defer.** This is the most complex, most expensive story. Deferring it still delivers bug fixes, deployment runbook, and Projects v2 activation. **Impact of deferral:** Cannot confirm Suggest tier works end-to-end. Sprint 4 picks this up.

2. **Story 30.10 (Preflight + Container Isolation) -- second to defer.** This requires Docker daemon and container lifecycle management. Lower value than the deployment runbook. **Impact of deferral:** Cannot confirm safety gates work with real providers. Not blocking for Observe or Suggest tier processing.

If time runs short, cut 30.12 first, then 30.10.

---

## Retro Reference

**Prior sprints for Epic 30:**
- **Sprint 1 (2026-03-18):** Delivered eval harness + 3 agent validations. Key lessons: 77% allocation was appropriate; feature flag mismatch caught in dependency review; cheapest-agent-first sequencing worked well.
- **Sprint 2 (2026-03-18):** Delivered full pipeline Docker validation + failure catalog. Key lessons: Docker container rebuild required after env changes (F1); per-issue cost ($0.087) far under budget.

**Actions carried forward:**
- Always rebuild Docker containers after `.env` changes (F1 mitigation)
- Run dependency review before scheduling (caught feature flag mismatch in Sprint 1)
- Maintain failure catalog as living document (9 failure modes tracked)

---

## Definition of Done (Sprint Level)

- [ ] F8 fixed: `AssemblerAgentOutput.qa_handoff[].criterion` accepts `str | list[str]`
- [ ] F7 fixed: Router eval template variables resolve correctly
- [ ] F9 fixed: Intake/context eval pass rates > 0%
- [ ] Routing eval re-run: >= 6/8 tests pass, results in `docs/eval-results/`
- [ ] `docs/DEPLOYMENT.md` exists with complete env var, service, and flag documentation
- [ ] Story 30.9: Projects v2 and Meridian Portfolio flags activated and verified
- [ ] All existing tests pass (`pytest` green, `ruff check .` clean)
- [ ] Sprint plan reviewed by Meridian before execution begins

---

## Meridian Review: COMMITTABLE (2026-03-19)

**Verdict: 7/7 PASS. No red flags. No gaps requiring fixes.**

| # | Question | Status |
|---|----------|--------|
| 1 | Testable sprint goal? | PASS |
| 2 | Single order of work? | PASS |
| 3 | Dependencies confirmed? | PASS |
| 4 | Estimation reasoning? | PASS |
| 5 | Retro actions? | PASS |
| 6 | Capacity and buffer? | PASS |
| 7 | Async-readable? | PASS |

**Observations (non-blocking):**
- Story 30.12 test repo name should be confirmed (thestudio-test-target vs. thestudio-production-test-rig)
- Deployment runbook 8-hour estimate could itemize per-section effort for tighter tracking
- If bug fixes and runbook go smoothly by Day 3, actively pull 30.10 into committed scope
