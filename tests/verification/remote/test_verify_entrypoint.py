"""Tests for verification container entrypoint (Story 40.9)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.verification.remote.verify_entrypoint import (
    main,
    read_task,
    run_step,
    write_result,
)


class TestReadTask:
    """Tests for read_task()."""

    def test_reads_valid_json(self, tmp_path: Path) -> None:
        """Reads and parses a valid task JSON file."""
        task_file = tmp_path / "task.json"
        task_data = {
            "install_command": "pip install .",
            "lint_command": "ruff check src/",
            "test_command": "pytest",
            "install_timeout": 60,
        }
        task_file.write_text(json.dumps(task_data))

        result = read_task(str(task_file))

        assert result["install_command"] == "pip install ."
        assert result["lint_command"] == "ruff check src/"
        assert result["test_command"] == "pytest"
        assert result["install_timeout"] == 60

    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        """Returns empty dict when task file does not exist."""
        result = read_task(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        """Raises ValueError on malformed JSON."""
        task_file = tmp_path / "task.json"
        task_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            read_task(str(task_file))


class TestRunStep:
    """Tests for run_step()."""

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_successful_step(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Successful command returns passed=True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        result = run_step("install", "pip install -e .", str(tmp_path))

        assert result["name"] == "install"
        assert result["passed"] is True
        assert result["duration_ms"] >= 0

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_failed_step(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Failed command returns passed=False with output."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")

        result = run_step("ruff", "ruff check .", str(tmp_path))

        assert result["name"] == "remote_ruff"
        assert result["passed"] is False
        assert "error msg" in result["details"]

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_test_no_tests_collected(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """pytest exit code 5 (no tests) is treated as pass."""
        mock_run.return_value = MagicMock(returncode=5, stdout="no tests", stderr="")

        result = run_step("test", "pytest", str(tmp_path))

        assert result["name"] == "remote_test"
        assert result["passed"] is True
        assert "No tests collected" in result["details"]

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Timeout returns passed=False with timeout message."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ruff", timeout=10)

        result = run_step("ruff", "ruff check .", str(tmp_path), timeout=10)

        assert result["passed"] is False
        assert "timed out" in result["details"]

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_command_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """FileNotFoundError returns passed=False."""
        mock_run.side_effect = FileNotFoundError("not found")

        result = run_step("install", "nonexistent", str(tmp_path))

        assert result["passed"] is False
        assert "Command not found" in result["details"]

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_install_name_not_prefixed(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Install step uses 'install' as name, not 'remote_install'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        result = run_step("install", "pip install -e .", str(tmp_path))

        assert result["name"] == "install"

    @patch("src.verification.remote.verify_entrypoint.subprocess.run")
    def test_lint_name_prefixed(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Non-install steps are prefixed with 'remote_'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        result = run_step("ruff", "ruff check .", str(tmp_path))

        assert result["name"] == "remote_ruff"


class TestWriteResult:
    """Tests for write_result()."""

    def test_writes_valid_json(self, tmp_path: Path) -> None:
        """Writes properly formatted result JSON."""
        result_path = tmp_path / "result.json"
        checks = [
            {"name": "install", "passed": True, "details": "", "duration_ms": 100},
            {"name": "remote_ruff", "passed": True, "details": "", "duration_ms": 50},
        ]

        write_result(checks, str(result_path))

        output = json.loads(result_path.read_text())
        assert output["passed"] is True
        assert output["total_duration_ms"] == 150
        assert len(output["checks"]) == 2

    def test_passed_false_when_any_fails(self, tmp_path: Path) -> None:
        """Overall passed is False when any check fails."""
        result_path = tmp_path / "result.json"
        checks = [
            {"name": "install", "passed": True, "details": "", "duration_ms": 100},
            {"name": "remote_pytest", "passed": False, "details": "1 failed", "duration_ms": 200},
        ]

        write_result(checks, str(result_path))

        output = json.loads(result_path.read_text())
        assert output["passed"] is False


class TestMain:
    """Tests for main() entrypoint."""

    @patch("src.verification.remote.verify_entrypoint.run_step")
    def test_all_pass_returns_zero(self, mock_step: MagicMock, tmp_path: Path) -> None:
        """When all steps pass, main returns 0."""
        task_file = tmp_path / "task.json"
        task_file.write_text(json.dumps({"repo_dir": str(tmp_path)}))
        result_file = tmp_path / "result.json"

        mock_step.return_value = {"name": "install", "passed": True, "details": "", "duration_ms": 10}

        exit_code = main(str(task_file), str(result_file))

        assert exit_code == 0
        assert mock_step.call_count == 3  # install, lint, test

    @patch("src.verification.remote.verify_entrypoint.run_step")
    def test_install_failure_stops_early(self, mock_step: MagicMock, tmp_path: Path) -> None:
        """When install fails, lint and test are skipped."""
        task_file = tmp_path / "task.json"
        task_file.write_text(json.dumps({"repo_dir": str(tmp_path)}))
        result_file = tmp_path / "result.json"

        mock_step.return_value = {
            "name": "install",
            "passed": False,
            "details": "pip error",
            "duration_ms": 10,
        }

        exit_code = main(str(task_file), str(result_file))

        assert exit_code == 1
        assert mock_step.call_count == 1  # only install

    @patch("src.verification.remote.verify_entrypoint.run_step")
    def test_test_failure_returns_one(self, mock_step: MagicMock, tmp_path: Path) -> None:
        """When test fails, main returns 1."""
        task_file = tmp_path / "task.json"
        task_file.write_text(json.dumps({"repo_dir": str(tmp_path)}))
        result_file = tmp_path / "result.json"

        def side_effect(name, cmd, cwd, timeout=300):
            if name == "test":
                return {"name": "remote_test", "passed": False, "details": "fail", "duration_ms": 10}
            return {"name": name, "passed": True, "details": "", "duration_ms": 10}

        mock_step.side_effect = side_effect

        exit_code = main(str(task_file), str(result_file))

        assert exit_code == 1

    def test_defaults_used_when_no_task_file(self, tmp_path: Path) -> None:
        """main() uses defaults when task file is missing."""
        task_file = tmp_path / "nonexistent.json"
        result_file = tmp_path / "result.json"

        with patch("src.verification.remote.verify_entrypoint.run_step") as mock_step:
            mock_step.return_value = {"name": "install", "passed": True, "details": "", "duration_ms": 10}

            exit_code = main(str(task_file), str(result_file))

            # Should still call all 3 steps with defaults
            assert mock_step.call_count == 3
            assert exit_code == 0
