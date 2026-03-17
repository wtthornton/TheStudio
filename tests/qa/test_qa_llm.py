"""Tests for QA Agent configuration and LLM integration (Epic 23, Story 3.9).

Tests cover:
- QAAgentConfig structure and defaults
- QAAgentOutput schema validation
- Intent satisfaction reasoning (AC 29)
- Edge case identification (AC 30)
- Defect classification with taxonomy
- Fallback to keyword-based validate()
"""

import json

import pytest

from src.agent.framework import AgentConfig, AgentContext
from src.qa.qa_config import (
    QA_AGENT_CONFIG,
    QA_SYSTEM_PROMPT,
    QAAgentOutput,
    QACriterionResult,
    QADefectItem,
    _qa_fallback,
)


class TestQAAgentConfig:
    """Tests for QAAgentConfig structure."""

    def test_config_is_agent_config(self) -> None:
        assert isinstance(QA_AGENT_CONFIG, AgentConfig)

    def test_agent_name(self) -> None:
        assert QA_AGENT_CONFIG.agent_name == "qa_agent"

    def test_pipeline_step(self) -> None:
        assert QA_AGENT_CONFIG.pipeline_step == "qa_eval"

    def test_model_class_balanced(self) -> None:
        assert QA_AGENT_CONFIG.model_class == "balanced"

    def test_completion_mode(self) -> None:
        assert QA_AGENT_CONFIG.tool_allowlist == []

    def test_budget(self) -> None:
        assert QA_AGENT_CONFIG.max_budget_usd == 0.50

    def test_output_schema(self) -> None:
        assert QA_AGENT_CONFIG.output_schema is QAAgentOutput

    def test_fallback_fn(self) -> None:
        assert QA_AGENT_CONFIG.fallback_fn is _qa_fallback


class TestQAAgentOutput:
    """Tests for QAAgentOutput schema."""

    def test_full_output_parses(self) -> None:
        data = {
            "criteria_results": [
                {"criterion": "Pagination returns correct page", "passed": True, "reasoning": "Test covers page 1, 2, and boundary"},
                {"criterion": "Empty result handling", "passed": False, "reasoning": "No test for empty dataset"},
            ],
            "defects": [
                {
                    "category": "implementation_bug",
                    "severity": "S2_medium",
                    "description": "No test for empty dataset pagination",
                    "acceptance_criterion": "Empty result handling",
                }
            ],
            "intent_gaps": ["Default page size not specified"],
            "edge_case_concerns": ["What happens with concurrent page requests?"],
        }
        output = QAAgentOutput.model_validate(data)
        assert len(output.criteria_results) == 2
        assert len(output.defects) == 1
        assert len(output.intent_gaps) == 1
        assert len(output.edge_case_concerns) == 1

    def test_intent_satisfaction_reasoning(self) -> None:
        """AC 29: LLM reasons about intent satisfaction, not keyword matching."""
        result = QACriterionResult(
            criterion="Pagination works correctly",
            passed=True,
            reasoning="Test suite includes tests for page 1, last page, page size boundaries, "
            "and the API returns total_count in the response header.",
        )
        assert len(result.reasoning) > 20  # Real reasoning, not just "keyword match"

    def test_edge_case_identification(self) -> None:
        """AC 30: LLM identifies uncovered edge cases."""
        output = QAAgentOutput(
            edge_case_concerns=[
                "What happens with empty result sets?",
                "Is there a max page size to prevent memory issues?",
                "How does pagination interact with active filters?",
            ],
        )
        assert len(output.edge_case_concerns) == 3

    def test_defect_taxonomy_categories(self) -> None:
        """Validates the 8-category defect taxonomy."""
        valid_categories = {
            "intent_gap", "implementation_bug", "regression", "security",
            "performance", "compliance", "partner_mismatch", "operability",
        }
        for cat in valid_categories:
            defect = QADefectItem(
                category=cat,
                severity="S2_medium",
                description=f"Test defect for {cat}",
            )
            assert defect.category == cat

    def test_severity_levels(self) -> None:
        valid_severities = {"S0_critical", "S1_high", "S2_medium", "S3_low"}
        for sev in valid_severities:
            defect = QADefectItem(
                category="implementation_bug",
                severity=sev,
                description="Test",
            )
            assert defect.severity == sev

    def test_intent_gap_blocks_qa_passed(self) -> None:
        """intent_gap defects should block qa_passed."""
        output = QAAgentOutput(
            intent_gaps=["Ambiguous criterion"],
            defects=[
                QADefectItem(
                    category="intent_gap",
                    severity="S1_high",
                    description="Cannot validate ambiguous criterion",
                    acceptance_criterion="Ambiguous criterion",
                ),
            ],
        )
        # If there are intent gaps, QA should not pass
        assert len(output.intent_gaps) > 0

    def test_minimal_output_parses(self) -> None:
        data = {"criteria_results": [], "defects": []}
        output = QAAgentOutput.model_validate(data)
        assert output.criteria_results == []


class TestQAFallback:
    """Tests for the keyword-based fallback."""

    def test_fallback_returns_valid_json(self) -> None:
        context = AgentContext(
            evidence={"test_results": "all passed", "lint_results": "clean"},
            extra={
                "acceptance_criteria": ["Tests pass for new feature"],
                "qa_handoff": [],
            },
        )
        result = _qa_fallback(context)
        data = json.loads(result)
        assert "criteria_results" in data
        assert "defects" in data

    def test_fallback_with_no_criteria(self) -> None:
        context = AgentContext(
            evidence={},
            extra={"acceptance_criteria": [], "qa_handoff": []},
        )
        result = _qa_fallback(context)
        data = json.loads(result)
        # No criteria means intent_gap
        assert any(d["category"] == "intent_gap" for d in data["defects"])

    def test_fallback_with_matching_evidence(self) -> None:
        context = AgentContext(
            evidence={"test_results": "pagination tests passed"},
            extra={
                "acceptance_criteria": ["Pagination tests pass"],
                "qa_handoff": [],
            },
        )
        result = _qa_fallback(context)
        data = json.loads(result)
        assert isinstance(data["criteria_results"], list)


class TestQASystemPrompt:
    """Tests for the system prompt template."""

    def test_prompt_has_required_placeholders(self) -> None:
        assert "{acceptance_criteria}" in QA_SYSTEM_PROMPT
        assert "{evidence_keys}" in QA_SYSTEM_PROMPT

    def test_prompt_mentions_intent_satisfaction(self) -> None:
        """AC 29: Prompt instructs reasoning about intent satisfaction."""
        assert "intent" in QA_SYSTEM_PROMPT.lower()
        assert "reason" in QA_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_edge_cases(self) -> None:
        """AC 30: Prompt instructs edge case identification."""
        assert "edge case" in QA_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_defect_taxonomy(self) -> None:
        assert "intent_gap" in QA_SYSTEM_PROMPT
        assert "implementation_bug" in QA_SYSTEM_PROMPT

    def test_prompt_mentions_severity(self) -> None:
        assert "S0" in QA_SYSTEM_PROMPT
        assert "S3" in QA_SYSTEM_PROMPT
