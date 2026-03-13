# Story 26.4 — Migrate Seed Experts to File Format

> **As a** platform developer,
> **I want** all five seed experts migrated from `seed.py` to file-based `EXPERT.md` manifests and the startup hook rewired to use the scanner/registrar,
> **so that** the `experts/` directory is the single source of truth and `seed.py` is no longer needed.

**Purpose:** This is the end-to-end validation story. It proves that the manifest schema (26.1), scanner (26.2), and registrar (26.3) work together to replace the existing Python-based seeding. If the Router produces identical results after migration, the system is correct.

**Intent:** Create `experts/` directory at the project root with five subdirectories — one for each seed expert. Each contains an `EXPERT.md` with YAML frontmatter matching the current `seed.py` definitions. Deprecate `seed.py` (keep the file, remove the startup call). Wire the app lifespan to call `scan_expert_directories()` + `sync_experts()` at startup. Verify all routing tests still pass.

**Points:** 8 | **Size:** L
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.1-26.4)
**Depends on:** Story 26.1, Story 26.2, Story 26.3

---

## Description

The five experts currently defined in `src/experts/seed.py` are:
1. `security-review` (ExpertClass.SECURITY)
2. `qa-validation` (ExpertClass.QA_VALIDATION)
3. `technical-review` (ExpertClass.TECHNICAL)
4. `compliance-check` (ExpertClass.COMPLIANCE)
5. `process-quality` (ExpertClass.PROCESS_QUALITY)

Each must be converted to an `EXPERT.md` file with:
- YAML frontmatter containing all fields from the `ExpertCreate` instance
- A markdown body containing the system prompt template (derived from the `definition.operating_procedure` and `scope_description`)
- The `definition` fields (scope_boundaries, expected_outputs, operating_procedure, edge_cases, failure_modes) encoded in the YAML frontmatter under a `definition` key or naturally mapped to frontmatter fields

The startup hook in `src/app.py` must be extended to call `scan_expert_directories()` + `sync_experts()`. Note: `seed_experts()` is not currently called in the app lifespan — it was invoked manually or via migration scripts. This story adds the scanner/registrar as the canonical startup path.

## Tasks

- [ ] Create `experts/` directory at project root
- [ ] Create `experts/security-reviewer/EXPERT.md`:
  - Map all fields from `SEED_EXPERTS[0]` in `seed.py`
  - name: `security-review`
  - class: `security`
  - capability_tags: `[auth, secrets, crypto, injection]`
  - trust_tier: `probation`
  - description: from `scope_description`
  - tool_policy: from `tool_policy`
  - constraints: from `definition.scope_boundaries`
  - Markdown body: system prompt derived from `operating_procedure`, `expected_outputs`, `edge_cases`, `failure_modes`
- [ ] Create `experts/qa-validation/EXPERT.md`:
  - Map all fields from `SEED_EXPERTS[1]` in `seed.py`
  - name: `qa-validation`
  - class: `qa_validation`
  - capability_tags: `[intent_validation, acceptance_criteria, defect_classification]`
  - trust_tier: `probation`
- [ ] Create `experts/technical-review/EXPERT.md`:
  - Map all fields from `SEED_EXPERTS[2]` in `seed.py`
  - name: `technical-review`
  - class: `technical`
  - capability_tags: `[architecture, code_quality, performance, design_review]`
  - trust_tier: `probation`
- [ ] Create `experts/compliance-check/EXPERT.md`:
  - Map all fields from `SEED_EXPERTS[3]` in `seed.py`
  - name: `compliance-check`
  - class: `compliance`
  - capability_tags: `[regulatory, data_handling, audit_trail, retention]`
  - trust_tier: `probation`
- [ ] Create `experts/process-quality/EXPERT.md`:
  - Map all fields from `SEED_EXPERTS[4]` in `seed.py`
  - name: `process-quality`
  - class: `process_quality`
  - capability_tags: `[release_readiness, operational_hygiene, runbook, incident_response]`
  - trust_tier: `probation`
- [ ] Modify `src/app.py` lifespan:
  - Replace `seed_experts(session)` call with:
    ```python
    from src.experts.scanner import scan_expert_directories
    from src.experts.registrar import sync_experts
    from pathlib import Path

    base_path = Path(__file__).resolve().parent.parent / "experts"
    scan_result = scan_expert_directories(base_path)
    if scan_result.errors:
        for err in scan_result.errors:
            logger.warning("Expert scan error", directory=str(err.directory), error=err.error)
    sync_result = await sync_experts(session, scan_result.experts)
    logger.info("Expert sync complete", **sync_result.__dict__)
    ```
  - Keep `seed.py` import removed or commented out with deprecation note
- [ ] Add deprecation docstring to `src/experts/seed.py`:
  - ```python
    """DEPRECATED: Seed experts are now defined as EXPERT.md files in the experts/ directory.
    This module is kept for reference only. See Epic 26 — File-Based Expert Packaging.
    """
    ```
- [ ] Add `experts/` to the project's known directories (update any tooling config if needed)
- [ ] Create `tests/experts/test_migration.py`:
  - Test: all 5 expert directories exist with EXPERT.md files
  - Test: each EXPERT.md parses successfully via `parse_expert_manifest()`
  - Test: each manifest's fields match the corresponding `SEED_EXPERTS` entry
  - Test: `manifest_to_expert_create()` produces `ExpertCreate` equivalent to seed.py definitions
  - Test: startup scan + sync creates all 5 experts in the database
  - Test: routing tests still pass (import and run existing routing test scenarios)
- [ ] Verify all existing tests pass (especially `tests/unit/test_workflow.py`, routing tests, and any test that depends on seeded experts)

## Acceptance Criteria

- [ ] Five expert directories exist under `experts/` with valid `EXPERT.md` files
- [ ] Each manifest's fields match the corresponding `seed.py` definition
- [ ] `src/app.py` lifespan calls scanner + registrar at startup (not `seed_experts()`)
- [ ] `seed.py` is deprecated with a docstring explaining the change
- [ ] All five experts are registered in the database after startup
- [ ] Existing routing tests pass without modification
- [ ] All existing tests pass (zero regression)

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | All manifests parse | `experts/*/EXPERT.md` | 5 valid `ExpertManifest` objects |
| 2 | Fields match seed.py | Manifest for `security-review` | name, class, tags, tier, description all match |
| 3 | Startup loads experts | App lifespan runs | 5 experts in DB with `_version_hash` set |
| 4 | Routing unchanged | Same inputs as existing routing tests | Same `ConsultPlan` results |
| 5 | Idempotent startup | App lifespan runs twice | No duplicate experts, no version bumps |
| 6 | seed.py not called | App startup | No import of `seed_experts` in active code path |

## Files Affected

| File | Action |
|------|--------|
| `experts/security-reviewer/EXPERT.md` | Create |
| `experts/qa-validation/EXPERT.md` | Create |
| `experts/technical-review/EXPERT.md` | Create |
| `experts/compliance-check/EXPERT.md` | Create |
| `experts/process-quality/EXPERT.md` | Create |
| `src/app.py` | Modify (replace seed_experts call) |
| `src/experts/seed.py` | Modify (add deprecation docstring) |
| `tests/experts/test_migration.py` | Create |

## Technical Notes

- The `experts/` directory is at the project root, not under `src/`. The path resolution in `app.py` uses `Path(__file__).resolve().parent.parent / "experts"` (from `src/app.py` up two levels to project root).
- Expert directory names do not need to match expert names. The `name` field in the YAML frontmatter is the canonical identifier. However, for clarity, directory names should be the slugified expert name.
- The first startup after migration will see all 5 experts as "created" (if the DB is fresh) or "updated" (if seed.py previously ran). Subsequent startups will see "unchanged" for all 5. This is correct behavior.
- If seed.py previously ran and created experts without `_version_hash`, the registrar (Story 26.3) treats them as changed and updates them. This is the expected migration path.
- The `definition` dict in the database after migration should contain all the same keys as the seed.py definition, plus `_version_hash`, `_source_path`, and `system_prompt_template`.
