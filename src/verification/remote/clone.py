"""Repo clone utility for remote verification.

Shallow-clones a GitHub repository branch to a temporary directory using
asyncio subprocess. Used by the remote verification orchestrator to obtain
a workspace for running the target repo's test and lint suites.

Story 40.1 — Epic 40 Slice 1 MVP.
"""

import asyncio
import logging
import tempfile
import time

logger = logging.getLogger("thestudio.remote_verify")


class CloneError(Exception):
    """Raised when git clone fails (network, auth, branch-not-found)."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


async def clone_repo(
    owner: str,
    repo: str,
    branch: str,
    token: str,
    depth: int = 1,
    timeout: int = 60,
) -> str:
    """Shallow-clone a GitHub repository branch to a temp directory.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        branch: Branch to clone.
        token: GitHub token for authentication (PAT or installation token).
        depth: Shallow clone depth (default 1).
        timeout: Maximum seconds for the clone operation.

    Returns:
        Absolute path to the cloned workspace directory.
        Caller is responsible for cleanup (e.g. shutil.rmtree).

    Raises:
        CloneError: On network failure, auth failure, or branch-not-found.
    """
    # Optional OTel tracing — graceful skip if not available
    tracer = None
    span = None
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("thestudio.remote_verify")
    except ImportError:
        pass

    if tracer is not None:
        span = tracer.start_span("clone_repo")
        span.set_attribute("repo", f"{owner}/{repo}")
        span.set_attribute("branch", branch)
        span.set_attribute("depth", depth)

    start = time.monotonic()
    workspace = tempfile.mkdtemp(prefix="thestudio_clone_")
    clone_url = f"https://{token}@github.com/{owner}/{repo}.git"

    logger.info(
        "remote_verify.clone owner=%s repo=%s branch=%s depth=%d",
        owner,
        repo,
        branch,
        depth,
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            str(depth),
            "--branch",
            branch,
            "--single-branch",
            clone_url,
            workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stderr_text = stderr.decode(errors="replace")

        if proc.returncode != 0:
            # Clean up the workspace on failure
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

            error_msg = f"git clone failed with exit code {proc.returncode}"
            if "could not read Username" in stderr_text or "Authentication" in stderr_text:
                error_msg = f"Authentication failed for {owner}/{repo}"
            elif "Remote branch" in stderr_text and "not found" in stderr_text:
                error_msg = f"Branch '{branch}' not found in {owner}/{repo}"
            elif "Repository not found" in stderr_text:
                error_msg = f"Repository {owner}/{repo} not found"

            logger.error(
                "remote_verify.clone.failed owner=%s repo=%s branch=%s error=%s",
                owner,
                repo,
                branch,
                error_msg,
            )
            raise CloneError(
                error_msg, returncode=proc.returncode, stderr=stderr_text[:2000]
            )

        logger.info(
            "remote_verify.clone.success owner=%s repo=%s branch=%s elapsed_ms=%d",
            owner,
            repo,
            branch,
            elapsed_ms,
        )
        return workspace

    except TimeoutError:
        # Clean up on timeout
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        error_msg = f"Clone timed out after {timeout}s for {owner}/{repo}"
        logger.error("remote_verify.clone.timeout owner=%s repo=%s", owner, repo)
        raise CloneError(error_msg, returncode=-1, stderr="timeout") from None

    finally:
        if span is not None:
            span.end()
