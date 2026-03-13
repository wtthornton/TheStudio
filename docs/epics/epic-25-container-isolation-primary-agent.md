# Epic 25 — Container Isolation for Primary Agent: Sandbox Code Execution Behind an Ephemeral Docker Boundary

**Author:** Saga
**Date:** 2026-03-13
**Status:** Draft — Awaiting Meridian Review
**Target Sprint:** Multi-sprint (estimated 2-3 sprints, ~3 months)
**Prerequisites:** None hard-required. Epic 23 (Unified Agent Framework) recommended but not blocking.

---

## 1. Title

Container Isolation for Primary Agent: Sandbox Code Execution Behind an Ephemeral Docker Boundary — Launch every Primary Agent implementation job in a purpose-built, resource-limited, network-restricted Docker container that receives a serialized task, returns a serialized result, and is destroyed on completion, eliminating state leakage, resource abuse, and host-infrastructure exposure from agent code execution.

## 2. Narrative

The Primary Agent runs code. It reads files, writes files, runs tests, runs linters, and shells out to git. Today, it does all of this inside the Temporal worker process. That process has access to the host filesystem, every environment variable (including database credentials, API keys, and encryption secrets), the internal network (PostgreSQL, Temporal, NATS, FastAPI admin), and unlimited CPU and memory. The agent is one `Bash("curl ...")` away from talking to any internal service.

This was acceptable for Phase 0 when the agent was running against test repos under direct observation. It is not acceptable for production, where the agent will run against customer repositories with varying trust levels, and where a prompt injection in an issue body could instruct the agent to exfiltrate secrets or saturate infrastructure.

**The thepopebot pattern solves this.** Every agent job gets an ephemeral Docker container with:

- **A clean filesystem.** The cloned repo is mounted in, the task context is serialized to a JSON file, and results are written to another JSON file. No state leaks between tasks. No leftover files from a previous run influencing the next one.
- **Resource limits.** CPU, memory, and wall-clock time are capped per trust tier. An Observe-tier task cannot consume 8 CPUs for two hours. An Execute-tier task gets more headroom but still has a ceiling.
- **Network isolation.** The container can reach GitHub (for git operations and API calls). It cannot reach PostgreSQL, Temporal, NATS, or the FastAPI admin. The agent communicates with the platform exclusively through the mounted volume — write your results to `/workspace/result.json` and exit.
- **Easy cleanup.** Container crashes, timeouts, and OOM kills are handled by the lifecycle manager. Orphaned containers get reaped. Partial results are collected when available.

**The communication model is deliberately simple.** No WebSocket streaming, no gRPC, no callback APIs. The Temporal activity serializes the task to a JSON file, launches the container, waits for the container to exit, reads the result JSON file, and returns. This is the simplest possible integration that still gives full isolation.

**Backward compatibility is non-negotiable.** A configuration flag (`THESTUDIO_AGENT_ISOLATION=container|process`) controls the mode. Default is `process` — the current in-process behavior. Container mode is opt-in. This means: no Docker? No problem. CI without Docker-in-Docker? No problem. Local development without the agent image built? No problem. The agent works exactly as it does today unless you explicitly turn on container isolation.

### Why Now

Three factors converge:

1. **Execute tier is landing (Epic 22).** Execute-tier tasks auto-merge PRs. An agent that can touch internal infrastructure and auto-merge is a security incident waiting to happen.

2. **Multi-repo onboarding is starting.** When the agent runs against repos we do not control, the risk surface expands from "our code" to "their code with their dependencies and their build scripts." Isolation is table stakes.

3. **Resource predictability matters for pricing.** If we cannot cap what a single task consumes, we cannot price the service. Resource limits per tier are a business requirement, not just an engineering nicety.

## 3. References

| Artifact | Location |
|----------|----------|
| Primary Agent implementation | `src/agent/primary_agent.py` |
| Developer Role config + system prompt | `src/agent/developer_role.py` |
| Evidence Bundle model | `src/agent/evidence.py` |
| Workflow activities (implement_activity) | `src/workflow/activities.py` |
| Temporal pipeline workflow | `src/workflow/pipeline.py` |
| Application settings | `src/settings.py` |
| Dev Docker Compose | `docker-compose.dev.yml` |
| Prod Docker Compose | `infra/docker-compose.prod.yml` |
| Agent Roles architecture | `thestudioarc/08-agent-roles.md` |
| System Runtime Flow | `thestudioarc/15-system-runtime-flow.md` |
| Coding standards | `thestudioarc/20-coding-standards.md` |
| Pipeline stage mapping | `.claude/rules/pipeline-stages.md` |
| thepopebot architecture (inspiration) | External — ephemeral container per agent job pattern |

## 4. Acceptance Criteria

### Container Image

1. **Agent container image builds successfully.** `docker/agent/Dockerfile` exists, builds a Python 3.12-slim image with project dependencies, git, and the Claude Agent SDK. The image runs as non-root user `agent` (UID 1000). Entrypoint is `python -m src.agent.container_runner`.

2. **Container runner reads task input and writes results.** `src/agent/container_runner.py` reads `AgentTaskInput` from `/workspace/task.json`, executes the Primary Agent logic, and writes `AgentContainerResult` to `/workspace/result.json`. Exit code 0 on success, non-zero on failure.

3. **Container image is tagged per release.** CI builds and tags the agent image on every release. Tag format: `thestudio-agent:{version}` and `thestudio-agent:latest`.

### Container Lifecycle

4. **ContainerManager launches containers with resource limits.** `src/agent/container_manager.py` contains a `ContainerManager` class with `launch()`, `wait()`, `collect_results()`, and `cleanup()` methods. `launch()` creates a container with configurable `--memory`, `--cpus`, and `--pids-limit`.

5. **ContainerManager collects results from mounted volumes.** After container exit, `collect_results()` reads `/workspace/result.json` from the container's workspace volume and deserializes it into `AgentContainerResult`.

6. **ContainerManager cleans up on all exit paths.** Container and volumes are removed after result collection, on timeout, on failure, and on OOM kill. No orphaned containers persist beyond the reaper threshold.

### Task Serialization

7. **AgentTaskInput is a complete, self-contained task description.** Pydantic model with fields: `taskpacket_id`, `correlation_id`, `repo_url`, `branch`, `system_prompt`, `tool_allowlist`, `intent_spec` (serialized), `context_summary`, `max_turns`, `max_budget_usd`. The container needs no database access or API access to TheStudio.

8. **AgentContainerResult captures all agent output.** Pydantic model with fields: `success`, `evidence_bundle` (serialized), `changed_files`, `execution_log`, `tokens_used`, `cost_usd`, `duration_ms`, `exit_reason`. The activity can reconstruct an `EvidenceBundle` from this.

9. **Round-trip serialization is lossless.** `AgentTaskInput` serializes to JSON and deserializes without data loss. Same for `AgentContainerResult`. Tested with property-based or parametric tests.

### Activity Integration

10. **implement_activity supports both modes.** When `THESTUDIO_AGENT_ISOLATION=container`, the activity serializes the task, calls `ContainerManager.launch()`, waits, collects results, and returns an `ImplementOutput`. When `THESTUDIO_AGENT_ISOLATION=process` (default), it runs in-process as today.

11. **Fallback to in-process mode on Docker unavailability.** If container mode is configured but Docker is unavailable (socket not found, daemon not running), the activity logs a warning and falls back to in-process execution. The task does not fail because of infrastructure issues.

12. **Resource limits are configurable per trust tier.** Settings define CPU, memory, and wall-clock timeout per tier: Observe (1 CPU, 2GB, 30min), Suggest (2 CPU, 4GB, 60min), Execute (4 CPU, 8GB, 120min). These are overridable via environment variables.

### Network Isolation

13. **Agent container cannot reach internal services.** The container runs on a restricted Docker network (`agent-net`) that blocks access to PostgreSQL (port 5432), Temporal (port 7233), NATS (port 4222), and the FastAPI admin (port 8000). Verified by integration test.

14. **Agent container can reach GitHub.** Outbound HTTPS to `github.com` and `api.github.com` is allowed for git clone/push and API calls. DNS resolution works inside the container.

15. **Agent communicates with platform only via mounted volume.** No HTTP callbacks, no WebSocket connections, no message queue publishing from inside the container. Input goes in via `/workspace/task.json`, output comes out via `/workspace/result.json`.

### Resource Management

16. **Wall-clock timeout is enforced independently.** `ContainerManager.wait()` enforces a wall-clock timeout that kills the container if exceeded, independent of Docker's resource limits (which handle CPU and memory).

17. **Partial results are collected on timeout.** If the container is killed by timeout, `collect_results()` attempts to read `/workspace/result.json`. If the file exists (agent wrote intermediate results), those are returned with `exit_reason="timeout"`.

18. **Dead container reaper runs periodically.** A cleanup task (callable from cron or Temporal schedule) removes containers with the `thestudio-agent` label that are older than 4 hours. This catches orphaned containers from crashed workers.

### Observability

19. **OpenTelemetry spans cover the container lifecycle.** Spans are emitted for: container launch, container wait, result collection, and cleanup. Span attributes include: `container_id`, `resource_limits`, `exit_code`, `duration_ms`, `repo_tier`.

20. **Container logs are captured with correlation_id.** Container stdout/stderr are collected after exit and logged as structured log entries with the task's `correlation_id` for traceability.

21. **Container metrics are emittable.** Active container count, resource usage by tier, average duration by tier, and timeout rate are available as structured log events (or OpenTelemetry metrics if the metrics SDK is wired).

### 4b. Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docker-in-Docker complexity in CI | High | Medium — CI cannot run integration tests | Integration tests with real Docker run only in environments with Docker; unit tests mock the Docker API. CI label or env var gates Docker tests. |
| Docker socket access is itself a security surface | Medium | High — host escape via Docker socket | Agent container does NOT get Docker socket. Only the Temporal worker (trusted platform code) talks to Docker. Document this boundary clearly. |
| Container startup latency adds to task duration | Medium | Medium — 5-15 seconds per task | Pre-pull agent image on worker startup. Measure and track container_launch_ms span. Acceptable overhead for the security gain. |
| Volume mount permissions break agent file access | Medium | Medium — agent cannot write results | Container runs as UID 1000; workspace volume is created with matching ownership. Tested in Story 25.1. |
| OOM kill loses all results | Medium | Low — partial results mitigate | Agent writes intermediate `result.json` periodically (or at least once before heavy operations). OOM handler in ContainerManager reads partial file. |
| Networking rules differ between Docker Desktop (macOS/Windows) and Linux | High | Medium — isolation tests pass locally but fail in prod | Test network isolation on Linux (production target). Document Docker Desktop limitations. |

## 5. Constraints & Non-Goals

### Constraints

- **No changes to the Temporal workflow structure.** `implement_activity` is still called the same way. Only its internal implementation changes based on the isolation mode.
- **No changes to domain models.** TaskPacket, IntentSpec, EvidenceBundle are unchanged. The container protocol wraps/unwraps them for serialization.
- **Default mode is in-process.** `THESTUDIO_AGENT_ISOLATION` defaults to `process`. Container mode is opt-in. This protects existing deployments and CI.
- **No Docker socket inside agent containers.** The agent cannot launch child containers or access the Docker API. Only the platform (Temporal worker) manages containers.
- **Python 3.12+, existing dependencies only.** The only new dependency candidate is `docker` (docker-py) for the ContainerManager. Evaluate `httpx` against Docker Engine API as a lighter alternative.
- **Dev Compose is not modified for production concerns.** Network isolation configuration goes in `docker-compose.dev.yml` only as a testable example. Production networking is in `infra/docker-compose.prod.yml`.
- **All existing tests pass.** Container isolation is additive. In-process mode is unchanged.

### Non-Goals

- **Not isolating other pipeline agents.** This epic isolates the Primary Agent only — the agent that runs arbitrary code. Other agents (Intake, Context, Intent, etc.) are completion-mode LLM calls with no code execution. If Epic 23 lands and other agents gain tool access, isolation for them is a future epic.
- **Not building a container orchestrator.** This is not Kubernetes. One container per task, managed by the Temporal worker via Docker Engine API. No scheduling, no auto-scaling, no pod management.
- **Not implementing streaming output.** The agent writes results to a file and exits. No live streaming of agent output to the UI. Live output viewing is a future feature.
- **Not building a custom base image registry.** The agent image is built from the repo's Dockerfile and pushed to whatever registry the deployment uses (GHCR, ECR, local). Registry management is out of scope.
- **Not implementing per-repo custom images.** All repos use the same agent image. Per-repo customization (different dependencies, different Python version) is future work.
- **Not adding GPU access.** The agent does not need GPU. If ML workloads are ever needed, that is a different problem.

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Epic Owner | Platform Lead (TBD — assign before sprint start) | Accepts epic scope, reviews AC completion |
| Tech Lead | Backend/Infra Engineer (TBD — assign before sprint start) | Owns container architecture, Docker integration, network policy |
| QA | QA Engineer (TBD — assign before sprint start) | Validates isolation boundaries, resource limits, cleanup behavior |
| Saga | Epic Creator | Authored this epic; available for scope clarification |
| Meridian | VP Success | Reviews this epic before commit; reviews sprint plans |

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Isolation enforced | Agent container cannot reach internal services | Integration test: `curl postgres:5432` from agent container fails; `curl github.com:443` succeeds |
| Resource limits respected | No container exceeds tier limits | Docker stats: memory and CPU stay within configured limits under load |
| Cleanup reliability | Zero orphaned containers after 4 hours | Reaper log: no containers older than threshold found on consecutive runs |
| Mode parity | In-process and container mode produce equivalent EvidenceBundle | Comparison test: same task input produces same files_changed and agent_summary structure in both modes |
| Fallback works | Docker unavailability does not fail tasks | Integration test: stop Docker daemon, run task, verify in-process fallback with warning log |
| Startup overhead | Container launch < 15 seconds (warm image) | Span metric: `container_launch_ms` p95 < 15000 |
| Observability coverage | Every container lifecycle event has a span | Trace export: spans exist for launch, wait, collect, cleanup |
| Zero regression | All pre-existing tests pass with default (process) mode | CI green on merge |

## 8. Context & Assumptions

### Systems Affected

| System | Impact |
|--------|--------|
| `docker/agent/Dockerfile` | **New file** — Agent container image definition |
| `src/agent/container_runner.py` | **New file** — In-container entrypoint: reads task, runs agent, writes result |
| `src/agent/container_manager.py` | **New file** — `ContainerManager`: launch, wait, collect, cleanup |
| `src/agent/container_protocol.py` | **New file** — `AgentTaskInput`, `AgentContainerResult` Pydantic models |
| `src/workflow/activities.py` | **Modified** — `implement_activity` gains container mode branch |
| `src/settings.py` | **Modified** — Add `agent_isolation`, tier resource limits |
| `docker-compose.dev.yml` | **Modified** — Add `agent-net` network definition |
| `infra/docker-compose.prod.yml` | **Modified** — Add `agent-net` network with production iptables rules |
| `src/agent/primary_agent.py` | **Unchanged** — Container runner imports and calls existing `implement()` / `handle_loopback()` |
| `src/agent/developer_role.py` | **Unchanged** — System prompt and tool config reused inside container |
| `src/agent/evidence.py` | **Unchanged** — EvidenceBundle model reused in serialization protocol |

### Assumptions

1. **Docker Engine API is available on the Temporal worker host.** The worker machine runs Docker and exposes the Engine API via Unix socket (`/var/run/docker.sock`) or TCP. Windows development uses Docker Desktop with the Unix socket proxy.

2. **The agent image can be pre-pulled.** Worker startup pulls the `thestudio-agent:latest` image. This avoids cold-start latency on the first task. Image pull time is not counted against task wall-clock timeout.

3. **Mounted volumes are fast enough.** The workspace volume is a Docker volume (not a bind mount to slow storage). File I/O for `task.json` and `result.json` is negligible compared to agent execution time.

4. **Network restriction via Docker network is sufficient.** We do not need iptables rules inside the container or a sidecar proxy. Docker's built-in network isolation (no connection to the `default` bridge) plus explicit egress rules on `agent-net` provide the boundary. This assumption should be validated on the production host OS.

5. **Claude Agent SDK works inside the container.** The SDK needs an API key (passed via environment variable to the container) and outbound HTTPS to Anthropic's API. Both are available in the container.

6. **Git clone works inside the container.** The container has git installed and can clone via HTTPS using a GitHub token passed as an environment variable. SSH clone is not required.

7. **The Temporal activity timeout (already configurable) is the outer bound.** The wall-clock timeout in `ContainerManager` is shorter than the Temporal activity timeout, ensuring the container is cleaned up before Temporal considers the activity timed out.

### Dependencies

- **Upstream:** None hard-required. Epic 23 (Unified Agent Framework) is recommended — if `AgentRunner` exists, the container runner can use it. If not, the container runner calls `primary_agent.implement()` directly.
- **Upstream (infrastructure):** Docker must be available in production. Docker Desktop must be available for local development of container-mode features.
- **Downstream unblocks:** Per-repo custom images (future), multi-agent container isolation (future if Epic 23 agents gain tool access), pricing model (resource limits enable per-tier pricing).

---

## Story Map

Stories are ordered by risk reduction. Sprint 1 builds the container image, protocol, and lifecycle manager. Sprint 2 wires the activity integration, network isolation, and resource management. Sprint 3 adds observability and hardens cleanup.

### Sprint 1: Container Foundation

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 25.1 | **Agent Container Image Definition** | M | Container exists and runs | `docker/agent/Dockerfile`, `src/agent/container_runner.py` |
| 25.2 | **Container Lifecycle Manager** | L | Platform can launch/wait/collect/cleanup containers | `src/agent/container_manager.py` |
| 25.3 | **Task Serialization and Result Collection Protocol** | M | Clean contract between platform and container | `src/agent/container_protocol.py`, `src/agent/container_runner.py` |

### Sprint 2: Integration and Isolation

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 25.4 | **Implement Activity Integration** | L | Container mode works end-to-end | `src/workflow/activities.py`, `src/settings.py` |
| 25.5 | **Agent Network Isolation** | M | Security boundary enforced | `docker-compose.dev.yml`, `infra/docker-compose.prod.yml` |
| 25.6 | **Resource Limits and Cleanup** | L | Tier-based resource control, orphan reaping | `src/agent/container_manager.py`, `src/settings.py` |

### Sprint 3: Observability and Hardening

| # | Story | Size | Value | Files |
|---|-------|------|-------|-------|
| 25.7 | **Observability for Containerized Agents** | M | Full traceability of container lifecycle | `src/agent/container_manager.py`, `src/observability/conventions.py` |

---

## Meridian Review Status

**Round 1: Pending**

| # | Issue | Resolution |
|---|-------|------------|
| — | — | — |
