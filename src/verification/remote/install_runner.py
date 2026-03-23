"""Dependency installer runner for remote verification.

Runs the repository's install command (e.g. pip install -e .) as a subprocess
in the cloned workspace. Returns a CheckResult for the orchestrator.

Story 40.3 — Epic 40 Slice 1 MVP.
"""

import asyncio
import logging
import shlex
import time

from src.verification.runners.base import CheckResult

logger = logging.getLogger("thestudio.remote_verify")


async def run_install(
    workspace: str,
    install_command: str = "pip install -e .",
    timeout: int = 300,
) -> CheckResult:
    """Run the dependency install command in the workspace.

    Args:
        workspace: Root directory of the cloned repository.
        install_command: Shell command to install dependencies.
        timeout: Maximum seconds before the install is killed.

    Returns:
        CheckResult with name="install" and pass/fail status.
    """
    start = time.monotonic()
    logger.info(
        "remote_verify.install workspace=%s command=%s timeout=%d",
        workspace,
        install_command,
        timeout,
    )

    try:
        args = shlex.split(install_command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0:
            logger.info(
                "remote_verify.install.success workspace=%s elapsed_ms=%d",
                workspace,
                elapsed,
            )
            return CheckResult(
                name="install",
                passed=True,
                details="",
                duration_ms=elapsed,
            )

        stderr_text = stderr.decode(errors="replace")
        logger.warning(
            "remote_verify.install.failed workspace=%s exit=%d",
            workspace,
            proc.returncode,
        )
        return CheckResult(
            name="install",
            passed=False,
            details=stderr_text[:2000],
            duration_ms=elapsed,
        )

    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        detail = f"install timed out after {timeout}s"
        logger.error("remote_verify.install.timeout workspace=%s", workspace)
        return CheckResult(
            name="install",
            passed=False,
            details=detail,
            duration_ms=elapsed,
        )

    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error("remote_verify.install.not_found command=%s", install_command)
        return CheckResult(
            name="install",
            passed=False,
            details=f"Command not found: {install_command}",
            duration_ms=elapsed,
        )
