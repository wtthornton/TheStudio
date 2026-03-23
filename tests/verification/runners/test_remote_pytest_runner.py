"""Tests for remote pytest runner (Story 40.4)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.runners.remote_pytest_runner import run_remote_pytest


def _make_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Create a mock subprocess process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_remote_pytest_exit_0():
    """Exit code 0 means all tests passed."""
    proc = _make_process(returncode=0, stdout=b"5 passed in 2.3s")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace")

    assert result.name == "remote_pytest"
    assert result.passed is True
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_remote_pytest_exit_1():
    """Exit code 1 means some tests failed."""
    proc = _make_process(
        returncode=1,
        stdout=b"FAILED test_foo.py::test_bar\n1 failed, 4 passed in 3.1s",
    )

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace")

    assert result.name == "remote_pytest"
    assert result.passed is False
    assert "FAILED" in result.details


@pytest.mark.asyncio
async def test_remote_pytest_exit_2():
    """Exit code 2 means interrupted/error."""
    proc = _make_process(returncode=2, stderr=b"ERROR: file not found")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace")

    assert result.name == "remote_pytest"
    assert result.passed is False
    assert "ERROR" in result.details


@pytest.mark.asyncio
async def test_remote_pytest_exit_5():
    """Exit code 5 means no tests collected (treated as pass)."""
    proc = _make_process(returncode=5, stdout=b"no tests ran")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace")

    assert result.name == "remote_pytest"
    assert result.passed is True
    assert "No tests collected" in result.details


@pytest.mark.asyncio
async def test_remote_pytest_timeout():
    """Timeout returns a failure result."""

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    proc = MagicMock()
    proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace", timeout=0)

    assert result.name == "remote_pytest"
    assert result.passed is False
    assert "timed out" in result.details


@pytest.mark.asyncio
async def test_remote_pytest_custom_command():
    """Uses custom test command."""
    proc = _make_process(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc
    ) as mock_exec:
        await run_remote_pytest("/tmp/workspace", test_command="python -m pytest -x --cov")

    args = mock_exec.call_args[0]
    assert args[0] == "python"
    assert "-x" in args
    assert "--cov" in args


@pytest.mark.asyncio
async def test_remote_pytest_output_truncated():
    """Output is truncated to 4000 chars."""
    long_output = b"x" * 10000
    proc = _make_process(returncode=1, stdout=long_output)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_pytest("/tmp/workspace")

    assert result.passed is False
    assert len(result.details) <= 4000
