# Claude Code Best Practices Audit — TheStudio

**Date:** 2026-03-10
**Scope:** All Claude Code configuration files evaluated against 2026 official best practices
**Sources:** [Claude Code Docs](https://code.claude.com/docs/), [Best Practices](https://code.claude.com/docs/en/best-practices.md), [Memory](https://code.claude.com/docs/en/memory.md), [Hooks](https://code.claude.com/docs/en/hooks.md), [Sub-agents](https://code.claude.com/docs/en/sub-agents.md), [Skills](https://code.claude.com/docs/en/skills.md), [Settings](https://code.claude.com/docs/en/settings.md)

---

## Summary Scorecard

| File / Area | Current Grade | Issues | Target |
|---|---|---|---|
| **CLAUDE.md** | B | Too long (158 lines of TAPPS boilerplate), missing WHAT/WHY/HOW structure | A+ |
| **AGENTS.md** | B- | Entirely TAPPS-generated, no project-specific agent guidance | A+ |
| **.claude/settings.json** | F | **Missing entirely** | A+ |
| **.claude/settings.local.json** | F | **Missing entirely** | A+ |
| **.claude/rules/** | F | **Missing entirely** — no modular rules | A+ |
| **.claudeignore** | F | **Missing entirely** | A+ |
| **.mcp.json** | C+ | Windows paths, single server, no env var expansion | A+ |
| **.claude/agents/** | B+ | Well-structured, minor gaps | A+ |
| **.claude/hooks/** | C | PowerShell-only (no cross-platform), no settings.json binding | A+ |
| **.claude/skills/** | B+ | Good coverage, minor frontmatter gaps | A+ |
| **Subdirectory CLAUDE.md** | F | **None exist** — no monorepo-style scoping | A+ |
| **CLAUDE.local.md** | F | **Missing** — no local override template | A+ |

**Overall Project Grade: C+**

---

## Detailed Assessments

---

### 1. CLAUDE.md — Grade: B

**What's good:**
- Clear project identity ("AI-augmented software delivery platform")
- Persona chain is well-documented with a decision table
- Key references section provides navigability
- Principles section is concise and opinionated
- TAPPS pipeline instructions are comprehensive

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **158 lines total, ~100 lines of TAPPS boilerplate** | High | Best practice: <200 lines, but TAPPS content should be in `.claude/rules/` not CLAUDE.md |
| **No WHAT/WHY/HOW structure** | Medium | 2026 standard: organize as What (tech stack, structure), Why (purpose), How (working patterns) |
| **No tech stack declaration** | Medium | Claude needs to know: language, framework, package manager, test runner |
| **No build/test/lint commands** | High | Most impactful content for CLAUDE.md — "how to run things" |
| **No file structure overview** | Medium | Helps Claude navigate without excessive exploration |
| **Persona detail is too much for root file** | Medium | Move to `.claude/rules/personas.md` — CLAUDE.md should summarize, not teach |
| **References use relative paths, not `@` imports** | Low | `@thestudioarc/00-overview.md` syntax allows Claude to lazy-load |
| **No coding conventions summary** | Medium | Even a 3-line summary (indent style, naming, import order) helps |
| **"You should call" phrasing is weak** | Low | Use imperative: "Call X" or "REQUIRED: Call X" |

**Recommendations to reach A+:**

1. **Restructure to WHAT/WHY/HOW** — 3 clear sections
2. **Move TAPPS pipeline to `.claude/rules/tapps-pipeline.md`** — reduces CLAUDE.md to ~60 lines
3. **Move persona details to `.claude/rules/personas.md`** — CLAUDE.md keeps only the chain summary and table
4. **Add build/test/lint commands:**
   ```markdown
   ## Commands
   - Install: `pip install -e ".[dev]"`
   - Test: `pytest`
   - Lint: `ruff check .`
   - Type check: `mypy src/`
   ```
5. **Add tech stack summary:**
   ```markdown
   ## Tech Stack
   Python 3.11+, FastAPI, SQLAlchemy, Temporal, PostgreSQL
   ```
6. **Add file structure overview** (5-10 key directories)
7. **Use `@` imports** for referenced docs instead of inline paths

---

### 2. AGENTS.md — Grade: B-

**What's good:**
- Comprehensive tool reference table
- Clear session_start vs init distinction
- Domain hints for expert consultation are valuable
- Memory systems section is well-written
- Troubleshooting sections are practical

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **300 lines — far too long** | High | AGENTS.md should be concise; move details to rules or skill docs |
| **100% TAPPS-generated, no project-specific content** | High | Should include TheStudio-specific agent roles, not just TAPPS tool docs |
| **No reference to thestudioarc/08-agent-roles.md** | Medium | Project has rich agent role definitions that AGENTS.md ignores |
| **Duplicates CLAUDE.md content** | Medium | TAPPS workflow repeated in both files |
| **DocsMCP section is 35 lines of tool tables** | Low | Could be a separate `.claude/rules/docsmcp.md` |
| **Troubleshooting (60+ lines) belongs in docs/** | Medium | AGENTS.md shouldn't be a support doc |

**Recommendations to reach A+:**

1. **Trim to <100 lines** — essential workflow, tools table, domain hints only
2. **Add TheStudio-specific agents** — reference the persona chain, agent roles from `08-agent-roles.md`
3. **Move troubleshooting to `docs/TAPPS_TROUBLESHOOTING.md`**
4. **Move DocsMCP reference to `.claude/rules/docsmcp.md`**
5. **Remove duplication with CLAUDE.md** — one authoritative source per topic

---

### 3. .claude/settings.json — Grade: F (Missing)

**This is the most critical gap.** Without `settings.json`, Claude Code has:
- No permission allowlists (every MCP tool call prompts for approval)
- No project-wide behavioral defaults
- No sandbox configuration
- No attribution settings

**Required for A+:**

```json
{
  "permissions": {
    "allow": [
      "mcp__tapps-mcp",
      "mcp__tapps-mcp__*",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)",
      "Bash(pip install *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Read(.env)",
      "Read(**/credentials*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [{"type": "command", "command": "bash .claude/hooks/session-start.sh"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "bash .claude/hooks/post-edit.sh"}]
      }
    ],
    "Stop": [
      {
        "hooks": [{"type": "command", "command": "bash .claude/hooks/stop.sh"}]
      }
    ]
  }
}
```

**Recommendations:**
1. **Create `.claude/settings.json`** with permissions, hooks, and MCP enablement
2. **Create `.claude/settings.local.json` template** (gitignored) for personal overrides
3. **Bind hooks in settings.json** — the `.ps1` scripts exist but aren't referenced anywhere Claude Code can find them
4. **Add `.claude/settings.local.json` to `.gitignore`**

---

### 4. .claude/rules/ — Grade: F (Missing)

**No modular rules exist.** The `.cursor/rules/` directory has 7 rules files, but `.claude/rules/` has zero. This means Claude Code gets no path-specific or topic-specific guidance.

**Required for A+:**

| Rule File | Content | Path Filter |
|---|---|---|
| `tapps-pipeline.md` | TAPPS quality pipeline (move from CLAUDE.md) | Always apply |
| `personas.md` | Persona chain, when-to-use table | `**/epics/**`, `**/planning/**` |
| `python-quality.md` | 7 scoring categories, quality thresholds | `**/*.py` |
| `security.md` | Security gates, bandit config, secret detection | `**/*.py`, `**/Dockerfile` |
| `testing.md` | Test patterns, pytest conventions, coverage requirements | `**/test_*`, `**/tests/**` |
| `api-design.md` | FastAPI patterns, endpoint conventions | `**/api/**`, `**/routes/**` |
| `architecture.md` | SOUL.md principles, intent layer rules | Always apply |

**Recommendations:**
1. **Port `.cursor/rules/*.mdc` to `.claude/rules/*.md`** — same content, different format
2. **Add `paths:` frontmatter** for scoped loading
3. **Keep each rule file under 50 lines** — focused and actionable

---

### 5. .claudeignore — Grade: F (Missing)

**Without `.claudeignore`, Claude Code indexes everything** including build artifacts, lock files, and large assets. This wastes context tokens and slows file searches.

**Required for A+:**

```
# Dependencies & virtual envs
node_modules/
.venv/
vendor/
__pycache__/
*.pyc

# Build artifacts
dist/
build/
.next/
*.egg-info/

# Lock files (Claude doesn't need these)
*.lock
pnpm-lock.yaml
poetry.lock
package-lock.json

# IDE & OS
.cursor/
.vscode/
.idea/
.DS_Store
Thumbs.db

# Assets & media
*.png
*.jpg
*.svg
*.gif
*.ico
*.woff
*.woff2

# Logs & temp
*.log
tmp/
.tmp/
coverage/
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Sensitive
.env
.env.*
**/credentials*
**/secrets*
```

---

### 6. .mcp.json — Grade: C+

**What's good:**
- Correct file location (project root `.mcp.json`)
- Has `instructions` field (good practice)
- Environment variable for project root

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **Windows absolute path** (`C:\Users\tappt\.local\bin\tapps-mcp.exe`) | Critical | Not portable — fails for any other developer or CI |
| **Only 1 MCP server** | Medium | `.cursor/mcp.json` has 4 servers (Context7, DocsMCP, Playwright) |
| **No environment variable expansion** | Medium | Should use `${HOME}` or `$HOME` for paths |
| **Missing Context7 server** | Medium | Cursor has it but Claude Code doesn't |

**Recommendations to reach A+:**

```json
{
  "mcpServers": {
    "tapps-mcp": {
      "command": "tapps-mcp",
      "args": ["serve"],
      "env": {
        "TAPPS_MCP_PROJECT_ROOT": "."
      },
      "instructions": "Code quality scoring, security scanning, quality gates, doc lookup, and expert consultation for Python."
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      },
      "instructions": "Look up library documentation with version-specific context."
    }
  }
}
```

1. **Use `tapps-mcp` (no path)** — assumes it's on `$PATH` (portable)
2. **Add Context7** for documentation lookup parity with Cursor
3. **Use `${ENV_VAR}` syntax** for any environment-specific values

---

### 7. .claude/agents/ — Grade: B+

**What's good:**
- All 4 agents have proper YAML frontmatter
- `name`, `description`, `tools`, `model`, `maxTurns`, `permissionMode` all present
- `memory: project` enables cross-session learning
- `mcpServers` scoped correctly
- `tapps-review-fixer` uses `isolation: worktree` (excellent)
- Skills preloaded where appropriate

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **No project-specific agents** | Medium | All 4 are TAPPS-generated; no agents for TheStudio personas (Saga, Helm, Meridian) |
| **tapps-reviewer has `permissionMode: acceptEdits` but tools are read-only** | Low | Inconsistency — `Read, Glob, Grep` can't edit |
| **No `argument-hint`** in any agent | Low | Helps with discoverability |
| **No debugger or test-runner agent** | Medium | Common high-value agents missing |

**Recommendations to reach A+:**

1. **Add project-specific agents:**
   - `saga-epic-creator.md` — invokes Saga persona for epic creation
   - `helm-planner.md` — invokes Helm for sprint planning
   - `meridian-reviewer.md` — invokes Meridian for review
   - `test-runner.md` — runs pytest with intelligent failure analysis
   - `debugger.md` — systematic debugging with log analysis
2. **Fix `tapps-reviewer` permission mode** to `plan` (read-only agent shouldn't accept edits)
3. **Add descriptions that explain WHEN to delegate** (critical for auto-routing)

---

### 8. .claude/hooks/ — Grade: C

**What's good:**
- 9 hook scripts covering the full lifecycle (session start, post-edit, stop, compact, subagent)
- `tapps-stop.ps1` checks sidecar progress files (sophisticated)
- `tapps-post-edit.ps1` correctly filters for `.py` files only
- Guard against infinite loops in stop hook (`stop_hook_active` check)

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **All hooks are PowerShell (.ps1)** | Critical | Linux/macOS/CI have no PowerShell; should be bash/sh |
| **No `.claude/settings.json` binding** | Critical | Hooks exist as files but aren't registered in settings.json — **Claude Code cannot discover them** |
| **No matcher patterns** | High | Without matchers, hooks fire on every event (wasteful) |
| **Exit code semantics not fully used** | Medium | No hooks use exit code 2 (block) — all exit 0 |
| **`tapps-session-start.ps1` outputs text but doesn't set context** | Medium | Should append to session context via stdout + exit 0 pattern |

**This is the second most critical gap.** The hooks exist but are effectively dead code because:
1. They're not referenced in any `settings.json`
2. They're PowerShell on what may be a Linux host
3. Claude Code discovers hooks via `settings.json`, not by scanning directories

**Recommendations to reach A+:**

1. **Rewrite all hooks as bash scripts** (`.sh`) for cross-platform compatibility
2. **Register hooks in `.claude/settings.json`** (see settings.json section above)
3. **Add matchers** to scope hooks appropriately:
   - `PostToolUse` matcher: `"Edit|Write"` (only fire after edits)
   - `SessionStart` matcher: `"startup|resume"` (not on compact)
   - `SubagentStart` matcher: filter by agent type if needed
4. **Use exit code 2** in `PreToolUse` hooks to block dangerous operations
5. **Add a `PreToolUse` hook** to block writes to protected files

---

### 9. .claude/skills/ — Grade: B+

**What's good:**
- 11 skills with proper `SKILL.md` format
- `allowed-tools` restricts tool access (good security)
- `argument-hint` present on some skills
- `disable-model-invocation: true` on `tapps-validate` (manual-only, correct)
- Clear step-by-step instructions in each skill

**Issues found:**

| Issue | Severity | Best Practice Violated |
|---|---|---|
| **No project-specific skills** | Medium | All 11 are TAPPS-generated; no `/epic`, `/sprint`, `/review` skills |
| **No `context: fork` usage** | Low | Expensive skills should run in isolated subagent context |
| **No supporting files** (reference.md, examples.md) | Low | Skills could include examples |
| **Missing `user-invocable` frontmatter** on some | Low | Explicit is better than default |

**Recommendations to reach A+:**

1. **Add project-specific skills:**
   - `/epic` — Create an epic using Saga persona structure
   - `/sprint` — Plan a sprint using Helm persona
   - `/review` — Run Meridian review checklist
   - `/deploy` — Deployment checklist with safety gates
2. **Add `context: fork` to heavy skills** (`tapps-review-pipeline`, `tapps-security`)
3. **Add `user-invocable: true/false` explicitly** to all skills

---

### 10. Subdirectory CLAUDE.md Files — Grade: F (Missing)

**The project has a rich directory structure** (`thestudioarc/`, `thestudioarc/personas/`, likely `src/`, `tests/`) but no subdirectory CLAUDE.md files. This means Claude gets no scoped context when working in specific areas.

**Recommendations to reach A+:**

| Location | Purpose |
|---|---|
| `thestudioarc/CLAUDE.md` | Architecture conventions, doc format requirements |
| `thestudioarc/personas/CLAUDE.md` | Persona editing rules, 8-part epic structure, review checklist format |
| `src/CLAUDE.md` (if exists) | Source code conventions, import ordering, module patterns |
| `tests/CLAUDE.md` (if exists) | Test patterns, fixture conventions, coverage requirements |

---

### 11. CLAUDE.local.md — Grade: F (Missing)

**No local override template exists.** Developers have nowhere to put machine-specific instructions (local paths, personal preferences, debug settings) without modifying the shared CLAUDE.md.

**Recommendations to reach A+:**

1. Create `CLAUDE.local.md.example` as a template:
   ```markdown
   # CLAUDE.local.md — Personal Overrides (do not commit)

   ## Local Environment
   - Python: /path/to/your/venv
   - Database: localhost:5432

   ## Personal Preferences
   - Preferred test runner flags: --verbose --tb=short
   ```
2. Add `CLAUDE.local.md` to `.gitignore`
3. Document in CLAUDE.md that `CLAUDE.local.md` exists for overrides

---

## Cross-Cutting Issues

### Platform Parity Gap

The `.cursor/` directory has significantly richer configuration than `.claude/`:

| Feature | .cursor/ | .claude/ | Gap |
|---|---|---|---|
| MCP config | 4 servers | 1 server | Missing Context7, DocsMCP, Playwright |
| Rules | 7 `.mdc` files | 0 rule files | Full gap |
| Settings | N/A (Cursor uses own) | No `settings.json` | Full gap |
| Hooks binding | `hooks.json` | No binding | Hooks exist but are dead |
| Agents | 4 agents | 4 agents (same) | Parity |
| Skills | 11 skills | 11 skills (same) | Parity |

### Windows-Only Assumptions

Multiple files use Windows-specific paths and PowerShell:
- `.mcp.json`: `C:\Users\tappt\.local\bin\tapps-mcp.exe`
- All hooks: `.ps1` extension, PowerShell syntax
- `.cursor/mcp.json`: Windows paths

This makes the project non-portable to Linux, macOS, or CI environments.

### TAPPS Dependency

The project is heavily coupled to TAPPS MCP. While TAPPS provides valuable quality tooling, the configuration should gracefully degrade when TAPPS is unavailable (CI, new developer onboarding, different IDE).

---

## Priority Action Items (Ordered by Impact)

| Priority | Action | Impact | Effort |
|---|---|---|---|
| **P0** | Create `.claude/settings.json` with permissions and hook bindings | Unblocks hooks, fixes MCP permissions | 30 min |
| **P0** | Create `.claudeignore` | Reduces token waste, speeds up searches | 15 min |
| **P0** | Rewrite hooks as bash (`.sh`) and bind in settings.json | Makes hooks actually functional | 1 hour |
| **P1** | Fix `.mcp.json` to use portable paths | Makes project work cross-platform | 15 min |
| **P1** | Create `.claude/rules/` with modular topic rules | Moves bulk from CLAUDE.md, adds path-scoping | 1 hour |
| **P1** | Restructure CLAUDE.md to WHAT/WHY/HOW (<80 lines) | Improves Claude's comprehension and adherence | 45 min |
| **P2** | Add project-specific agents (Saga, Helm, Meridian) | Leverages existing persona system in Claude Code | 1 hour |
| **P2** | Add project-specific skills (/epic, /sprint, /review) | Makes persona workflow discoverable via slash commands | 45 min |
| **P2** | Add subdirectory CLAUDE.md files | Scoped context for different project areas | 30 min |
| **P3** | Add CLAUDE.local.md template + .gitignore entry | Enables personal overrides | 15 min |
| **P3** | Trim AGENTS.md to <100 lines | Reduces context bloat | 30 min |
| **P3** | Achieve platform parity (.cursor/ <-> .claude/) | Consistent experience across IDEs | 1 hour |

---

## What A+ Looks Like

A project scoring A+ across all categories would have:

```
project-root/
├── CLAUDE.md                          # <80 lines: WHAT/WHY/HOW + commands
├── CLAUDE.local.md.example            # Template for local overrides
├── AGENTS.md                          # <100 lines: essential workflow only
├── .claudeignore                      # Optimized context filtering
├── .mcp.json                          # Portable paths, all needed servers
├── .claude/
│   ├── settings.json                  # Permissions, hooks, MCP enablement
│   ├── settings.local.json            # (gitignored) personal overrides
│   ├── rules/
│   │   ├── tapps-pipeline.md          # Quality pipeline (moved from CLAUDE.md)
│   │   ├── personas.md               # Persona chain details
│   │   ├── python-quality.md          # Scoring categories, thresholds
│   │   ├── security.md               # Security gates
│   │   ├── testing.md                # Test patterns (paths: **/test_*)
│   │   └── api-design.md             # API conventions (paths: **/api/**)
│   ├── agents/
│   │   ├── tapps-reviewer.md          # (existing, fixed permissionMode)
│   │   ├── tapps-researcher.md        # (existing)
│   │   ├── tapps-validator.md         # (existing)
│   │   ├── tapps-review-fixer.md      # (existing)
│   │   ├── saga-epic-creator.md       # NEW: Saga persona agent
│   │   ├── helm-planner.md            # NEW: Helm persona agent
│   │   └── meridian-reviewer.md       # NEW: Meridian persona agent
│   ├── skills/
│   │   ├── (11 existing TAPPS skills)
│   │   ├── epic/SKILL.md             # NEW: /epic command
│   │   ├── sprint/SKILL.md           # NEW: /sprint command
│   │   └── review/SKILL.md           # NEW: /review command
│   └── hooks/
│       ├── session-start.sh           # Bash, registered in settings.json
│       ├── post-edit.sh               # Bash, matcher: Edit|Write
│       ├── stop.sh                    # Bash, with validation reminder
│       └── protect-files.sh           # NEW: PreToolUse blocker
├── thestudioarc/
│   ├── CLAUDE.md                      # Scoped: architecture doc conventions
│   └── personas/
│       └── CLAUDE.md                  # Scoped: persona editing rules
└── .gitignore                         # Includes CLAUDE.local.md, settings.local.json
```

---

*Generated by Claude Code best practices audit | 2026-03-10*
