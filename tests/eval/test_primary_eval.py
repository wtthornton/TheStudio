"""Tests for the primary agent evaluation runner.

Epic 30, Story 30.4: Unit tests (mock adapter, always run) and integration
tests (real Anthropic API, requires_api_key marker).
"""

from __future__ import annotations

import pytest

from src.eval.dataset import load_intent_dataset
from src.eval.primary_eval import (
    primary_context_builder,
    run_primary_eval,
    score_primary_raw,
    _SIMPLE_CASE_IDS,
)


# ---------------------------------------------------------------------------
# Dataset selection tests
# ---------------------------------------------------------------------------


class TestPrimaryDataset:
    """Validate the primary eval dataset selection."""

    def test_selects_3_simple_cases(self) -> None:
        all_cases = load_intent_dataset()
        selected = [c for c in all_cases if c.case_id in _SIMPLE_CASE_IDS]
        assert len(selected) == 3

    def test_selected_cases_are_low_or_medium_complexity(self) -> None:
        all_cases = load_intent_dataset()
        selected = [c for c in all_cases if c.case_id in _SIMPLE_CASE_IDS]
        for case in selected:
            assert case.complexity in ("low", "medium"), (
                f"Case {case.case_id} has complexity {case.complexity}"
            )


# ---------------------------------------------------------------------------
# Context builder tests
# ---------------------------------------------------------------------------


class TestPrimaryContextBuilder:
    """Tests for primary_context_builder."""

    def test_builds_context_with_prompts(self) -> None:
        case = load_intent_dataset()[0]  # bug_fix_01
        ctx = primary_context_builder(case)

        assert "system_prompt" in ctx.extra
        assert "user_prompt" in ctx.extra
        assert case.issue_title in ctx.extra["user_prompt"]


# ---------------------------------------------------------------------------
# Raw output scoring tests
# ---------------------------------------------------------------------------


class TestScorePrimaryRaw:
    """Tests for score_primary_raw."""

    def test_empty_output_scores_zero(self) -> None:
        case = load_intent_dataset()[0]
        scores = score_primary_raw("", case)
        assert all(v == 0.0 for v in scores.values())

    def test_valid_json_scores_high(self) -> None:
        import json
        case = load_intent_dataset()[0]  # avatar bug
        output = json.dumps({
            "agent_summary": "Fix UserProfile.avatar_url to return Gravatar fallback URL when no custom avatar is set",
            "file_changes": ["src/models/user_profile.py", "tests/models/test_user_profile.py"],
            "approach": "Add a default Gravatar URL computed from MD5 hash of the user email",
            "risks": ["MD5 is weak for security but standard for Gravatar"],
            "estimated_complexity": "low",
        })
        scores = score_primary_raw(output, case)
        assert scores["has_summary"] == 1.0
        assert scores["has_file_changes"] == 1.0
        assert scores["coherence"] > 0.2

    def test_no_file_changes_penalized(self) -> None:
        import json
        case = load_intent_dataset()[0]
        output = json.dumps({
            "agent_summary": "Would fix the avatar URL issue",
            "file_changes": [],
        })
        scores = score_primary_raw(output, case)
        assert scores["has_file_changes"] == 0.0

    def test_wrapped_json_extracted(self) -> None:
        import json
        case = load_intent_dataset()[0]
        inner = json.dumps({
            "agent_summary": "Fix the avatar URL to return a Gravatar fallback for default users",
            "file_changes": ["src/models/user_profile.py"],
            "approach": "Add Gravatar URL generation based on email hash",
        })
        output = f"Here's my implementation plan:\n\n{inner}\n\nLet me know if you need changes."
        scores = score_primary_raw(output, case)
        assert scores["has_summary"] == 1.0


# ---------------------------------------------------------------------------
# Unit tests — mock adapter
# ---------------------------------------------------------------------------


class TestPrimaryEvalUnit:
    """Verify eval runner wiring with mock adapter."""

    @pytest.mark.asyncio
    async def test_run_primary_eval_mock(self) -> None:
        """Eval runner completes with mock adapter."""
        summary = await run_primary_eval()

        assert summary.agent_name == "developer"
        assert summary.total_cases == 3
        assert len(summary.results) == 3

    @pytest.mark.asyncio
    async def test_mock_cost_is_minimal(self) -> None:
        """Mock adapter should have negligible cost."""
        summary = await run_primary_eval()
        assert summary.total_cost_usd < 0.10


# ---------------------------------------------------------------------------
# Integration tests — real Anthropic API
# ---------------------------------------------------------------------------


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestPrimaryEvalIntegration:
    """Run primary agent against real Claude."""

    @pytest.mark.asyncio
    async def test_all_cases_produce_output(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All 3 cases should produce non-empty output."""
        _enable_real_primary_llm(monkeypatch)
        summary = await run_primary_eval()

        assert summary.total_cases == 3
        for result in summary.results:
            assert result.raw_output.strip(), (
                f"Case {result.case_id} produced empty output"
            )

    @pytest.mark.asyncio
    async def test_summaries_are_coherent(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All 3 cases should produce coherent summaries."""
        _enable_real_primary_llm(monkeypatch)
        summary = await run_primary_eval()

        assert summary.passed_count >= 2, (
            f"Only {summary.passed_count}/3 passed. "
            f"Failures: {[r.case_id for r in summary.results if not r.passed]}"
        )

    @pytest.mark.asyncio
    async def test_file_changes_suggested(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """At least 2/3 cases should suggest file changes."""
        _enable_real_primary_llm(monkeypatch)
        summary = await run_primary_eval()

        with_files = 0
        for result in summary.results:
            case = [c for c in load_intent_dataset() if c.case_id == result.case_id]
            if case:
                scores = score_primary_raw(result.raw_output, case[0])
                if scores["has_file_changes"] > 0:
                    with_files += 1

        assert with_files >= 2, f"Only {with_files}/3 suggested file changes"

    @pytest.mark.asyncio
    async def test_total_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Total cost for 3 cases should stay under $5."""
        _enable_real_primary_llm(monkeypatch)
        summary = await run_primary_eval()

        assert summary.total_cost_usd < 5.0, (
            f"Total cost ${summary.total_cost_usd:.4f} exceeds $5.00 budget"
        )

    @pytest.mark.asyncio
    async def test_no_timeouts(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No case should take longer than 120s."""
        _enable_real_primary_llm(monkeypatch)
        summary = await run_primary_eval()

        for result in summary.results:
            assert result.duration_ms < 120_000, (
                f"Case {result.case_id} timed out: {result.duration_ms}ms"
            )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _enable_real_primary_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure settings to use real Anthropic LLM for primary agent."""
    import os
    from src.settings import settings

    api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    assert api_key.startswith("sk-ant-"), (
        "THESTUDIO_ANTHROPIC_API_KEY must be a valid Anthropic key"
    )
    monkeypatch.setattr(settings, "anthropic_api_key", api_key)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")

    enabled = dict(settings.agent_llm_enabled)
    enabled["developer"] = True
    monkeypatch.setattr(settings, "agent_llm_enabled", enabled)
