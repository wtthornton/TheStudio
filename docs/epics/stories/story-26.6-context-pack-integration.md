# Story 26.6 — Context Pack Integration

> **As a** platform developer,
> **I want** expert manifests to reference supporting context files that are automatically included in the expert's prompt context,
> **so that** experts carry their own domain knowledge without relying on separately registered context packs.

**Purpose:** Experts need domain context — API checklists, coding patterns, compliance rules — to produce quality outputs. Currently, context packs are registered separately in `src/context/packs.py`. File-based experts should carry their own context files alongside the manifest, making the expert directory self-contained.

**Intent:** Allow `EXPERT.md` to declare `context_files` in the YAML frontmatter (a list of relative paths to supporting documents). The scanner validates these paths exist and reads their contents. When the pipeline invokes an expert, the Assembler includes the context file contents in the expert's prompt context, keyed by filename.

**Points:** 5 | **Size:** M
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.5-26.6)
**Depends on:** Story 26.1 (Manifest Schema), Story 26.2 (Scanner), Story 26.3 (Registrar)

---

## Description

This story connects three pieces:

1. **Manifest declaration:** The `context_files` field in `ExpertManifest` (already defined in Story 26.1) lists relative paths to supporting files. Example: `context_files: ["owasp-checklist.md", "auth-patterns.md"]`.

2. **Scanner validation:** The scanner (Story 26.2) already collects supporting files. This story adds validation that files listed in `context_files` actually exist in the expert directory. Missing referenced files produce a `ManifestParseError`.

3. **Assembler injection:** When the Assembler prepares the prompt context for an expert invocation, it looks up the expert's `definition.context_files` dict and appends the content to the expert's context. This replaces the current pattern where context packs are registered in `src/context/packs.py` for domain-specific knowledge.

The key distinction: `context_files` are expert-specific context (shipped with the expert). Service Context Packs in `src/context/packs.py` are repo-specific context (shipped with the repo profile). Both can coexist.

## Tasks

- [ ] Update `src/experts/manifest.py`:
  - Ensure `context_files: list[str]` field is defined (should already exist from Story 26.1)
  - Add validation: if `context_files` is non-empty, paths must be relative (no absolute paths, no `..` path traversal)
- [ ] Update `src/experts/scanner.py`:
  - After parsing manifest, validate that each path in `context_files` resolves to a file in the expert directory
  - If a referenced file does not exist: add to `ScanResult.errors` with detail "Referenced context file not found: {path}"
  - If a referenced file exists: read its content and store in `ScannedExpert.supporting_files` (may already be collected)
- [ ] Update `src/experts/registrar.py` (or `manifest_to_expert_create`):
  - When building the `definition` dict, include a `context_files` key:
    ```python
    "context_files": {
        "owasp-checklist.md": "... file content ...",
        "auth-patterns.md": "... file content ...",
    }
    ```
  - Content is stored in the expert version's `definition` JSON field in the database
- [ ] Update `src/assembler/assembler.py`:
  - When preparing expert prompt context, check `expert.definition.get("context_files", {})`
  - If non-empty, append each file's content to the expert context under a clear delimiter:
    ```
    --- Expert Context: owasp-checklist.md ---
    {content}
    --- End Expert Context ---
    ```
  - This content is included in the prompt sent to the expert agent
- [ ] Create example context files for the security-reviewer expert:
  - `experts/security-reviewer/owasp-top-10-checklist.md` — a concise OWASP Top 10 reference
  - Update `experts/security-reviewer/EXPERT.md` to reference it in `context_files`
- [ ] Create `tests/experts/test_context_integration.py`:
  - Test: manifest with `context_files` listing existing files parses successfully
  - Test: manifest with `context_files` listing non-existent file produces scan error
  - Test: manifest with absolute path in `context_files` fails validation
  - Test: manifest with `..` path traversal in `context_files` fails validation
  - Test: context file contents are stored in `definition.context_files` after sync
  - Test: Assembler includes context file contents in expert prompt context
  - Test: Assembler handles expert without context_files gracefully (no error)
  - Test: context file contents survive round-trip (scan -> sync -> read from DB -> inject in prompt)

## Acceptance Criteria

- [ ] `context_files` in manifest references supporting files by relative path
- [ ] Scanner validates that referenced files exist; missing files produce errors
- [ ] Path traversal (`..`) and absolute paths are rejected
- [ ] Context file contents are stored in the expert's `definition` in the database
- [ ] Assembler injects context file contents into expert prompt context
- [ ] Experts without `context_files` work unchanged (no regression)
- [ ] All unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Valid context files | `context_files: ["checklist.md"]`, file exists | Manifest parses, content included |
| 2 | Missing context file | `context_files: ["missing.md"]`, file does not exist | Scan error with detail |
| 3 | Absolute path | `context_files: ["/etc/passwd"]` | Validation error |
| 4 | Path traversal | `context_files: ["../../secrets.md"]` | Validation error |
| 5 | DB round-trip | Scan -> sync -> read expert from DB | `definition.context_files` has file content |
| 6 | Assembler injection | Expert with context files invoked | Prompt includes context file content with delimiters |
| 7 | No context files | Expert without `context_files` field | Assembler works normally, no error |
| 8 | Multiple context files | `context_files: ["a.md", "b.yaml"]` | Both contents included in prompt |

## Files Affected

| File | Action |
|------|--------|
| `src/experts/manifest.py` | Modify (add path validation for context_files) |
| `src/experts/scanner.py` | Modify (validate context_files exist, read contents) |
| `src/experts/registrar.py` | Modify (include context_files contents in definition) |
| `src/assembler/assembler.py` | Modify (inject context file contents into expert prompt) |
| `experts/security-reviewer/owasp-top-10-checklist.md` | Create (example context file) |
| `experts/security-reviewer/EXPERT.md` | Modify (add context_files reference) |
| `tests/experts/test_context_integration.py` | Create |

## Technical Notes

- Context file contents are stored as strings in the `definition` JSON field. For large files, this could bloat the database. Set a reasonable limit: reject context files larger than 50KB each, total context files per expert limited to 200KB.
- The Assembler's context injection point depends on Epic 23's Agent Framework. If the Agent Framework is not yet implemented, inject into the `definition` dict that the existing assembler reads. If the Agent Framework is in place, inject into the `AgentContext.extra` dict.
- Path validation must use `pathlib.PurePosixPath` (not platform-specific) to ensure consistent behavior across Windows and Unix. Resolve relative paths against the expert directory, then verify the resolved path starts with the expert directory (prevents traversal).
- Service Context Packs (`src/context/packs.py`) are orthogonal to expert context files. Service packs describe repo conventions; expert context files describe domain knowledge. Both can be active simultaneously.
- The delimiter format (`--- Expert Context: filename ---`) should be consistent so that agents can identify context boundaries. Consider making this a constant in `src/experts/manifest.py`.
