"""Verification Friction Eval — measures iterations-to-green and time-to-green.

Analyzes workflow timeline entries to compute friction scores normalized by
complexity band.
"""

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType

# Complexity band multipliers for friction normalization
# Higher complexity tasks are expected to take more iterations
COMPLEXITY_MULTIPLIERS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.5,
}

# Baseline expectations (iterations and time in ms)
BASELINE_ITERATIONS = 2
BASELINE_TIME_MS = 60_000  # 1 minute


class VerificationFrictionEval(EvalSuite):
    """Evaluates verification friction from workflow timeline data.

    Input data format:
        timeline: list[dict] — verification step entries with:
            step: str — step name (e.g., "verify_lint", "verify_test")
            attempt: int — attempt number
            duration_ms: int — duration of this attempt
            passed: bool — whether this attempt passed
        complexity_band: str — "low", "medium", or "high"

    Expected output format:
        friction_level: str — "low", "moderate", or "high"
    """

    eval_type = EvalType.VERIFICATION_FRICTION

    def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        results = []
        for case in cases:
            if case.eval_type != self.eval_type:
                continue
            results.append(self._evaluate_case(case))
        return results

    def _evaluate_case(self, case: EvalCase) -> EvalResult:
        timeline = case.input_data.get("timeline", [])
        complexity_band = case.input_data.get("complexity_band", "medium")

        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity_band, 1.5)

        total_iterations = len(timeline)
        total_time_ms = sum(entry.get("duration_ms", 0) for entry in timeline)
        failed_attempts = sum(1 for e in timeline if not e.get("passed", True))

        # Normalized friction score: iterations and time relative to baseline
        iter_ratio = total_iterations / (BASELINE_ITERATIONS * multiplier)
        time_ratio = total_time_ms / (BASELINE_TIME_MS * multiplier)

        # Weighted: 60% iteration friction, 40% time friction
        friction_score = 0.6 * iter_ratio + 0.4 * time_ratio

        # Invert to get a quality score (1.0 = no friction, 0.0 = extreme)
        score = max(0.0, min(1.0, 1.0 - (friction_score - 1.0) / 3.0))

        if friction_score <= 1.2:
            friction_level = "low"
        elif friction_score <= 2.0:
            friction_level = "moderate"
        else:
            friction_level = "high"

        expected_level = case.expected_output.get("friction_level")
        label_correct = expected_level is None or friction_level == expected_level

        failure_reason = None
        if not label_correct:
            failure_reason = (
                f"Expected friction_level={expected_level} but got {friction_level} "
                f"(friction_score={friction_score:.3f})"
            )

        return EvalResult(
            case_id=case.id,
            eval_type=self.eval_type,
            passed=label_correct,
            score=round(score, 3),
            details={
                "total_iterations": total_iterations,
                "total_time_ms": total_time_ms,
                "failed_attempts": failed_attempts,
                "complexity_band": complexity_band,
                "friction_score": round(friction_score, 3),
                "friction_level": friction_level,
            },
            failure_reason=failure_reason,
        )
