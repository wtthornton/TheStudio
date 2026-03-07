"""Eval runner — loads fixtures, runs eval suites, produces aggregate report.

Usage: python -m src.evals.runner
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.evals.framework import EvalCase, EvalResult, EvalSuite, EvalType
from src.evals.intent_correctness import IntentCorrectnessEval
from src.evals.qa_defect_mapping import QADefectMappingEval
from src.evals.routing_correctness import RoutingCorrectnessEval
from src.evals.verification_friction import VerificationFrictionEval

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class EvalReport:
    """Aggregate eval report across all suites."""

    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    results: list[EvalResult] = field(default_factory=list)
    score_by_eval_type: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": (
                round(self.passed / self.total_cases, 3) if self.total_cases else 0.0
            ),
            "score_by_eval_type": self.score_by_eval_type,
            "results": [r.to_dict() for r in self.results],
        }


def load_fixtures(fixtures_dir: Path | None = None) -> list[EvalCase]:
    """Load all eval cases from JSON fixture files."""
    directory = fixtures_dir or FIXTURES_DIR
    cases: list[EvalCase] = []

    for fixture_file in sorted(directory.glob("*.json")):
        with open(fixture_file) as f:
            raw_cases = json.load(f)

        for raw in raw_cases:
            cases.append(
                EvalCase(
                    id=raw["id"],
                    eval_type=EvalType(raw["eval_type"]),
                    input_data=raw["input_data"],
                    expected_output=raw["expected_output"],
                    metadata=raw.get("metadata", {}),
                )
            )

    return cases


def get_all_suites() -> list[EvalSuite]:
    """Return all registered eval suites."""
    return [
        IntentCorrectnessEval(),
        RoutingCorrectnessEval(),
        VerificationFrictionEval(),
        QADefectMappingEval(),
    ]


def run_evals(
    cases: list[EvalCase] | None = None,
    suites: list[EvalSuite] | None = None,
    fixtures_dir: Path | None = None,
) -> EvalReport:
    """Run all eval suites against cases and produce aggregate report."""
    if cases is None:
        cases = load_fixtures(fixtures_dir)
    if suites is None:
        suites = get_all_suites()

    report = EvalReport()

    for suite in suites:
        suite_cases = [c for c in cases if c.eval_type == suite.eval_type]
        if not suite_cases:
            continue

        results = suite.run(suite_cases)
        report.results.extend(results)
        report.total_cases += len(results)
        report.passed += sum(1 for r in results if r.passed)
        report.failed += sum(1 for r in results if not r.passed)

        avg_score = (
            sum(r.score for r in results) / len(results) if results else 0.0
        )
        report.score_by_eval_type[suite.eval_type.value] = round(avg_score, 3)

    return report


def main() -> None:
    """CLI entry point: run all evals and print report."""
    report = run_evals()

    print(json.dumps(report.to_dict(), indent=2))

    if report.failed > 0:
        print(f"\n{report.failed}/{report.total_cases} eval(s) FAILED", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll {report.total_cases} eval(s) PASSED", file=sys.stderr)


if __name__ == "__main__":
    main()
