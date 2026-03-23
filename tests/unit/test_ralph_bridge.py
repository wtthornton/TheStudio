"""Unit tests for src/agent/ralph_bridge.py — Epic 43 Story 43.5.

Tests all five bridge functions:
  - taskpacket_to_ralph_input
  - ralph_result_to_evidence
  - build_ralph_config
  - check_ralph_cli_available
  - build_verification_loopback_context
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from ralph_sdk.converters import ComplexityBand, TrustTier
from ralph_sdk.status import RalphLoopStatus, RalphStatus, WorkType

from src.agent.ralph_bridge import (
    build_ralph_config,
    build_verification_loopback_context,
    check_ralph_cli_available,
    ralph_result_to_evidence,
    taskpacket_to_ralph_input,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_taskpacket(
    *,
    taskpacket_id: UUID | None = None,
    loopback_count: int = 0,
    complexity_index: dict | None = None,
    risk_flags: dict | None = None,
    task_trust_tier: object = None,
    correlation_id: UUID | None = None,
) -> MagicMock:
    """Create a minimal mock TaskPacketRow for bridge tests."""
    tp = MagicMock()
    tp.id = taskpacket_id or uuid4()
    tp.loopback_count = loopback_count
    tp.complexity_index = complexity_index
    tp.risk_flags = risk_flags or {}
    tp.task_trust_tier = task_trust_tier
    tp.correlation_id = correlation_id or uuid4()
    tp.repo = "owner/repo"
    tp.issue_id = 42
    return tp


def _make_intent(
    *,
    version: int = 1,
    goal: str = "Implement the feature",
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> MagicMock:
    """Create a minimal mock IntentSpecRead for bridge tests."""
    intent = MagicMock()
    intent.version = version
    intent.goal = goal
    intent.constraints = constraints or ["Must not break existing tests"]
    intent.acceptance_criteria = acceptance_criteria or ["All tests pass"]
    intent.non_goals = non_goals or ["Do not add new dependencies"]
    return intent


def _make_task_result(
    *,
    output: str = "- src/agent/primary_agent.py: refactored",
    progress_summary: str = "Completed implementation",
    exit_signal: bool = True,
    loop_count: int = 3,
    duration_seconds: float = 12.5,
) -> MagicMock:
    """Create a minimal mock TaskResult for bridge tests."""
    result = MagicMock()
    result.output = output
    result.status = RalphStatus(
        progress_summary=progress_summary,
        exit_signal=exit_signal,
        status=RalphLoopStatus.COMPLETED,
        work_type=WorkType.IMPLEMENTATION,
        loop_count=loop_count,
    )
    result.loop_count = loop_count
    result.duration_seconds = duration_seconds
    result.error = ""
    return result


# ---------------------------------------------------------------------------
# taskpacket_to_ralph_input
# ---------------------------------------------------------------------------


class TestTaskpacketToRalphInput:
    def test_maps_goal(self) -> None:
        tp = _make_taskpacket()
        intent = _make_intent(goal="Add rate limiting to the API")
        packet, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.goal == "Add rate limiting to the API"

    def test_maps_constraints(self) -> None:
        tp = _make_taskpacket()
        intent = _make_intent(constraints=["Must be backward compatible", "No new deps"])
        packet, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert "Must be backward compatible" in intent_input.constraints
        assert "No new deps" in intent_input.constraints

    def test_maps_acceptance_criteria(self) -> None:
        tp = _make_taskpacket()
        intent = _make_intent(acceptance_criteria=["All tests green", "Coverage >= 80%"])
        packet, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.acceptance_criteria == ["All tests green", "Coverage >= 80%"]

    def test_maps_non_goals(self) -> None:
        tp = _make_taskpacket()
        intent = _make_intent(non_goals=["Do not refactor unrelated code"])
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert "Do not refactor unrelated code" in intent_input.non_goals

    def test_maps_complexity_high(self) -> None:
        tp = _make_taskpacket(complexity_index={"band": "high", "score": 0.9})
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.complexity == ComplexityBand.HIGH

    def test_maps_complexity_low_via_hint(self) -> None:
        tp = _make_taskpacket(complexity_index=None)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent, complexity_hint="low")
        assert intent_input.complexity == ComplexityBand.LOW

    def test_maps_complexity_unknown_when_missing(self) -> None:
        tp = _make_taskpacket(complexity_index=None)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.complexity == ComplexityBand.UNKNOWN

    def test_maps_trust_tier_execute(self) -> None:
        from src.models.taskpacket import TaskTrustTier

        tp = _make_taskpacket(task_trust_tier=TaskTrustTier.EXECUTE)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.trust_tier == TrustTier.FULL

    def test_maps_trust_tier_suggest(self) -> None:
        from src.models.taskpacket import TaskTrustTier

        tp = _make_taskpacket(task_trust_tier=TaskTrustTier.SUGGEST)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.trust_tier == TrustTier.STANDARD

    def test_maps_trust_tier_observe(self) -> None:
        from src.models.taskpacket import TaskTrustTier

        tp = _make_taskpacket(task_trust_tier=TaskTrustTier.OBSERVE)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.trust_tier == TrustTier.RESTRICTED

    def test_maps_trust_tier_none_to_standard(self) -> None:
        tp = _make_taskpacket(task_trust_tier=None)
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        assert intent_input.trust_tier == TrustTier.STANDARD

    def test_maps_risk_flags_to_risk_flag_objects(self) -> None:
        tp = _make_taskpacket(risk_flags={"security_sensitive": True, "low_risk": False})
        intent = _make_intent()
        _, intent_input = taskpacket_to_ralph_input(tp, intent)
        flag_categories = [rf.category for rf in intent_input.risk_flags]
        # Only True flags should be included
        assert "security_sensitive" in flag_categories
        assert "low_risk" not in flag_categories

    def test_packet_id_is_taskpacket_uuid_string(self) -> None:
        tp_id = uuid4()
        tp = _make_taskpacket(taskpacket_id=tp_id)
        intent = _make_intent()
        packet, _ = taskpacket_to_ralph_input(tp, intent)
        assert packet.id == str(tp_id)

    def test_loopback_context_passed_through(self) -> None:
        tp = _make_taskpacket()
        intent = _make_intent()
        packet, _ = taskpacket_to_ralph_input(tp, intent, loopback_context="## Failed checks")
        assert packet.loopback_context == "## Failed checks"

    def test_loopback_attempt_from_taskpacket(self) -> None:
        tp = _make_taskpacket(loopback_count=2)
        intent = _make_intent()
        packet, _ = taskpacket_to_ralph_input(tp, intent)
        assert packet.loopback_attempt == 2


# ---------------------------------------------------------------------------
# ralph_result_to_evidence
# ---------------------------------------------------------------------------


class TestRalphResultToEvidence:
    def test_taskpacket_id_preserved(self) -> None:
        tp_id = uuid4()
        result = _make_task_result()
        bundle = ralph_result_to_evidence(result, tp_id, intent_version=1, loopback_attempt=0)
        assert bundle.taskpacket_id == tp_id

    def test_intent_version_preserved(self) -> None:
        result = _make_task_result()
        bundle = ralph_result_to_evidence(result, uuid4(), intent_version=3, loopback_attempt=0)
        assert bundle.intent_version == 3

    def test_loopback_attempt_preserved(self) -> None:
        result = _make_task_result()
        bundle = ralph_result_to_evidence(result, uuid4(), intent_version=1, loopback_attempt=2)
        assert bundle.loopback_attempt == 2

    def test_files_changed_extracted_from_output(self) -> None:
        result = _make_task_result(
            output=(
                "Changes made:\n"
                "- src/agent/primary_agent.py: refactored\n"
                "- tests/unit/test_primary_agent.py: updated\n"
            )
        )
        bundle = ralph_result_to_evidence(result, uuid4(), intent_version=1, loopback_attempt=0)
        assert "src/agent/primary_agent.py" in bundle.files_changed
        assert "tests/unit/test_primary_agent.py" in bundle.files_changed

    def test_agent_summary_includes_progress_summary(self) -> None:
        result = _make_task_result(progress_summary="All tasks complete", output="")
        bundle = ralph_result_to_evidence(result, uuid4(), intent_version=1, loopback_attempt=0)
        assert "All tasks complete" in bundle.agent_summary

    def test_agent_summary_includes_output(self) -> None:
        result = _make_task_result(progress_summary="", output="Implemented rate limiting")
        bundle = ralph_result_to_evidence(result, uuid4(), intent_version=1, loopback_attempt=0)
        assert "Implemented rate limiting" in bundle.agent_summary

    def test_uuid_type_correct(self) -> None:
        tp_id = uuid4()
        result = _make_task_result()
        bundle = ralph_result_to_evidence(result, tp_id, intent_version=1, loopback_attempt=0)
        assert isinstance(bundle.taskpacket_id, UUID)


# ---------------------------------------------------------------------------
# build_ralph_config
# ---------------------------------------------------------------------------


class TestBuildRalphConfig:
    def test_returns_ralph_config(self) -> None:
        from ralph_sdk.config import RalphConfig

        config = build_ralph_config()
        assert isinstance(config, RalphConfig)

    def test_project_name_is_thestudio(self) -> None:
        config = build_ralph_config()
        assert config.project_name == "thestudio-task"

    def test_max_turns_scaled_by_complexity_high(self) -> None:
        config = build_ralph_config(max_turns=20, complexity=ComplexityBand.HIGH)
        # HIGH complexity -> 50 turns (from COMPLEXITY_MAX_TURNS); max(20, 50) = 50
        assert config.max_turns == 50

    def test_max_turns_uses_caller_value_when_higher(self) -> None:
        config = build_ralph_config(max_turns=60, complexity=ComplexityBand.LOW)
        # LOW complexity -> 20 turns; max(60, 20) = 60
        assert config.max_turns == 60

    def test_session_continuity_enabled(self) -> None:
        config = build_ralph_config()
        assert config.session_continuity is True

    def test_output_format_json(self) -> None:
        config = build_ralph_config()
        assert config.output_format == "json"


# ---------------------------------------------------------------------------
# check_ralph_cli_available
# ---------------------------------------------------------------------------


class TestCheckRalphCliAvailable:
    def test_returns_true_when_claude_in_path(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            assert check_ralph_cli_available() is True

    def test_returns_false_when_claude_not_in_path(self) -> None:
        with patch("shutil.which", return_value=None):
            assert check_ralph_cli_available() is False


# ---------------------------------------------------------------------------
# build_verification_loopback_context
# ---------------------------------------------------------------------------


class TestBuildVerificationLoopbackContext:
    def _make_verification_result(
        self, checks: list[tuple[str, bool, str]]
    ) -> MagicMock:
        """Build a mock VerificationResult from (name, passed, details) tuples."""
        result = MagicMock()
        check_mocks = []
        for name, passed, details in checks:
            c = MagicMock()
            c.name = name
            c.passed = passed
            c.details = details
            check_mocks.append(c)
        result.checks = check_mocks
        return result

    def test_returns_fallback_message_when_no_checks(self) -> None:
        result = MagicMock()
        result.checks = []
        text = build_verification_loopback_context(result)
        assert "no check details" in text.lower()

    def test_includes_failed_check_name(self) -> None:
        result = self._make_verification_result(
            [("ruff", False, "E501: line too long")]
        )
        text = build_verification_loopback_context(result)
        assert "ruff" in text
        assert "FAILED" in text

    def test_includes_passed_check_name(self) -> None:
        result = self._make_verification_result(
            [("pytest", True, "All 42 tests passed")]
        )
        text = build_verification_loopback_context(result)
        assert "pytest" in text
        assert "PASSED" in text

    def test_includes_check_details(self) -> None:
        result = self._make_verification_result(
            [("security", False, "B101: assert detected in non-test code")]
        )
        text = build_verification_loopback_context(result)
        assert "B101" in text

    def test_multiple_checks_all_appear(self) -> None:
        result = self._make_verification_result(
            [
                ("ruff", False, "E501 error"),
                ("pytest", True, "Tests pass"),
                ("security", False, "Bandit warning"),
            ]
        )
        text = build_verification_loopback_context(result)
        assert "ruff" in text
        assert "pytest" in text
        assert "security" in text
