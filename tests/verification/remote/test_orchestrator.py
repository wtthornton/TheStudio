"""Tests for remote verification orchestrator (Story 40.6)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.verification.remote.clone import CloneError
from src.verification.remote.orchestrator import verify_remote
from src.verification.runners.base import CheckResult


def _cr(name: str, passed: bool, details: str = "", duration_ms: int = 100) -> CheckResult:
    """Shorthand for creating a CheckResult."""
    return CheckResult(name=name, passed=passed, details=details, duration_ms=duration_ms)


@pytest.mark.asyncio
async def test_happy_path_all_pass():
    """All steps pass: install, lint, test."""
    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator.run_install",
            new_callable=AsyncMock,
            return_value=_cr("install", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_ruff",
            new_callable=AsyncMock,
            return_value=_cr("remote_ruff", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_pytest",
            new_callable=AsyncMock,
            return_value=_cr("remote_pytest", True),
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
        )

    assert len(results) == 3
    assert all(r.passed for r in results)
    assert results[0].name == "install"
    assert results[1].name == "remote_ruff"
    assert results[2].name == "remote_pytest"


@pytest.mark.asyncio
async def test_install_failure_stops_early():
    """When install fails, lint and test are skipped."""
    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator.run_install",
            new_callable=AsyncMock,
            return_value=_cr("install", False, "pip failed"),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_ruff",
            new_callable=AsyncMock,
        ) as mock_lint,
        patch(
            "src.verification.remote.orchestrator.run_remote_pytest",
            new_callable=AsyncMock,
        ) as mock_test,
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
        )

    assert len(results) == 1
    assert results[0].name == "install"
    assert results[0].passed is False
    mock_lint.assert_not_called()
    mock_test.assert_not_called()


@pytest.mark.asyncio
async def test_test_failure():
    """Install and lint pass, test fails."""
    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator.run_install",
            new_callable=AsyncMock,
            return_value=_cr("install", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_ruff",
            new_callable=AsyncMock,
            return_value=_cr("remote_ruff", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_pytest",
            new_callable=AsyncMock,
            return_value=_cr("remote_pytest", False, "1 failed"),
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
        )

    assert len(results) == 3
    assert results[0].passed is True   # install
    assert results[1].passed is True   # lint
    assert results[2].passed is False  # test


@pytest.mark.asyncio
async def test_total_timeout():
    """Total timeout returns a single failure result."""

    async def hang(*args, **kwargs) -> str:
        await asyncio.sleep(100)
        return "/tmp/ws"

    with (
        patch("src.verification.remote.orchestrator.clone_repo", side_effect=hang),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
            verify_timeout_seconds=0,
        )

    assert len(results) == 1
    assert results[0].name == "remote_verify"
    assert results[0].passed is False
    assert "timeout" in results[0].details.lower()


@pytest.mark.asyncio
async def test_clone_failure_triggers_fallback():
    """When branch clone fails, falls back to main + apply_changed_files."""
    call_count = {"clone": 0}

    async def mock_clone(owner, repo, branch, token, depth=1, timeout=60) -> str:
        call_count["clone"] += 1
        if branch == "feat-branch":
            raise CloneError("Branch not found")
        return "/tmp/ws_main"

    with (
        patch("src.verification.remote.orchestrator.clone_repo", side_effect=mock_clone),
        patch(
            "src.verification.remote.orchestrator.apply_changed_files",
            new_callable=AsyncMock,
            return_value=["/tmp/ws_main/a.py"],
        ) as mock_apply,
        patch(
            "src.verification.remote.orchestrator.run_install",
            new_callable=AsyncMock,
            return_value=_cr("install", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_ruff",
            new_callable=AsyncMock,
            return_value=_cr("remote_ruff", True),
        ),
        patch(
            "src.verification.remote.orchestrator.run_remote_pytest",
            new_callable=AsyncMock,
            return_value=_cr("remote_pytest", True),
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat-branch", token="t",
            changed_files=["a.py"],
        )

    assert call_count["clone"] == 2  # branch + main
    mock_apply.assert_called_once()
    assert len(results) == 3
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_fallback_failure_returns_error():
    """When both branch and fallback clone fail, returns error."""

    async def mock_clone(owner, repo, branch, token, depth=1, timeout=60) -> str:
        raise CloneError(f"Clone failed for {branch}")

    with (
        patch("src.verification.remote.orchestrator.clone_repo", side_effect=mock_clone),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
        )

    assert len(results) == 1
    assert results[0].name == "clone"
    assert results[0].passed is False
    assert "failed" in results[0].details.lower()
