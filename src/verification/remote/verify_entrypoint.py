"""Verification container entrypoint — runs inside the ephemeral container.

Epic 40 Story 40.9: Reads a verification task JSON file from the mounted
workspace, runs install + lint + test commands, and writes a result JSON
file with CheckResult-compatible output.

This module runs INSIDE the Docker container. It has:
- Filesystem access to the cloned repo (mounted at /workspace/repo)
- No access to PostgreSQL, Temporal, NATS, or FastAPI
- No TheStudio source imports (standalone script)

Communication with the platform is exclusively via the mounted volume:
  /workspace/task.json  -> input (verification config)
  /workspace/result.json <- output (check results)
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("thestudio.verify_entrypoint")

# Default paths (aligned with container_protocol volume convention)
WORKSPACE_DIR = "/workspace"
TASK_INPUT_PATH = f"{WORKSPACE_DIR}/task.json"
RESULT_OUTPUT_PATH = f"{WORKSPACE_DIR}/result.json"
REPO_DIR = f"{WORKSPACE_DIR}/repo"


def read_task(task_path: str = TASK_INPUT_PATH) -> dict:
    """Read and parse the verification task JSON.

    Expected schema::

        {
            "install_command": "pip install -e .",
            "lint_command": "ruff check .",
            "test_command": "python -m pytest --tb=short -q",
            "install_timeout": 300,
            "lint_timeout": 120,
            "test_timeout": 300,
            "repo_dir": "/workspace/repo"
        }

    All fields are optional with sensible defaults.
    """
    path = Path(task_path)
    if not path.exists():
        logger.warning("No task file at %s, using defaults", task_path)
        return {}

    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def run_step(
    name: str,
    command: str,
    cwd: str,
    timeout: int = 300,
) -> dict:
    """Run a single verification step as a subprocess.

    Args:
        name: Step name (install, lint, test).
        command: Shell command to execute.
        cwd: Working directory.
        timeout: Maximum seconds before the step is killed.

    Returns:
        Dict with CheckResult-compatible fields:
        name, passed, details, duration_ms.
    """
    start = time.monotonic()
    logger.info("verify.%s.start command=%s cwd=%s timeout=%d", name, command, cwd, timeout)

    try:
        args = shlex.split(command)
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0 or (name == "test" and proc.returncode == 5):
            # pytest exit code 5 = no tests collected (treated as pass)
            logger.info("verify.%s.passed elapsed_ms=%d", name, elapsed)
            details = ""
            if proc.returncode == 5:
                details = "No tests collected"
            return {
                "name": f"remote_{name}" if name != "install" else "install",
                "passed": True,
                "details": details,
                "duration_ms": elapsed,
            }

        # Failure
        output = (proc.stdout + proc.stderr)[:4000]
        logger.warning("verify.%s.failed exit=%d elapsed_ms=%d", name, proc.returncode, elapsed)
        return {
            "name": f"remote_{name}" if name != "install" else "install",
            "passed": False,
            "details": output,
            "duration_ms": elapsed,
        }

    except subprocess.TimeoutExpired:
        elapsed = int((time.monotonic() - start) * 1000)
        detail = f"{name} timed out after {timeout}s"
        logger.error("verify.%s.timeout", name)
        return {
            "name": f"remote_{name}" if name != "install" else "install",
            "passed": False,
            "details": detail,
            "duration_ms": elapsed,
        }

    except FileNotFoundError:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error("verify.%s.not_found command=%s", name, command)
        return {
            "name": f"remote_{name}" if name != "install" else "install",
            "passed": False,
            "details": f"Command not found: {command}",
            "duration_ms": elapsed,
        }


def write_result(results: list[dict], result_path: str = RESULT_OUTPUT_PATH) -> None:
    """Write verification results to the output JSON file.

    Output schema::

        {
            "checks": [
                {"name": "install", "passed": true, "details": "", "duration_ms": 1200},
                {"name": "remote_ruff", "passed": true, "details": "", "duration_ms": 500},
                {"name": "remote_pytest", "passed": false, "details": "...", "duration_ms": 3000}
            ],
            "passed": false,
            "total_duration_ms": 4700
        }
    """
    total_ms = sum(r.get("duration_ms", 0) for r in results)
    all_passed = all(r.get("passed", False) for r in results)

    output = {
        "checks": results,
        "passed": all_passed,
        "total_duration_ms": total_ms,
    }

    path = Path(result_path)
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("verify.result_written path=%s passed=%s", result_path, all_passed)


def main(task_path: str = TASK_INPUT_PATH, result_path: str = RESULT_OUTPUT_PATH) -> int:
    """Container entrypoint: read task, run verification steps, write result.

    Returns:
        0 if all checks pass, 1 if any fail.
    """
    logger.info("verify_entrypoint.start")
    total_start = time.monotonic()

    task = read_task(task_path)

    # Extract configuration with defaults
    repo_dir = task.get("repo_dir", REPO_DIR)
    install_command = task.get("install_command", "pip install -e .")
    lint_command = task.get("lint_command", "ruff check .")
    test_command = task.get("test_command", "python -m pytest --tb=short -q")
    install_timeout = task.get("install_timeout", 300)
    lint_timeout = task.get("lint_timeout", 120)
    test_timeout = task.get("test_timeout", 300)

    results: list[dict] = []

    # Step 1: Install dependencies
    install_result = run_step("install", install_command, repo_dir, install_timeout)
    results.append(install_result)

    if not install_result["passed"]:
        logger.warning("verify_entrypoint: install failed, stopping early")
        write_result(results, result_path)
        total_elapsed = int((time.monotonic() - total_start) * 1000)
        logger.info("verify_entrypoint.complete passed=false total_ms=%d", total_elapsed)
        return 1

    # Step 2: Lint
    lint_result = run_step("ruff", lint_command, repo_dir, lint_timeout)
    results.append(lint_result)

    # Step 3: Test
    test_result = run_step("test", test_command, repo_dir, test_timeout)
    results.append(test_result)

    write_result(results, result_path)

    all_passed = all(r["passed"] for r in results)
    total_elapsed = int((time.monotonic() - total_start) * 1000)
    logger.info(
        "verify_entrypoint.complete passed=%s total_ms=%d",
        all_passed,
        total_elapsed,
    )
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
