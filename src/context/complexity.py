"""Complexity Index v0 — categorical scoring.

Phase 0: low/medium/high based on scope breadth + risk flag count.
Phase 3 defines a formal rubric with dimensions and formula.
"""


def compute_complexity(affected_files_estimate: int, risk_flags: dict[str, bool]) -> str:
    """Compute Complexity Index v0.

    Rules:
    - low: single file, no risk flags
    - medium: multiple files or 1 risk flag
    - high: many files (5+) or 2+ risk flags
    """
    risk_count = sum(1 for v in risk_flags.values() if v)

    if risk_count >= 2 or affected_files_estimate >= 5:
        return "high"
    if risk_count >= 1 or affected_files_estimate > 1:
        return "medium"
    return "low"
