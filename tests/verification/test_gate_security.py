"""Tests for security check dispatch in the verification gate."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.verification.gate import _RUNNERS, _run_check
from src.verification.runners.base import CheckResult


@pytest.mark.asyncio
async def test_run_check_dispatches_to_security():
    """_run_check routes 'security' to run_security_scan."""
    expected = CheckResult(name="security", passed=True)

    with patch(
        "src.verification.gate.run_security_scan",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_scan:
        result = await _run_check("security", ["file.py"], "/repo")

    mock_scan.assert_called_once_with(["file.py"], "/repo")
    assert result.passed is True
    assert result.name == "security"


@pytest.mark.asyncio
async def test_run_check_unknown_returns_failure():
    """Unknown check name returns a failed CheckResult."""
    result = await _run_check("nonexistent", [], "/repo")

    assert result.passed is False
    assert "Unknown check" in result.details


def test_runners_map_includes_security():
    """The _RUNNERS map includes the security entry."""
    assert "security" in _RUNNERS
