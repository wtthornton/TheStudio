"""Readiness scoring engine — rule-based, pure function, no I/O.

Evaluates issue readiness across 6 dimensions and produces a ReadinessScore
with gate decision. Reuses extraction functions from intent_builder.

All scoring is deterministic and side-effect-free.
"""

from __future__ import annotations

import re

from src.intent.intent_builder import extract_acceptance_criteria, extract_non_goals
from src.readiness.config import ReadinessThresholds, get_thresholds
from src.readiness.models import (
    ComplexityTier,
    DimensionScore,
    GateDecision,
    ReadinessDimension,
    ReadinessScore,
)

# --- Question templates per dimension ---

_QUESTIONS: dict[ReadinessDimension, list[str]] = {
    ReadinessDimension.GOAL_CLARITY: [
        "Could you describe the problem or feature you need in more detail?",
        "What specific behavior are you seeing, and what behavior do you expect instead?",
    ],
    ReadinessDimension.ACCEPTANCE_CRITERIA: [
        "What would need to be true for you to consider this issue resolved?",
        "Could you add a checklist of specific requirements using markdown checkboxes (- [ ] ...)?",
    ],
    ReadinessDimension.SCOPE_BOUNDARIES: [
        "Are there any areas that should explicitly be left out of this change?",
        "Could you clarify the boundaries of what this issue should and should not address?",
    ],
    ReadinessDimension.RISK_COVERAGE: [
        "Are there any risks or edge cases we should be aware of for this change?",
        "Does this change affect security, performance, or data integrity?",
    ],
    ReadinessDimension.REPRODUCTION_CONTEXT: [
        "Could you provide steps to reproduce the issue?",
        "What environment are you using (OS, browser, version)?",
    ],
    ReadinessDimension.DEPENDENCY_AWARENESS: [
        "Does this work depend on or block any other issues?",
        "Are there external services or libraries this change requires?",
    ],
}

# --- Patterns for detection ---

_PROBLEM_KEYWORDS = re.compile(
    r"\b(bug|issue|error|fail|broken|crash|fix|problem|wrong|unexpected)\b",
    re.IGNORECASE,
)
_FEATURE_KEYWORDS = re.compile(
    r"\b(add|create|implement|feature|support|enable|allow|new|introduce)\b",
    re.IGNORECASE,
)
_REPRO_KEYWORDS = re.compile(
    r"(steps?\s+to\s+reproduce|expected\s+(behavior|result|output)|"
    r"actual\s+(behavior|result|output)|environment|version|os\b|browser)",
    re.IGNORECASE,
)
_DEPENDENCY_KEYWORDS = re.compile(
    r"\b(depends?\s+on|requires?|blocked\s+by|prerequisite|after\s+#\d+)\b",
    re.IGNORECASE,
)
_BUG_LABEL = re.compile(r"\bbug\b", re.IGNORECASE)


# --- Individual dimension scorers ---


def _score_goal_clarity(body: str) -> tuple[float, str]:
    """Score goal clarity based on body length and keyword presence."""
    score = 0.0
    reasons = []

    # Body length component (0.3)
    if len(body.strip()) > 50:
        score += 0.3
        reasons.append("body has sufficient detail")
    elif len(body.strip()) > 0:
        score += 0.1
        reasons.append("body is brief")

    # Problem/feature keyword component (0.3)
    has_problem = bool(_PROBLEM_KEYWORDS.search(body))
    has_feature = bool(_FEATURE_KEYWORDS.search(body))
    if has_problem or has_feature:
        score += 0.3
        reasons.append("contains problem or feature keywords")

    # Coherent paragraph (0.4) — find the longest paragraph with 10+ words
    paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    best_word_count = max((len(p.split()) for p in paragraphs), default=0)
    if best_word_count >= 10:
        score += 0.4
        reasons.append("coherent paragraph")
    elif best_word_count >= 5:
        score += 0.2
        reasons.append("short paragraphs")

    return score, "; ".join(reasons) if reasons else "empty or unclear goal"


def _score_acceptance_criteria(body: str) -> tuple[float, str]:
    """Score acceptance criteria presence and format."""
    criteria = extract_acceptance_criteria(body)
    count = len(criteria)

    if count == 0:
        return 0.0, "no acceptance criteria found"
    if count == 1:
        return 0.5, "1 acceptance criterion found"

    # Check if using checkbox format (higher quality)
    has_checkboxes = bool(re.search(r"- \[[ x]\]", body))
    if has_checkboxes:
        return 1.0, f"{count} acceptance criteria with checkbox format"

    if count >= 2:
        return 0.8, f"{count} acceptance criteria found"

    return 0.5, f"{count} acceptance criterion found"


def _score_scope_boundaries(
    body: str, complexity_tier: ComplexityTier
) -> tuple[float, str]:
    """Score scope boundary definition."""
    non_goals = extract_non_goals(body)

    if non_goals:
        # Check for explicit section header
        has_section = bool(
            re.search(
                r"(out\s+of\s+scope|non[- ]?goals?|not\s+included|exclusions?)",
                body,
                re.IGNORECASE,
            )
        )
        if has_section:
            return 1.0, f"explicit scope section with {len(non_goals)} non-goals"
        return 0.7, f"{len(non_goals)} scope boundaries identified"

    # No non-goals found — severity depends on complexity
    if complexity_tier == ComplexityTier.LOW:
        return 0.5, "no explicit scope boundaries (acceptable for low complexity)"

    return 0.0, "no scope boundaries defined"


def _score_risk_coverage(
    body: str, risk_flags: dict[str, bool] | None
) -> tuple[float, str]:
    """Score whether the issue body covers identified risk areas."""
    if not risk_flags:
        return 1.0, "no risk flags to cover"

    active_flags = [k for k, v in risk_flags.items() if v]
    if not active_flags:
        return 1.0, "no active risk flags"

    # Map risk flag names to body search terms
    ci = re.IGNORECASE
    risk_terms: dict[str, re.Pattern[str]] = {
        "risk_security": re.compile(r"\b(security|auth|permission|access|token)\b", ci),
        "risk_data": re.compile(r"\b(data|migration|schema|database|backup)\b", ci),
        "risk_performance": re.compile(r"\b(performance|latency|throughput|scale|load)\b", ci),
        "risk_destructive": re.compile(r"\b(delete|remove|drop|destructive|irreversible)\b", ci),
        "risk_privileged_access": re.compile(r"\b(admin|root|privilege|elevated|sudo)\b", ci),
        "risk_migration": re.compile(r"\b(migration|rollback|downtime|upgrade)\b", ci),
    }

    covered = 0
    for flag in active_flags:
        pattern = risk_terms.get(flag)
        if pattern and pattern.search(body):
            covered += 1
        elif not pattern:
            # Unknown risk flag — don't penalize
            covered += 1

    ratio = covered / len(active_flags) if active_flags else 1.0
    if ratio >= 1.0:
        return 1.0, "all risk areas covered in issue body"
    if ratio > 0:
        return ratio, f"{covered}/{len(active_flags)} risk areas covered"
    return 0.0, "risk areas not addressed in issue body"


def _score_reproduction_context(
    body: str, labels: list[str]
) -> tuple[float, str]:
    """Score reproduction context for bug-type issues."""
    is_bug = any(_BUG_LABEL.search(label) for label in labels)

    if not is_bug:
        # Check body heuristics for bug-like content
        has_repro_language = bool(
            re.search(r"(steps?\s+to\s+reproduce|expected\s+behavior)", body, re.IGNORECASE)
        )
        if not has_repro_language:
            return 1.0, "not a bug report (reproduction context not required)"

    # It's a bug — check for reproduction elements
    matches = _REPRO_KEYWORDS.findall(body)
    match_count = len(matches)

    if match_count >= 3:
        return 1.0, "comprehensive reproduction context"
    if match_count >= 2:
        return 0.7, "partial reproduction context"
    if match_count >= 1:
        return 0.4, "minimal reproduction context"
    return 0.0, "no reproduction context for bug report"


def _score_dependency_awareness(
    body: str, complexity_tier: ComplexityTier
) -> tuple[float, str]:
    """Score dependency awareness for complex issues."""
    if complexity_tier == ComplexityTier.LOW:
        return 1.0, "dependency awareness not required for low complexity"

    has_deps = bool(_DEPENDENCY_KEYWORDS.search(body))
    has_issue_refs = bool(re.search(r"#\d+", body))

    if has_deps or has_issue_refs:
        return 1.0, "dependencies or related issues referenced"

    if complexity_tier == ComplexityTier.MEDIUM:
        return 0.3, "no dependencies mentioned (recommended for medium complexity)"

    return 0.0, "no dependencies mentioned (expected for high complexity)"


# --- Main scoring function ---


def score_readiness(
    *,
    issue_title: str,
    issue_body: str,
    complexity_tier: ComplexityTier,
    risk_flags: dict[str, bool] | None = None,
    labels: list[str] | None = None,
    trust_tier: str = "observe",
    thresholds_override: ReadinessThresholds | None = None,
) -> ReadinessScore:
    """Score issue readiness across all 6 dimensions.

    Pure function — no I/O, no database, no external calls.

    Args:
        issue_title: The GitHub issue title.
        issue_body: The GitHub issue body (markdown).
        complexity_tier: Derived from complexity index score.
        risk_flags: Active risk flags from context enrichment.
        labels: GitHub issue labels.
        trust_tier: Repository trust tier ("observe", "suggest", "execute").
        thresholds_override: Optional repo-level threshold override.

    Returns:
        ReadinessScore with gate decision.
    """
    labels = labels or []
    full_text = f"{issue_title}\n\n{issue_body}"
    thresholds = get_thresholds(complexity_tier, thresholds_override)

    # Score each dimension
    scorers: dict[ReadinessDimension, tuple[float, str]] = {
        ReadinessDimension.GOAL_CLARITY: _score_goal_clarity(full_text),
        ReadinessDimension.ACCEPTANCE_CRITERIA: _score_acceptance_criteria(issue_body),
        ReadinessDimension.SCOPE_BOUNDARIES: _score_scope_boundaries(
            issue_body, complexity_tier
        ),
        ReadinessDimension.RISK_COVERAGE: _score_risk_coverage(
            issue_body, risk_flags
        ),
        ReadinessDimension.REPRODUCTION_CONTEXT: _score_reproduction_context(
            issue_body, labels
        ),
        ReadinessDimension.DEPENDENCY_AWARENESS: _score_dependency_awareness(
            issue_body, complexity_tier
        ),
    }

    dimension_scores: list[DimensionScore] = []
    for dim in ReadinessDimension:
        raw_score, reason = scorers[dim]
        clamped = max(0.0, min(1.0, raw_score))
        dimension_scores.append(
            DimensionScore(
                dimension=dim,
                score=clamped,
                reason=reason,
                required=dim in thresholds.required_dimensions,
            )
        )

    # Compute weighted overall score
    overall_score = sum(
        ds.score * thresholds.dimension_weights[ds.dimension]
        for ds in dimension_scores
    )

    # Find missing dimensions (below per-dimension threshold)
    missing: list[ReadinessDimension] = []
    for ds in dimension_scores:
        if ds.score < thresholds.per_dimension_thresholds[ds.dimension]:
            missing.append(ds.dimension)

    # Generate questions for missing dimensions
    questions: list[str] = []
    for dim in missing:
        dim_questions = _QUESTIONS.get(dim, [])
        if dim_questions:
            questions.append(dim_questions[0])

    # Determine gate decision
    gate_decision = _decide_gate(
        overall_score=overall_score,
        dimension_scores=dimension_scores,
        thresholds=thresholds,
        trust_tier=trust_tier,
    )

    return ReadinessScore(
        overall_score=round(overall_score, 4),
        dimension_scores=tuple(dimension_scores),
        missing_dimensions=tuple(missing),
        recommended_questions=tuple(questions),
        gate_decision=gate_decision,
        complexity_tier=complexity_tier,
    )


def _decide_gate(
    *,
    overall_score: float,
    dimension_scores: list[DimensionScore],
    thresholds: ReadinessThresholds,
    trust_tier: str,
) -> GateDecision:
    """Determine the gate decision.

    - Observe tier always passes (score recorded but not enforced).
    - Required dimensions scoring 0 force HOLD regardless of overall score.
    - Overall score below threshold forces HOLD.
    """
    # Observe tier: always pass (record score but don't enforce)
    if trust_tier == "observe":
        return GateDecision.PASS

    # Check required dimensions — any required dimension at 0 forces HOLD
    for ds in dimension_scores:
        if ds.required and ds.score == 0.0:
            return GateDecision.HOLD

    # Check overall threshold
    if overall_score < thresholds.overall_pass_threshold:
        return GateDecision.HOLD

    return GateDecision.PASS
