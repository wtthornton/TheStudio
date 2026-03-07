"""Eval framework — base types and eval suite interface.

Provides EvalCase, EvalResult, and EvalSuite base class for all eval types.
"""

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class EvalType(enum.StrEnum):
    """Eval type identifiers."""

    INTENT_CORRECTNESS = "intent_correctness"
    ROUTING_CORRECTNESS = "routing_correctness"
    VERIFICATION_FRICTION = "verification_friction"
    QA_DEFECT_MAPPING = "qa_defect_mapping"


@dataclass
class EvalCase:
    """A single eval test case with input, expected output, and metadata."""

    id: str
    eval_type: EvalType
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of running a single eval case."""

    case_id: str
    eval_type: EvalType
    passed: bool
    score: float  # 0.0 to 1.0
    details: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "eval_type": self.eval_type.value,
            "passed": self.passed,
            "score": self.score,
            "details": self.details,
            "failure_reason": self.failure_reason,
        }


class EvalSuite(ABC):
    """Base class for eval suites."""

    eval_type: EvalType

    @abstractmethod
    def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        """Run evaluation on a list of cases and return results."""
        ...
