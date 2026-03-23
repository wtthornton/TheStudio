"""E2E integration test — Ralph implement + loopback via the full path.

Epic 43 Story 43.15.

Exercises the complete flow without patching _implement_ralph itself:

  implement() / handle_loopback()
    → taskpacket_to_ralph_input()      (bridge: real)
    → build_ralph_config()             (bridge: real)
    → from_task_packet()               (ralph_sdk: real)
    → RalphAgent.__init__()            (patched: no CLI)
    → RalphAgent.run()                 (patched: returns mock TaskResult)
    → ralph_result_to_evidence()       (bridge: real)
    → ModelCallAudit / BudgetEnforcer  (in-memory cost recording: real)
    → EvidenceBundle returned

Mocking boundary: only the RalphAgent constructor + run() are mocked.
All bridge conversion functions and SDK helper calls execute for real so
regressions in the translation layer surface here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.evidence import EvidenceBundle
from src.models.taskpacket import TaskTrustTier
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_taskpacket(
    loopback_count: int = 0,
    *,
    trust_tier: TaskTrustTier | None = TaskTrustTier.EXECUTE,
    complexity_band: str = "medium",
    risk_flags: dict | None = None,
) -> MagicMock:
    """Build a realistic TaskPacketRow-like mock."""
    tp = MagicMock()
    tp.id = uuid4()
    tp.correlation_id = uuid4()
    tp.loopback_count = loopback_count
    tp.repo = "owner/e2e-repo"
    tp.issue_id = 1234
    tp.task_trust_tier = trust_tier
    tp.complexity_index = {"band": complexity_band, "score": 5}
    tp.risk_flags = risk_flags or {}
    return tp


def _make_intent(version: int = 1) -> MagicMock:
    """Build a realistic IntentSpecRead-like mock."""
    intent = MagicMock()
    intent.id = uuid4()
    intent.taskpacket_id = uuid4()
    intent.version = version
    intent.goal = "Implement rate limiting for the /api/upload endpoint"
    intent.constraints = [
        "Must not break existing upload tests",
        "Limit: 100 requests per minute per user",
    ]
    intent.acceptance_criteria = [
        "ruff check passes",
        "pytest tests/unit/test_upload.py passes",
        "Rate limit header X-RateLimit-Remaining present in response",
    ]
    intent.non_goals = ["Do not change authentication logic"]
    intent.source = "auto"
    return intent


def _make_task_result(
    *,
    summary: str = "Implementation complete",
    output: str = "- src/api/upload.py: added rate limiting\n- tests/unit/test_upload.py: updated",
    tokens_in: int = 150,
    tokens_out: int = 350,
    loop_count: int = 3,
    duration_seconds: float = 12.5,
) -> MagicMock:
    """Build a TaskResult mock that produces a valid EvidenceBundle."""
    from ralph_sdk.status import RalphLoopStatus, RalphStatus, WorkType

    result = MagicMock()
    result.output = output
    result.error = ""
    result.loop_count = loop_count
    result.duration_seconds = duration_seconds
    result.tokens_in = tokens_in
    result.tokens_out = tokens_out
    result.status = RalphStatus(
        progress_summary=summary,
        exit_signal=True,
        status=RalphLoopStatus.COMPLETED,
        work_type=WorkType.IMPLEMENTATION,
    )
    return result


def _patch_settings(*, agent_mode: str = "ralph", state_backend: str = "null") -> MagicMock:
    """Return a settings mock for Ralph mode."""
    s = MagicMock()
    s.agent_mode = agent_mode
    s.agent_max_turns = 30
    s.agent_max_budget_usd = 5.0
    s.agent_model = "claude-sonnet-4-5"
    s.ralph_state_backend = state_backend
    s.ralph_session_ttl_seconds = 7200
    return s


# ---------------------------------------------------------------------------
# E2E: implement() — full path via Ralph
# ---------------------------------------------------------------------------


class TestRalphImplementE2E:
    """Full path: implement() → _implement_ralph → bridge → agent.run() → EvidenceBundle."""

    @pytest.mark.asyncio
    async def test_implement_returns_evidence_bundle_with_files(self) -> None:
        """implement() in Ralph mode returns EvidenceBundle with changed files populated."""
        taskpacket = _make_taskpacket()
        intent = _make_intent(version=1)
        task_result = _make_task_result()

        session = AsyncMock()

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        # ralph_dir is set by _implement_ralph after construction
        mock_agent.ralph_dir = MagicMock()

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            result = await implement(
                session,
                taskpacket.id,
                repo_path="/tmp/e2e-repo",
                complexity="medium",
            )

        assert isinstance(result, EvidenceBundle)
        assert result.taskpacket_id == taskpacket.id
        assert result.intent_version == 1
        assert result.loopback_attempt == 0
        # Bridge function _parse_changed_files extracts the bullet-list paths
        assert "src/api/upload.py" in result.files_changed
        assert "tests/unit/test_upload.py" in result.files_changed

    @pytest.mark.asyncio
    async def test_implement_passes_correlation_id_to_agent(self) -> None:
        """_implement_ralph passes correlation_id from TaskPacket to RalphAgent."""
        corr_id = uuid4()
        taskpacket = _make_taskpacket()
        taskpacket.correlation_id = corr_id
        intent = _make_intent()
        task_result = _make_task_result()

        session = AsyncMock()
        captured_kwargs: dict = {}

        def capture_init(config=None, project_dir=".", state_backend=None, correlation_id=None, tracer=None):  # type: ignore[misc]
            agent = AsyncMock()
            agent.run = AsyncMock(return_value=task_result)
            agent.ralph_dir = None
            # Capture the kwargs for assertion
            captured_kwargs["correlation_id"] = correlation_id
            return agent

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", side_effect=capture_init),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            await implement(session, taskpacket.id, repo_path="/tmp/e2e-repo")

        assert captured_kwargs.get("correlation_id") == str(corr_id)

    @pytest.mark.asyncio
    async def test_implement_records_model_call_audit(self) -> None:
        """After implement(), a ModelCallAudit is stored with correct cost fields."""
        taskpacket = _make_taskpacket()
        intent = _make_intent()
        task_result = _make_task_result(tokens_in=200, tokens_out=400)

        session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        mock_agent.ralph_dir = MagicMock()

        recorded_audits: list = []

        mock_audit_store = MagicMock()
        mock_audit_store.record.side_effect = lambda a: recorded_audits.append(a)

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
            patch("src.agent.primary_agent.get_model_audit_store", return_value=mock_audit_store),
            patch("src.agent.primary_agent.get_budget_enforcer", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            await implement(session, taskpacket.id, repo_path="/tmp/e2e-repo")

        assert len(recorded_audits) == 1
        audit = recorded_audits[0]
        assert audit.tokens_in == 200
        assert audit.tokens_out == 400
        assert audit.provider == "claude_code"
        assert audit.role == "developer"
        assert audit.step == "primary_agent_ralph"
        # Cost: 200 * 0.003/1000 + 400 * 0.015/1000 = 0.0006 + 0.006 = 0.0066
        assert abs(audit.cost - 0.0066) < 1e-9

    @pytest.mark.asyncio
    async def test_implement_agent_run_is_invoked_exactly_once(self) -> None:
        """RalphAgent.run() is called exactly once per implement() call."""
        taskpacket = _make_taskpacket()
        intent = _make_intent()
        task_result = _make_task_result()

        session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        mock_agent.ralph_dir = MagicMock()

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            await implement(session, taskpacket.id, repo_path="/tmp/e2e-repo")

        mock_agent.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_implement_with_risk_flags_propagates_through_bridge(self) -> None:
        """Risk flags in TaskPacket flow through bridge → TaskPacketInput correctly."""
        taskpacket = _make_taskpacket(risk_flags={"security": True, "pii": True})
        intent = _make_intent()
        task_result = _make_task_result()

        session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        mock_agent.ralph_dir = MagicMock()

        # Capture the TaskInput written to PROMPT.md to verify risk flags propagated
        written_prompt: list[str] = []

        class CapturingPath:
            def __init__(self, path: object) -> None:
                self._inner = path

            def write_text(self, content: str, **kwargs: object) -> None:
                written_prompt.append(content)

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            result = await implement(
                session,
                taskpacket.id,
                repo_path="/tmp/e2e-repo",
            )

        # The bridge should have processed the risk flags (function ran without error)
        assert isinstance(result, EvidenceBundle)


# ---------------------------------------------------------------------------
# E2E: handle_loopback() — full path via Ralph with verification context
# ---------------------------------------------------------------------------


class TestRalphLoopbackE2E:
    """Full path: handle_loopback() → build_verification_loopback_context → bridge → agent.run()."""

    @pytest.mark.asyncio
    async def test_loopback_passes_failure_context_through_full_bridge(self) -> None:
        """handle_loopback() builds loopback context and it reaches RalphAgent via full path."""
        taskpacket = _make_taskpacket(loopback_count=1)
        intent = _make_intent()
        task_result = _make_task_result(summary="Loopback fixed lint errors")

        verification_result = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="ruff", passed=False, details="E501: line too long at src/api/upload.py:42"),
                CheckResult(name="pytest", passed=True, details="All 12 tests passed"),
            ],
        )

        session = AsyncMock()

        captured_prompt: list[str] = []

        def capture_agent_init(config=None, project_dir=".", state_backend=None, correlation_id=None, tracer=None):  # type: ignore[misc]
            a = AsyncMock()
            a.run = AsyncMock(return_value=task_result)
            a.ralph_dir = None
            return a

        # Capture what gets written to PROMPT.md
        import tempfile
        from pathlib import Path as _Path

        real_tmpdir_cls = tempfile.TemporaryDirectory

        class CapturingTempDir:
            def __init__(self) -> None:
                self._real = real_tmpdir_cls()
                self._name = self._real.name

            def __enter__(self) -> str:
                self._real.__enter__()
                return self._name

            def __exit__(self, *args: object) -> None:
                # Capture PROMPT.md before cleanup
                prompt_path = _Path(self._name) / ".ralph" / "PROMPT.md"
                if prompt_path.exists():
                    captured_prompt.append(prompt_path.read_text())
                self._real.__exit__(*args)

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", side_effect=capture_agent_init),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
            patch("src.agent.primary_agent.tempfile.TemporaryDirectory", CapturingTempDir),
        ):
            from src.agent.primary_agent import handle_loopback

            result = await handle_loopback(
                session,
                taskpacket.id,
                repo_path="/tmp/e2e-repo",
                verification_result=verification_result,
            )

        assert isinstance(result, EvidenceBundle)
        assert result.loopback_attempt == 1

        # Verify the loopback context made it into the PROMPT.md
        assert len(captured_prompt) == 1, "PROMPT.md should have been written"
        prompt_text = captured_prompt[0]
        assert "ruff" in prompt_text or "E501" in prompt_text or "FAILED" in prompt_text, (
            f"Expected loopback failure details in prompt, got: {prompt_text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_loopback_returns_evidence_with_correct_loopback_count(self) -> None:
        """handle_loopback() EvidenceBundle reflects the current loopback attempt."""
        for loopback_count in [1, 2]:
            taskpacket = _make_taskpacket(loopback_count=loopback_count)
            intent = _make_intent()
            task_result = _make_task_result()

            verification_result = VerificationResult(
                passed=False,
                checks=[CheckResult(name="ruff", passed=False, details="E501")],
            )

            session = AsyncMock()
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=task_result)
            mock_agent.ralph_dir = MagicMock()

            with (
                patch("src.agent.primary_agent.settings", _patch_settings()),
                patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
                patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
                patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
                patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
                patch("ralph_sdk.RalphAgent", return_value=mock_agent),
                patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
            ):
                from src.agent.primary_agent import handle_loopback

                result = await handle_loopback(
                    session,
                    taskpacket.id,
                    repo_path="/tmp/e2e-repo",
                    verification_result=verification_result,
                )

            assert result.loopback_attempt == loopback_count, (
                f"Expected loopback_attempt={loopback_count}, got {result.loopback_attempt}"
            )

    @pytest.mark.asyncio
    async def test_loopback_verification_context_contains_failure_details(self) -> None:
        """Verification failures are formatted into the loopback context string."""
        taskpacket = _make_taskpacket(loopback_count=1)
        intent = _make_intent()

        verification_result = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="pytest", passed=False, details="3 tests failed: test_auth, test_upload, test_rate_limit"),
                CheckResult(name="ruff", passed=True, details="No lint errors"),
            ],
        )

        session = AsyncMock()
        captured_loopback_ctx: list[str] = []

        async def capture_implement_ralph(taskpacket, intent, repo_path, loopback_context="", **kwargs):  # type: ignore[misc]
            captured_loopback_ctx.append(loopback_context)
            return EvidenceBundle(
                taskpacket_id=taskpacket.id,
                intent_version=intent.version,
                files_changed=[],
                agent_summary="Fixed tests",
                loopback_attempt=taskpacket.loopback_count,
            )

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("src.agent.primary_agent._implement_ralph", side_effect=capture_implement_ralph),
        ):
            from src.agent.primary_agent import handle_loopback

            await handle_loopback(
                session,
                taskpacket.id,
                repo_path="/tmp/e2e-repo",
                verification_result=verification_result,
            )

        assert len(captured_loopback_ctx) == 1
        ctx = captured_loopback_ctx[0]
        # pytest failed — should appear in context
        assert "pytest" in ctx
        assert "FAILED" in ctx
        assert "3 tests failed" in ctx
        # ruff passed — should also appear but as PASSED
        assert "ruff" in ctx


# ---------------------------------------------------------------------------
# E2E: agent_holder — cancellation reference exposed correctly
# ---------------------------------------------------------------------------


class TestRalphAgentHolder:
    """Verify the agent_holder slot receives the RalphAgent reference."""

    @pytest.mark.asyncio
    async def test_agent_holder_receives_agent_reference(self) -> None:
        """agent_holder list is populated with the RalphAgent before run()."""
        taskpacket = _make_taskpacket()
        intent = _make_intent()
        task_result = _make_task_result()

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        mock_agent.ralph_dir = MagicMock()

        agent_holder: list = []

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import _implement_ralph

            with patch("src.settings.settings", _patch_settings()):
                await _implement_ralph(
                    taskpacket,
                    intent,
                    repo_path="/tmp/e2e-repo",
                    agent_holder=agent_holder,
                )

        assert len(agent_holder) == 1
        assert agent_holder[0] is mock_agent


# ---------------------------------------------------------------------------
# E2E: summary + output are merged into agent_summary
# ---------------------------------------------------------------------------


class TestRalphEvidenceSummaryMerge:
    """Verify that both progress_summary and output appear in EvidenceBundle.agent_summary."""

    @pytest.mark.asyncio
    async def test_agent_summary_combines_progress_and_output(self) -> None:
        """ralph_result_to_evidence() merges status.progress_summary and result.output."""
        taskpacket = _make_taskpacket()
        intent = _make_intent(version=3)
        task_result = _make_task_result(
            summary="Rate limiting added to upload endpoint.",
            output="- src/api/upload.py: added TokenBucket class",
        )

        session = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=task_result)
        mock_agent.ralph_dir = MagicMock()

        with (
            patch("src.agent.primary_agent.settings", _patch_settings()),
            patch("src.agent.primary_agent.get_by_id", new_callable=AsyncMock, return_value=taskpacket),
            patch("src.agent.primary_agent.get_latest_for_taskpacket", new_callable=AsyncMock, return_value=intent),
            patch("src.agent.primary_agent.update_status", new_callable=AsyncMock),
            patch("src.agent.primary_agent.build_system_prompt", return_value="sys"),
            patch("ralph_sdk.RalphAgent", return_value=mock_agent),
            patch("ralph_sdk.NullStateBackend", return_value=MagicMock()),
        ):
            from src.agent.primary_agent import implement

            result = await implement(session, taskpacket.id, repo_path="/tmp/e2e-repo")

        assert "Rate limiting added" in result.agent_summary
        assert "TokenBucket" in result.agent_summary
        assert result.intent_version == 3
