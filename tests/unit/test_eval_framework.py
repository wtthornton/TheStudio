"""Tests for eval framework and intent correctness eval (Story 5.1)."""

import json
from pathlib import Path

import pytest

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType
from src.evals.intent_correctness import (
    IntentCorrectnessEval,
    _compute_criteria_coverage,
    _compute_goal_overlap,
    _extract_key_terms,
)
from src.evals.runner import EvalReport, load_fixtures, run_evals


class TestEvalFramework:
    """Tests for core framework types."""

    def test_eval_case_creation(self):
        case = EvalCase(
            id="test-1",
            eval_type=EvalType.INTENT_CORRECTNESS,
            input_data={"issue_text": "test"},
            expected_output={"match_quality": "clear_match"},
        )
        assert case.id == "test-1"
        assert case.eval_type == EvalType.INTENT_CORRECTNESS
        assert case.metadata == {}

    def test_eval_result_to_dict(self):
        result = EvalResult(
            case_id="test-1",
            eval_type=EvalType.INTENT_CORRECTNESS,
            passed=True,
            score=0.85,
            details={"goal_keyword_overlap": 0.9},
        )
        d = result.to_dict()
        assert d["case_id"] == "test-1"
        assert d["eval_type"] == "intent_correctness"
        assert d["passed"] is True
        assert d["score"] == 0.85
        assert d["failure_reason"] is None

    def test_eval_type_values(self):
        assert EvalType.INTENT_CORRECTNESS == "intent_correctness"
        assert EvalType.ROUTING_CORRECTNESS == "routing_correctness"
        assert EvalType.VERIFICATION_FRICTION == "verification_friction"
        assert EvalType.QA_DEFECT_MAPPING == "qa_defect_mapping"

    def test_eval_suite_is_abstract(self):
        with pytest.raises(TypeError):
            EvalSuite()  # type: ignore[abstract]


class TestIntentCorrectnessHelpers:
    """Tests for intent correctness helper functions."""

    def test_extract_key_terms_filters_stop_words(self):
        terms = _extract_key_terms("the user should login with email and password")
        assert "the" not in terms
        assert "and" not in terms
        assert "login" in terms
        assert "email" in terms
        assert "password" in terms

    def test_extract_key_terms_handles_empty(self):
        terms = _extract_key_terms("")
        assert terms == set()

    def test_extract_key_terms_min_length(self):
        terms = _extract_key_terms("a to go by do it is")
        assert terms == set()

    def test_goal_overlap_perfect(self):
        overlap, found, missing = _compute_goal_overlap(
            "implement user authentication", "implement user authentication"
        )
        assert overlap == 1.0
        assert len(missing) == 0

    def test_goal_overlap_partial(self):
        overlap, found, missing = _compute_goal_overlap(
            "implement user authentication with JWT",
            "implement user login",
        )
        assert 0.0 < overlap < 1.0
        assert "implement" in found
        assert "user" in found

    def test_goal_overlap_none(self):
        overlap, found, missing = _compute_goal_overlap(
            "fix payment timeout", "optimize database queries"
        )
        assert overlap == 0.0
        assert len(found) == 0

    def test_criteria_coverage_full(self):
        coverage = _compute_criteria_coverage(
            "login with email and password, get JWT token",
            [
                "login endpoint accepts email and password",
                "returns JWT token on success",
            ],
        )
        assert coverage > 0.7

    def test_criteria_coverage_none(self):
        coverage = _compute_criteria_coverage(
            "fix payment timeout",
            ["optimize database queries", "add caching layer"],
        )
        assert coverage < 0.3

    def test_criteria_coverage_empty_criteria(self):
        coverage = _compute_criteria_coverage("some issue text", [])
        assert coverage == 0.0


class TestIntentCorrectnessEval:
    """Tests for IntentCorrectnessEval suite."""

    def test_clear_match(self):
        case = EvalCase(
            id="clear-1",
            eval_type=EvalType.INTENT_CORRECTNESS,
            input_data={
                "issue_text": "Add JWT authentication with login, token refresh, and logout",
                "goal": "Implement JWT authentication with login, token refresh, and logout endpoints",
                "acceptance_criteria": [
                    "Login endpoint accepts credentials and returns JWT",
                    "Token refresh endpoint extends validity",
                    "Logout endpoint invalidates token",
                ],
            },
            expected_output={"match_quality": "clear_match"},
        )
        suite = IntentCorrectnessEval()
        results = suite.run([case])
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].score >= 0.7

    def test_mismatch(self):
        case = EvalCase(
            id="mismatch-1",
            eval_type=EvalType.INTENT_CORRECTNESS,
            input_data={
                "issue_text": "Fix Stripe webhook timeout causing blank confirmation page",
                "goal": "Improve general application performance",
                "acceptance_criteria": [
                    "Response time under 200ms for GET endpoints",
                    "Database query optimization applied",
                ],
            },
            expected_output={"match_quality": "mismatch"},
        )
        suite = IntentCorrectnessEval()
        results = suite.run([case])
        assert len(results) == 1
        assert results[0].passed is True  # Label check passes: mismatch correctly detected
        assert results[0].score < 0.6

    def test_skips_wrong_eval_type(self):
        case = EvalCase(
            id="wrong-type",
            eval_type=EvalType.ROUTING_CORRECTNESS,
            input_data={},
            expected_output={},
        )
        suite = IntentCorrectnessEval()
        results = suite.run([case])
        assert len(results) == 0

    def test_eval_type_attribute(self):
        suite = IntentCorrectnessEval()
        assert suite.eval_type == EvalType.INTENT_CORRECTNESS


class TestEvalRunner:
    """Tests for eval runner and fixture loading."""

    def test_load_fixtures_from_directory(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        cases = load_fixtures(fixtures_dir)
        assert len(cases) >= 3
        assert all(isinstance(c, EvalCase) for c in cases)

    def test_run_evals_with_intent_fixtures(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        report = run_evals(fixtures_dir=fixtures_dir)
        assert isinstance(report, EvalReport)
        assert report.total_cases >= 3
        assert report.passed + report.failed == report.total_cases
        assert "intent_correctness" in report.score_by_eval_type

    def test_report_to_dict(self):
        report = EvalReport(total_cases=10, passed=8, failed=2)
        d = report.to_dict()
        assert d["total_cases"] == 10
        assert d["pass_rate"] == 0.8
        assert d["results"] == []

    def test_run_evals_empty(self):
        report = run_evals(cases=[], suites=[])
        assert report.total_cases == 0
        assert report.passed == 0
