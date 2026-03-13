# Story 25.1 — Agent Container Image Definition

> **As a** platform engineer,
> **I want** a purpose-built Docker image for the Primary Agent with non-root execution, project dependencies, and a JSON-based entrypoint,
> **so that** agent jobs can run in isolated containers with a clean, reproducible environment.

**Purpose:** Without a dedicated agent image, there is no container to launch. This story creates the image definition and the in-container entrypoint that reads a task, runs the agent, and writes results. Everything else in Epic 25 depends on this image existing and working.

**Intent:** Create `docker/agent/Dockerfile` (Python 3.12-slim, non-root user `agent` UID 1000, git, project deps, Claude Agent SDK) and `src/agent/container_runner.py` (reads `/workspace/task.json`, runs Primary Agent, writes `/workspace/result.json`, exits with code 0 on success, non-zero on failure). Add CI step to build and tag the image on release.

**Points:** 5 | **Size:** M
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 1 (Container Foundation)
**Depends on:** None

---

## Description

The agent container image is the foundation for all container isolation work. It must be minimal (small attack surface), run as non-root (defense in depth), include all dependencies the agent needs (Python packages, git, Claude Agent SDK), and have an entrypoint that follows the container protocol (JSON in, JSON out, exit code signals success/failure).

The container runner (`src/agent/container_runner.py`) is the bridge between the container world and the existing agent code. It deserializes the task input, calls the Primary Agent's `implement()` or `handle_loopback()` function, captures the result, serializes it, and exits. It must handle exceptions gracefully — a crash should still produce a partial result file if possible.

## Tasks

- [ ] Create `docker/agent/Dockerfile`:
  - Base image: `python:3.12-slim`
  - Install system deps: `git`, `curl` (for health checks)
  - Create non-root user `agent` (UID 1000, GID 1000)
  - Copy `requirements.txt` and install Python deps
  - Copy `src/` directory
  - Set `WORKDIR /app`
  - Set `USER agent`
  - Set entrypoint: `python -m src.agent.container_runner`
  - Add labels: `org.opencontainers.image.title=thestudio-agent`, `org.thestudio.component=agent`
- [ ] Create `src/agent/container_runner.py`:
  - `main()` function: reads `/workspace/task.json`, deserializes to `AgentTaskInput`, runs agent, writes `AgentContainerResult` to `/workspace/result.json`
  - On success: exit code 0
  - On agent failure (exception during execution): write result with `success=False`, `exit_reason` containing the exception, exit code 1
  - On input deserialization failure: write error result, exit code 2
  - On unexpected crash: best-effort write of partial result, exit code 3
  - Structured logging to stdout with `correlation_id` from task input
  - `if __name__ == "__main__": main()` guard
- [ ] Create `.dockerignore` for agent image (exclude tests, docs, .git, __pycache__)
- [ ] Add CI workflow step (or document manual build command): `docker build -f docker/agent/Dockerfile -t thestudio-agent:latest .`
- [ ] Write tests:
  - `tests/agent/test_container_runner.py`: container_runner with mock task input file produces valid result output file
  - `tests/agent/test_container_runner.py`: container_runner handles missing task file gracefully (exit code 2)
  - `tests/agent/test_container_runner.py`: container_runner handles agent exception gracefully (exit code 1, result has success=False)
  - Dockerfile build test (integration, requires Docker): image builds, container starts with mock task and exits cleanly

## Acceptance Criteria

- [ ] `docker build -f docker/agent/Dockerfile -t thestudio-agent:latest .` succeeds
- [ ] Container runs as non-root user (UID 1000)
- [ ] Container reads `/workspace/task.json` and writes `/workspace/result.json`
- [ ] Exit code 0 on success, non-zero on failure
- [ ] Graceful error handling: missing input, agent crash, deserialization failure all produce a result file
- [ ] Unit tests pass without Docker installed (mock file I/O)

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Happy path | Valid `task.json` with mock agent | `result.json` with `success=True`, exit code 0 |
| 2 | Missing task file | No `/workspace/task.json` | `result.json` with `success=False`, `exit_reason="input_missing"`, exit code 2 |
| 3 | Invalid JSON | Malformed `/workspace/task.json` | `result.json` with `success=False`, `exit_reason="input_invalid"`, exit code 2 |
| 4 | Agent exception | Valid input, agent raises ValueError | `result.json` with `success=False`, `exit_reason` contains exception, exit code 1 |
| 5 | Docker build | Dockerfile | Image builds, `docker run --rm thestudio-agent:latest --help` exits cleanly |
| 6 | Non-root check | Running container | `whoami` returns `agent`, `id -u` returns `1000` |

## Files Affected

| File | Action |
|------|--------|
| `docker/agent/Dockerfile` | Create |
| `docker/agent/.dockerignore` | Create |
| `src/agent/container_runner.py` | Create |
| `tests/agent/test_container_runner.py` | Create |

## Technical Notes

- The container runner imports from `src.agent.container_protocol` (Story 25.3) for `AgentTaskInput` and `AgentContainerResult`. If 25.3 is not yet complete, define minimal placeholder models in the runner and refactor when 25.3 lands.
- The runner calls `primary_agent.implement()` with a mock `AsyncSession` — it does not have database access. The session is needed only for status transitions, which the container skips (the platform handles status transitions before/after container execution).
- Claude Agent SDK API key is passed via `ANTHROPIC_API_KEY` environment variable to the container (set by `ContainerManager.launch()`).
- Git credentials for repo clone are passed via `GITHUB_TOKEN` environment variable.
