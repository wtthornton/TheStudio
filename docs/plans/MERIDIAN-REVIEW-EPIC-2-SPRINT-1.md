# Meridian Review — Epic 2 Sprint 1 Plan

**Reviewer:** Meridian (VP Success)
**Date:** 2026-03-06
**Plan:** `docs/plans/epic-2-sprint-1-plan.md`
**Checklist:** `thestudioarc/personas/meridian-review-checklist.md`

---

## Plan Review — 7 Questions

### 1. Testable sprint goal — Objective + how we'll verify?

**Pass.**

Sprint goal is testable:
- **Objective:** Complexity Index computed on TaskPackets; Outcome Ingestor normalizes and attributes; Reputation Engine stores weights; Router consumes weights.
- **Test:** 5 specific criteria, each with test case counts (6+, 10+, 8+, 8+) and code quality gates (ruff, mypy, migrations).

The goal ends with "so that Sprint 2 can build quarantine/replay operations and Admin UI against a working learning loop" — clear handoff condition.

---

### 2. Single order of work — First → second → … and what's explicitly out?

**Pass.**

Order is explicit:
1. Phase A (week 1): 2.1 Complexity Index
2. Phase B (weeks 1–2): 2.2 Outcome Ingestor (depends on 2.1)
3. Phase C (weeks 2–3): 2.5 Reputation Engine → 2.7 Router

"What's Explicitly Out This Sprint" table lists 13 items with "Why" and "When" columns. No ambiguity.

---

### 3. Dependencies confirmed — Visible on board?

**Pass.**

Dependencies table shows:
- 2.1 → Epic 1 Context Manager (Complete)
- 2.2 → 2.1 (must land first)
- 2.5 → 2.2 indicator format
- 2.7 → 2.5 query API

Cross-dependency risk is identified: "Linear chain. Mitigation: 2.5 can mock indicators to start early."

**Note:** Dependencies are internal to the sprint. No external team dependencies.

---

### 4. Estimation reasoning — What changed, what's still unknown?

**Pass.**

Each story has:
- Points and size (M or L)
- "Unknowns / risks" section with specific mitigations:
  - 2.1: "Formula may need tuning" → store dimensions in jsonb
  - 2.2: "Provenance links may be incomplete" → treat as low confidence
  - 2.5: "Learning rate may need tuning" → make configurable
  - 2.7: "No weights for new experts" → treat as neutral

Total: 26 points in 3 weeks, 80% commitment with 20% buffer.

---

### 5. Retro actions — From last time, how do we know they're done?

**Pass.**

Retro Actions table references 4 actions from Epic 0/1:
- mypy in edit loop → constraint in DoD
- Integration tests against real DB → DoD for each story
- Estimate infra as real story → "No new infrastructure in Sprint 1; tables are part of 2.5"
- One commit per story → enforced in constraint

Each action has "How addressed in this sprint" column.

---

### 6. Capacity and buffer — Plan within it?

**Pass.**

- Commitment: 80% (26 points of 32 available)
- Buffer: 20% for integration issues, bugfixes, unknowns
- 4 stories total: 5 + 8 + 8 + 5 = 26 points

Timeline shows parallel work for 2 developers or sequential for 1 developer. Both fit in 3 weeks.

---

### 7. Async-readable — Can someone understand "done" and what's blocked?

**Pass.**

The plan includes:
- Sprint Goal with explicit test criteria
- Per-story Definition of Done with checkboxes
- Dependencies table
- "What's Explicitly Out" table
- Timeline for 1 or 2 developers
- Sprint Definition of Done (7 items including "Learning loop verified")

An agent reading this plan can:
1. Know what "done" means for each story
2. Know the order and dependencies
3. Know what's out of scope
4. Know the verification criteria for the sprint

---

## Red Flags Check

| Red Flag | Present? |
|----------|----------|
| Wish not goal | No — goal is testable with specific criteria |
| Everything P0 | No — 4 stories with clear priority order |
| Hidden dependencies | No — dependency table explicit |
| Estimate without reasoning | No — unknowns/risks documented per story |
| Retro without action | No — actions table with "how addressed" |
| "The agent will handle it" | No — DoDs are specific and testable |
| No capacity/buffer | No — 80/20 split documented |

---

## Verdict

**PASS** — Sprint 1 plan is approved for execution.

**No watch items.** The plan is well-structured:
- Learning loop focus aligns with Meridian's recommendation
- Dependencies are linear and manageable
- Buffer is realistic
- DoDs are testable

**Handoff to execution:** Stories 2.1, 2.2, 2.5, 2.7 are sprint-ready. Begin with 2.1 Complexity Index.

---

*Meridian — VP Success. Plan approved. Execute.*
