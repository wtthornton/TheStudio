# Story 26.3 — Expert Registration and Versioning

> **As a** platform developer,
> **I want** a registrar that syncs scanned expert manifests to the database with hash-based change detection,
> **so that** file changes to EXPERT.md automatically update the Expert Library without duplicate entries or unnecessary writes.

**Purpose:** The registrar connects the filesystem (scanner output) to the database (Expert Library). Without it, scanned manifests are parsed but never persisted, and the Router cannot discover file-based experts. Hash-based versioning ensures that only actual content changes trigger database writes.

**Intent:** Create `src/experts/registrar.py` with a `sync_experts()` function that compares manifest version hashes against stored records, creates new experts, updates changed ones with incremented versions, and optionally deactivates removed experts. Uses existing `expert_crud.py` functions for all database operations.

**Points:** 5 | **Size:** M
**Epic:** 26 — File-Based Expert Packaging
**Sprint:** 1 (Stories 26.1-26.4)
**Depends on:** Story 26.1 (Expert Manifest Schema), Story 26.2 (Expert Directory Scanner)

---

## Description

The registrar is the synchronization layer between the filesystem and the database. It takes a list of `ScannedExpert` objects from the scanner and ensures the Expert Library (PostgreSQL) reflects the current state of the `experts/` directory.

The sync algorithm:
1. Fetch all existing experts from the database.
2. For each scanned manifest:
   a. If no expert with that name exists: create it via `create_expert()`.
   b. If an expert with that name exists and the `version_hash` differs: update via `update_expert_version()` with the new definition.
   c. If an expert with that name exists and the `version_hash` matches: skip (no-op).
3. For each database expert not found in the scanned manifests:
   a. If `deactivate_removed=True`: deprecate via `deprecate_expert()`.
   b. If `deactivate_removed=False` (default): ignore.

The version hash is stored in the expert's `definition` JSON field under a `_version_hash` key. This avoids schema changes to the `ExpertRow` model.

## Tasks

- [ ] Create `src/experts/registrar.py`
- [ ] Define `SyncResult` dataclass:
  - `created: list[str]` — names of newly created experts
  - `updated: list[str]` — names of experts with version bumps
  - `unchanged: list[str]` — names of experts with matching hashes
  - `deactivated: list[str]` — names of experts deprecated (if `deactivate_removed=True`)
  - `errors: list[str]` — names of experts that failed to sync with error detail
- [ ] Implement `async sync_experts(session: AsyncSession, scanned: list[ScannedExpert], deactivate_removed: bool = False) -> SyncResult`:
  - Fetch all active experts from DB using `search_experts(session)` (no filters, all classes)
  - Build a dict of `{name: ExpertRead}` for existing experts
  - Build a dict of `{name: ScannedExpert}` for scanned experts
  - For each scanned expert:
    - Call `manifest_to_expert_create()` from Story 26.1 to get `ExpertCreate`
    - Include `_version_hash` in the `definition` dict
    - Include `_source_path` (str of absolute path) in the `definition` dict
    - If name not in existing: call `create_expert(session, expert_create)` → add to `created`
    - If name in existing and hash differs: call `update_expert_version(session, expert_id, new_definition)` → add to `updated`
    - Also update `capability_tags`, `scope_description`, `trust_tier`, `tool_policy` on the `ExpertRow` if they changed (fetch row, update fields, flush)
    - If name in existing and hash matches: add to `unchanged`
  - If `deactivate_removed=True`:
    - For each existing expert whose name is not in scanned: call `deprecate_expert(session, expert_id)` → add to `deactivated`
  - Return `SyncResult`
- [ ] Implement `_get_stored_hash(expert: ExpertRead) -> str | None`:
  - Extract `_version_hash` from the expert's latest version definition
  - Return None if not found (legacy expert without hash)
- [ ] Add structured logging:
  - INFO: "Syncing N expert manifests against M existing experts"
  - INFO: "Created expert" / "Updated expert" / "Expert unchanged" per expert
  - WARNING: "Deactivating removed expert" when `deactivate_removed=True`
  - ERROR: "Failed to sync expert" with name and error detail
- [ ] Create `tests/experts/test_registrar.py`:
  - Test: new expert is created (name not in DB)
  - Test: changed expert triggers version bump (hash differs)
  - Test: unchanged expert is skipped (hash matches, no DB write)
  - Test: deactivate_removed=True deprecates missing experts
  - Test: deactivate_removed=False (default) ignores missing experts
  - Test: multiple experts sync correctly in one call (mix of create, update, unchanged)
  - Test: legacy expert without `_version_hash` is treated as changed (triggers update)
  - Test: `_source_path` is stored in definition
  - Test: SyncResult counts are correct

## Acceptance Criteria

- [ ] New manifests create new experts in the database
- [ ] Changed manifests (different hash) trigger version increments
- [ ] Unchanged manifests produce no database writes
- [ ] `deactivate_removed=True` deprecates experts not found in scanned manifests
- [ ] `deactivate_removed=False` (default) ignores missing experts
- [ ] Version hash is stored in the `definition` JSON field
- [ ] Source path is stored in the `definition` JSON field
- [ ] All unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | New expert | Manifest for "new-expert", no DB record | `SyncResult(created=["new-expert"])` |
| 2 | Changed expert | Manifest with different hash than DB | `SyncResult(updated=["changed-expert"])`, version incremented |
| 3 | Unchanged expert | Manifest with same hash as DB | `SyncResult(unchanged=["same-expert"])`, no DB write |
| 4 | Deactivate removed | DB has "old-expert", not in scanned, `deactivate_removed=True` | `SyncResult(deactivated=["old-expert"])` |
| 5 | Ignore removed | DB has "old-expert", not in scanned, `deactivate_removed=False` | `SyncResult(deactivated=[])` |
| 6 | Mixed sync | 1 new, 1 changed, 1 unchanged | Correct counts in each SyncResult list |
| 7 | Legacy expert | DB expert with no `_version_hash` in definition | Treated as changed, updated |
| 8 | Source path stored | Any scanned expert | `definition["_source_path"]` is set to absolute path string |

## Files Affected

| File | Action |
|------|--------|
| `src/experts/registrar.py` | Create |
| `tests/experts/test_registrar.py` | Create |

## Technical Notes

- The `_version_hash` and `_source_path` keys are prefixed with underscore to indicate they are metadata, not expert content. The Assembler and Router should ignore keys starting with `_` in the definition dict.
- The registrar uses existing `expert_crud` functions for all DB operations. It does not construct SQL or touch `ExpertRow` directly except for field updates on existing rows (capability_tags, scope_description, trust_tier, tool_policy).
- For field updates on existing rows, the registrar fetches the `ExpertRow` via `session.get()`, updates the fields, and flushes. This is necessary because `update_expert_version()` only creates a new version row — it does not update the expert's top-level fields.
- Tests should use an in-memory or mocked database session. The `expert_crud` functions accept `AsyncSession`, so tests can mock the session or use a test database fixture.
- The `search_experts()` function returns only active experts by default. Legacy seed experts that were never given a `_version_hash` will be treated as changed on the first sync, which is correct — they get a version bump and a hash.
