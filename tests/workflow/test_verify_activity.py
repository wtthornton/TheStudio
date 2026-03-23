"""Tests for verify_activity remote verification integration (Story 40.7)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.verification.runners.base import CheckResult
from src.workflow.activities import VerifyInput, VerifyOutput, verify_activity


@pytest.fixture()
def _mock_stage_events():
    """Mock dashboard event emitters to avoid side effects."""
    with (
        patch(
            "src.workflow.activities.emit_stage_enter",
            new_callable=AsyncMock,
        ) if False else patch(
            "src.dashboard.events_publisher.emit_stage_enter",
            new_callable=AsyncMock,
        ),
        patch(
            "src.dashboard.events_publisher.emit_stage_exit",
            new_callable=AsyncMock,
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_verify_disabled_path_no_repo():
    """When repo field is empty, uses existing files_exist behavior."""
    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
    ):
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=["src/foo.py"],
                repo="",
                branch="",
            )
        )

    assert result.passed is True
    assert len(result.checks) == 1
    assert result.checks[0]["name"] == "files_exist"
    assert result.checks[0]["passed"] == "true"


@pytest.mark.asyncio
async def test_verify_disabled_path_no_files():
    """When no files changed, returns files_exist failure."""
    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
    ):
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=[],
                repo="owner/repo",
                branch="thestudio/abc/v1",
            )
        )

    assert result.passed is False
    assert result.loopback_triggered is True


@pytest.mark.asyncio
async def test_verify_remote_all_pass():
    """Remote verification with all checks passing."""
    mock_profile = MagicMock()
    mock_profile.remote_verification_enabled = True
    mock_profile.test_command = "python -m pytest"
    mock_profile.lint_command = "ruff check ."
    mock_profile.install_command = "pip install -e ."
    mock_profile.verify_timeout_seconds = 900
    mock_profile.clone_depth = 1

    check_results = [
        CheckResult(name="install", passed=True, duration_ms=1000),
        CheckResult(name="remote_ruff", passed=True, duration_ms=500),
        CheckResult(name="remote_pytest", passed=True, duration_ms=2000),
    ]

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
        patch("src.db.connection.get_async_session", return_value=mock_session),
        patch(
            "src.repo.repo_profile_crud.get_by_repo",
            new_callable=AsyncMock,
            return_value=mock_profile,
        ),
        patch(
            "src.verification.remote.orchestrator.verify_remote",
            new_callable=AsyncMock,
            return_value=check_results,
        ),
        patch("src.settings.settings") as mock_settings,
    ):
        mock_settings.intake_poll_token = "ghp_test_token"
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=["src/foo.py"],
                repo="owner/repo",
                branch="thestudio/abc/v1",
            )
        )

    assert result.passed is True
    assert len(result.checks) == 3
    assert result.checks[0]["name"] == "install"
    assert result.checks[0]["passed"] == "True"
    assert result.checks[2]["name"] == "remote_pytest"


@pytest.mark.asyncio
async def test_verify_remote_some_fail():
    """Remote verification with some checks failing."""
    mock_profile = MagicMock()
    mock_profile.remote_verification_enabled = True
    mock_profile.test_command = "python -m pytest"
    mock_profile.lint_command = "ruff check ."
    mock_profile.install_command = "pip install -e ."
    mock_profile.verify_timeout_seconds = 900
    mock_profile.clone_depth = 1

    check_results = [
        CheckResult(name="install", passed=True, duration_ms=1000),
        CheckResult(name="remote_ruff", passed=True, duration_ms=500),
        CheckResult(name="remote_pytest", passed=False, details="1 failed", duration_ms=2000),
    ]

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
        patch("src.db.connection.get_async_session", return_value=mock_session),
        patch(
            "src.repo.repo_profile_crud.get_by_repo",
            new_callable=AsyncMock,
            return_value=mock_profile,
        ),
        patch(
            "src.verification.remote.orchestrator.verify_remote",
            new_callable=AsyncMock,
            return_value=check_results,
        ),
        patch("src.settings.settings") as mock_settings,
    ):
        mock_settings.intake_poll_token = "ghp_test_token"
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=["src/foo.py"],
                repo="owner/repo",
                branch="thestudio/abc/v1",
            )
        )

    assert result.passed is False
    assert len(result.checks) == 3
    assert result.checks[2]["passed"] == "False"
    assert result.checks[2]["details"] == "1 failed"


@pytest.mark.asyncio
async def test_verify_remote_disabled_on_profile():
    """When remote_verification_enabled is False, falls back to files_exist."""
    mock_profile = MagicMock()
    mock_profile.remote_verification_enabled = False

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
        patch("src.db.connection.get_async_session", return_value=mock_session),
        patch(
            "src.repo.repo_profile_crud.get_by_repo",
            new_callable=AsyncMock,
            return_value=mock_profile,
        ),
    ):
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=["src/foo.py"],
                repo="owner/repo",
                branch="thestudio/abc/v1",
            )
        )

    assert result.passed is True
    assert result.checks[0]["name"] == "files_exist"


@pytest.mark.asyncio
async def test_verify_remote_error_fallback():
    """When remote verification raises, falls back to files_exist."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.dashboard.events_publisher.emit_stage_enter", new_callable=AsyncMock),
        patch("src.dashboard.events_publisher.emit_stage_exit", new_callable=AsyncMock),
        patch(
            "src.db.connection.get_async_session",
            side_effect=RuntimeError("DB unavailable"),
        ),
    ):
        result = await verify_activity(
            VerifyInput(
                taskpacket_id="abc-123",
                changed_files=["src/foo.py"],
                repo="owner/repo",
                branch="thestudio/abc/v1",
            )
        )

    # Falls back to files_exist when remote verify fails
    assert result.passed is True
    assert result.checks[0]["name"] == "files_exist"
