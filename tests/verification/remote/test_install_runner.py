"""Tests for dependency installer runner (Story 40.3)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.remote.install_runner import run_install


def _make_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Create a mock subprocess process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_install_success():
    """Install succeeds with exit code 0."""
    proc = _make_process(returncode=0, stdout=b"Successfully installed foo-1.0")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_install("/tmp/workspace")

    assert result.name == "install"
    assert result.passed is True
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_install_failure():
    """Install fails with nonzero exit code and captures stderr."""
    proc = _make_process(
        returncode=1,
        stderr=b"ERROR: Could not find a version that satisfies the requirement foo",
    )

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_install("/tmp/workspace")

    assert result.name == "install"
    assert result.passed is False
    assert "Could not find a version" in result.details


@pytest.mark.asyncio
async def test_install_timeout():
    """Install times out and returns appropriate error."""

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    proc = MagicMock()
    proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_install("/tmp/workspace", timeout=0)

    assert result.name == "install"
    assert result.passed is False
    assert "timed out" in result.details


@pytest.mark.asyncio
async def test_install_custom_command():
    """Install uses the custom command."""
    proc = _make_process(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc
    ) as mock_exec:
        await run_install("/tmp/workspace", install_command="npm install")

    args = mock_exec.call_args[0]
    assert args[0] == "npm"
    assert args[1] == "install"


@pytest.mark.asyncio
async def test_install_stderr_truncated():
    """Install truncates stderr to 2000 chars."""
    long_stderr = b"x" * 5000
    proc = _make_process(returncode=1, stderr=long_stderr)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_install("/tmp/workspace")

    assert result.passed is False
    assert len(result.details) <= 2000
