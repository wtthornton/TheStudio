# TheStudio Kickoff Plan — Epic & Story Creation

**Date:** 2026-03-05
**Status:** DRAFT — Pending Meridian review
**Scope:** Use docs-mcp tooling + persona chain to produce Phase 0 epics, stories, and a sprint plan ready for execution.

---

## Chain order (from TEAM.md)

```
Strategy/OKRs --> Saga (epic) --> Meridian (epic review)
              --> Helm (plan)  --> Meridian (plan review)
              --> Execution
```

Every step below names the **persona**, the **docs-mcp tool** that produces the artifact, and the **Meridian checklist items** that gate commit.

---

## Step 1: Saga — Create Phase 0 Epic

**Persona:** Saga (epic creator)
**Tool:** `docs_generate_epic`
**Input source:** Phase 0 deliverables from `MERIDIAN-ROADMAP-AGGRESSIVE.md` (lines 46-73)

### Parameters

| Parameter | Value |
|-----------|-------|
| title | "Phase 0 — Foundation: Prove the Pipe" |
| number | 0 |
| goal | "One registered repo, Observe tier. Issue to TaskPacket to Context to Intent to Primary Agent to Verification to Publisher to draft PR with evidence. Prove the end-to-end pipe works." |
| motivation | "Validate the core architecture before investing in experts, QA agents, or multi-repo. Every later phase depends on this pipe being real and tested." |
| status | Proposed |
| priority | "P0 - Critical" |
| estimated_loe | "~8-10 weeks (1-2 developers)" |
| style | comprehensive |
| auto_populate | true |
| output_path | "docs/epics/epic-0-foundation.md" |

### Stories to generate (Step 2)

Each story maps to a Phase 0 deliverable. Use `docs_generate_story` for each:

| # | Story title | Size | Key files/components |
|---|------------|------|---------------------|
| 0.1 | Ingress: webhook receive, signature validation, dedupe | L | Webhook handler, delivery ID dedupe, Temporal workflow trigger |
| 0.2 | TaskPacket: minimal schema and persistence | M | TaskPacket model, DB migration, CRUD |
| 0.3 | Context Manager: enrich TaskPacket with scope and risk flags | L | Context enrichment, Service Context Pack stub, Complexity Index v0 |
| 0.4 | Intent Builder: produce Intent Specification | L | Intent model, goal/constraints/AC/non-goals extraction, persistence |
| 0.5 | Primary Agent: single Developer role, implement from intent | XL | Developer agent, tool allowlist, evidence bundle production |
| 0.6 | Verification Gate: repo-profile checks with loopback | L | Ruff/pytest runner, JetStream emit, loopback logic (max 2) |
| 0.7 | Publisher: draft PR with evidence comment | L | GitHub PR creation, evidence comment template, lifecycle labels, idempotency |
| 0.8 | Repo Profile: register one repo at Observe tier | M | Repo registration, tier config, required checks, tool allowlist |
| 0.9 | Observability: OpenTelemetry tracing with correlation_id | M | OTel setup, span instrumentation, correlation_id propagation |

### Acceptance criteria (epic-level, for Saga to include)

- [ ] 100% of test issues produce exactly one TaskPacket and one workflow run (no duplicates)
- [ ] 100% of published PRs have evidence comment and correct lifecycle labels
- [ ] Verification failure causes a loopback with evidence; no silent skip
- [ ] One runnable diagram or doc matches the as-built flow

### Non-goals (epic-level)

- No expert bench (Phase 1)
- No QA Agent (Phase 1)
- No Router/Assembler (Phase 1)
- No multi-repo (Phase 2)
- No reputation or learning loop (Phase 2)

### Risks

- Ingress dedupe wrong -> duplicate TaskPackets. Mitigation: replay tests with same delivery ID.
- Publisher creates duplicate PRs on retry. Mitigation: idempotency key + lookup-before-create.

---

## Step 2: Saga — Generate Stories

**Persona:** Saga
**Tool:** `docs_generate_story` (run 9 times, once per story above)
**Style:** comprehensive
**Criteria format:** checkbox

Each story uses the "As a / I want / So that" format with:
- Tasks broken into file-level work items
- Acceptance criteria (checkbox format, testable)
- Technical notes from architecture docs
- Dependencies on prior stories

### Execution command pattern

For each story, call `docs_generate_story` with:
- `epic_number`: 0
- `story_number`: 1-9
- `role`: "TheStudio platform"
- `style`: "comprehensive"
- `auto_populate`: true
- `output_path`: "docs/epics/stories/story-0.N-title.md"

---

## Step 3: Meridian — Review Epic

**Persona:** Meridian (reviewer)
**Tool:** Manual review against `meridian-review-checklist.md`
**Gate:** Epic MUST pass before Helm planning begins

### Checklist to run (Saga section — 7 items)

1. One measurable success metric — and how we read it
2. Top three risks — quality, performance, delivery; mitigations
3. Non-goals in writing
4. External dependencies — owner and date
5. Link to goal/OKR
6. Testable acceptance criteria — verifiable by human or script
7. AI-ready — Cursor/Claude can implement from this epic alone

### Red flags to watch for

- Vague success metrics
- "The AI will figure it out"
- Missing dependencies between stories (e.g., 0.5 depends on 0.4)
- Unrealistic scope for 8-10 weeks
- No test for "done" at story level

### Output format

Per checklist item: **Pass** or **Gap** (with what must be fixed).
List red flags. State what blocks commit.

### Iteration budget

- Max 3 review rounds before escalation (from MERIDIAN-TEAM-REVIEW-AND-OKRS.md)

---

## Step 4: Helm — Sprint Plan

**Persona:** Helm (planner)
**Tool:** Manual (Helm produces; no docs-mcp sprint planner yet)
**Input:** Approved epic + approved stories from Steps 1-3

### What Helm produces

1. **Testable sprint goal** — objective + test + constraint
2. **Single order of work** — story sequence with rationale
3. **Dependency map** — which stories block which
4. **Estimation reasoning** — per story, what's assumed, what's unknown
5. **Capacity and buffer** — 80% commitment / 20% buffer
6. **What's out** — explicit list of what won't fit Sprint 1

### Suggested story order (dependency-driven)

```
Sprint 1 (weeks 1-3):
  0.2 TaskPacket schema        (no deps, everything needs this)
  0.8 Repo Profile             (no deps, config foundation)
  0.1 Ingress                  (depends on 0.2)
  0.9 Observability            (parallel, no deps)

Sprint 2 (weeks 4-6):
  0.3 Context Manager          (depends on 0.2)
  0.4 Intent Builder           (depends on 0.3)
  0.6 Verification Gate        (depends on 0.8)

Sprint 3 (weeks 7-9):
  0.5 Primary Agent            (depends on 0.4, 0.6)
  0.7 Publisher                (depends on 0.5, 0.6)

Week 10: Integration test, diagram validation, buffer
```

---

## Step 5: Meridian — Review Plan

**Persona:** Meridian (reviewer)
**Tool:** Manual review against `meridian-review-checklist.md`
**Gate:** Plan MUST pass before execution begins

### Checklist to run (Helm section — 7 items)

1. Testable sprint goal — objective + verification method
2. Single order of work — first to last, what's out
3. Dependencies confirmed — visible and acknowledged
4. Estimation reasoning — for largest/riskiest items
5. Retro actions — from previous cycle (N/A for first sprint)
6. Capacity and buffer — stated and plan is within it
7. Async-readable — someone reading later understands "done" and blockers

### Iteration budget

- Max 2 review rounds before escalation

---

## Step 6: Supporting Artifacts (docs-mcp)

These can be generated in parallel with Steps 1-2 to enrich the epic and plan:

| Artifact | Tool | Purpose |
|----------|------|---------|
| PRD | `docs_generate_prd` | Formal product requirements for Phase 0 with phased delivery |
| ADR: MCP architecture | `docs_generate_adr` | Record decision to use MCP protocol for tool integration |
| ADR: Temporal for workflows | `docs_generate_adr` | Record decision to use Temporal for durable workflow orchestration |
| ADR: JetStream for signals | `docs_generate_adr` | Record decision to use NATS JetStream for event streaming |
| Module map diagram | `docs_generate_diagram` (type: module_map) | Visualize package structure as code is created |
| Dependency diagram | `docs_generate_diagram` (type: dependency) | Visualize import dependencies |
| Onboarding guide | `docs_generate_onboarding` | Developer getting-started for new contributors |
| CONTRIBUTING.md | `docs_generate_contributing` | Contribution workflow |
| CHANGELOG.md | `docs_generate_changelog` | Git history changelog |

---

## Execution Order Summary

```
[NOW]  Step 1: Saga creates Phase 0 epic          --> docs_generate_epic
[NOW]  Step 2: Saga creates 9 stories              --> docs_generate_story (x9)
[GATE] Step 3: Meridian reviews epic               --> checklist (7 items)
       Step 3a: Saga fixes gaps (if any)           --> edit epic/stories
[GATE] Step 3b: Meridian re-reviews (max 3 rounds)
[NEXT] Step 4: Helm creates sprint plan            --> manual
[GATE] Step 5: Meridian reviews plan               --> checklist (7 items)
       Step 5a: Helm fixes gaps (if any)
[GATE] Step 5b: Meridian re-reviews (max 2 rounds)
[GO]   Execution begins (Agent Plane roles)
```

---

## OKR Alignment (from MERIDIAN-TEAM-REVIEW-AND-OKRS.md)

| OKR | How this plan supports it |
|-----|--------------------------|
| KR1.1: 100% checklist before commit | Steps 3 and 5 are explicit Meridian gates |
| KR1.2: Zero vague success metrics | Epic acceptance criteria are measurable (100% metrics) |
| KR1.3: Zero wish sprint goals | Helm must produce objective + test + constraint |
| KR2.1: Every epic ties to OKR | Phase 0 ties to "prove the pipe" — foundational for all OKRs |
| KR2.2: Dependencies visible and confirmed | Story dependency map in Step 4 |
| KR2.3: Estimation reasoning recorded | Helm records per-story in Step 4 |
| KR3.1: Order of work + what's out | Sprint breakdown with explicit "what's out" |
| KR3.2: Capacity and buffer stated | 80/20 rule applied in sprint plan |
| KR3.3: Retro actions tracked | N/A for Sprint 1; established for Sprint 2+ |

---

*This plan follows the chain: Strategy/OKRs -> Saga -> Meridian -> Helm -> Meridian -> Execution. No artifact is committed without passing the Meridian checklist.*
