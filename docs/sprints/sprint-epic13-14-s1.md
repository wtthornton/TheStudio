# Sprint Plan: Epics 13 + 14 — Agent Infrastructure & Content Enrichment, Sprint 1

**Planned by:** Helm
**Date:** 2026-03-10
**Status:** DRAFT — Awaiting Meridian review
**Epics:**
- `docs/epics/epic-13-agent-persona-infrastructure.md`
- `docs/epics/epic-14-agent-content-enrichment.md`
**Capacity:** Single developer, 1-week sprint (5 working days, ~6 productive hours/day = 30 hours)

---

## Sprint Goal (Testable Format)

**Objective:** Establish the agent infrastructure foundation — standardized frontmatter, a working linter, a canonical-to-multi-tool converter, drift reconciliation, CODEOWNERS protection, and CI enforcement — so that agent files are validated, synced, and protected on every PR. In parallel, deliver the two highest-value pipeline walkthrough examples and enrich the 4 thinnest agent definitions.

**Test:** After all stories are complete:
1. `python -c "import yaml; [yaml.safe_load(open(f).read().split('---')[1]) for f in __import__('glob').glob('.claude/agents/*.md')]"` succeeds and every file has `name`, `description`, `tools`, `model`, `maturity` fields.
2. `scripts/lint-agents.sh` exits 0 on all agent and persona files.
3. `scripts/convert-agents.sh --check` exits 0 (zero drift between canonical and generated files).
4. `grep -c "@your-team" CODEOWNERS` returns 0.
5. `thestudioarc/examples/walkthrough-simple-bugfix.md` contains 9 labeled pipeline stage sections, each with at least one JSON data snippet.
6. `thestudioarc/examples/walkthrough-feature-with-loopback.md` contains loopback signals with specific evidence and evidence comment recording loopback history.
7. Each of the 4 enriched agent files (tapps-researcher, tapps-reviewer, tapps-validator, compass-navigator) contains at least 2 `src/` path references, a tech stack section, and escalation rules.

**Constraint:** 5 working days. Agent/persona files, scripts, CI workflows, and documentation only. No application code changes. No new agents added. No changes to TAPPS MCP integration or its rules files.

---

## What's In / What's Out

**In Sprint 1 (10 stories, ~25 story points):**
- All 6 Epic 13 stories (13.1 through 13.6) — the full infrastructure chain
- Epic 14: Stories 14.1, 14.2, 14.7 — two walkthroughs + thin agent enrichment

**Deferred to Sprint 2 (~22 story points):**
- 14.3: Complex multi-expert walkthrough (5 pts) — valuable but lower priority than the happy-path and loopback examples
- 14.4: Persona chain to pipeline walkthrough (4 pts) — depends conceptually on having the simpler walkthroughs done first as reference material
- 14.5: Assign maturity levels to all agents (3 pts) — depends on 13.1; could fit Sprint 1 but creates Day 5 congestion
- 14.6: Build maturity summary generator (2 pts) — depends on 14.5
- **Rationale for cut line:** Epic 13 is the critical path — it establishes infrastructure that prevents drift going forward. Completing it fully in Sprint 1 avoids carrying half-built tooling across sprints. From Epic 14, we take the two foundational walkthroughs (14.1 happy path, 14.2 loopback — these are the most referenced examples) and 14.7 (independent, high value, no dependencies). Stories 14.5 and 14.6 are deferred not because they're hard but because they compete for Day 5 capacity with drift reconciliation (13.6) which is higher priority — drift is a live problem, maturity tracking is forward-looking.

---

## Ordered Backlog

### Day 1 (Stories 13.1 + 13.2 + 13.3) — ~7 hours

#### Story 13.1: Add Structured Frontmatter to All Agent Files (Est: 2 pts / 1.5 hours)

**Sequence rationale:** Everything else depends on standardized frontmatter. The linter validates it (13.2), the converter reads it (13.4), maturity fields need it (14.5). This is the foundation stone — do it first.

**Work:**
- Update all 11 files in `.claude/agents/` with YAML frontmatter containing `name`, `description`, `tools`, `model`, `maturity`
- Assign maturity values: `proven` for Saga, Helm, Meridian, Scout, Sentinel; `reviewed` for Compass, Forge, TAPPS agents
- Preserve all existing fields (`maxTurns`, `permissionMode`, `memory`, `skills`, `mcpServers`, `isolation`)

**Unknowns:** None significant. Current frontmatter structure is visible in the files.
**Estimate reasoning:** Mechanical edit across 11 files. 1 hour of edits + 30 min YAML validation.

#### Story 13.2: Build the Agent Linter Script (Est: 3 pts / 2.5 hours)

**Sequence rationale:** Must exist before CI (13.5) can use it. Building it on Day 1 lets us validate the frontmatter from 13.1 immediately — the linter is the acceptance test for the frontmatter work.

**Work:**
- Create `scripts/lint-agents.sh` — validates YAML frontmatter, required fields, body sections, content length
- Exit code 1 on errors, 0 on warnings-only or clean
- Output format: `ERROR <file>: <message>` / `WARN <file>: <message>` with summary
- Scans `.claude/agents/` and `thestudioarc/personas/` by default, accepts file arguments

**Unknowns:**
- YAML parsing in bash — likely use `python -c` inline or `yq` for robustness. Reference implementation in agency-agents uses bash+grep which is simpler but less reliable for YAML edge cases.

**Estimate reasoning:** Reference implementation exists. 1.5 hours of scripting + 1 hour of testing against current files (should find at least 1 issue pre-13.1).

#### Story 13.3: Add CODEOWNERS for Agent and Persona Directories (Est: 2 pts / 1 hour)

**Sequence rationale:** Independent of all other stories. Slot it on Day 1 to get protection in place early. Low effort, high value — prevents accidental unreviewed changes while the rest of the infrastructure is being built.

**Work:**
- Replace all `@your-team` placeholders in CODEOWNERS with actual GitHub username
- Add entries for `.claude/agents/**`, `.cursor/rules/persona-*.mdc`, `thestudioarc/personas/**`
- Verify branch protection settings on `master`

**Unknowns:**
- Requires admin access to verify/enable branch protection. If admin access is unavailable, the CODEOWNERS file changes can still merge and protection can be enabled later.

**Estimate reasoning:** Small, well-scoped. 30 min of edits + 30 min verifying branch protection.

---

### Day 2 (Story 13.4 + Start 14.7) — ~6 hours

#### Story 13.4: Build the Canonical-to-Multi-Tool Converter (Est: 5 pts / 4.5 hours)

**Sequence rationale:** This is the critical-path bottleneck. Stories 13.5 (CI), 13.6 (drift fix), and conceptually 14.5 (maturity) all depend on the converter existing. Front-load it on Day 2 after frontmatter is standardized.

**Work:**
- Create `scripts/convert-agents.sh` reading from `thestudioarc/personas/` (Saga, Helm, Meridian)
- Generate `.claude/agents/` files with Claude Code frontmatter
- Generate `.cursor/rules/persona-*.mdc` files with Cursor frontmatter
- Implement `--check` flag for CI drift detection
- Skip non-persona files (TAPPS rules, pipeline agents)

**Unknowns:**
- Mapping between canonical persona format and Claude Code frontmatter requires understanding exact field differences. Need to inventory current fields in both formats before writing mapping logic.
- Cursor `.mdc` frontmatter format (`description`, `globs`, `alwaysApply`) is different enough to require separate template logic.
- Whether bash is sufficient or Python would be more maintainable for YAML manipulation. Bash is consistent with lint script; Python is more robust for YAML.

**Estimate reasoning:** This is the largest story in Epic 13. Format mapping + template generation + diff logic for `--check`. 3 hours of implementation + 1.5 hours of testing against all 6 generated files. The reference in agency-agents `convert.sh` reduces unknowns.

#### Story 14.7: Enrich Thin Agent Definitions — Start (Est: 5 pts / 5 hours total, ~1.5 hours Day 2)

**Sequence rationale:** 14.7 has zero dependencies and can be worked in parallel or during testing gaps. Start it on Day 2 afternoon after the converter is drafted. It is creative work (reading architecture docs, writing domain context) that benefits from spreading across multiple days.

**Work (Day 2 portion):** Read architecture docs (`thestudioarc/00-overview.md`, `08-agent-roles.md`, `11-intent-layer.md`, `20-coding-standards.md`). Draft enrichment for `tapps-researcher.md` (tech stack reference, priority libraries, escalation rules).

---

### Day 3 (Story 14.1 + Continue 14.7) — ~6 hours

#### Story 14.1: Simple Bug Fix Pipeline Walkthrough (Est: 4 pts / 3.5 hours)

**Sequence rationale:** The walkthrough stories are independent of Epic 13 infrastructure. Day 3 is a natural break after the heavy converter work on Day 2. Writing the happy-path walkthrough first gives a template for the loopback walkthrough (14.2). Switching from scripting to documentation work also helps maintain focus.

**Work:**
- Create `thestudioarc/examples/walkthrough-simple-bugfix.md`
- 9 labeled sections (one per pipeline stage)
- JSON snippets showing key fields at each stage transition (TaskPacket, intent spec, verification signals, evidence comment)
- Realistic scenario: "Fix incorrect HTTP status code in intake webhook"

**Unknowns:**
- Need to verify exact TaskPacket field names from `src/models/` to write accurate JSON snippets
- Intent specification format — reference `thestudioarc/11-intent-layer.md` for structure

**Estimate reasoning:** Requires reading pipeline docs and writing realistic synthetic data for 9 stages. 2.5 hours of writing + 1 hour of review and cross-checking against architecture docs.

#### Story 14.7: Enrich Thin Agent Definitions — Continue (~2.5 hours)

**Work (Day 3 portion):** Draft enrichment for `tapps-reviewer.md` (quality categories, common patterns to flag, score interpretation) and `tapps-validator.md` (high-risk files, passing criteria, blocking issue format). Each file must stay under 400 lines.

---

### Day 4 (Stories 14.2 + 13.5 + Finish 14.7) — ~6 hours

#### Story 14.2: Feature with Loopback Pipeline Walkthrough (Est: 5 pts / 4 hours)

**Sequence rationale:** Must follow 14.1 (uses the same template/format). The loopback walkthrough is the second-most important example — it demonstrates the core resilience mechanism (gates fail closed, loopbacks carry evidence). Doing it on Day 4 gives time to absorb lessons from writing 14.1.

**Work:**
- Create `thestudioarc/examples/walkthrough-feature-with-loopback.md`
- Show Router selecting Developer + Security overlay
- Show Verification failure with specific lint errors
- Show loopback signal with evidence (file locations, error messages)
- Show QA catching missing acceptance criterion
- Show evidence comment with full loopback history

**Unknowns:**
- Exact verification signal format for loopback (reference `src/verification/` for signal structure)
- QA defect taxonomy categories (reference `src/qa/`)

**Estimate reasoning:** More complex than 14.1 due to branching paths and loopback mechanics. 3 hours of writing + 1 hour of review.

#### Story 13.5: CI Workflow for Agent Linting and Drift Detection (Est: 3 pts / 2 hours)

**Sequence rationale:** Depends on 13.2 (linter) and 13.4 (converter). By Day 4 both are complete and tested. CI is the enforcement mechanism — without it, the linter and converter are only as reliable as the developer remembering to run them.

**Work:**
- Create `.github/workflows/lint-agents.yml`
- Trigger on PRs modifying `.claude/agents/`, `.cursor/rules/persona-*`, `thestudioarc/personas/`
- Run `scripts/lint-agents.sh` — errors block, warnings report
- Run `scripts/convert-agents.sh --check` — drift blocks
- Use `actions/checkout@v4` with `fetch-depth: 0`

**Unknowns:** None significant. Standard GitHub Actions pattern.
**Estimate reasoning:** Straightforward CI workflow. 1.5 hours of YAML + 30 min of testing (push a test PR or use `act` locally).

#### Story 14.7: Enrich Thin Agent Definitions — Finish (~0.5 hours)

**Work (Day 4 portion):** Draft enrichment for `compass-navigator.md` (cross-cutting modules, FAQ). Final review of all 4 enriched files for consistency, line count (<400), and TheStudio-specificity.

---

### Day 5 (Story 13.6 + Integration Testing + Buffer) — ~4 hours work + 2 hours buffer

#### Story 13.6: Fix Existing Drift Between Persona Locations (Est: 4 pts / 3.5 hours)

**Sequence rationale:** Must be last in the Epic 13 chain because it uses the converter (13.4) to regenerate files, then validates with the linter (13.2) and CI workflow (13.5). This is the capstone that proves the infrastructure works end-to-end.

**Work:**
- Audit 9 files across 3 locations (thestudioarc/personas/, .claude/agents/, .cursor/rules/) for Saga, Helm, Meridian
- Resolve differences — establish `thestudioarc/personas/` as canonical source
- Document intentional differences as converter configuration
- Run converter to regenerate tool-specific files
- Run linter to validate
- Run `--check` to confirm zero drift

**Unknowns:**
- Scope of existing drift is unknown until audit. Could be minor (formatting) or significant (missing sections, conflicting instructions). Medium-confidence estimate accounts for this.
- Judgment calls on which version is authoritative when content diverges — plan: prefer the most complete version, verify against SOUL.md and TEAM.md for correctness.

**Estimate reasoning:** Reading and comparing 9 files (1.5 hours) + making reconciliation decisions and applying changes (1.5 hours) + running converter/linter/check cycle (30 min).

#### Integration Testing (~0.5 hours)

Run the full validation cycle end-to-end:
1. Lint all agent files
2. Run converter with `--check`
3. Verify CODEOWNERS has no placeholders
4. Spot-check walkthrough documents for completeness
5. Verify enriched agent files meet acceptance criteria (src/ paths, tech stack, escalation rules)

---

## Dependency Map

| Dependency | Status | Blocks |
|---|---|---|
| Epic 11 (Production Hardening) — no file overlap | Complete | Nothing blocked |
| `.claude/agents/*.md` — current agent files | Available | Starting point for 13.1 |
| `thestudioarc/personas/*.md` — canonical personas | Available | Starting point for 13.4, 13.6 |
| `.cursor/rules/persona-*.mdc` — Cursor personas | Available | Starting point for 13.4, 13.6 |
| `CODEOWNERS` — existing with placeholders | Available | Starting point for 13.3 |
| Repository admin access (branch protection) | Required for 13.3 | Non-blocking if unavailable — CODEOWNERS changes can merge, protection enabled later |
| Agency-agents reference scripts | External reference | Not a dependency — reference only |
| Architecture docs (`thestudioarc/`) | Available | Required reading for 14.1, 14.2, 14.7 |
| `src/models/` — TaskPacket definition | Available | Reference for walkthrough JSON snippets |

### Internal Story Dependencies (Sequence Constraints)

```
13.1 -----> 13.4 -----> 13.5
              |           ^
              |          /
              v         /
             13.6     13.2

13.3 (independent — Day 1)

14.1 -----> 14.2 (format template dependency, not code dependency)

14.7 (independent — spread across Days 2-4)
```

Full dependency chain:
- 13.1 must precede 13.4 (converter reads standardized frontmatter)
- 13.2 and 13.4 must precede 13.5 (CI runs both scripts)
- 13.4 must precede 13.6 (drift fix uses converter)
- 13.3 is independent — do early for protection
- 14.1 should precede 14.2 (establishes walkthrough format)
- 14.7 is independent — spread across slack time
- 14.1, 14.2, 14.7 have no Epic 13 dependencies

---

## Estimation Summary

| Story | Points | Hours | Confidence | Key Risk |
|---|---|---|---|---|
| 13.1 Frontmatter | 2 | 1.5 | High | Mechanical edits, low risk |
| 13.2 Linter | 3 | 2.5 | High | Reference impl exists |
| 13.3 CODEOWNERS | 2 | 1 | High | Admin access may be needed |
| 13.4 Converter | 5 | 4.5 | Medium | Format mapping complexity; largest script |
| 13.5 CI Workflow | 3 | 2 | High | Standard GitHub Actions |
| 13.6 Drift Fix | 4 | 3.5 | Medium | Drift scope unknown until audit |
| 14.1 Bugfix Walkthrough | 4 | 3.5 | Medium | Requires deep pipeline understanding |
| 14.2 Loopback Walkthrough | 5 | 4 | Medium | Branching paths add complexity |
| 14.7 Agent Enrichment | 5 | 5 | Medium | Spread across 3 days; architecture reading |
| **Total** | **33** | **28** | | |

### Big Estimates = Big Unknowns

- **13.4 (5 pts, Medium confidence):** The converter is the riskiest story. It must correctly map between three different frontmatter formats (canonical, Claude Code, Cursor). If the mapping logic is more complex than expected (e.g., fields that don't have 1:1 equivalents), this could expand by 1-2 hours. Mitigation: inventory all fields across formats before writing code.
- **14.7 (5 pts, Medium confidence):** Enrichment quality depends on understanding architecture deeply enough to write accurate, specific content. If architecture docs are incomplete in areas (e.g., reputation weights, outcome signals), enrichment for those areas will be thinner. Mitigation: spread across 3 days to allow time for reading and verification.
- **13.6 (4 pts, Medium confidence):** Drift scope is unknown. If the three persona locations have significant content divergence (not just formatting), reconciliation decisions take longer. Mitigation: do this last so the converter is battle-tested.

---

## Capacity Allocation

| Category | Points | Hours | % of 30-hour sprint |
|---|---|---|---|
| Planned story work | 33 | 28 | 93% |
| Buffer for unknowns | — | 2 | 7% |
| **Total** | | **30** | **100%** |

**Note on allocation:** At 93%, this sprint is tighter than the preferred 77-83% range. This is acceptable because:
1. Most stories are documentation and scripting with known patterns (not novel infrastructure like Temporal migration)
2. Story 14.7 is spread across slack time in Days 2-4, acting as natural flex capacity
3. The stories have high confidence estimates (7 of 10 are High confidence)

Buffer is allocated to:
1. Converter format mapping surprises (13.4) — up to 1 hour
2. Drift reconciliation judgment calls (13.6) — up to 1 hour

**If we run over:** Two compressible stories exist:
- **14.2 (Loopback Walkthrough)** can be deferred to Sprint 2 if Days 1-3 run long, freeing 4 hours. The simple bugfix walkthrough (14.1) still delivers value standalone.
- **14.7 (Agent Enrichment)** can ship with 3 of 4 agents enriched if time runs short. Compass-navigator (the last one scheduled) is the cut candidate.

**What won't fit this sprint:**
- 14.3: Complex multi-expert walkthrough (5 pts)
- 14.4: Persona chain to pipeline walkthrough (4 pts)
- 14.5: Maturity level assignment (3 pts) — good Sprint 2 opener since 13.1 frontmatter will be done
- 14.6: Maturity summary generator (2 pts) — follows 14.5

---

## Daily Plan Summary

| Day | Stories | Hours | Cumulative |
|---|---|---|---|
| 1 | 13.1 + 13.2 + 13.3 | ~5 | 5 |
| 2 | 13.4 + 14.7 (start) | ~6 | 11 |
| 3 | 14.1 + 14.7 (continue) | ~6 | 17 |
| 4 | 14.2 + 13.5 + 14.7 (finish) | ~6.5 | 23.5 |
| 5 | 13.6 + integration testing + buffer | ~4.5+buffer | 28-30 |

---

## Sprint 2 Preview (Not Committed)

Stories deferred from this sprint, in suggested order:
1. **14.5** — Assign maturity levels (3 pts). First: depends on 13.1 which is now complete.
2. **14.6** — Maturity summary generator (2 pts). Follows 14.5.
3. **14.3** — Multi-expert walkthrough (5 pts). Benefits from 14.1/14.2 format being established.
4. **14.4** — Persona chain walkthrough (4 pts). Last: references all other walkthroughs.
Total deferred: ~14 pts. Comfortable Sprint 2 with room for retro actions and any Sprint 1 carryover.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Converter format mapping more complex than expected | Medium | Medium (delays 13.4, cascades to 13.5/13.6) | Inventory all fields before coding; reference agency-agents convert.sh |
| Persona drift is extensive (significant content divergence) | Low-Medium | Medium (delays 13.6) | Scheduled last; converter is battle-tested by then; can defer part to Sprint 2 |
| Admin access unavailable for branch protection | Low | Low (13.3 partially effective) | CODEOWNERS changes merge regardless; protection enabled when access available |
| Walkthrough data structures inaccurate | Medium | Low (documentation, fixable) | Cross-reference src/models/ and architecture docs; review before finalizing |
| 93% allocation leaves insufficient buffer | Low-Medium | Medium (sprint overrun) | Two compressible stories identified (14.2, 14.7 partial); Day 1 light at 5 hours |

---

## Lessons from Prior Sprints

From Epic 11 sprint execution:
- **Script creation is routinely underestimated** by 30-50%. Estimates for 13.2 (linter) and 13.4 (converter) include this padding.
- **Documentation stories compress** when time is short. 14.2 is explicitly identified as the first-cut candidate.
- **Compose-related stories estimate well** — not directly applicable here, but the pattern of "mechanical edits estimate well" applies to 13.1 and 13.3.

---

## Meridian Review

**Status:** AWAITING REVIEW

This plan requires Meridian review before sprint commitment. Key questions for review:
1. Is the 93% allocation acceptable given the story confidence profiles?
2. Is the cut line correct (all Epic 13 + selected Epic 14 stories)?
3. Are the compressible story designations (14.2, 14.7 partial) reasonable?
4. Does the dependency chain have any hidden blockers?
