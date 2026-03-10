# Epic 13 — Agent & Persona Infrastructure: Canonical Source, CI Linting, and Multi-Tool Distribution

**Author:** Saga
**Date:** 2026-03-10
**Status:** Complete — YAML frontmatter, linter, converter, drift detection all delivered

---

## 1. Title

Single Source of Truth for Agent Definitions — Add structured frontmatter, CI linting, CODEOWNERS protection, and a canonical-to-multi-tool converter so persona and agent files stay consistent, validated, and distributable across Claude Code, Cursor, and future tools.

## 2. Narrative

TheStudio defines 11 agent personalities in `.claude/agents/*.md` and 6 rule files in `.cursor/rules/` (3 persona `.mdc` files + 3 TAPPS configuration files). Three personas (Saga, Helm, Meridian) exist in **both** locations with overlapping but divergent content. The persona source of truth lives in `thestudioarc/personas/` — a third location — with no automated sync to the tool-specific directories.

This creates three problems:

**Drift.** When someone updates the Meridian checklist in `.claude/agents/meridian-reviewer.md`, the corresponding `.cursor/rules/persona-meridian.mdc` file doesn't get updated. The canonical `thestudioarc/personas/meridian-vp-success.md` may also be out of sync. Today the team is small enough that drift is manageable. As more agents are added (the pipeline has 9 stages, each potentially spawning specialized agents), undetected drift will cause inconsistent behavior depending on which tool invokes the persona.

**No validation.** There is no CI check that agent files contain required sections. Agency-agents (an open source prompt library we reviewed) runs a frontmatter linter on every PR — it catches missing `name`, `description`, and `color` fields plus recommended sections like Identity, Core Mission, and Critical Rules. TheStudio's agent files are load-bearing (they drive epic creation, sprint planning, code review, and gate enforcement), yet a typo in frontmatter or a missing section goes undetected until someone notices wrong behavior.

**No protection.** Agent and persona files can be modified in any PR without explicit review. Given that these files are effectively "configuration as code" that changes system behavior, they should be protected by CODEOWNERS requiring explicit approval.

The agency-agents project solved the distribution problem with a `convert.sh` script that reads canonical markdown files and generates tool-specific formats (Cursor `.mdc`, Claude Code agents, Aider `CONVENTIONS.md`, Windsurf `.windsurfrules`). TheStudio should adopt a similar pattern: maintain personas in one canonical location and generate the tool-specific files.

**Roadmap linkage:** This is infrastructure work that unblocks scaling the agent roster. Epics 14+ will add example workflows and maturity tracking, both of which depend on having a validated, consistent agent inventory.

## 3. References

- Current agent definitions: `.claude/agents/*.md` (11 files)
- Current Cursor rules: `.cursor/rules/*.mdc` (4 persona files, 3 TAPPS files)
- Canonical personas: `thestudioarc/personas/*.md`
- Agency-agents lint script (reference): `scripts/lint-agents.sh` in msitarzewski/agency-agents
- Agency-agents convert script (reference): `scripts/convert.sh` in msitarzewski/agency-agents
- Agent roles architecture: `thestudioarc/08-agent-roles.md`
- Pipeline stage mapping: `.claude/rules/pipeline-stages.md`
- SOUL principles: `thestudioarc/SOUL.md`

## 4. Acceptance Criteria

**AC-1: All agent files in `.claude/agents/` have structured YAML frontmatter.**
Every `.md` file in `.claude/agents/` starts with a `---` delimited YAML block containing at minimum: `name`, `description`, `tools`, `model`, and `maturity` (one of `draft`, `reviewed`, `proven`). Existing fields (`maxTurns`, `permissionMode`, `memory`, `skills`, `mcpServers`, `isolation`) are preserved. A script can parse the frontmatter and extract a catalog of all agents programmatically.

**AC-2: A linter script validates agent and persona files.**
`scripts/lint-agents.sh` (or equivalent) checks:
- YAML frontmatter exists and contains required fields
- Required sections are present in the body (at minimum: role description, scope/coverage, voice/communication style)
- Body has meaningful content (>50 words)
- The script exits non-zero on errors, zero on warnings-only or clean

The linter runs on both `.claude/agents/*.md` and `thestudioarc/personas/*.md`.

**AC-3: CI runs the linter on PRs that touch agent/persona files.**
A GitHub Actions workflow triggers on PRs modifying files in `.claude/agents/`, `.cursor/rules/`, or `thestudioarc/personas/`. It runs the linter on changed files only. Errors block merge; warnings are reported but don't block.

**AC-4: CODEOWNERS protects agent and persona directories.**
A `CODEOWNERS` file (or addition to existing one) requires explicit review approval for changes to `.claude/agents/`, `.cursor/rules/persona-*.mdc`, and `thestudioarc/personas/`. The owner can be the repository owner or a designated team.

**AC-5: A converter generates tool-specific files from canonical source.**
`scripts/convert-agents.sh` (or equivalent) reads persona/agent definitions from a single canonical location and generates:
- `.claude/agents/*.md` files with Claude Code frontmatter
- `.cursor/rules/persona-*.mdc` files with Cursor frontmatter (`description`, `globs`, `alwaysApply`)

Running the converter produces identical output to the current checked-in files (or better — with drift fixed). A `--check` flag verifies that generated files match checked-in files without modifying them (useful in CI).

**AC-6: Converter drift check runs in CI.**
The same GitHub Actions workflow from AC-3 runs `scripts/convert-agents.sh --check` and fails if any tool-specific file is out of sync with its canonical source. This prevents manual edits to generated files from going undetected.

**AC-7: TAPPS-specific rules are excluded from conversion.**
Files like `tapps-pipeline.mdc`, `tapps-python-quality.mdc`, and `tapps-expert-consultation.mdc` are not personas — they're tool configuration. The converter and linter skip these files. They remain manually maintained in `.cursor/rules/`.

## 5. Constraints & Non-Goals

**In scope:**
- Frontmatter standardization for existing agent files
- Linter for structure validation
- CI integration for linting and drift detection
- CODEOWNERS for change protection
- Converter from canonical → Claude Code + Cursor formats

**Out of scope:**
- Content quality review of agent prompts (that's Epic 14)
- Adding new agents or personas
- Support for tools beyond Claude Code and Cursor (Aider, Windsurf, Copilot) — can be added later to the converter
- Runtime agent orchestration or programmatic handoffs
- Changes to the TAPPS MCP integration or its rules files

## 6. Stakeholders & Roles

- **Owner:** Repository maintainer (agent/persona infrastructure)
- **Involved:** Any contributor who modifies agent or persona files
- **Consumer:** All developers using Claude Code or Cursor with TheStudio

## 7. Success Metrics

**Primary metric:** Zero drift between canonical persona source and tool-specific generated files, measured by CI passing on every PR.

**Secondary metrics:**
- Linter catches at least 1 structural issue in the current agent inventory (proving it adds value on day one)
- Time to add a new agent drops from "edit 3 files manually" to "edit 1 file + run converter"
- No agent-file PRs merge without CODEOWNERS approval (measured by GitHub audit log)

## 8. Context & Assumptions

- The canonical source location will be `thestudioarc/personas/` for the 3 core personas (Saga, Helm, Meridian) and `.claude/agents/` for pipeline-specific agents (Compass, Forge, Scout, Sentinel). The converter handles both source locations.
- The linter is a bash script (consistent with the project's existing `ruff`/`pytest` toolchain and the agency-agents reference implementation). No new dependencies required.
- CODEOWNERS requires the repository to have branch protection enabled on `master` with "Require review from Code Owners" active. Story 13.3 includes verifying and enabling this as a prerequisite. The existing CODEOWNERS file uses placeholder `@your-team` entries that must be replaced with real GitHub usernames before CODEOWNERS provides any protection.
- The `maturity` frontmatter field is informational for now. Enforcement (e.g., "only `proven` agents can be used in production pipelines") is deferred to a future epic.

---

## Stories

### Story 13.1 — Add Structured Frontmatter to All Agent Files

**What:** Update all 11 files in `.claude/agents/` to ensure YAML frontmatter includes `name`, `description`, `tools`, `model`, and `maturity` fields. Add `maturity: proven` to Saga, Helm, Meridian, Scout, and Sentinel (established agents). Add `maturity: reviewed` to Compass, Forge, and TAPPS agents. Preserve all existing fields.

**Acceptance test:** A YAML parser (e.g., `python -c "import yaml; ..."`) can load the frontmatter of every file and extract all required fields without error.

**Estimate:** Small (1-2 hours). Mechanical edit across 11 files.

---

### Story 13.2 — Build the Agent Linter Script

**What:** Create `scripts/lint-agents.sh` that validates:
1. YAML frontmatter exists with required fields (`name`, `description` at minimum)
2. Recommended body sections exist (role/identity description, scope or coverage, voice or communication style)
3. Body has >50 words of meaningful content
4. Exit code: 1 on errors, 0 on warnings-only or clean

The script accepts file arguments or defaults to scanning `.claude/agents/` and `thestudioarc/personas/`. Output format: `ERROR <file>: <message>` or `WARN <file>: <message>`, with a summary line.

**Acceptance test:** Running the linter on the current (pre-Story-13.1) files produces at least one finding. Running it after Story 13.1 produces zero errors.

**Estimate:** Small (2-3 hours). Reference implementation exists in agency-agents.

---

### Story 13.3 — Add CODEOWNERS for Agent and Persona Directories

**What:** Update the existing `CODEOWNERS` file (currently all entries use placeholder `@your-team`) to:
1. Replace `@your-team` with the actual repository owner's GitHub username on all existing entries
2. Add entries for agent/persona directories:
   - `.claude/agents/**`
   - `.cursor/rules/persona-*.mdc`
   - `thestudioarc/personas/**`
3. Verify that branch protection is enabled on `master` with "Require review from Code Owners" checked. If not enabled, enable it (requires admin access).

**Acceptance test:** A PR that modifies any file in these paths shows a required reviewer (real GitHub username, not placeholder) in the GitHub PR UI. `grep -c "@your-team" CODEOWNERS` returns 0.

**Estimate:** Small (1 hour). Requires replacing placeholders across CODEOWNERS and verifying branch protection settings.

**Dependency:** Repository admin access to enable branch protection if not already active.

---

### Story 13.4 — Build the Canonical-to-Multi-Tool Converter

**What:** Create `scripts/convert-agents.sh` that:
1. Reads persona definitions from `thestudioarc/personas/` (Saga, Helm, Meridian)
2. Generates `.claude/agents/` files with Claude Code frontmatter (`name`, `description`, `tools`, `model`, `maxTurns`, `permissionMode`, `memory`, `skills`)
3. Generates `.cursor/rules/persona-*.mdc` files with Cursor frontmatter (`description`, `globs`, `alwaysApply`)
4. Supports a `--check` flag that compares generated output to existing files and exits non-zero on diff
5. Does NOT touch non-persona files (TAPPS rules, pipeline agents like Compass/Forge/Scout/Sentinel)

The converter resolves the current three-location problem: canonical source → generated tool files.

**Acceptance test:** `scripts/convert-agents.sh && git diff --exit-code .claude/agents/saga-epic-creator.md .claude/agents/helm-planner.md .claude/agents/meridian-reviewer.md .cursor/rules/persona-saga.mdc .cursor/rules/persona-helm.mdc .cursor/rules/persona-meridian.mdc` exits 0 (generated files match checked-in files, or drift is intentionally fixed).

**Estimate:** Medium (4-6 hours). The format differences between Claude Code and Cursor frontmatter require mapping logic. Reference in agency-agents `convert.sh`.

**Dependency:** Story 13.1 (frontmatter must be standardized first).

---

### Story 13.5 — CI Workflow for Agent Linting and Drift Detection

**What:** Add a GitHub Actions workflow (`.github/workflows/lint-agents.yml`) that:
1. Triggers on PRs modifying files in `.claude/agents/`, `.cursor/rules/persona-*`, or `thestudioarc/personas/`
2. Runs `scripts/lint-agents.sh` on changed files — errors block merge, warnings are reported
3. Runs `scripts/convert-agents.sh --check` — drift between canonical and generated files blocks merge
4. Uses `actions/checkout@v4` with `fetch-depth: 0` for proper diff detection

**Acceptance test:** A PR that removes a required frontmatter field from an agent file fails the CI check. A PR that manually edits a generated persona file without updating the canonical source fails the drift check.

**Estimate:** Small (2-3 hours). Standard GitHub Actions pattern, reference in agency-agents workflow.

**Dependency:** Stories 13.2 and 13.4.

---

### Story 13.6 — Fix Existing Drift Between Persona Locations

**What:** Audit and reconcile the three persona locations:
- `thestudioarc/personas/saga-epic-creator.md` vs `.claude/agents/saga-epic-creator.md` vs `.cursor/rules/persona-saga.mdc`
- Same for Helm and Meridian

Resolve all differences by establishing `thestudioarc/personas/` as the canonical source and regenerating tool-specific files using the converter from Story 13.4. Document any intentional differences (e.g., Cursor rules may have shorter content due to context window considerations) as converter configuration, not manual overrides.

**Acceptance test:** `scripts/convert-agents.sh --check` exits 0 after reconciliation.

**Estimate:** Medium (3-4 hours). Requires reading and comparing 9 files, making judgment calls on which version is authoritative.

**Dependency:** Story 13.4 (converter must exist to regenerate files).
