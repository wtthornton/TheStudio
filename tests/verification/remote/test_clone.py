"""Tests for repo clone utility (Story 40.1)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.remote.clone import CloneError, clone_repo


def _make_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Create a mock subprocess process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_clone_repo_success():
    """Clone succeeds with exit code 0 and returns workspace path."""
    proc = _make_process(returncode=0)

    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc),
        patch("tempfile.mkdtemp", return_value="/tmp/thestudio_clone_abc123"),
    ):
        result = await clone_repo("owner", "repo", "main", "ghp_token123")

    assert result == "/tmp/thestudio_clone_abc123"


@pytest.mark.asyncio
async def test_clone_repo_auth_failure():
    """Clone raises CloneError on authentication failure."""
    proc = _make_process(
        returncode=128,
        stderr=b"fatal: could not read Username for 'https://github.com': terminal prompts disabled",
    )

    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc),
        patch("tempfile.mkdtemp", return_value="/tmp/thestudio_clone_abc123"),
        patch("shutil.rmtree"),
    ):
        with pytest.raises(CloneError, match="Authentication failed"):
            await clone_repo("owner", "repo", "main", "bad_token")


@pytest.mark.asyncio
async def test_clone_repo_branch_not_found():
    """Clone raises CloneError when branch doesn't exist."""
    proc = _make_process(
        returncode=128,
        stderr=b"fatal: Remote branch 'nonexistent' not found in upstream origin",
    )

    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc),
        patch("tempfile.mkdtemp", return_value="/tmp/thestudio_clone_abc123"),
        patch("shutil.rmtree"),
    ):
        with pytest.raises(CloneError, match="Branch 'nonexistent' not found"):
            await clone_repo("owner", "repo", "nonexistent", "ghp_token123")


@pytest.mark.asyncio
async def test_clone_repo_nonzero_exit():
    """Clone raises CloneError on generic nonzero exit."""
    proc = _make_process(returncode=1, stderr=b"some git error")

    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc),
        patch("tempfile.mkdtemp", return_value="/tmp/thestudio_clone_abc123"),
        patch("shutil.rmtree"),
    ):
        with pytest.raises(CloneError, match="git clone failed"):
            await clone_repo("owner", "repo", "main", "ghp_token123")


@pytest.mark.asyncio
async def test_clone_repo_timeout():
    """Clone raises CloneError when subprocess times out."""

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    proc = MagicMock()
    proc.returncode = None
    proc.communicate = slow_communicate

    with (
        patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc),
        patch("tempfile.mkdtemp", return_value="/tmp/thestudio_clone_abc123"),
        patch("shutil.rmtree"),
    ):
        with pytest.raises(CloneError, match="timed out"):
            await clone_repo("owner", "repo", "main", "ghp_token123", timeout=0)


@pytest.mark.asyncio
async def test_clone_repo_uses_correct_git_args():
    """Clone passes correct arguments to git."""
    proc = _make_process(returncode=0)

    with (
        patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc
        ) as mock_exec,
        patch("tempfile.mkdtemp", return_value="/tmp/ws"),
    ):
        await clone_repo("myorg", "myrepo", "feature-branch", "tok123", depth=5)

    args = mock_exec.call_args[0]
    assert args[0] == "git"
    assert args[1] == "clone"
    assert "--depth" in args
    assert "5" in args
    assert "--branch" in args
    assert "feature-branch" in args
    assert "--single-branch" in args
    assert "https://tok123@github.com/myorg/myrepo.git" in args
    assert "/tmp/ws" in args
