# Story 0.3 -- Context Manager: enrich TaskPacket with scope and risk flags

<!-- docsmcp:start:user-story -->

> **As a** TheStudio platform, **I want** to enrich each TaskPacket with scope analysis, risk flags, Service Context Pack stubs, and a Complexity Index v0, **so that** downstream components (Intent Builder, Router in Phase 1) have structured context to make better decisions

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 8 | **Size:** L
**Epic:** 0 — Foundation: Prove the Pipe
**Sprint:** 2 (weeks 4-6)
**Depends on:** Story 0.2 (TaskPacket schema and CRUD)

<!-- docsmcp:end:sizing -->

---

<!-- docsmcp:start:description -->
## Description

The Context Manager sits between Ingress and Intent Builder. It reads the TaskPacket, analyzes the GitHub issue content and repo metadata to determine scope and risk, attaches 0..n Service Context Packs (stubs in Phase 0, real packs in Phase 3), and computes a Complexity Index v0.

**Scope analysis** examines:
- Number of files likely affected (from issue description)
- Whether the issue mentions tests, security, API changes, or breaking changes
- Labels and metadata from GitHub

**Risk flags** are boolean markers:
- `risk_security` — mentions security, auth, credentials, secrets
- `risk_breaking` — mentions breaking change, migration, deprecation
- `risk_cross_team` — mentions other repos, services, or teams
- `risk_data` — mentions database, migration, schema

**Complexity Index v0** is a simple categorical score:
- `low` — single file, no risk flags
- `medium` — multiple files or 1 risk flag
- `high` — many files or 2+ risk flags

After enrichment, the TaskPacket status moves from "received" to "enriched".

<!-- docsmcp:end:description -->

---

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create Context Manager module (`src/context/context_manager.py`)
  - Accept TaskPacket ID, fetch TaskPacket + GitHub issue content
  - Orchestrate scope analysis, risk flagging, and complexity scoring
  - Update TaskPacket with enrichment data and set status to "enriched"
- [ ] Implement scope analyzer (`src/context/scope_analyzer.py`)
  - Parse issue title + body for file references, component mentions
  - Estimate affected file count from keywords and patterns
  - Return structured scope object
- [ ] Implement risk flagger (`src/context/risk_flagger.py`)
  - Keyword-based detection for each risk category
  - Return dict of boolean risk flags
- [ ] Implement Complexity Index v0 (`src/context/complexity.py`)
  - Combine scope breadth + risk flag count into low/medium/high
  - Store on TaskPacket enrichment data
- [ ] Create Service Context Pack stub (`src/context/service_context_pack.py`)
  - Define pack interface (name, version, content dict)
  - Implement one stub pack (or empty list for Phase 0)
  - Attach to TaskPacket enrichment
- [ ] Add enrichment fields to TaskPacket model (`src/models/taskpacket.py`)
  - `scope` (JSON: affected_files_estimate, components)
  - `risk_flags` (JSON: risk_security, risk_breaking, risk_cross_team, risk_data)
  - `complexity_index` (string: low/medium/high)
  - `context_packs` (JSON array of pack references)
- [ ] Add OpenTelemetry span (`src/context/context_manager.py`)
  - Span name: `context.enrich`
  - Attributes: correlation_id, complexity_index, risk_flag_count
- [ ] Write tests (`tests/test_context_manager.py`)
  - Unit tests for scope analyzer, risk flagger, complexity scoring
  - Integration test for full enrichment flow

<!-- docsmcp:end:tasks -->

---

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Context Manager reads a TaskPacket and produces scope, risk flags, complexity index, and context pack list
- [ ] Risk flags are correctly set based on issue content keywords
- [ ] Complexity Index v0 correctly categorizes as low/medium/high based on scope + risk
- [ ] TaskPacket status transitions from "received" to "enriched" after successful enrichment
- [ ] Enrichment data is persisted on the TaskPacket and retrievable
- [ ] Service Context Pack stub is attached (empty list or one stub pack)
- [ ] OpenTelemetry span emitted with complexity_index and risk_flag_count

<!-- docsmcp:end:acceptance-criteria -->

---

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Unit tests for scope analyzer with various issue texts
- [ ] Unit tests for risk flagger (each risk category triggered and not triggered)
- [ ] Unit tests for complexity scoring (low, medium, high scenarios)
- [ ] Integration test: TaskPacket enrichment end-to-end
- [ ] Code passes ruff lint and mypy type check

<!-- docsmcp:end:definition-of-done -->

---

<!-- docsmcp:start:test-cases -->
## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Simple issue, no risks | "Fix typo in README" | low complexity, no risk flags |
| 2 | Multi-file issue | "Refactor auth module across 5 files" | medium complexity, risk_security=true |
| 3 | Breaking change | "Remove deprecated API v1 endpoints" | high complexity, risk_breaking=true |
| 4 | Security issue | "Fix credential leak in config" | high complexity, risk_security+risk_data=true |
| 5 | Cross-team mention | "Update shared API contract with team-payments" | medium+, risk_cross_team=true |
| 6 | Empty issue body | Issue with title only, no body | low complexity, no risk flags |
| 7 | Status transition | TaskPacket status=received | After enrichment: status=enriched |

<!-- docsmcp:end:test-cases -->

---

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Keyword detection** is intentionally simple for Phase 0 — regex/keyword matching, not ML
- **Complexity Index v0** is categorical (low/medium/high). Phase 3 defines a formal rubric with dimensions and formula
- **Service Context Packs** are stubs in Phase 0. The interface is defined now so Phase 3 can plug in real packs without refactoring
- **Architecture references:**
  - Context Manager: `thestudioarc/03-context-manager.md`
  - Service Context Packs: `thestudioarc/09-service-context-packs.md`
  - System runtime flow: `thestudioarc/15-system-runtime-flow.md` (Step 2)

<!-- docsmcp:end:technical-notes -->

---

## Files Affected

| File | Action | Description |
|------|--------|-------------|
| `src/context/__init__.py` | Create | Package init |
| `src/context/context_manager.py` | Create | Orchestration: fetch, analyze, enrich, persist |
| `src/context/scope_analyzer.py` | Create | Scope analysis from issue content |
| `src/context/risk_flagger.py` | Create | Risk flag detection |
| `src/context/complexity.py` | Create | Complexity Index v0 scoring |
| `src/context/service_context_pack.py` | Create | Pack interface and stub |
| `src/models/taskpacket.py` | Modify | Add enrichment fields |
| `tests/test_context_manager.py` | Create | Unit and integration tests |

---

<!-- docsmcp:start:dependencies -->
## Dependencies

- **Story 0.2 (TaskPacket):** Context Manager reads and updates TaskPackets
- **Blocked by:** Must complete before Story 0.4 (Intent Builder) can start

<!-- docsmcp:end:dependencies -->

---

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Depends only on TaskPacket (Story 0.2)
- [x] **N**egotiable -- Keyword lists, complexity thresholds, pack interface are flexible
- [x] **V**aluable -- Provides structured context that improves intent quality and routing (Phase 1)
- [x] **E**stimable -- 8 points, well-scoped analysis + persistence
- [x] **S**mall -- Completable within one sprint
- [x] **T**estable -- 7 test cases with deterministic keyword-based logic

<!-- docsmcp:end:invest -->

---

*Story created by Saga. Part of Epic 0 — Foundation: Prove the Pipe.*
