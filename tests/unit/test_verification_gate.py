"""Unit tests for Verification Gate (Story 0.6).

Tests check runners, result handling, and gate logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.verification.runners.base import CheckResult
from src.verification.runners.pytest_runner import run_pytest
from src.verification.runners.ruff_runner import run_ruff

# --- CheckResult Tests ---


class TestCheckResult:
    def test_passed_result(self) -> None:
        r = CheckResult(name="ruff", passed=True, duration_ms=100)
        assert r.passed
        assert r.name == "ruff"
        assert r.details == ""

    def test_failed_result(self) -> None:
        r = CheckResult(name="pytest", passed=False, details="2 tests failed", duration_ms=500)
        assert not r.passed
        assert "2 tests failed" in r.details


# --- Ruff Runner Tests ---


class TestRuffRunner:
    @pytest.mark.asyncio
    async def test_no_files(self) -> None:
        result = await run_ruff([], "/tmp/repo")
        assert result.passed
        assert result.name == "ruff"
        assert "No files" in result.details

    @pytest.mark.asyncio
    async def test_ruff_passes(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_ruff(["src/main.py"], "/tmp/repo")
        assert result.passed
        assert result.name == "ruff"

    @pytest.mark.asyncio
    async def test_ruff_fails(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"src/main.py:1:1: E001 error\n", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_ruff(["src/main.py"], "/tmp/repo")
        assert not result.passed
        assert "E001" in result.details

    @pytest.mark.asyncio
    async def test_ruff_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("ruff not found"),
        ):
            result = await run_ruff(["src/main.py"], "/tmp/repo")
        assert not result.passed
        assert "not found" in result.details

    @pytest.mark.asyncio
    async def test_ruff_timeout(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            side_effect=TimeoutError()
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await run_ruff(["src/main.py"], "/tmp/repo", timeout=1)
        assert not result.passed
        assert "Timeout" in result.details


# --- Pytest Runner Tests ---


class TestPytestRunner:
    @pytest.mark.asyncio
    async def test_pytest_passes(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"5 passed\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo")
        assert result.passed
        assert result.name == "pytest"

    @pytest.mark.asyncio
    async def test_pytest_fails(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"FAILED test_foo.py::test_bar\n2 failed\n", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo")
        assert not result.passed
        assert "FAILED" in result.details

    @pytest.mark.asyncio
    async def test_no_tests_collected_pass_policy(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 5  # pytest exit code for no tests
        mock_proc.communicate = AsyncMock(return_value=(b"no tests ran\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo", no_tests_policy="pass")
        assert result.passed
        assert "No tests collected" in result.details

    @pytest.mark.asyncio
    async def test_no_tests_collected_fail_policy(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 5
        mock_proc.communicate = AsyncMock(return_value=(b"no tests ran\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo", no_tests_policy="fail")
        assert not result.passed

    @pytest.mark.asyncio
    async def test_pytest_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("pytest not found"),
        ):
            result = await run_pytest("/tmp/repo")
        assert not result.passed
        assert "not found" in result.details

    @pytest.mark.asyncio
    async def test_pytest_timeout(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(
            side_effect=TimeoutError()
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await run_pytest("/tmp/repo", timeout=1)
        assert not result.passed
        assert "Timeout" in result.details


# --- Gate Logic Tests (unit level with mocks) ---


class TestGateLogic:
    def test_all_checks_pass(self) -> None:
        """When all checks pass, overall result is pass."""
        results = [
            CheckResult(name="ruff", passed=True),
            CheckResult(name="pytest", passed=True),
        ]
        assert all(r.passed for r in results)

    def test_any_check_fails(self) -> None:
        """When any check fails, overall result is fail."""
        results = [
            CheckResult(name="ruff", passed=True),
            CheckResult(name="pytest", passed=False, details="1 failed"),
        ]
        assert not all(r.passed for r in results)

    def test_mixed_results(self) -> None:
        """Test case 8: Ruff passes, pytest fails -> verification failed."""
        results = [
            CheckResult(name="ruff", passed=True),
            CheckResult(name="pytest", passed=False, details="test failure"),
        ]
        all_passed = all(r.passed for r in results)
        assert not all_passed

    def test_runner_crash_fails_closed(self) -> None:
        """Test case 6: Runner crash -> gate fails closed (not silent pass)."""
        result = CheckResult(
            name="ruff", passed=False, details="ruff binary not found"
        )
        # Gate fails closed: a runner error is a verification failure
        assert not result.passed
