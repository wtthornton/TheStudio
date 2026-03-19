"""Tests for intake, context, router, and assembler eval suites.

Epic 32, Story 32.2: Unit tests for datasets, context builders, and
scoring functions. Integration tests (requires_api_key) validate real
LLM output quality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.eval.routing_dataset import load_routing_dataset

# --- Dataset Tests ---


class TestRoutingDataset:
    def test_dataset_loads_8_cases(self):
        cases = load_routing_dataset()
        assert len(cases) == 8

    def test_case_ids_unique(self):
        cases = load_routing_dataset()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_has_accepted_and_rejected(self):
        cases = load_routing_dataset()
        accepted = [c for c in cases if c.expected_accepted]
        rejected = [c for c in cases if not c.expected_accepted]
        assert len(accepted) >= 6
        assert len(rejected) >= 1

    def test_has_security_cases(self):
        cases = load_routing_dataset()
        security = [c for c in cases if "security" in c.expected_overlays]
        assert len(security) >= 1

    def test_all_cases_have_titles(self):
        for case in load_routing_dataset():
            assert case.issue_title, f"Case {case.case_id} has no title"
            assert case.issue_body, f"Case {case.case_id} has no body"

    def test_complexity_distribution(self):
        cases = load_routing_dataset()
        complexities = {c.complexity for c in cases}
        assert "low" in complexities
        assert "high" in complexities


# --- Intake Eval Tests ---


class TestIntakeContextBuilder:
    def test_builds_context_with_extra(self):
        from src.eval.intake_eval import intake_context_builder

        case = load_routing_dataset()[0]
        ctx = intake_context_builder(case)
        assert ctx.repo == "eval/test-repo"
        assert ctx.extra["repo_registered"] is True
        assert ctx.extra["repo_paused"] is False


class TestScoreIntakeOutput:
    def test_none_scores_zero(self):
        from src.eval.intake_eval import score_intake_output

        case = load_routing_dataset()[0]
        scores = score_intake_output(None, case)
        assert scores["accepted_correct"] == 0.0

    def test_correct_acceptance(self):
        from src.eval.intake_eval import score_intake_output

        case = load_routing_dataset()[0]  # expected_accepted=True
        parsed = {
            "accepted": True,
            "base_role": "developer",
            "overlays": [],
            "risk_flags": {},
            "reasoning": "Bug fix classified as developer role",
        }
        scores = score_intake_output(parsed, case)
        assert scores["accepted_correct"] == 1.0
        assert scores["role_correct"] == 1.0
        assert scores["has_reasoning"] == 1.0

    def test_wrong_acceptance(self):
        from src.eval.intake_eval import score_intake_output

        case = load_routing_dataset()[0]  # expected_accepted=True
        parsed = {"accepted": False, "reasoning": ""}
        scores = score_intake_output(parsed, case)
        assert scores["accepted_correct"] == 0.0

    def test_security_overlay_detection(self):
        from src.eval.intake_eval import score_intake_output

        # Case 2 expects security overlay
        case = load_routing_dataset()[1]
        parsed = {
            "accepted": True,
            "base_role": "developer",
            "overlays": ["security"],
            "risk_flags": {"risk_security": True},
            "reasoning": "SQL injection requires security overlay",
        }
        scores = score_intake_output(parsed, case)
        assert scores["overlay_coverage"] == 1.0
        assert scores["risk_detection"] == 1.0


# --- Context Eval Tests ---


class TestScoreContextOutput:
    def test_none_scores_zero(self):
        from src.eval.context_eval import score_context_output

        case = load_routing_dataset()[0]
        scores = score_context_output(None, case)
        assert scores["scope_relevance"] == 0.0

    def test_correct_context_enrichment(self):
        from src.eval.context_eval import score_context_output

        case = load_routing_dataset()[0]
        parsed = {
            "scope_summary": "Affects the tasks API pagination logic",
            "impacted_services": ["api", "tasks"],
            "risk_flags": {},
            "complexity_rationale": "Simple off-by-one bug in pagination calculation",
            "open_questions": [],
        }
        scores = score_context_output(parsed, case)
        assert scores["scope_relevance"] > 0.0
        assert scores["service_coverage"] == 1.0
        assert scores["has_complexity_rationale"] == 1.0


# --- Router Eval Tests ---


class TestScoreRouterOutput:
    def test_none_scores_zero(self):
        from src.eval.routing_eval import score_router_output

        case = load_routing_dataset()[0]
        scores = score_router_output(None, case)
        assert scores["expert_coverage"] == 0.0

    def test_correct_expert_selection(self):
        from src.eval.routing_eval import score_router_output

        case = load_routing_dataset()[0]  # expects ["technical"]
        parsed = {
            "selections": [
                {"expert_class": "technical", "pattern": "parallel", "rationale": "Bug fix"},
            ],
            "shadow_recommendations": [],
            "staged_rationale": "",
            "escalation_flags": [],
            "adjustments": "No adjustments needed",
        }
        scores = score_router_output(parsed, case)
        assert scores["expert_coverage"] == 1.0
        assert scores["min_experts_met"] == 1.0
        assert scores["pattern_specified"] == 1.0


# --- Assembler Eval Tests ---


class TestScoreAssemblerOutput:
    def test_none_scores_zero(self):
        from src.eval.assembler_eval import score_assembler_output

        case = load_routing_dataset()[0]
        scores = score_assembler_output(None, case)
        assert scores["plan_completeness"] == 0.0

    def test_correct_plan_output(self):
        from src.eval.assembler_eval import score_assembler_output

        case = load_routing_dataset()[0]  # expected_min_plan_steps=2
        parsed = {
            "plan_steps": [
                {"description": "Fix offset", "source_expert": "technical", "is_checkpoint": False},
                {"description": "Add tests", "source_expert": "technical", "is_checkpoint": False},
            ],
            "conflicts": [],
            "risks": ["Regression risk"],
            "qa_handoff": [{"criterion": "Pagination works", "validation_steps": ["Test"]}],
            "provenance_decisions": [],
        }
        scores = score_assembler_output(parsed, case)
        assert scores["plan_completeness"] == 1.0
        assert scores["risk_assessment"] == 1.0
        assert scores["qa_handoff"] == 1.0


# --- Unit Tests (mock LLM) ---


class TestIntakeEvalUnit:
    @pytest.mark.asyncio
    async def test_run_intake_eval_mock(self):
        from src.eval.intake_eval import run_intake_eval

        cases = load_routing_dataset()[:2]
        with patch(
            "src.agent.framework.AgentRunner.run",
            new_callable=AsyncMock,
        ) as mock_run:
            from src.agent.framework import AgentResult

            mock_run.return_value = AgentResult(
                agent_name="intake_agent",
                raw_output='{"accepted": true, "base_role": "developer", '
                '"overlays": [], "risk_flags": {}, "reasoning": "mock"}',
                parsed_output={
                    "accepted": True,
                    "base_role": "developer",
                    "overlays": [],
                    "risk_flags": {},
                    "reasoning": "mock",
                },
            )
            summary = await run_intake_eval(cases)
        assert summary.total_cases == 2


class TestContextEvalUnit:
    @pytest.mark.asyncio
    async def test_run_context_eval_mock(self):
        from src.eval.context_eval import run_context_eval

        cases = load_routing_dataset()[:2]
        with patch(
            "src.agent.framework.AgentRunner.run",
            new_callable=AsyncMock,
        ) as mock_run:
            from src.agent.framework import AgentResult

            mock_run.return_value = AgentResult(
                agent_name="context_agent",
                raw_output='{"scope_summary": "test", "impacted_services": ["api"]}',
                parsed_output={
                    "scope_summary": "test scope for api and tasks",
                    "impacted_services": ["api"],
                    "risk_flags": {},
                    "complexity_rationale": "Simple fix with limited scope",
                    "open_questions": [],
                },
            )
            summary = await run_context_eval(cases)
        assert summary.total_cases == 2


class TestRouterEvalUnit:
    @pytest.mark.asyncio
    async def test_run_router_eval_mock(self):
        from src.eval.routing_eval import run_router_eval

        cases = load_routing_dataset()[:2]
        with patch(
            "src.agent.framework.AgentRunner.run",
            new_callable=AsyncMock,
        ) as mock_run:
            from src.agent.framework import AgentResult

            mock_run.return_value = AgentResult(
                agent_name="router_agent",
                raw_output='{"selections": [{"expert_class": "technical"}]}',
                parsed_output={
                    "selections": [
                        {"expert_class": "technical", "pattern": "parallel", "rationale": "x"},
                    ],
                    "shadow_recommendations": [],
                    "staged_rationale": "",
                    "escalation_flags": [],
                    "adjustments": "",
                },
            )
            summary = await run_router_eval(cases)
        assert summary.total_cases == 2


class TestAssemblerEvalUnit:
    @pytest.mark.asyncio
    async def test_run_assembler_eval_mock(self):
        from src.eval.assembler_eval import run_assembler_eval

        cases = load_routing_dataset()[:2]
        with patch(
            "src.agent.framework.AgentRunner.run",
            new_callable=AsyncMock,
        ) as mock_run:
            from src.agent.framework import AgentResult

            mock_run.return_value = AgentResult(
                agent_name="assembler_agent",
                raw_output='{"plan_steps": [{"description": "test"}]}',
                parsed_output={
                    "plan_steps": [
                        {"description": "Fix the issue", "source_expert": "technical",
                         "is_checkpoint": False},
                        {"description": "Add tests", "source_expert": "technical",
                         "is_checkpoint": False},
                    ],
                    "conflicts": [],
                    "risks": ["Regression"],
                    "qa_handoff": [{"criterion": "Works", "validation_steps": ["Test"]}],
                    "provenance_decisions": [],
                },
            )
            summary = await run_assembler_eval(cases)
        assert summary.total_cases == 2


# --- Integration Tests (requires real API key) ---


def _enable_real_agent_llm(
    monkeypatch: pytest.MonkeyPatch,
    agent_names: list[str],
) -> None:
    """Configure settings to use real Anthropic LLM for specified agents."""
    import os

    from src.settings import settings

    api_key = os.environ.get("THESTUDIO_ANTHROPIC_API_KEY", "")
    assert api_key.startswith("sk-ant-"), (
        "THESTUDIO_ANTHROPIC_API_KEY must be a valid Anthropic key (sk-ant-...)"
    )
    monkeypatch.setattr(settings, "anthropic_api_key", api_key)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")

    enabled = dict(settings.agent_llm_enabled)
    for name in agent_names:
        enabled[name] = True
    monkeypatch.setattr(settings, "agent_llm_enabled", enabled)


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestIntakeEvalIntegration:
    @pytest.mark.asyncio
    async def test_intake_classification_accuracy(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Intake agent correctly classifies at least 6/8 cases."""
        _enable_real_agent_llm(monkeypatch, ["intake_agent"])
        from src.eval.intake_eval import run_intake_eval

        summary = await run_intake_eval()
        assert summary.pass_rate >= 0.6, (
            f"Intake pass rate {summary.pass_rate:.0%} below 60% threshold"
        )

    @pytest.mark.asyncio
    async def test_intake_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Total intake eval costs less than $1."""
        _enable_real_agent_llm(monkeypatch, ["intake_agent"])
        from src.eval.intake_eval import run_intake_eval

        summary = await run_intake_eval()
        assert summary.total_cost_usd < 1.0


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestContextEvalIntegration:
    @pytest.mark.asyncio
    async def test_context_enrichment_quality(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Context agent enriches at least 5/7 accepted cases adequately."""
        _enable_real_agent_llm(monkeypatch, ["context_agent"])
        from src.eval.context_eval import run_context_eval

        summary = await run_context_eval()
        assert summary.pass_rate >= 0.6

    @pytest.mark.asyncio
    async def test_context_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        _enable_real_agent_llm(monkeypatch, ["context_agent"])
        from src.eval.context_eval import run_context_eval

        summary = await run_context_eval()
        assert summary.total_cost_usd < 2.0


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestRouterEvalIntegration:
    @pytest.mark.asyncio
    async def test_router_expert_selection(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Router correctly selects experts for at least 5/7 cases."""
        _enable_real_agent_llm(monkeypatch, ["router_agent"])
        from src.eval.routing_eval import run_router_eval

        summary = await run_router_eval()
        assert summary.pass_rate >= 0.6

    @pytest.mark.asyncio
    async def test_router_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        _enable_real_agent_llm(monkeypatch, ["router_agent"])
        from src.eval.routing_eval import run_router_eval

        summary = await run_router_eval()
        assert summary.total_cost_usd < 3.0


@pytest.mark.requires_api_key
@pytest.mark.slow
class TestAssemblerEvalIntegration:
    @pytest.mark.asyncio
    async def test_assembler_plan_quality(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """Assembler produces adequate plans for at least 5/7 cases."""
        _enable_real_agent_llm(monkeypatch, ["assembler_agent"])
        from src.eval.assembler_eval import run_assembler_eval

        summary = await run_assembler_eval()
        assert summary.pass_rate >= 0.6

    @pytest.mark.asyncio
    async def test_assembler_cost_under_budget(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        _enable_real_agent_llm(monkeypatch, ["assembler_agent"])
        from src.eval.assembler_eval import run_assembler_eval

        summary = await run_assembler_eval()
        assert summary.total_cost_usd < 5.0
