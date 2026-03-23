"""Remote verification orchestrator.

Coordinates the full remote verification pipeline: clone, install, lint, test.
Handles the fallback path (clone main + apply changed files) when the branch
clone fails. Enforces a total wall-clock timeout.

Story 40.6 — Epic 40 Slice 1 MVP.
"""

import asyncio
import logging
import shutil

from src.verification.remote.clone import CloneError, clone_repo
from src.verification.remote.diff_apply import apply_changed_files
from src.verification.remote.install_runner import run_install
from src.verification.runners.base import CheckResult
from src.verification.runners.remote_pytest_runner import run_remote_pytest
from src.verification.runners.remote_ruff_runner import run_remote_ruff

logger = logging.getLogger("thestudio.remote_verify")


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

    Returns:
        List of CheckResult objects from each verification step.
    """
    logger.info(
        "remote_verify.start owner=%s repo=%s branch=%s files=%d",
        owner,
        repo,
        branch,
        len(changed_files),
    )

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
        logger.info(
            "remote_verify.complete owner=%s repo=%s passed=%s",
            owner,
            repo,
            all(r.passed for r in results),
        )
        return results

    except TimeoutError:
        detail = (
            f"Total verification timeout exceeded after {verify_timeout_seconds}s"
        )
        logger.error(
            "remote_verify.total_timeout owner=%s repo=%s timeout=%d",
            owner,
            repo,
            verify_timeout_seconds,
        )
        return [
            CheckResult(
                name="remote_verify",
                passed=False,
                details=detail,
                duration_ms=verify_timeout_seconds * 1000,
            )
        ]


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
    """Inner verification logic, wrapped by total timeout."""
    workspace: str | None = None
    results: list[CheckResult] = []

    try:
        # Step 1: Clone branch (primary path)
        logger.info("remote_verify.clone branch=%s", branch)
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
                "remote_verify.clone.fallback branch=%s error=%s",
                branch,
                str(exc),
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
                    "remote_verify.fallback.failed error=%s",
                    str(fallback_exc),
                )
                return [
                    CheckResult(
                        name="clone",
                        passed=False,
                        details=f"Clone and fallback both failed: {fallback_exc}",
                    )
                ]

        # Step 2: Install dependencies
        logger.info("remote_verify.install workspace=%s", workspace)
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
        logger.info("remote_verify.lint workspace=%s", workspace)
        lint_result = await run_remote_ruff(
            workspace=workspace,
            lint_command=lint_command,
            timeout=lint_timeout,
        )
        results.append(lint_result)

        # Step 4: Run tests
        logger.info("remote_verify.test workspace=%s", workspace)
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
                logger.info("remote_verify.cleanup workspace=%s", workspace)
            except Exception:
                logger.exception("remote_verify.cleanup.failed workspace=%s", workspace)
