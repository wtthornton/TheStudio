"""Tests for QA defect mapping eval and full eval runner (Story 5.3)."""

from pathlib import Path

from src.evals.framework import EvalCase, EvalType
from src.evals.qa_defect_mapping import QADefectMappingEval, _extract_terms, _match_defect_to_criteria
from src.evals.runner import load_fixtures, run_evals


class TestQADefectMappingHelpers:
    """Tests for QA defect mapping helper functions."""

    def test_extract_terms(self):
        terms = _extract_terms("Login endpoint returns 401 error for invalid credentials")
        assert "login" in terms
        assert "endpoint" in terms
        assert "error" in terms
        assert "invalid" in terms
        assert "credentials" in terms

    def test_match_defect_finds_best_criterion(self):
        criteria = [
            "Login endpoint accepts email and password",
            "JWT token returned on successful login",
            "Invalid credentials return 401 error",
        ]
        idx = _match_defect_to_criteria(
            "Invalid credentials not returning 401 error", criteria
        )
        assert idx == 2  # Best match is criterion about invalid credentials

    def test_match_defect_returns_none_for_no_match(self):
        criteria = [
            "Dashboard shows user profile",
            "Profile picture uploads work",
        ]
        idx = _match_defect_to_criteria(
            "Database connection pool exhausted under load", criteria
        )
        assert idx is None


class TestQADefectMappingEval:
    """Tests for QADefectMappingEval suite."""

    def test_all_defects_mapped(self):
        case = EvalCase(
            id="mapped",
            eval_type=EvalType.QA_DEFECT_MAPPING,
            input_data={
                "acceptance_criteria": [
                    "Login endpoint accepts email and password",
                    "JWT token returned on login",
                ],
                "qa_defects": [
                    {"description": "Login endpoint crashes with valid email and password", "category": "bug", "severity": "s1"},
                ],
            },
            expected_output={"unmapped_classification": {"intent_gap": 0, "implementation_bug": 1}},
        )
        suite = QADefectMappingEval()
        results = suite.run([case])
        assert results[0].passed is True
        assert results[0].details["mapped_count"] == 1
        assert results[0].details["unmapped_count"] == 0

    def test_intent_gap_detected(self):
        case = EvalCase(
            id="gap",
            eval_type=EvalType.QA_DEFECT_MAPPING,
            input_data={
                "acceptance_criteria": ["Users can create posts"],
                "qa_defects": [
                    {"description": "Memory leak in background worker process", "category": "performance", "severity": "s0"},
                ],
            },
            expected_output={"unmapped_classification": {"intent_gap": 1, "implementation_bug": 0}},
        )
        suite = QADefectMappingEval()
        results = suite.run([case])
        assert results[0].passed is True
        assert results[0].details["intent_gaps"] == 1

    def test_no_defects(self):
        case = EvalCase(
            id="clean",
            eval_type=EvalType.QA_DEFECT_MAPPING,
            input_data={
                "acceptance_criteria": ["API returns data"],
                "qa_defects": [],
            },
            expected_output={"unmapped_classification": {"intent_gap": 0, "implementation_bug": 0}},
        )
        suite = QADefectMappingEval()
        results = suite.run([case])
        assert results[0].passed is True
        assert results[0].score == 1.0

    def test_mixed_mapping(self):
        case = EvalCase(
            id="mixed",
            eval_type=EvalType.QA_DEFECT_MAPPING,
            input_data={
                "acceptance_criteria": [
                    "Users can upload profile pictures in PNG format",
                ],
                "qa_defects": [
                    {"description": "Profile picture upload fails for PNG format files", "category": "bug", "severity": "s1"},
                    {"description": "SQL injection in search endpoint", "category": "security", "severity": "s0"},
                ],
            },
            expected_output={"unmapped_classification": {"intent_gap": 1, "implementation_bug": 1}},
        )
        suite = QADefectMappingEval()
        results = suite.run([case])
        assert results[0].passed is True

    def test_skips_wrong_eval_type(self):
        case = EvalCase(
            id="wrong", eval_type=EvalType.INTENT_CORRECTNESS, input_data={}, expected_output={},
        )
        suite = QADefectMappingEval()
        assert suite.run([case]) == []


class TestFullEvalRunner:
    """Tests for the complete eval runner with all 4 eval types."""

    def test_all_fixtures_load(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        cases = load_fixtures(fixtures_dir)
        # 3 intent + 3 routing + 3 verification + 4 QA = 13
        assert len(cases) >= 13

    def test_run_all_evals(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        report = run_evals(fixtures_dir=fixtures_dir)
        assert report.total_cases >= 13
        assert "intent_correctness" in report.score_by_eval_type
        assert "routing_correctness" in report.score_by_eval_type
        assert "verification_friction" in report.score_by_eval_type
        assert "qa_defect_mapping" in report.score_by_eval_type

    def test_all_fixtures_pass(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        report = run_evals(fixtures_dir=fixtures_dir)
        assert report.failed == 0, (
            f"{report.failed} fixture(s) failed: "
            + ", ".join(r.case_id for r in report.results if not r.passed)
        )

    def test_report_structure(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        report = run_evals(fixtures_dir=fixtures_dir)
        d = report.to_dict()
        assert "total_cases" in d
        assert "passed" in d
        assert "failed" in d
        assert "pass_rate" in d
        assert "score_by_eval_type" in d
        assert "results" in d
        assert d["pass_rate"] == 1.0
