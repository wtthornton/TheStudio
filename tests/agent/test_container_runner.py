"""Tests for container runner — in-container entrypoint (Epic 25 Story 25.1)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.container_protocol import AgentContainerResult, AgentTaskInput
from src.agent.container_runner import _build_evidence_bundle, _read_task_input


class TestReadTaskInput:
    def test_reads_valid_task(self, tmp_path):
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="test",
        )
        task_file = tmp_path / "task.json"
        task_file.write_text(task.model_dump_json(), encoding="utf-8")

        with patch(
            "src.agent.container_protocol.TASK_INPUT_PATH",
            str(task_file),
        ):
            data = _read_task_input()

        assert data["repo_url"] == "https://github.com/org/repo.git"
        assert "taskpacket_id" in data

    def test_raises_on_missing_file(self):
        with patch(
            "src.agent.container_protocol.TASK_INPUT_PATH",
            "/nonexistent/task.json",
        ):
            with pytest.raises(FileNotFoundError):
                _read_task_input()


class TestBuildEvidenceBundle:
    def test_extracts_files_from_summary(self):
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="test",
        )

        agent_result = MagicMock()
        agent_result.raw_output = (
            "I modified: src/auth/login.py\nCreated: tests/test_login.py\nChanged: src/config.py"
        )
        agent_result.used_fallback = False
        agent_result.tokens_in = 100
        agent_result.tokens_out = 200
        agent_result.cost_estimated = 0.01
        agent_result.duration_ms = 5000

        result = _build_evidence_bundle(task, agent_result)

        assert result.success is True
        assert "src/auth/login.py" in result.files_changed
        assert "tests/test_login.py" in result.files_changed
        assert "src/config.py" in result.files_changed
        assert result.tokens_used == 300
        assert result.cost_usd == 0.01

    def test_fallback_marks_failure(self):
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="test",
        )

        agent_result = MagicMock()
        agent_result.raw_output = ""
        agent_result.used_fallback = True
        agent_result.tokens_in = 0
        agent_result.tokens_out = 0
        agent_result.cost_estimated = 0.0
        agent_result.duration_ms = 100

        result = _build_evidence_bundle(task, agent_result)
        assert result.success is False

    def test_no_duplicate_files(self):
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="test",
        )

        agent_result = MagicMock()
        agent_result.raw_output = "Modified: src/main.py\nUpdated: src/main.py"
        agent_result.used_fallback = False
        agent_result.tokens_in = 50
        agent_result.tokens_out = 50
        agent_result.cost_estimated = 0.005
        agent_result.duration_ms = 2000

        result = _build_evidence_bundle(task, agent_result)
        assert result.files_changed.count("src/main.py") == 1
