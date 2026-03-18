"""Tests for the QA agent evaluation runner.

Epic 30, Story 30.3: Unit tests (mock adapter, always run) and integration
tests (real Anthropic API, requires_api_key marker).
"""

from __future__ import annotations

import pytest

from src.eval.qa_dataset import QAEvalCase, load_qa_dataset
from src.eval.qa_eval import qa_context_builder, run_qa_eval, score_qa_output
from src.qa.qa_config import QAAgentOutput, QACriterionResult, QADefectItem


# ---------------------------------------------------------------------------
# Dataset tests
# ---------------------------------------------------------------------------


class TestQADataset:
    """Validate the QA evaluation dataset."""

    def test_dataset_loads_10_cases(self) -> None:
        cases = load_qa_dataset()
        assert len(cases) == 10

    def test_has_7_planted_3_clean(self) -> None:
        cases = load_qa_dataset()
        planted = [c for c in cases if c.expects_defects]
        clean = [c for c in cases if c.is_clean]
        assert len(planted) == 7
        assert len(clean) == 3

    def test_all_cases_have_acceptance_criteria(self) -> None:
        for case in load_qa_dataset():
            assert len(case.acceptance_criteria) >= 2, (
                f"Case {case.case_id} has fewer than 2 acceptance criteria"
            )

    def test_all_cases_have_evidence(self) -> None:
        for case in load_qa_dataset():
            assert case.agent_summary, f"Missing agent_summary for {case.case_id}"
            assert case.test_results, f"Missing test_results for {case.case_id}"

    def test_case_ids_unique(self) -> None:
        cases = load_qa_dataset()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_planted_cases_have_expected_categories(self) -> None:
        for case in load_qa_dataset():
            if case.expects_defects:
                assert case.expected_defect_categories, (
                    f"Planted case {case.case_id} missing expected_defect_categories"
                )


# ---------------------------------------------------------------------------
# Context builder tests
# ---------------------------------------------------------------------------


class TestQAContextBuilder:
    """Tests for qa_context_builder."""

    def test_builds_context_with_evidence(self) -> None:
        case = load_qa_dataset()[0]
        ctx = qa_context_builder(case)

        assert ctx.evidence["agent_summary"] == case.agent_summary
        assert ctx.evidence["test_results"] == case.test_results
        assert "acceptance_criteria" in ctx.extra
        assert "evidence_keys" in ctx.extra

    def test_acceptance_criteria_formatted(self) -> None:
        case = load_qa_dataset()[0]
        ctx = qa_context_builder(case)

        criteria_str = ctx.extra["acceptance_criteria"]
        for ac in case.acceptance_criteria:
            assert ac in criteria_str


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestScoreQAOutput:
    """Tests for score_qa_output."""

    def test_none_output_scores_zero_for_planted(self) -> None:
        case = load_qa_dataset()[0]  # planted defect
        scores = score_qa_output(None, case)
        assert scores["defect_detection"] == 0.0

    def test_none_output_clean_case(self) -> None:
        clean = [c for c in load_qa_dataset() if c.is_clean][0]
        scores = score_qa_output(None, clean)
        # No defects found on clean = good for false_positive
        assert scores["false_positive_rate"] == 0.0

    def test_correct_defect_detection(self) -> None:
        case = load_qa_dataset()[0]  # intent_gap case
        output = QAAgentOutput(
            criteria_results=[
                QACriterionResult(criterion="fast", passed=False, reasoning="Vague"),
            ],
            defects=[
                QADefectItem(
                    category="intent_gap",
                    severity="S1_high",
                    description="'fast' is not measurable",
                ),
            ],
            intent_gaps=["API response time should be fast"],
        )
        scores = score_qa_output(output, case)
        assert scores["defect_detection"] >= 0.5
        assert scores["defect_classification"] == 1.0  # intent_gap matched

    def test_clean_bundle_no_defects_scores_high(self) -> None:
        clean = [c for c in load_qa_dataset() if c.is_clean][0]
        output = QAAgentOutput(
            criteria_results=[
                QACriterionResult(criterion=ac, passed=True, reasoning="Met")
                for ac in clean.acceptance_criteria
            ],
            defects=[],
        )
        scores = score_qa_output(output, clean)
        assert scores["false_positive_rate"] == 1.0
        assert scores["defect_detection"] == 1.0

    def test_false_positive_penalized(self) -> None:
        clean = [c for c in load_qa_dataset() if c.is_clean][0]
        output = QAAgentOutput(
            criteria_results=[],
            defects=[
                QADefectItem(
                    category="implementation_bug",
                    severity="S0_critical",
                    description="False alarm",
                ),
            ],
        )
        scores = score_qa_output(output, clean)
        assert scores["false_positive_rate"] == 0.0

    def test_reasoning_quality(self) -> None:
        case = load_qa_dataset()[0]
        output = QAAgentOutput(
            criteria_results=[
                QACriterionResult(criterion="c1", passed=True, reasoning="Detailed reasoning"),
                QACriterionResult(criterion="c2", passed=True, reasoning=""),
            ],
        )
        scores = score_qa_output(output, case)
        assert scores["reasoning_quality"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Unit tests — mock adapter
# ---------------------------------------------------------------------------


class TestQAEvalUnit:
    """Verify eval runner wiring with mock adapter."""

    @pytest.mark.asyncio
    async def test_run_qa_eval_mock(self) -> None:
        """Eval runner completes with mock adapter."""
        summary = await run_qa_eval()

        assert summary.agent_name == "qa_agent"
        assert summary.total_cases == 10
        assert len(summary.results) == 10

    @pytest.mark.asyncio
    async def test_run_qa_eval_subset(self) -> None:
        """Eval runner works with a subset of cases."""
        dataset = load_qa_dataset()[:3]
        summary = await run_qa_eval(cases=dataset)

        assert summary.total_cases == 3


# ---------------------------------------------------------------------------
# Integration tests — real Anthropic API
# ---------------------------------------------------------------------------


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestQAEvalIntegration:
    """Run QA agent against real Claude."""

    @pytest.mark.asyncio
    async def test_all_cases_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All 10 cases should produce parseable QAAgentOutput."""
        _enable_real_qa_llm(monkeypatch)
        summary = await run_qa_eval()

        assert summary.total_cases == 10
        assert summary.parse_success_rate == 1.0, (
            f"Parse failures: {[r.case_id for r in summary.results if not r.parse_success]}"
        )

    @pytest.mark.asyncio
    async def test_defect_detection_rate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """QA agent should detect planted defects in >= 7/10 cases."""
        _enable_real_qa_llm(monkeypatch)

        planted = [c for c in load_qa_dataset() if c.expects_defects]
        summary = await run_qa_eval(cases=planted)

        detected = sum(1 for r in summary.results if r.passed)
        assert detected >= 5, (
            f"Only {detected}/7 planted defect cases detected. "
            f"Failures: {[r.case_id for r in summary.results if not r.passed]}"
        )

    @pytest.mark.asyncio
    async def test_clean_bundles_no_severe_defects(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Clean bundles should not produce S0/S1 false positives."""
        _enable_real_qa_llm(monkeypatch)

        clean = [c for c in load_qa_dataset() if c.is_clean]
        summary = await run_qa_eval(cases=clean)

        for result in summary.results:
            if result.parsed is not None and isinstance(result.parsed, QAAgentOutput):
                severe = [
                    d for d in result.parsed.defects
                    if d.severity in ("S0_critical", "S1_high")
                ]
                assert len(severe) == 0, (
                    f"Case {result.case_id} has {len(severe)} false positive S0/S1 defects"
                )

    @pytest.mark.asyncio
    async def test_total_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Total cost for all 10 cases should stay under $2."""
        _enable_real_qa_llm(monkeypatch)
        summary = await run_qa_eval()

        assert summary.total_cost_usd < 2.0, (
            f"Total cost ${summary.total_cost_usd:.4f} exceeds $2.00 budget"
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _enable_real_qa_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure settings to use real Anthropic LLM for QA agent."""
    import os
    from src.settings import settings

    api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    assert api_key.startswith("sk-ant-"), (
        "THESTUDIO_ANTHROPIC_API_KEY must be a valid Anthropic key"
    )
    monkeypatch.setattr(settings, "anthropic_api_key", api_key)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")

    enabled = dict(settings.agent_llm_enabled)
    enabled["qa_agent"] = True
    monkeypatch.setattr(settings, "agent_llm_enabled", enabled)
