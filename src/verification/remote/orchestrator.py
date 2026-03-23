"""Remote verification orchestrator.

Coordinates the full remote verification pipeline: clone, install, lint, test.
Handles the fallback path (clone main + apply changed files) when the branch
clone fails. Enforces a total wall-clock timeout.

Story 40.6 — Epic 40 Slice 1 MVP (subprocess mode).
Story 40.11 — Epic 40 Slice 2 (container mode).
Story 40.13 — Epic 40 Slice 2 (observability / structured logging).
"""

import asyncio
import logging
import shutil
import time

from src.observability.conventions import (
    ATTR_CORRELATION_ID,
    ATTR_REMOTE_VERIFY_ALL_PASSED,
    ATTR_REMOTE_VERIFY_BRANCH,
    ATTR_REMOTE_VERIFY_CHECKS_COUNT,
    ATTR_REMOTE_VERIFY_DURATION_MS,
    ATTR_REMOTE_VERIFY_MODE,
    ATTR_REPO,
    ATTR_TASKPACKET_ID,
    SPAN_REMOTE_VERIFY,
    SPAN_REMOTE_VERIFY_CLONE,
    SPAN_REMOTE_VERIFY_INSTALL,
    SPAN_REMOTE_VERIFY_LINT,
    SPAN_REMOTE_VERIFY_TEST,
)
from src.observability.tracing import get_tracer
from src.verification.remote.clone import CloneError, clone_repo
from src.verification.remote.diff_apply import apply_changed_files
from src.verification.remote.install_runner import run_install
from src.verification.runners.base import CheckResult
from src.verification.runners.remote_pytest_runner import run_remote_pytest
from src.verification.runners.remote_ruff_runner import run_remote_ruff

logger = logging.getLogger("thestudio.remote_verify")
tracer = get_tracer("thestudio.remote_verify")


async def verify_remote(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    changed_files: list[str],
    test_command: str = "python -m pytest --tb=short -q",
    lint_command: str = "ruff check .",
    install_command: str = "pip install -e .",
    verify_timeout_seconds: int = 900,
    clone_depth: int = 1,
    clone_timeout: int = 60,
    install_timeout: int = 300,
    lint_timeout: int = 120,
    test_timeout: int = 300,
    remote_verify_mode: str = "subprocess",
    taskpacket_id: str = "",
    correlation_id: str = "",
    container_image: str = "",
    cpu_limit: float = 1.0,
    memory_mb: int = 512,
) -> list[CheckResult]:
    """Run remote verification: clone, install, lint, test.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        branch: Branch to verify (pushed by implement stage).
        token: GitHub token for authentication.
        changed_files: List of changed file paths.
        test_command: Command to run tests.
        lint_command: Command to run linting.
        install_command: Command to install dependencies.
        verify_timeout_seconds: Total wall-clock timeout for entire verification.
        clone_depth: Shallow clone depth.
        clone_timeout: Timeout for clone operation.
        install_timeout: Timeout for install step.
        lint_timeout: Timeout for lint step.
        test_timeout: Timeout for test step.
        remote_verify_mode: "subprocess" (default) or "container".
        taskpacket_id: TaskPacket ID for observability.
        correlation_id: Correlation ID for observability.
        container_image: Docker image for container mode (uses default if empty).
        cpu_limit: CPU limit for container mode.
        memory_mb: Memory limit in MB for container mode.

    Returns:
        List of CheckResult objects from each verification step.
    """
    total_start = time.monotonic()

    with tracer.start_as_current_span(SPAN_REMOTE_VERIFY) as span:
        span.set_attribute(ATTR_REPO, f"{owner}/{repo}")
        span.set_attribute(ATTR_REMOTE_VERIFY_BRANCH, branch)
        span.set_attribute(ATTR_REMOTE_VERIFY_MODE, remote_verify_mode)
        if taskpacket_id:
            span.set_attribute(ATTR_TASKPACKET_ID, taskpacket_id)
        if correlation_id:
            span.set_attribute(ATTR_CORRELATION_ID, correlation_id)

        logger.info(
            "remote_verify.start",
            extra={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "mode": remote_verify_mode,
                "files": len(changed_files),
                "taskpacket_id": taskpacket_id,
                "correlation_id": correlation_id,
            },
        )

        # Route to the appropriate verification mode
        if remote_verify_mode == "container":
            results = await _verify_container_mode(
                owner=owner,
                repo=repo,
                branch=branch,
                token=token,
                changed_files=changed_files,
                test_command=test_command,
                lint_command=lint_command,
                install_command=install_command,
                verify_timeout_seconds=verify_timeout_seconds,
                clone_depth=clone_depth,
                clone_timeout=clone_timeout,
                install_timeout=install_timeout,
                lint_timeout=lint_timeout,
                test_timeout=test_timeout,
                taskpacket_id=taskpacket_id,
                correlation_id=correlation_id,
                container_image=container_image,
                cpu_limit=cpu_limit,
                memory_mb=memory_mb,
            )
        else:
            results = await _verify_subprocess_mode(
                owner=owner,
                repo=repo,
                branch=branch,
                token=token,
                changed_files=changed_files,
                test_command=test_command,
                lint_command=lint_command,
                install_command=install_command,
                verify_timeout_seconds=verify_timeout_seconds,
                clone_depth=clone_depth,
                clone_timeout=clone_timeout,
                install_timeout=install_timeout,
                lint_timeout=lint_timeout,
                test_timeout=test_timeout,
            )

        total_ms = int((time.monotonic() - total_start) * 1000)
        all_passed = all(r.passed for r in results)

        span.set_attribute(ATTR_REMOTE_VERIFY_CHECKS_COUNT, len(results))
        span.set_attribute(ATTR_REMOTE_VERIFY_ALL_PASSED, all_passed)
        span.set_attribute(ATTR_REMOTE_VERIFY_DURATION_MS, total_ms)

        logger.info(
            "remote_verify.complete",
            extra={
                "owner": owner,
                "repo": repo,
                "mode": remote_verify_mode,
                "passed": all_passed,
                "checks": len(results),
                "duration_ms": total_ms,
                "taskpacket_id": taskpacket_id,
                "correlation_id": correlation_id,
            },
        )

        return results


async def _verify_subprocess_mode(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    changed_files: list[str],
    test_command: str,
    lint_command: str,
    install_command: str,
    verify_timeout_seconds: int,
    clone_depth: int,
    clone_timeout: int,
    install_timeout: int,
    lint_timeout: int,
    test_timeout: int,
) -> list[CheckResult]:
    """Subprocess mode: existing Slice 1 behavior."""
    try:
        results = await asyncio.wait_for(
            _verify_inner(
                owner=owner,
                repo=repo,
                branch=branch,
                token=token,
                changed_files=changed_files,
                test_command=test_command,
                lint_command=lint_command,
                install_command=install_command,
                clone_depth=clone_depth,
                clone_timeout=clone_timeout,
                install_timeout=install_timeout,
                lint_timeout=lint_timeout,
                test_timeout=test_timeout,
            ),
            timeout=verify_timeout_seconds,
        )
        return results

    except TimeoutError:
        detail = (
            f"Total verification timeout exceeded after {verify_timeout_seconds}s"
        )
        logger.error(
            "remote_verify.total_timeout",
            extra={"owner": owner, "repo": repo, "timeout": verify_timeout_seconds},
        )
        return [
            CheckResult(
                name="remote_verify",
                passed=False,
                details=detail,
                duration_ms=verify_timeout_seconds * 1000,
            )
        ]


async def _verify_container_mode(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    changed_files: list[str],
    test_command: str,
    lint_command: str,
    install_command: str,
    verify_timeout_seconds: int,
    clone_depth: int,
    clone_timeout: int,
    install_timeout: int,
    lint_timeout: int,
    test_timeout: int,
    taskpacket_id: str,
    correlation_id: str,
    container_image: str,
    cpu_limit: float,
    memory_mb: int,
) -> list[CheckResult]:
    """Container mode: clone on host, then run verification inside a container.

    Falls back to subprocess mode if Docker is unavailable and the isolation
    policy allows fallback for the current tier.
    """
    workspace: str | None = None

    try:
        # Step 1: Clone repo on host (same as subprocess mode)
        clone_start = time.monotonic()
        with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_CLONE) as clone_span:
            clone_span.set_attribute(ATTR_REMOTE_VERIFY_BRANCH, branch)
            logger.info(
                "remote_verify.clone",
                extra={"branch": branch, "mode": "container", "taskpacket_id": taskpacket_id},
            )
            try:
                workspace = await clone_repo(
                    owner=owner,
                    repo=repo,
                    branch=branch,
                    token=token,
                    depth=clone_depth,
                    timeout=clone_timeout,
                )
            except CloneError:
                logger.warning(
                    "remote_verify.clone.fallback",
                    extra={"branch": branch, "taskpacket_id": taskpacket_id},
                )
                try:
                    workspace = await clone_repo(
                        owner=owner,
                        repo=repo,
                        branch="main",
                        token=token,
                        depth=clone_depth,
                        timeout=clone_timeout,
                    )
                    await apply_changed_files(
                        workspace=workspace,
                        changed_files=changed_files,
                        owner=owner,
                        repo=repo,
                        branch=branch,
                        github_token=token,
                    )
                except Exception as fallback_exc:
                    logger.error(
                        "remote_verify.fallback.failed",
                        extra={"error": str(fallback_exc), "taskpacket_id": taskpacket_id},
                    )
                    return [
                        CheckResult(
                            name="clone",
                            passed=False,
                            details=f"Clone and fallback both failed: {fallback_exc}",
                        )
                    ]

            clone_ms = int((time.monotonic() - clone_start) * 1000)
            clone_span.set_attribute(ATTR_REMOTE_VERIFY_DURATION_MS, clone_ms)

        # Step 2: Check Docker availability
        docker_available = _is_docker_available()

        if not docker_available:
            logger.warning(
                "remote_verify.container.docker_unavailable — falling back to subprocess",
                extra={"taskpacket_id": taskpacket_id},
            )
            # Fall back to subprocess execution in the already-cloned workspace
            return await _run_subprocess_in_workspace(
                workspace=workspace,
                install_command=install_command,
                lint_command=lint_command,
                test_command=test_command,
                install_timeout=install_timeout,
                lint_timeout=lint_timeout,
                test_timeout=test_timeout,
            )

        # Step 3: Run verification in container
        logger.info(
            "remote_verify.container.launch",
            extra={
                "workspace": workspace,
                "image": container_image,
                "taskpacket_id": taskpacket_id,
            },
        )

        from src.verification.remote.container_runner import (
            run_verification_container,
        )

        # Run container synchronously in thread pool (Temporal activity pattern)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: run_verification_container(
                workspace,
                install_command=install_command,
                lint_command=lint_command,
                test_command=test_command,
                install_timeout=install_timeout,
                lint_timeout=lint_timeout,
                test_timeout=test_timeout,
                container_timeout=verify_timeout_seconds,
                image=container_image or "thestudio-verify:latest",
                cpu_limit=cpu_limit,
                memory_mb=memory_mb,
                taskpacket_id=taskpacket_id,
                correlation_id=correlation_id,
            ),
        )

        return results

    finally:
        # Cleanup workspace (always, regardless of mode)
        if workspace is not None:
            try:
                shutil.rmtree(workspace, ignore_errors=True)
                logger.info(
                    "remote_verify.cleanup",
                    extra={"workspace": workspace, "taskpacket_id": taskpacket_id},
                )
            except Exception:
                logger.exception(
                    "remote_verify.cleanup.failed",
                    extra={"workspace": workspace},
                )


def _is_docker_available() -> bool:
    """Check if Docker daemon is reachable."""
    try:
        from src.agent.container_manager import ContainerManager

        return ContainerManager.is_docker_available()
    except Exception:
        return False


async def _run_subprocess_in_workspace(
    workspace: str,
    install_command: str,
    lint_command: str,
    test_command: str,
    install_timeout: int,
    lint_timeout: int,
    test_timeout: int,
) -> list[CheckResult]:
    """Run verification steps as subprocesses in an existing workspace.

    Used as the fallback when container mode is requested but Docker
    is unavailable.
    """
    results: list[CheckResult] = []

    with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_INSTALL):
        logger.info(
            "remote_verify.install",
            extra={"workspace": workspace, "mode": "subprocess_fallback"},
        )
        install_result = await run_install(
            workspace=workspace,
            install_command=install_command,
            timeout=install_timeout,
        )
        results.append(install_result)

    if not install_result.passed:
        logger.warning("remote_verify.install.failed — stopping early")
        return results

    with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_LINT):
        logger.info(
            "remote_verify.lint",
            extra={"workspace": workspace, "mode": "subprocess_fallback"},
        )
        lint_result = await run_remote_ruff(
            workspace=workspace,
            lint_command=lint_command,
            timeout=lint_timeout,
        )
        results.append(lint_result)

    with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_TEST):
        logger.info(
            "remote_verify.test",
            extra={"workspace": workspace, "mode": "subprocess_fallback"},
        )
        test_result = await run_remote_pytest(
            workspace=workspace,
            test_command=test_command,
            timeout=test_timeout,
        )
        results.append(test_result)

    return results


async def _verify_inner(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    changed_files: list[str],
    test_command: str,
    lint_command: str,
    install_command: str,
    clone_depth: int,
    clone_timeout: int,
    install_timeout: int,
    lint_timeout: int,
    test_timeout: int,
) -> list[CheckResult]:
    """Inner verification logic for subprocess mode, wrapped by total timeout."""
    workspace: str | None = None
    results: list[CheckResult] = []

    try:
        # Step 1: Clone branch (primary path)
        with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_CLONE):
            logger.info("remote_verify.clone", extra={"branch": branch, "mode": "subprocess"})
            try:
                workspace = await clone_repo(
                    owner=owner,
                    repo=repo,
                    branch=branch,
                    token=token,
                    depth=clone_depth,
                    timeout=clone_timeout,
                )
            except CloneError as exc:
                # Fallback: clone main branch + apply changed files
                logger.warning(
                    "remote_verify.clone.fallback",
                    extra={"branch": branch, "error": str(exc)},
                )
                try:
                    workspace = await clone_repo(
                        owner=owner,
                        repo=repo,
                        branch="main",
                        token=token,
                        depth=clone_depth,
                        timeout=clone_timeout,
                    )
                    await apply_changed_files(
                        workspace=workspace,
                        changed_files=changed_files,
                        owner=owner,
                        repo=repo,
                        branch=branch,
                        github_token=token,
                    )
                except Exception as fallback_exc:
                    logger.error(
                        "remote_verify.fallback.failed",
                        extra={"error": str(fallback_exc)},
                    )
                    return [
                        CheckResult(
                            name="clone",
                            passed=False,
                            details=f"Clone and fallback both failed: {fallback_exc}",
                        )
                    ]

        # Step 2: Install dependencies
        with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_INSTALL):
            logger.info("remote_verify.install", extra={"workspace": workspace, "mode": "subprocess"})
            install_result = await run_install(
                workspace=workspace,
                install_command=install_command,
                timeout=install_timeout,
            )
            results.append(install_result)

        if not install_result.passed:
            logger.warning("remote_verify.install.failed — stopping early")
            return results

        # Step 3: Run lint
        with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_LINT):
            logger.info("remote_verify.lint", extra={"workspace": workspace, "mode": "subprocess"})
            lint_result = await run_remote_ruff(
                workspace=workspace,
                lint_command=lint_command,
                timeout=lint_timeout,
            )
            results.append(lint_result)

        # Step 4: Run tests
        with tracer.start_as_current_span(SPAN_REMOTE_VERIFY_TEST):
            logger.info("remote_verify.test", extra={"workspace": workspace, "mode": "subprocess"})
            test_result = await run_remote_pytest(
                workspace=workspace,
                test_command=test_command,
                timeout=test_timeout,
            )
            results.append(test_result)

        return results

    finally:
        # Step 5: Cleanup workspace (always)
        if workspace is not None:
            try:
                shutil.rmtree(workspace, ignore_errors=True)
                logger.info("remote_verify.cleanup", extra={"workspace": workspace})
            except Exception:
                logger.exception("remote_verify.cleanup.failed", extra={"workspace": workspace})
