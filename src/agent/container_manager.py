"""Container lifecycle manager for ephemeral agent execution.

Epic 25 Story 25.2: Manages the Docker container lifecycle for
Primary Agent jobs: launch, wait, collect results, and cleanup.

Epic 25 Story 25.7: Full OTel span coverage for each lifecycle phase
(launch, wait, collect, cleanup). Container logs captured with
correlation_id. Structured metrics emitted for active containers,
resource usage by tier, and timeout rates.

Platform side only — this code runs on the Temporal worker, NOT
inside the agent container.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.agent.container_protocol import (
    AgentContainerResult,
    AgentTaskInput,
)
from src.observability.conventions import (
    ATTR_CONTAINER_CPU_LIMIT,
    ATTR_CONTAINER_EXIT_CODE,
    ATTR_CONTAINER_ID,
    ATTR_CONTAINER_IMAGE,
    ATTR_CONTAINER_LAUNCH_MS,
    ATTR_CONTAINER_MEMORY_MB,
    ATTR_CONTAINER_OOM_KILLED,
    ATTR_CONTAINER_TIMED_OUT,
    ATTR_CONTAINER_TIMEOUT,
    ATTR_CONTAINER_TOTAL_MS,
    ATTR_CONTAINER_WAIT_MS,
    ATTR_CORRELATION_ID,
    ATTR_REPO_TIER,
    ATTR_TASKPACKET_ID,
    SPAN_CONTAINER_CLEANUP,
    SPAN_CONTAINER_COLLECT,
    SPAN_CONTAINER_LAUNCH,
    SPAN_CONTAINER_LIFECYCLE,
    SPAN_CONTAINER_WAIT,
)
from src.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.container")

# Default image tag
DEFAULT_AGENT_IMAGE = "thestudio-agent:latest"

# Label for reaper to find agent containers
CONTAINER_LABEL = "thestudio.role"
CONTAINER_LABEL_VALUE = "agent"

# Reaper threshold: containers older than this are reaped (seconds)
REAPER_THRESHOLD_SECONDS = 4 * 60 * 60  # 4 hours


@dataclass
class ContainerConfig:
    """Resource limits and configuration for an agent container."""

    image: str = DEFAULT_AGENT_IMAGE
    cpu_limit: float = 1.0
    memory_mb: int = 512
    timeout_seconds: int = 300
    network: str = "agent-net"
    pids_limit: int = 256
    environment: dict[str, str] = field(default_factory=dict)


@dataclass
class ContainerOutcome:
    """Result of a container run including lifecycle metadata."""

    result: AgentContainerResult | None
    container_id: str = ""
    exit_code: int = -1
    timed_out: bool = False
    oom_killed: bool = False
    logs: str = ""
    launch_ms: int = 0
    wait_ms: int = 0
    total_ms: int = 0


class ContainerManager:
    """Manages ephemeral Docker containers for agent code execution.

    Lifecycle: launch → wait → collect_results → cleanup.
    All methods are synchronous (called from Temporal activity thread).
    """

    def __init__(self, config: ContainerConfig | None = None) -> None:
        self.config = config or ContainerConfig()
        self._client = None

    def _get_client(self):
        """Lazy-initialize Docker client."""
        if self._client is None:
            import docker

            self._client = docker.from_env()
        return self._client

    @staticmethod
    def is_docker_available() -> bool:
        """Check if Docker daemon is reachable."""
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def launch(
        self,
        task_input: AgentTaskInput,
        *,
        repo_path: str = "",
    ) -> ContainerOutcome:
        """Launch a container, wait for completion, collect results, and clean up.

        This is the primary entry point. It handles the full lifecycle.
        OTel spans are emitted for each phase: launch, wait, collect, cleanup.

        Args:
            task_input: Serialized task for the agent.
            repo_path: Local path to the cloned repo (bind-mounted into container).

        Returns:
            ContainerOutcome with the result and lifecycle metadata.
        """
        total_start = time.monotonic()
        container = None
        workspace_dir = None

        with tracer.start_as_current_span(SPAN_CONTAINER_LIFECYCLE) as span:
            span.set_attribute(ATTR_TASKPACKET_ID, str(task_input.taskpacket_id))
            span.set_attribute(ATTR_CORRELATION_ID, str(task_input.correlation_id))
            span.set_attribute(ATTR_CONTAINER_IMAGE, self.config.image)
            span.set_attribute(ATTR_CONTAINER_CPU_LIMIT, self.config.cpu_limit)
            span.set_attribute(ATTR_CONTAINER_MEMORY_MB, self.config.memory_mb)
            span.set_attribute(ATTR_CONTAINER_TIMEOUT, self.config.timeout_seconds)
            span.set_attribute(ATTR_REPO_TIER, task_input.repo_tier)

            try:
                # Create workspace with task input
                workspace_dir = tempfile.mkdtemp(prefix="thestudio-agent-")
                task_path = Path(workspace_dir) / "task.json"
                task_path.write_text(
                    task_input.model_dump_json(indent=2),
                    encoding="utf-8",
                )

                # Launch container (child span)
                container, launch_ms = self._launch_container(
                    workspace_dir=workspace_dir,
                    repo_path=repo_path,
                    task_input=task_input,
                )

                span.set_attribute(ATTR_CONTAINER_ID, container.short_id)
                span.set_attribute(ATTR_CONTAINER_LAUNCH_MS, launch_ms)

                # Wait for container to finish (child span)
                wait_result, wait_ms = self._wait_with_span(container)

                exit_code = wait_result["StatusCode"]
                span.set_attribute(ATTR_CONTAINER_EXIT_CODE, exit_code)
                span.set_attribute(ATTR_CONTAINER_WAIT_MS, wait_ms)

                # Check for OOM kill
                container.reload()
                oom_killed = container.attrs.get("State", {}).get("OOMKilled", False)
                if oom_killed:
                    span.set_attribute(ATTR_CONTAINER_OOM_KILLED, True)
                    logger.warning(
                        "container.oom_killed",
                        extra={
                            "container_id": container.short_id,
                            "taskpacket_id": str(task_input.taskpacket_id),
                        },
                    )

                # Collect logs with correlation_id (AC #20)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                self._log_container_output(
                    logs,
                    container_id=container.short_id,
                    correlation_id=str(task_input.correlation_id),
                    taskpacket_id=str(task_input.taskpacket_id),
                )

                # Collect results (child span)
                result = self._collect_with_span(workspace_dir)

                total_ms = int((time.monotonic() - total_start) * 1000)
                span.set_attribute(ATTR_CONTAINER_TOTAL_MS, total_ms)

                outcome = ContainerOutcome(
                    result=result,
                    container_id=container.short_id,
                    exit_code=exit_code,
                    timed_out=False,
                    oom_killed=oom_killed,
                    logs=logs,
                    launch_ms=launch_ms,
                    wait_ms=wait_ms,
                    total_ms=total_ms,
                )

                # Emit structured metrics (AC #21)
                self._emit_metrics(outcome, task_input)
                return outcome

            except TimeoutError:
                total_ms = int((time.monotonic() - total_start) * 1000)
                span.set_attribute(ATTR_CONTAINER_TIMED_OUT, True)
                span.set_attribute(ATTR_CONTAINER_TOTAL_MS, total_ms)

                logger.warning(
                    "container.timeout",
                    extra={
                        "container_id": container.short_id if container else "",
                        "taskpacket_id": str(task_input.taskpacket_id),
                        "timeout_seconds": self.config.timeout_seconds,
                    },
                )
                # Attempt partial result collection
                result = self._collect_with_span(workspace_dir) if workspace_dir else None
                if result:
                    result.exit_reason = "timeout"

                outcome = ContainerOutcome(
                    result=result,
                    container_id=container.short_id if container else "",
                    exit_code=-1,
                    timed_out=True,
                    logs="",
                    total_ms=total_ms,
                )
                self._emit_metrics(outcome, task_input)
                return outcome

            except Exception as exc:
                total_ms = int((time.monotonic() - total_start) * 1000)
                span.set_attribute(ATTR_CONTAINER_TOTAL_MS, total_ms)
                logger.exception(
                    "container.error",
                    extra={
                        "taskpacket_id": str(task_input.taskpacket_id),
                        "error": str(exc),
                    },
                )
                outcome = ContainerOutcome(
                    result=AgentContainerResult(
                        success=False,
                        exit_reason="launch_error",
                        error_message=str(exc),
                    ),
                    container_id=container.short_id if container else "",
                    exit_code=-1,
                    total_ms=total_ms,
                )
                self._emit_metrics(outcome, task_input)
                return outcome

            finally:
                self._cleanup_with_span(container, workspace_dir)

    def _launch_container(
        self,
        *,
        workspace_dir: str,
        repo_path: str,
        task_input: AgentTaskInput,
    ) -> tuple:
        """Launch container with a dedicated OTel span. Returns (container, launch_ms)."""
        with tracer.start_as_current_span(SPAN_CONTAINER_LAUNCH) as launch_span:
            launch_start = time.monotonic()
            container = self._create_container(
                workspace_dir=workspace_dir,
                repo_path=repo_path,
                task_input=task_input,
            )
            container.start()
            launch_ms = int((time.monotonic() - launch_start) * 1000)

            launch_span.set_attribute(ATTR_CONTAINER_ID, container.short_id)
            launch_span.set_attribute(ATTR_CONTAINER_LAUNCH_MS, launch_ms)
            launch_span.set_attribute(ATTR_CONTAINER_IMAGE, self.config.image)

            logger.info(
                "container.launched",
                extra={
                    "container_id": container.short_id,
                    "taskpacket_id": str(task_input.taskpacket_id),
                    "correlation_id": str(task_input.correlation_id),
                    "launch_ms": launch_ms,
                },
            )
            return container, launch_ms

    def _wait_with_span(self, container) -> tuple:
        """Wait for container exit with a dedicated OTel span. Returns (result_dict, wait_ms)."""
        with tracer.start_as_current_span(SPAN_CONTAINER_WAIT) as wait_span:
            wait_start = time.monotonic()
            wait_result = self._wait(container)
            wait_ms = int((time.monotonic() - wait_start) * 1000)

            wait_span.set_attribute(ATTR_CONTAINER_ID, container.short_id)
            wait_span.set_attribute(ATTR_CONTAINER_EXIT_CODE, wait_result["StatusCode"])
            wait_span.set_attribute(ATTR_CONTAINER_WAIT_MS, wait_ms)

            return wait_result, wait_ms

    def _collect_with_span(self, workspace_dir: str) -> AgentContainerResult | None:
        """Collect results with a dedicated OTel span."""
        with tracer.start_as_current_span(SPAN_CONTAINER_COLLECT) as collect_span:
            result = self._collect_results(workspace_dir)
            collect_span.set_attribute("thestudio.container.result_found", result is not None)
            if result:
                collect_span.set_attribute("thestudio.container.result_success", result.success)
                collect_span.set_attribute(
                    "thestudio.container.files_changed_count", len(result.files_changed),
                )
            return result

    def _cleanup_with_span(self, container, workspace_dir: str | None) -> None:
        """Cleanup with a dedicated OTel span."""
        with tracer.start_as_current_span(SPAN_CONTAINER_CLEANUP) as cleanup_span:
            container_id = container.short_id if container else ""
            cleanup_span.set_attribute(ATTR_CONTAINER_ID, container_id)
            self._cleanup(container, workspace_dir)

    def _create_container(
        self,
        *,
        workspace_dir: str,
        repo_path: str,
        task_input: AgentTaskInput,
    ):
        """Create the Docker container with resource limits and mounts."""
        client = self._get_client()

        volumes = {
            workspace_dir: {"bind": "/workspace", "mode": "rw"},
        }
        if repo_path:
            volumes[repo_path] = {"bind": "/workspace/repo", "mode": "rw"}

        mem_limit = f"{self.config.memory_mb}m"

        environment = {
            "THESTUDIO_TASKPACKET_ID": str(task_input.taskpacket_id),
            "THESTUDIO_CORRELATION_ID": str(task_input.correlation_id),
        }
        environment.update(self.config.environment)

        return client.containers.create(
            image=self.config.image,
            volumes=volumes,
            environment=environment,
            mem_limit=mem_limit,
            nano_cpus=int(self.config.cpu_limit * 1e9),
            pids_limit=self.config.pids_limit,
            network=self.config.network,
            labels={
                CONTAINER_LABEL: CONTAINER_LABEL_VALUE,
                "thestudio.taskpacket_id": str(task_input.taskpacket_id),
                "thestudio.correlation_id": str(task_input.correlation_id),
            },
            detach=True,
        )

    def _wait(self, container) -> dict:
        """Wait for container to exit, enforcing wall-clock timeout."""
        try:
            return container.wait(timeout=self.config.timeout_seconds)
        except Exception as exc:
            # Timeout or connection error — kill the container
            try:
                container.kill()
            except Exception:
                logger.debug("container.kill_failed", extra={"id": container.short_id})
            raise TimeoutError(
                f"Container {container.short_id} exceeded {self.config.timeout_seconds}s timeout"
            ) from exc

    def _collect_results(self, workspace_dir: str) -> AgentContainerResult | None:
        """Read result.json from the workspace volume."""
        result_path = Path(workspace_dir) / "result.json"
        if not result_path.exists():
            logger.warning(
                "container.no_result_file",
                extra={"workspace": workspace_dir},
            )
            return None

        try:
            raw = json.loads(result_path.read_text(encoding="utf-8"))
            return AgentContainerResult.model_validate(raw)
        except Exception as exc:
            logger.warning(
                "container.result_parse_error",
                extra={"workspace": workspace_dir, "error": str(exc)},
            )
            return None

    def _cleanup(self, container, workspace_dir: str | None) -> None:
        """Remove container and workspace directory."""
        if container:
            try:
                container.remove(force=True)
                logger.debug("container.removed", extra={"id": container.short_id})
            except Exception:
                logger.warning(
                    "container.remove_failed",
                    extra={"id": container.short_id},
                )

        if workspace_dir:
            import shutil

            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                logger.debug("container.workspace_cleanup_failed", extra={"dir": workspace_dir})

    def _log_container_output(
        self,
        logs: str,
        *,
        container_id: str,
        correlation_id: str,
        taskpacket_id: str,
    ) -> None:
        """Log container stdout/stderr with correlation_id for traceability (AC #20)."""
        if not logs.strip():
            return

        for line in logs.splitlines():
            logger.info(
                "container.output",
                extra={
                    "container_id": container_id,
                    "correlation_id": correlation_id,
                    "taskpacket_id": taskpacket_id,
                    "line": line,
                },
            )

    def _emit_metrics(
        self,
        outcome: ContainerOutcome,
        task_input: AgentTaskInput,
    ) -> None:
        """Emit structured log events for container metrics (AC #21).

        Emits: active container count proxy, resource usage by tier,
        duration by tier, and timeout indicator.
        """
        logger.info(
            "container.metrics",
            extra={
                "container_id": outcome.container_id,
                "taskpacket_id": str(task_input.taskpacket_id),
                "correlation_id": str(task_input.correlation_id),
                "repo_tier": task_input.repo_tier,
                "exit_code": outcome.exit_code,
                "timed_out": outcome.timed_out,
                "oom_killed": outcome.oom_killed,
                "launch_ms": outcome.launch_ms,
                "wait_ms": outcome.wait_ms,
                "total_ms": outcome.total_ms,
                "cpu_limit": self.config.cpu_limit,
                "memory_mb": self.config.memory_mb,
                "timeout_seconds": self.config.timeout_seconds,
                "success": outcome.result.success if outcome.result else False,
            },
        )

    def reap_orphans(self) -> int:
        """Remove agent containers older than the reaper threshold.

        Returns the number of containers reaped.
        """
        import datetime

        client = self._get_client()
        reaped = 0

        containers = client.containers.list(
            all=True,
            filters={"label": f"{CONTAINER_LABEL}={CONTAINER_LABEL_VALUE}"},
        )

        now = datetime.datetime.now(datetime.UTC)
        for container in containers:
            created_str = container.attrs.get("Created", "")
            if not created_str:
                continue

            try:
                # Docker returns ISO format timestamps
                created = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_seconds = (now - created).total_seconds()

                if age_seconds > REAPER_THRESHOLD_SECONDS:
                    container.remove(force=True)
                    reaped += 1
                    logger.info(
                        "container.reaped",
                        extra={
                            "container_id": container.short_id,
                            "age_seconds": int(age_seconds),
                        },
                    )
            except Exception:
                logger.warning(
                    "container.reap_failed",
                    extra={"container_id": container.short_id},
                )

        return reaped
