---
name: session-plan
description: Review open epics and create a Helm session plan with Meridian review
user-invocable: true
context: fork
argument-hint: "[optional: focus area or epic number]"
allowed-tools: Read, Glob, Grep, Write, Edit, Agent
---

Create a session plan by running the full persona chain: evaluate open epics, invoke Helm for planning, then Meridian for review.

## Process (follow in order)

### Step 1: Discover Open Epics

1. Read `docs/TAPPS_HANDOFF.md` for current project status
2. Glob `docs/epics/epic-*.md` and read each epic file
3. Classify each epic as: **Complete**, **Approved** (Meridian passed), or **Draft** (awaiting review)
4. Read any existing sprint plans in `docs/sprints/` to avoid re-planning completed work
5. Check stories in `docs/epics/stories/` for any that are already implemented

### Step 2: Summarize Findings

Present a concise table to the user:

| Epic | Title | Status | Stories Done / Total | Recommendation |
|------|-------|--------|---------------------|----------------|

Recommendations should be one of:
- **Build now** — Meridian-approved, ready to implement
- **Review first** — Draft needs Meridian review before planning
- **Defer** — Not on critical path or has unmet prerequisites
- **Complete** — Already delivered

### Step 3: Invoke Helm (Sprint Planning)

Use the `helm-planner` agent to create a session plan for the highest-priority approved epic(s). If $ARGUMENTS specifies an epic number or focus area, plan that instead.

Helm must read:
- `thestudioarc/personas/helm-planner-dev-manager.md` (persona definition)
- The target epic file and all its story files
- Any prior sprint plans or retros for context

Helm produces a plan at `docs/sprints/sprint-epic{N}-s{sprint}.md` with:
1. **Sprint Goal** — Testable format: objective + test + constraint
2. **Ordered Backlog** — With rationale for sequence
3. **Dependency List** — External and internal, with status
4. **Estimation Notes** — Reasoning and unknowns
5. **Capacity Allocation** — With buffer (never 100%)
6. **Compressible Stories** — What gets cut if time runs short
7. **Retro Reference** — Prior retro actions or "first sprint for this workstream"

### Step 4: Invoke Meridian (Review)

Use the `meridian-reviewer` agent to run the 7-question plan review checklist.

Meridian must read:
- `thestudioarc/personas/meridian-vp-success.md` (persona definition)
- `thestudioarc/personas/meridian-review-checklist.md` (the checklist)
- The sprint plan from Step 3
- The parent epic

Meridian gives: COMMITTABLE, CONDITIONAL PASS, or REJECTED.

### Step 5: Fix and Commit

- If CONDITIONAL PASS: fix the identified gaps in the plan, update status to COMMITTED
- If REJECTED: report the rejection reasons to the user for discussion
- If COMMITTABLE: update plan status to COMMITTED

### Step 6: Present the Session Plan

Show the user:
- The committed sprint goal
- Ordered work items with estimates
- Critical path and dependencies
- What to cut if time runs short
- Ask if they want to start building
