"""Tests for remote ruff lint runner (Story 40.5)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.runners.remote_ruff_runner import run_remote_ruff


def _make_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Create a mock subprocess process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_remote_ruff_pass():
    """Lint passes with exit code 0."""
    proc = _make_process(returncode=0)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_ruff("/tmp/workspace")

    assert result.name == "remote_ruff"
    assert result.passed is True
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_remote_ruff_fail():
    """Lint fails with nonzero exit and captures output."""
    proc = _make_process(
        returncode=1,
        stdout=b"src/foo.py:10:1: E501 Line too long (120 > 100)\nFound 3 errors.",
    )

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_ruff("/tmp/workspace")

    assert result.name == "remote_ruff"
    assert result.passed is False
    assert "E501" in result.details


@pytest.mark.asyncio
async def test_remote_ruff_timeout():
    """Lint times out and returns failure."""

    async def slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    proc = MagicMock()
    proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_ruff("/tmp/workspace", timeout=0)

    assert result.name == "remote_ruff"
    assert result.passed is False
    assert "timed out" in result.details


@pytest.mark.asyncio
async def test_remote_ruff_custom_command():
    """Uses custom lint command."""
    proc = _make_process(returncode=0)

    with patch(
        "asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc
    ) as mock_exec:
        await run_remote_ruff("/tmp/workspace", lint_command="flake8 src/")

    args = mock_exec.call_args[0]
    assert args[0] == "flake8"
    assert "src/" in args


@pytest.mark.asyncio
async def test_remote_ruff_output_truncated():
    """Output is truncated to 4000 chars."""
    long_output = b"lint error\n" * 1000
    proc = _make_process(returncode=1, stdout=long_output)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await run_remote_ruff("/tmp/workspace")

    assert result.passed is False
    assert len(result.details) <= 4000
