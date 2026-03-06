"""QA Agent — validates implementation against Intent Specification.

Architecture reference: thestudioarc/14-qa-quality-layer.md

The QA Agent:
1. Validates acceptance criteria from Intent Specification
2. Classifies defects by category (8 types) and severity (S0-S3)
3. Blocks qa_passed when intent_gap defects exist
4. Emits qa_passed / qa_defect / qa_rework signals to JetStream
5. Triggers loopback to Primary Agent on failure
6. Requests intent refinement when criteria are ambiguous
"""

import logging
from dataclasses import dataclass, field

from src.assembler.assembler import QAHandoffMapping
from src.qa.defect import CriterionResult, DefectCategory, QADefect, Severity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentRefinementRequest:
    """Request to refine intent when acceptance criteria are ambiguous."""

    questions: list[str]
    source: str = "qa_agent"


@dataclass(frozen=True)
class LoopbackRequest:
    """Request to loop back to Primary Agent with defect list."""

    defects: list[QADefect]
    intent_mapping: dict[str, list[str]]  # criterion → defect descriptions


@dataclass
class QAResult:
    """Complete output of QA validation."""

    passed: bool = False
    criteria_results: list[CriterionResult] = field(default_factory=list)
    defects: list[QADefect] = field(default_factory=list)
    loopback: LoopbackRequest | None = None
    intent_refinement: IntentRefinementRequest | None = None
    has_intent_gap: bool = False


def validate(
    acceptance_criteria: list[str],
    qa_handoff: list[QAHandoffMapping],
    evidence: dict[str, object],
) -> QAResult:
    """Validate implementation against acceptance criteria.

    Args:
        acceptance_criteria: Criteria from Intent Specification.
        qa_handoff: QA handoff mappings from Assembler.
        evidence: Evidence bundle from implementation/verification.

    Returns:
        QAResult with pass/fail, defects, loopback request, or refinement request.
    """
    result = QAResult()

    # If no acceptance criteria, request intent refinement
    if not acceptance_criteria:
        result.intent_refinement = IntentRefinementRequest(
            questions=["No acceptance criteria found — cannot validate"],
        )
        result.has_intent_gap = True
        result.defects.append(
            QADefect(
                category=DefectCategory.INTENT_GAP,
                severity=Severity.S1_HIGH,
                description="No acceptance criteria provided in Intent Specification",
                acceptance_criterion="(none)",
            )
        )
        return result

    # Build handoff index for quick lookup
    handoff_index: dict[str, QAHandoffMapping] = {
        m.criterion: m for m in qa_handoff
    }

    # Validate each criterion
    for criterion in acceptance_criteria:
        criterion_result = _validate_criterion(
            criterion, handoff_index.get(criterion), evidence,
        )
        result.criteria_results.append(criterion_result)
        result.defects.extend(criterion_result.defects)

    # Check for intent_gap defects — blocks qa_passed
    result.has_intent_gap = any(
        d.category == DefectCategory.INTENT_GAP for d in result.defects
    )

    # Determine overall pass/fail
    all_criteria_passed = all(cr.passed for cr in result.criteria_results)
    result.passed = all_criteria_passed and not result.has_intent_gap

    # If failed, build loopback request
    if not result.passed and result.defects:
        intent_mapping: dict[str, list[str]] = {}
        for defect in result.defects:
            key = defect.acceptance_criterion
            if key not in intent_mapping:
                intent_mapping[key] = []
            intent_mapping[key].append(defect.description)

        result.loopback = LoopbackRequest(
            defects=result.defects,
            intent_mapping=intent_mapping,
        )

    # If intent_gap detected, request refinement
    if result.has_intent_gap:
        gap_criteria = [
            d.acceptance_criterion
            for d in result.defects
            if d.category == DefectCategory.INTENT_GAP
        ]
        result.intent_refinement = IntentRefinementRequest(
            questions=[
                f"Clarify acceptance criterion: {c}" for c in gap_criteria
            ],
        )

    logger.info(
        "QA validation: passed=%s, defects=%d, intent_gap=%s",
        result.passed, len(result.defects), result.has_intent_gap,
    )

    return result


def _validate_criterion(
    criterion: str,
    handoff: QAHandoffMapping | None,
    evidence: dict[str, object],
) -> CriterionResult:
    """Validate a single acceptance criterion against evidence.

    Uses the QA handoff mapping to determine which validations to check.
    """
    defects: list[QADefect] = []

    # Check if criterion is ambiguous (too short or vague)
    if len(criterion.strip()) < 10:
        defects.append(
            QADefect(
                category=DefectCategory.INTENT_GAP,
                severity=Severity.S1_HIGH,
                description=f"Acceptance criterion too vague: '{criterion}'",
                acceptance_criterion=criterion,
            )
        )
        return CriterionResult(
            criterion=criterion,
            passed=False,
            defects=tuple(defects),
        )

    # Check evidence for criterion satisfaction
    criterion_key = criterion.lower().strip()
    evidence_keys = {str(k).lower() for k in evidence.keys()}
    evidence_values = {str(v).lower() for v in evidence.values()}

    # Look for matching evidence
    has_evidence = False
    for key in evidence_keys | evidence_values:
        if _has_keyword_match(criterion_key, key):
            has_evidence = True
            break

    if not has_evidence:
        # No evidence found — classify based on criterion type
        category = _classify_defect_category(criterion)
        defects.append(
            QADefect(
                category=category,
                severity=Severity.S2_MEDIUM,
                description=f"No evidence found for criterion: {criterion}",
                acceptance_criterion=criterion,
            )
        )
        return CriterionResult(
            criterion=criterion,
            passed=False,
            defects=tuple(defects),
            evidence="No matching evidence",
        )

    # Evidence found — check handoff validations
    if handoff:
        for validation_step in handoff.validation_steps:
            validation_key = validation_step.lower()
            # Check if validation is satisfied in evidence
            validation_satisfied = any(
                _has_keyword_match(validation_key, str(v).lower())
                for v in evidence.values()
            )
            if not validation_satisfied:
                defects.append(
                    QADefect(
                        category=DefectCategory.IMPLEMENTATION_BUG,
                        severity=Severity.S2_MEDIUM,
                        description=f"Validation step not satisfied: {validation_step}",
                        acceptance_criterion=criterion,
                    )
                )

    passed = len(defects) == 0
    return CriterionResult(
        criterion=criterion,
        passed=passed,
        defects=tuple(defects),
        evidence="Evidence matched" if passed else "Partial evidence",
    )


def _classify_defect_category(criterion: str) -> DefectCategory:
    """Classify defect category from criterion keywords."""
    criterion_lower = criterion.lower()

    keyword_map: list[tuple[list[str], DefectCategory]] = [
        (["security", "auth", "secret", "encrypt"], DefectCategory.SECURITY),
        (["performance", "latency", "throughput"], DefectCategory.PERFORMANCE),
        (["compliance", "retention", "audit"], DefectCategory.COMPLIANCE),
        (["partner", "integration", "api contract"], DefectCategory.PARTNER_MISMATCH),
        (["logging", "metric", "alert", "runbook"], DefectCategory.OPERABILITY),
        (["regression", "previously", "broke"], DefectCategory.REGRESSION),
    ]

    for keywords, category in keyword_map:
        if any(kw in criterion_lower for kw in keywords):
            return category

    return DefectCategory.IMPLEMENTATION_BUG


def _has_keyword_match(text_a: str, text_b: str) -> bool:
    """Check if two texts share meaningful keywords (4+ chars)."""
    words_a = {w for w in text_a.split() if len(w) >= 4}
    words_b = {w for w in text_b.split() if len(w) >= 4}
    return bool(words_a & words_b)
