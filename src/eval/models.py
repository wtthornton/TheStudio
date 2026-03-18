"""Data models for the evaluation harness.

Epic 30, Story 30.1: EvalCase (labeled test input), EvalResult (per-case
output with dimension scores), and EvalSummary (aggregated results).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    """A labeled test case for agent evaluation.

    Each case represents a realistic GitHub issue with expected output
    characteristics that scoring functions can validate against.
    """

    case_id: str
    category: str  # e.g. "bug_fix", "feature", "security", "refactor"
    issue_title: str
    issue_body: str
    labels: list[str] = field(default_factory=list)
    risk_flags: dict[str, bool] = field(default_factory=dict)
    complexity: str = "medium"  # "low", "medium", "high"

    # Expected output characteristics for scoring
    expected_goal_keywords: list[str] = field(default_factory=list)
    expected_constraints: list[str] = field(default_factory=list)
    expected_acs: list[str] = field(default_factory=list)
    expects_invariants: bool = False
    expects_non_goals: bool = True


@dataclass
class EvalResult:
    """Result of evaluating one agent against one test case."""

    case_id: str
    agent_name: str
    passed: bool = False

    # Dimension scores (0.0 to 1.0)
    goal_clarity: float = 0.0
    constraint_coverage: float = 0.0
    ac_completeness: float = 0.0
    invariant_presence: float = 0.0
    non_goal_specificity: float = 0.0

    # Metadata
    parse_success: bool = False
    raw_output: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str = ""

    # Parsed output for downstream use
    parsed: Any = None


@dataclass
class EvalSummary:
    """Aggregated results across all test cases for one agent."""

    agent_name: str
    total_cases: int = 0
    passed_count: int = 0
    pass_rate: float = 0.0
    parse_success_rate: float = 0.0

    # Mean dimension scores
    mean_goal_clarity: float = 0.0
    mean_constraint_coverage: float = 0.0
    mean_ac_completeness: float = 0.0
    mean_invariant_presence: float = 0.0
    mean_non_goal_specificity: float = 0.0

    # Cost and performance
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    mean_duration_ms: float = 0.0

    # Per-case results
    results: list[EvalResult] = field(default_factory=list)


@dataclass
class ModelComparisonResult:
    """Comparison of an agent's eval results across two model classes.

    Epic 32, Story 32.3: Used to validate that downgrading an agent
    to a cheaper model class doesn't degrade output quality below
    a configurable threshold.
    """

    agent_name: str
    baseline_class: str = "balanced"
    candidate_class: str = "fast"
    baseline_summary: EvalSummary | None = None
    candidate_summary: EvalSummary | None = None

    # Derived metrics
    pass_rate_delta: float = 0.0  # candidate - baseline (negative = regression)
    cost_savings_pct: float = 0.0  # % cost reduction
    quality_ratio: float = 0.0  # candidate_pass_rate / baseline_pass_rate

    # Verdict
    meets_threshold: bool = False  # True if quality_ratio >= threshold
