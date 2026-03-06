# Tooling Guide — Cursor & Claude for Personas

Version: 1.0 | Last updated: 2026-03-05

Shared reference for how Saga, Helm, and Meridian use Cursor and Claude. Each persona doc links here instead of repeating this content.

---

## Cursor (2026)

### Agent (Cmd/Ctrl+I)

- Unlimited tool calls; semantic codebase search; file read/edit; terminal; web search; browser for validation.
- Persona outputs (epics, plans, checklists) should live in the repo so Agent finds them via semantic search.
- Agent can summarize scope, blockers, and sprint goals from repo docs and issue bodies.

### Rules (`.cursor/rules/`)

- Three persona rules: `persona-saga.mdc`, `persona-helm.mdc`, `persona-meridian.mdc`.
- Rules encode structure (epic template, sprint goal format, review checklist) and link to full persona docs.
- Set to **Apply Intelligently** (description-based trigger) plus **globs** for file-path triggers (e.g. `**/epics/**`, `**/planning/**`, `**/review*`).
- Reference TheStudio docs (`08-agent-roles.md`, `11-intent-layer.md`, `15-system-runtime-flow.md`) in rules so implementation stays aligned.

### AGENTS.md

- `thestudioarc/AGENTS.md` maps agent roles and now includes a Personas section showing how Saga, Helm, and Meridian feed the Agent Plane.
- Nested `AGENTS.md` in subdirectories (e.g. `docs/`, `thestudioarc/personas/`) can scope persona behavior.

### Context injection

- Cursor injects project context (open files, git status, recent errors, workspace rules).
- Persona instructions assume Agent already sees repo structure, existing epics/intent docs, sprint goals, and dependency notes.

### Other features

- **Checkpoints:** Use when drafting or editing epics, plans, or review docs — undo edits if a revision goes wrong.
- **Browser tool:** For demos or acceptance checks, Agent can use the browser to verify sprint goals against a running app.
- **Export:** Export persona chats as markdown for stakeholder review or for attaching to issues/Confluence.

---

## Claude (2026)

### Extended thinking

- Use for complex epics (many stakeholders, compliance, multi-team dependencies), complex planning (dependency trade-offs, capacity), or deep reviews.
- Claude reasons step-by-step before producing output, improving quality for ambiguous or high-stakes work.

### Artifacts

- Use Artifacts to draft and iterate on epic documents (Saga), sprint goal templates and dependency matrices (Helm), or review reports (Meridian).
- Keeps the working document visible and editable in one place.

### Long context (200K)

- Paste discovery notes, OKRs, stakeholder comments, backlog excerpts, and capacity notes so persona outputs are grounded in real input.

### Structured outputs

- Ask for persona outputs in a consistent format (markdown sections matching the persona's required structure) so they can be dropped into Jira, GitHub issues, or TheStudio Intent Specification.

---

## MCP Servers

Four MCP servers are configured in `.cursor/mcp.json`:

### TappsMCP (tapps-mcp)

Code quality, scoring, security, domain experts, and project memory. 29+ tools.

**Key tools for personas:**
- `tapps_consult_expert` — Query built-in domains (17) or TheStudio custom domains (6)
- `tapps_research` — Combined expert + docs lookup in one call
- `tapps_memory` — Persist architecture decisions and quality patterns across sessions
- `tapps_validate_changed` — Quality gate on changed files before commit

**Custom expert domains** (`.tapps-mcp/experts.yaml`):
`intent-specification`, `agent-roles-routing`, `verification-qa`, `workflow-orchestration`, `epic-planning`, `publisher-github`

### DocsMCP (docs-mcp)

Documentation generation and validation. 14 tools.

**Key tools for personas:**

| Persona | Tools | Usage |
|---------|-------|-------|
| **Saga** | `docs_generate_epic`, `docs_generate_story`, `docs_generate_prd`, `docs_generate_adr`, `docs_generate_diagram` | Create epics, stories, PRDs, ADRs, and architecture diagrams |
| **Helm** | `docs_check_completeness`, `docs_check_drift` | Verify planning docs are complete and current |
| **Meridian** | `docs_project_scan`, `docs_check_freshness` | Audit documentation state during reviews |

### Context7

Library documentation lookup via `@upstash/context7-mcp`.

### Playwright

Browser automation for acceptance testing and validation.

---

## Integration with TheStudio

| Persona | Feeds into | Key docs |
|---------|-----------|----------|
| **Saga** | Intent Builder — epic-level acceptance criteria and constraints become Intent Specification | `11-intent-layer.md`, `08-agent-roles.md` (Planner role) |
| **Helm** | Planner role, Context Manager — order of work, sprint goals, dependencies feed Intake and Context Manager | `15-system-runtime-flow.md`, `08-agent-roles.md` |
| **Meridian** | Verification, QA, Outcome Ingestor — review bar aligns with gates and metrics | `13-verification-gate.md`, `14-qa-quality-layer.md`, `12-outcome-ingestor.md` |

### Evidence and provenance

- When epics and plans are stored in the repo or linked from issues, Cursor and Claude can reference them during implementation and QA, keeping "definition of done" consistent.
- PRs and evidence comments should reflect intent and plan. No "we'll document it later."

---

*Shared tooling reference for Saga, Helm, and Meridian. See individual persona docs for role-specific behaviors.*
