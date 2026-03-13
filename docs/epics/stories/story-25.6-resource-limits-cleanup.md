# Story 25.6 — Resource Limits and Cleanup

> **As a** platform engineer,
> **I want** configurable resource limits per trust tier with independent wall-clock timeout and a dead container reaper,
> **so that** agent tasks cannot exhaust host resources, runaway containers are killed reliably, and orphaned containers are cleaned up automatically.

**Purpose:** Container isolation without resource limits is an incomplete boundary. A container that can consume unlimited CPU and memory can denial-of-service the host even if it cannot access internal services. This story enforces per-tier resource budgets and ensures cleanup happens on every exit path, including the ones we did not anticipate.

**Intent:** Implement per-tier resource limit selection (Observe/Suggest/Execute), independent wall-clock timeout enforcement in `ContainerManager.wait()`, partial result collection on timeout/OOM, and a reaper function that cleans up orphaned containers older than 4 hours. Resource limits are configured via environment variables and enforced by Docker.

**Points:** 8 | **Size:** L
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 2 (Integration and Isolation)
**Depends on:** Stories 25.2 (ContainerManager), 25.4 (activity integration with tier config)

---

## Description

Resource limits are enforced at two levels:

1. **Docker resource limits** (`--memory`, `--cpus`, `--pids-limit`): Docker enforces these kernel-level. If a container exceeds memory, it gets OOM-killed. If it exceeds CPU, it gets throttled. These are hard limits that the agent cannot bypass.

2. **Wall-clock timeout** (ContainerManager): The Temporal activity enforces a wall-clock timeout independent of Docker. If the container runs too long (even if it is within CPU/memory limits), it gets killed. This catches agents that are stuck in infinite loops, waiting on network timeouts, or just taking too long.

The reaper is a safety net for the safety net. If a Temporal worker crashes after launching a container but before cleaning it up, the container is orphaned. The reaper runs periodically (invoked by cron, Temporal schedule, or admin endpoint) and removes any agent container older than 4 hours.

## Tasks

- [ ] Implement `get_resource_limits(repo_tier: str) -> ResourceLimits` in `src/agent/container_manager.py` or `src/agent/resource_limits.py`:
  - Read from settings: `agent_{tier}_cpus`, `agent_{tier}_memory_mb`, `agent_{tier}_timeout_minutes`
  - Tier mapping: `observe` -> conservative, `suggest` -> moderate, `execute` -> generous
  - Unknown tier falls back to `observe` limits (fail safe)
  - Default values: Observe (1 CPU, 2GB, 30min), Suggest (2 CPU, 4GB, 60min), Execute (4 CPU, 8GB, 120min)
- [ ] Enhance `ContainerManager.wait()` wall-clock timeout:
  - Use `asyncio.wait_for()` or polling loop with time tracking
  - On timeout: call `container.kill()`, set exit code to -1
  - Log timeout event with `container_id`, `timeout_seconds`, `repo_tier`
- [ ] Implement partial result collection on timeout/OOM:
  - After timeout kill: attempt `collect_results()` — if `/workspace/result.json` exists, return it with `exit_reason="timeout"`
  - After OOM kill (detected via `container.attrs["State"]["OOMKilled"]`): attempt `collect_results()` with `exit_reason="oom"`
  - If no result file: return `AgentContainerResult(success=False, exit_reason="timeout|oom", error_detail="...")`
- [ ] Implement `ContainerManager.reap_orphans(max_age_hours: int = 4) -> int`:
  - List containers with label `thestudio.component=agent`
  - Check `thestudio.created_at` label against current time
  - Remove containers (and their volumes) older than `max_age_hours`
  - Return count of removed containers
  - Log each removal with container_id and age
- [ ] Add pids_limit to container creation: `pids_limit=256` (prevents fork bombs)
- [ ] Write tests in `tests/agent/test_resource_limits.py`:
  - `get_resource_limits("observe")` returns correct defaults
  - `get_resource_limits("suggest")` returns correct defaults
  - `get_resource_limits("execute")` returns correct defaults
  - `get_resource_limits("unknown")` falls back to observe
  - Custom override via settings
- [ ] Write tests in `tests/agent/test_container_cleanup.py`:
  - Timeout: mock container that exceeds timeout, verify kill and partial collection
  - OOM: mock container with OOMKilled=True, verify detection and partial collection
  - Reaper: mock container list with old and new containers, verify only old removed
  - Reaper: empty container list, verify returns 0
- [ ] Integration test (requires Docker): launch container with `--memory=32m` running a memory hog, verify OOM kill detected

## Acceptance Criteria

- [ ] Resource limits are configurable per tier via environment variables
- [ ] Unknown tier falls back to Observe limits
- [ ] Wall-clock timeout kills container independently of Docker resource limits
- [ ] Partial results are collected on timeout when available
- [ ] OOM kills are detected and reported with `exit_reason="oom"`
- [ ] Reaper removes containers older than threshold
- [ ] Reaper is idempotent (running twice does not error on already-removed containers)
- [ ] pids_limit is enforced (prevents fork bombs)

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Observe limits | `repo_tier="observe"` | 1 CPU, 2048 MB, 30 min |
| 2 | Suggest limits | `repo_tier="suggest"` | 2 CPU, 4096 MB, 60 min |
| 3 | Execute limits | `repo_tier="execute"` | 4 CPU, 8192 MB, 120 min |
| 4 | Unknown tier | `repo_tier="foo"` | Falls back to Observe |
| 5 | Wall-clock timeout | Container runs 5s, timeout 2s | Container killed, exit code -1 |
| 6 | Partial result on timeout | Container writes result.json then hangs | Result collected with `exit_reason="timeout"` |
| 7 | No result on timeout | Container hangs without writing | `AgentContainerResult(success=False, exit_reason="timeout")` |
| 8 | OOM detection | Container OOM-killed | `exit_reason="oom"` in result |
| 9 | Reaper: old containers | Container created 5 hours ago | Removed, count=1 |
| 10 | Reaper: recent containers | Container created 1 hour ago | Kept, count=0 |
| 11 | Reaper: no containers | Empty list | count=0, no errors |

## Files Affected

| File | Action |
|------|--------|
| `src/agent/container_manager.py` | Modify (enhance wait, add reaper, add OOM detection) |
| `src/settings.py` | Modify (add per-tier resource limit settings — may already exist from 25.4) |
| `tests/agent/test_resource_limits.py` | Create |
| `tests/agent/test_container_cleanup.py` | Create |

## Technical Notes

- Docker memory limit: `mem_limit="2048m"` or `mem_limit=2147483648` (bytes). OOM behavior: container process is killed with SIGKILL, `State.OOMKilled` is set to True.
- Docker CPU limit: `nano_cpus=1000000000` (1 CPU) or `cpu_quota` + `cpu_period`. The `nano_cpus` parameter is simpler.
- Docker pids_limit: `pids_limit=256`. This is a hard limit on the number of processes in the container. Prevents fork bombs.
- Wall-clock timeout is separate from Docker's `--stop-timeout`. We use `container.kill()` (SIGKILL, immediate) rather than `container.stop()` (SIGTERM then SIGKILL after grace period) because the agent has already exceeded its time budget.
- The reaper can be exposed as: (1) a standalone script callable from cron, (2) a Temporal scheduled workflow, or (3) an admin API endpoint. For Phase 1, implement it as a callable function and document invocation options. Do not build the scheduling infrastructure in this story.
- OOM detection: after `container.wait()`, check `container.attrs["State"]["OOMKilled"]`. If True, this was an OOM kill, not a normal exit or timeout.
