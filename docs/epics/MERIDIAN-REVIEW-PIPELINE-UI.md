# Meridian Review: Pipeline UI Epics 34-39

> **Reviewer:** Meridian (VP of Success)
> **Date:** 2026-03-20
> **Scope:** Epics 34, 35, 36, 37, 38, 39 (Pipeline UI Phases 0-5)
> **Prior Review:** Design suite (docs/design/00-06) FAILED on 2026-03-20 due to missing backend story tracking
> **This Review:** Evaluates the 6 epics written to address those gaps

---

## Executive Summary

These six epics represent a massive improvement over the raw design docs I reviewed earlier today. The backend stories from `docs/design/06-BACKEND-REQUIREMENTS.md` are now fully tracked -- all 83 backend stories (B-0.1 through B-5.8) appear in at least one epic with explicit references. Story-level acceptance criteria are testable. Non-goals are explicit. Dependencies are identified.

That said, there are systemic problems that cut across all six epics:

1. **The aggregate timeline is 37-47 weeks for a solo developer with zero buffer.** That is 9-12 months of continuous, uninterrupted delivery. No one delivers 9 months of work without interruptions, bugs in production, or scope discoveries.

2. **Several success metrics are unmeasurable** with existing or planned instrumentation ("developer identifies X within N seconds" requires a human with a stopwatch, not a CI gate).

3. **No epic defines what happens if Phase 0 fails.** The SSE-over-NATS bridge is the load-bearing assumption of the entire initiative. If it does not work, 258 downstream stories are waste. Phase 0 needs an explicit kill criterion.

4. **Cost of the initiative itself is never stated.** At ~$5/eval-run and potentially hundreds of LLM calls for implementation, what is the budget for building this dashboard? The irony of building a budget dashboard without a budget for the build is not lost on me.

**Verdicts:**

| Epic | Verdict |
|------|---------|
| Epic 34 (Phase 0) | **CONDITIONAL PASS** |
| Epic 35 (Phase 1) | **CONDITIONAL PASS** |
| Epic 36 (Phase 2) | **CONDITIONAL PASS** |
| Epic 37 (Phase 3) | **CONDITIONAL PASS** |
| Epic 38 (Phase 4) | **CONDITIONAL PASS** |
| Epic 39 (Phase 5) | **CONDITIONAL PASS** |

No epic fails outright. Every epic has gaps that must be fixed before commit. Details follow.

---

## Cross-Epic Analysis

### Backend Story Coverage: PASS

All 83 backend stories from `docs/design/06-BACKEND-REQUIREMENTS.md` are accounted for:

| Phase | Backend Ref Range | Stories in Epic | Coverage |
|-------|-------------------|-----------------|----------|
| 0 | B-0.1 through B-0.7 | Epic 34: 7 | 7/7 |
| 1 | B-1.1 through B-1.14 | Epic 35: 14 | 14/14 |
| 2 | B-2.1 through B-2.18 | Epic 36: 18 (across 12 stories, some consolidated) | 18/18 |
| 3 | B-3.1 through B-3.24 | Epic 37: 24 (across 18 stories, some consolidated) | 24/24 |
| 4 | B-4.1 through B-4.12 | Epic 38: 12 (across 14 stories) | 12/12 |
| 5 | B-5.1 through B-5.8 | Epic 39: 8 (across 10 stories) | 8/8 |

This was the primary failure in the design doc review. It is now fixed. Credit where due.

### Story ID Uniqueness: PASS

- Epic 34: B-0.1 through B-0.7, F-0.1 through F-0.3 (10 stories)
- Epic 35: S1.B1-S1.B5, S1.F1-S1.F9, S2.B1-S2.B5, S2.F1-S2.F12, S3.B1-S3.B3, S3.F1-S3.F11, S4.B1, S4.F1-S4.F14 (60 stories)
- Epic 36: 36.1 through 36.20 (20 stories)
- Epic 37: 37.1 through 37.28 (28 stories)
- Epic 38: 38.1 through 38.27 (27 stories)
- Epic 39: 39.1 through 39.21 (21 stories)

No ID collisions. No duplicated stories across epics. **Total: 166 stories.**

The design doc claims 268 stories. The gap (102 stories) is because the design doc counted frontend-only stories that are now consolidated or subsumed into the epic story maps. This is fine -- consolidation during epic creation is normal -- but the 268 number should be updated in `docs/design/06-BACKEND-REQUIREMENTS.md` Section 4 to avoid confusion.

### Cross-Epic Dependencies: Gap

Dependencies between epics are stated but never dated. Every epic says "Phase 0 must be complete" but none says "Phase 0 must be complete by [date] or this epic's start slips to [date]." For a solo developer executing sequentially, this is less of a scheduling risk (there is only one person), but it means there is no calendar-anchored commitment anywhere. If Phase 0 takes 5 weeks instead of 3, the entire initiative silently slips by 2 weeks with no trigger for re-evaluation.

**Required fix:** Add a calendar target (even approximate) for Phase 0 completion. Define a decision point: "If Phase 0 is not complete by [date], re-evaluate the initiative scope."

### Aggregate Timeline: RED FLAG

| Epic | Stated Duration |
|------|----------------|
| 34 (Phase 0) | 2-3 weeks |
| 35 (Phase 1) | 8-10 weeks |
| 36 (Phase 2) | 8-10 weeks |
| 37 (Phase 3) | 10-12 weeks |
| 38 (Phase 4) | 5-7 weeks |
| 39 (Phase 5) | 4-5 weeks |
| **Total** | **37-47 weeks** |

That is **9-12 months** of uninterrupted solo development. No buffer for:
- Production bugs in existing pipeline
- Dependency upgrades (React 19, Temporal SDK, nats-py)
- Scope discoveries during implementation
- Vacations, illness, context switching to other epics (30-33 just closed)
- The inevitable "this Temporal signal handler does not work as expected" investigation

At 80% capacity with 20% buffer (which is the standard Helm plans against), this becomes **46-59 weeks** -- over a year.

**Required fix across all epics:** Either (a) define explicit MVP cut-lines per epic so the initiative can ship value at Phase 1 or Phase 2 and stop if needed, or (b) acknowledge the 12+ month timeline and get explicit buy-in. Epic 35 already marks MVP stories, which is good. Epics 37, 38, and 39 do not have MVP marks on individual stories. Epic 36 defines a textual MVP ("Slice 1 + Slice 2") but does not mark stories.

---

## Epic 34: Phase 0 -- SSE Proof-of-Concept

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "A browser displays live pipeline stage transitions from a real Temporal workflow" -- binary, testable. The end-to-end validation in Slice 6 is a concrete test script. |
| 2 | Acceptance criteria testable at epic scale? | **Pass** | All 7 ACs are specific (HTTP status codes, header values, latency targets, event payloads). AC 3 has an explicit integration test description. |
| 3 | Non-goals explicit? | **Pass** | 10 non-goals listed. Clear boundaries: no Radix UI, no Playwright, no REST endpoints, no mobile. Well done. |
| 4 | Dependencies with owners and dates? | **Gap** | Dependencies listed (NATS, Temporal, Node.js 22+) but no dates. Node.js 22+ is a new dependency for the project -- is it installed in CI? The `.github/workflows/ci.yml` does not set up Node.js. Who adds that? |
| 5 | Success metrics measurable? | **Pass** | SSE latency (<200ms p95), reconnection gap (0 missed events), stage coverage (9/9), build size (<50KB). All measurable, all automatable. |
| 6 | AI-implementable? | **Pass** | File paths, endpoint signatures, event payload shapes, and test file locations are specified per story. An AI agent could implement from this. |
| 7 | Narrative compelling? | **Pass** | The "answer one question before committing to 268 stories" framing is exactly right. This is a validation gate. |

### Issues to Fix

1. **No kill criterion.** What if SSE-over-NATS latency is 2 seconds instead of 200ms? What if NATS JetStream replay does not work reliably? This epic should define: "If [condition], we stop the initiative and evaluate alternatives (WebSocket, polling, etc.)." Without this, the epic is a PoC that cannot fail, which means it is not a real PoC.

2. **Node.js 22 in CI.** The CI pipeline (`.github/workflows/ci.yml`) has 3 jobs (lint, test, integration). None sets up Node.js. Story F-0.1 creates a frontend project but does not add CI for it. Add a story or subtask: "Add Node.js setup and `npm run typecheck` + `npm run test` to CI."

3. **B-0.6 scope mismatch.** The backend requirements doc describes B-0.6 as "Create minimal test page that connects to SSE." The epic's Story B-0.6 is "FastAPI Static Mount for Frontend" -- a different, larger scope. The test page is subsumed by F-0.3. This is fine functionally but the backend ref should be corrected or noted.

4. **Story count discrepancy.** The Definition of Done says "All 10 stories (B-0.1 through B-0.7 + F-0.1 through F-0.3)" but B-0.1 through B-0.7 is 7 stories + F-0.1 through F-0.3 is 3 stories = 10 total. That math checks out, but the story IDs in the epic skip from B-0.5 to B-0.7 then B-0.6 (Slice 5 reverses order). Not wrong, but confusing -- reorder Slice 5 to B-0.6 then B-0.7 for clarity.

---

## Epic 35: Phase 1 -- Pipeline Visibility

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "Developers see every TaskPacket flow through the pipeline in real time" is supported by 10 specific ACs. |
| 2 | Acceptance criteria testable at epic scale? | **Gap** | AC 5 (Activity Stream) says "structured entries: file reads, file edits (with 3-line diff preview), searches, test runs, shell commands, agent reasoning, and LLM calls." The agent framework (`src/agent/framework.py`) does not emit any of these today. Instrumenting the agent to emit structured events for every tool call is a major refactoring risk. The AC treats this as a backend story (S3.B1) but the estimation is "L" with no spike or prototype. This is the single riskiest story in the entire 166-story initiative. |
| 3 | Non-goals explicit? | **Pass** | 11 non-goals. Planning, steering, budget governance, keyboard nav, animations, and timeline scrubbing are all explicitly out. |
| 4 | Dependencies with owners and dates? | **Gap** | Phase 0 is a "hard blocker" but has no target date. No contingency plan if Phase 0 is late. |
| 5 | Success metrics measurable? | **Gap** | "Developer identifies current stage of any TaskPacket in < 3 seconds" -- how? Manual timing test with a stopwatch? This is not automatable and not repeatable. Same for "Developer can identify what the agent is currently doing within 5 seconds." Restate these as: "Pipeline Rail renders current stage status for all active TaskPackets on initial page load" (measurable via Playwright). |
| 6 | AI-implementable? | **Pass** | Stories specify files to create/modify, endpoint signatures, event payload shapes. Backend refs map to doc 06. |
| 7 | Narrative compelling? | **Pass** | The competitive framing (Devin, Factory, Codegen) is effective. "The pipeline is the differentiator -- but only if the developer can see it" is a strong hook. |

### Issues to Fix

1. **Activity event emission (S3.B1) needs a spike.** This is rated "L" but it requires instrumenting every tool call in `src/agent/framework.py` to emit structured NATS events. The agent framework was not designed for observability emission. Add a 1-day spike story before S3.B1: "Prototype activity event emission for 2 tool types (file_read, test_run). Validate that NATS publish does not slow agent execution by >5%." If the spike fails, the Activity Stream is rescoped to show only stage-level events (enter/exit/gate), not tool-level events.

2. **60 stories in 8-10 weeks = 6-7.5 stories/week.** That is more than one story per working day for 2+ months. The 30 MVP stories in 8-10 weeks is 3-3.75/week, which is more reasonable. State clearly: "MVP scope is 30 stories in 8-10 weeks. The remaining 30 polish stories are a separate sprint/epic."

3. **Success metrics need automation.** Replace "developer identifies X within N seconds" with Playwright-testable criteria: "Pipeline Rail renders with correct stage status data within 2 seconds of page load (Playwright test)." The intent is the same; the measurement is real.

4. **SSE event vocabulary inconsistency.** The Constraints section references `pipeline.stage_enter` (underscore) but Phase 0 AC 4 uses `pipeline.stage.enter` (dot). Pick one. The NATS subject hierarchy should use dots (NATS convention). Update the Phase 1 Constraints section to match.

---

## Epic 36: Phase 2 -- Planning Experience

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "Developers plan with confidence before the pipeline writes a single line of code." Supported by concrete ACs: triage queue holds issues, intent review pauses workflow, routing review pauses workflow. |
| 2 | Acceptance criteria testable at epic scale? | **Pass** | 11 ACs, all specific. AC 5 (Intent wait point) describes the exact Temporal signal flow. AC 9 (Routing preview) defines the override contract. |
| 3 | Non-goals explicit? | **Pass** | 8 non-goals. GitHub Projects sync, drag-and-drop, priority matrix, rich editor, keyboard shortcuts all explicitly out. |
| 4 | Dependencies with owners and dates? | **Gap** | Dependency table lists Phase 0 + Phase 1 as "Not yet built" with no target dates. The "Impact if Missing" column is good (describes fallback behavior), but there is no decision point: "If Phase 1 is not complete by [date], defer Slice 4 (Backlog Board)." |
| 5 | Success metrics measurable? | **Gap** | "Intent review rate: 80%+" is measurable via database query -- good. "Rework reduction: 20% fewer loopbacks" requires a baseline measurement that does not exist yet. How many loopbacks happen today? Is the baseline tracked anywhere? If not, this metric cannot be evaluated. "Planning stage dwell time: Median < 5 minutes" is measurable but the target is arbitrary -- what is it based on? |
| 6 | AI-implementable? | **Pass** | Stories specify files, endpoints, Pydantic schemas, and Temporal signal names. The existing `approve_publish` signal pattern is cited as the template for new wait points. |
| 7 | Narrative compelling? | **Pass** | "The developer's first real interaction with the system's understanding of a task happens when a draft PR appears. If the Intent Specification was wrong, the entire pipeline ran for nothing." Strong motivation. |

### Issues to Fix

1. **Baseline for "20% fewer loopbacks" metric.** Add a prerequisite: "Before Phase 2 begins, measure and record the current loopback rate (loopbacks per TaskPacket, averaged over last 30 days). Store this as the baseline in a persistent artifact." Without a baseline, the 20% target is untestable.

2. **Story 36.4 (Context Pre-Scan) is underspecified.** It says "lightweight synchronous pre-scan" but does not define what inputs it uses. The issue body is available, but file impact analysis requires cloning/scanning the repo. Is this a heuristic based on issue text, or does it actually scan files? If it scans files, "synchronous" is wrong -- it could take 30+ seconds. Define the boundary: "Pre-scan uses issue title, body, and labels only. No repository file access. Complexity hint is based on keyword heuristics and label-to-category mapping."

3. **Story 36.8 (Temporal wait point) needs a rollback plan.** The risk table says "incorrect signal/timer implementation could deadlock workflows." What is the rollback if a deployed wait point deadlocks production workflows? Add: "The `INTENT_REVIEW_ENABLED` flag defaults to false. If a deadlock is detected (workflow stuck in intent_review state for >30 minutes with no pending signal), emit an alert and auto-approve."

4. **Duration estimate: 8-10 weeks.** Epic 36 has 20 stories. At 2-2.5 stories/week, 8-10 weeks is reasonable for this scope. However, Story 36.8 (Temporal wait point) and Story 36.14 (Routing wait point) are both high-risk and both sized as single stories. Consider breaking each into: (a) signal handler implementation, (b) API endpoint, (c) integration test. This makes risk more visible in the plan.

---

## Epic 37: Phase 3 -- Interactive Controls

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "Developers can pause, steer, budget, and trust-configure the pipeline without touching code." Each verb maps to a concrete AC. |
| 2 | Acceptance criteria testable at epic scale? | **Gap** | AC 4 (Trust Tier Rule Engine) says "conditions joined by AND" and "first match wins." What happens with conflicting rules? Is there validation that rules do not overlap in contradictory ways? The AC does not address rule conflict detection. |
| 3 | Non-goals explicit? | **Pass** | 8 non-goals. Reputation dashboard, drag-to-reorder, custom date range, notification preferences, pipeline rail context menu, hold-at-gate all explicitly out. |
| 4 | Dependencies with owners and dates? | **Gap** | Dependencies table has "Required By" column pointing to slices, but no calendar dates. Phase 1 `pipeline.cost_update` events "must be complete" for Slice 4, but what if Phase 1 delivers only MVP (30 stories) and `pipeline.cost_update` (S1.B5) is in MVP but the data is unreliable? |
| 5 | Success metrics measurable? | **Gap** | "Time-to-intervention: < 10 seconds from intent to confirmed action" -- measurable via UI interaction timing, good. "Trust tier adoption: at least 1 custom rule created within 2 weeks" -- this is a usage metric, not a quality metric. It tells you someone clicked a button, not that the feature works correctly. Add: "Trust tier rule evaluation produces the correct tier for 100% of test cases in the integration test suite." |
| 6 | AI-implementable? | **Gap** | Story 37.13 says "existing expert-level tiers (`src/reputation/tiers.py`) are not modified" but B-3.5 in the backend requirements doc says "Map design trust tiers to codebase tiers -- reconcile or extend." These contradict. The epic says "parallel concept, not modified." The backend doc says "reconcile." Which is it? An AI agent implementing Story 37.13 will not know whether to modify `tiers.py` or leave it alone. |
| 7 | Narrative compelling? | **Pass** | "The only option is to wait, watch, and hope" followed by the budget risk argument is effective. Citing eval test costs (~$5/run) makes the budget dashboard concrete. |

### Issues to Fix

1. **B-3.5 reconciliation contradiction.** Story 37.13 must explicitly state the reconciliation outcome. My recommendation: "The task-level trust tier (Observe/Suggest/Execute) is a NEW field on TaskPacket. It does NOT replace or modify the expert-level reputation tiers (Shadow/Probation/Trusted). The two systems operate independently. `src/reputation/tiers.py` is not modified. B-3.5 is satisfied by documenting this parallel-system design in a code comment and updating `docs/design/06-BACKEND-REQUIREMENTS.md` Section 6." State this explicitly in the story AC.

2. **Redirect signal complexity (Story 37.8).** This is the hardest story in the entire initiative. Temporal does not support "jump to step N" -- the epic acknowledges this in Risk R2 and proposes modeling it as a flag + loop re-entry. But the story is sized as a single "L" story. This should be 2-3 stories: (a) redirect flag and workflow loop modification, (b) state cleanup (discard downstream artifacts), (c) integration tests for redirect at every stage boundary. A single story that says "test that redirects from Implement to Router" is insufficient -- what about redirecting from QA to Intent? From Verify to Context?

3. **Budget-pause atomicity (Story 37.21, Risk R4).** The epic says "iterate through active workflow IDs, send pause to each, log failures, and retry." What is the retry policy? How many retries? What if one workflow is in a Temporal server that is temporarily unreachable? Define: max 3 retries with 5-second backoff, then log as partial failure and emit a notification.

4. **No MVP markers on stories.** Epic 35 marks MVP stories. Epic 37 does not. For a 28-story, 10-12 week epic, this is a problem. Define: "MVP is Slice 1 (Steering) + Slice 4 (Budget Dashboard). Slices 2, 3, and 5 are post-MVP." Or pick a different cut. But pick one.

5. **10-12 weeks timeline.** 28 stories in 10-12 weeks = 2.3-2.8 stories/week. Reasonable per-story, but this epic contains the two highest-risk stories in the initiative (redirect signal, budget-pause automation). Add 2 weeks of buffer explicitly.

---

## Epic 38: Phase 4 -- GitHub Integration

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "Make GitHub the natural co-pilot for every pipeline run." Each sub-capability (import, evidence, sync, comments, bridge) has its own AC. |
| 2 | Acceptance criteria testable at epic scale? | **Pass** | AC-1 through AC-8 are specific. AC-8 (no regression) explicitly names the existing webhook path and feature flag. |
| 3 | Non-goals explicit? | **Pass** | 7 non-goals. Diff annotation by expert, auto-merge, mobile, issue creation, notification integrations all out. |
| 4 | Dependencies with owners and dates? | **Gap** | Phase 2 TRIAGE status is listed as "Optional" with a runtime guard fallback. Good defensive design. But the `ProjectsV2Client` (Epic 29) is listed as "Implemented, feature-flagged off." Is it tested? The epic does not mention the current test coverage of `projects_client.py`. If it has zero tests, Slice 3 starts with unknown reliability. |
| 5 | Success metrics measurable? | **Gap** | "PR evidence engagement: Reviewers spend 2x more time on Evidence Explorer tabs than on raw GitHub PR evidence comment." How is this measured? The epic says "Dashboard interaction logs (tab switches, time-on-page)" but no story creates this logging infrastructure. This metric requires analytics instrumentation that is not scoped in any epic. Either add a story for interaction logging or replace this metric. Similarly, "Pipeline comment usefulness: Developers report via feedback" is qualitative, not measurable. |
| 6 | AI-implementable? | **Pass** | Stories specify files, endpoints, and Pydantic models. The `EvidencePayload` model is called out as a prerequisite before frontend work. |
| 7 | Narrative compelling? | **Pass** | "If TheStudio's intelligence stays locked inside its own dashboard, adoption stalls" is the right argument. GitHub is where developers live. |

### Issues to Fix

1. **Replace unmeasurable metrics.** "Reviewers spend 2x more time" requires interaction logging that no story builds. Replace with: "Evidence Explorer renders all 5 tabs (Evidence, Diff, Intent, Gates, Cost) with data within 2 seconds of page load for any published TaskPacket." "Pipeline comment usefulness" should become: "100% of TaskPackets with linked GitHub issues have a pipeline comment by the time they reach Publish stage (when comments are enabled)."

2. **Feedback loop guard (Story 38.19) needs a test scenario.** The story says "tag outbound mutations, detect and skip inbound webhooks." The integration test (38.20) should explicitly test: "TheStudio pushes status update -> GitHub fires webhook -> TheStudio receives webhook -> TheStudio skips it (no re-processing)." If this test is not in 38.20's scope, add it.

3. **GitHub API token scopes.** Risk R1 says "validate token scopes on project connect." This should be a story, not just a risk mitigation. Add explicit AC to Story 38.13: "If the token lacks `project` scope, return a 403 with a message explaining which scopes are needed."

4. **Story count: 27 in 5-7 weeks.** That is 3.9-5.4 stories/week, the highest velocity assumption of any epic. Several stories are sized "M" and involve GitHub API integration with rate limits, GraphQL mutations, and webhook handling. This pace is aggressive. Recommend 7-9 weeks or scope reduction to Slices 1-2 (MVP) + Slice 4 (webhook bridge), deferring Slice 3 (Projects sync) as post-MVP.

---

## Epic 39: Phase 5 -- Analytics & Learning

**Verdict: CONDITIONAL PASS**

### 7-Question Review

| # | Question | Verdict | Detail |
|---|----------|---------|--------|
| 1 | Goal testable? | **Pass** | "Pipeline performance becomes visible: developers see what works, what fails, and what drifts." Each visibility dimension maps to an AC. |
| 2 | Acceptance criteria testable at epic scale? | **Pass** | ACs 1-8 are specific. AC 1 defines load time target (<2 seconds). AC 2 defines the visual highlight. AC 7 defines the drift window (14 days). |
| 3 | Non-goals explicit? | **Pass** | 6 non-goals. Predictive analytics, custom reports, CSV export, real-time streaming analytics, multi-repo, alerting integrations all out. |
| 4 | Dependencies with owners and dates? | **Gap** | Dependency table lists 7 dependencies from Phases 0-4. No dates. No contingency. What if Phase 4 (GitHub webhooks for PR merge status) is not complete? Merge rate calculations (AC 3, AC 8) would show null. Add: "If Phase 4 is not complete, merge rate columns show 'Data not available' and are excluded from summary cards." |
| 5 | Success metrics measurable? | **Pass** | "Dashboard load time: all analytics views render in under 2 seconds" (Playwright). "API response time: all endpoints respond in under 1 second for 10,000 TaskPackets" (pytest benchmark). These are automatable. |
| 6 | AI-implementable? | **Pass** | Stories specify exact endpoint paths, query logic descriptions, and component file paths. |
| 7 | Narrative compelling? | **Pass** | "Trust is the product" is a strong framing. The argument that invisible reputation/outcome systems cannot build developer trust is correct. |

### Issues to Fix

1. **Insufficient data risk (R1) needs a concrete gate.** The epic says "require minimum 10 completed tasks before rendering trend lines." Where is this enforced? Add explicit AC to Story 39.6 (Throughput chart) and 39.7 (Bottleneck bars): "If fewer than 10 completed tasks exist in the selected period, show an empty state with 'Need at least 10 completed tasks for meaningful analytics' message."

2. **Drift score computation (Story 39.15) is a black box.** AC 7 says the drift score considers "gate pass rates, expert weight trends, cost trends, and loopback rates." What are the weights? What is "normal range"? Is this a z-score? A percentile? A hardcoded threshold? The story needs to define the computation or cite a specific section of the design doc that does. If the computation is not defined anywhere, add a spike: "Define drift score formula with synthetic test data before implementing."

3. **Chart library not specified.** The Constraints say "use whatever was established in Phase 3 (cost dashboard charts)." Phase 3 Story 37.22 says "Chart.js or similar." Neither epic commits to a specific library. This means the first developer to implement a chart picks the library for the entire initiative. Add to Epic 37, Story 37.22: "Select and document the chart library in `frontend/package.json`. Candidates: Chart.js, Recharts, or Nivo. Decision recorded in a code comment in the chart component."

4. **4-5 weeks for 21 stories.** 4.2-5.25 stories/week. Several backend stories require aggregation queries against tables that may not have indexes. Story 39.1 (throughput) and 39.2 (bottleneck) depend on B-1.12 (stage timing), which depends on Phase 1 being complete. If the stage timing data has nulls for historical records (as Epic 35 S1.B1 notes), the aggregation queries need to handle them. Add explicit AC: "Queries handle NULL stage timestamps gracefully (exclude records with missing data, do not error)."

---

## Red Flags (Cross-Epic)

| # | Red Flag | Epics Affected | Severity |
|---|----------|----------------|----------|
| RF-1 | **No kill criterion for Phase 0.** If SSE-over-NATS does not work, there is no defined exit. | 34, all downstream | High |
| RF-2 | **37-47 week timeline with zero buffer.** Solo developer, sequential execution, no slack. | All | High |
| RF-3 | **Unmeasurable success metrics.** "Developer identifies X within N seconds" appears in Epics 35, 37, 38. | 35, 37, 38 | Medium |
| RF-4 | **No budget for building the budget dashboard.** The initiative itself has no stated cost budget. At ~$5/eval and potentially hundreds of AI-assisted implementation sessions, this could cost $500-2000+ in API calls alone. | All | Medium |
| RF-5 | **B-3.5 reconciliation contradicts Epic 37 Story 37.13.** Backend doc says "reconcile or extend." Epic says "not modified." | 37 | Medium |
| RF-6 | **SSE event naming inconsistency.** `pipeline.stage_enter` (underscore) vs `pipeline.stage.enter` (dot) appears in Epic 35 Constraints vs Epic 34 AC 4. | 34, 35 | Low |
| RF-7 | **Node.js CI setup missing.** No epic adds Node.js to the CI pipeline. Frontend code will not be tested in CI. | 34 | Medium |

---

## Required Fixes Before Commit

These must be addressed before any epic is treated as committed work:

### Must Fix (All Epics)

1. **Add a kill criterion to Epic 34.** Define: "If the SSE endpoint cannot deliver events to a browser within 500ms p95 after 1 week of development, evaluate WebSocket alternative. If no viable real-time transport works within 2 weeks, descope Phases 1-5 to polling-based architecture."

2. **Add MVP cut-lines to Epics 37, 38, and 39.** Every epic must define which stories are MVP and which are post-MVP. The initiative must be shippable at Phase 0 + Phase 1 MVP + Phase 2 MVP. Phases 3-5 are valuable but not existential.

3. **Replace all "developer identifies X within N seconds" metrics** with Playwright-automatable equivalents across Epics 35, 37, and 38.

4. **Add a CI story to Epic 34** for Node.js setup, `npm run typecheck`, and `npm run test` in the CI pipeline.

5. **Resolve B-3.5 contradiction in Epic 37** by explicitly stating the reconciliation outcome in Story 37.13.

### Should Fix (Per-Epic)

6. **Epic 34:** Add calendar target for completion. Define decision point for initiative re-evaluation.
7. **Epic 35:** Add activity event emission spike before S3.B1. Fix SSE event naming to use dots consistently.
8. **Epic 36:** Define loopback baseline measurement. Specify pre-scan input boundary. Add rollback plan for wait point deadlock.
9. **Epic 37:** Break Story 37.8 (redirect) into 2-3 stories. Define budget-pause retry policy. Add 2 weeks buffer.
10. **Epic 38:** Replace "2x engagement" metric. Add token scope validation as explicit AC. Reduce velocity assumption.
11. **Epic 39:** Define drift score formula or add spike. Specify chart library in Epic 37. Add NULL-handling AC for aggregation queries.

---

## What I Got Wrong Last Time

My previous review of the design suite flagged ~50-70 untracked backend stories. The actual count turned out to be 83 (from `docs/design/06-BACKEND-REQUIREMENTS.md`). All 83 are now tracked in these epics. The systematic gap I identified has been closed.

The design suite review also flagged missing MVP criteria. Epics 34 and 35 now have explicit MVP markers. Epics 36-39 still need them.

---

## Final Assessment

These are well-crafted epics. The story-level detail is exceptional -- file paths, endpoint signatures, Pydantic models, test file locations. The non-goals are explicit. The risks are identified with real mitigations. The backend story coverage is complete.

The problems are systemic, not per-epic: an unrealistic aggregate timeline, a handful of unmeasurable metrics, and a missing kill criterion for the foundational PoC. Fix those, and these epics are ready for Helm to plan against.

The single most important thing to get right is Phase 0. If SSE-over-NATS works, the initiative is viable. If it does not, 166 stories are waste. Protect Phase 0 with a kill criterion and a time box. Everything else follows.

---

*Reviewed by Meridian, VP of Success. 2026-03-20.*
