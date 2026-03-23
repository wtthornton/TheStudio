# Meridian Review — Epic 51: Ralph Vendored SDK Parity

**Reviewer:** Meridian (VP Success)  
**Date:** 2026-03-23  
**Epic:** `docs/epics/epic-51-ralph-vendored-sdk-parity.md`  
**Checklist:** `thestudioarc/personas/meridian-review-checklist.md`

---

## Epic Review — 7 Questions

### 1. One measurable success metric — What is it, and how will we read it?

**Pass.**

**Primary metric (designated):** **Deferred-test stall visibility** — the SDK must not silently burn loops when tests stay deferred (aligned with `TESTS_STATUS: DEFERRED` / LOGFIX-6 class failures).

**How we read it:** Automated harness or integration scenario where deferred tests repeat without file progress; circuit breaker trips **or** a structured metric/span proves the stall was detected. Epic §Success Metrics row 1 defines baseline/target/measurement.

Secondary metrics (context trim, `files_changed` contract) remain explicit in the same table and support P0 stories 51.2 and 51.3.

---

### 2. Top three risks — How are we mitigating each?

**Pass** (after epic lists three distinct risks).

| # | Risk | Mitigation |
|---|------|------------|
| 1 | **Upstream / vendor drift** when rebasing `vendor/ralph-sdk` | Diff checkpoints; upstream issues filed; contribute patches when stable. |
| 2 | **Incomplete tool-use capture** for `files_changed` | `git diff` fallback; contract tests; align with Claude tool records when available. |
| 3 | **Story stubs lack file-level tasks** until Helm decomposes | Implementation order is fixed (51.1→51.3); before autonomous execution, run `docs_generate_story` or Helm slice planning so each story has concrete file paths and AC. |

---

### 3. Non-goals in writing — What are we explicitly not doing?

**Pass.**

Epic §Out of Scope states: no Docker-only upgrades for CLI 2.2.0; no replacement of Epic 43. Clear boundaries.

---

### 4. External dependencies — Written or agreed commitment (owner, date)?

**Pass with note.**

- **Epic 43:** TheStudio integration epic — dependency documented; sequencing is “parallel or prerequisite” for consuming new `TaskResult` fields. Owner: Primary Developer (solo). No external team SLA.
- **Upstream Ralph (`frankbria/ralph-claude-code`):** Optional contribution path; vendor copy is default. GitHub issue(s) opened for visibility (see `docs/ralph-upstream-issues.md`).

**Note:** Upstream maintainers are not pre-committed; vendor path de-risks delivery.

---

### 5. Link to goal/OKR — Why this epic now?

**Pass.**

References include `docs/ralph-sdk-upgrade-evaluation.md` (dated analysis) and Epic 43. Explicit OKR tie: implementation quality and autonomous operation (auto-merge / Execute tier posture) per `thestudioarc/personas/MERIDIAN-TEAM-REVIEW-AND-OKRS.md` — reducing silent Ralph failures and token waste directly supports reliable autonomous implementation.

---

### 6. Testable acceptance criteria — Verifiable by human or script?

**Pass.**

Epic §Acceptance Criteria are checkboxes with concrete artifacts: named modules (`circuit_breaker.py`), behaviors (`build_progressive_context`, `TaskResult.files_changed`), removal of regex parsing, tests, traceability docs. No “user feels good” language.

---

### 7. AI-ready — Enough to know “done” without guessing?

**Pass with note.**

P0 scope is clear from evaluation doc + file list + implementation order. **Gap closed by process:** story-level tasks are still generic; before unsupervised multi-loop implementation, expand stories (or Ralph loop with one story at a time) using the evaluation’s section 1–2 as the spec source of truth.

---

## Red flags

None blocking. Watch: **everything tagged P0** across stories — sequencing in §Implementation Order mitigates “all at once.”

---

## Verdict

**PASS** — Epic 51 may be treated as **approved for scheduling** after metadata reflects Meridian sign-off. Preconditions: (a) Helm/story expansion before bulk autonomous execution; (b) vendor diff discipline when pulling upstream.

**Sign-off:** Meridian PASS (2026-03-23)
