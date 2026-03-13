# Story 26.2 — Expert Directory Scanner

> **As a** platform developer,
> **I want** a scanner that discovers all expert directories, parses their manifests, and collects supporting files,
> **so that** the system automatically finds all file-based experts without manual registration.

**Purpose:** The scanner is the discovery mechanism that turns a directory tree into a list of typed `ExpertManifest` objects. Without it, the registrar (Story 26.3) has nothing to sync and the migration (Story 26.4) has no way to load experts at startup.

**Intent:** Create `src/experts/scanner.py` with a `scan_expert_directories(base_path)` function that walks all immediate subdirectories of a base path, finds `EXPERT.md` files, parses each into an `ExpertManifest`, collects supporting files, and returns the results. Invalid manifests are skipped with a warning log, not fatal errors.

**Points:** 5 | **Size:** M
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.1-26.4)
**Depends on:** Story 26.1 (Expert Manifest Schema)

---

## Description

The scanner is the bridge between the filesystem and the expert registration system. It performs a shallow scan (one level of subdirectories only — no recursive nesting), validates that each subdirectory contains a parseable `EXPERT.md`, and bundles the manifest with metadata about supporting files found alongside it.

Supporting files are any `.md` files other than `EXPERT.md`, plus `.json` and `.yaml`/`.yml` files. These are collected as `SupportingFile` records (path + content) that Story 26.6 will use for context pack integration.

## Tasks

- [ ] Create `src/experts/scanner.py`
- [ ] Define `SupportingFile` dataclass:
  - `relative_path: str` — path relative to the expert directory
  - `content: str` — file content (read at scan time)
- [ ] Define `ScannedExpert` dataclass:
  - `manifest: ExpertManifest`
  - `directory: Path` — absolute path to the expert directory
  - `supporting_files: list[SupportingFile]`
- [ ] Define `ScanResult` dataclass:
  - `experts: list[ScannedExpert]`
  - `errors: list[ScanError]` — directories that failed to parse
- [ ] Define `ScanError` dataclass:
  - `directory: Path`
  - `error: str`
- [ ] Implement `scan_expert_directories(base_path: Path) -> ScanResult`:
  - Verify `base_path` exists and is a directory; raise `ValueError` if not
  - List all immediate subdirectories of `base_path` (no recursion)
  - For each subdirectory:
    - Check for `EXPERT.md` file; skip with info log if not found
    - Call `parse_expert_manifest()` from Story 26.1
    - On `ManifestParseError`: add to `errors`, log warning, continue
    - Collect supporting files: all `.md` (except `EXPERT.md`), `.json`, `.yaml`, `.yml` files in the directory (non-recursive)
    - Read supporting file contents
    - Create `ScannedExpert` with manifest, directory path, and supporting files
  - Check for duplicate expert names across directories; add to `errors` if found
  - Return `ScanResult` with experts and errors
- [ ] Add structured logging with `correlation_id` where available:
  - INFO: "Scanning expert directories" with `base_path` and count of subdirectories
  - INFO: "Parsed expert manifest" with `name` and `version_hash` per expert
  - WARNING: "Skipping directory — no EXPERT.md" with directory path
  - WARNING: "Skipping directory — invalid manifest" with directory path and error detail
  - WARNING: "Duplicate expert name" with name and both directory paths
- [ ] Create `tests/experts/test_scanner.py`:
  - Test: scan directory with one valid expert
  - Test: scan directory with multiple valid experts
  - Test: scan empty directory (returns empty list, no errors)
  - Test: scan directory where one subdirectory has invalid manifest (valid ones still load)
  - Test: scan directory where subdirectory has no EXPERT.md (skipped silently)
  - Test: supporting files are collected correctly (.md, .json, .yaml, .yml)
  - Test: EXPERT.md is not included in supporting files
  - Test: non-matching files (.py, .txt) are not collected as supporting files
  - Test: duplicate expert names across directories produce errors
  - Test: base_path that does not exist raises ValueError

## Acceptance Criteria

- [ ] Scanner discovers all expert directories with valid `EXPERT.md` files
- [ ] Invalid manifests are skipped with warnings, not fatal errors
- [ ] Supporting files (`.md`, `.json`, `.yaml`, `.yml`) are collected with contents
- [ ] `EXPERT.md` is excluded from supporting files
- [ ] Duplicate expert names across directories are detected and reported
- [ ] Non-existent base path raises a clear error
- [ ] All unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Single valid expert | `experts/sec/EXPERT.md` (valid) | `ScanResult` with 1 expert, 0 errors |
| 2 | Multiple valid | `experts/sec/EXPERT.md`, `experts/qa/EXPERT.md` | `ScanResult` with 2 experts, 0 errors |
| 3 | Empty base | `experts/` (no subdirs) | `ScanResult` with 0 experts, 0 errors |
| 4 | Mixed valid/invalid | `experts/sec/EXPERT.md` (valid), `experts/bad/EXPERT.md` (invalid YAML) | `ScanResult` with 1 expert, 1 error |
| 5 | No EXPERT.md | `experts/empty/` (no EXPERT.md) | `ScanResult` with 0 experts, 0 errors (skipped) |
| 6 | Supporting files | `experts/sec/EXPERT.md`, `experts/sec/checklist.md`, `experts/sec/rules.yaml` | `ScannedExpert` with 2 supporting files |
| 7 | Exclude EXPERT.md | `experts/sec/EXPERT.md`, `experts/sec/other.md` | Supporting files contains only `other.md` |
| 8 | Exclude non-matching | `experts/sec/EXPERT.md`, `experts/sec/helper.py` | Supporting files is empty |
| 9 | Duplicate names | Two directories with `name: security-reviewer` | `ScanResult` with 0 experts, 1 error (or 2 errors) |
| 10 | Missing base path | `/nonexistent/path` | `ValueError` raised |

## Files Affected

| File | Action |
|------|--------|
| `src/experts/scanner.py` | Create |
| `tests/experts/test_scanner.py` | Create |

## Technical Notes

- Use `pathlib.Path` for all file system operations. Avoid `os.path` and `os.listdir`.
- The scan is shallow: only immediate subdirectories of `base_path`. No recursion into nested directories. This prevents accidental discovery of unrelated markdown files.
- Supporting file contents are read eagerly at scan time. This is acceptable because expert directories are small (typically 2-5 files, < 100KB total). If this becomes a concern, switch to lazy loading.
- Use `tmp_path` pytest fixture for all tests that create temporary directory structures.
- Log at module level using `structlog` or the project's logging pattern with `correlation_id`.
