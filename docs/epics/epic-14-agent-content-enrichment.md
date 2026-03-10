# Epic 14 — Agent Content Enrichment: Example Workflows, Maturity Tracking, and Pipeline Walkthrough Documentation

**Author:** Saga
**Date:** 2026-03-10
**Status:** Meridian PASS (Round 2) — Approved for sprint commitment

---

## 1. Title

Pipeline Walkthroughs, Agent Maturity Tracking, and Thin-Agent Enrichment — Add 3+ concrete pipeline examples, maturity metadata to all agent files, and TheStudio-specific domain context to the 4 thinnest agent definitions.

## 2. Narrative

TheStudio has a sophisticated 9-step pipeline (Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish), 11 agent definitions, 3 personas, and extensive architecture documentation. But there's a gap: **no concrete examples showing the pipeline in action**.

A new contributor (human or AI) reading the architecture docs understands the pipeline abstractly. They know Intake creates TaskPackets, that gates fail closed, that evidence comments go on every PR. But they can't see what a real flow looks like — what data moves between stages, what a loopback looks like with evidence, how the persona chain feeds into the agent plane, or what happens when QA rejects a change.

The agency-agents project we reviewed addresses this with an `examples/` directory containing concrete multi-agent workflow walkthroughs (landing page sprint, startup MVP, memory integration). These are the most useful files in the repo — they make abstract agent roles concrete by showing them working together on a real task.

Meanwhile, our agent definitions vary in depth. The core personas (Saga, Helm, Meridian) are deeply specified with checklists, formats, and red flags. The pipeline agents (Compass, Forge, Scout, Sentinel) are well-scoped but vary in detail. The TAPPS agents (researcher, reviewer, validator, review-fixer) are thin — they're essentially function-calling scripts with minimal domain context.

This epic enriches the agent ecosystem in three ways:
1. **Example walkthroughs** that show the pipeline processing real-world scenarios
2. **Maturity tracking** that makes agent quality visible and improvable
3. **Content gaps** closed in thin agent definitions

**Roadmap linkage:** This work directly improves the onboarding experience for new contributors and makes the agent definitions more effective when invoked. It also provides integration test specifications — each example walkthrough describes expected inputs and outputs that could become automated tests.

## 3. References

- Pipeline overview: `thestudioarc/00-overview.md`
- Agent roles: `thestudioarc/08-agent-roles.md`
- Intent layer: `thestudioarc/11-intent-layer.md`
- Current agents: `.claude/agents/*.md`
- Persona chain: `thestudioarc/personas/TEAM.md`
- SOUL principles: `thestudioarc/SOUL.md`
- Agency-agents examples (reference): `examples/` in msitarzewski/agency-agents
- Agency-agents orchestrator (reference): `specialized/agents-orchestrator.md` in msitarzewski/agency-agents
- Agency-agents handoff templates (reference): `strategy/coordination/handoff-templates.md` in msitarzewski/agency-agents
- Coding standards: `thestudioarc/20-coding-standards.md`
- Epic 13 (agent infrastructure): `docs/epics/epic-13-agent-persona-infrastructure.md`

## 4. Acceptance Criteria

**AC-1: At least 3 pipeline walkthrough examples exist in `thestudioarc/examples/`.**
Each example documents a concrete scenario flowing through the 9-step pipeline with:
- The triggering event (e.g., GitHub issue content)
- Key data at each stage (TaskPacket state, intent specification, expert routing decisions)
- Decision points (what the Router chose, what the Verifier checked)
- The output (PR content, evidence comment)
- At least one example must include a loopback (QA or Verification failure → retry with evidence)

Scenarios must be:
1. **Simple bug fix** — Happy path through all 9 stages, single expert, no loopback
2. **Feature with loopback** — Full pipeline where Verification fails (e.g., lint error), loops back to Primary Agent, succeeds on retry
3. **Complex multi-expert change** — Router selects multiple experts, Assembler merges outputs, QA validates against intent specification

**AC-2: Every agent file has a `maturity` field in frontmatter.**
Values are one of: `draft` (created, not validated in production), `reviewed` (peer-reviewed and used in dev), `proven` (used successfully in at least 3 real pipeline runs). Initial values are assigned based on current usage evidence, documented in a maturity log.

**AC-3: A maturity summary is generated from agent frontmatter.**
A script or command can produce a table showing all agents, their maturity level, last validation date, and coverage scope. This serves as the "agent catalog" that agency-agents puts in its README — but generated from structured data rather than manually maintained.

**AC-4: Thin agent definitions are enriched with domain context.**
At minimum, the following agents get content enrichment:
- `tapps-researcher.md` — Add: what TheStudio-specific libraries/patterns to prioritize, when to escalate to a human
- `tapps-reviewer.md` — Add: TheStudio quality standards summary, common patterns to flag, how to interpret TAPPS scores in project context
- `tapps-validator.md` — Add: what "passing" means in TheStudio context, which files are highest-risk, how to report blocking issues
- `compass-navigator.md` — Add: cross-cutting module explanations (models, reputation, outcome), common "where does this go?" questions with answers

Enrichment must stay concise (not bloating agent definitions beyond what fits in context windows) and must be TheStudio-specific (not generic advice). Each enriched file must contain: at least 2 references to specific `src/` directory paths, a tech stack quick-reference section, and explicit escalation rules (when to defer to another agent). These are checkable by grep.

**AC-5: A persona-to-agent handoff example exists.**
One document in `thestudioarc/examples/` shows the complete persona chain in action:
- Saga creates an epic (abbreviated, referencing a real epic like Epic 11)
- Meridian reviews it (showing checklist questions and answers)
- Helm creates a sprint plan (showing testable goal format)
- Meridian reviews the plan
- The approved epic + plan flows into Intake as a GitHub issue
- The pipeline processes it

This closes the gap between the persona layer (human-facing planning) and the agent plane (automated execution).

## 5. Constraints & Non-Goals

**In scope:**
- Creating 3+ pipeline walkthrough examples
- Assigning maturity levels to all agents
- Enriching 4-5 thin agent definitions
- One persona-chain-to-pipeline walkthrough
- A maturity summary generator (script or command)

**Out of scope:**
- Automated integration tests derived from examples (future work — examples are specifications, not test code)
- Adding new agents or personas (only enriching existing ones)
- Changes to the pipeline code itself
- Runtime orchestration or programmatic handoffs between agents
- Agency-agents' "personality-driven" approach — TheStudio agents stay role-based and policy-driven
- Full content audit of all 11 agents (only the 4-5 thinnest get enriched)

## 6. Stakeholders & Roles

- **Owner:** Repository maintainer (documentation and agent quality)
- **Involved:** Contributors who use agents for development
- **Consumer:** New contributors onboarding to TheStudio, AI agents loading context for pipeline work

## 7. Success Metrics

**Primary metric:** All 3+ walkthrough examples pass a structural completeness check: each references all 9 pipeline stages, includes at least one data structure sample per stage (TaskPacket, intent spec, verification signal, etc.), and at least one example includes a loopback with evidence. Measurable by script: `grep -c "Intake\|Context\|Intent\|Router\|Assembler\|Implement\|Verify\|QA\|Publish" thestudioarc/examples/walkthrough-*.md` returns >= 9 per file.

**Secondary metrics:**
- All agents have a `maturity` field assigned (measurable: `grep -c "maturity:" .claude/agents/*.md` equals agent count)
- Enriched agent files contain TheStudio-specific content: at least 2 file path references to `src/` directories, a tech stack section, and escalation/handoff rules (checkable by grep)
- The maturity summary command produces output without manual data entry

## 8. Context & Assumptions

- Example walkthroughs use realistic but simplified data. They don't need to use real GitHub issues — synthetic examples that demonstrate the pipeline mechanics are sufficient.
- Maturity assignment is a human judgment call based on current usage. The `proven` tier requires evidence of successful use, not just code review. For agents that haven't been used in real pipeline runs yet, `reviewed` is the highest appropriate tier.
- Agent enrichment must respect context window limits. Claude Code agents load the full file as a system prompt — a 2,000-line agent file is counterproductive. Target 200-400 lines per agent file.
- This epic depends on Epic 13 Story 13.1 for the `maturity` frontmatter field format. **Fallback plan:** If Epic 13 is delayed, Story 14.5 can proceed by adding `maturity` fields directly to `.claude/agents/` files using the format `maturity: draft|reviewed|proven`. The converter from Epic 13 Story 13.4 will pick these up later. Stories 14.1-14.4 and 14.7 have no dependency on Epic 13 and can start immediately.
- The handoff templates from agency-agents are a useful reference but too verbose for TheStudio's needs. TheStudio's handoff is programmatic (TaskPacket carries context), not copy-paste prompts. The examples should show TaskPacket state, not handoff documents.

---

## Stories

### Story 14.1 — Simple Bug Fix Pipeline Walkthrough

**What:** Create `thestudioarc/examples/walkthrough-simple-bugfix.md` documenting a bug fix flowing through all 9 pipeline stages. Use a realistic scenario (e.g., "Fix incorrect HTTP status code in intake webhook"). Show:
- The GitHub issue that triggers Intake
- TaskPacket creation with eligibility check
- Context enrichment (repo profile, complexity: low, risk: low)
- Intent specification (goal, constraint, AC, non-goal)
- Router selecting a single expert (Developer role, no overlays)
- Assembler passing through (single expert, no merge needed)
- Primary Agent implementing the fix
- Verification Gate running ruff + pytest (both pass)
- QA Agent validating against intent specification (pass)
- Publisher creating draft PR with evidence comment

Include abbreviated data structures at each stage as JSON snippets showing key fields only (TaskPacket fields, intent spec sections, verification signals). Full objects are not needed — show the 3-5 most important fields at each stage transition.

**Acceptance test:** The document contains 9 labeled sections (one per pipeline stage), each with at least one JSON data snippet. A `grep -c` for each stage name returns >= 1.

**Estimate:** Medium (3-4 hours). Requires understanding all 9 stages deeply enough to write realistic data.

---

### Story 14.2 — Feature with Loopback Pipeline Walkthrough

**What:** Create `thestudioarc/examples/walkthrough-feature-with-loopback.md` documenting a feature request where Verification fails on the first attempt. Show:
- Router selecting Developer + Security overlay (risk flags from Context)
- Verification Gate failing (ruff lint error on first attempt)
- Loopback signal with evidence (specific lint errors, file locations)
- Primary Agent fixing the issues
- Second Verification pass (success)
- QA Agent catching a missing acceptance criterion
- QA loopback with defect category and evidence
- Primary Agent addressing the QA finding
- Second QA pass (success)
- Publisher creating PR with loopback history in evidence comment

This example demonstrates the core resilience mechanism: gates fail closed, loopbacks carry evidence, retries are bounded.

**Acceptance test:** The example clearly shows that loopback signals include specific evidence (not just "failed"), and that the evidence comment records the loopback history.

**Estimate:** Medium (4-5 hours). More complex than 14.1 due to branching paths.

---

### Story 14.3 — Complex Multi-Expert Pipeline Walkthrough

**What:** Create `thestudioarc/examples/walkthrough-multi-expert.md` documenting a complex change requiring multiple experts. Show:
- Context flagging high complexity and multiple risk categories
- Router selecting multiple experts with reputation-weighted scoring
- Mandatory coverage rules triggering additional expert inclusion
- Assembler merging expert outputs with provenance tracking
- How conflicts between expert recommendations are resolved
- Full verification and QA cycle

**Acceptance test:** The example demonstrates how the Router's expert selection differs from a simple bug fix and how the Assembler merges multiple expert contributions with attribution.

**Estimate:** Medium (4-5 hours). Requires understanding Router policy and Assembler merge logic.

---

### Story 14.4 — Persona Chain to Pipeline Walkthrough

**What:** Create `thestudioarc/examples/walkthrough-persona-to-pipeline.md` showing the full lifecycle from strategic planning to automated execution:
1. Saga creates an abbreviated epic (referencing Epic 11 structure as example)
2. Meridian reviews it (showing 3-4 checklist questions with answers)
3. Helm creates a sprint plan with a testable goal
4. Meridian reviews the plan
5. The approved work becomes a GitHub issue
6. Intake processes the issue, creating a TaskPacket
7. The pipeline executes (abbreviated — reference walkthroughs 14.1-14.3 for full detail)

This is the "Rosetta Stone" document that connects the persona layer to the agent plane.

**Acceptance test:** The document contains labeled sections for each of the 6 handoff points (Saga output, Meridian epic review, Helm output, Meridian plan review, GitHub issue creation, Intake processing). Each section includes at least one concrete artifact sample (abbreviated epic, checklist Q&A, sprint goal, issue body, TaskPacket).

**Estimate:** Medium (3-4 hours). Can reference other walkthroughs for pipeline detail.

---

### Story 14.5 — Assign Maturity Levels to All Agents

**What:** Review each agent definition and assign a `maturity` value:
- `proven`: Saga, Helm, Meridian (used in every epic/plan cycle), Scout (runs on every code change)
- `reviewed`: Sentinel, Compass, Forge (well-defined but less frequently invoked)
- `draft`: tapps-researcher, tapps-reviewer, tapps-validator, tapps-review-fixer (function-calling wrappers, not deeply tested as standalone agents)

Add a `last_validated` date field and `coverage` field (which directories/stages the agent operates on). Document the rationale for each assignment in a `docs/agent-maturity-log.md` file.

**Acceptance test:** Every file in `.claude/agents/` has `maturity`, `last_validated`, and `coverage` fields in frontmatter. The maturity log explains each assignment.

**Estimate:** Small (2-3 hours). Mostly mechanical with some judgment calls.

**Dependency:** Story 13.1 (frontmatter standardization).

---

### Story 14.6 — Build Maturity Summary Generator

**What:** Create a script (`scripts/agent-catalog.sh` or Python equivalent) that:
1. Reads frontmatter from all `.claude/agents/*.md` files
2. Produces a markdown table: Name | Description | Model | Maturity | Last Validated | Coverage
3. Outputs to stdout (can be piped to a file or used in CI)

Optional: add a `--json` flag for programmatic consumption.

**Acceptance test:** `scripts/agent-catalog.sh` produces a valid markdown table with one row per agent, all fields populated. The output is correct compared to manual inspection of the files.

**Estimate:** Small (1-2 hours). YAML parsing in bash (awk) or Python (pyyaml).

**Dependency:** Story 14.5 (maturity fields must exist).

---

### Story 14.7 — Enrich Thin Agent Definitions

**What:** Add TheStudio-specific domain context to the 4 thinnest agent definitions:

**`tapps-researcher.md`** — Add:
- TheStudio's tech stack quick reference (FastAPI, Pydantic, Temporal, NATS, SQLAlchemy async, Ruff, pytest)
- Priority libraries to look up docs for (temporal-sdk, nats-py, sqlalchemy async, pydantic v2)
- When to escalate: if the question touches pipeline architecture (defer to Compass) or gate logic (defer to Sentinel)

**`tapps-reviewer.md`** — Add:
- TheStudio's 7 quality categories with score thresholds
- Common patterns to flag: sync/async mixing, missing correlation_id, mutable global state, missing type annotations on public interfaces
- How to interpret scores in context: <60 = blocking, 60-70 = needs attention, 70-85 = acceptable, >85 = strong

**`tapps-validator.md`** — Add:
- Highest-risk files (anything in src/verification/, src/qa/, src/publisher/ — gate-adjacent code)
- What "passing" means: all files score >=70, no security findings, no dead code in public APIs
- Blocking issue format: file path, category, score, one-line description, suggested fix

**`compass-navigator.md`** — Add:
- Cross-cutting modules explained: src/models/ (TaskPacket, all domain objects), src/reputation/ (weights, decay, drift), src/outcome/ (signal ingestor, quarantine, replay), src/observability/ (correlation_id, structured logging), src/db/ (async SQLAlchemy, migrations)
- FAQ section: "Where does X go?" for 5-6 common scenarios (e.g., "I need to add a new field to TaskPacket" → src/models/ + migration + update consumers)

**Acceptance test:** Each enriched agent file stays under 400 lines. The added content is TheStudio-specific (not generic advice). A qualitative review confirms the enriched agents give more useful guidance when loaded as system prompts.

**Estimate:** Medium (4-6 hours total across 4 files). Requires reading architecture docs to write accurate domain context.

**Dependency:** None (can be done in parallel with other stories).
