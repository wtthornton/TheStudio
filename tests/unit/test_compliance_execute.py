"""Unit tests for Execute tier compliance checks (Epic 22, Story 22.12).

Tests EXECUTE_TIER_POLICY check in ComplianceChecker and label requirements.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from src.admin.merge_mode import MergeMode
from src.compliance.checker import ComplianceChecker, GitHubRepoInfo
from src.compliance.models import (
    REQUIRED_LABELS,
    ComplianceCheck,
)


def _make_repo_info(**overrides) -> GitHubRepoInfo:
    defaults = {
        "owner": "acme",
        "repo": "widgets",
        "default_branch": "main",
        "rulesets": [{"rules": [{"type": "required_status_checks"}]}],
        "branch_protection": {
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
            }
        },
        "labels": REQUIRED_LABELS + ["tier:observe", "tier:suggest"],
        "codeowners_exists": True,
        "codeowners_paths": ["auth/**", "billing/**", "exports/**", "infra/**"],
    }
    defaults.update(overrides)
    return GitHubRepoInfo(**defaults)


class TestExecuteTierPolicyCheck:
    """Tests for _check_execute_tier_policy."""

    @pytest.mark.asyncio
    async def test_passes_when_all_conditions_met(self) -> None:
        """All conditions met: AUTO_MERGE + full CODEOWNERS coverage."""
        repo_info = _make_repo_info()
        checker = ComplianceChecker()

        with patch(
            "src.compliance.checker.get_merge_mode",
            return_value=MergeMode.AUTO_MERGE,
        ):
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=repo_info,
                triggered_by="test",
                check_execution_plane=False,
                target_tier="execute",
                repo_full_name="acme/widgets",
            )

        execute_check = next(
            c for c in result.checks
            if c.check == ComplianceCheck.EXECUTE_TIER_POLICY
        )
        assert execute_check.passed is True

    @pytest.mark.asyncio
    async def test_fails_when_merge_mode_not_auto(self) -> None:
        """Fails when merge mode is REQUIRE_REVIEW instead of AUTO_MERGE."""
        repo_info = _make_repo_info()
        checker = ComplianceChecker()

        with patch(
            "src.compliance.checker.get_merge_mode",
            return_value=MergeMode.REQUIRE_REVIEW,
        ):
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=repo_info,
                triggered_by="test",
                check_execution_plane=False,
                target_tier="execute",
                repo_full_name="acme/widgets",
            )

        execute_check = next(
            c for c in result.checks
            if c.check == ComplianceCheck.EXECUTE_TIER_POLICY
        )
        assert execute_check.passed is False
        assert "auto_merge" in execute_check.failure_reason

    @pytest.mark.asyncio
    async def test_fails_when_no_codeowners(self) -> None:
        """Fails when CODEOWNERS file is missing."""
        repo_info = _make_repo_info(
            codeowners_exists=False, codeowners_paths=[],
        )
        checker = ComplianceChecker()

        with patch(
            "src.compliance.checker.get_merge_mode",
            return_value=MergeMode.AUTO_MERGE,
        ):
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=repo_info,
                triggered_by="test",
                check_execution_plane=False,
                target_tier="execute",
                repo_full_name="acme/widgets",
            )

        execute_check = next(
            c for c in result.checks
            if c.check == ComplianceCheck.EXECUTE_TIER_POLICY
        )
        assert execute_check.passed is False
        assert "CODEOWNERS" in execute_check.failure_reason

    @pytest.mark.asyncio
    async def test_fails_when_codeowners_incomplete(self) -> None:
        """Fails when CODEOWNERS doesn't cover all sensitive paths."""
        repo_info = _make_repo_info(
            codeowners_paths=["auth/**"],  # missing billing, exports, infra
        )
        checker = ComplianceChecker()

        with patch(
            "src.compliance.checker.get_merge_mode",
            return_value=MergeMode.AUTO_MERGE,
        ):
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=repo_info,
                triggered_by="test",
                check_execution_plane=False,
                target_tier="execute",
                repo_full_name="acme/widgets",
            )

        execute_check = next(
            c for c in result.checks
            if c.check == ComplianceCheck.EXECUTE_TIER_POLICY
        )
        assert execute_check.passed is False
        assert "sensitive paths" in execute_check.failure_reason

    @pytest.mark.asyncio
    async def test_not_run_for_suggest_tier(self) -> None:
        """EXECUTE_TIER_POLICY check not included for suggest tier target."""
        repo_info = _make_repo_info()
        checker = ComplianceChecker()

        result = await checker.check_compliance(
            repo_id=uuid4(),
            repo_info=repo_info,
            triggered_by="test",
            check_execution_plane=False,
            target_tier="suggest",
        )

        check_names = [c.check for c in result.checks]
        assert ComplianceCheck.EXECUTE_TIER_POLICY not in check_names

    @pytest.mark.asyncio
    async def test_overall_fails_when_execute_policy_fails(self) -> None:
        """Overall compliance result fails if EXECUTE_TIER_POLICY fails."""
        repo_info = _make_repo_info()
        checker = ComplianceChecker()

        with patch(
            "src.compliance.checker.get_merge_mode",
            return_value=MergeMode.DRAFT_ONLY,
        ):
            result = await checker.check_compliance(
                repo_id=uuid4(),
                repo_info=repo_info,
                triggered_by="test",
                check_execution_plane=False,
                target_tier="execute",
                repo_full_name="acme/widgets",
            )

        assert result.overall_passed is False


class TestRequiredLabelsIncludeExecute:
    def test_tier_execute_in_required_labels(self) -> None:
        assert "tier:execute" in REQUIRED_LABELS

    def test_remediation_hint_exists(self) -> None:
        from src.compliance.models import REMEDIATION_HINTS

        assert ComplianceCheck.EXECUTE_TIER_POLICY in REMEDIATION_HINTS
