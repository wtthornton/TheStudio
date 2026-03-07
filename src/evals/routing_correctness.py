"""Routing Correctness Eval — checks if required expert classes were consulted.

Given a task with risk flags and mandatory coverage rules, verifies that all
required expert classes were included in routing decisions.
"""

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType


class RoutingCorrectnessEval(EvalSuite):
    """Evaluates whether routing consulted all required expert classes.

    Input data format:
        risk_flags: list[str] — risk flags present on the task
        consulted_expert_classes: list[str] — expert classes actually consulted
        mandatory_coverage_rules: dict[str, list[str]] — maps risk_flag -> required classes

    Expected output format:
        all_covered: bool — whether all required classes were consulted
    """

    eval_type = EvalType.ROUTING_CORRECTNESS

    def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        results = []
        for case in cases:
            if case.eval_type != self.eval_type:
                continue
            results.append(self._evaluate_case(case))
        return results

    def _evaluate_case(self, case: EvalCase) -> EvalResult:
        risk_flags = case.input_data.get("risk_flags", [])
        consulted = set(case.input_data.get("consulted_expert_classes", []))
        rules = case.input_data.get("mandatory_coverage_rules", {})

        required: set[str] = set()
        for flag in risk_flags:
            required |= set(rules.get(flag, []))

        covered = required & consulted
        missing = sorted(required - consulted)
        extra = sorted(consulted - required)

        if required:
            score = len(covered) / len(required)
        else:
            score = 1.0  # No requirements means no violations

        all_covered = len(missing) == 0
        expected = case.expected_output.get("all_covered")
        label_correct = expected is None or all_covered == expected

        failure_reason = None
        if not label_correct:
            failure_reason = (
                f"Expected all_covered={expected} but got {all_covered}. "
                f"Missing: {missing}"
            )

        return EvalResult(
            case_id=case.id,
            eval_type=self.eval_type,
            passed=label_correct,
            score=round(score, 3),
            details={
                "required_classes": sorted(required),
                "consulted_classes": sorted(consulted),
                "missing_classes": missing,
                "extra_classes": extra,
                "all_covered": all_covered,
            },
            failure_reason=failure_reason,
        )
