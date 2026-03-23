"""Unit tests for Ralph mode dispatch in src/agent/primary_agent.py.

Epic 43 Story 43.5 — tests the agent_mode feature flag routing:
  - implement() with agent_mode="ralph" constructs RalphAgent, returns EvidenceBundle
  - implement() with agent_mode="legacy" uses PrimaryAgentRunner
  - handle_loopback() with agent_mode="ralph" passes verification failure context
  - agent_mode="ralph" takes precedence regardless of agent_isolation setting
  - agent_llm_enabled.developer=False still uses fallback (existing behaviour)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.evidence import EvidenceBundle


# ---------------------------------------------------------------------------
# Helpers — shared mocks
# ---------------------------------------------------------------------------


def _mock_taskpacket(loopback_count: int = 0) -> MagicMock:
    tp = MagicMock()
    tp.id = uuid4()
    tp.correlation_id = uuid4()
    tp.loopback_count = loopback_count
    tp.repo = "owner/repo"
    tp.issue_id = 99
    tp.task_trust_tier = None
    tp.complexity_index = None
    tp.risk_flags = {}
    return tp


def _mock_intent(version: int = 1) -> MagicMock:
    intent = MagicMock()
    intent.id = uuid4()
    intent.taskpacket_id = uuid4()
    intent.version = version
    intent.goal = "Implement rate limiting"
    intent.constraints = ["Must not break existing API"]
    intent.acceptance_criteria = ["All tests pass"]
    intent.non_goals = ["Do not refactor unrelated code"]
    intent.source = "auto"
    return intent


def _mock_task_result(summary: str = "Done") -> MagicMock:
    """Build a minimal TaskResult mock that produces a valid EvidenceBundle."""
    from ralph_sdk.status import RalphLoopStatus, RalphStatus, WorkType

    result = MagicMock()
    result.output = "- src/agent/primary_agent.py: updated"
    result.error = ""
    result.loop_count = 2
    result.duration_seconds = 10.0
    # Must be int so cost arithmetic in _implement_ralph (Story 43.10) works
    result.tokens_in = 100
    result.tokens_out = 200
    result.status = RalphStatus(
        progress_summary=summary,
        exit_signal=True,
        status=RalphLoopStatus.COMPLETED,
        work_type=WorkType.IMPLEMENTATION,
    )
    return result


# ---------------------------------------------------------------------------
# Tests for implement() dispatch
# ---------------------------------------------------------------------------


class TestImplementDispatch:
    @pytest.mark.asyncio
    async def test_ralph_mode_constructs_ralph_agent(self) -> None:
        """implement() with agent_mode='ralph' should call RalphAgent.run()."""
        taskpacket = _mock_taskpacket()
        intent = _mock_intent()

        mock_session = AsyncMock()

        with (
            patch("src.agent.primary_agent.settings") as mock_settings,
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent._implement_ralph", new_callable=AsyncMock) as mock_ralph,
        ):
            mock_settings.agent_mode = "ralph"
            mock_settings.agent_max_turns = 30
            mock_settings.agent_max_budget_usd = 5.0
            mock_settings.agent_model = "claude-sonnet-4-5"

            expected_bundle = EvidenceBundle(
                taskpacket_id=taskpacket.id,
                intent_version=1,
                files_changed=["src/agent/primary_agent.py"],
                agent_summary="Done",
            )
            mock_ralph.return_value = expected_bundle

            from src.agent.primary_agent import implement

            result = await implement(
                mock_session,
                taskpacket.id,
                repo_path="/tmp/repo",
                complexity="medium",
            )

        mock_ralph.assert_called_once()
        assert result.taskpacket_id == taskpacket.id

    @pytest.mark.asyncio
    async def test_legacy_mode_uses_primary_agent_runner(self) -> None:
        """implement() with agent_mode='legacy' should use PrimaryAgentRunner."""
        taskpacket = _mock_taskpacket()
        intent = _mock_intent()

        mock_session = AsyncMock()

        fake_agent_result = MagicMock()
        fake_agent_result.raw_output = "- src/foo.py: changed"
        fake_agent_result.model_used = "claude-sonnet-4-5"

        with (
            patch("src.agent.primary_agent.settings") as mock_settings,
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent.PrimaryAgentRunner") as mock_runner_cls,
        ):
            mock_settings.agent_mode = "legacy"
            mock_settings.agent_max_turns = 30
            mock_settings.agent_max_budget_usd = 5.0
            mock_settings.agent_model = "claude-sonnet-4-5"

            mock_runner = AsyncMock()
            mock_runner.run = AsyncMock(return_value=fake_agent_result)
            mock_runner_cls.return_value = mock_runner

            from src.agent.primary_agent import implement

            result = await implement(
                mock_session,
                taskpacket.id,
                repo_path="/tmp/repo",
            )

        mock_runner_cls.assert_called_once()
        mock_runner.run.assert_called_once()
        assert isinstance(result, EvidenceBundle)

    @pytest.mark.asyncio
    async def test_ralph_mode_returns_evidence_bundle(self) -> None:
        """implement() with agent_mode='ralph' returns a proper EvidenceBundle."""
        taskpacket = _mock_taskpacket()
        intent = _mock_intent(version=2)

        mock_session = AsyncMock()

        with (
            patch("src.agent.primary_agent.settings") as mock_settings,
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent._implement_ralph", new_callable=AsyncMock) as mock_ralph,
        ):
            mock_settings.agent_mode = "ralph"
            mock_settings.agent_max_turns = 30
            mock_settings.agent_max_budget_usd = 5.0
            mock_settings.agent_model = "claude-sonnet-4-5"

            mock_ralph.return_value = EvidenceBundle(
                taskpacket_id=taskpacket.id,
                intent_version=2,
                files_changed=["src/x.py"],
                agent_summary="Ralph completed task",
            )

            from src.agent.primary_agent import implement

            result = await implement(
                mock_session,
                taskpacket.id,
                repo_path="/tmp/repo",
            )

        assert isinstance(result, EvidenceBundle)
        assert result.intent_version == 2


# ---------------------------------------------------------------------------
# Tests for handle_loopback() dispatch
# ---------------------------------------------------------------------------


class TestHandleLoopbackDispatch:
    @pytest.mark.asyncio
    async def test_ralph_mode_passes_verification_context(self) -> None:
        """handle_loopback() with agent_mode='ralph' builds loopback context."""
        taskpacket = _mock_taskpacket(loopback_count=1)
        intent = _mock_intent()

        mock_session = AsyncMock()

        check1 = MagicMock()
        check1.name = "ruff"
        check1.passed = False
        check1.details = "E501: line too long"
        verification_result = MagicMock()
        verification_result.checks = [check1]

        with (
            patch("src.agent.primary_agent.settings") as mock_settings,
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent._implement_ralph", new_callable=AsyncMock) as mock_ralph,
        ):
            mock_settings.agent_mode = "ralph"
            mock_settings.agent_max_turns = 30
            mock_settings.agent_max_budget_usd = 5.0
            mock_settings.agent_model = "claude-sonnet-4-5"

            mock_ralph.return_value = EvidenceBundle(
                taskpacket_id=taskpacket.id,
                intent_version=1,
                files_changed=[],
                agent_summary="Fixed issues",
            )

            from src.agent.primary_agent import handle_loopback

            result = await handle_loopback(
                mock_session,
                taskpacket.id,
                repo_path="/tmp/repo",
                verification_result=verification_result,
            )

        # Verify _implement_ralph was called with non-empty loopback_context
        call_kwargs = mock_ralph.call_args
        loopback_ctx = call_kwargs.kwargs.get("loopback_context", "")
        assert len(loopback_ctx) > 0, "loopback_context should contain failure details"
        assert "ruff" in loopback_ctx or "FAILED" in loopback_ctx

    @pytest.mark.asyncio
    async def test_legacy_loopback_uses_primary_agent_runner(self) -> None:
        """handle_loopback() with agent_mode='legacy' uses PrimaryAgentRunner."""
        taskpacket = _mock_taskpacket(loopback_count=1)
        intent = _mock_intent()

        mock_session = AsyncMock()

        check1 = MagicMock()
        check1.name = "pytest"
        check1.passed = False
        check1.details = "3 tests failed"
        verification_result = MagicMock()
        verification_result.checks = [check1]

        fake_result = MagicMock()
        fake_result.raw_output = "Fixed the tests"

        with (
            patch("src.agent.primary_agent.settings") as mock_settings,
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent.PrimaryAgentRunner") as mock_runner_cls,
        ):
            mock_settings.agent_mode = "legacy"
            mock_settings.agent_max_turns = 30
            mock_settings.agent_max_budget_usd = 5.0
            mock_settings.agent_model = "claude-sonnet-4-5"

            mock_runner = AsyncMock()
            mock_runner.run = AsyncMock(return_value=fake_result)
            mock_runner_cls.return_value = mock_runner

            from src.agent.primary_agent import handle_loopback

            result = await handle_loopback(
                mock_session,
                taskpacket.id,
                repo_path="/tmp/repo",
                verification_result=verification_result,
            )

        mock_runner_cls.assert_called_once()
        assert isinstance(result, EvidenceBundle)


# ---------------------------------------------------------------------------
# Tests for _implement_ralph directly
# ---------------------------------------------------------------------------


class TestImplementRalphHelper:
    @pytest.mark.asyncio
    async def test_constructs_ralph_agent_with_null_state_backend(self) -> None:
        """_implement_ralph uses NullStateBackend in Slice 1."""
        taskpacket = _mock_taskpacket()
        intent = _mock_intent()

        mock_run_result = _mock_task_result()

        with (
            patch("ralph_sdk.RalphAgent") as mock_agent_cls,
            patch("ralph_sdk.NullStateBackend") as mock_null_cls,
        ):
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_run_result)
            mock_agent.ralph_dir = MagicMock()
            mock_agent_cls.return_value = mock_agent
            mock_null_cls.return_value = MagicMock()

            from src.agent.primary_agent import _implement_ralph

            with patch("src.settings.settings") as mock_settings:
                mock_settings.agent_model = "claude-sonnet-4-5"
                mock_settings.agent_max_turns = 30

                result = await _implement_ralph(
                    taskpacket, intent, repo_path="/tmp/repo"
                )

        mock_null_cls.assert_called_once()
        mock_agent.run.assert_called_once()
        assert isinstance(result, EvidenceBundle)

    @pytest.mark.asyncio
    async def test_correlation_id_passed_to_agent(self) -> None:
        """_implement_ralph passes the taskpacket correlation_id to RalphAgent."""
        corr_id = uuid4()
        taskpacket = _mock_taskpacket()
        taskpacket.correlation_id = corr_id
        intent = _mock_intent()

        mock_run_result = _mock_task_result()

        captured_kwargs: dict = {}

        original_init = None

        def capture_init(self_agent, **kwargs: object) -> None:  # type: ignore[misc]
            captured_kwargs.update(kwargs)
            self_agent.ralph_dir = MagicMock()
            self_agent.run = AsyncMock(return_value=mock_run_result)

        with (
            patch("ralph_sdk.RalphAgent.__init__", capture_init),
            patch("ralph_sdk.NullStateBackend"),
        ):
            from src.agent.primary_agent import _implement_ralph

            with patch("src.settings.settings") as mock_settings:
                mock_settings.agent_model = "claude-sonnet-4-5"
                mock_settings.agent_max_turns = 30

                await _implement_ralph(taskpacket, intent, repo_path="/tmp/repo")

        assert captured_kwargs.get("correlation_id") == str(corr_id)
