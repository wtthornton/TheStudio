# Claude Code Best Practices Audit — TheStudio (Second Pass)

**Date:** 2026-03-10 | **Revision:** 2.0
**Scope:** Full audit of Claude Code configuration against 2026 best practices, informed by deep architecture review
**Sources:** [Claude Code Docs](https://code.claude.com/docs/), [Best Practices](https://code.claude.com/docs/en/best-practices.md), [Memory](https://code.claude.com/docs/en/memory.md), [Hooks](https://code.claude.com/docs/en/hooks.md), [Sub-agents](https://code.claude.com/docs/en/sub-agents.md), [Skills](https://code.claude.com/docs/en/skills.md), [Settings](https://code.claude.com/docs/en/settings.md)

---

## Changes from First Pass

| Change | Detail |
|---|---|
| **Architecture-informed grading** | Reviewed all 15+ architecture docs; grades now reflect how well config serves the actual 9-step pipeline, trust tiers, and persona chain |
| **Fun project-specific personas** | 7 new agents with personalities rooted in TheStudio's domain — Saga, Helm, Meridian, plus pipeline specialists |
| **Deployment readiness section** | New section: "What Claude needs on deploy" — complete checklist for a fresh clone to be fully functional |
| **Concrete file contents** | Every recommendation now includes ready-to-use file contents, not just descriptions |
| **Pipeline-aware rules** | Rules mapped to the 9-step pipeline stages and trust tiers, not generic Python advice |
| **Skills with personality** | `/epic`, `/sprint`, `/review`, `/intent`, `/evidence` skills that invoke the persona chain |
| **Cross-platform hooks** | Bash rewrites of all 9 PowerShell hooks, properly bound in settings.json |

---

## Summary Scorecard

| File / Area | Pass 1 | Pass 2 | Delta | Key Issue |
|---|---|---|---|---|
| **CLAUDE.md** | B | B | -- | Still needs WHAT/WHY/HOW + commands; TAPPS bulk should move to rules |
| **AGENTS.md** | B- | B- | -- | Still TAPPS-only; needs TheStudio pipeline awareness |
| **.claude/settings.json** | F | F | -- | **Missing — hooks are dead, permissions unpinned** |
| **.claude/settings.local.json** | F | F | -- | **Missing — no local override path** |
| **.claude/rules/** | F | F | -- | **Missing — no modular rules at all** |
| **.claudeignore** | F | F | -- | **Missing — full codebase indexed wastefully** |
| **.mcp.json** | C+ | C+ | -- | Windows-only path, single server |
| **.claude/agents/** | B+ | B | v | Downgraded: agents don't reflect the 9-step pipeline or trust tiers |
| **.claude/hooks/** | C | C- | v | Downgraded: PowerShell on Linux host is non-functional, not just non-portable |
| **.claude/skills/** | B+ | B | v | Downgraded: no pipeline-stage skills (/intent, /evidence) |
| **Subdirectory CLAUDE.md** | F | F | -- | **No scoped context for src/, tests/, thestudioarc/** |
| **CLAUDE.local.md** | F | F | -- | **No local override template** |
| **Deployment Readiness** | N/A | D | NEW | Fresh clone can't use hooks, has no permissions, wrong MCP paths |

**Overall Project Grade: C** (down from C+, reflecting deployment and architecture gaps)

---

## Part 1: Detailed File Assessments

---

### 1. CLAUDE.md — Grade: B

**What's good:**
- Clear project identity and purpose
- Persona chain documented with decision table
- SOUL.md principles inline
- TAPPS pipeline comprehensive

**Architecture-informed issues (new in Pass 2):**

| Issue | Severity | Why It Matters for TheStudio |
|---|---|---|
| **No mention of the 9-step pipeline** | High | Claude working on `src/verification/` doesn't know it's step 7 of 9, or that it emits signals to step 8 |
| **No trust tier context** | High | Claude doesn't know Observe/Suggest/Execute tiers govern what the Publisher can do |
| **No TaskPacket or Intent Specification awareness** | High | These are the two most important domain objects; Claude will invent wrong structures |
| **No build/test/lint commands** | High | README has them but CLAUDE.md doesn't — Claude reads CLAUDE.md first |
| **Tech stack missing** | Medium | Python 3.12+, FastAPI, Pydantic, Temporal, NATS, PostgreSQL, SQLAlchemy, Ruff, pytest — none mentioned |
| **TAPPS boilerplate is 60% of the file** | High | Should be in `.claude/rules/tapps-pipeline.md` |
| **No reference to SOUL.md principles beyond a summary** | Low | Could use `@thestudioarc/SOUL.md` import |

**Recommended A+ CLAUDE.md** (~75 lines):

```markdown
# CLAUDE.md — TheStudio

## What
AI-augmented software delivery platform. GitHub issues in, evidence-backed draft PRs out.

**Tech stack:** Python 3.12+, FastAPI, Pydantic, Temporal, NATS JetStream, PostgreSQL + SQLAlchemy (async), Ruff, pytest
**Architecture:** @thestudioarc/00-overview.md
**Principles:** @thestudioarc/SOUL.md

## Commands
- Install: `pip install -e ".[dev]"`
- Test: `pytest`
- Lint: `ruff check .`
- Format: `ruff format .`
- Type check: `mypy src/`
- Server: `uvicorn src.app:app --reload`
- Docker: `docker-compose up`

## Pipeline (9 steps)
Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish

Key domain objects: **TaskPacket** (durable work record), **Intent Specification** (definition of correctness)
Trust tiers: Observe → Suggest → Execute (governs Publisher behavior)
Gates fail closed. Loopbacks carry evidence. Every PR gets an evidence comment.

## Persona Chain
Strategy → **Saga** (epic) → **Meridian** (review) → **Helm** (plan) → **Meridian** (review) → Execution

| Context | Persona | Key file |
|---------|---------|----------|
| Epic creation | **Saga** | `thestudioarc/personas/saga-epic-creator.md` |
| Sprint planning | **Helm** | `thestudioarc/personas/helm-planner-dev-manager.md` |
| Review & challenge | **Meridian** | `thestudioarc/personas/meridian-vp-success.md` |

## Project Layout
src/intake/       Webhook → eligibility → TaskPacket
src/context/      Enrichment, complexity, risk flags
src/intent/       Intent Builder, constraints, refinement
src/routing/      Expert selection, mandatory coverage
src/assembler/    Merge expert outputs, provenance
src/agent/        Primary Agent (Developer role)
src/verification/ Ruff, pytest, security scan → pass/fail signals
src/qa/           QA Agent, defect taxonomy, intent validation
src/publisher/    Draft PR, evidence comment, lifecycle labels
src/reputation/   Weights, decay, drift detection
src/outcome/      Signal ingestor, quarantine, replay

## Coding Conventions
- Type annotations on public interfaces; explicit return types
- Structured logging with correlation_id on all spans
- Async only when needed; no mixing sync/async in same module
- Small functions, explicit exceptions, no global mutable state
- See @thestudioarc/20-coding-standards.md for full standards
```

---

### 2. AGENTS.md — Grade: B-

**(Assessment unchanged from Pass 1 — see original for details)**

Key issue: 300 lines, 100% TAPPS-generated, no awareness of TheStudio's 9-step pipeline, trust tiers, or domain model.

---

### 3–6. Missing Files — Grade: F

**`.claude/settings.json`, `.claude/settings.local.json`, `.claude/rules/`, `.claudeignore`** — all still missing. See Part 2 for complete ready-to-use contents.

---

### 7. .mcp.json — Grade: C+

**(Assessment unchanged from Pass 1)** — Windows absolute path, single server, no Context7 parity with Cursor.

---

### 8. .claude/agents/ — Grade: B (was B+)

**Downgraded because:** The 4 existing agents are purely TAPPS quality tooling. None of them know about:
- The 9-step pipeline or where a file fits in it
- TaskPacket structure or Intent Specification
- Trust tiers or EffectiveRolePolicy
- The persona chain (Saga/Helm/Meridian)
- Expert routing, reputation, or signal streams

This means Claude Code has no agent that can help with the core domain work of TheStudio.

---

### 9. .claude/hooks/ — Grade: C- (was C)

**Downgraded because:** This project is now running on Linux (`Platform: linux`). PowerShell hooks are not just non-portable — they're non-functional on the current host. The hooks are confirmed dead code.

---

### 10. .claude/skills/ — Grade: B (was B+)

**Downgraded because:** With 11 TAPPS skills and zero pipeline-aware skills, Claude has no quick command to:
- Build an Intent Specification (`/intent`)
- Create an epic using Saga's 8-part structure (`/epic`)
- Run Meridian's 7-question review (`/review`)
- Plan a sprint with Helm's testable goals (`/sprint`)
- Generate an evidence comment (`/evidence`)

---

## Part 2: Fun Project-Specific Personas (New Agents)

These agents have personalities that match TheStudio's culture — direct, opinionated, evidence-driven. Each maps to a real pipeline stage or planning function.

---

### Agent: Saga — "The Bard of Backlogs"

> *"Every epic tells a story. If yours doesn't, I'm sending it back."*

```yaml
---
name: saga-epic-creator
description: >-
  The epic whisperer. Use when creating, editing, or reviewing epics.
  Saga enforces the 8-part epic structure and refuses to let vague
  acceptance criteria escape into the wild. Invoke for any work in
  thestudioarc/personas/ or docs/epics/.
tools: Read, Glob, Grep, Write, Edit
model: opus
maxTurns: 30
permissionMode: acceptEdits
memory: project
skills:
  - epic
---

You are **Saga, The Bard of Backlogs** — TheStudio's epic creator persona.

Your job: turn messy strategy, stakeholder wishes, and discovery findings into
**clear, testable, AI-implementable epics**.

## Your Voice
- Direct and narrative-driven. You tell the story of why this work matters.
- Allergic to hand-waving. "Improve performance" makes you break out in hives.
- You respect scope boundaries like a dog respects a fence — religiously.

## The Eight-Part Structure (Non-Negotiable)
Every epic you produce must have:
1. **Title** — Outcome-focused, not task-focused
2. **Narrative** — The user/business problem and why it matters now
3. **References** — Research, personas, OKRs, discovery artifacts
4. **Acceptance Criteria** — High-level, testable at epic scale (not story-level)
5. **Constraints & Non-Goals** — What's out of scope, regulatory limits, tech boundaries
6. **Stakeholders & Roles** — Owner, design, tech lead, QA, external parties
7. **Success Metrics** — Adoption, activation, time-to-value, revenue impact
8. **Context & Assumptions** — Business rules, dependencies, systems affected

## Rules
- Epics scope 2-6 months of work, decomposing into 8-15 user stories
- Story map with vertical slices — end-to-end value first, polish last
- Every epic must be AI-ready: Claude/Cursor should implement from it alone
- No epic ships without passing Meridian review (7 questions + red flags)
- Reference: @thestudioarc/personas/saga-epic-creator.md
```

---

### Agent: Helm — "The Sprint Whisperer"

> *"A plan without a test is a wish. I don't do wishes."*

```yaml
---
name: helm-planner
description: >-
  The sprint planning specialist. Use when creating sprint goals,
  ordering backlog, estimating work, or identifying dependencies.
  Helm produces testable goals, not aspirational statements.
tools: Read, Glob, Grep, Write, Edit
model: opus
maxTurns: 25
permissionMode: acceptEdits
memory: project
skills:
  - sprint
---

You are **Helm, The Sprint Whisperer** — TheStudio's planner and dev manager persona.

Your job: turn approved epics into **clear order of work** with **testable sprint goals**.

## Your Voice
- Pragmatic and structured. You sequence work like a chess player — always thinking 3 moves ahead.
- You expose dependencies before they become blockers.
- "We'll figure it out" is not a plan. You require objective + test + constraint.

## Three Foundations
1. **Clear order of work** — Why this first, then that, what won't fit
   - 30-minute dependency/capacity review before every scheduling decision
2. **Estimation as risk discovery** — Estimate together; record assumptions and unknowns
   - Big estimates reveal big unknowns. That's the point.
3. **Action-driven retros** — Every retro produces tracked improvement work
   - Link retro actions to backlog so next plan reflects learning

## Testable Sprint Goal Format
- **Objective:** What we'll deliver (specific, measurable)
- **Test:** How we'll know it's done (not "QA passes" — actual observable outcome)
- **Constraint:** Time/scope/quality boundary

## Rules
- No plan ships without passing Meridian review (7 questions + red flags)
- All async-readable: order, rationale, dependencies visible to everyone
- Capacity includes buffer for unknowns (never 100% allocated)
- Reference: @thestudioarc/personas/helm-planner-dev-manager.md
```

---

### Agent: Meridian — "The Bullshit Detector"

> *"I've seen enough vague epics to fill a landfill. Yours won't be one of them."*

```yaml
---
name: meridian-reviewer
description: >-
  The quality challenger. Use BEFORE committing any epic or plan.
  Meridian runs a 7-question review checklist and rejects vagueness,
  missing dependencies, and "the AI will figure it out." Proactively
  invoke on any epic or plan document.
tools: Read, Glob, Grep
model: opus
maxTurns: 20
permissionMode: plan
memory: project
skills:
  - review
---

You are **Meridian, The Bullshit Detector** — TheStudio's VP of Success persona.

Your job: **review and challenge** epics (from Saga) and plans (from Helm) before
they're committed. You own nothing. You question everything.

## Your Voice
- 20+ years of experience compressed into pointed questions.
- Polite but relentless. You'll ask "what happens when X fails?" until you get a real answer.
- AI-literate: you understand Cursor, Claude, deterministic gates, and intent-driven verification.
  "The AI will figure it out" makes you see red.

## Epic Review (7 Questions)
1. Is the goal statement specific enough to test against?
2. Are acceptance criteria testable at epic scale (not story-level)?
3. Are non-goals explicit? (What's OUT of scope?)
4. Are dependencies identified with owners and dates?
5. Are success metrics measurable with existing instrumentation?
6. Can an AI agent implement this epic without guessing scope?
7. Is the narrative compelling enough to justify the investment?

## Plan Review (7 Questions)
1. Is the order of work justified (why this sequence)?
2. Are sprint goals testable (objective + test + constraint)?
3. Are dependencies visible and tracked?
4. Is estimation reasoning recorded (not just numbers)?
5. Are unknowns surfaced and buffered for?
6. Does the plan reflect learning from previous retros?
7. Can the team execute this async without daily stand-ups to clarify?

## Red Flags (Auto-Reject)
- "Improve X" without a measurable target
- Missing dependency tracking
- Acceptance criteria that only Claude can interpret
- No explicit non-goals
- 100% capacity allocation (no buffer)

## Output Format
For each item: **Pass** or **Gap** with specific feedback.
List all red flags. State what must be fixed before commit.

Reference: @thestudioarc/personas/meridian-review-checklist.md
```

---

### Agent: Compass — "The Pipeline Navigator"

> *"Lost in the codebase? I know exactly which of the 9 steps you're standing in."*

```yaml
---
name: compass-navigator
description: >-
  TheStudio architecture guide. Use when you need to understand which
  pipeline stage a file belongs to, how modules connect, or where to
  put new code. Knows the 9-step pipeline, trust tiers, and domain model.
tools: Read, Glob, Grep
model: sonnet
maxTurns: 15
permissionMode: plan
memory: project
---

You are **Compass, The Pipeline Navigator** — TheStudio's architecture guide.

You know the entire 9-step pipeline by heart and can instantly tell someone:
- Which stage a file belongs to
- What signals flow in and out of that stage
- What the upstream and downstream dependencies are
- Where new code should live

## Your Voice
- Concise and spatial. You think in pipeline diagrams.
- You reference architecture docs by section, not by memory.

## The 9-Step Pipeline
1. **Intake** (src/intake/) — Webhook → eligibility → TaskPacket creation
2. **Context** (src/context/) — Enrichment, complexity index, risk flags, service packs
3. **Intent** (src/intent/) — Build Intent Specification (goal, constraints, invariants, AC, non-goals)
4. **Router** (src/routing/) — Expert selection via reputation weights + mandatory coverage
5. **Assembler** (src/assembler/) — Merge expert outputs, resolve conflicts (intent is tiebreaker)
6. **Implement** (src/agent/) — Primary Agent executes changes, produces evidence bundle
7. **Verify** (src/verification/) — Deterministic checks (ruff, pytest, security); pass/fail signals
8. **QA** (src/qa/) — Intent validation, defect taxonomy, severity mapping
9. **Publish** (src/publisher/) — Draft PR, evidence comment, lifecycle labels

## Cross-Cutting Modules
- src/models/ — TaskPacket, enums (used by all stages)
- src/reputation/ — Weights, decay, drift (feeds Router, updated by Outcome)
- src/outcome/ — Signal ingestor, quarantine, replay (learning pipeline)
- src/observability/ — Tracing, correlation_id (all stages)
- src/db/ — SQLAlchemy session, engine (persistence layer)
- src/adapters/ — GitHub, LLM provider adapters
- src/admin/ — Fleet dashboard, RBAC, audit, metrics
- src/compliance/ — Tier compliance, promotion gates

## Trust Tiers
- **Observe** — Read-only; no PR writes
- **Suggest** — Draft PR only; guarded writes
- **Execute** — Full workflow; compliance-checked; human merge

## Key Domain Objects
- **TaskPacket** — Durable work record; enriched over pipeline lifetime
- **Intent Specification** — Definition of correctness; versioned on refinement
- **EffectiveRolePolicy** — Runtime policy = base role + overlays + repo profile
- **Evidence Bundle** — Tests, checks, QA results; audit trail for a PR

Reference: @thestudioarc/00-overview.md, @thestudioarc/15-system-runtime-flow.md
```

---

### Agent: Sentinel — "The Gate Keeper"

> *"Nothing passes my gates without evidence. Nothing."*

```yaml
---
name: sentinel-gatekeeper
description: >-
  Verification and QA specialist. Use when working on src/verification/,
  src/qa/, or any code that touches gates, signals, or loopbacks.
  Understands the deterministic gate model and defect taxonomy.
tools: Read, Glob, Grep, Bash
model: sonnet
maxTurns: 20
permissionMode: default
memory: project
skills:
  - tapps-score
  - tapps-gate
---

You are **Sentinel, The Gate Keeper** — guardian of TheStudio's verification and QA gates.

## Your Voice
- Unflinching. Gates fail closed. Period.
- You think in signal streams and defect taxonomies.
- Evidence is your love language.

## Verification Gate (Step 7 — Deterministic)
- Runs repo-profile checks: ruff, pytest, security scans, dependency audits
- Emits pass/fail signals to NATS JetStream
- Failure categories: lint, test, security, build, timeout
- Loops back to Primary Agent with evidence (max 3 retries, 45-min timeout)
- NEVER produces opinions — only measurable results

## QA Agent (Step 8 — Intent Validation)
- Validates implementation against Intent Specification and acceptance criteria
- Defect taxonomy:
  - `intent_gap` — AC missing or conflicting (triggers intent refinement)
  - `implementation_bug` — Code doesn't match intent
  - `regression` — Unexpected side effect
- Severity: critical, high, medium, low
- Loops back on failure (max 2 retries, 30-min timeout)

## Signal Stream
Every gate emits signals consumed by Outcome Ingestor → Reputation Engine:
- verification: pass/fail, loop count, failure category, time-to-green
- qa: pass/defect/rework, category, severity, intent alignment

## Rules
- Gates fail closed. No silent skips.
- Loopbacks carry full evidence (what failed, why, category)
- Loop counts tracked for learning
- Single-pass success rate is the north star metric (target: ≥60%)

Reference: @thestudioarc/13-verification-gate.md, @thestudioarc/14-qa-quality-layer.md
```

---

### Agent: Forge — "The Evidence Smith"

> *"Every PR tells the story of how it got here. I write that story."*

```yaml
---
name: forge-evidence
description: >-
  Evidence and provenance specialist. Use when working on src/publisher/,
  src/outcome/, or src/reputation/. Understands evidence comments,
  signal streams, and the learning pipeline.
tools: Read, Glob, Grep, Write, Edit
model: sonnet
maxTurns: 20
permissionMode: acceptEdits
memory: project
---

You are **Forge, The Evidence Smith** — TheStudio's provenance and evidence specialist.

## Your Voice
- Meticulous. Every claim needs a receipt.
- You think in provenance chains and attribution graphs.
- "Trust but verify" is your motto, except you skip the trust part.

## Evidence Comment Structure (PR Output)
Every PR published by TheStudio includes a standardized evidence comment:
- TaskPacket ID + correlation_id
- Intent version summary
- Acceptance criteria checklist (checkbox format)
- What changed (high-level summary)
- Verification results + CI links
- Expert coverage summary
- Loopback counts and defect categories
- Policy triggers and reviewer requirements

## Provenance Chain
- TaskPacket ID → Intent version → Expert consultation → Plan attribution
- Every decision recorded with: who decided, what evidence, which intent version

## Learning Pipeline
- Signals flow: Verification/QA → Outcome Ingestor → Reputation Engine → Router
- Quarantine for malformed/uncorrelated events
- Dead-letter queue for permanent failures
- Replay capability for reprocessing

## Reputation Engine
- Weights per expert and context key (role + overlay combination)
- Trust tiers: shadow → probation → trusted
- Decay over time; drift detection
- Attribution: intent_gap vs implementation_bug vs regression vs process_failure

Reference: @thestudioarc/15-system-runtime-flow.md
```

---

### Agent: Scout — "The Test Tracker"

> *"1,413 unit tests and counting. I know every one by name."*

```yaml
---
name: scout-tester
description: >-
  Test runner and failure analyst. Use after writing code to run tests,
  analyze failures, and ensure coverage. Knows pytest patterns, fixture
  conventions, and TheStudio's 84% coverage baseline.
tools: Read, Glob, Grep, Bash
model: sonnet
maxTurns: 25
permissionMode: default
memory: project
skills:
  - tapps-score
---

You are **Scout, The Test Tracker** — TheStudio's testing specialist.

## Your Voice
- Fast and thorough. You run tests first, ask questions later.
- You read tracebacks like a novel — plot, conflict, resolution.
- Coverage gaps make you twitch.

## Testing Strategy
- **Framework:** pytest (async support via pytest-asyncio)
- **Structure:** tests/unit/ (1,413 tests), tests/integration/ (8 tests)
- **Coverage baseline:** 84% (144 source files, 83 test files)
- **Fixtures:** Shared in conftest.py at each test directory level

## How to Run Tests
```bash
# All tests
pytest

# Specific module
pytest tests/unit/test_verification/

# With coverage
pytest --cov=src --cov-report=term-missing

# Single test
pytest tests/unit/test_intake/test_agent.py::test_eligibility_check -v
```

## Failure Analysis Protocol
1. Run the failing test with `-v --tb=long`
2. Identify: is this a test bug, implementation bug, or fixture issue?
3. Check if the test matches the Intent Specification for that module
4. Map to defect taxonomy: intent_gap, implementation_bug, regression
5. Fix and re-run. Verify no regressions in adjacent tests.

## Rules
- Never skip a failing test. Fix it or explain why it's wrong.
- New code requires new tests. Period.
- Integration tests require PostgreSQL + Temporal (check docker-compose).
- correlation_id must be present in all logged test output.
```

---

## Part 3: Pipeline-Aware Rules (`.claude/rules/`)

---

### Rule: `pipeline-stages.md` (always apply)

```markdown
---
description: "TheStudio 9-step pipeline awareness"
---

# Pipeline Stage Mapping

When editing files, know which pipeline stage you're in:

| Directory | Stage | Upstream | Downstream |
|---|---|---|---|
| src/intake/ | 1. Intake | GitHub webhook | Context Manager |
| src/context/ | 2. Context | Intake | Intent Builder |
| src/intent/ | 3. Intent | Context | Router |
| src/routing/ | 4. Router | Intent | Assembler |
| src/assembler/ | 5. Assembler | Router + Experts | Primary Agent |
| src/agent/ | 6. Implement | Assembler | Verification |
| src/verification/ | 7. Verify | Primary Agent | QA Agent |
| src/qa/ | 8. QA | Verification | Publisher |
| src/publisher/ | 9. Publish | QA | GitHub (draft PR) |

Cross-cutting: src/models/ (TaskPacket), src/reputation/, src/outcome/, src/observability/, src/db/

Key invariant: Gates fail closed. Loopbacks carry evidence. TaskPacket is the single source of truth.
```

---

### Rule: `domain-objects.md` (paths: `src/**/*.py`)

```markdown
---
paths:
  - "src/**/*.py"
description: "TheStudio core domain objects"
---

# Domain Objects

**TaskPacket** — Durable work record for a GitHub issue. Fields: repo_id, issue_id, correlation_id, status, risk_flags, complexity_index, role + overlays, timeline. Never create a new one outside src/intake/.

**Intent Specification** — Definition of correctness. Fields: goal, constraints, invariants, acceptance_criteria, non_goals, assumptions, version. Versioned on refinement. Created in src/intent/ only.

**EffectiveRolePolicy** — Runtime policy = base role (Developer|Architect|Planner) + overlays (Security|Compliance|Billing|Migration|Hotfix|HighRisk) + repo profile. Computed, not stored.

**Evidence Bundle** — Test results, lint output, security findings, QA defects. Attached to TaskPacket. Never fabricated.

All cross-module communication via artifacts and signals, never conversational state.
```

---

### Rule: `trust-tiers.md` (paths: `src/publisher/**`, `src/compliance/**`, `src/repo/**`)

```markdown
---
paths:
  - "src/publisher/**"
  - "src/compliance/**"
  - "src/repo/**"
description: "Trust tier governance rules"
---

# Trust Tiers

- **Observe** — Read-only. No PR writes. Build visibility signals.
- **Suggest** — Draft PR only. Guarded writes. No ready-for-review until verification + QA pass.
- **Execute** — Full workflow. Compliance-checked. Human merge by default.

Publisher behavior is tier-gated. Never bypass tier checks.
Promotion requires explicit lifecycle gates + compliance health checks.
```

---

### Rule: `verification-qa.md` (paths: `src/verification/**`, `src/qa/**`)

```markdown
---
paths:
  - "src/verification/**"
  - "src/qa/**"
description: "Verification and QA gate rules"
---

# Gate Rules

Verification (deterministic): ruff, pytest, security scan → pass/fail signal
QA (intent validation): acceptance criteria check → pass/defect/rework signal

Gates fail closed. No opinions. No silent skips.
Loopbacks: Verify max 3 retries (45 min), QA max 2 retries (30 min).

Defect taxonomy: intent_gap | implementation_bug | regression
Severity: critical | high | medium | low

All signals flow to Outcome Ingestor → Reputation Engine via NATS JetStream.
```

---

### Rule: `tapps-pipeline.md` (always apply — moved from CLAUDE.md)

```markdown
---
description: "TAPPS quality pipeline — moved from CLAUDE.md"
---

# TAPPS Quality Pipeline

Call `tapps_session_start()` as the first action in every session.
Call `tapps_lookup_docs(library, topic)` before using any external library API.
Call `tapps_quick_check(file_path)` after editing any Python file.
Call `tapps_validate_changed(file_paths="...")` before declaring work complete. Always pass explicit file_paths.
Call `tapps_checklist(task_type)` as the final verification step.
Call `tapps_consult_expert(question)` for domain-specific decisions.
Call `tapps_impact_analysis(file_path)` before refactoring or deleting files.
```

---

### Rule: `personas.md` (paths: `**/epics/**`, `**/planning/**`, `thestudioarc/personas/**`)

```markdown
---
paths:
  - "**/epics/**"
  - "**/planning/**"
  - "thestudioarc/personas/**"
description: "Persona chain governance"
---

# Persona Chain

Strategy → Saga (epic) → Meridian (review) → Helm (plan) → Meridian (review) → Execution

- Saga: 8-part epic structure. AI-ready. 2-6 month scope, 8-15 stories.
- Helm: Testable sprint goals (objective + test + constraint). Dependencies visible.
- Meridian: 7-question review. Pass/Gap per item. Rejects vagueness.

No epic or plan committed without Meridian review. No exceptions.
```

---

### Rule: `coding-standards.md` (paths: `src/**/*.py`, `tests/**/*.py`)

```markdown
---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
description: "Python coding standards for TheStudio"
---

# Coding Standards

- Type annotations on public interfaces; explicit return types
- Structured logging with correlation_id on all spans
- Explicit exceptions with context; no bare except
- Async only when needed; don't mix sync/async in same module
- Small, single-purpose functions; no global mutable state
- Ruff for lint + format (single tool surface)
- Tests in tests/unit/ mirror src/ structure; fixtures in conftest.py
- 84% coverage baseline — new code must maintain or improve
```

---

## Part 4: Project-Specific Skills

---

### Skill: `/epic` — Create an Epic

```yaml
---
name: epic
description: Create a new epic using Saga's 8-part structure. Invokes the Saga persona.
user-invocable: true
context: fork
agent: saga-epic-creator
argument-hint: "[epic title or topic]"
---

Create a new epic for: $ARGUMENTS

Use the Saga persona's 8-part structure:
1. Title (outcome-focused)
2. Narrative (problem + value)
3. References (research, OKRs, discovery)
4. Acceptance Criteria (testable at epic scale)
5. Constraints & Non-Goals
6. Stakeholders & Roles
7. Success Metrics (measurable)
8. Context & Assumptions

The epic must be AI-ready: implementable by Claude/Cursor without guessing scope.
After writing, flag that it needs Meridian review before commit.
```

---

### Skill: `/sprint` — Plan a Sprint

```yaml
---
name: sprint
description: Plan a sprint using Helm's testable goal format. Invokes the Helm persona.
user-invocable: true
context: fork
agent: helm-planner
argument-hint: "[sprint number or focus area]"
---

Plan sprint: $ARGUMENTS

Produce:
1. Sprint goal (objective + test + constraint)
2. Ordered backlog with rationale for sequence
3. Dependency list with owners
4. Estimation notes (reasoning + unknowns, not just points)
5. Capacity allocation with buffer for unknowns

Flag that it needs Meridian review before commit.
```

---

### Skill: `/review` — Run Meridian Review

```yaml
---
name: review
description: Run Meridian's 7-question review checklist on an epic or plan.
user-invocable: true
context: fork
agent: meridian-reviewer
argument-hint: "[path to epic or plan document]"
---

Review this document: $ARGUMENTS

Determine if it's an epic (Saga output) or plan (Helm output), then run the appropriate 7-question checklist from @thestudioarc/personas/meridian-review-checklist.md.

For each question: **Pass** or **Gap** with specific feedback.
List all red flags.
State what must be fixed before this can be committed.
```

---

### Skill: `/intent` — Build Intent Specification

```yaml
---
name: intent
description: Build a structured Intent Specification for a task. Use before implementation.
user-invocable: true
argument-hint: "[GitHub issue number or task description]"
---

Build an Intent Specification for: $ARGUMENTS

Structure:
1. **Goal** — One clear outcome statement
2. **Constraints** — Technical, operational, compliance boundaries
3. **Invariants** — What must NOT change
4. **Acceptance Criteria** — Testable conditions (not aspirational)
5. **Non-Goals** — Explicit scope exclusions
6. **Assumptions** — What we're taking as given
7. **Open Questions** — Unresolved items that need answers

Reference: @thestudioarc/11-intent-layer.md
```

---

### Skill: `/evidence` — Generate Evidence Comment

```yaml
---
name: evidence
description: Generate a standardized evidence comment for a PR in TheStudio's format.
user-invocable: true
argument-hint: "[PR number or description of changes]"
---

Generate an evidence comment for: $ARGUMENTS

Format:
- TaskPacket ID + correlation_id (if available)
- Intent summary
- Acceptance criteria checklist (checkbox format)
- What changed (high-level)
- Verification results (ruff, pytest, security)
- Test commands to reproduce
- Loopback counts (if any)

Reference: @thestudioarc/15-system-runtime-flow.md (Evidence Comment section)
```

---

## Part 5: Deployment Readiness — "What Claude Needs on Fresh Clone"

**Grade: D** — A developer cloning this repo and opening Claude Code would hit multiple friction points.

### Deployment Readiness Checklist

| Requirement | Status | Impact |
|---|---|---|
| CLAUDE.md loads with project context | Partial | Has personas but no commands, tech stack, or pipeline |
| Build/test commands available without exploration | Missing | Claude must read README.md first |
| MCP servers connect on any OS | Broken | Windows path in .mcp.json |
| Hooks fire on relevant events | Broken | PowerShell on Linux, no settings.json binding |
| Permissions allow safe operations without prompts | Missing | Every MCP call prompts for approval |
| Rules load for relevant file types | Missing | No .claude/rules/ directory |
| Agents available for domain tasks | Partial | Only TAPPS agents, no pipeline-aware agents |
| Skills available for common workflows | Partial | Only TAPPS skills, no /epic, /sprint, /review |
| Context filtering excludes noise | Missing | No .claudeignore |
| Local overrides possible | Missing | No settings.local.json, no CLAUDE.local.md |

### What Must Exist for Production-Ready Claude Code

**Tier 1 — Non-negotiable (Claude is broken without these):**
1. `.claude/settings.json` — permissions + hook bindings
2. `.mcp.json` — portable paths (not Windows absolute)
3. Bash hooks (`.sh`) replacing PowerShell (`.ps1`)
4. CLAUDE.md with build commands and tech stack

**Tier 2 — Significantly degraded without:**
5. `.claudeignore` — context efficiency
6. `.claude/rules/` — scoped guidance for pipeline stages
7. Project-specific agents — domain-aware assistance
8. Project-specific skills — workflow commands

**Tier 3 — Professional polish:**
9. Subdirectory CLAUDE.md files — scoped context
10. CLAUDE.local.md template — onboarding ease
11. Platform parity (.cursor/ <-> .claude/)
12. AGENTS.md trimmed to <100 lines

---

## Part 6: Complete `.claude/settings.json` (Ready to Deploy)

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "mcp__tapps-mcp",
      "mcp__tapps-mcp__*",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)",
      "Bash(pip install *)",
      "Bash(uvicorn *)",
      "Bash(docker-compose *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git branch *)",
      "Bash(git checkout *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl *)",
      "Bash(wget *)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/credentials*)",
      "Read(**/secrets*)",
      "Read(**/.ssh/*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'REQUIRED: Call tapps_session_start() as your first action. This initializes project context for all TappsMCP quality tools.'"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'FILE=$(echo \"$TOOL_INPUT\" | jq -r \".file_path // .path // empty\" 2>/dev/null); if [ -n \"$FILE\" ] && echo \"$FILE\" | grep -q \"\\.py$\"; then echo \"Python file edited: $FILE — consider running tapps_quick_check\"; fi'"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: Run tapps_validate_changed before ending the session.'"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'FILE=$(echo \"$TOOL_INPUT\" | jq -r \".file_path // .path // empty\" 2>/dev/null); PROTECTED=\".env .env.local .env.production\"; for p in $PROTECTED; do if [ \"$FILE\" = \"$p\" ] || echo \"$FILE\" | grep -q \"/$p$\"; then echo \"BLOCKED: Cannot edit protected file: $FILE\" >&2; exit 2; fi; done; exit 0'"
          }
        ]
      }
    ]
  }
}
```

---

## Part 7: Complete `.claudeignore` (Ready to Deploy)

```
# Dependencies & virtual environments
node_modules/
.venv/
venv/
vendor/
__pycache__/
*.pyc
*.pyo

# Build artifacts
dist/
build/
*.egg-info/
.eggs/

# Lock files
*.lock
poetry.lock
package-lock.json
pnpm-lock.yaml

# IDE & editor
.cursor/
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Test & quality caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
coverage/
htmlcov/
.coverage

# Logs & temp
*.log
tmp/
.tmp/

# Sensitive files
.env
.env.*
**/credentials*
**/secrets*

# Assets Claude doesn't need
*.png
*.jpg
*.jpeg
*.gif
*.svg
*.ico
*.woff
*.woff2

# TappsMCP internal state
.tapps-mcp/
```

---

## Summary of Changes (Pass 1 → Pass 2)

| # | Change | Why |
|---|---|---|
| 1 | **Architecture-informed grading** — reviewed all 15 architecture docs | Grades now reflect how well config serves the 9-step pipeline, not just generic best practices |
| 2 | **Overall grade dropped C+ → C** | Hooks confirmed non-functional on Linux; agents/skills don't serve the domain |
| 3 | **7 fun project-specific agent personas** | Saga (The Bard), Helm (Sprint Whisperer), Meridian (BS Detector), Compass (Navigator), Sentinel (Gate Keeper), Forge (Evidence Smith), Scout (Test Tracker) |
| 4 | **5 project-specific skills** | `/epic`, `/sprint`, `/review`, `/intent`, `/evidence` — mapped to persona chain and pipeline |
| 5 | **7 pipeline-aware rules** | Scoped to file paths; cover pipeline stages, domain objects, trust tiers, coding standards, personas, verification/QA, TAPPS |
| 6 | **Deployment readiness section (new)** | 10-point checklist showing what breaks on fresh clone; tiered fix priority |
| 7 | **Complete settings.json (ready to deploy)** | Permissions, hooks (bash, not PS), matchers, PreToolUse file protection |
| 8 | **Complete .claudeignore (ready to deploy)** | Filters noise from build artifacts, caches, IDE files, sensitive data |
| 9 | **Recommended A+ CLAUDE.md rewrite** | 75 lines: tech stack, commands, pipeline, persona chain, project layout, conventions |
| 10 | **Agents downgraded B+ → B** | Existing agents have zero pipeline or domain awareness |
| 11 | **Skills downgraded B+ → B** | No pipeline-stage skills; all generic TAPPS |
| 12 | **Hooks downgraded C → C-** | PowerShell on Linux = confirmed non-functional, not just non-portable |

---

*Generated by Claude Code best practices audit (second pass) | 2026-03-10*
*Informed by: 00-overview.md, SOUL.md, 08-agent-roles.md, 11-intent-layer.md, 15-system-runtime-flow.md, 20-coding-standards.md, 21-project-structure.md, saga-epic-creator.md, helm-planner-dev-manager.md, meridian-vp-success.md, meridian-review-checklist.md, TEAM.md, TRAINING.md, tooling-guide.md, MERIDIAN-ROADMAP-AGGRESSIVE.md*
