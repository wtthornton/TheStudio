# Story 25.4 — Implement Activity Integration

> **As a** platform engineer,
> **I want** the `implement_activity` to support both container-isolated and in-process execution modes via a configuration flag,
> **so that** container isolation is opt-in, backward-compatible, and gracefully degrades when Docker is unavailable.

**Purpose:** Stories 25.1-25.3 built the container image, lifecycle manager, and protocol. This story wires them into the Temporal activity that orchestrates the Primary Agent. Without this integration, the container infrastructure exists but is never used. This is the story that makes container isolation real.

**Intent:** Modify `implement_activity` in `src/workflow/activities.py` to check `THESTUDIO_AGENT_ISOLATION` setting. In `container` mode: serialize task via `container_protocol`, launch via `ContainerManager`, wait, collect results, map back to `ImplementOutput`. In `process` mode: run as today. Fallback: if `container` mode is configured but Docker is unavailable, log warning and run in-process. Add resource limit configuration per trust tier to `src/settings.py`.

**Points:** 8 | **Size:** L
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 2 (Integration and Isolation)
**Depends on:** Stories 25.1, 25.2, 25.3

---

## Description

This story connects all the container infrastructure to the actual pipeline. The `implement_activity` is the Temporal activity that runs the Primary Agent. Today, it delegates to `primary_agent.implement()` in-process. After this story, it has two execution paths:

1. **Container mode** (`THESTUDIO_AGENT_ISOLATION=container`): Serialize the task context to `AgentTaskInput`, call `ContainerManager.launch()`, wait for the container to finish, call `ContainerManager.collect_results()`, map the `AgentContainerResult` back to `ImplementOutput`, and clean up.

2. **Process mode** (`THESTUDIO_AGENT_ISOLATION=process`, default): Run exactly as today. No behavior change.

The mode selection happens at the top of `implement_activity`. The rest of the pipeline is unaware of which mode was used.

## Tasks

- [ ] Add settings to `src/settings.py`:
  - `agent_isolation: str = "process"` — valid values: `"process"`, `"container"`
  - `agent_container_image: str = "thestudio-agent:latest"`
  - `agent_container_network: str = "agent-net"`
  - Resource limits per tier (nested or flat):
    - `agent_observe_cpus: float = 1.0`
    - `agent_observe_memory_mb: int = 2048`
    - `agent_observe_timeout_minutes: int = 30`
    - `agent_suggest_cpus: float = 2.0`
    - `agent_suggest_memory_mb: int = 4096`
    - `agent_suggest_timeout_minutes: int = 60`
    - `agent_execute_cpus: float = 4.0`
    - `agent_execute_memory_mb: int = 8192`
    - `agent_execute_timeout_minutes: int = 120`
- [ ] Create helper function `_get_resource_limits(repo_tier: str) -> ResourceLimits` in activities or a shared utility
- [ ] Modify `implement_activity` in `src/workflow/activities.py`:
  - Import `ContainerManager`, `AgentTaskInput`, `AgentContainerResult`, protocol helpers
  - At top: check `settings.agent_isolation`
  - If `"container"`:
    1. Check `ContainerManager.is_available()` — if False, log warning, fall back to process mode
    2. Build `AgentTaskInput` from activity params (use `task_input_from_implement_context` helper)
    3. Write task input to temp file
    4. Get resource limits for the task's tier
    5. Call `ContainerManager.launch()`
    6. Call `ContainerManager.wait()` with tier timeout
    7. Call `ContainerManager.collect_results()`
    8. Call `ContainerManager.collect_logs()` — log with correlation_id
    9. Call `ContainerManager.cleanup()`
    10. Map `AgentContainerResult` to `ImplementOutput`
    11. On timeout: collect partial results if available, return with what we have
    12. On any container error: log error, return failure output (do not crash the activity)
  - If `"process"`: existing behavior unchanged
- [ ] Write tests in `tests/workflow/test_implement_container.py`:
  - Container mode happy path: mock ContainerManager, verify launch/wait/collect/cleanup sequence
  - Container mode timeout: mock wait returns -1, verify partial result collection
  - Container mode Docker unavailable: mock is_available returns False, verify fallback to process mode
  - Process mode: verify existing behavior unchanged when `agent_isolation="process"`
  - Resource limits: verify correct limits selected per tier
- [ ] Update existing tests to ensure they still pass with default `agent_isolation="process"`

## Acceptance Criteria

- [ ] `implement_activity` supports `THESTUDIO_AGENT_ISOLATION=container` mode
- [ ] `implement_activity` falls back to process mode when Docker is unavailable
- [ ] Resource limits are selected based on repo tier
- [ ] Container mode follows full lifecycle: serialize -> launch -> wait -> collect -> cleanup
- [ ] Timeout handling collects partial results
- [ ] Default mode (`process`) behavior is identical to pre-epic behavior
- [ ] All existing workflow tests pass without modification

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Container happy path | `agent_isolation=container`, Docker available | ContainerManager lifecycle called, ImplementOutput from container result |
| 2 | Container timeout | Container exceeds timeout | Partial result collected, `ImplementOutput` with available data |
| 3 | Container error | Container exits with code 1 | Error logged, `ImplementOutput` with failure info |
| 4 | Docker unavailable | `agent_isolation=container`, no Docker | Warning logged, runs in-process, returns normal output |
| 5 | Process mode | `agent_isolation=process` (default) | Existing behavior, ContainerManager never called |
| 6 | Observe tier limits | `repo_tier="observe"` | 1 CPU, 2GB RAM, 30min timeout |
| 7 | Execute tier limits | `repo_tier="execute"` | 4 CPU, 8GB RAM, 120min timeout |
| 8 | Unknown tier | `repo_tier="unknown"` | Falls back to Observe tier limits |

## Files Affected

| File | Action |
|------|--------|
| `src/settings.py` | Modify (add isolation and resource limit settings) |
| `src/workflow/activities.py` | Modify (add container mode branch to implement_activity) |
| `tests/workflow/test_implement_container.py` | Create |

## Technical Notes

- The `ImplementInput` dataclass does not currently carry `repo_tier`. Either add it as an optional field or look it up from the TaskPacket. Adding it to `ImplementInput` is cleaner and avoids a database call in the activity.
- The temp file for task input should be created via `tempfile.NamedTemporaryFile` and cleaned up after the container copies it to the volume.
- Container environment variables to pass: `ANTHROPIC_API_KEY` (from settings), `GITHUB_TOKEN` (from settings or per-repo config).
- The mapping from `AgentContainerResult` to `ImplementOutput` is straightforward: `taskpacket_id` passes through, `files_changed` maps directly, `agent_summary` maps directly, `intent_version` comes from the task input.
