# Story 25.2 — Container Lifecycle Manager

> **As a** platform engineer,
> **I want** a `ContainerManager` class that launches, monitors, collects results from, and cleans up agent containers,
> **so that** the Temporal activity can delegate code execution to an isolated container with reliable lifecycle management.

**Purpose:** The container image (Story 25.1) defines what runs. This story defines how the platform controls it: launching with resource limits, waiting for completion, reading results, and cleaning up regardless of exit path. Without this, there is no bridge between Temporal and Docker.

**Intent:** Create `src/agent/container_manager.py` with a `ContainerManager` class that talks to the Docker Engine API. Methods: `launch()` creates a container with resource limits and mounted volumes, `wait()` blocks until exit or timeout, `collect_results()` reads the result file from the container, `cleanup()` removes the container and volumes. All methods are async. Error paths (timeout, OOM, crash) are handled explicitly.

**Points:** 8 | **Size:** L
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 1 (Container Foundation)
**Depends on:** Story 25.1 (agent image must exist to launch)

---

## Description

The `ContainerManager` is the platform's Docker interface. It is the only code that talks to the Docker Engine API. No other module in TheStudio should import `docker` or make Docker API calls.

The manager uses the Docker Engine API via the `docker` Python package (docker-py) or direct HTTP calls via `httpx` to the Unix socket. The choice should favor reliability and error handling over minimalism — `docker-py` is the more battle-tested option.

Key design decisions:
- **Volumes, not bind mounts.** The workspace is a Docker volume created per task, not a bind mount to a host directory. This avoids permission issues and path leakage.
- **Labels for tracking.** Every container gets labels: `thestudio.component=agent`, `thestudio.taskpacket_id={id}`, `thestudio.correlation_id={id}`, `thestudio.created_at={timestamp}`. The reaper uses these labels.
- **No streaming.** The manager does not stream container output during execution. It waits for exit, then collects stdout/stderr and the result file in one batch.

## Tasks

- [ ] Create `src/agent/container_manager.py`:
  - `ContainerManager` class:
    - `__init__(self, image: str = "thestudio-agent:latest", docker_url: str | None = None)` — connects to Docker Engine
    - `async launch(self, task_input_path: str, resource_limits: ResourceLimits, env: dict[str, str], network: str = "agent-net") -> str` — creates volume, copies task input, creates and starts container, returns container_id
    - `async wait(self, container_id: str, timeout_seconds: int) -> int` — waits for container exit, returns exit code. On timeout: kills container, returns -1.
    - `async collect_results(self, container_id: str) -> AgentContainerResult | None` — reads `/workspace/result.json` from container filesystem. Returns None if file missing.
    - `async collect_logs(self, container_id: str) -> str` — reads stdout+stderr from container.
    - `async cleanup(self, container_id: str) -> None` — removes container and associated volume. Idempotent.
    - `async reap_orphans(self, max_age_hours: int = 4) -> int` — finds and removes containers with `thestudio.component=agent` label older than `max_age_hours`. Returns count removed.
  - `ResourceLimits` dataclass: `cpus: float`, `memory_mb: int`, `pids_limit: int = 256`
  - `ContainerLaunchError`, `ContainerTimeoutError` exception classes
- [ ] Handle Docker unavailability: `is_available() -> bool` class method that checks Docker socket connectivity
- [ ] Write unit tests in `tests/agent/test_container_manager.py`:
  - Mock Docker API: launch creates container with correct resource limits
  - Mock Docker API: wait returns exit code
  - Mock Docker API: collect_results reads file from container
  - Mock Docker API: cleanup removes container and volume
  - Mock Docker API: timeout kills container
  - Mock Docker API: reap_orphans finds and removes old containers
  - Mock Docker API: is_available returns False when socket missing
- [ ] Write integration test in `tests/integration/test_container_manager_docker.py` (requires Docker):
  - Launch real container with `alpine:latest`, verify resource limits applied
  - Verify cleanup removes container

## Acceptance Criteria

- [ ] `ContainerManager.launch()` creates a Docker container with specified resource limits
- [ ] `ContainerManager.wait()` returns exit code on normal completion, -1 on timeout
- [ ] `ContainerManager.collect_results()` reads result JSON from container workspace
- [ ] `ContainerManager.cleanup()` removes container and volumes (idempotent)
- [ ] `ContainerManager.reap_orphans()` removes containers older than threshold
- [ ] `ContainerManager.is_available()` detects Docker availability
- [ ] All unit tests pass without Docker installed (mocked API)

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Launch with limits | ResourceLimits(cpus=2, memory_mb=4096) | Container created with `--cpus=2 --memory=4096m` |
| 2 | Wait success | Container exits with code 0 | `wait()` returns 0 |
| 3 | Wait timeout | Container runs past timeout | Container killed, `wait()` returns -1 |
| 4 | Collect results | Container has `/workspace/result.json` | `AgentContainerResult` deserialized |
| 5 | Collect missing results | Container has no result file | Returns None |
| 6 | Cleanup | Container ID | Container and volume removed |
| 7 | Double cleanup | Container ID (already removed) | No error (idempotent) |
| 8 | Reap orphans | 2 containers: 1 old (5h), 1 recent (1h) | Old one removed, recent one kept, returns 1 |
| 9 | Docker unavailable | No Docker socket | `is_available()` returns False |

## Files Affected

| File | Action |
|------|--------|
| `src/agent/container_manager.py` | Create |
| `tests/agent/test_container_manager.py` | Create |
| `tests/integration/test_container_manager_docker.py` | Create |

## Technical Notes

- Docker Engine API: use `docker` package (docker-py) version 7.x. Add to `pyproject.toml` dev and optional dependencies.
- Unix socket path: `/var/run/docker.sock` on Linux, Docker Desktop proxies on macOS/Windows.
- Container creation: use `client.containers.create()` then `container.start()` (not `client.containers.run()`) for better error handling.
- Volume management: create a named volume per task (`thestudio-agent-{taskpacket_id}`), mount at `/workspace`.
- Reading files from container: use `container.get_archive("/workspace/result.json")` to extract the file without needing the container to be running.
- Resource limits mapping: `cpus` -> `nano_cpus` (multiply by 1e9), `memory_mb` -> `mem_limit` (string like `4096m`), `pids_limit` -> `pids_limit`.
- The `reap_orphans` method filters by label `thestudio.component=agent` and compares `thestudio.created_at` against current time.
