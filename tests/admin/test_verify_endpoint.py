"""Tests for admin verify endpoint (Story 40.14)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.admin.platform_router import (
    VerifyCheckResult,
    VerifyRequest,
    VerifyResponse,
    admin_trigger_verify,
)
from src.verification.runners.base import CheckResult


class TestVerifyRequestModel:
    """Tests for the VerifyRequest Pydantic model."""

    def test_defaults(self) -> None:
        req = VerifyRequest()
        assert req.branch == ""
        assert req.changed_files == []
        assert req.mode == "subprocess"

    def test_custom_values(self) -> None:
        req = VerifyRequest(
            branch="feat-branch",
            changed_files=["a.py", "b.py"],
            mode="container",
        )
        assert req.branch == "feat-branch"
        assert len(req.changed_files) == 2
        assert req.mode == "container"


class TestVerifyResponseModel:
    """Tests for the VerifyResponse Pydantic model."""

    def test_all_pass(self) -> None:
        resp = VerifyResponse(
            taskpacket_id="tp-123",
            passed=True,
            checks=[
                VerifyCheckResult(name="install", passed=True, details="", duration_ms=100),
                VerifyCheckResult(name="remote_ruff", passed=True, details="", duration_ms=50),
            ],
        )
        assert resp.passed is True
        assert len(resp.checks) == 2
        assert resp.error == ""

    def test_failure_with_error(self) -> None:
        resp = VerifyResponse(
            taskpacket_id="tp-123",
            passed=False,
            error="Docker unavailable",
        )
        assert resp.passed is False
        assert resp.error == "Docker unavailable"
        assert resp.checks == []


class TestVerifyCheckResultModel:
    """Tests for the VerifyCheckResult Pydantic model."""

    def test_remote_check_names(self) -> None:
        for name in ["install", "remote_ruff", "remote_pytest", "container_verify"]:
            check = VerifyCheckResult(name=name, passed=True)
            assert check.name == name
            assert check.duration_ms == 0


def _fake_session_factory(session=None):
    """Create a factory that returns fake async session context managers.

    Since the admin endpoint may call get_async_session() multiple times,
    we return a callable that produces a new context manager each time.
    """
    mock_session = session or AsyncMock()

    class FakeSessionCtx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    def factory():
        return FakeSessionCtx()

    return factory


class TestAdminTriggerVerify:
    """Tests for the admin_trigger_verify endpoint function."""

    @pytest.mark.asyncio
    async def test_invalid_uuid(self) -> None:
        """Invalid UUID returns 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await admin_trigger_verify("not-a-uuid")

        assert exc_info.value.status_code == 400
        assert "Invalid UUID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_taskpacket_not_found(self) -> None:
        """Missing TaskPacket returns 404."""
        from fastapi import HTTPException

        tp_id = str(uuid4())

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await admin_trigger_verify(tp_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_remote_verification_not_enabled(self) -> None:
        """Repo with remote verification disabled returns 400."""
        from fastapi import HTTPException

        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=False,
        )

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await admin_trigger_verify(tp_id)

        assert exc_info.value.status_code == 400
        assert "not enabled" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_successful_verification(self) -> None:
        """Successful verification returns VerifyResponse with checks."""
        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=True,
            test_command="pytest",
            lint_command="ruff check .",
            install_command="pip install -e .",
            verify_timeout_seconds=900,
            clone_depth=1,
        )

        mock_checks = [
            CheckResult(name="install", passed=True, details="", duration_ms=100),
            CheckResult(name="remote_ruff", passed=True, details="", duration_ms=50),
            CheckResult(name="remote_pytest", passed=True, details="", duration_ms=200),
        ]

        mock_settings = MagicMock(intake_poll_token="ghp_test")

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
            patch("src.settings.settings", mock_settings),
            patch(
                "src.verification.remote.orchestrator.verify_remote",
                new_callable=AsyncMock,
                return_value=mock_checks,
            ),
        ):
            body = VerifyRequest(branch="feat-branch")
            response = await admin_trigger_verify(tp_id, body=body)

        assert isinstance(response, VerifyResponse)
        assert response.passed is True
        assert len(response.checks) == 3
        assert response.checks[0].name == "install"
        assert response.error == ""

    @pytest.mark.asyncio
    async def test_verification_failure(self) -> None:
        """Failed verification returns passed=False."""
        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=True,
            test_command="pytest",
            lint_command="ruff check .",
            install_command="pip install -e .",
            verify_timeout_seconds=900,
            clone_depth=1,
        )

        mock_checks = [
            CheckResult(name="install", passed=True, details="", duration_ms=100),
            CheckResult(name="remote_pytest", passed=False, details="2 failed", duration_ms=300),
        ]

        mock_settings = MagicMock(intake_poll_token="ghp_test")

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
            patch("src.settings.settings", mock_settings),
            patch(
                "src.verification.remote.orchestrator.verify_remote",
                new_callable=AsyncMock,
                return_value=mock_checks,
            ),
        ):
            response = await admin_trigger_verify(tp_id)

        assert response.passed is False
        assert len(response.checks) == 2

    @pytest.mark.asyncio
    async def test_verification_exception(self) -> None:
        """Exception during verification returns error in response."""
        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=True,
            test_command="pytest",
            lint_command="ruff check .",
            install_command="pip install -e .",
            verify_timeout_seconds=900,
            clone_depth=1,
        )

        mock_settings = MagicMock(intake_poll_token="ghp_test")

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
            patch("src.settings.settings", mock_settings),
            patch(
                "src.verification.remote.orchestrator.verify_remote",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Clone failed"),
            ),
        ):
            response = await admin_trigger_verify(tp_id)

        assert response.passed is False
        assert "Clone failed" in response.error

    @pytest.mark.asyncio
    async def test_container_mode_request(self) -> None:
        """Container mode parameter is passed through."""
        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=True,
            test_command="pytest",
            lint_command="ruff check .",
            install_command="pip install -e .",
            verify_timeout_seconds=900,
            clone_depth=1,
        )

        mock_checks = [CheckResult(name="install", passed=True, details="", duration_ms=100)]
        mock_settings = MagicMock(intake_poll_token="ghp_test")

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
            patch("src.settings.settings", mock_settings),
            patch(
                "src.verification.remote.orchestrator.verify_remote",
                new_callable=AsyncMock,
                return_value=mock_checks,
            ) as mock_verify,
        ):
            body = VerifyRequest(mode="container", branch="feat")
            await admin_trigger_verify(tp_id, body=body)

        mock_verify.assert_called_once()
        call_kwargs = mock_verify.call_args[1]
        assert call_kwargs["remote_verify_mode"] == "container"

    @pytest.mark.asyncio
    async def test_no_github_token(self) -> None:
        """Missing GitHub token returns 500."""
        from fastapi import HTTPException

        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )
        mock_profile = SimpleNamespace(
            remote_verification_enabled=True,
        )

        mock_settings = MagicMock(intake_poll_token="")

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=mock_profile),
            patch("src.settings.settings", mock_settings),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await admin_trigger_verify(tp_id)

        assert exc_info.value.status_code == 500
        assert "token" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_no_repo_profile(self) -> None:
        """Missing repo profile returns 404."""
        from fastapi import HTTPException

        tp_id = str(uuid4())
        mock_tp = SimpleNamespace(
            repo="owner/repo",
            correlation_id=uuid4(),
        )

        with (
            patch("src.db.connection.get_async_session", side_effect=_fake_session_factory()),
            patch("src.models.taskpacket_crud.get_by_id", new_callable=AsyncMock, return_value=mock_tp),
            patch("src.repo.repo_profile_crud.get_by_repo", new_callable=AsyncMock, return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await admin_trigger_verify(tp_id)

        assert exc_info.value.status_code == 404
        assert "No repo profile" in exc_info.value.detail
