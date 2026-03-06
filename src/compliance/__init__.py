"""Compliance module — repo compliance checking for tier promotion.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Repo Compliance Scorecard, Execute Tier Compliance Gate, Repo Compliance Checker)
"""

from src.compliance.checker import ComplianceChecker
from src.compliance.models import (
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceResult,
    ComplianceResultRow,
)

__all__ = [
    "ComplianceCheck",
    "ComplianceCheckResult",
    "ComplianceChecker",
    "ComplianceResult",
    "ComplianceResultRow",
]
