# Epic 51: Ralph Vendored SDK Parity — Stall Detection, Progressive Context, and Structured Outputs

<!-- docsmcp:start:metadata -->
**Status:** **COMPLETE** (2026-03-25) — All P0/P1 tasks delivered (eval gaps closed, cancel hardening, git hardening, tests). Meridian PASS (2026-03-23); see `MERIDIAN-REVIEW-EPIC-51.md`
**Priority:** P0-P1 — Production quality and cost
**Estimated LOE:** ~3-4 weeks (P0 slice 2.5-4.5 days; full backlog 17-21 days per evaluation)
**Dependencies:** Epic 43 (Ralph SDK integration) — parallel or prerequisite for consuming new TaskResult fields

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that TheStudio's embedded Ralph SDK matches production-grade behaviors already shipped in the bash CLI (v2.2.0+), closes P0 integration risks (deferred-test stalls, bloated fix_plan context, fragile changed-files parsing), and can be patched in vendor/ralph-sdk without waiting for an upstream SDK release.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Implement prioritized SDK enhancements and bridge fixes identified in docs/ralph-sdk-upgrade-evaluation.md: P0 first (stall detection, progressive context loading, structured files_changed on TaskResult), then P1/P2 backlog. Upstream contributions remain optional; vendor copy is the default execution path.

**Tech Stack:** thestudio, Python >=3.12

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Ralph CLI v2.2.0 fixed production bugs but the Python SDK stayed at 2.0.2. TheStudio's epic-boundary QA (TESTS_STATUS: DEFERRED) and large fix plans amplify SDK gaps; LOGFIX-6 class failures and token waste are documented in the evaluation.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [x] **P0 — Stall detection:** `FastTripDetector` and `StallDetector` in `circuit_breaker.py` with configurable thresholds (fast-trip, deferred-test stall, consecutive timeouts).
- [x] **P0 — Progressive context:** `ContextManager` (or equivalent) provides `build_progressive_context` + token estimate for `fix_plan.md`.
- [ ] **P0 — Structured outputs:** `TaskResult.files_changed` populated from tool/git records; TheStudio removes regex extraction from `ralph_bridge` / `primary_agent` once the field is reliable. *(Structured paths preferred; legacy bullet heuristic remains as fallback.)*
- [x] **P1 backlog:** Stories 51.4–51.6 (and later P2 items from the evaluation) tracked; implement in priority order after P0. *(51.4–51.6 delivered; P2 per evaluation doc.)*
- [x] **Tests:** Unit tests cover new detectors and context trimming; regression tests for `files_changed` contract.
- [x] **Traceability:** `docs/ralph-sdk-upgrade-evaluation.md` and `EPIC-STATUS-TRACKER.md` reference this epic.

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 51.1 -- P0 — Stall detection (fast-trip, deferred-test, consecutive timeout)

**Points:** 5

Port CLI stall semantics to vendor circuit_breaker.py

(4 acceptance criteria)

**Tasks:**
- [x] Implement p0 — stall detection (fast-trip, deferred-test, consecutive timeout)
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P0 — Stall detection (fast-trip, deferred-test, consecutive timeout) is implemented, tests pass, and documentation is updated.

---

### 51.2 -- P0 — Progressive context loading for fix_plan.md

**Points:** 5

ContextManager trims plan to current section + N unchecked items

(3 acceptance criteria)

**Tasks:**
- [x] Implement p0 — progressive context loading for fix_plan.md
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P0 — Progressive context loading for fix_plan.md is implemented, tests pass, and documentation is updated.

---

### 51.3 -- P0 — Structured files_changed on TaskResult

**Points:** 3

Eliminate freeform parsing in TheStudio bridge

(4 acceptance criteria)

**Tasks:**
- [x] Implement p0 — structured files_changed on taskresult
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P0 — Structured files_changed on TaskResult is implemented, tests pass, and documentation is updated.

---

### 51.4 -- P1 — Task decomposition detection

**Points:** 3

detect_decomposition_needed heuristic

(2 acceptance criteria)

**Tasks:**
- [x] Implement p1 — task decomposition detection
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P1 — Task decomposition detection is implemented, tests pass, and documentation is updated.

---

### 51.5 -- P1 — Cost tracking and budget guardrails

**Points:** 5

CostTracker with per-model rates

(3 acceptance criteria)

**Tasks:**
- [x] Implement p1 — cost tracking and budget guardrails
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P1 — Cost tracking and budget guardrails is implemented, tests pass, and documentation is updated.

---

### 51.6 -- P1 — Document and harden RalphAgent.cancel()

**Points:** 2

SIGTERM, CancelResult, Temporal alignment

(3 acceptance criteria)

**Tasks:**
- [x] Implement p1 — document and harden ralphagent.cancel()
- [x] Write unit tests
- [ ] Update documentation

**Definition of Done:** P1 — Document and harden RalphAgent.cancel() is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Vendor tree:** `vendor/ralph-sdk/ralph_sdk/`
- **Source evaluation:** `docs/ralph-sdk-upgrade-evaluation.md` (feature gaps, integration pain points, effort estimates)
- **TheStudio bridge:** `src/agent/primary_agent.py` and `ralph_bridge` (or equivalent) once `TaskResult` exposes structured paths
- **Dev CLI (optional):** Ralph bash CLI v2.2.0+ is separate from the vendored SDK. If `~/.ralph` is not a git clone, clone the Ralph project there before `git pull` (WSL).

**Project Structure:** 7 packages, 262 modules, 1267 public APIs

**Key Dependencies:** fastapi>=0.115.0, uvicorn[standard]>=0.34.0, sqlalchemy[asyncio]>=2.0.36, asyncpg>=0.30.0, pydantic>=2.10.0, pydantic-settings>=2.7.0, temporalio>=1.9.0, nats-py>=2.9.0, cryptography>=44.0.0, opentelemetry-api>=1.29.0

### Expert Recommendations

- **Security Expert** (71%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (66%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Upgrading production Docker images solely to pick up Ralph **CLI** v2.2.0 (SDK unchanged per evaluation).
- Replacing or shrinking Epic 43 (integration); this epic **complements** it via vendor SDK patches.

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Lines | Recent Commits | Public Symbols |
|------|-------|----------------|----------------|
| `vendor/ralph-sdk/ralph_sdk/circuit_breaker.py` | 194 | - | 1 classes |
| `vendor/ralph-sdk/ralph_sdk/agent.py` | 619 | 1 recent: 6669ba7 feat(deploy): production Docker hardeni... | 4 classes |
| `vendor/ralph-sdk/ralph_sdk/parsing.py` | 183 | 1 recent: 6669ba7 feat(deploy): production Docker hardeni... | 2 classes, 1 functions |
| `vendor/ralph-sdk/ralph_sdk/status.py` | 279 | 1 recent: 6669ba7 feat(deploy): production Docker hardeni... | 5 classes |
| `src/agent/primary_agent.py` | 609 | 5 recent: 796be79 feat(epic43): E2E integration test for ... | 1 classes, 2 functions |

<!-- docsmcp:end:files-affected -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

**Primary success metric:** **Deferred-test stall visibility** — the SDK must surface or trip on repeated deferred-test / no-progress loops (see §1.1 in `docs/ralph-sdk-upgrade-evaluation.md`). Measured via harness + logs or circuit breaker state.

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Deferred-test stall visibility | SDK does not trip on deferred tests | Harness / integration repro of deferred-test stall trips CB or surfaces metric | Tests + logs |
| Context size for large fix plans | Full plan loaded each iteration | Trimmed progressive context; token estimate available | Fixture plans + assertions |
| Changed-files accuracy | Regex on freeform output | `TaskResult.files_changed` only (no duplicate heuristics) | Unit + bridge tests |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:stakeholders -->
## Stakeholders

| Role | Person | Responsibility |
|------|--------|----------------|
| Owner | Primary Developer | Implementation |

<!-- docsmcp:end:stakeholders -->

<!-- docsmcp:start:references -->
## References

- `docs/ralph-sdk-upgrade-evaluation.md` — full gap analysis and prioritization
- `docs/epics/epic-43-ralph-sdk-integration.md` — Primary Agent integration epic
- `docs/architecture/RFC-001-ralph-sdk-integration.md`
- `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` — implementation quality / autonomous operation KRs
- `docs/ralph-upstream-issues.md` — upstream GitHub tracking (frankbria/ralph-claude-code)

<!-- docsmcp:end:references -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 51.1: P0 — Stall detection (fast-trip, deferred-test, consecutive timeout)
2. Story 51.2: P0 — Progressive context loading for fix_plan.md
3. Story 51.3: P0 — Structured files_changed on TaskResult
4. Story 51.4: P1 — Task decomposition detection
5. Story 51.5: P1 — Cost tracking and budget guardrails
6. Story 51.6: P1 — Document and harden RalphAgent.cancel()

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Upstream drift when rebasing `vendor/ralph-sdk` | Medium | Medium | Document diff checkpoints; contribute patches upstream when stable |
| Incomplete tool-use capture for `files_changed` | Medium | High | Fall back to `git diff` + explicit tests; align with Claude tool records when available |
| Story stubs lack file-level tasks until Helm expands them | Medium | Medium | Follow §Implementation order; expand with `docs_generate_story` or sprint planning before bulk AI execution |

**Expert-Identified Risks:**

- **Security Expert**: *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*

<!-- docsmcp:end:risk-assessment -->
