# Story 0.2 -- TaskPacket: minimal schema and persistence

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** a durable TaskPacket record with a minimal schema (repo, issue_id, correlation_id, status, timestamps), **so that** every work item has a single source of truth that all downstream components can read and update

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** M
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 1 (weeks 1-3)
**Depends on:** None (first story in dependency chain)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The TaskPacket is the durable work record for a single GitHub work item. It is created by Ingress (Story 0.1) and enriched by Context Manager (Story 0.3). Every downstream component — Intent Builder, Primary Agent, Verification Gate, Publisher — reads from and/or updates the TaskPacket.

Phase 0 requires a minimal schema:
- `id` (UUID, primary key)
- `repo` (string, e.g. "owner/repo")
- `issue_id` (integer, GitHub issue number)
- `delivery_id` (string, GitHub delivery GUID — for dedupe)
- `correlation_id` (UUID, for tracing)
- `status` (enum: received, enriched, intent_built, in_progress, verification_passed, verification_failed, published, failed)
- `created_at` (timestamp)
- `updated_at` (timestamp)

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Define TaskPacket model with all Phase 0 fields (`src/models/taskpacket.py`)
  - Pydantic model for validation
  - SQLAlchemy or equivalent ORM model for persistence
  - Status enum with all Phase 0 states
- [ ] Create database migration (`src/db/migrations/001_taskpacket.py`)
  - Table creation with indexes on (delivery_id, repo) for dedupe
  - Index on correlation_id for tracing queries
  - Index on status for queue queries
- [ ] Implement CRUD operations (`src/models/taskpacket_crud.py`)
  - `create(repo, issue_id, delivery_id, correlation_id) -> TaskPacket`
  - `get_by_id(id) -> TaskPacket | None`
  - `get_by_delivery(delivery_id, repo) -> TaskPacket | None` (for dedupe)
  - `update_status(id, new_status) -> TaskPacket`
  - `get_by_correlation_id(correlation_id) -> TaskPacket | None`
- [ ] Add database connection setup (`src/db/connection.py`)
  - Connection pooling
  - Configuration from environment variables
- [ ] Write tests (`tests/test_taskpacket.py`)
  - Unit tests for model validation
  - Integration tests for CRUD operations
  - Test unique constraint on (delivery_id, repo)

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] TaskPacket can be created with all required fields and returns a valid UUID id
- [ ] TaskPacket can be retrieved by id, by delivery_id + repo, and by correlation_id
- [ ] Status updates are persisted and updated_at timestamp changes
- [ ] Duplicate (delivery_id, repo) insert raises a constraint violation or returns existing record
- [ ] All status enum values are valid and enforced at the model level
- [ ] Database migration runs cleanly on a fresh database
- [ ] created_at is set automatically on insert; updated_at on every update

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for model validation (valid fields, invalid fields, missing required)
- [ ] Integration tests for all CRUD operations
- [ ] Integration test for unique constraint violation
- [ ] Migration tested on fresh database
- [ ] Code passes ruff lint and mypy type check
- [ ] No hardcoded database credentials

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Create valid TaskPacket | All required fields | TaskPacket with UUID id, status=received, timestamps set |
| 2 | Create duplicate | Same delivery_id + repo | Constraint violation or existing record returned |
| 3 | Get by id | Valid UUID | Matching TaskPacket |
| 4 | Get by id (not found) | Random UUID | None |
| 5 | Get by delivery | delivery_id + repo | Matching TaskPacket |
| 6 | Update status | id + new status | Status changed, updated_at advanced |
| 7 | Invalid status | id + "invalid_status" | Validation error |
| 8 | Get by correlation_id | Valid correlation_id | Matching TaskPacket |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Database:** PostgreSQL recommended (supports UUID natively, strong constraint enforcement)
- **ORM:** SQLAlchemy 2.0+ with async support, or raw asyncpg if minimal overhead preferred
- **Pydantic:** Use Pydantic v2 for model validation (aligns with FastAPI)
- **Status machine:** Status transitions should be validated (e.g., can't go from "published" back to "received") — implement as a simple allowed-transitions dict
- **Architecture references:**
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (TaskPacket is the durable work record)
  - Overview: `thestudioarc/00-overview.md` (Core System Artifacts)

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/models/__init__.py` | Create | Package init |
| `src/models/taskpacket.py` | Create | TaskPacket model (Pydantic + ORM) |
| `src/models/taskpacket_crud.py` | Create | CRUD operations |
| `src/db/__init__.py` | Create | Package init |
| `src/db/connection.py` | Create | Database connection and pooling |
| `src/db/migrations/001_taskpacket.py` | Create | Initial migration |
| `tests/test_taskpacket.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **None** — TaskPacket is the foundational data model. Stories 0.1, 0.3, 0.4, 0.5, 0.6, 0.7 all depend on this.

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- No upstream dependencies; can start immediately
- [x] **N**egotiable -- ORM choice, migration tool, exact field types are flexible
- [x] **V**aluable -- Every component in the system depends on TaskPacket
- [x] **E**stimable -- 5 points, standard CRUD + schema pattern
- [x] **S**mall -- Completable in 2-3 days
- [x] **T**estable -- 8 test cases with clear pass/fail

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
