"""Diff application fallback for remote verification.

When a branch clone fails (e.g. the branch doesn't exist yet on the remote),
this module retrieves changed files from the GitHub Contents API and writes
them into an existing workspace (cloned from the default branch).

Story 40.2 — Epic 40 Slice 1 MVP.
"""

import base64
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("thestudio.remote_verify")


class PathTraversalError(Exception):
    """Raised when a file path attempts directory traversal."""


class DiffApplyError(Exception):
    """Raised when diff application fails."""


def _validate_path(file_path: str) -> None:
    """Reject path traversal attempts.

    Raises:
        PathTraversalError: If the path contains traversal patterns.
    """
    if "\x00" in file_path:
        raise PathTraversalError(f"Null byte in path: {file_path!r}")
    if file_path.startswith("/"):
        raise PathTraversalError(f"Absolute path rejected: {file_path}")
    if ".." in file_path.split("/"):
        raise PathTraversalError(f"Path traversal rejected: {file_path}")
    # Also check backslash-separated segments on Windows
    if ".." in file_path.split("\\"):
        raise PathTraversalError(f"Path traversal rejected: {file_path}")


async def apply_changed_files(
    workspace: str,
    changed_files: list[str],
    owner: str,
    repo: str,
    branch: str,
    github_token: str,
) -> list[str]:
    """Retrieve changed files from GitHub Contents API and write to workspace.

    Args:
        workspace: Root directory of the cloned repository.
        changed_files: List of relative file paths to retrieve.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        branch: Branch/ref to retrieve files from.
        github_token: GitHub token for API authentication.

    Returns:
        List of absolute paths of successfully applied files.

    Raises:
        PathTraversalError: If any path attempts directory traversal.
        DiffApplyError: If file retrieval or write fails.
    """
    # Validate all paths upfront before any writes
    for file_path in changed_files:
        _validate_path(file_path)

    applied_files: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for file_path in changed_files:
                url = (
                    f"https://api.github.com/repos/{owner}/{repo}"
                    f"/contents/{file_path}?ref={branch}"
                )
                headers = {
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }

                logger.info(
                    "remote_verify.diff_apply.fetch path=%s ref=%s",
                    file_path,
                    branch,
                )

                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    # File was deleted in the branch — skip it
                    logger.info(
                        "remote_verify.diff_apply.deleted path=%s",
                        file_path,
                    )
                    continue

                if response.status_code != 200:
                    raise DiffApplyError(
                        f"GitHub API returned {response.status_code} for {file_path}: "
                        f"{response.text[:500]}"
                    )

                data = response.json()
                content_b64 = data.get("content", "")
                content_bytes = base64.b64decode(content_b64)

                # Write file to workspace
                dest = os.path.join(workspace, file_path)
                dest_dir = os.path.dirname(dest)
                os.makedirs(dest_dir, exist_ok=True)
                Path(dest).write_bytes(content_bytes)

                applied_files.append(dest)
                logger.info(
                    "remote_verify.diff_apply.written path=%s size=%d",
                    file_path,
                    len(content_bytes),
                )

    except (PathTraversalError, DiffApplyError):
        # Re-raise known errors after rollback
        _rollback(applied_files)
        raise
    except Exception as exc:
        # Rollback on any unexpected failure
        _rollback(applied_files)
        raise DiffApplyError(f"Failed to apply changed files: {exc}") from exc

    return applied_files


def _rollback(applied_files: list[str]) -> None:
    """Remove all previously written files on failure."""
    for fpath in applied_files:
        try:
            os.remove(fpath)
            logger.info("remote_verify.diff_apply.rollback path=%s", fpath)
        except OSError:
            pass
