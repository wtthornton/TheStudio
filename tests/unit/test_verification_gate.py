"""Unit tests for Verification Gate (Story 0.6).

Tests check runners, result handling, gate logic, and the verify() orchestrator.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.taskpacket import TaskPacketStatus
from src.verification.gate import (
    MAX_LOOPBACKS,
    VerificationResult,
    _run_check,
    verify,
)
from src.verification.runners.base import CheckResult
from src.verification.runners.pytest_runner import run_pytest
from src.verification.runners.ruff_runner import run_ruff

# ---------------------------------------------------------------------------
# CheckResult Tests
# ---------------------------------------------------------------------------


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

    def test_defaults(self) -> None:
        r = CheckResult(name="lint", passed=True)
        assert r.details == ""
        assert r.duration_ms == 0


# ---------------------------------------------------------------------------
# VerificationResult Tests
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_passed_defaults(self) -> None:
        vr = VerificationResult(passed=True, checks=[])
        assert vr.passed
        assert vr.loopback_triggered is False
        assert vr.exhausted is False

    def test_loopback_triggered(self) -> None:
        vr = VerificationResult(passed=False, checks=[], loopback_triggered=True)
        assert not vr.passed
        assert vr.loopback_triggered

    def test_exhausted(self) -> None:
        vr = VerificationResult(passed=False, checks=[], exhausted=True)
        assert vr.exhausted
        assert not vr.loopback_triggered


# ---------------------------------------------------------------------------
# Ruff Runner Tests
# ---------------------------------------------------------------------------


class TestRuffRunner:
    async def test_no_files(self) -> None:
        result = await run_ruff([], "/tmp/repo")
        assert result.passed
        assert result.name == "ruff"
        assert "No files" in result.details

    async def test_ruff_passes(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_ruff(["src/main.py"], "/tmp/repo")
        assert result.passed
        assert result.name == "ruff"

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

    async def test_ruff_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("ruff not found"),
        ):
            result = await run_ruff(["src/main.py"], "/tmp/repo")
        assert not result.passed
        assert "not found" in result.details

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


# ---------------------------------------------------------------------------
# Pytest Runner Tests
# ---------------------------------------------------------------------------


class TestPytestRunner:
    async def test_pytest_passes(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"5 passed\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo")
        assert result.passed
        assert result.name == "pytest"

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

    async def test_no_tests_collected_pass_policy(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 5  # pytest exit code for no tests
        mock_proc.communicate = AsyncMock(return_value=(b"no tests ran\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo", no_tests_policy="pass")
        assert result.passed
        assert "No tests collected" in result.details

    async def test_no_tests_collected_fail_policy(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 5
        mock_proc.communicate = AsyncMock(return_value=(b"no tests ran\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run_pytest("/tmp/repo", no_tests_policy="fail")
        assert not result.passed

    async def test_pytest_not_found(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("pytest not found"),
        ):
            result = await run_pytest("/tmp/repo")
        assert not result.passed
        assert "not found" in result.details

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


# ---------------------------------------------------------------------------
# Gate Logic Tests (unit level with mocks)
# ---------------------------------------------------------------------------


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

    def test_empty_check_list_passes(self) -> None:
        """An empty list of checks evaluates to all-passed (vacuous truth)."""
        results: list[CheckResult] = []
        assert all(r.passed for r in results)


# ---------------------------------------------------------------------------
# _run_check Tests
# ---------------------------------------------------------------------------


class TestRunCheck:
    async def test_run_check_ruff(self) -> None:
        """_run_check dispatches to run_ruff for 'ruff' check."""
        ruff_result = CheckResult(name="ruff", passed=True)
        with patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_result):
            result = await _run_check("ruff", ["file.py"], "/repo")
        assert result.passed
        assert result.name == "ruff"

    async def test_run_check_pytest(self) -> None:
        """_run_check dispatches to run_pytest for 'pytest' check."""
        pytest_result = CheckResult(name="pytest", passed=True)
        with patch("src.verification.gate.run_pytest", new_callable=AsyncMock, return_value=pytest_result):
            result = await _run_check("pytest", ["file.py"], "/repo")
        assert result.passed
        assert result.name == "pytest"

    async def test_run_check_unknown(self) -> None:
        """_run_check returns failed result for unknown check names."""
        result = await _run_check("bandit", ["file.py"], "/repo")
        assert not result.passed
        assert "Unknown check" in result.details
        assert result.name == "bandit"


# ---------------------------------------------------------------------------
# verify() Orchestrator Tests
# ---------------------------------------------------------------------------


def _make_taskpacket(
    loopback_count: int = 0,
    repo: str = "owner/repo",
    correlation_id=None,
):
    """Helper to build a fake TaskPacket namespace for mocking."""
    return SimpleNamespace(
        id=uuid4(),
        repo=repo,
        correlation_id=correlation_id or uuid4(),
        loopback_count=loopback_count,
    )


def _make_profile(required_checks: list[str] | None = None):
    """Helper to build a fake RepoProfile namespace."""
    return SimpleNamespace(required_checks=required_checks or ["ruff", "pytest"])


class TestVerify:
    """Tests for the verify() orchestrator function."""

    async def test_verify_all_checks_pass(self) -> None:
        """When all checks pass, verify returns passed=True and emits passed signal."""
        tp_id = uuid4()
        tp = _make_taskpacket()
        profile = _make_profile(["ruff"])
        session = AsyncMock()

        ruff_ok = CheckResult(name="ruff", passed=True)

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_ok),
            patch("src.verification.gate.update_status", new_callable=AsyncMock) as mock_update,
            patch("src.verification.gate.emit_verification_passed", new_callable=AsyncMock) as mock_emit,
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert result.passed
        assert len(result.checks) == 1
        assert not result.loopback_triggered
        assert not result.exhausted
        mock_update.assert_awaited_once_with(session, tp_id, TaskPacketStatus.VERIFICATION_PASSED)
        mock_emit.assert_awaited_once()

    async def test_verify_taskpacket_not_found(self) -> None:
        """verify raises ValueError when TaskPacket is not found."""
        tp_id = uuid4()
        session = AsyncMock()

        with patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await verify(session, tp_id, ["file.py"], "/repo")

    async def test_verify_failure_triggers_loopback(self) -> None:
        """When checks fail and loopback budget remains, loopback is triggered."""
        tp_id = uuid4()
        tp = _make_taskpacket(loopback_count=0)
        profile = _make_profile(["ruff"])
        session = AsyncMock()

        ruff_fail = CheckResult(name="ruff", passed=False, details="lint error")

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_fail),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=1),
            patch("src.verification.gate.update_status", new_callable=AsyncMock) as mock_update,
            patch("src.verification.gate.emit_verification_failed", new_callable=AsyncMock) as mock_emit,
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert not result.passed
        assert result.loopback_triggered
        assert not result.exhausted
        mock_update.assert_awaited_once_with(session, tp_id, TaskPacketStatus.VERIFICATION_FAILED)
        mock_emit.assert_awaited_once()

    async def test_verify_failure_exhausted(self) -> None:
        """When checks fail and loopback budget is exhausted, result is exhausted."""
        tp_id = uuid4()
        tp = _make_taskpacket(loopback_count=MAX_LOOPBACKS)
        profile = _make_profile(["pytest"])
        session = AsyncMock()

        pytest_fail = CheckResult(name="pytest", passed=False, details="test fail")

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_pytest", new_callable=AsyncMock, return_value=pytest_fail),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=MAX_LOOPBACKS + 1),
            patch("src.verification.gate.update_status", new_callable=AsyncMock) as mock_update,
            patch("src.verification.gate.emit_verification_exhausted", new_callable=AsyncMock) as mock_emit,
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert not result.passed
        assert not result.loopback_triggered
        assert result.exhausted
        mock_update.assert_awaited_once_with(session, tp_id, TaskPacketStatus.FAILED)
        mock_emit.assert_awaited_once()

    async def test_verify_uses_default_checks_when_no_profile(self) -> None:
        """When no repo profile exists, verify uses default checks [ruff, pytest]."""
        tp_id = uuid4()
        tp = _make_taskpacket()
        session = AsyncMock()

        ruff_ok = CheckResult(name="ruff", passed=True)
        pytest_ok = CheckResult(name="pytest", passed=True)

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=None),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_ok) as mock_ruff,
            patch("src.verification.gate.run_pytest", new_callable=AsyncMock, return_value=pytest_ok) as mock_pytest,
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_passed", new_callable=AsyncMock),
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert result.passed
        assert len(result.checks) == 2
        mock_ruff.assert_awaited_once()
        mock_pytest.assert_awaited_once()

    async def test_verify_mixed_results_one_fails(self) -> None:
        """When one check passes and another fails, overall fails."""
        tp_id = uuid4()
        tp = _make_taskpacket()
        profile = _make_profile(["ruff", "pytest"])
        session = AsyncMock()

        ruff_ok = CheckResult(name="ruff", passed=True)
        pytest_fail = CheckResult(name="pytest", passed=False, details="1 failed")

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_ok),
            patch("src.verification.gate.run_pytest", new_callable=AsyncMock, return_value=pytest_fail),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=1),
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_failed", new_callable=AsyncMock),
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert not result.passed
        assert len(result.checks) == 2
        passed_names = [c.name for c in result.checks if c.passed]
        failed_names = [c.name for c in result.checks if not c.passed]
        assert "ruff" in passed_names
        assert "pytest" in failed_names

    async def test_verify_loopback_boundary_at_max(self) -> None:
        """When loopback count equals MAX_LOOPBACKS, loopback is still triggered (count <= MAX)."""
        tp_id = uuid4()
        tp = _make_taskpacket(loopback_count=MAX_LOOPBACKS - 1)
        profile = _make_profile(["ruff"])
        session = AsyncMock()

        ruff_fail = CheckResult(name="ruff", passed=False, details="error")

        # increment_loopback returns MAX_LOOPBACKS (equal, not greater)
        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_fail),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=MAX_LOOPBACKS),
            patch("src.verification.gate.update_status", new_callable=AsyncMock) as mock_update,
            patch("src.verification.gate.emit_verification_failed", new_callable=AsyncMock) as mock_emit,
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        # current_count == MAX_LOOPBACKS is NOT > MAX_LOOPBACKS, so loopback is triggered
        assert not result.passed
        assert result.loopback_triggered
        assert not result.exhausted
        mock_update.assert_awaited_once_with(session, tp_id, TaskPacketStatus.VERIFICATION_FAILED)

    async def test_verify_repo_split(self) -> None:
        """verify correctly splits owner/repo from the TaskPacket."""
        tp_id = uuid4()
        tp = _make_taskpacket(repo="myorg/myrepo")
        session = AsyncMock()

        ruff_ok = CheckResult(name="ruff", passed=True)

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=_make_profile(["ruff"])) as mock_get_repo,
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_ok),
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_passed", new_callable=AsyncMock),
        ):
            await verify(session, tp_id, ["file.py"], "/repo")

        mock_get_repo.assert_awaited_once_with(session, "myorg", "myrepo")

    async def test_verify_unknown_check_in_profile(self) -> None:
        """If profile includes unknown check, it fails closed via _run_check."""
        tp_id = uuid4()
        tp = _make_taskpacket()
        profile = _make_profile(["bandit"])
        session = AsyncMock()

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=1),
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_failed", new_callable=AsyncMock),
        ):
            result = await verify(session, tp_id, ["file.py"], "/repo")

        assert not result.passed
        assert result.checks[0].name == "bandit"
        assert "Unknown check" in result.checks[0].details

    async def test_verify_signal_args_on_pass(self) -> None:
        """Verify that emit_verification_passed receives correct arguments."""
        tp_id = uuid4()
        correlation_id = uuid4()
        tp = _make_taskpacket(correlation_id=correlation_id)
        profile = _make_profile(["ruff"])
        session = AsyncMock()

        ruff_ok = CheckResult(name="ruff", passed=True)

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_ok),
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_passed", new_callable=AsyncMock) as mock_emit,
        ):
            await verify(session, tp_id, ["file.py"], "/repo")

        mock_emit.assert_awaited_once_with(
            tp_id, correlation_id, tp.loopback_count, [ruff_ok]
        )

    async def test_verify_signal_args_on_exhausted(self) -> None:
        """Verify that emit_verification_exhausted receives correct arguments."""
        tp_id = uuid4()
        correlation_id = uuid4()
        tp = _make_taskpacket(correlation_id=correlation_id)
        profile = _make_profile(["ruff"])
        session = AsyncMock()

        ruff_fail = CheckResult(name="ruff", passed=False, details="err")
        current_count = MAX_LOOPBACKS + 1

        with (
            patch("src.verification.gate.get_by_id", new_callable=AsyncMock, return_value=tp),
            patch("src.verification.gate.get_by_repo", new_callable=AsyncMock, return_value=profile),
            patch("src.verification.gate.run_ruff", new_callable=AsyncMock, return_value=ruff_fail),
            patch("src.verification.gate.increment_loopback", new_callable=AsyncMock, return_value=current_count),
            patch("src.verification.gate.update_status", new_callable=AsyncMock),
            patch("src.verification.gate.emit_verification_exhausted", new_callable=AsyncMock) as mock_emit,
        ):
            await verify(session, tp_id, ["file.py"], "/repo")

        mock_emit.assert_awaited_once_with(
            tp_id, correlation_id, current_count, [ruff_fail]
        )


# ---------------------------------------------------------------------------
# Constants Tests
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_loopbacks_value(self) -> None:
        assert MAX_LOOPBACKS == 2

    def test_max_loopbacks_is_positive(self) -> None:
        assert MAX_LOOPBACKS > 0
