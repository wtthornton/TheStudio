"""Compliance module — repo compliance checking for tier promotion.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Repo Compliance Scorecard, Execute Tier Compliance Gate, Repo Compliance Checker)
"""

from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.execution_plane import (
    CredentialScopeChecker,
    CredentialScopeHealth,
    ExecutionPlaneChecker,
    ExecutionPlaneHealth,
    PublisherIdempotencyChecker,
    PublisherIdempotencyHealth,
)
from src.compliance.models import (
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceResult,
    ComplianceResultRow,
)
from src.compliance.promotion import (
    DemotionResult,
    EligibilityResult,
    PromotionBlockReason,
    PromotionResult,
    PromotionService,
    TierTransition,
)

__all__ = [
    "ComplianceCheck",
    "ComplianceCheckResult",
    "ComplianceChecker",
    "ComplianceResult",
    "ComplianceResultRow",
    "CredentialScopeChecker",
    "CredentialScopeHealth",
    "DemotionResult",
    "EligibilityResult",
    "ExecutionPlaneChecker",
    "ExecutionPlaneHealth",
    "GitHubRepoInfo",
    "PromotionBlockReason",
    "PromotionResult",
    "PromotionService",
    "PublisherIdempotencyChecker",
    "PublisherIdempotencyHealth",
    "TierTransition",
]
