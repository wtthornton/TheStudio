# Sprint Plan: Epic 26 — File-Based Expert Packaging

**Planned by:** Helm
**Date:** 2026-03-13
**Status:** COMMITTED -- Meridian CONDITIONAL PASS (2026-03-13), retro reference added
**Epic:** `docs/epics/epic-26-file-based-expert-packaging.md`
**Sprint Duration:** 1 week (5 working days, 2026-03-17 to 2026-03-21)
**Capacity:** Single developer, 30 hours total (5 days x 6 productive hours), 80% allocation = 24 hours, 6 hours buffer

---

## Sprint Goal (Testable Format)

**Objective:** Complete Epic 26 in a single sprint: deliver a file-based expert packaging system where experts are defined as `EXPERT.md` manifests in the `experts/` directory, scanned at startup, synced to the database via content-hash versioning, hot-reloadable via admin API, and carrying their own context files. All five seed experts are migrated from `seed.py` to file-based format. Zero regression.

**Test:** After all stories (26.2 through 26.6) are complete:

1. `experts/` directory at the project root contains 5 subdirectories, each with a valid `EXPERT.md` that parses via `parse_expert_manifest()`.
2. `pytest tests/experts/` passes with tests covering scanner, registrar, migration, and context integration.
3. Application startup (via `src/app.py` lifespan) scans `experts/`, syncs all 5 experts to the database, and logs `SyncResult` with `created=5` on a fresh database.
4. A second startup produces `unchanged=5` (idempotent, no version churn).
5. `POST /admin/experts/reload` re-scans and returns JSON with created/updated/unchanged/deactivated counts.
6. `GET /admin/experts/registry` returns all 5 experts with `source_path` and `version_hash` populated.
7. Creating a new expert directory with a valid `EXPERT.md`, calling the reload endpoint, and querying the registry shows the new expert -- no Python code touched.
8. All existing tests pass (`pytest` green, `ruff check .` clean).
9. Existing routing tests produce identical results (Router is unaware of the registration source).

**Constraint:** 5 working days. Changes confined to `src/experts/`, `src/admin/`, `src/assembler/assembler.py`, `src/app.py`, `experts/` (new root directory), and test files. No changes to `src/routing/`, `src/experts/expert.py`, `src/experts/expert_crud.py`, or domain models. No new runtime dependencies (pyyaml already available). Story 26.1 is already implemented and tested -- this sprint covers 26.2 through 26.6.

---

## What's In / What's Out

**In this sprint (5 stories, ~22.5 estimated hours):**
- Story 26.2: Expert Directory Scanner
- Story 26.3: Expert Registration and Versioning
- Story 26.4: Migrate Seed Experts to File Format (end-to-end validation)
- Story 26.5: Hot Reload and Admin API
- Story 26.6: Context Pack Integration

**Already done:**
- Story 26.1: Expert Manifest Schema -- implemented and tested (`src/experts/manifest.py`, `tests/experts/test_manifest.py`)

**Out of scope:**
- File watcher via `watchdog` (optional dev convenience from 26.5 -- defer to avoid adding a dependency)
- Expert marketplace or remote registry
- Expert activation/deactivation via symlinks
- Changes to the Router algorithm or Assembler's expert invocation flow
- Epic 16 (Issue Readiness Gate) -- separate sprint(s)

---

## Dependency Review (30-Minute Pre-Planning)

### External Dependencies

| Dependency | Status | Impact if Missing | Mitigation |
|-----------|--------|-------------------|------------|
| `pyyaml` in dependency tree | Available (confirmed) | Cannot parse frontmatter | Already installed -- no action |
| Async DB session in app lifespan | Available (confirmed pattern in `src/app.py`) | Cannot sync at startup | Use existing `get_async_session` pattern |
| `expert_crud` functions (create, update_version, deprecate, search, get_by_name) | Implemented (`src/experts/expert_crud.py`) | Registrar has no DB layer | Already complete and tested |
| `ExpertCreate`, `ExpertClass`, `TrustTier` models | Implemented (`src/experts/expert.py`) | Cannot map manifests | Already complete |
| `src/admin/platform_router.py` exists | Must verify | Endpoints registered on wrong router | Check at story start; create or use existing admin router |

### Internal Dependencies (Story-to-Story)

```
26.1 (DONE) --> 26.2 --> 26.3 --> 26.4
                  |         |
                  v         v
                26.6      26.5
```

- **26.2 depends on 26.1** (scanner calls `parse_expert_manifest()`) -- SATISFIED
- **26.3 depends on 26.1 + 26.2** (registrar consumes `ScannedExpert` from scanner, calls `manifest_to_expert_create()` from manifest)
- **26.4 depends on 26.1 + 26.2 + 26.3** (migration wires scanner + registrar into startup)
- **26.5 depends on 26.2 + 26.3** (admin endpoints call scanner + registrar) -- can start after 26.3 is done
- **26.6 depends on 26.1 + 26.2 + 26.3** (context file validation in scanner, content storage in registrar, injection in assembler) -- can start after 26.3 is done

**Critical path:** 26.2 --> 26.3 --> 26.4. Stories 26.5 and 26.6 are parallel after 26.3.

---

## Ordered Work Items

### Day 1-2: Foundation Chain (Critical Path)

#### Item 1: Story 26.2 — Expert Directory Scanner
**Estimate:** 4 hours (5 story points, M size)
**Rationale for sequence:** Scanner is the first layer on top of the manifest schema. Without it, nothing else can discover expert directories.

**Key tasks:**
- Create `src/experts/scanner.py` with `SupportingFile`, `ScannedExpert`, `ScanError`, `ScanResult` dataclasses
- Implement `scan_expert_directories(base_path: Path) -> ScanResult`
- Shallow scan: immediate subdirectories only
- Skip directories without `EXPERT.md` (info log)
- Skip invalid manifests (warning log, add to errors)
- Collect supporting files (`.md` except `EXPERT.md`, `.json`, `.yaml`, `.yml`)
- Detect duplicate expert names
- Create `tests/experts/test_scanner.py` (10 test cases per story spec)
- All tests use `tmp_path` fixture

**Estimation reasoning:** Well-specified file system operations with clear inputs/outputs. The `parse_expert_manifest()` function from 26.1 handles the hard parsing work. Main complexity is error handling and duplicate detection. Low risk.

**Done when:** All 10 test cases pass. Scanner handles mixed valid/invalid directories. No fatal errors on bad manifests.

---

#### Item 2: Story 26.3 — Expert Registration and Versioning
**Estimate:** 5 hours (5 story points, M size)
**Rationale for sequence:** Must follow scanner. The registrar is the bridge between filesystem and database -- required by both migration (26.4) and admin API (26.5).

**Key tasks:**
- Create `src/experts/registrar.py` with `SyncResult` dataclass
- Implement `async sync_experts(session, scanned, deactivate_removed=False) -> SyncResult`
- Sync algorithm: fetch existing experts, compare by name and `_version_hash`
- Create new / update changed / skip unchanged / optionally deactivate removed
- Store `_version_hash` and `_source_path` in `definition` dict (metadata prefix convention)
- Update top-level `ExpertRow` fields when content changes (capability_tags, scope_description, trust_tier, tool_policy)
- Implement `_get_stored_hash()` helper
- Create `tests/experts/test_registrar.py` (9 test cases per story spec)

**Estimation reasoning:** Database interaction adds async complexity. The sync algorithm has several branches (create/update/skip/deactivate/legacy-without-hash). Tests need DB session mocking or fixtures. Bumped to 5 hours because the field-update-on-existing-row logic (beyond just version bumping) touches the `ExpertRow` directly, which the story spec calls out as unusual for the registrar.

**Unknowns:**
- How `search_experts()` returns version definitions -- need to verify if `ExpertRead` includes the `definition` from the latest version or just top-level fields. If it does not include definitions, `_get_stored_hash()` will need a separate version query.

**Done when:** All 9 test cases pass. New experts created, changed experts version-bumped, unchanged experts produce zero DB writes.

---

### Day 2-3: End-to-End Validation

#### Item 3: Story 26.4 — Migrate Seed Experts to File Format
**Estimate:** 6 hours (8 story points, L size)
**Rationale for sequence:** This is the integration story that proves 26.1-26.3 work together. Cannot begin until scanner and registrar are both complete and tested.

**Key tasks:**
- Create `experts/` directory at project root
- Create 5 expert subdirectories with `EXPERT.md` files, each mapping field-by-field from `seed.py` `SEED_EXPERTS` definitions
- Wire `src/app.py` lifespan to call `scan_expert_directories()` + `sync_experts()` at startup
- Add deprecation docstring to `src/experts/seed.py`
- Create `tests/experts/test_migration.py` (6 test cases)
- Verify all existing routing tests pass (zero regression)
- Run full `pytest` suite to confirm no breakage

**Estimation reasoning:** Largest story because it involves manual field mapping for 5 experts (each has detailed `definition` dicts with scope_boundaries, operating_procedure, expected_outputs, edge_cases, failure_modes), plus app.py integration and regression verification. The field mapping from `seed.py` to YAML frontmatter + markdown body requires careful attention -- each expert has ~20 lines of definition content. 6 hours accounts for the mapping work plus regression testing.

**Unknowns:**
- How the `definition` dict's structured fields (operating_procedure as list vs markdown body) map to the EXPERT.md format. The story says "naturally mapped" but each expert's operating_procedure, expected_outputs, edge_cases, and failure_modes need a clear mapping decision.
- Whether `src/app.py` currently calls `seed_experts()` anywhere or if it was always manual. (Epic says it was not called in lifespan -- need to verify.)

**Done when:** All 5 expert directories parse successfully. App startup loads all 5 experts. Existing routing tests pass unchanged. `seed.py` has deprecation docstring.

---

### Day 3-4: Operational Capabilities (Parallel Track)

#### Item 4: Story 26.5 — Hot Reload and Admin API
**Estimate:** 4 hours (5 story points, M size)
**Rationale for sequence:** After 26.3 (registrar) is complete, admin endpoints can call scanner + registrar on demand. Independent of 26.6.

**Key tasks:**
- Create `src/experts/config.py` with `get_experts_base_path()` (env var `EXPERTS_BASE_PATH` override)
- Add `POST /admin/experts/reload` endpoint to `src/admin/platform_router.py`
- Add `GET /admin/experts/registry` endpoint to `src/admin/platform_router.py`
- Define `ExpertSummary` Pydantic response model
- Extract `_source_path` and `_version_hash` from `definition` for the list response
- Refactor `src/app.py` to use `get_experts_base_path()`
- Create `tests/admin/test_expert_admin.py` (7 test cases)
- **DEFER** file watcher (`watchdog`) -- not building this. Dev convenience, not required for the sprint goal.

**Estimation reasoning:** Standard FastAPI endpoint work. Two endpoints, one response model, one config utility. The main nuance is routing the endpoints to `platform_router.py` (not `router.py`), and extracting metadata from the `definition` JSON field for the list response. 4 hours is sufficient because the scanner and registrar do all the heavy lifting.

**Done when:** Both endpoints work. Reload returns accurate SyncResult. Registry returns all experts with source_path and version_hash.

---

#### Item 5: Story 26.6 — Context Pack Integration
**Estimate:** 3.5 hours (5 story points, M size)
**Rationale for sequence:** After 26.3 (registrar stores context file contents in definition). Independent of 26.5. Touches the assembler -- smallest blast radius if left to last.

**Key tasks:**
- Add path validation to `src/experts/manifest.py` (reject absolute paths, reject `..` traversal)
- Update `src/experts/scanner.py` to validate `context_files` references exist
- Update registrar / `manifest_to_expert_create()` to include context file contents in `definition.context_files`
- Update `src/assembler/assembler.py` to inject context file contents into expert prompt
- Create example context file: `experts/security-reviewer/owasp-top-10-checklist.md`
- Update `experts/security-reviewer/EXPERT.md` to reference it
- Create `tests/experts/test_context_integration.py` (8 test cases)

**Estimation reasoning:** Touches 4 existing files plus creates test file and example content file. Each touch is small -- a validator, a file-existence check, a dict-population step, and a prompt-context injection. The assembler change is the most sensitive since it affects the pipeline, but it is additive (checks for a dict key, appends if present). 3.5 hours accounts for careful assembler integration.

**Unknowns:**
- Whether the assembler's current prompt-building flow has a clear injection point for expert-specific context. Need to read `src/assembler/assembler.py` at implementation time.

**Done when:** Context files referenced in manifests are validated at scan time, stored in DB, and injected into expert prompt context. Path traversal is rejected. Experts without context_files are unaffected.

---

## Capacity Summary

| Story | Estimate | Day | Cumulative |
|-------|----------|-----|------------|
| 26.2 Scanner | 4.0h | Day 1 | 4.0h |
| 26.3 Registrar | 5.0h | Day 1-2 | 9.0h |
| 26.4 Migration | 6.0h | Day 2-3 | 15.0h |
| 26.5 Admin API | 4.0h | Day 3-4 | 19.0h |
| 26.6 Context Integration | 3.5h | Day 4 | 22.5h |
| **Total** | **22.5h** | | **75% of 30h capacity** |
| **Buffer** | **7.5h** | | **25%** |

**Allocation rationale:** 75% allocation leaves 25% buffer. This is conservative. The unknowns around registrar DB interaction (26.3) and assembler integration (26.6) justify the extra buffer. If 26.3's `ExpertRead` does not include version definitions, the registrar needs a version-query helper, which could add 1-2 hours. The buffer absorbs this.

---

## Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | `ExpertRead` model does not include `definition` from latest version -- registrar cannot extract stored hash | Medium | High (blocks 26.3) | Check `ExpertRead` model at start of 26.3. If missing, add `get_expert_versions()` call to fetch latest definition. Fallback: query `ExpertVersionRow` directly. |
| 2 | `definition` dict structure in migrated experts diverges from `seed.py` structure, breaking Router or Assembler | Medium | High (breaks routing) | Run existing routing tests after each migration step. Snapshot the `seed.py` definition dicts and compare field-by-field. |
| 3 | `src/admin/platform_router.py` does not exist or has a different pattern than expected | Low | Low (1h rework) | Check file structure before starting 26.5. If it does not exist, register endpoints on the existing admin router with the specified paths. |
| 4 | Assembler has no clear injection point for expert-specific context | Medium | Medium (2h rework for 26.6) | Read `src/assembler/assembler.py` before starting 26.6. If no injection point, add context as a new key in the definition dict that the assembler reads during prompt construction. |
| 5 | Line ending normalization causes hash differences between developer machines | Low | Low (version churn) | Already mitigated in `compute_version_hash()` which normalizes `\r\n` and `\r` to `\n`. Covered by test. |

---

## Compressible Stories (What Gets Cut If Time Runs Short)

**Two compressible stories identified:**

1. **Story 26.6 (Context Pack Integration) -- first to defer.** The core system works without context file injection. Experts load and route correctly. Context integration is additive enrichment, not structural. Defer to a follow-up if day 4 is overrun. **Impact of deferral:** Experts work but lack bundled domain context. The security-reviewer expert still functions; it just does not get OWASP checklist content injected into its prompt.

2. **Story 26.5 file watcher portion -- already deferred.** The `watchdog`-based file watcher is explicitly out of scope. The reload endpoint is the minimum viable hot-reload mechanism.

If both 26.5 and 26.6 are at risk, prioritize 26.5 (admin API) over 26.6 (context integration). The admin API provides operational visibility; context integration is enrichment.

---

## Epic 16 — Issue Readiness Gate: Not This Sprint

Epic 16 is Meridian-approved and ready, but it is a 2-sprint epic (Sprint 17 + Sprint 18 per the epic's own mapping). It has 9 stories across 2 sprints with fundamentally different concerns (scoring engine, pipeline workflow integration, Temporal signal waits, webhook handler expansion, calibration loop, Admin UI).

**Sequencing rationale:** Complete Epic 26 fully before starting Epic 16. Reasons:
1. Epic 26 is a single-sprint, low-risk, infrastructure epic with a clean dependency chain. Finishing it first clears the deck.
2. Epic 16 requires Temporal workflow modification, webhook handler expansion, and TaskPacket model changes -- higher risk, higher blast radius.
3. Epic 26 has synergy with Epic 23 (Unified Agent Framework). Delivering file-based experts before Epic 23 begins means the Agent Framework can consume `EXPERT.md` system prompt templates from day one.
4. Starting Epic 16 mid-sprint would split context and create a task-switching tax.

**Epic 16 Sprint 17 plan will be created after this sprint is complete** (week of 2026-03-24).

---

## Definition of Done (Sprint Level)

- [ ] All 5 stories (26.2-26.6) implemented and tested
- [ ] All existing tests pass (`pytest` green)
- [ ] `ruff check .` clean
- [ ] 5 expert directories under `experts/` with valid `EXPERT.md` files
- [ ] Application startup loads experts from filesystem (not `seed.py`)
- [ ] Admin reload + registry endpoints functional
- [ ] Context files validated and injected into expert prompt context
- [ ] Sprint plan reviewed by Meridian before execution begins

---

## Retro Reference

This is the first sprint for the Epic 26 workstream. No prior retro exists to draw from. Lessons from earlier sprints (Epics 19-22) are reflected in: 25% buffer allocation, explicit unknowns with mitigations, and compressible story identification — patterns established in Epics 21-22 sprint plans.

---

## Meridian Review Required

This sprint plan requires Meridian review before commit. Specifically:

1. Is the single-sprint scope for all remaining Epic 26 stories realistic at 75% allocation?
2. Is the sequencing (Epic 26 complete before Epic 16 begins) the right call?
3. Are the identified unknowns (ExpertRead definition access, assembler injection point) adequately mitigated?
4. Does the compressible-stories strategy (cut 26.6 first) protect the sprint goal?
