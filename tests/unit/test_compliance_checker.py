"""Tests for Story 3.1: Compliance Checker Core Checks.

Validates that the compliance checker correctly evaluates:
- Rulesets with required status checks
- Required reviewers for sensitive paths
- Branch protection on default branch
- Standard agent labels
- Projects v2 integration (or waiver)
"""

from typing import Any
from uuid import uuid4

import pytest

from src.compliance.checker import (
    ComplianceChecker,
    GitHubRepoInfo,
    clear,
    get_all_results,
    get_latest_result,
    store_result,
)
from src.compliance.models import (
    REMEDIATION_HINTS,
    REQUIRED_LABELS,
    ComplianceCheck,
)


@pytest.fixture(autouse=True)
def clear_state() -> None:
    """Clear compliance results before each test."""
    clear()


def make_repo_info(
    *,
    owner: str = "test-org",
    repo: str = "test-repo",
    default_branch: str = "main",
    rulesets: list[dict[str, Any]] | None = None,
    branch_protection: dict[str, Any] | None = None,
    labels: list[str] | None = None,
    codeowners_exists: bool = False,
    codeowners_paths: list[str] | None = None,
) -> GitHubRepoInfo:
    """Helper to create GitHubRepoInfo with sensible defaults."""
    return GitHubRepoInfo(
        owner=owner,
        repo=repo,
        default_branch=default_branch,
        rulesets=rulesets or [],
        branch_protection=branch_protection,
        labels=labels or [],
        codeowners_exists=codeowners_exists,
        codeowners_paths=codeowners_paths or [],
    )


class TestRulesetsCheck:
    """Tests for rulesets_configured check."""

    @pytest.mark.asyncio
    async def test_no_rulesets_fails(self) -> None:
        """No rulesets -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(rulesets=[])

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        rulesets_check = next(
            c for c in result.checks if c.check == ComplianceCheck.RULESETS_CONFIGURED
        )
        assert rulesets_check.passed is False
        assert "No rulesets configured" in (rulesets_check.failure_reason or "")
        assert rulesets_check.remediation_hint is not None

    @pytest.mark.asyncio
    async def test_rulesets_without_status_checks_fails(self) -> None:
        """Rulesets without required status checks -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            rulesets=[
                {"name": "branch-name-policy", "rules": [{"type": "branch_name_pattern"}]}
            ]
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        rulesets_check = next(
            c for c in result.checks if c.check == ComplianceCheck.RULESETS_CONFIGURED
        )
        assert rulesets_check.passed is False
        assert "none have required status checks" in (rulesets_check.failure_reason or "")

    @pytest.mark.asyncio
    async def test_rulesets_with_status_checks_passes(self) -> None:
        """Rulesets with required status checks -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            rulesets=[
                {
                    "name": "ci-checks",
                    "rules": [
                        {"type": "required_status_checks", "parameters": {"checks": ["test"]}}
                    ],
                }
            ]
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        rulesets_check = next(
            c for c in result.checks if c.check == ComplianceCheck.RULESETS_CONFIGURED
        )
        assert rulesets_check.passed is True
        assert rulesets_check.details is not None
        assert rulesets_check.details.get("rulesets_with_status_checks") == 1


class TestRequiredReviewersCheck:
    """Tests for required_reviewers check."""

    @pytest.mark.asyncio
    async def test_no_codeowners_no_branch_protection_fails(self) -> None:
        """No CODEOWNERS and no branch protection reviewers -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(codeowners_exists=False, branch_protection=None)

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        reviewers_check = next(
            c for c in result.checks if c.check == ComplianceCheck.REQUIRED_REVIEWERS
        )
        assert reviewers_check.passed is False
        assert "No CODEOWNERS file" in (reviewers_check.failure_reason or "")

    @pytest.mark.asyncio
    async def test_branch_protection_with_reviewers_passes(self) -> None:
        """Branch protection with required reviewers -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            codeowners_exists=False,
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        reviewers_check = next(
            c for c in result.checks if c.check == ComplianceCheck.REQUIRED_REVIEWERS
        )
        assert reviewers_check.passed is True
        assert reviewers_check.details is not None
        assert reviewers_check.details.get("method") == "branch_protection"

    @pytest.mark.asyncio
    async def test_codeowners_exists_passes(self) -> None:
        """CODEOWNERS file exists -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            codeowners_exists=True,
            codeowners_paths=["auth/**", "billing/**"],
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        reviewers_check = next(
            c for c in result.checks if c.check == ComplianceCheck.REQUIRED_REVIEWERS
        )
        assert reviewers_check.passed is True


class TestBranchProtectionCheck:
    """Tests for branch_protection check."""

    @pytest.mark.asyncio
    async def test_no_branch_protection_fails(self) -> None:
        """No branch protection -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(branch_protection=None)

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        protection_check = next(
            c for c in result.checks if c.check == ComplianceCheck.BRANCH_PROTECTION
        )
        assert protection_check.passed is False
        assert "Branch protection not enabled" in (protection_check.failure_reason or "")

    @pytest.mark.asyncio
    async def test_branch_protection_without_pr_reviews_fails(self) -> None:
        """Branch protection without PR reviews -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            branch_protection={"enforce_admins": True}  # No required_pull_request_reviews
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        protection_check = next(
            c for c in result.checks if c.check == ComplianceCheck.BRANCH_PROTECTION
        )
        assert protection_check.passed is False
        assert "required PR reviews not configured" in (protection_check.failure_reason or "")

    @pytest.mark.asyncio
    async def test_branch_protection_with_pr_reviews_passes(self) -> None:
        """Branch protection with PR reviews -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            branch_protection={
                "required_pull_request_reviews": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews": True,
                }
            }
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        protection_check = next(
            c for c in result.checks if c.check == ComplianceCheck.BRANCH_PROTECTION
        )
        assert protection_check.passed is True
        assert protection_check.details is not None
        assert protection_check.details.get("dismiss_stale_reviews") is True


class TestLabelsCheck:
    """Tests for labels_exist check."""

    @pytest.mark.asyncio
    async def test_no_labels_fails(self) -> None:
        """No agent labels -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(labels=[])

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        labels_check = next(
            c for c in result.checks if c.check == ComplianceCheck.LABELS_EXIST
        )
        assert labels_check.passed is False
        assert "Missing required labels" in (labels_check.failure_reason or "")

    @pytest.mark.asyncio
    async def test_partial_labels_fails(self) -> None:
        """Some but not all required labels -> check fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(labels=["agent:in-progress", "agent:done"])

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        labels_check = next(
            c for c in result.checks if c.check == ComplianceCheck.LABELS_EXIST
        )
        assert labels_check.passed is False
        assert labels_check.details is not None
        missing = labels_check.details.get("missing_labels")
        assert isinstance(missing, list)
        assert "agent:queued" in missing
        assert "agent:blocked" in missing

    @pytest.mark.asyncio
    async def test_all_labels_passes(self) -> None:
        """All required labels present -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(labels=REQUIRED_LABELS.copy())

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        labels_check = next(
            c for c in result.checks if c.check == ComplianceCheck.LABELS_EXIST
        )
        assert labels_check.passed is True


class TestProjectsV2Check:
    """Tests for projects_v2 check."""

    @pytest.mark.asyncio
    async def test_projects_v2_waived_passes(self) -> None:
        """Projects v2 explicitly waived -> check passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info()

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        projects_check = next(
            c for c in result.checks if c.check == ComplianceCheck.PROJECTS_V2
        )
        assert projects_check.passed is True
        assert projects_check.details is not None
        assert projects_check.details.get("waived") is True


class TestOverallCompliance:
    """Tests for overall compliance result."""

    @pytest.mark.asyncio
    async def test_all_checks_pass_overall_passes(self) -> None:
        """All checks pass -> overall compliance passes."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            rulesets=[
                {"name": "ci", "rules": [{"type": "required_status_checks"}]}
            ],
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },
            labels=REQUIRED_LABELS.copy(),
            codeowners_exists=True,
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        assert result.overall_passed is True
        assert result.score == 100.0
        assert all(c.passed for c in result.checks)

    @pytest.mark.asyncio
    async def test_any_check_fails_overall_fails(self) -> None:
        """Any check fails -> overall compliance fails."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            rulesets=[
                {"name": "ci", "rules": [{"type": "required_status_checks"}]}
            ],
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },
            labels=[],  # Missing labels
            codeowners_exists=True,
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        assert result.overall_passed is False
        assert result.score < 100.0

    @pytest.mark.asyncio
    async def test_compliance_score_calculation(self) -> None:
        """Score is percentage of checks passed."""
        checker = ComplianceChecker()
        # 2 of 5 checks will fail: rulesets (no rulesets), labels (no labels)
        repo_info = make_repo_info(
            rulesets=[],  # Fail
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },  # Pass
            labels=[],  # Fail
            codeowners_exists=True,  # Pass (required_reviewers)
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            projects_v2_waived=True,  # Pass
            check_execution_plane=False,
        )

        # 3 passed (branch_protection, required_reviewers, projects_v2)
        # 2 failed (rulesets, labels)
        assert result.score == 60.0  # 3/5 = 60%


class TestRemediationHints:
    """Tests for remediation hints."""

    @pytest.mark.asyncio
    async def test_failed_checks_have_remediation_hints(self) -> None:
        """Failed checks include remediation hints."""
        checker = ComplianceChecker()
        repo_info = make_repo_info(
            rulesets=[],
            labels=[],
            branch_protection=None,
        )

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        failed_checks = [c for c in result.checks if not c.passed]
        for check in failed_checks:
            assert check.remediation_hint is not None
            assert len(check.remediation_hint) > 0

    def test_all_checks_have_remediation_hints_defined(self) -> None:
        """All ComplianceCheck values have remediation hints."""
        for check in ComplianceCheck:
            assert check in REMEDIATION_HINTS
            assert len(REMEDIATION_HINTS[check]) > 0


class TestResultStorage:
    """Tests for compliance result storage (in-memory stub)."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_result(self) -> None:
        """Can store and retrieve compliance results."""
        checker = ComplianceChecker()
        repo_id = uuid4()
        repo_info = make_repo_info()

        result = await checker.check_compliance(
            repo_id=repo_id,
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
        )

        store_result(result)

        retrieved = get_latest_result(repo_id)
        assert retrieved is not None
        assert retrieved.repo_id == repo_id
        assert retrieved.triggered_by == "test"

    @pytest.mark.asyncio
    async def test_get_all_results(self) -> None:
        """Can retrieve all results for a repo."""
        checker = ComplianceChecker()
        repo_id = uuid4()
        repo_info = make_repo_info()

        # Store multiple results
        for i in range(3):
            result = await checker.check_compliance(
                repo_id=repo_id,
                repo_info=repo_info,
                triggered_by=f"test-{i}",
                check_execution_plane=False,
            )
            store_result(result)

        all_results = get_all_results(repo_id)
        assert len(all_results) == 3

    def test_get_latest_returns_none_for_unknown_repo(self) -> None:
        """get_latest_result returns None for unknown repo."""
        result = get_latest_result(uuid4())
        assert result is None


class TestIdempotency:
    """Tests for compliance checker idempotency."""

    @pytest.mark.asyncio
    async def test_same_input_same_output(self) -> None:
        """Same repo state produces same result."""
        checker = ComplianceChecker()
        repo_id = uuid4()
        repo_info = make_repo_info(
            rulesets=[{"name": "ci", "rules": [{"type": "required_status_checks"}]}],
            branch_protection={
                "required_pull_request_reviews": {"required_approving_review_count": 1}
            },
            labels=REQUIRED_LABELS.copy(),
            codeowners_exists=True,
        )

        result1 = await checker.check_compliance(
            repo_id=repo_id,
            repo_info=repo_info,
            triggered_by="test-1",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        result2 = await checker.check_compliance(
            repo_id=repo_id,
            repo_info=repo_info,
            triggered_by="test-2",
            projects_v2_waived=True,
            check_execution_plane=False,
        )

        # Same inputs -> same pass/fail results
        assert result1.overall_passed == result2.overall_passed
        assert result1.score == result2.score
        assert len(result1.checks) == len(result2.checks)

        for c1, c2 in zip(result1.checks, result2.checks, strict=True):
            assert c1.check == c2.check
            assert c1.passed == c2.passed
