"""Unit tests for Primary Agent (Story 0.5).

Tests developer role config, system prompt building, evidence parsing,
and agent orchestration with mocked SDK calls.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agent.developer_role import (
    DEFAULT_TOOL_ALLOWLIST,
    DeveloperRoleConfig,
    build_system_prompt,
)
from src.agent.evidence import EvidenceBundle
from src.agent.primary_agent import _parse_changed_files
from src.intent.intent_spec import IntentSpecRead
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

# --- Fixtures ---


def _make_taskpacket(**overrides: object) -> TaskPacketRead:
    defaults = {
        "id": uuid4(),
        "repo": "acme/widgets",
        "issue_id": 42,
        "delivery_id": "abc123",
        "correlation_id": uuid4(),
        "status": TaskPacketStatus.INTENT_BUILT,
        "scope": {"type": "feature", "components": ["api"]},
        "risk_flags": {"auth": False, "migration": False},
        "complexity_index": {"score": 0.4, "band": "medium", "dimensions": {"scope_breadth": 2, "risk_flag_count": 1, "dependency_count": 3, "lines_estimate": 100, "expert_coverage": 1}},
        "context_packs": [],
        "intent_spec_id": uuid4(),
        "intent_version": 1,
        "loopback_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return TaskPacketRead(**defaults)  # type: ignore[arg-type]


def _make_intent(**overrides: object) -> IntentSpecRead:
    defaults = {
        "id": uuid4(),
        "taskpacket_id": uuid4(),
        "version": 1,
        "goal": "Add a /health endpoint that returns HTTP 200 with JSON body",
        "constraints": ["No new dependencies", "Must pass existing tests"],
        "acceptance_criteria": [
            "GET /health returns 200",
            "Response body is JSON with status field",
        ],
        "non_goals": ["Authentication on health endpoint", "Metrics endpoint"],
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return IntentSpecRead(**defaults)  # type: ignore[arg-type]


# --- DeveloperRoleConfig Tests ---


class TestDeveloperRoleConfig:
    def test_defaults(self) -> None:
        config = DeveloperRoleConfig()
        assert config.tool_allowlist == DEFAULT_TOOL_ALLOWLIST
        assert config.model == "claude-sonnet-4-5"
        assert config.max_turns == 30
        assert config.max_budget_usd == 5.0
        assert config.permission_mode == "acceptEdits"

    def test_custom_config(self) -> None:
        config = DeveloperRoleConfig(
            tool_allowlist=["Read", "Edit"],
            model="claude-haiku-4-5",
            max_turns=10,
        )
        assert config.tool_allowlist == ["Read", "Edit"]
        assert config.model == "claude-haiku-4-5"
        assert config.max_turns == 10

    def test_frozen(self) -> None:
        config = DeveloperRoleConfig()
        with pytest.raises(AttributeError):
            config.model = "changed"  # type: ignore[misc]


# --- System Prompt Tests ---


class TestBuildSystemPrompt:
    def test_includes_goal(self) -> None:
        intent = _make_intent()
        tp = _make_taskpacket()
        prompt = build_system_prompt(intent, tp)
        assert intent.goal in prompt

    def test_includes_constraints(self) -> None:
        intent = _make_intent(constraints=["No new deps", "Must be async"])
        tp = _make_taskpacket()
        prompt = build_system_prompt(intent, tp)
        assert "No new deps" in prompt
        assert "Must be async" in prompt

    def test_includes_acceptance_criteria(self) -> None:
        intent = _make_intent(acceptance_criteria=["Returns 200", "JSON body"])
        tp = _make_taskpacket()
        prompt = build_system_prompt(intent, tp)
        assert "Returns 200" in prompt
        assert "JSON body" in prompt

    def test_includes_non_goals(self) -> None:
        intent = _make_intent(non_goals=["Auth", "Metrics"])
        tp = _make_taskpacket()
        prompt = build_system_prompt(intent, tp)
        assert "Auth" in prompt
        assert "Metrics" in prompt

    def test_includes_repo_and_taskpacket(self) -> None:
        tp = _make_taskpacket(repo="acme/api")
        intent = _make_intent()
        prompt = build_system_prompt(intent, tp)
        assert "acme/api" in prompt
        assert str(tp.id) in prompt

    def test_empty_lists_show_none(self) -> None:
        intent = _make_intent(constraints=[], acceptance_criteria=[], non_goals=[])
        tp = _make_taskpacket()
        prompt = build_system_prompt(intent, tp)
        assert "- None" in prompt

    def test_includes_complexity_and_risk(self) -> None:
        tp = _make_taskpacket(
            complexity_index={"score": 0.8, "band": "high", "dimensions": {"scope_breadth": 5, "risk_flag_count": 3, "dependency_count": 5, "lines_estimate": 500, "expert_coverage": 3}},
            risk_flags={"auth": True, "migration": False},
        )
        intent = _make_intent()
        prompt = build_system_prompt(intent, tp)
        assert "high" in prompt
        assert "auth=True" in prompt


# --- Evidence Bundle Tests ---


class TestEvidenceBundle:
    def test_creation(self) -> None:
        tp_id = uuid4()
        evidence = EvidenceBundle(
            taskpacket_id=tp_id,
            intent_version=1,
            files_changed=["src/main.py"],
            test_results="5 passed",
            lint_results="ok",
            agent_summary="Added health endpoint",
        )
        assert evidence.taskpacket_id == tp_id
        assert evidence.intent_version == 1
        assert evidence.files_changed == ["src/main.py"]
        assert evidence.loopback_attempt == 0

    def test_defaults(self) -> None:
        evidence = EvidenceBundle(taskpacket_id=uuid4(), intent_version=1)
        assert evidence.files_changed == []
        assert evidence.test_results == ""
        assert evidence.lint_results == ""
        assert evidence.agent_summary == ""
        assert evidence.loopback_attempt == 0


# --- File Parsing Tests ---


class TestParseChangedFiles:
    def test_parses_file_paths(self) -> None:
        summary = (
            "Files changed:\n"
            "- src/main.py: Added health endpoint\n"
            "- tests/test_health.py: Added test\n"
            "- README.md: Updated docs\n"
        )
        files = _parse_changed_files(summary)
        assert "src/main.py" in files
        assert "tests/test_health.py" in files
        assert "README.md" in files

    def test_ignores_non_file_lines(self) -> None:
        summary = (
            "Summary:\n"
            "- Added a new feature\n"
            "- No breaking changes\n"
            "- src/app.py: Modified\n"
        )
        files = _parse_changed_files(summary)
        assert "src/app.py" in files
        assert len(files) == 1

    def test_empty_summary(self) -> None:
        assert _parse_changed_files("") == []

    def test_no_files(self) -> None:
        summary = "Everything looks good!\nNo files were changed."
        assert _parse_changed_files(summary) == []


# --- Primary Agent Orchestration Tests ---


class TestImplement:
    @pytest.mark.asyncio
    async def test_implement_success(self) -> None:
        """Agent implements successfully, returns evidence bundle."""
        tp_id = uuid4()
        tp = _make_taskpacket(id=tp_id, status=TaskPacketStatus.INTENT_BUILT)
        intent = _make_intent(taskpacket_id=tp_id)

        mock_session = AsyncMock()

        with (
            patch("src.agent.primary_agent.get_by_id", return_value=tp),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", return_value=intent),
            patch("src.agent.primary_agent.update_status", return_value=tp),
            patch(
                "src.agent.primary_agent._run_agent",
                return_value="Files changed:\n- src/health.py: Added endpoint\n",
            ),
        ):
            from src.agent.primary_agent import implement

            evidence = await implement(mock_session, tp_id, "/tmp/repo")

        assert evidence.taskpacket_id == tp_id
        assert evidence.intent_version == intent.version
        assert "src/health.py" in evidence.files_changed

    @pytest.mark.asyncio
    async def test_implement_no_taskpacket_raises(self) -> None:
        with patch("src.agent.primary_agent.get_by_id", return_value=None):
            from src.agent.primary_agent import implement

            with pytest.raises(ValueError, match="not found"):
                await implement(AsyncMock(), uuid4(), "/tmp/repo")

    @pytest.mark.asyncio
    async def test_implement_no_intent_raises(self) -> None:
        tp = _make_taskpacket()

        with (
            patch("src.agent.primary_agent.get_by_id", return_value=tp),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", return_value=None),
            patch("src.agent.primary_agent.update_status", return_value=tp),
        ):
            from src.agent.primary_agent import implement

            with pytest.raises(ValueError, match="No IntentSpec"):
                await implement(AsyncMock(), tp.id, "/tmp/repo")


class TestHandleLoopback:
    @pytest.mark.asyncio
    async def test_loopback_provides_failure_context(self) -> None:
        """Loopback sends verification failure details to the agent."""
        tp_id = uuid4()
        tp = _make_taskpacket(
            id=tp_id,
            status=TaskPacketStatus.VERIFICATION_FAILED,
            loopback_count=1,
        )
        intent = _make_intent(taskpacket_id=tp_id)

        from src.verification.gate import VerificationResult
        from src.verification.runners.base import CheckResult

        vr = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="ruff", passed=True),
                CheckResult(name="pytest", passed=False, details="1 test failed"),
            ],
            loopback_triggered=True,
        )

        captured_prompt = ""

        async def mock_run_agent(
            system_prompt: str, user_prompt: str, repo_path: str, role_config: object
        ) -> str:
            nonlocal captured_prompt
            captured_prompt = user_prompt
            return "Fixed:\n- src/health.py: Fixed test\n"

        with (
            patch("src.agent.primary_agent.get_by_id", return_value=tp),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", return_value=intent),
            patch("src.agent.primary_agent.update_status", return_value=tp),
            patch("src.agent.primary_agent._run_agent", side_effect=mock_run_agent),
        ):
            from src.agent.primary_agent import handle_loopback

            evidence = await handle_loopback(AsyncMock(), tp_id, "/tmp/repo", vr)

        assert "1 test failed" in captured_prompt
        assert "loopback attempt" in captured_prompt.lower()
        assert evidence.loopback_attempt == 1

    @pytest.mark.asyncio
    async def test_loopback_no_taskpacket_raises(self) -> None:
        from src.verification.gate import VerificationResult

        vr = VerificationResult(passed=False, checks=[], loopback_triggered=True)

        with patch("src.agent.primary_agent.get_by_id", return_value=None):
            from src.agent.primary_agent import handle_loopback

            with pytest.raises(ValueError, match="not found"):
                await handle_loopback(AsyncMock(), uuid4(), "/tmp/repo", vr)
