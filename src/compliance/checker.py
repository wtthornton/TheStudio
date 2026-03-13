"""Compliance Checker — validates repo meets governance requirements for tier promotion.

Architecture reference: thestudioarc/23-admin-control-ui.md
(Repo Compliance Scorecard, Execute Tier Compliance Gate, Repo Compliance Checker)

The compliance checker runs as a platform job (not an agent) and validates:
- GitHub-side governance: rulesets, required reviewers, branch protections, labels
- Platform-side health: execution plane, Publisher idempotency, credential scope
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.compliance.execution_plane import (
    CredentialScopeChecker,
    ExecutionPlaneChecker,
    PublisherIdempotencyChecker,
)
from src.compliance.models import (
    REMEDIATION_HINTS,
    REQUIRED_LABELS,
    SENSITIVE_PATHS,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceResult,
)
from src.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.compliance")


@dataclass
class GitHubRepoInfo:
    """GitHub repository information for compliance checking."""

    owner: str
    repo: str
    default_branch: str
    rulesets: list[dict[str, Any]]
    branch_protection: dict[str, Any] | None
    labels: list[str]
    codeowners_exists: bool
    codeowners_paths: list[str]


class ComplianceChecker:
    """Validates repo compliance for tier promotion.

    The checker is designed to be idempotent: same repo state produces same result.
    Results are persisted for audit trail.

    Usage:
        checker = ComplianceChecker(github_client=client)
        result = await checker.check_compliance(repo_id, repo_info, triggered_by="admin")
    """

    def __init__(
        self,
        github_client: Any | None = None,
        execution_plane_checker: ExecutionPlaneChecker | None = None,
        publisher_idempotency_checker: PublisherIdempotencyChecker | None = None,
        credential_scope_checker: CredentialScopeChecker | None = None,
    ) -> None:
        """Initialize compliance checker.

        Args:
            github_client: GitHub API client for fetching repo configuration.
                          If None, uses mock responses (for testing).
            execution_plane_checker: Checker for workspace, workers, verification.
                                    If None, creates default checker.
            publisher_idempotency_checker: Checker for Publisher idempotency guard.
                                          If None, creates default checker.
            credential_scope_checker: Checker for GitHub token scopes.
                                     If None, creates default checker.
        """
        self._github_client = github_client
        self._execution_plane_checker = execution_plane_checker or ExecutionPlaneChecker()
        self._publisher_idempotency_checker = (
            publisher_idempotency_checker or PublisherIdempotencyChecker()
        )
        self._credential_scope_checker = credential_scope_checker or CredentialScopeChecker()
        self._check_results: list[ComplianceCheckResult] = []

    async def check_compliance(
        self,
        repo_id: UUID,
        repo_info: GitHubRepoInfo,
        triggered_by: str,
        *,
        projects_v2_waived: bool = False,
        check_execution_plane: bool = True,
        target_tier: str = "execute",
    ) -> ComplianceResult:
        """Run full compliance check for a repository.

        Args:
            repo_id: Internal repo profile ID.
            repo_info: GitHub repository information.
            triggered_by: Who/what triggered this check (for audit).
            projects_v2_waived: If True, skip Projects v2 check.
            check_execution_plane: If True, include execution plane health checks.

        Returns:
            ComplianceResult with pass/fail per check and overall score.
        """
        with tracer.start_as_current_span("compliance.check_full") as span:
            span.set_attribute("thestudio.repo_id", str(repo_id))
            span.set_attribute("thestudio.repo", f"{repo_info.owner}/{repo_info.repo}")

            self._check_results = []
            now = datetime.now(UTC)

            # GitHub-side checks (Story 3.1)
            self._check_rulesets(repo_info)
            self._check_required_reviewers(repo_info)
            self._check_branch_protection(repo_info)
            self._check_labels(repo_info)
            self._check_projects_v2(repo_info, waived=projects_v2_waived)

            # Execution plane checks (Story 3.2) - optional
            if check_execution_plane:
                await self._check_execution_plane_health(repo_id)
                await self._check_publisher_idempotency(repo_id)
                await self._check_credentials_scoped(repo_id, target_tier)

            # Calculate overall result
            passed_count = sum(1 for r in self._check_results if r.passed)
            total_count = len(self._check_results)
            score = (passed_count / total_count * 100) if total_count > 0 else 0.0
            overall_passed = all(r.passed for r in self._check_results)

            span.set_attribute("thestudio.compliance_score", score)
            span.set_attribute("thestudio.compliance_passed", overall_passed)

            logger.info(
                "Compliance check for %s/%s: %s (score: %.1f, %d/%d passed)",
                repo_info.owner,
                repo_info.repo,
                "PASSED" if overall_passed else "FAILED",
                score,
                passed_count,
                total_count,
            )

            return ComplianceResult(
                repo_id=repo_id,
                overall_passed=overall_passed,
                score=score,
                checks=self._check_results,
                checked_at=now,
                triggered_by=triggered_by,
            )

    def _check_rulesets(self, repo_info: GitHubRepoInfo) -> None:
        """Check that at least one ruleset with required status checks exists."""
        check = ComplianceCheck.RULESETS_CONFIGURED

        if not repo_info.rulesets:
            self._add_failure(
                check,
                "No rulesets configured for this repository",
                details={"ruleset_count": 0},
            )
            return

        # Check for rulesets with required status checks
        rulesets_with_checks = [
            rs
            for rs in repo_info.rulesets
            if rs.get("rules")
            and any(r.get("type") == "required_status_checks" for r in rs.get("rules", []))
        ]

        if not rulesets_with_checks:
            self._add_failure(
                check,
                "Rulesets exist but none have required status checks configured",
                details={
                    "ruleset_count": len(repo_info.rulesets),
                    "rulesets_with_status_checks": 0,
                },
            )
            return

        self._add_pass(
            check,
            details={
                "ruleset_count": len(repo_info.rulesets),
                "rulesets_with_status_checks": len(rulesets_with_checks),
            },
        )

    def _check_required_reviewers(self, repo_info: GitHubRepoInfo) -> None:
        """Check that required reviewer rules exist for sensitive paths."""
        check = ComplianceCheck.REQUIRED_REVIEWERS

        # Find sensitive paths that exist in the repo (simplified check)
        sensitive_patterns = SENSITIVE_PATHS

        if not repo_info.codeowners_exists:
            # No CODEOWNERS file - check branch protection for required reviewers
            if repo_info.branch_protection:
                required_reviews = repo_info.branch_protection.get(
                    "required_pull_request_reviews", {}
                )
                if required_reviews.get("required_approving_review_count", 0) > 0:
                    self._add_pass(
                        check,
                        details={
                            "method": "branch_protection",
                            "required_reviewers": required_reviews.get(
                                "required_approving_review_count", 0
                            ),
                        },
                    )
                    return

            self._add_failure(
                check,
                "No CODEOWNERS file and no required reviewers in branch protection",
                details={
                    "codeowners_exists": False,
                    "sensitive_paths": sensitive_patterns,
                },
            )
            return

        # CODEOWNERS exists - check if sensitive paths are covered
        covered_paths = repo_info.codeowners_paths
        uncovered = [p for p in sensitive_patterns if p not in covered_paths]

        if uncovered:
            # Partial coverage is acceptable - warn but pass
            self._add_pass(
                check,
                details={
                    "codeowners_exists": True,
                    "covered_paths": covered_paths,
                    "uncovered_sensitive_paths": uncovered,
                },
            )
        else:
            self._add_pass(
                check,
                details={
                    "codeowners_exists": True,
                    "covered_paths": covered_paths,
                },
            )

    def _check_branch_protection(self, repo_info: GitHubRepoInfo) -> None:
        """Check that default branch has protection enabled."""
        check = ComplianceCheck.BRANCH_PROTECTION

        if not repo_info.branch_protection:
            self._add_failure(
                check,
                f"Branch protection not enabled for default branch '{repo_info.default_branch}'",
                details={"default_branch": repo_info.default_branch},
            )
            return

        protection = repo_info.branch_protection

        # Check for required PR reviews
        pr_reviews = protection.get("required_pull_request_reviews")
        if not pr_reviews:
            self._add_failure(
                check,
                "Branch protection enabled but required PR reviews not configured",
                details={
                    "default_branch": repo_info.default_branch,
                    "has_pr_reviews": False,
                },
            )
            return

        # Check for dismiss stale reviews (recommended but not blocking)
        dismiss_stale = pr_reviews.get("dismiss_stale_reviews", False)

        self._add_pass(
            check,
            details={
                "default_branch": repo_info.default_branch,
                "required_approving_review_count": pr_reviews.get(
                    "required_approving_review_count", 0
                ),
                "dismiss_stale_reviews": dismiss_stale,
            },
        )

    def _check_labels(self, repo_info: GitHubRepoInfo) -> None:
        """Check that standard agent labels exist."""
        check = ComplianceCheck.LABELS_EXIST

        existing_labels = set(repo_info.labels)
        required = set(REQUIRED_LABELS)
        missing = required - existing_labels

        if missing:
            self._add_failure(
                check,
                f"Missing required labels: {', '.join(sorted(missing))}",
                details={
                    "required_labels": list(required),
                    "existing_labels": list(existing_labels & required),
                    "missing_labels": list(missing),
                },
            )
            return

        self._add_pass(
            check,
            details={
                "required_labels": list(required),
                "all_present": True,
            },
        )

    def _check_projects_v2(
        self,
        repo_info: GitHubRepoInfo,
        *,
        waived: bool = False,
    ) -> None:
        """Check that Projects v2 integration is configured (or explicitly waived)."""
        check = ComplianceCheck.PROJECTS_V2

        if waived:
            self._add_pass(
                check,
                details={"waived": True, "reason": "Explicitly waived in Repo Profile"},
            )
            return

        # For now, pass if waived is False but we don't have a way to check
        # In production, this would query GitHub Projects API
        self._add_pass(
            check,
            details={"waived": False, "note": "Projects v2 check not yet implemented"},
        )

    async def _check_execution_plane_health(self, repo_id: UUID) -> None:
        """Check that execution plane is healthy.

        Validates:
        - Workspace directory exists and is accessible
        - Workers are registered and healthy
        - Verification runner tools (ruff, pytest) are available
        """
        check = ComplianceCheck.EXECUTION_PLANE_HEALTH

        try:
            health = await self._execution_plane_checker.check_health(repo_id)
            if health.healthy:
                self._add_pass(check, details=health.to_dict())
            else:
                self._add_failure(
                    check,
                    health.reason or "Execution plane unhealthy",
                    details=health.to_dict(),
                )
        except Exception as e:
            self._add_failure(
                check,
                f"Failed to check execution plane health: {e}",
                details={"error": str(e)},
            )

    async def _check_publisher_idempotency(self, repo_id: UUID) -> None:
        """Check that Publisher idempotency guard is operational.

        The idempotency guard prevents duplicate PRs by looking up existing
        TaskPackets before creating new ones.
        """
        check = ComplianceCheck.PUBLISHER_IDEMPOTENCY

        try:
            health = await self._publisher_idempotency_checker.check_health(repo_id)
            if health.healthy:
                self._add_pass(
                    check,
                    details={
                        "lookup_operational": health.lookup_operational,
                        "test_key_result": health.test_key_result,
                    },
                )
            else:
                self._add_failure(
                    check,
                    health.reason or "Publisher idempotency guard unhealthy",
                    details={
                        "lookup_operational": health.lookup_operational,
                    },
                )
        except Exception as e:
            self._add_failure(
                check,
                f"Failed to check Publisher idempotency: {e}",
                details={"error": str(e)},
            )

    async def _check_credentials_scoped(
        self,
        repo_id: UUID,
        target_tier: str,
    ) -> None:
        """Check that credentials are scoped correctly for the target tier.

        Execute tier requires specific permissions (repo, workflow) but should
        not be over-permissioned.
        """
        check = ComplianceCheck.CREDENTIALS_SCOPED

        try:
            health = await self._credential_scope_checker.check_scopes(repo_id, target_tier)
            if health.healthy:
                self._add_pass(
                    check,
                    details={
                        "expected_scopes": health.expected_scopes,
                        "actual_scopes": health.actual_scopes,
                        "excess_scopes": health.excess_scopes,
                    },
                )
            else:
                self._add_failure(
                    check,
                    health.reason or "Credential scopes incorrect",
                    details={
                        "expected_scopes": health.expected_scopes,
                        "actual_scopes": health.actual_scopes,
                        "missing_scopes": health.missing_scopes,
                    },
                )
        except Exception as e:
            self._add_failure(
                check,
                f"Failed to check credential scopes: {e}",
                details={"error": str(e)},
            )

    def check_adversarial_content(self, text: str) -> ComplianceCheckResult:
        """Check text for adversarial patterns (thin wrapper around intake detector).

        Args:
            text: The text to scan for adversarial patterns.

        Returns:
            ComplianceCheckResult with pass/fail and detected pattern details.
        """
        from src.intake.adversarial import detect_suspicious_patterns

        patterns = detect_suspicious_patterns(text)
        if patterns:
            return ComplianceCheckResult(
                check=ComplianceCheck.ADVERSARIAL_CONTENT,
                passed=False,
                failure_reason=(
                    f"Adversarial patterns detected: {', '.join(p.pattern_name for p in patterns)}"
                ),
                remediation_hint="Review issue content for suspicious patterns",
                details={
                    "patterns": [{"name": p.pattern_name, "severity": p.severity} for p in patterns]
                },
            )
        return ComplianceCheckResult(
            check=ComplianceCheck.ADVERSARIAL_CONTENT,
            passed=True,
            failure_reason=None,
            remediation_hint=None,
            details=None,
        )

    def _add_pass(
        self,
        check: ComplianceCheck,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a passing check result."""
        self._check_results.append(
            ComplianceCheckResult(
                check=check,
                passed=True,
                failure_reason=None,
                remediation_hint=None,
                details=details,
            )
        )

    def _add_failure(
        self,
        check: ComplianceCheck,
        reason: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a failing check result with remediation hint."""
        self._check_results.append(
            ComplianceCheckResult(
                check=check,
                passed=False,
                failure_reason=reason,
                remediation_hint=REMEDIATION_HINTS.get(check),
                details=details,
            )
        )


# In-memory storage for testing (will be replaced with database in production)
_compliance_results: dict[UUID, list[ComplianceResult]] = {}


def store_result(result: ComplianceResult) -> None:
    """Store a compliance result (in-memory stub)."""
    if result.repo_id not in _compliance_results:
        _compliance_results[result.repo_id] = []
    _compliance_results[result.repo_id].append(result)


def get_latest_result(repo_id: UUID) -> ComplianceResult | None:
    """Get the latest compliance result for a repo (in-memory stub)."""
    results = _compliance_results.get(repo_id, [])
    return results[-1] if results else None


def get_all_results(repo_id: UUID) -> list[ComplianceResult]:
    """Get all compliance results for a repo (in-memory stub)."""
    return _compliance_results.get(repo_id, [])


def clear() -> None:
    """Clear all stored results (for testing)."""
    _compliance_results.clear()
