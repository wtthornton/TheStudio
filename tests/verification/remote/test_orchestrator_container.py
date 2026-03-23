"""Tests for orchestrator container mode (Story 40.11)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.remote.clone import CloneError
from src.verification.remote.orchestrator import verify_remote
from src.verification.runners.base import CheckResult


def _cr(name: str, passed: bool, details: str = "", duration_ms: int = 100) -> CheckResult:
    """Shorthand for creating a CheckResult."""
    return CheckResult(name=name, passed=passed, details=details, duration_ms=duration_ms)


@pytest.mark.asyncio
async def test_subprocess_mode_is_default():
    """Default mode is 'subprocess', existing behavior unchanged."""
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


@pytest.mark.asyncio
async def test_subprocess_mode_explicit():
    """Explicitly setting mode='subprocess' works."""
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
            remote_verify_mode="subprocess",
        )

    assert len(results) == 3
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_container_mode_happy_path():
    """Container mode: clone on host, run in container, return results."""
    container_results = [
        _cr("install", True),
        _cr("remote_ruff", True),
        _cr("remote_pytest", True),
    ]

    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator._is_docker_available",
            return_value=True,
        ),
        patch(
            "src.verification.remote.container_runner.run_verification_container",
            return_value=container_results,
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
            remote_verify_mode="container",
            taskpacket_id="tp-123",
        )

    assert len(results) == 3
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_container_mode_docker_unavailable_fallback():
    """When Docker is unavailable, container mode falls back to subprocess."""
    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator._is_docker_available",
            return_value=False,
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
            remote_verify_mode="container",
        )

    assert len(results) == 3
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_container_mode_clone_failure_fallback():
    """Container mode: clone failure triggers main branch fallback."""
    call_count = {"clone": 0}

    async def mock_clone(owner, repo, branch, token, depth=1, timeout=60) -> str:
        call_count["clone"] += 1
        if branch == "feat-branch":
            raise CloneError("Branch not found")
        return "/tmp/ws_main"

    container_results = [
        _cr("install", True),
        _cr("remote_ruff", True),
        _cr("remote_pytest", True),
    ]

    with (
        patch("src.verification.remote.orchestrator.clone_repo", side_effect=mock_clone),
        patch(
            "src.verification.remote.orchestrator.apply_changed_files",
            new_callable=AsyncMock,
        ),
        patch(
            "src.verification.remote.orchestrator._is_docker_available",
            return_value=True,
        ),
        patch(
            "src.verification.remote.container_runner.run_verification_container",
            return_value=container_results,
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat-branch", token="t",
            changed_files=["a.py"],
            remote_verify_mode="container",
        )

    assert call_count["clone"] == 2  # branch + main
    assert len(results) == 3


@pytest.mark.asyncio
async def test_container_mode_clone_and_fallback_both_fail():
    """When both clone attempts fail in container mode, returns error."""

    async def mock_clone(owner, repo, branch, token, depth=1, timeout=60) -> str:
        raise CloneError(f"Clone failed for {branch}")

    with (
        patch("src.verification.remote.orchestrator.clone_repo", side_effect=mock_clone),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
            remote_verify_mode="container",
        )

    assert len(results) == 1
    assert results[0].name == "clone"
    assert results[0].passed is False


@pytest.mark.asyncio
async def test_container_mode_test_failure():
    """Container mode: test failure is propagated."""
    container_results = [
        _cr("install", True),
        _cr("remote_ruff", True),
        _cr("remote_pytest", False, "2 tests failed"),
    ]

    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator._is_docker_available",
            return_value=True,
        ),
        patch(
            "src.verification.remote.container_runner.run_verification_container",
            return_value=container_results,
        ),
        patch("shutil.rmtree"),
    ):
        results = await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
            remote_verify_mode="container",
        )

    assert len(results) == 3
    assert results[2].passed is False
    assert "2 tests failed" in results[2].details


@pytest.mark.asyncio
async def test_subprocess_mode_total_timeout():
    """Subprocess mode: total timeout still returns failure."""

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
            remote_verify_mode="subprocess",
        )

    assert len(results) == 1
    assert results[0].name == "remote_verify"
    assert results[0].passed is False


@pytest.mark.asyncio
async def test_container_mode_workspace_cleaned_up():
    """Container mode: workspace is cleaned up even on success."""
    container_results = [_cr("install", True)]
    cleanup_called = {"called": False}

    original_rmtree = None

    def mock_rmtree(path, *args, **kwargs):
        cleanup_called["called"] = True

    with (
        patch(
            "src.verification.remote.orchestrator.clone_repo",
            new_callable=AsyncMock,
            return_value="/tmp/ws",
        ),
        patch(
            "src.verification.remote.orchestrator._is_docker_available",
            return_value=True,
        ),
        patch(
            "src.verification.remote.container_runner.run_verification_container",
            return_value=container_results,
        ),
        patch("src.verification.remote.orchestrator.shutil.rmtree", side_effect=mock_rmtree),
    ):
        await verify_remote(
            owner="o", repo="r", branch="feat", token="t",
            changed_files=["a.py"],
            remote_verify_mode="container",
        )

    assert cleanup_called["called"] is True
