"""Remote pytest runner for remote verification.

Runs a configurable test command in the cloned workspace using asyncio
subprocess. Handles pytest exit codes including 0 (pass), 1 (failures),
2 (interrupted/error), and 5 (no tests collected).

Story 40.4 — Epic 40 Slice 1 MVP.
"""

import asyncio
import logging
import shlex
import time

from src.verification.runners.base import CheckResult

logger = logging.getLogger("thestudio.remote_verify")

MAX_OUTPUT_CHARS = 4000


async def run_remote_pytest(
    workspace: str,
    test_command: str = "python -m pytest --tb=short -q",
    timeout: int = 300,
) -> CheckResult:
    """Run the test command in the workspace.

    Args:
        workspace: Root directory of the cloned repository.
        test_command: Shell command to run tests (split with shlex).
        timeout: Maximum seconds before the test run is killed.

    Returns:
        CheckResult with name="remote_pytest" and pass/fail status.
    """
    start = time.monotonic()
    logger.info(
        "remote_verify.test workspace=%s command=%s timeout=%d",
        workspace,
        test_command,
        timeout,
    )

    try:
        args = shlex.split(test_command)
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

        # pytest exit codes:
        # 0 = all tests passed
        # 1 = some tests failed
        # 2 = test execution interrupted / internal error
        # 5 = no tests collected (treated as pass)
        if proc.returncode == 0:
            logger.info(
                "remote_verify.test.passed workspace=%s elapsed_ms=%d",
                workspace,
                elapsed,
            )
            return CheckResult(
                name="remote_pytest",
                passed=True,
                details="",
                duration_ms=elapsed,
            )

        if proc.returncode == 5:
            logger.info(
                "remote_verify.test.no_tests workspace=%s elapsed_ms=%d",
                workspace,
                elapsed,
            )
            return CheckResult(
                name="remote_pytest",
                passed=True,
                details="No tests collected",
                duration_ms=elapsed,
            )

        # Exit code 1 (test failures) or 2 (error) or other
        logger.warning(
            "remote_verify.test.failed workspace=%s exit=%d elapsed_ms=%d",
            workspace,
            proc.returncode,
            elapsed,
        )
        return CheckResult(
            name="remote_pytest",
            passed=False,
            details=output_truncated,
            duration_ms=elapsed,
        )

    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        detail = f"Test command timed out after {timeout}s"
        logger.error("remote_verify.test.timeout workspace=%s", workspace)
        return CheckResult(
            name="remote_pytest",
            passed=False,
            details=detail,
            duration_ms=elapsed,
        )

    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error("remote_verify.test.not_found command=%s", test_command)
        return CheckResult(
            name="remote_pytest",
            passed=False,
            details=f"Command not found: {test_command}",
            duration_ms=elapsed,
        )
