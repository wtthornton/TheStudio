"""Tests for container verification runner (Story 40.10)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.verification.remote.container_runner import (
    _parse_result,
    run_verification_container,
)
from src.verification.runners.base import CheckResult


class TestParseResult:
    """Tests for _parse_result()."""

    def test_parses_full_result(self) -> None:
        """Parses a complete result with multiple checks."""
        raw = {
            "checks": [
                {"name": "install", "passed": True, "details": "", "duration_ms": 100},
                {"name": "remote_ruff", "passed": True, "details": "", "duration_ms": 50},
                {"name": "remote_pytest", "passed": False, "details": "1 failed", "duration_ms": 200},
            ],
            "passed": False,
            "total_duration_ms": 350,
        }

        checks = _parse_result(raw)

        assert len(checks) == 3
        assert checks[0].name == "install"
        assert checks[0].passed is True
        assert checks[1].name == "remote_ruff"
        assert checks[2].name == "remote_pytest"
        assert checks[2].passed is False
        assert checks[2].details == "1 failed"

    def test_fallback_when_no_checks(self) -> None:
        """Returns single fallback result when no checks in result."""
        raw = {"passed": True, "total_duration_ms": 500}

        checks = _parse_result(raw)

        assert len(checks) == 1
        assert checks[0].name == "container_verify"
        assert checks[0].passed is True

    def test_handles_empty_dict(self) -> None:
        """Handles empty result dict gracefully."""
        checks = _parse_result({})

        assert len(checks) == 1
        assert checks[0].passed is False

    def test_handles_missing_fields(self) -> None:
        """Handles check entries with missing fields."""
        raw = {
            "checks": [
                {"name": "install"},
                {},
            ],
        }

        checks = _parse_result(raw)

        assert len(checks) == 2
        assert checks[0].name == "install"
        assert checks[0].passed is False  # default
        assert checks[1].name == "unknown"


class TestRunVerificationContainer:
    """Tests for run_verification_container()."""

    @patch("src.verification.remote.container_runner.docker")
    def test_happy_path(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """Successful container run returns check results."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        # Mock Docker client
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.short_id = "abc123"
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"verification done"
        mock_client.containers.create.return_value = mock_container

        # Write result.json to exchange dir
        result_data = {
            "checks": [
                {"name": "install", "passed": True, "details": "", "duration_ms": 100},
                {"name": "remote_ruff", "passed": True, "details": "", "duration_ms": 50},
                {"name": "remote_pytest", "passed": True, "details": "", "duration_ms": 200},
            ],
            "passed": True,
            "total_duration_ms": 350,
        }

        # We need to mock tempfile.mkdtemp and inject result.json
        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            # Simulate the container writing result.json
            def fake_wait(**kwargs):
                result_path = Path(exchange_dir) / "result.json"
                result_path.write_text(json.dumps(result_data))
                return {"StatusCode": 0}

            mock_container.wait.side_effect = fake_wait

            checks = run_verification_container(
                workspace,
                taskpacket_id="tp-123",
                correlation_id="corr-456",
            )

        assert len(checks) == 3
        assert all(c.passed for c in checks)
        mock_container.start.assert_called_once()
        mock_container.remove.assert_called_once_with(force=True)

    @patch("src.verification.remote.container_runner.docker")
    def test_container_timeout(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """Container timeout returns error CheckResult."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.short_id = "timeout123"
        mock_container.wait.side_effect = Exception("Connection timed out")
        mock_client.containers.create.return_value = mock_container

        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            checks = run_verification_container(
                workspace,
                container_timeout=1,
            )

        assert len(checks) == 1
        assert checks[0].passed is False
        assert "timed out" in checks[0].details.lower() or "timeout" in checks[0].details.lower()

    @patch("src.verification.remote.container_runner.docker")
    def test_no_result_file(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """No result.json returns error CheckResult."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.short_id = "noresult"
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"error output"
        mock_client.containers.create.return_value = mock_container

        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            checks = run_verification_container(workspace)

        assert len(checks) == 1
        assert checks[0].passed is False
        assert "no result file" in checks[0].details.lower()

    @patch("src.verification.remote.container_runner.docker")
    def test_docker_error(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """Docker API error returns error CheckResult."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        mock_docker.from_env.side_effect = Exception("Docker not available")

        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            checks = run_verification_container(workspace)

        assert len(checks) == 1
        assert checks[0].passed is False
        assert "Docker not available" in checks[0].details

    @patch("src.verification.remote.container_runner.docker")
    def test_task_json_written(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """Task JSON is written with correct config before container launch."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.short_id = "check123"
        mock_container.logs.return_value = b""
        mock_client.containers.create.return_value = mock_container

        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        result_data = {"checks": [{"name": "install", "passed": True, "details": "", "duration_ms": 10}], "passed": True}

        def fake_wait(**kwargs):
            (Path(exchange_dir) / "result.json").write_text(json.dumps(result_data))
            return {"StatusCode": 0}

        mock_container.wait.side_effect = fake_wait

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            run_verification_container(
                workspace,
                install_command="pip install .",
                lint_command="ruff check src/",
                test_command="pytest -x",
            )

        task_path = Path(exchange_dir) / "task.json"
        assert task_path.exists()
        task = json.loads(task_path.read_text())
        assert task["install_command"] == "pip install ."
        assert task["lint_command"] == "ruff check src/"
        assert task["test_command"] == "pytest -x"
        assert task["repo_dir"] == "/workspace/repo"

    @patch("src.verification.remote.container_runner.docker")
    def test_container_network_none(self, mock_docker: MagicMock, tmp_path: Path) -> None:
        """Container is created with no network access."""
        workspace = str(tmp_path / "repo")
        Path(workspace).mkdir()

        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.short_id = "net123"
        mock_container.logs.return_value = b""
        mock_client.containers.create.return_value = mock_container

        exchange_dir = str(tmp_path / "exchange")
        Path(exchange_dir).mkdir()

        def fake_wait(**kwargs):
            result_data = {"checks": [], "passed": True}
            (Path(exchange_dir) / "result.json").write_text(json.dumps(result_data))
            return {"StatusCode": 0}

        mock_container.wait.side_effect = fake_wait

        with patch(
            "src.verification.remote.container_runner.tempfile.mkdtemp",
            return_value=exchange_dir,
        ):
            run_verification_container(workspace)

        create_call = mock_client.containers.create
        assert create_call.called
        kwargs = create_call.call_args[1]
        assert kwargs["network_mode"] == "none"
