"""Tests for the security (bandit) runner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.runners.security_runner import run_security_scan


@pytest.mark.asyncio
async def test_clean_code_passes():
    """Bandit returncode 0 means passed."""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await run_security_scan(["app.py"], "/repo")

    assert result.passed is True
    assert result.name == "security"


@pytest.mark.asyncio
async def test_vulnerable_code_fails():
    """Bandit returncode 1 with output means failed."""
    output = b'{"results": [{"issue_text": "Use of eval"}]}'
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(output, b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await run_security_scan(["app.py"], "/repo")

    assert result.passed is False
    assert result.name == "security"
    assert "eval" in result.details


@pytest.mark.asyncio
async def test_missing_binary_fails_closed():
    """FileNotFoundError when bandit is not installed."""
    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError,
    ):
        result = await run_security_scan(["app.py"], "/repo")

    assert result.passed is False
    assert result.details == "bandit binary not found"


@pytest.mark.asyncio
async def test_timeout_fails_closed():
    """TimeoutError when bandit exceeds the deadline."""
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=TimeoutError)

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", side_effect=TimeoutError):
            result = await run_security_scan(["app.py"], "/repo")

    assert result.passed is False
    assert result.details == "Timeout exceeded"


@pytest.mark.asyncio
async def test_empty_files_returns_pass():
    """Empty file list returns immediate pass."""
    result = await run_security_scan([], "/repo")

    assert result.passed is True
    assert result.details == "No files to check"
