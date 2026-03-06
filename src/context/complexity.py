"""Complexity Index v1 — quantified scoring with dimensions.

Architecture reference: docs/architecture/complexity-index-v1.md
Enables fair outcome normalization in the learning loop (Outcome Ingestor, Reputation Engine).
"""

from dataclasses import dataclass
from typing import Any

from src.context.scope_analyzer import ScopeResult


@dataclass(frozen=True)
class ComplexityDimensions:
    """Individual dimensions that contribute to the complexity score."""

    scope_breadth: int  # 1=single file, 2=few files, 3=cross-module
    risk_flag_count: int  # Count of risk labels
    dependency_count: int  # External dependencies touched
    lines_estimate: int  # Estimated lines changed
    expert_coverage: int  # Required expert classes count

    def to_dict(self) -> dict[str, int]:
        return {
            "scope_breadth": self.scope_breadth,
            "risk_flag_count": self.risk_flag_count,
            "dependency_count": self.dependency_count,
            "lines_estimate": self.lines_estimate,
            "expert_coverage": self.expert_coverage,
        }


@dataclass(frozen=True)
class ComplexityIndex:
    """Complexity Index v1 — quantified score with band classification.

    Stored as JSONB on TaskPacket. Used by Outcome Ingestor for normalization
    and by Reputation Engine for fair attribution.
    """

    score: float
    band: str  # "low", "medium", "high"
    dimensions: ComplexityDimensions

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "dimensions": self.dimensions.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComplexityIndex":
        """Reconstruct ComplexityIndex from stored dict."""
        dims_data = data.get("dimensions") or {}
        dimensions = ComplexityDimensions(
            scope_breadth=dims_data.get("scope_breadth", 1),
            risk_flag_count=dims_data.get("risk_flag_count", 0),
            dependency_count=dims_data.get("dependency_count", 0),
            lines_estimate=dims_data.get("lines_estimate", 0),
            expert_coverage=dims_data.get("expert_coverage", 0),
        )
        return cls(
            score=data.get("score", 0.0),
            band=data.get("band", "low"),
            dimensions=dimensions,
        )


# Complexity band thresholds
BAND_LOW_MAX = 5.0
BAND_MEDIUM_MAX = 12.0


def _classify_band(score: float) -> str:
    """Classify complexity score into band."""
    if score <= BAND_LOW_MAX:
        return "low"
    if score <= BAND_MEDIUM_MAX:
        return "medium"
    return "high"


def _scope_breadth_from_files(affected_files: int) -> int:
    """Convert affected files estimate to scope breadth (1-3)."""
    if affected_files <= 1:
        return 1
    if affected_files <= 4:
        return 2
    return 3


def _estimate_lines(scope_result: ScopeResult) -> int:
    """Estimate lines changed from scope analysis.

    Heuristic: components * 50 lines, file refs * 30 lines.
    """
    if scope_result.file_references:
        return len(scope_result.file_references) * 30
    if scope_result.components:
        return len(scope_result.components) * 50
    return 25  # Default for single-file changes


def compute_complexity_index(
    scope_result: ScopeResult,
    risk_flags: dict[str, bool],
    mandatory_expert_classes: tuple[Any, ...] | list[Any] = (),
) -> ComplexityIndex:
    """Compute Complexity Index v1 from context data.

    Args:
        scope_result: Scope analysis output from analyze_scope().
        risk_flags: Dict of risk flag name -> bool.
        mandatory_expert_classes: Tuple/list of required expert classes from EffectiveRolePolicy.

    Returns:
        ComplexityIndex with score, band, and dimensions.
    """
    # Extract dimensions
    scope_breadth = _scope_breadth_from_files(scope_result.affected_files_estimate)
    risk_flag_count = sum(1 for v in risk_flags.values() if v)
    dependency_count = len(scope_result.components)
    lines_estimate = _estimate_lines(scope_result)
    expert_coverage = len(mandatory_expert_classes)

    # Compute score using weighted formula
    score = (
        scope_breadth * 2.0
        + risk_flag_count * 3.0
        + dependency_count * 1.0
        + (lines_estimate / 50.0)
        + expert_coverage * 1.5
    )

    # Round to one decimal place for cleaner storage
    score = round(score, 1)

    # Classify into band
    band = _classify_band(score)

    # Build dimensions
    dimensions = ComplexityDimensions(
        scope_breadth=scope_breadth,
        risk_flag_count=risk_flag_count,
        dependency_count=dependency_count,
        lines_estimate=lines_estimate,
        expert_coverage=expert_coverage,
    )

    return ComplexityIndex(score=score, band=band, dimensions=dimensions)


def compute_complexity(affected_files_estimate: int, risk_flags: dict[str, bool]) -> str:
    """Legacy v0 interface — returns band string only.

    DEPRECATED: Use compute_complexity_index() for v1 with full dimensions.
    Kept for backward compatibility with existing code during migration.
    """
    scope_result = ScopeResult(affected_files_estimate=affected_files_estimate)
    index = compute_complexity_index(scope_result, risk_flags)
    return index.band
