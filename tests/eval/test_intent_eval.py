"""Tests for the intent agent evaluation runner.

Epic 30, Story 30.2: Unit tests (mock adapter, always run) and integration
tests (real Anthropic API, requires_api_key marker).
"""

from __future__ import annotations

import pytest

from src.eval.dataset import load_intent_dataset
from src.eval.intent_eval import run_intent_eval
from src.intent.intent_config import IntentAgentOutput


# ---------------------------------------------------------------------------
# Unit tests — mock adapter, no API key required
# ---------------------------------------------------------------------------


class TestIntentEvalUnit:
    """Verify eval runner wiring with mock adapter (default settings)."""

    @pytest.mark.asyncio
    async def test_run_intent_eval_mock(self) -> None:
        """Eval runner completes with mock adapter and returns a summary."""
        summary = await run_intent_eval()

        assert summary.agent_name == "intent_agent"
        assert summary.total_cases == 10
        # Mock adapter returns canned text, so parse will fail (no JSON)
        # but the harness should still produce results without crashing
        assert len(summary.results) == 10

    @pytest.mark.asyncio
    async def test_run_intent_eval_subset(self) -> None:
        """Eval runner works with a subset of cases."""
        dataset = load_intent_dataset()[:3]
        summary = await run_intent_eval(cases=dataset)

        assert summary.total_cases == 3
        assert len(summary.results) == 3

    @pytest.mark.asyncio
    async def test_mock_results_have_zero_cost(self) -> None:
        """Mock adapter should report minimal/zero cost."""
        summary = await run_intent_eval()

        # Mock adapter estimates cost from token approximation, should be tiny
        assert summary.total_cost_usd < 0.10


# ---------------------------------------------------------------------------
# Integration tests — real Anthropic API
# ---------------------------------------------------------------------------


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestIntentEvalIntegration:
    """Run intent agent against real Claude. Requires THESTUDIO_ANTHROPIC_API_KEY."""

    @pytest.mark.asyncio
    async def test_all_cases_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All 10 cases should produce parseable IntentAgentOutput."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        assert summary.total_cases == 10
        assert summary.parse_success_rate == 1.0, (
            f"Parse failures: {[r.case_id for r in summary.results if not r.parse_success]}"
        )

        # Verify parsed outputs are IntentAgentOutput instances
        for result in summary.results:
            assert result.parsed is not None, f"Case {result.case_id} has no parsed output"
            assert isinstance(result.parsed, IntentAgentOutput), (
                f"Case {result.case_id} parsed to {type(result.parsed)}"
            )

    @pytest.mark.asyncio
    async def test_pass_rate_at_least_8_of_10(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """At least 8/10 cases should produce valid intent specs (AC target)."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        assert summary.passed_count >= 8, (
            f"Only {summary.passed_count}/10 passed. "
            f"Failures: {[r.case_id for r in summary.results if not r.passed]}"
        )

    @pytest.mark.asyncio
    async def test_goal_non_empty_all_cases(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Every case should produce a non-empty goal with relevant keywords."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        for result in summary.results:
            assert result.parse_success, f"Case {result.case_id} failed to parse"
            assert result.parsed is not None
            assert result.parsed.goal.strip(), f"Case {result.case_id} has empty goal"

        # At least 8/10 should have good goal clarity
        good_goals = sum(1 for r in summary.results if r.goal_clarity >= 0.5)
        assert good_goals >= 8, f"Only {good_goals}/10 have adequate goal clarity"

    @pytest.mark.asyncio
    async def test_constraints_non_empty(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """At least 9/10 cases should produce non-empty constraints."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        with_constraints = sum(
            1 for r in summary.results
            if r.parse_success and r.parsed is not None and len(r.parsed.constraints) > 0
        )
        assert with_constraints >= 9, (
            f"Only {with_constraints}/10 have constraints. "
            f"Missing: {[r.case_id for r in summary.results if r.parsed and not r.parsed.constraints]}"
        )

    @pytest.mark.asyncio
    async def test_invariants_for_breaking_changes(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Breaking-change cases should produce non-empty invariants."""
        _enable_real_llm(monkeypatch)

        dataset = load_intent_dataset()
        breaking_cases = [c for c in dataset if c.expects_invariants]
        summary = await run_intent_eval(cases=breaking_cases)

        for result in summary.results:
            assert result.parse_success, f"Case {result.case_id} failed to parse"
            assert result.parsed is not None
            assert len(result.parsed.invariants) > 0, (
                f"Case {result.case_id} expects invariants but got none"
            )

    @pytest.mark.asyncio
    async def test_acs_are_specific(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ACs should be specific (not just restating the title)."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        good_acs = sum(1 for r in summary.results if r.ac_completeness >= 0.4)
        assert good_acs >= 8, (
            f"Only {good_acs}/10 have adequate AC completeness. "
            f"Low scorers: {[(r.case_id, r.ac_completeness) for r in summary.results if r.ac_completeness < 0.4]}"
        )

    @pytest.mark.asyncio
    async def test_total_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Total cost for all 10 cases should stay under $2."""
        _enable_real_llm(monkeypatch)

        summary = await run_intent_eval()

        assert summary.total_cost_usd < 2.0, (
            f"Total cost ${summary.total_cost_usd:.4f} exceeds $2.00 budget"
        )

    @pytest.mark.asyncio
    async def test_detailed_results_logged(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Per-case results should be logged for debugging."""
        _enable_real_llm(monkeypatch)

        with caplog.at_level("INFO", logger="src.eval"):
            summary = await run_intent_eval()

        # Verify logging happened for each case
        for result in summary.results:
            assert any(result.case_id in record.message for record in caplog.records), (
                f"No log entry found for case {result.case_id}"
            )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _enable_real_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure settings to use real Anthropic LLM for intent agent.

    The settings singleton is constructed at import time, so env vars
    sourced after that won't be reflected. We monkeypatch all three
    values: provider, feature flag, and API key.
    """
    import os

    from src.settings import settings

    # The API key may have been sourced into the env after settings init
    api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    assert api_key.startswith("sk-ant-"), (
        "THESTUDIO_ANTHROPIC_API_KEY must be a valid Anthropic key (sk-ant-...)"
    )
    monkeypatch.setattr(settings, "anthropic_api_key", api_key)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")

    # Enable intent agent LLM — create a new dict to avoid mutating the default
    enabled = dict(settings.agent_llm_enabled)
    enabled["intent_agent"] = True
    monkeypatch.setattr(settings, "agent_llm_enabled", enabled)
