"""Tests for container lifecycle manager (Epic 25 Story 25.2).

These tests mock the Docker API — no real Docker daemon required.
Integration tests with real Docker are gated by @pytest.mark.docker.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.container_manager import (
    CONTAINER_LABEL,
    CONTAINER_LABEL_VALUE,
    ContainerConfig,
    ContainerManager,
    ContainerOutcome,
)
from src.agent.container_protocol import AgentContainerResult, AgentTaskInput


def _make_task_input(**overrides) -> AgentTaskInput:
    """Create a minimal AgentTaskInput for testing."""
    defaults = {
        "taskpacket_id": uuid4(),
        "correlation_id": uuid4(),
        "repo_url": "https://github.com/test-org/test-repo.git",
        "system_prompt": "You are a developer.",
        "repo_tier": "observe",
    }
    defaults.update(overrides)
    return AgentTaskInput(**defaults)


def _make_success_result() -> dict:
    """Create a success result dict as the container would write."""
    return AgentContainerResult(
        success=True,
        files_changed=["src/fix.py"],
        agent_summary="Fixed the bug.",
        tokens_used=100,
        cost_usd=0.01,
        duration_ms=5000,
    ).model_dump(mode="json")


def _write_result_to_dir(directory: str, result_data: dict | None = None) -> None:
    """Write a result.json file to the given directory."""
    if result_data is None:
        result_data = _make_success_result()
    result_path = Path(directory) / "result.json"
    result_path.write_text(json.dumps(result_data), encoding="utf-8")


class TestContainerConfig:
    def test_defaults(self):
        config = ContainerConfig()
        assert config.cpu_limit == 1.0
        assert config.memory_mb == 512
        assert config.timeout_seconds == 300
        assert config.network == "agent-net"
        assert config.pids_limit == 256

    def test_custom_config(self):
        config = ContainerConfig(
            cpu_limit=4.0,
            memory_mb=8192,
            timeout_seconds=7200,
        )
        assert config.cpu_limit == 4.0
        assert config.memory_mb == 8192


class TestDockerAvailability:
    def test_docker_available(self):
        """Docker is available when ping succeeds."""
        mock_docker = MagicMock()
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        with patch.dict("sys.modules", {"docker": mock_docker}):
            # Need to reimport to pick up the mock
            assert ContainerManager.is_docker_available() is True

    def test_docker_unavailable_no_module(self):
        """Docker unavailable when docker package not installed."""
        with patch.dict("sys.modules", {"docker": None}):
            assert ContainerManager.is_docker_available() is False


class TestContainerManagerLaunch:
    """Test the launch lifecycle with mocked Docker client."""

    def _setup_mock_container(self, exit_code=0, oom_killed=False):
        """Create a mock Docker container."""
        container = MagicMock()
        container.short_id = "abc123"
        container.wait.return_value = {"StatusCode": exit_code}
        container.logs.return_value = b"agent output logs"
        container.attrs = {
            "State": {"OOMKilled": oom_killed},
            "Created": "2026-03-17T00:00:00Z",
        }
        return container

    def _make_manager_with_mock(self, container):
        """Create a ContainerManager with a mocked Docker client."""
        mock_client = MagicMock()
        mock_client.containers.create.return_value = container
        manager = ContainerManager()
        manager._client = mock_client
        return manager, mock_client

    def test_successful_launch(self):
        """Full lifecycle: launch → wait → collect → cleanup."""
        task = _make_task_input()
        mock_container = self._setup_mock_container()
        manager, mock_client = self._make_manager_with_mock(mock_container)

        # Patch mkdtemp to create a real temp dir with result.json
        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        _write_result_to_dir(real_dir)

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            outcome = manager.launch(task)

        assert outcome.result is not None
        assert outcome.result.success is True
        assert outcome.exit_code == 0
        assert outcome.timed_out is False
        assert outcome.oom_killed is False
        assert outcome.container_id == "abc123"
        assert outcome.launch_ms >= 0
        assert outcome.total_ms >= 0

        # Container was started and cleaned up
        mock_container.start.assert_called_once()
        mock_container.remove.assert_called_once_with(force=True)

    def test_container_with_resource_limits(self):
        """Container is created with correct resource limits."""
        config = ContainerConfig(cpu_limit=2.0, memory_mb=4096, pids_limit=512)
        task = _make_task_input()

        mock_container = self._setup_mock_container()
        mock_client = MagicMock()
        mock_client.containers.create.return_value = mock_container

        manager = ContainerManager(config)
        manager._client = mock_client

        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        _write_result_to_dir(real_dir)

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            manager.launch(task)

        call_kwargs = mock_client.containers.create.call_args[1]
        assert call_kwargs["mem_limit"] == "4096m"
        assert call_kwargs["nano_cpus"] == int(2.0 * 1e9)
        assert call_kwargs["pids_limit"] == 512

    def test_container_labels(self):
        """Container gets correct labels for reaper identification."""
        task = _make_task_input()
        mock_container = self._setup_mock_container()
        manager, mock_client = self._make_manager_with_mock(mock_container)

        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        _write_result_to_dir(real_dir)

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            manager.launch(task)

        labels = mock_client.containers.create.call_args[1]["labels"]
        assert labels[CONTAINER_LABEL] == CONTAINER_LABEL_VALUE
        assert labels["thestudio.taskpacket_id"] == str(task.taskpacket_id)

    def test_oom_killed_detected(self):
        """OOM kill is detected via container state."""
        task = _make_task_input()
        mock_container = self._setup_mock_container(exit_code=137, oom_killed=True)
        manager, _ = self._make_manager_with_mock(mock_container)

        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        _write_result_to_dir(real_dir)

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            outcome = manager.launch(task)

        assert outcome.oom_killed is True
        assert outcome.exit_code == 137

    def test_no_result_file(self):
        """Missing result.json returns None result."""
        task = _make_task_input()
        mock_container = self._setup_mock_container(exit_code=1)
        manager, _ = self._make_manager_with_mock(mock_container)

        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        # No result.json written

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            outcome = manager.launch(task)

        assert outcome.result is None
        assert outcome.exit_code == 1

    def test_timeout_kills_container(self):
        """Timeout triggers kill and partial result collection."""
        task = _make_task_input()
        mock_container = MagicMock()
        mock_container.short_id = "timeout123"
        mock_container.wait.side_effect = Exception("timeout")
        mock_container.attrs = {"State": {"OOMKilled": False}}

        manager, _ = self._make_manager_with_mock(mock_container)
        manager.config = ContainerConfig(timeout_seconds=1)

        real_dir = tempfile.mkdtemp(prefix="test-agent-")
        # Write partial result
        _write_result_to_dir(
            real_dir,
            AgentContainerResult(
                success=False,
                files_changed=["partial.py"],
                agent_summary="Partial work",
            ).model_dump(mode="json"),
        )

        with patch("src.agent.container_manager.tempfile.mkdtemp", return_value=real_dir):
            outcome = manager.launch(task)

        assert outcome.timed_out is True
        assert outcome.result is not None
        assert outcome.result.exit_reason == "timeout"
        assert outcome.result.files_changed == ["partial.py"]
        mock_container.kill.assert_called_once()

    def test_cleanup_always_runs(self):
        """Container and workspace are cleaned up even on error."""
        task = _make_task_input()

        mock_client = MagicMock()
        mock_client.containers.create.side_effect = RuntimeError("Docker error")

        manager = ContainerManager()
        manager._client = mock_client

        outcome = manager.launch(task)
        assert outcome.result is not None
        assert outcome.result.success is False
        assert "Docker error" in outcome.result.error_message


class TestContainerManagerReaper:
    """Test dead container reaping."""

    def test_reap_old_containers(self):
        """Containers older than threshold are removed."""
        old_container = MagicMock()
        old_container.short_id = "old123"
        old_container.attrs = {"Created": "2026-03-10T00:00:00Z"}

        recent_container = MagicMock()
        recent_container.short_id = "new456"
        recent_container.attrs = {"Created": "2026-03-17T12:00:00Z"}

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [old_container, recent_container]

        manager = ContainerManager()
        manager._client = mock_client

        reaped = manager.reap_orphans()
        assert reaped == 1
        old_container.remove.assert_called_once_with(force=True)
        recent_container.remove.assert_not_called()

    def test_reap_no_containers(self):
        """No containers to reap returns 0."""
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []

        manager = ContainerManager()
        manager._client = mock_client

        assert manager.reap_orphans() == 0


class TestCollectResults:
    """Test result file parsing."""

    def test_valid_result(self, tmp_path):
        result_data = AgentContainerResult(
            success=True,
            files_changed=["a.py"],
            agent_summary="Done",
        ).model_dump(mode="json")
        (tmp_path / "result.json").write_text(json.dumps(result_data), encoding="utf-8")

        manager = ContainerManager()
        result = manager._collect_results(str(tmp_path))

        assert result is not None
        assert result.success is True
        assert result.files_changed == ["a.py"]

    def test_malformed_json(self, tmp_path):
        (tmp_path / "result.json").write_text("not valid json", encoding="utf-8")

        manager = ContainerManager()
        result = manager._collect_results(str(tmp_path))
        assert result is None

    def test_missing_file(self, tmp_path):
        manager = ContainerManager()
        result = manager._collect_results(str(tmp_path))
        assert result is None
