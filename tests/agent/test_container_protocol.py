"""Tests for container protocol — serialization models (Epic 25 Story 25.3)."""

import json
from uuid import UUID, uuid4

import pytest

from src.agent.container_protocol import (
    RESULT_OUTPUT_PATH,
    TASK_INPUT_PATH,
    WORKSPACE_DIR,
    AgentContainerResult,
    AgentTaskInput,
)


class TestAgentTaskInput:
    """Validate AgentTaskInput serialization and deserialization."""

    def test_minimal_construction(self):
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/test-org/test-repo.git",
            system_prompt="You are a developer.",
        )
        assert task.branch == "main"
        assert task.max_turns == 30
        assert task.max_budget_usd == 5.0
        assert task.loopback_attempt == 0
        assert task.repo_tier == "observe"
        assert task.tool_allowlist == []

    def test_full_construction(self):
        tp_id = uuid4()
        corr_id = uuid4()
        task = AgentTaskInput(
            taskpacket_id=tp_id,
            correlation_id=corr_id,
            repo_url="https://github.com/test-org/test-repo.git",
            branch="feature/fix-login",
            system_prompt="You are a developer agent.",
            tool_allowlist=["Read", "Write", "Edit", "Bash"],
            intent_goal="Fix login timeout",
            intent_constraints=["No new dependencies"],
            acceptance_criteria=["Login completes in <2s"],
            non_goals=["Do not refactor auth module"],
            context_summary="Users report 30s timeout",
            max_turns=20,
            max_budget_usd=3.0,
            loopback_attempt=1,
            verification_feedback="pytest failed: test_login_speed",
            repo_tier="suggest",
            complexity="medium",
            risk_flags={"security": True, "breaking_change": False},
        )
        assert task.taskpacket_id == tp_id
        assert task.repo_tier == "suggest"
        assert len(task.intent_constraints) == 1

    def test_round_trip_json(self):
        """Serialization round-trip is lossless (AC #9)."""
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="Test prompt",
            tool_allowlist=["Read", "Bash"],
            intent_goal="Fix bug",
            acceptance_criteria=["Tests pass", "No regressions"],
            risk_flags={"security": True},
        )
        json_str = task.model_dump_json()
        restored = AgentTaskInput.model_validate_json(json_str)

        assert restored.taskpacket_id == task.taskpacket_id
        assert restored.correlation_id == task.correlation_id
        assert restored.repo_url == task.repo_url
        assert restored.tool_allowlist == task.tool_allowlist
        assert restored.intent_goal == task.intent_goal
        assert restored.acceptance_criteria == task.acceptance_criteria
        assert restored.risk_flags == task.risk_flags

    def test_json_dict_round_trip(self):
        """Round-trip through dict (simulates file I/O)."""
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="prompt",
        )
        data = json.loads(task.model_dump_json())
        restored = AgentTaskInput.model_validate(data)
        assert restored == task

    def test_uuid_serialization(self):
        """UUIDs serialize as strings in JSON."""
        task = AgentTaskInput(
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            repo_url="https://github.com/org/repo.git",
            system_prompt="test",
        )
        data = json.loads(task.model_dump_json())
        assert isinstance(data["taskpacket_id"], str)
        # Can parse back to UUID
        UUID(data["taskpacket_id"])


class TestAgentContainerResult:
    """Validate AgentContainerResult serialization and deserialization."""

    def test_success_result(self):
        result = AgentContainerResult(
            success=True,
            files_changed=["src/auth/login.py", "tests/test_login.py"],
            test_results="5 passed",
            lint_results="no errors",
            agent_summary="Fixed login timeout by adding connection pooling.",
            tokens_used=1500,
            cost_usd=0.02,
            duration_ms=45000,
        )
        assert result.success is True
        assert len(result.files_changed) == 2
        assert result.exit_reason == "completed"

    def test_failure_result(self):
        result = AgentContainerResult(
            success=False,
            exit_reason="error",
            error_message="Agent crashed: ImportError",
        )
        assert result.success is False
        assert result.error_message != ""

    def test_timeout_result(self):
        result = AgentContainerResult(
            success=False,
            files_changed=["src/partial.py"],
            exit_reason="timeout",
            agent_summary="Partial implementation before timeout.",
        )
        assert result.exit_reason == "timeout"
        assert len(result.files_changed) == 1  # Partial results preserved

    def test_round_trip_json(self):
        """Serialization round-trip is lossless (AC #9)."""
        result = AgentContainerResult(
            success=True,
            files_changed=["a.py", "b.py"],
            test_results="all pass",
            lint_results="clean",
            agent_summary="Done",
            intent_version=2,
            tokens_used=500,
            cost_usd=0.01,
            duration_ms=30000,
        )
        json_str = result.model_dump_json()
        restored = AgentContainerResult.model_validate_json(json_str)

        assert restored.success == result.success
        assert restored.files_changed == result.files_changed
        assert restored.intent_version == result.intent_version
        assert restored.tokens_used == result.tokens_used
        assert restored.duration_ms == result.duration_ms

    def test_created_at_auto_populated(self):
        result = AgentContainerResult(success=True)
        assert result.created_at is not None


class TestProtocolConstants:
    """Verify volume path constants."""

    def test_workspace_dir(self):
        assert WORKSPACE_DIR == "/workspace"

    def test_task_input_path(self):
        assert TASK_INPUT_PATH == "/workspace/task.json"

    def test_result_output_path(self):
        assert RESULT_OUTPUT_PATH == "/workspace/result.json"
