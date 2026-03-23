"""Remote ruff lint runner for remote verification.

Runs a configurable lint command in the cloned workspace using asyncio
subprocess. Returns a CheckResult for the orchestrator.

Story 40.5 — Epic 40 Slice 1 MVP.
"""

import asyncio
import logging
import shlex
import time

from src.verification.runners.base import CheckResult

logger = logging.getLogger("thestudio.remote_verify")

MAX_OUTPUT_CHARS = 4000


async def run_remote_ruff(
    workspace: str,
    lint_command: str = "ruff check .",
    timeout: int = 120,
) -> CheckResult:
    """Run the lint command in the workspace.

    Args:
        workspace: Root directory of the cloned repository.
        lint_command: Shell command to run linting (split with shlex).
        timeout: Maximum seconds before the lint run is killed.

    Returns:
        CheckResult with name="remote_ruff" and pass/fail status.
    """
    start = time.monotonic()
    logger.info(
        "remote_verify.lint workspace=%s command=%s timeout=%d",
        workspace,
        lint_command,
        timeout,
    )

    try:
        args = shlex.split(lint_command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = int((time.monotonic() - start) * 1000)
        output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
        output_truncated = output[:MAX_OUTPUT_CHARS]

        if proc.returncode == 0:
            logger.info(
                "remote_verify.lint.passed workspace=%s elapsed_ms=%d",
                workspace,
                elapsed,
            )
            return CheckResult(
                name="remote_ruff",
                passed=True,
                details="",
                duration_ms=elapsed,
            )

        logger.warning(
            "remote_verify.lint.failed workspace=%s exit=%d elapsed_ms=%d",
            workspace,
            proc.returncode,
            elapsed,
        )
        return CheckResult(
            name="remote_ruff",
            passed=False,
            details=output_truncated,
            duration_ms=elapsed,
        )

    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        detail = f"Lint command timed out after {timeout}s"
        logger.error("remote_verify.lint.timeout workspace=%s", workspace)
        return CheckResult(
            name="remote_ruff",
            passed=False,
            details=detail,
            duration_ms=elapsed,
        )

    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error("remote_verify.lint.not_found command=%s", lint_command)
        return CheckResult(
            name="remote_ruff",
            passed=False,
            details=f"Command not found: {lint_command}",
            duration_ms=elapsed,
        )
