# Story 25.3 — Task Serialization and Result Collection Protocol

> **As a** platform engineer,
> **I want** well-defined Pydantic models for task input and container output that serialize losslessly to JSON,
> **so that** the platform and agent container have an explicit, testable contract for data exchange.

**Purpose:** The container protocol is the interface between the Temporal worker (platform) and the agent container. Without a rigorous, typed contract, data will be lost in serialization, fields will drift between the two sides, and debugging will be painful. This story defines the models and proves round-trip fidelity.

**Intent:** Create `src/agent/container_protocol.py` with `AgentTaskInput` and `AgentContainerResult` Pydantic models. Update `src/agent/container_runner.py` (from Story 25.1) to use these models. Write round-trip serialization tests and container_runner integration tests with mock agent.

**Points:** 5 | **Size:** M
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 1 (Container Foundation)
**Depends on:** Story 25.1 (container_runner consumes these models)

---

## Description

The container protocol defines exactly what data flows in and out of the agent container. It is the API boundary between trusted platform code and sandboxed agent code.

`AgentTaskInput` contains everything the agent needs to do its job without any access to TheStudio's internal services. The platform serializes this to `/workspace/task.json` before launching the container. The agent reads it, does its work, and writes `AgentContainerResult` to `/workspace/result.json`.

Key design decisions:
- **Self-contained input.** The task input includes the full system prompt, intent spec, context summary, and repo URL. The agent does not need to query a database or API to understand its task.
- **Structured result.** The result includes success/failure, evidence bundle fields, execution metrics, and an exit reason. The platform can reconstruct an `EvidenceBundle` from the result without guessing.
- **Version field.** Both models include a `protocol_version` field (starting at 1) to allow future evolution without breaking existing containers.

## Tasks

- [ ] Create `src/agent/container_protocol.py`:
  - `AgentTaskInput` (Pydantic BaseModel):
    - `protocol_version: int = 1`
    - `taskpacket_id: str` (UUID as string for JSON safety)
    - `correlation_id: str`
    - `repo_url: str`
    - `branch: str = "main"`
    - `system_prompt: str`
    - `tool_allowlist: list[str]`
    - `intent_spec: dict` (serialized IntentSpec — goal, constraints, acceptance_criteria, non_goals)
    - `context_summary: dict` (scope, risk_flags, complexity)
    - `max_turns: int = 30`
    - `max_budget_usd: float = 5.0`
    - `loopback_attempt: int = 0`
    - `verification_failures: list[dict] | None = None` (for loopback: previous check results)
  - `AgentContainerResult` (Pydantic BaseModel):
    - `protocol_version: int = 1`
    - `success: bool`
    - `taskpacket_id: str`
    - `correlation_id: str`
    - `evidence_bundle: dict | None = None` (serialized EvidenceBundle fields)
    - `changed_files: list[str] = []`
    - `execution_log: str = ""`
    - `agent_summary: str = ""`
    - `tokens_used: int = 0`
    - `cost_usd: float = 0.0`
    - `duration_ms: int = 0`
    - `exit_reason: str = "success"` (success, error, timeout, oom, input_missing, input_invalid)
    - `error_detail: str | None = None`
  - Helper functions:
    - `serialize_task_input(input: AgentTaskInput) -> str` — JSON string
    - `deserialize_task_input(json_str: str) -> AgentTaskInput`
    - `serialize_result(result: AgentContainerResult) -> str` — JSON string
    - `deserialize_result(json_str: str) -> AgentContainerResult`
    - `task_input_from_implement_context(taskpacket, intent, role_config, ...) -> AgentTaskInput` — builds task input from platform domain objects
    - `evidence_bundle_from_result(result: AgentContainerResult) -> EvidenceBundle` — reconstructs EvidenceBundle from container result
- [ ] Update `src/agent/container_runner.py` to import and use `AgentTaskInput` and `AgentContainerResult` from this module
- [ ] Write tests in `tests/agent/test_container_protocol.py`:
  - Round-trip: `AgentTaskInput` -> JSON -> `AgentTaskInput` is lossless
  - Round-trip: `AgentContainerResult` -> JSON -> `AgentContainerResult` is lossless
  - `task_input_from_implement_context` produces valid input from domain objects
  - `evidence_bundle_from_result` reconstructs correct EvidenceBundle
  - Edge cases: empty fields, None values, large strings, Unicode content
  - Invalid JSON: deserialization raises clear error
  - Protocol version mismatch: deserialization of future version raises warning but succeeds (forward-compatible)

## Acceptance Criteria

- [ ] `AgentTaskInput` serializes to JSON and deserializes without data loss
- [ ] `AgentContainerResult` serializes to JSON and deserializes without data loss
- [ ] `task_input_from_implement_context` correctly maps platform domain objects to task input
- [ ] `evidence_bundle_from_result` correctly reconstructs `EvidenceBundle` from container result
- [ ] Container runner reads `AgentTaskInput` and writes `AgentContainerResult`
- [ ] Protocol version field is present on both models

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Task input round-trip | `AgentTaskInput` with all fields populated | Deserialized object equals original |
| 2 | Result round-trip | `AgentContainerResult` with all fields populated | Deserialized object equals original |
| 3 | Minimal task input | Only required fields | Serializes/deserializes; defaults applied |
| 4 | Failure result | `success=False, exit_reason="error", error_detail="ValueError: ..."` | Round-trips correctly |
| 5 | From domain objects | TaskPacketRead + IntentSpecRead + DeveloperRoleConfig | Valid `AgentTaskInput` with all fields mapped |
| 6 | To evidence bundle | `AgentContainerResult` with `changed_files` and `agent_summary` | `EvidenceBundle` with matching fields |
| 7 | Invalid JSON | `"not json"` | `ValidationError` raised |
| 8 | Unicode content | Issue body with CJK characters, emoji | Round-trips without corruption |

## Files Affected

| File | Action |
|------|--------|
| `src/agent/container_protocol.py` | Create |
| `src/agent/container_runner.py` | Modify (import protocol models) |
| `tests/agent/test_container_protocol.py` | Create |

## Technical Notes

- Use `model_dump_json()` and `model_validate_json()` for serialization — these are Pydantic v2 native methods that handle all type coercion.
- UUIDs are stored as strings in the protocol models to avoid JSON serialization issues. The platform converts to/from `UUID` at the boundary.
- The `intent_spec` field is a dict, not an `IntentSpecRead`, because the container does not import database models. The dict contains the same fields: `goal`, `constraints`, `acceptance_criteria`, `non_goals`.
- The `evidence_bundle` field in the result is a dict for the same reason — the platform reconstructs the `EvidenceBundle` Pydantic model from this dict.
- Protocol version 1 is the initial version. Future versions add fields with defaults (backward-compatible) or bump the version number for breaking changes.
