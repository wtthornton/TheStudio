# Story 26.1 — Expert Manifest Schema

> **As a** platform developer,
> **I want** a Pydantic model that parses YAML frontmatter from `EXPERT.md` files into a validated `ExpertManifest`,
> **so that** expert definitions have a clear, enforced schema and invalid manifests are caught at parse time.

**Purpose:** The manifest schema is the foundation for all file-based expert packaging. Without it, the scanner, registrar, and migration stories have nothing to parse into. This story defines the contract between the `EXPERT.md` file format and the rest of the system.

**Intent:** Create `src/experts/manifest.py` with a Pydantic model `ExpertManifest` that parses YAML frontmatter from markdown files. The model validates all required fields, computes a content hash for versioning, and captures the markdown body as a system prompt template. Validation rejects manifests with missing required fields, invalid enum values, or empty capability tags.

**Points:** 3 | **Size:** S
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.1-26.4)
**Depends on:** None

---

## Description

The `ExpertManifest` Pydantic model is the typed representation of an `EXPERT.md` file. It parses YAML frontmatter (the `---` delimited block at the top of the file) and captures the remaining markdown body as the system prompt template. A SHA-256 hash of the full file content (frontmatter + body, with normalized line endings) serves as the version identifier.

## Tasks

- [ ] Create `src/experts/manifest.py`
- [ ] Define `ExpertManifest` Pydantic model with fields:
  - `name: str` (required) — unique expert identifier
  - `expert_class: ExpertClass` (required) — maps from `class` field in YAML to `ExpertClass` enum
  - `capability_tags: list[str]` (required, min length 1) — non-empty list of capability tags
  - `trust_tier: TrustTier` (optional, default `TrustTier.SHADOW`) — maps from `trust_tier` field in YAML
  - `description: str` (required) — human-readable scope description
  - `constraints: list[str]` (optional, default empty) — scope constraints
  - `tool_policy: dict[str, Any]` (optional, default empty dict) — tool access policy
  - `context_files: list[str]` (optional, default empty) — relative paths to supporting files
  - `system_prompt_template: str` (computed) — the markdown body after frontmatter
  - `version_hash: str` (computed) — SHA-256 of full file content with normalized line endings
  - `source_path: Path` (computed) — absolute path to the EXPERT.md file
- [ ] Implement `parse_expert_manifest(file_path: Path) -> ExpertManifest` function:
  - Read the file content
  - Split on `---` delimiters to extract YAML frontmatter and markdown body
  - Parse YAML frontmatter with `yaml.safe_load()`
  - Construct `ExpertManifest` with parsed fields + computed fields
  - Raise `ManifestParseError` (custom exception) on any failure with file path in message
- [ ] Implement `compute_version_hash(content: str) -> str` function:
  - Normalize line endings (`\r\n` and `\r` to `\n`)
  - Return SHA-256 hex digest
- [ ] Define `ManifestParseError(Exception)` with `file_path` and `detail` attributes
- [ ] Implement `manifest_to_expert_create(manifest: ExpertManifest) -> ExpertCreate` function:
  - Map manifest fields to `ExpertCreate` fields per Appendix B of the epic
  - Pack `constraints`, `system_prompt_template`, and `context_files` data into the `definition` dict
- [ ] Create `tests/experts/test_manifest.py`:
  - Test: parse valid manifest with all fields
  - Test: parse manifest with only required fields (optional fields default correctly)
  - Test: reject manifest with missing `name`
  - Test: reject manifest with missing `class`
  - Test: reject manifest with empty `capability_tags`
  - Test: reject manifest with invalid `class` value
  - Test: reject manifest with invalid `trust_tier` value
  - Test: `version_hash` changes when content changes
  - Test: `version_hash` is stable for identical content
  - Test: `version_hash` is consistent across `\n` and `\r\n` line endings
  - Test: `manifest_to_expert_create` maps all fields correctly
  - Test: `ManifestParseError` includes file path

## Acceptance Criteria

- [ ] `ExpertManifest` parses valid `EXPERT.md` files with YAML frontmatter
- [ ] Required field validation rejects incomplete manifests with clear errors
- [ ] Enum validation rejects invalid `class` and `trust_tier` values
- [ ] `version_hash` is deterministic and changes only when content changes
- [ ] `manifest_to_expert_create` produces a valid `ExpertCreate` object
- [ ] All unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Valid full manifest | EXPERT.md with all fields | `ExpertManifest` with all fields populated |
| 2 | Minimal manifest | EXPERT.md with only required fields | `ExpertManifest` with defaults for optional fields |
| 3 | Missing name | EXPERT.md without `name` | `ManifestParseError` |
| 4 | Missing class | EXPERT.md without `class` | `ManifestParseError` |
| 5 | Empty capability_tags | EXPERT.md with `capability_tags: []` | Pydantic `ValidationError` |
| 6 | Invalid class | EXPERT.md with `class: nonexistent` | Pydantic `ValidationError` |
| 7 | Invalid trust_tier | EXPERT.md with `trust_tier: ultimate` | Pydantic `ValidationError` |
| 8 | Hash stability | Same content read twice | Same `version_hash` |
| 9 | Hash sensitivity | Content with one character changed | Different `version_hash` |
| 10 | Cross-platform hash | Same content with `\n` vs `\r\n` | Same `version_hash` |
| 11 | ExpertCreate mapping | Valid `ExpertManifest` | `ExpertCreate` with correct field mapping |

## Files Affected

| File | Action |
|------|--------|
| `src/experts/manifest.py` | Create |
| `tests/experts/__init__.py` | Create (empty) |
| `tests/experts/test_manifest.py` | Create |

## Technical Notes

- YAML frontmatter parsing: split file content on `---` (first occurrence starts frontmatter, second ends it). Content before the first `---` is ignored. Content after the second `---` is the markdown body.
- Use `yaml.safe_load()` — never `yaml.load()` — to prevent code execution from YAML.
- The `class` field in YAML maps to `expert_class` in the Pydantic model. Use a field alias: `Field(alias="class")`.
- Import `ExpertClass` and `TrustTier` from `src.experts.expert` — do not redefine enums.
- The `definition` dict structure in `ExpertCreate` should mirror the structure used in `seed.py` for backward compatibility with the Router and Assembler.
