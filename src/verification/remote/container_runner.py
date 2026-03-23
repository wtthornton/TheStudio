"""Container-based verification runner for remote verification.

Epic 40 Story 40.10: Launches verification inside an ephemeral Docker
container via ContainerManager. Mounts the cloned workspace, passes
verification config as task JSON, waits for completion, and maps the
result JSON back to list[CheckResult].

This code runs on the PLATFORM side (Temporal activity thread), not
inside the container. All methods are synchronous because Temporal
activities run in a thread pool.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path

from src.verification.runners.base import CheckResult

logger = logging.getLogger("thestudio.remote_verify")

# Default verification container image
DEFAULT_VERIFY_IMAGE = "thestudio-verify:latest"

# Container label for identification and reaping
CONTAINER_LABEL = "thestudio.role"
CONTAINER_LABEL_VALUE = "verify"


def run_verification_container(
    workspace: str,
    *,
    install_command: str = "pip install -e .",
    lint_command: str = "ruff check .",
    test_command: str = "python -m pytest --tb=short -q",
    install_timeout: int = 300,
    lint_timeout: int = 120,
    test_timeout: int = 300,
    container_timeout: int = 900,
    image: str = DEFAULT_VERIFY_IMAGE,
    cpu_limit: float = 1.0,
    memory_mb: int = 512,
    taskpacket_id: str = "",
    correlation_id: str = "",
) -> list[CheckResult]:
    """Launch a verification container and collect results.

    The container runs verify_entrypoint.py which executes install, lint,
    and test steps sequentially. Results are written to /workspace/result.json
    and mapped back to CheckResult objects.

    Args:
        workspace: Host path to the cloned repo directory.
        install_command: Command to install dependencies.
        lint_command: Command to run linting.
        test_command: Command to run tests.
        install_timeout: Timeout for install step inside container.
        lint_timeout: Timeout for lint step inside container.
        test_timeout: Timeout for test step inside container.
        container_timeout: Wall-clock timeout for the entire container run.
        image: Docker image to use.
        cpu_limit: CPU limit for the container.
        memory_mb: Memory limit in MB.
        taskpacket_id: TaskPacket ID for logging/labels.
        correlation_id: Correlation ID for logging/labels.

    Returns:
        List of CheckResult objects from verification steps.
    """
    import docker

    start = time.monotonic()
    logger.info(
        "container_verify.start workspace=%s image=%s taskpacket=%s",
        workspace,
        image,
        taskpacket_id,
    )

    # Create a temp directory for task input/output exchange
    exchange_dir = tempfile.mkdtemp(prefix="thestudio-verify-")
    container = None

    try:
        # Write task configuration to exchange volume
        task_config = {
            "install_command": install_command,
            "lint_command": lint_command,
            "test_command": test_command,
            "install_timeout": install_timeout,
            "lint_timeout": lint_timeout,
            "test_timeout": test_timeout,
            "repo_dir": "/workspace/repo",
        }
        task_path = Path(exchange_dir) / "task.json"
        task_path.write_text(json.dumps(task_config, indent=2), encoding="utf-8")

        # Launch container
        client = docker.from_env()
        mem_limit = f"{memory_mb}m"

        volumes = {
            exchange_dir: {"bind": "/workspace", "mode": "rw"},
            workspace: {"bind": "/workspace/repo", "mode": "ro"},
        }

        environment = {}
        if taskpacket_id:
            environment["THESTUDIO_TASKPACKET_ID"] = taskpacket_id
        if correlation_id:
            environment["THESTUDIO_CORRELATION_ID"] = correlation_id

        container = client.containers.create(
            image=image,
            volumes=volumes,
            environment=environment,
            mem_limit=mem_limit,
            nano_cpus=int(cpu_limit * 1e9),
            network_mode="none",  # No network needed for verification
            labels={
                CONTAINER_LABEL: CONTAINER_LABEL_VALUE,
                "thestudio.taskpacket_id": taskpacket_id,
                "thestudio.correlation_id": correlation_id,
            },
            detach=True,
        )

        launch_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "container_verify.launched container=%s launch_ms=%d",
            container.short_id,
            launch_ms,
        )

        container.start()

        # Wait for container to finish
        try:
            wait_result = container.wait(timeout=container_timeout)
        except Exception as exc:
            # Timeout or connection error — kill the container
            try:
                container.kill()
            except Exception:
                pass
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(
                "container_verify.timeout container=%s elapsed_ms=%d",
                container.short_id,
                elapsed,
            )
            return [
                CheckResult(
                    name="container_verify",
                    passed=False,
                    details=f"Container timed out after {container_timeout}s: {exc}",
                    duration_ms=elapsed,
                )
            ]

        exit_code = wait_result.get("StatusCode", -1)
        elapsed = int((time.monotonic() - start) * 1000)

        # Log container output
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        if logs.strip():
            for line in logs.splitlines()[:50]:  # Cap log lines
                logger.info(
                    "container_verify.output container=%s line=%s",
                    container.short_id,
                    line,
                )

        # Collect results
        result_path = Path(exchange_dir) / "result.json"
        if not result_path.exists():
            logger.warning(
                "container_verify.no_result container=%s exit_code=%d",
                container.short_id,
                exit_code,
            )
            return [
                CheckResult(
                    name="container_verify",
                    passed=False,
                    details=f"Container exited with code {exit_code} but no result file found",
                    duration_ms=elapsed,
                )
            ]

        raw = json.loads(result_path.read_text(encoding="utf-8"))
        checks = _parse_result(raw)

        logger.info(
            "container_verify.complete container=%s exit_code=%d checks=%d elapsed_ms=%d",
            container.short_id,
            exit_code,
            len(checks),
            elapsed,
        )
        return checks

    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.exception(
            "container_verify.error taskpacket=%s error=%s",
            taskpacket_id,
            str(exc),
        )
        return [
            CheckResult(
                name="container_verify",
                passed=False,
                details=f"Container verification failed: {exc}",
                duration_ms=elapsed,
            )
        ]

    finally:
        # Cleanup container
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                logger.debug(
                    "container_verify.cleanup_failed container=%s",
                    container.short_id if container else "unknown",
                )

        # Cleanup exchange directory
        import shutil

        shutil.rmtree(exchange_dir, ignore_errors=True)


def _parse_result(raw: dict) -> list[CheckResult]:
    """Parse result.json from the container into CheckResult objects.

    Expected format::

        {
            "checks": [
                {"name": "install", "passed": true, "details": "", "duration_ms": 100},
                ...
            ],
            "passed": true,
            "total_duration_ms": 500
        }
    """
    checks: list[CheckResult] = []
    for entry in raw.get("checks", []):
        checks.append(
            CheckResult(
                name=entry.get("name", "unknown"),
                passed=bool(entry.get("passed", False)),
                details=str(entry.get("details", "")),
                duration_ms=int(entry.get("duration_ms", 0)),
            )
        )

    if not checks:
        # Fallback: use top-level passed field
        checks.append(
            CheckResult(
                name="container_verify",
                passed=bool(raw.get("passed", False)),
                details="No individual check results reported",
                duration_ms=int(raw.get("total_duration_ms", 0)),
            )
        )

    return checks
