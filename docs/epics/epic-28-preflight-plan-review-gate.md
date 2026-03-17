# Epic 28 — Preflight: Lightweight Plan Review Gate Before Implementation

**Author:** Saga
**Date:** 2026-03-17
**Status:** Meridian Reviewed — Conditional Pass (2026-03-17). Fixes applied.
**Target Sprint:** TBD (scheduling preference: after Epics 15, 24, 25 close. Not a hard blocker — can start independently.)
**Prerequisites:** Epic 23 (Unified Agent Framework) — complete. No hard blockers. Epics 15, 24, 25 are scheduling preferences only — Preflight can be developed and tested independently; it delivers more value once real repos are processing tasks.

---

## 1. Title

Preflight — Add a fast, automated plan-quality gate between Assembler (step 5) and Primary Agent (step 6) that catches bad plans before they waste implementation compute, using a new lightweight persona distinct from Meridian.

## 2. Narrative

The pipeline has a blind spot. The Assembler produces a plan — ordered steps, QA handoff, provenance — and the Primary Agent immediately executes it. Nobody asks "is this plan good enough to implement?" before committing 60 minutes of LLM compute and up to 5 loopback cycles.

Today, bad plans are caught late:
- **Verification gate (step 7):** Catches code that doesn't lint or pass tests. By then the agent has already spent time implementing a flawed plan.
- **QA gate (step 8):** Catches acceptance criteria misses. By then the agent has implemented, verified, and possibly looped back — all from a plan that was missing criteria from the start.
- **Loopback exhaustion:** After 2 verification loops and 2 QA loops (5 total attempts), the task fails. If the plan was fundamentally flawed, all 5 attempts were wasted.

The cost asymmetry is stark. Reviewing a plan costs ~$0.50 and takes seconds. Implementing a bad plan costs $10-20+ in LLM spend and minutes of wall-clock time before it fails. A 30-second preflight check that catches even 20% of bad plans pays for itself immediately.

**Preflight is not Meridian.** Meridian reviews epics and sprint plans at the portfolio level — human-scale artifacts with strategic implications. Preflight reviews machine-generated implementation plans at the TaskPacket level — automated, inline, no human involvement. Different scope, different cadence, different persona.

| Aspect | Meridian | Preflight |
|--------|----------|-----------|
| Reviews | Epics, sprint plans | Per-TaskPacket implementation plans |
| Cadence | Pre-sprint, async | Per-task, inline, automated |
| Audience | Humans (Saga, Helm) | Pipeline (Assembler → Agent) |
| Depth | 7 questions, red flags, iteration | 3 focused checks, single-pass |
| Cost | Human time + LLM | ~$0.50 LLM per task |
| Failure mode | Block epic commit | Loopback to Assembler once, then proceed with warning |

### Why now

Three factors:
1. **Real repo onboarding is imminent (Epic 15).** When the pipeline runs against real issues with real ambiguity, plan quality variance will increase. Catching bad plans before execution reduces wasted cycles.
2. **Container isolation adds cost to bad plans (Epic 25).** Each implementation attempt in container mode has startup overhead (5-15s). A bad plan that exhausts loopbacks wastes container resources.
3. **The framework exists (Epic 23).** Adding a new agent to the pipeline is now a config file + one activity + one workflow insertion. The AgentRunner infrastructure handles budget, observability, and prompt guard automatically.

## 3. References

| Artifact | Location |
|----------|----------|
| Assembler (upstream) | `src/assembler/assembler.py` |
| Assembler config (agent def) | `src/assembler/assembler_config.py` |
| Primary Agent (downstream) | `src/agent/primary_agent.py` |
| Pipeline workflow | `src/workflow/pipeline.py` |
| Activity definitions | `src/workflow/activities.py` |
| Agent framework | `src/agent/framework.py` |
| Intent Specification model | `src/intent/intent_spec.py` |
| QA Agent config (pattern reference) | `src/qa/qa_config.py` |
| Observability conventions | `src/observability/conventions.py` |
| Meridian persona (contrast reference) | `thestudioarc/personas/meridian-vp-success.md` |
| Team reset | `thestudioarc/personas/TEAM.md` |

## 4. Acceptance Criteria

### Preflight Agent

1. **Preflight agent config exists.** `src/preflight/preflight_config.py` defines `PREFLIGHT_AGENT_CONFIG` with `agent_name="preflight"`, `max_turns=1`, `max_budget_usd=0.50`, and a system prompt focused on three checks: criteria coverage, constraint compliance, and step specificity.

2. **Preflight system prompt implements three checks.** The system prompt instructs the LLM to evaluate:
   - **Criteria coverage:** Does every acceptance criterion from the IntentSpec have at least one plan step that addresses it? List any uncovered criteria.
   - **Constraint compliance:** Do any plan steps contradict the IntentSpec constraints? List any violations.
   - **Step specificity:** Are all plan steps specific enough to implement without guessing? Flag any step that says "figure out," "determine the best," or equivalent vagueness.

3. **Preflight output model exists.** `PreflightOutput` Pydantic model with fields: `approved` (bool), `uncovered_criteria` (list of strings), `constraint_violations` (list of strings), `vague_steps` (list of strings), `summary` (string — one sentence).

4. **Preflight fallback function exists.** If the LLM call fails, the fallback returns `approved=True` with `summary="Preflight skipped (provider error)"`. Preflight never blocks the pipeline on its own failure.

### Pipeline Integration

5. **`preflight_activity` exists in `src/workflow/activities.py`.** Uses `AgentRunner` with `PREFLIGHT_AGENT_CONFIG`. Input: `PreflightInput` with typed fields: `taskpacket_id: UUID`, `plan_steps: list[str]` (ordered step descriptions from `AssemblerOutput.plan_steps`), `acceptance_criteria: list[str]` (from IntentSpec), `constraints: list[str]` (from IntentSpec). Output: `PreflightOutput`.

6. **Pipeline workflow calls preflight between Assembler and Implement.** In `src/workflow/pipeline.py`, after `assembler_activity` returns and before `implement_activity` is called, the workflow calls `preflight_activity`. A `WorkflowStep.PREFLIGHT` enum entry is added to the step enum, and a corresponding entry is added to `STEP_POLICIES` with retry policy (timeout: 2 min, max retries: 1, backoff: 2.0x).

7. **Preflight failure triggers one Assembler loopback.** If `approved=False`, the workflow calls `assembler_activity` again with the preflight feedback (uncovered criteria, violations, vague steps). If the second plan also fails preflight, the workflow proceeds to Implement with a warning log — preflight does not block indefinitely.

8. **Preflight is feature-flagged.** `settings.preflight_enabled: bool = False`. When disabled, the workflow skips preflight entirely. No latency impact for repos that don't opt in.

9. **Preflight is configurable per trust tier.** `settings.preflight_tiers: list[str] = ["execute"]`. Only tasks for repos at the listed tiers run preflight. Default: Execute only.

### Observability

10. **OpenTelemetry span exists.** `thestudio.preflight.review` span with attributes: `taskpacket_id`, `correlation_id`, `approved`, `uncovered_count`, `violation_count`, `vague_count`.

11. **Preflight result is included in evidence comment.** The Publisher's evidence comment includes a "Preflight" section: "Approved" or "Approved after re-plan" or "Skipped (disabled)" or "Skipped (tier not configured)".

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Preflight rejects good plans (false positives) | Medium | Medium — adds latency for no value | Single loopback + proceed-with-warning. Track false-positive rate via outcome signals. Tune or disable if rate > 20%. |
| Preflight approves bad plans (false negatives) | High initially | Low — QA gate still catches | Preflight is additive. Verification and QA gates are unchanged. Preflight failing to catch a bad plan = status quo. |
| LLM cost adds up across all tasks | Low | Low — $0.50/task, max_turns=1 | Feature-flagged. Default off. Only Execute tier by default. Budget capped. |
| Assembler loopback produces worse plan | Low | Medium | Second plan compared to first. If both fail, use the first (original) plan. |

## 5. Constraints & Non-Goals

### Constraints

- **Single LLM call, max_turns=1.** Preflight is a single-pass judgment. No conversation, no iteration, no tool use.
- **Max one Assembler loopback.** Preflight can trigger one re-plan. If the re-plan fails, proceed. Never block indefinitely.
- **Fallback is always approve.** LLM error, timeout, or provider failure = plan is approved. Preflight is advisory, not a hard gate.
- **No changes to existing agents.** Assembler, Primary Agent, Verification, QA are unchanged. Preflight is inserted between Assembler and Implement in the workflow only.
- **Feature-flagged, off by default.** Existing deployments and tests are unaffected.
- **Python 3.12+, existing dependencies only.** No new dependencies. Uses AgentRunner framework.

### Non-Goals

- **Not a replacement for QA.** QA validates post-implementation against acceptance criteria. Preflight validates pre-implementation against plan quality. Both exist.
- **Not Meridian.** Preflight does not review epics, sprint plans, or strategic artifacts. It reviews a single TaskPacket's implementation plan. Different scope, different persona.
- **Not interactive.** No human involvement. No approval wait. No chat. Fully automated.
- **Not a hard gate.** Preflight failures produce warnings, not pipeline termination. The hard gates are Verification and QA.
- **Not evaluating code quality.** Preflight reviews the plan, not the code. Code quality is Verification's job.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Primary Developer | Accepts scope, reviews AC |
| Tech Lead | Primary Developer | Owns agent config, workflow integration |
| QA | Primary Developer | Validates gate behavior, false-positive rate |
| Saga | Epic Creator | Authored this epic |
| Meridian | VP Success | Reviews this epic before commit |

## 7. Success Metrics

| Metric | Target | Measurement | Definition |
|--------|--------|-------------|------------|
| Bad plan catch rate | > 20% of bad plans caught before implementation | Preflight rejections where the re-plan passes QA on first attempt / total preflight rejections | A "bad plan" is one where QA would fail on the first implementation attempt due to uncovered acceptance criteria or constraint violations — the two categories preflight checks for. |
| False positive rate | < 20% of rejections are false positives | Tasks where preflight rejected, Assembler re-planned, and QA still failed on the same criteria / total preflight rejections | A false positive is a rejection that did not improve the outcome — the re-plan failed on the same criteria the original would have. |
| Latency overhead | < 10 seconds per task (single LLM call) | `thestudio.preflight.review` span duration p95 | — |
| Cost per task | < $0.50 | Model Gateway audit: preflight step cost | — |
| Pipeline throughput unchanged | No increase in total pipeline failure rate | Compare pre/post preflight deployment failure rates over rolling 2-week window | — |
| Preflight-to-QA pass correlation | > 60% of preflight-approved plans pass QA on first attempt | `preflight.approved=True` tasks where `qa_activity` returns `passed=True` on first attempt / total preflight-approved tasks | Measures whether preflight approval is a meaningful positive signal. Replaces loopback reduction metric (no baseline exists). |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/preflight/__init__.py` | **New** — Package |
| `src/preflight/preflight_config.py` | **New** — Agent config, system prompt, output model |
| `src/workflow/activities.py` | **Modified** — Add `preflight_activity` |
| `src/workflow/pipeline.py` | **Modified** — Insert preflight between assembler and implement |
| `src/settings.py` | **Modified** — Add `preflight_enabled`, `preflight_tiers` |
| `src/observability/conventions.py` | **Modified** — Add preflight span names |
| `src/publisher/evidence_comment.py` | **Modified** — Add preflight section |

### Assumptions

1. **The Assembler output contains enough structure to review.** Plan steps, acceptance criteria mapping, and provenance are available from `AssemblerOutput`. No additional data needed.
2. **A single LLM call is sufficient for plan review.** The three checks (criteria coverage, constraint compliance, step specificity) are evaluable from a single prompt with the plan and intent as context.
3. **The AgentRunner framework handles all infrastructure.** Budget enforcement, observability, prompt guard, and provider routing work for a new agent with no framework changes.
4. **Feature flag granularity is sufficient at the tier level.** Per-repo preflight configuration is future work if needed.

### Dependencies

- **Upstream:** Epic 23 (Unified Agent Framework) — complete. Provides AgentRunner.
- **Downstream unblocks:** None directly. Preflight improves pipeline efficiency but does not gate other epics.

---

## Story Map

### Sprint 1: Preflight Agent + Pipeline Integration

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 28.1 | **Preflight Agent Config and Output Model** | S | Foundation | `src/preflight/preflight_config.py` |
| 28.2 | **Preflight Activity and Workflow Integration** | M | Pipeline wiring | `src/workflow/activities.py`, `src/workflow/pipeline.py`, `src/settings.py` |
| 28.3 | **Preflight Observability and Evidence** | S | Traceability | `src/observability/conventions.py`, `src/publisher/evidence_comment.py` |
| 28.4 | **Preflight Tests** | M | Quality assurance | `tests/preflight/`, `tests/integration/` |

---

## Persona Definition

**Name:** Preflight
**Role:** Plan quality reviewer. Fast, automated, inline.
**Scope:** Per-TaskPacket implementation plans only. Not epics. Not sprint plans. Not code.
**Relationship to Meridian:** Meridian reviews human-scale strategic artifacts (epics, plans). Preflight reviews machine-generated tactical artifacts (implementation plans). Meridian is the VP. Preflight is the checklist on the clipboard.

---

## Meridian Review Status

### Round 1: Conditional Pass (2026-03-17)

**Verdict:** 6/7 PASS, 1 CONDITIONAL. Well-crafted epic with strong narrative and testable ACs.

| # | Question | Verdict |
|---|----------|---------|
| 1 | Goal specific enough to test? | PASS |
| 2 | AC testable at epic scale? | PASS |
| 3 | Non-goals explicit? | PASS |
| 4 | Dependencies identified with owners/dates? | CONDITIONAL |
| 5 | Success metrics measurable? | CONDITIONAL |
| 6 | AI agent can implement without guessing? | PASS |
| 7 | Narrative compelling? | PASS |

**Gaps identified and resolved:**

| # | Issue | Resolution |
|---|-------|------------|
| 1 | "Bad plan" has no operational definition | **Resolved** — Definition added to metrics table: "QA fails on first attempt due to uncovered criteria or constraint violations" |
| 2 | Loopback reduction metric has no baseline | **Resolved** — Replaced with "Preflight-to-QA pass correlation" (automatically measurable) |
| 3 | Epics 15/24/25 listed as blockers but unclear if hard | **Resolved** — Clarified as scheduling preferences, not hard blockers |
| 4 | `PreflightInput.plan_steps` type unspecified | **Resolved** — Specified as `list[str]` in AC 5 |
| 5 | Missing `WorkflowStep.PREFLIGHT` enum entry | **Resolved** — Added to AC 6 with retry policy |

**Status: All gaps resolved. Ready to commit.**
