"""Ruff lint check runner.

Runs ruff check on changed files and reports pass/fail.
"""

import asyncio
import time

from src.verification.runners.base import CheckResult

DEFAULT_TIMEOUT = 120


async def run_ruff(
    changed_files: list[str],
    repo_path: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> CheckResult:
    """Run ruff lint on changed files.

    Args:
        changed_files: List of file paths to check.
        repo_path: Root path of the repository.
        timeout: Max seconds before the check is killed.

    Returns:
        CheckResult with pass/fail and details.
    """
    if not changed_files:
        return CheckResult(name="ruff", passed=True, details="No files to check")

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            "ruff", "check", *changed_files,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0:
            return CheckResult(name="ruff", passed=True, duration_ms=elapsed)
        else:
            output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
            return CheckResult(
                name="ruff",
                passed=False,
                details=output[:2000],
                duration_ms=elapsed,
            )
    except TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="ruff", passed=False, details="Timeout exceeded", duration_ms=elapsed
        )
    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="ruff", passed=False, details="ruff binary not found", duration_ms=elapsed
        )
