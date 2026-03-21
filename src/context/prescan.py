"""Lightweight pre-scan for triage card enrichment (Epic 36, Story 36.4).

This is NOT the full Context stage. It is a fast, synchronous heuristic
that produces estimated file count, complexity hint, and cost range
for display on triage queue cards. No DB access, no LLM call.
"""

import re

# Keywords that indicate higher complexity
_HIGH_COMPLEXITY_KEYWORDS = frozenset({
    "migration", "schema", "database", "breaking", "refactor",
    "architecture", "security", "authentication", "authorization",
    "performance", "scalability", "multi-tenant",
})

_MEDIUM_COMPLEXITY_KEYWORDS = frozenset({
    "test", "testing", "api", "endpoint", "integration",
    "workflow", "pipeline", "configuration", "deploy",
})

# File path patterns in issue bodies
_FILE_PATH_PATTERN = re.compile(
    r"(?:src/|tests/|frontend/|lib/|app/|pkg/)\S+\.\w+",
)

# Cost estimates per complexity tier (USD)
_COST_RANGES = {
    "low": {"min": 0.05, "max": 0.15},
    "medium": {"min": 0.10, "max": 0.40},
    "high": {"min": 0.30, "max": 1.00},
}


def prescan_issue(
    issue_title: str,
    issue_body: str,
    labels: list[str] | None = None,
) -> dict:
    """Run a lightweight pre-scan on an issue for triage enrichment.

    Returns a dict with:
        file_count_estimate: int — heuristic count of files mentioned
        complexity_hint: str — "low", "medium", or "high"
        cost_estimate_range: dict — {"min": float, "max": float}
    """
    labels = labels or []
    combined_text = f"{issue_title} {issue_body}".lower()

    # Estimate file count from path mentions in the body
    file_mentions = _FILE_PATH_PATTERN.findall(issue_body)
    file_count = max(len(set(file_mentions)), 1)

    # Determine complexity hint
    complexity = _compute_complexity(combined_text, labels, issue_body)

    return {
        "file_count_estimate": file_count,
        "complexity_hint": complexity,
        "cost_estimate_range": _COST_RANGES[complexity],
    }


def _compute_complexity(
    combined_text: str,
    labels: list[str],
    issue_body: str,
) -> str:
    """Compute complexity hint from text signals."""
    score = 0

    # Check keywords in text
    for keyword in _HIGH_COMPLEXITY_KEYWORDS:
        if keyword in combined_text:
            score += 2

    for keyword in _MEDIUM_COMPLEXITY_KEYWORDS:
        if keyword in combined_text:
            score += 1

    # Check labels
    label_text = " ".join(labels).lower()
    if any(kw in label_text for kw in ("breaking", "security", "migration")):
        score += 3
    if any(kw in label_text for kw in ("bug", "fix", "patch")):
        score -= 1

    # Body length as a signal
    if len(issue_body) > 2000:
        score += 2
    elif len(issue_body) > 500:
        score += 1

    if score >= 5:
        return "high"
    elif score >= 2:
        return "medium"
    return "low"
