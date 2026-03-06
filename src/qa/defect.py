"""QA defect taxonomy and severity — structured defect classification.

Architecture reference: thestudioarc/14-qa-quality-layer.md

Defect categories and severity rubric for consistent classification.
"""

import enum
from dataclasses import dataclass


class DefectCategory(enum.StrEnum):
    """Defect categories per 14-qa-quality-layer.md."""

    INTENT_GAP = "intent_gap"
    IMPLEMENTATION_BUG = "implementation_bug"
    REGRESSION = "regression"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    PARTNER_MISMATCH = "partner_mismatch"
    OPERABILITY = "operability"


class Severity(enum.StrEnum):
    """Severity rubric per 14-qa-quality-layer.md."""

    S0_CRITICAL = "S0"  # security breach, data loss, billing impact, compliance breach
    S1_HIGH = "S1"  # major user impact or repeated failures likely
    S2_MEDIUM = "S2"  # limited impact, workaround exists
    S3_LOW = "S3"  # minor, cosmetic, non-blocking


@dataclass(frozen=True)
class QADefect:
    """A single defect found during QA validation."""

    category: DefectCategory
    severity: Severity
    description: str
    acceptance_criterion: str  # Which criterion this maps to
    evidence: str = ""


@dataclass(frozen=True)
class CriterionResult:
    """Result of validating a single acceptance criterion."""

    criterion: str
    passed: bool
    defects: tuple[QADefect, ...] = ()
    evidence: str = ""
