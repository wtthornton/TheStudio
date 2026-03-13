# Epic 26 — File-Based Expert Packaging: Make Expert Onboarding a File Operation, Not a Code Change

**Author:** Saga
**Date:** 2026-03-13
**Status:** Draft — Awaiting Meridian Review
**Target Sprint:** Single sprint (estimated 2-3 weeks)
**Prerequisites:** None (can be done independently)

---

## 1. Title

File-Based Expert Packaging: Make Expert Onboarding a File Operation, Not a Code Change — Define experts as `EXPERT.md` manifest directories under `experts/` at the project root, with YAML frontmatter for identity/capabilities and markdown body for system prompt templates, loaded at startup and hot-reloadable via admin endpoint, so that adding a new expert never requires touching Python code.

## 2. Narrative

Adding a new expert to TheStudio today requires a developer who understands four things: the `ExpertCreate` Pydantic model, the `ExpertClass` and `TrustTier` enums, the `seed.py` seeding function, and the deployment cycle. That is three things too many. The result is that expert definitions are locked inside Python source files, invisible to anyone who cannot read code, and require a full redeploy to change.

This is a bottleneck that gets worse as the platform scales. Every new domain TheStudio enters — a new service team, a new compliance regime, a new partner API — needs new experts. If each expert requires a code change, a review, and a deploy, the expert library grows at the speed of the deployment pipeline, not the speed of the business.

The fix is stolen shamelessly from thepopebot's skills system: each skill is a directory with a manifest file and supporting context. Skills are activated by symlinking into `active/`. No code change, no deploy, no understanding of internal schemas. The manifest is the expert.

For TheStudio, this means:
- Each expert is a directory under `experts/` at the project root (e.g., `experts/security-reviewer/`)
- Each directory contains an `EXPERT.md` file with YAML frontmatter declaring identity, class, capabilities, trust tier, constraints, and tool policy
- The markdown body after the frontmatter is the system prompt template
- Supporting files (context packs, reference documents, example outputs) live alongside the manifest
- A scanner reads all expert directories at startup and syncs them to the Expert Library database
- Changes to manifest files are detected by content hash; only changed experts trigger re-registration
- An admin endpoint allows hot reload without restart

What does not change: the Router's selection algorithm, the Expert model in the database, the Assembler's consumption of expert outputs, or any pipeline contract. This epic changes how experts are packaged and registered. It does not change how they are selected or used.

The five seed experts currently hardcoded in `src/experts/seed.py` — security-review, qa-validation, technical-review, compliance-check, and process-quality — are migrated to file-based format. `seed.py` is deprecated. From this point forward, the `experts/` directory is the single source of truth for expert definitions.

### Why Now

Epic 23 (Unified Agent Framework) introduces `AgentConfig` with `system_prompt_template` as a first-class field. File-based experts align perfectly: the markdown body of `EXPERT.md` becomes the system prompt template that the Agent Framework consumes. Building this now means Epic 23's agent conversions can reference file-based expert definitions from day one instead of retrofitting later.

## 3. References

| Artifact | Location |
|----------|----------|
| Expert model (ExpertClass, TrustTier, ExpertRead) | `src/experts/expert.py` |
| Expert CRUD operations | `src/experts/expert_crud.py` |
| Current expert seeding | `src/experts/seed.py` |
| Expert Router | `src/routing/router.py` |
| Service Context Packs (related pattern) | `src/context/packs.py`, `src/context/service_context_pack.py` |
| Assembler (consumes expert outputs) | `src/assembler/assembler.py` |
| Expert Library architecture | `thestudioarc/10-expert-library.md` |
| Expert Taxonomy | `thestudioarc/02-expert-taxonomy.md` |
| Expert Router architecture | `thestudioarc/05-expert-router.md` |
| thepopebot skills system (inspiration) | External reference — directory-per-skill with YAML manifest |
| App lifespan (startup hooks) | `src/app.py` |
| Admin router (admin endpoints) | `src/admin/router.py` |
| Coding standards | `thestudioarc/20-coding-standards.md` |

## 4. Acceptance Criteria

### Expert Manifest

1. **`EXPERT.md` schema is defined and enforced.** A Pydantic model `ExpertManifest` in `src/experts/manifest.py` parses YAML frontmatter from markdown files. Required fields: `name` (str), `class` (ExpertClass), `capability_tags` (list[str], non-empty), `description` (str). Optional fields: `trust_tier` (TrustTier, default `shadow`), `constraints` (list[str]), `tool_policy` (dict), `context_files` (list[str] — relative paths to supporting documents). The markdown body after frontmatter is captured as `system_prompt_template`. A `version_hash` is computed from the full file content (frontmatter + body) using SHA-256.

2. **Manifest validation catches errors early.** Invalid class values, empty capability_tags, missing required fields, and duplicate names across directories all produce clear error messages with the file path included.

### Directory Scanning

3. **Scanner discovers all expert directories.** `scan_expert_directories(base_path)` in `src/experts/scanner.py` walks all immediate subdirectories of `base_path`, finds `EXPERT.md` files, parses each manifest, and collects supporting files (`.md` files other than `EXPERT.md`, plus `.json` and `.yaml` files) as context attachments. Directories without a valid `EXPERT.md` are skipped with a warning log.

4. **Scanner is resilient.** A single invalid manifest does not prevent other experts from loading. Errors are logged with the directory path and parse error detail.

### Registration and Versioning

5. **Sync creates, updates, and optionally deactivates experts.** `sync_experts(session, manifests)` in `src/experts/registrar.py` compares manifest `version_hash` values against stored hashes. New manifests create new experts via `expert_crud.create_expert()`. Changed hashes trigger `expert_crud.update_expert_version()` with the new definition. Removed directories optionally deprecate the corresponding expert (configurable via `deactivate_removed` parameter, default `False`).

6. **Version tracking works correctly.** When an expert's `EXPERT.md` content changes, the expert's `current_version` increments and a new `ExpertVersionRow` is created. When content has not changed, no database write occurs.

### Migration

7. **All five seed experts exist as file-based directories.** `experts/security-reviewer/`, `experts/qa-validation/`, `experts/technical-review/`, `experts/compliance-check/`, and `experts/process-quality/` each contain an `EXPERT.md` with frontmatter matching the current `seed.py` definitions. The `seed.py` module is deprecated (kept but not called).

8. **Startup hook loads file-based experts.** The application lifespan in `src/app.py` is extended to call `scan_expert_directories()` followed by `sync_experts()` at startup. Note: `seed_experts()` is defined in `src/experts/seed.py` but is not currently called in the lifespan — it was previously invoked manually or via migration. This story adds the scanner/registrar call as the canonical startup path; `seed.py` is deprecated but kept for reference.

9. **Router still selects migrated experts correctly.** After migration, the Router produces identical `ConsultPlan` results for the same inputs. Existing routing tests pass without modification.

### Hot Reload and Admin API

10. **Reload endpoint works.** `POST /admin/experts/reload` re-scans expert directories and syncs changes to the database. Returns a JSON response listing created, updated, unchanged, and (optionally) deactivated experts. This endpoint is registered on `src/admin/platform_router.py` (the platform API router), not on `src/admin/router.py`.

11. **List endpoint works.** `GET /admin/experts/registry` returns all registered experts with their source path (file-based or legacy) and current version hash. Note: the path is `/admin/experts/registry` (not `/admin/experts`) to avoid conflict with any existing expert admin endpoints.

### Context Pack Integration

12. **Expert manifests can reference context files.** When `context_files` lists relative paths (e.g., `["api-patterns.md", "security-checklist.md"]`), the scanner verifies those files exist in the expert directory and attaches their contents to the manifest. Missing referenced files produce a validation error.

13. **Context file contents are available to the Assembler.** When the pipeline invokes an expert, the expert's context file contents are included in the `definition` field passed to the expert's prompt context, keyed by filename.

### Cross-Cutting

14. **No changes to domain models.** `ExpertRow`, `ExpertVersionRow`, `ExpertCreate`, `ExpertRead`, and all other existing models are unchanged. The manifest maps to existing models, not the reverse. The `version_hash` is stored inside the `definition` JSON field of `ExpertVersionRow` (e.g., `definition["version_hash"]`), not as a new column. The registrar compares the incoming manifest hash against `definition["version_hash"]` of the current version to detect changes.

15. **No arbitrary code execution.** Expert directories contain data (markdown, YAML, JSON). No Python files are loaded or executed from expert directories.

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| YAML frontmatter parsing is fragile — malformed YAML crashes the scanner | Medium | Medium — prevents expert loading | Use `yaml.safe_load` with try/except per file; skip invalid, log error, continue scanning |
| Name collision between file-based and legacy seed experts during migration | Medium | High — duplicate key error in DB | Migration story explicitly handles the transition: check if name exists before create, update version if hash differs |
| File watcher in dev mode causes excessive reloads on rapid saves | Low | Low — dev inconvenience | Debounce file watcher with 2-second cooldown; watcher is optional and dev-only |
| Supporting files referenced in manifest are missing or moved | Medium | Medium — expert loads without context | Validate `context_files` paths at scan time; reject manifest if referenced files are missing |
| Hash computation differs across platforms (line endings) | Low | Medium — version churn on cross-platform teams | Normalize line endings to `\n` before hashing |
| `experts/` directory at project root conflicts with Python packaging conventions | Low | Low — cosmetic | Directory is at project root, not under `src/`; no `__init__.py`, not a Python package |

## 5. Constraints & Non-Goals

### Constraints

- **Experts are data, not code.** No Python files in expert directories. No dynamic imports. No plugin system. Expert directories contain markdown, YAML, and JSON only.
- **Existing Expert model schema is unchanged.** The manifest maps to `ExpertCreate` for registration. No new columns, no schema migration.
- **Router algorithm is unchanged.** This epic changes how experts are packaged and registered. The Router's selection logic (trust tier scoring, reputation weighting, budget limits) is not modified.
- **`experts/` lives at the project root.** Not under `src/` (it is not Python source). Not under `docs/` (it is operational configuration). The project root makes it a peer of `src/`, `tests/`, and `docs/`.
- **Python 3.12+, existing dependencies only.** `pyyaml` is already a dependency. `watchdog` may be added for optional dev file watching (evaluate before adding).
- **All existing tests must pass.** The migration must not break routing, expert CRUD, or any pipeline test.

### Non-Goals

- **Not building a marketplace or remote expert registry.** Experts are local directories in the repo. Remote fetching, versioning beyond content hash, and multi-repo expert sharing are future work.
- **Not adding expert activation/deactivation via symlinks.** Unlike thepopebot's `active/` symlink pattern, all experts in the `experts/` directory are active. Deactivation is via the existing `lifecycle_state` field in the database.
- **Not building a UI for expert authoring.** The `EXPERT.md` file is the authoring interface. A GUI editor is out of scope.
- **Not changing how the Assembler invokes experts.** The Assembler receives expert outputs from the Agent Framework. How those outputs are generated (system prompt template, tool access) is governed by Epic 23, not this epic.
- **Not building expert testing or qualification.** Validating that an expert produces quality outputs is a separate concern (Expert Recruiter qualification harness). This epic validates manifest syntax and schema, not expert behavior.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts epic scope, reviews AC completion |
| Tech Lead | Backend Engineer (TBD — assign before sprint start) | Owns manifest schema, scanner, registrar, and migration |
| QA | QA Engineer (TBD — assign before sprint start) | Validates AC, verifies migration preserves routing behavior |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plan |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Expert onboarding time | New expert registered via reload endpoint without Python code changes | Scripted test: create expert directory, write manifest, POST /admin/experts/reload, verify expert in GET /admin/experts/registry response |
| Zero code changes for new experts | 0 Python files modified to add an expert | Code review: new expert additions only touch `experts/` directory |
| Migration completeness | 5/5 seed experts migrated to file format | Database query: all 5 experts present with `definition->>'version_hash'` populated in `expert_versions` table |
| Routing stability | 100% identical ConsultPlan results before and after migration | Existing routing tests pass; snapshot test compares pre/post selection for same inputs |
| Hot reload works | Reload endpoint syncs changes within 2 seconds | Integration test: modify EXPERT.md, call reload, verify updated version in DB |
| Scanner resilience | Invalid manifests do not block valid experts | Unit test: mixed valid/invalid directories, all valid experts load |
| Zero regression | All pre-existing tests pass | CI green on merge |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `src/experts/manifest.py` | **New file** — `ExpertManifest` Pydantic model for YAML frontmatter parsing |
| `src/experts/scanner.py` | **New file** — `scan_expert_directories()` function |
| `src/experts/registrar.py` | **New file** — `sync_experts()` function |
| `src/experts/seed.py` | **Deprecated** — no longer called at startup; kept for reference |
| `src/experts/expert.py` | **Unchanged** — existing models are consumed, not modified |
| `src/experts/expert_crud.py` | **Unchanged** — existing CRUD functions are called by registrar |
| `src/app.py` | **Modified** — lifespan extended to call scanner + registrar at startup (seed_experts was not previously called here) |
| `src/admin/platform_router.py` | **Modified** — add `POST /admin/experts/reload` and `GET /admin/experts/registry` endpoints |
| `src/routing/router.py` | **Unchanged** — Router consumes experts from DB; source of registration is transparent |
| `src/assembler/assembler.py` | **Minor modification** — include context file contents in expert prompt context |
| `experts/` (project root) | **New directory** — contains expert subdirectories with EXPERT.md manifests |
| `experts/security-reviewer/EXPERT.md` | **New file** — migrated from seed.py |
| `experts/qa-validation/EXPERT.md` | **New file** — migrated from seed.py |
| `experts/technical-review/EXPERT.md` | **New file** — migrated from seed.py |
| `experts/compliance-check/EXPERT.md` | **New file** — migrated from seed.py |
| `experts/process-quality/EXPERT.md` | **New file** — migrated from seed.py |

### Assumptions

1. **`pyyaml` is available.** It is already in the dependency tree. No new dependency needed for YAML parsing.
2. **Startup time is acceptable.** Scanning 5-20 expert directories and syncing to the database adds negligible startup overhead (< 500ms).
3. **Content-hash versioning is sufficient.** SHA-256 of the full `EXPERT.md` file content detects all meaningful changes. Semantic versioning or manual version numbers are not needed.
4. **Database session is available at startup.** The lifespan function in `src/app.py` already has access to async sessions for seeding. The scanner/registrar uses the same pattern.
5. **Expert directories are committed to the repo.** They are not gitignored. This means expert definitions are version-controlled and reviewable, which is a feature, not a limitation.
6. **The `definition` JSON field in `ExpertVersionRow` can store manifest-derived data.** The existing schema uses a generic JSON column; the manifest's scope boundaries, operating procedure, expected outputs, edge cases, and failure modes map naturally to this structure.

### Dependencies

- **Upstream:** None. This epic is independent of all other epics.
- **Synergy with:** Epic 23 (Unified Agent Framework) — file-based experts provide `system_prompt_template` that the Agent Framework consumes. Building this first or in parallel avoids retrofitting.
- **Downstream unblocks:** Any future expert addition becomes a file operation. Expert Recruiter (when it creates new experts) can generate `EXPERT.md` files instead of Python code.

---

## Story Map

Stories are ordered as vertical slices: the manifest schema is foundational, the scanner builds on it, registration connects to the database, migration proves the system end-to-end, and then hot reload and context integration add operational capability.

### Sprint 1: Schema + Scanner + Registration + Migration

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 26.1 | **Expert Manifest Schema** — Define `ExpertManifest` Pydantic model for YAML frontmatter parsing | S | Foundation for all stories | `src/experts/manifest.py`, `tests/experts/test_manifest.py` |
| 26.2 | **Expert Directory Scanner** — Scan directories for EXPERT.md, parse manifests, collect supporting files | M | Discovery mechanism | `src/experts/scanner.py`, `tests/experts/test_scanner.py` |
| 26.3 | **Expert Registration and Versioning** — Sync manifests to DB with hash-based version detection | M | Database integration | `src/experts/registrar.py`, `tests/experts/test_registrar.py` |
| 26.4 | **Migrate Seed Experts to File Format** — Create expert directories, deprecate seed.py, wire startup | L | End-to-end validation | `experts/*/EXPERT.md`, `src/app.py`, `tests/experts/test_migration.py` |

### Sprint 1 continued: Operational Capabilities

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 26.5 | **Hot Reload and Admin API** — POST reload endpoint, GET list endpoint, optional file watcher | M | Zero-downtime expert updates | `src/admin/router.py`, `tests/admin/test_expert_admin.py` |
| 26.6 | **Context Pack Integration** — Reference supporting files in manifest, inject into expert prompt context | M | Richer expert definitions | `src/experts/manifest.py`, `src/experts/scanner.py`, `src/assembler/assembler.py`, `tests/experts/test_context_integration.py` |

---

## Appendix A: EXPERT.md Format Example

```markdown
---
name: security-reviewer
class: security
capability_tags:
  - auth
  - secrets
  - crypto
  - injection
trust_tier: probation
description: >
  Review code changes for security vulnerabilities including
  authentication, authorization, secret handling, cryptographic
  operations, and injection risks.
constraints:
  - Read-only access to repository
  - Cannot approve or merge changes
  - Must cite OWASP references for findings
tool_policy:
  allowed_suites: [repo_read, analysis]
  denied_suites: [repo_write, publish]
  read_only: true
context_files:
  - owasp-top-10-checklist.md
  - auth-patterns.md
---

You are a security review expert for TheStudio.

Your job is to review code changes for security vulnerabilities.
Focus on: authentication flows, secret handling, cryptographic
operations, input validation, and injection prevention.

For each finding, provide:
- Severity (S0-S3)
- Category (OWASP reference)
- Location (file and line range)
- Remediation recommendation

Be specific. "This looks unsafe" is not a finding. "Line 42 of
auth.py passes user input directly to SQL query without
parameterization (CWE-89, S0)" is a finding.
```

## Appendix B: Manifest-to-ExpertCreate Field Mapping

| EXPERT.md Field | ExpertCreate Field | Notes |
|----------------|--------------------|-------|
| `name` | `name` | Direct mapping |
| `class` | `expert_class` | String parsed to `ExpertClass` enum |
| `capability_tags` | `capability_tags` | Direct mapping |
| `description` | `scope_description` | Direct mapping |
| `trust_tier` | `trust_tier` | String parsed to `TrustTier` enum; default `shadow` |
| `tool_policy` | `tool_policy` | Direct mapping (dict) |
| `constraints` | `definition.scope_boundaries` | Mapped into definition JSON |
| Markdown body | `definition.system_prompt_template` | Stored in definition for Agent Framework consumption |
| `context_files` contents | `definition.context_files` | Dict keyed by filename |

## Appendix C: Version Hash Computation

```python
import hashlib

def compute_version_hash(content: str) -> str:
    """Compute SHA-256 hash of EXPERT.md content for version tracking."""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

---

## Meridian Review Status

### Round 1: CONDITIONAL PASS — 3 gaps fixed

**Date:** 2026-03-13
**Verdict:** CONDITIONAL PASS → all 3 must-fix items resolved in Round 2

| # | Question | R1 Status | R2 Status |
|---|----------|-----------|-----------|
| 1 | Are acceptance criteria testable without ambiguity? | PASS | PASS |
| 2 | Are constraints and non-goals explicit enough to prevent scope creep? | PASS | PASS |
| 3 | Do success metrics have concrete targets? | GAP (version_hash storage undefined, onboarding metric unmeasurable) | Fixed: version_hash stored in definition JSON; onboarding metric is scripted test |
| 4 | Are dependencies and affected systems fully enumerated? | GAP (seed_experts phantom replacement, route conflict, TBD stakeholders) | Fixed: AC8 rewritten, routes use /admin/experts/registry, platform_router.py specified |
| 5 | Is the story map ordered by risk reduction? | PASS | PASS |
| 6 | Can an AI agent implement each story from the description alone? | PASS | PASS |
| 7 | Are there red flags? | 4 flags (route conflict HIGH, phantom replacement MEDIUM, version_hash MEDIUM, TBD stakeholders MEDIUM) | All resolved except stakeholder assignment (non-blocking) |

### Round 2: COMMITTABLE

All Round 1 fixes verified. No red flags remain. Stakeholder assignment is recommended before sprint start but does not block commit.
