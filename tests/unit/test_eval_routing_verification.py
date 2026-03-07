"""Tests for routing correctness and verification friction evals (Story 5.2)."""

from pathlib import Path

from src.evals.framework import EvalCase, EvalType
from src.evals.routing_correctness import RoutingCorrectnessEval
from src.evals.runner import load_fixtures, run_evals
from src.evals.verification_friction import VerificationFrictionEval


class TestRoutingCorrectnessEval:
    """Tests for RoutingCorrectnessEval suite."""

    def test_all_classes_covered(self):
        case = EvalCase(
            id="test-covered",
            eval_type=EvalType.ROUTING_CORRECTNESS,
            input_data={
                "risk_flags": ["security_sensitive"],
                "consulted_expert_classes": ["security", "technical"],
                "mandatory_coverage_rules": {
                    "security_sensitive": ["security"],
                },
            },
            expected_output={"all_covered": True},
        )
        suite = RoutingCorrectnessEval()
        results = suite.run([case])
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].score == 1.0
        assert results[0].details["missing_classes"] == []

    def test_missing_class_detected(self):
        case = EvalCase(
            id="test-missing",
            eval_type=EvalType.ROUTING_CORRECTNESS,
            input_data={
                "risk_flags": ["security_sensitive", "compliance_required"],
                "consulted_expert_classes": ["technical"],
                "mandatory_coverage_rules": {
                    "security_sensitive": ["security"],
                    "compliance_required": ["compliance"],
                },
            },
            expected_output={"all_covered": False},
        )
        suite = RoutingCorrectnessEval()
        results = suite.run([case])
        assert len(results) == 1
        assert results[0].passed is True  # Label matches
        assert results[0].score == 0.0  # Neither required class consulted
        assert "security" in results[0].details["missing_classes"]
        assert "compliance" in results[0].details["missing_classes"]

    def test_no_risk_flags(self):
        case = EvalCase(
            id="test-no-flags",
            eval_type=EvalType.ROUTING_CORRECTNESS,
            input_data={
                "risk_flags": [],
                "consulted_expert_classes": ["technical"],
                "mandatory_coverage_rules": {},
            },
            expected_output={"all_covered": True},
        )
        suite = RoutingCorrectnessEval()
        results = suite.run([case])
        assert results[0].passed is True
        assert results[0].score == 1.0

    def test_extra_classes_tracked(self):
        case = EvalCase(
            id="test-extra",
            eval_type=EvalType.ROUTING_CORRECTNESS,
            input_data={
                "risk_flags": ["security_sensitive"],
                "consulted_expert_classes": ["security", "technical", "business"],
                "mandatory_coverage_rules": {
                    "security_sensitive": ["security"],
                },
            },
            expected_output={"all_covered": True},
        )
        suite = RoutingCorrectnessEval()
        results = suite.run([case])
        assert results[0].details["extra_classes"] == ["business", "technical"]

    def test_skips_wrong_eval_type(self):
        case = EvalCase(
            id="wrong", eval_type=EvalType.INTENT_CORRECTNESS, input_data={}, expected_output={},
        )
        suite = RoutingCorrectnessEval()
        assert suite.run([case]) == []


class TestVerificationFrictionEval:
    """Tests for VerificationFrictionEval suite."""

    def test_low_friction(self):
        case = EvalCase(
            id="test-low",
            eval_type=EvalType.VERIFICATION_FRICTION,
            input_data={
                "timeline": [
                    {"step": "verify_lint", "attempt": 1, "duration_ms": 5000, "passed": True},
                    {"step": "verify_test", "attempt": 1, "duration_ms": 15000, "passed": True},
                ],
                "complexity_band": "low",
            },
            expected_output={"friction_level": "low"},
        )
        suite = VerificationFrictionEval()
        results = suite.run([case])
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].details["friction_level"] == "low"
        assert results[0].details["failed_attempts"] == 0

    def test_high_friction(self):
        case = EvalCase(
            id="test-high",
            eval_type=EvalType.VERIFICATION_FRICTION,
            input_data={
                "timeline": [
                    {"step": "verify_lint", "attempt": i, "duration_ms": 10000, "passed": i == 5}
                    for i in range(1, 9)
                ],
                "complexity_band": "low",
            },
            expected_output={"friction_level": "high"},
        )
        suite = VerificationFrictionEval()
        results = suite.run([case])
        assert results[0].passed is True
        assert results[0].details["friction_level"] == "high"
        assert results[0].details["total_iterations"] == 8

    def test_complexity_normalization(self):
        """High-complexity tasks get more lenient friction scoring."""
        timeline = [
            {"step": "verify_test", "attempt": i, "duration_ms": 20000, "passed": i == 4}
            for i in range(1, 5)
        ]
        low_case = EvalCase(
            id="low-cx", eval_type=EvalType.VERIFICATION_FRICTION,
            input_data={"timeline": timeline, "complexity_band": "low"},
            expected_output={},
        )
        high_case = EvalCase(
            id="high-cx", eval_type=EvalType.VERIFICATION_FRICTION,
            input_data={"timeline": timeline, "complexity_band": "high"},
            expected_output={},
        )
        suite = VerificationFrictionEval()
        low_result = suite.run([low_case])[0]
        high_result = suite.run([high_case])[0]

        # Same timeline, but high complexity should have lower friction score
        assert (
            high_result.details["friction_score"] < low_result.details["friction_score"]
        )

    def test_empty_timeline(self):
        case = EvalCase(
            id="test-empty", eval_type=EvalType.VERIFICATION_FRICTION,
            input_data={"timeline": [], "complexity_band": "medium"},
            expected_output={"friction_level": "low"},
        )
        suite = VerificationFrictionEval()
        results = suite.run([case])
        assert results[0].details["friction_level"] == "low"
        assert results[0].details["total_iterations"] == 0

    def test_skips_wrong_eval_type(self):
        case = EvalCase(
            id="wrong", eval_type=EvalType.INTENT_CORRECTNESS, input_data={}, expected_output={},
        )
        suite = VerificationFrictionEval()
        assert suite.run([case]) == []


class TestFixtureIntegration:
    """Tests that fixture files load and run correctly for Stories 5.1-5.2."""

    def test_all_fixtures_load(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        cases = load_fixtures(fixtures_dir)
        # 3 intent + 3 routing + 3 verification = 9
        assert len(cases) >= 9

    def test_routing_fixtures_pass(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        suite = RoutingCorrectnessEval()
        cases = load_fixtures(fixtures_dir)
        routing_cases = [c for c in cases if c.eval_type == EvalType.ROUTING_CORRECTNESS]
        results = suite.run(routing_cases)
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_verification_fixtures_pass(self):
        fixtures_dir = Path(__file__).parent.parent.parent / "src" / "evals" / "fixtures"
        suite = VerificationFrictionEval()
        cases = load_fixtures(fixtures_dir)
        friction_cases = [c for c in cases if c.eval_type == EvalType.VERIFICATION_FRICTION]
        results = suite.run(friction_cases)
        assert len(results) == 3
        assert all(r.passed for r in results)
