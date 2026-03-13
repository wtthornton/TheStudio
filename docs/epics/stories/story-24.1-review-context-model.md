# Story 24.1 — Approval Review Context Model

> **As a** human reviewer,
> **I want** a single structured view of intent, QA results, verification results, evidence, and diff summary,
> **so that** I can make an informed approval decision without cross-referencing multiple sources.

**Purpose:** The review context is the foundation for everything else in this epic. Without it, the chat API has no context to give the LLM, the notification channels have no summary to include, and the reviewer has no structured data to inspect. This story delivers the data model and assembly function that all downstream stories depend on.

**Intent:** Create a `ReviewContext` Pydantic model that aggregates everything a reviewer needs for an approval decision, plus an async `build_review_context()` function that assembles it from existing database records.

**Points:** 5 | **Size:** M
**Epic:** 24 — Chat Interface for Approval Workflows
**Sprint:** 1 (Stories 24.1-24.3)
**Depends on:** None

---

## Description

The `ReviewContext` is a read-only aggregation of existing data. It does not create new data or modify existing records. It queries the TaskPacket, its associated intent specification, QA results, verification results, and evidence bundle, then assembles them into a single Pydantic model optimized for human review and LLM context injection.

The model must be serializable to JSON (for API responses) and renderable as a text block (for LLM system prompts). Include a `to_prompt_context() -> str` method that formats the context as a structured text block suitable for inclusion in an LLM system prompt.

## Tasks

- [ ] Create `src/approval/__init__.py`
- [ ] Create `src/approval/review_context.py`:
  - `DiffSummary` Pydantic model: `files_added: list[str]`, `files_modified: list[str]`, `files_removed: list[str]`, `total_lines_added: int`, `total_lines_removed: int`
  - `VerificationSummary` Pydantic model: `passed: bool`, `checks: list[dict]` (each with `name`, `passed`, `details`)
  - `QASummary` Pydantic model: `passed: bool`, `defect_count: int`, `defect_categories: list[str]`, `has_intent_gap: bool`
  - `IntentSummary` Pydantic model: `goal: str`, `constraints: list[str]`, `acceptance_criteria: list[str]`, `non_goals: list[str]`
  - `ReviewContext` Pydantic model:
    - `taskpacket_id: str`
    - `repo: str`
    - `status: str`
    - `repo_tier: str`
    - `intent: IntentSummary`
    - `qa: QASummary`
    - `verification: VerificationSummary`
    - `diff: DiffSummary`
    - `evidence_highlights: dict` (agent_summary, files_changed, loopback_count)
    - `created_at: datetime`
  - `to_prompt_context(self) -> str` method on `ReviewContext` — formats as structured text for LLM
  - `async build_review_context(session: AsyncSession, taskpacket_id: str) -> ReviewContext | None`
    - Query TaskPacket by ID
    - Return `None` if not found or not in `AWAITING_APPROVAL` status
    - Query related intent spec (latest version for this taskpacket)
    - Query QA result (latest for this taskpacket)
    - Query verification result (latest for this taskpacket)
    - Query evidence bundle (latest for this taskpacket)
    - Assemble into `ReviewContext`
    - If sub-queries return None (e.g., no QA result), populate with sensible defaults (e.g., `QASummary(passed=False, defect_count=0, ...)`)
- [ ] Write tests in `tests/approval/test_review_context.py`:
  - Test `ReviewContext` model creation with valid data
  - Test `to_prompt_context()` produces structured text
  - Test `build_review_context()` with mock session and complete data
  - Test `build_review_context()` returns None for missing TaskPacket
  - Test `build_review_context()` returns None for non-AWAITING_APPROVAL status
  - Test `build_review_context()` handles missing sub-records gracefully

## Acceptance Criteria

- [ ] `ReviewContext` model validates with all required fields
- [ ] `to_prompt_context()` produces human-readable, LLM-parseable text
- [ ] `build_review_context()` returns populated context for valid AWAITING_APPROVAL task
- [ ] `build_review_context()` returns None for invalid/wrong-status tasks
- [ ] Missing sub-records (no QA result, no verification) produce defaults, not errors
- [ ] Unit tests pass

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Complete data | TaskPacket in AWAITING_APPROVAL with intent, QA, verification, evidence | Fully populated ReviewContext |
| 2 | Missing TaskPacket | Non-existent taskpacket_id | None |
| 3 | Wrong status | TaskPacket in PUBLISHED status | None |
| 4 | Missing QA result | TaskPacket exists but no QA record | ReviewContext with default QASummary |
| 5 | Prompt context | Valid ReviewContext | Structured text with all sections |

## Files Affected

| File | Action |
|------|--------|
| `src/approval/__init__.py` | Create |
| `src/approval/review_context.py` | Create |
| `tests/approval/__init__.py` | Create |
| `tests/approval/test_review_context.py` | Create |

## Technical Notes

- Use existing query patterns from `src/models/taskpacket_crud.py` for TaskPacket lookups.
- The intent spec model is `IntentSpecRead` from `src/intent/intent_spec.py`. Map its fields to `IntentSummary`.
- The verification result model is `VerificationResult` from `src/verification/gate.py`.
- The evidence bundle model is `EvidenceBundle` from `src/agent/evidence.py`.
- QA results come from `src/qa/qa_agent.py` (`QAResult` or equivalent).
- The `to_prompt_context()` output should be structured with headers (e.g., "## Intent", "## QA Results") so the LLM can reference specific sections.
