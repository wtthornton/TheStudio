# Story 0.8 -- Repo Profile: register one repo at Observe tier

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform operator, **I want** to register a repo with tier=Observe, defining its required checks and tool allowlist, **so that** the system knows which repos it manages, what checks to run, and what tools agents can use

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 1 (weeks 1-3)
**Depends on:** None

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Repo Profile is the configuration record for a registered repository. It defines:

- **Repo identity:** owner/repo, GitHub App installation ID
- **Tier:** Observe (Phase 0), Suggest (Phase 1), Execute (Phase 2)
- **Required checks:** Which verification checks must pass (e.g., ruff, pytest)
- **Tool allowlist:** Which tools the Primary Agent is allowed to use
- **Webhook secret:** For signature validation in Ingress
- **Status:** active, paused, disabled

In Phase 0, we register exactly one repo at Observe tier. Observe means:
- Draft PRs only (no auto-merge)
- No tier promotion yet (Phase 2 adds compliance checker for promotion)

The Repo Profile is read by:
- Ingress (webhook secret for signature validation)
- Verification Gate (required checks list)
- Primary Agent (tool allowlist)
- Publisher (tier determines PR mode: draft vs ready-for-review)

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define Repo Profile model (`src/repo/repo_profile.py`)
  - Fields: id, owner, repo_name, installation_id, tier (enum), required_checks (JSON list), tool_allowlist (JSON list), webhook_secret (encrypted), status (enum), created_at, updated_at
  - Pydantic model for validation
  - Persistence (same DB as TaskPacket)
- [ ] Create database migration (`src/db/migrations/002_repo_profile.py`)
  - Table creation with unique constraint on (owner, repo_name)
  - Index on status for active repo queries
- [ ] Implement CRUD operations (`src/repo/repo_profile_crud.py`)
  - `register(owner, repo_name, installation_id, webhook_secret, ...) -> RepoProfile`
  - `get_by_repo(owner, repo_name) -> RepoProfile | None`
  - `get_active_repos() -> list[RepoProfile]`
  - `update_tier(id, new_tier) -> RepoProfile`
  - `update_status(id, new_status) -> RepoProfile`
- [ ] Define default check and tool configurations (`src/repo/defaults.py`)
  - Default required_checks for Observe tier: ["ruff", "pytest"]
  - Default tool_allowlist for Developer role: ["read_file", "write_file", "list_directory", "run_command_lint", "run_command_test"]
  - Configurable per repo but with sane defaults
- [ ] Implement webhook secret encryption (`src/repo/secrets.py`)
  - Encrypt at rest using Fernet or similar
  - Decrypt only when needed for signature validation
  - Key from environment variable
- [ ] Write tests (`tests/test_repo_profile.py`)
  - Unit tests for model validation
  - Integration tests for CRUD
  - Test unique constraint enforcement
  - Test secret encryption/decryption roundtrip

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Repo can be registered with all required fields and defaults applied
- [ ] Repo can be retrieved by owner/repo_name
- [ ] Duplicate (owner, repo_name) registration raises constraint violation
- [ ] Tier defaults to Observe for Phase 0
- [ ] Required checks and tool allowlist have sensible defaults
- [ ] Webhook secret is encrypted at rest and decryptable for validation
- [ ] Repo status can be updated (active, paused, disabled)

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for model validation (valid, invalid, missing required)
- [ ] Integration tests for CRUD (register, get, update tier, update status)
- [ ] Test for unique constraint on (owner, repo_name)
- [ ] Test for secret encryption/decryption roundtrip
- [ ] Migration tested on fresh database
- [ ] Code passes ruff lint and mypy type check
- [ ] No plaintext secrets in database or logs

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Register repo | All required fields | RepoProfile with id, tier=Observe, defaults applied |
| 2 | Duplicate register | Same owner/repo_name | Constraint violation |
| 3 | Get by repo | owner + repo_name | Matching RepoProfile |
| 4 | Get by repo (not found) | Unknown repo | None |
| 5 | Update tier | id + Suggest | Tier updated, updated_at advanced |
| 6 | Secret roundtrip | Store encrypted, retrieve decrypted | Original secret matches |
| 7 | Default checks | Register without specifying checks | ["ruff", "pytest"] applied |
| 8 | Pause repo | Update status to paused | Status = paused, no webhook processing |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Tier system:** Observe (draft PR only) -> Suggest (ready-for-review after V+QA) -> Execute (auto-merge with compliance). Phase 0 only uses Observe.
- **Webhook secret** must never appear in logs, error messages, or API responses.
- **Tool allowlist** is consumed by Primary Agent (Story 0.5) at runtime. Adding/removing tools requires a repo profile update.
- **Architecture references:**
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Repo Profile, tier system)
  - Overview: `thestudioarc/00-overview.md` (Repo Registration)

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/repo/__init__.py` | Create | Package init |
| `src/repo/repo_profile.py` | Create | RepoProfile model |
| `src/repo/repo_profile_crud.py` | Create | CRUD operations |
| `src/repo/defaults.py` | Create | Default configurations |
| `src/repo/secrets.py` | Create | Webhook secret encryption |
| `src/db/migrations/002_repo_profile.py` | Create | Database migration |
| `tests/test_repo_profile.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **None** — Repo Profile is foundational configuration. Stories 0.1, 0.5, 0.6, 0.7 read from it.

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No upstream dependencies; can start immediately
- [x] **N**egotiable -- Default checks, tool list, encryption method are flexible
- [x] **V**aluable -- Every runtime component needs repo configuration
- [x] **E**stimable -- 5 points, standard CRUD + config pattern
- [x] **S**mall -- Completable in 2-3 days
- [x] **T**estable -- 8 test cases with deterministic CRUD logic

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
