"""Pytest check runner.

Runs pytest on the repository and reports pass/fail.
"""

import asyncio
import time

from src.verification.runners.base import CheckResult

DEFAULT_TIMEOUT = 120


async def run_pytest(
    repo_path: str,
    timeout: int = DEFAULT_TIMEOUT,
    no_tests_policy: str = "pass",
) -> CheckResult:
    """Run pytest on the repository.

    Args:
        repo_path: Root path of the repository.
        timeout: Max seconds before the check is killed.
        no_tests_policy: "pass" or "warn" when no tests are found.

    Returns:
        CheckResult with pass/fail and details.
    """
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "pytest", "--tb=short", "-q",
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = int((time.monotonic() - start) * 1000)
        output = stdout.decode(errors="replace") + stderr.decode(errors="replace")

        # pytest exit code 5 = no tests collected
        if proc.returncode == 5:
            passed = no_tests_policy == "pass"
            return CheckResult(
                name="pytest",
                passed=passed,
                details="No tests collected" + ("" if passed else " (policy: fail)"),
                duration_ms=elapsed,
            )

        if proc.returncode == 0:
            return CheckResult(name="pytest", passed=True, duration_ms=elapsed)
        else:
            return CheckResult(
                name="pytest",
                passed=False,
                details=output[:2000],
                duration_ms=elapsed,
            )
    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="pytest", passed=False, details="Timeout exceeded", duration_ms=elapsed
        )
    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="pytest", passed=False, details="pytest not found", duration_ms=elapsed
        )
