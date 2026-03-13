"""Tests for Compliance Scorecard Service (Story 7.7)."""

import pytest

from src.admin.compliance_scorecard import (
    ComplianceScorecard,
    ComplianceScorecardService,
    RepoComplianceData,
    ScorecardCheck,
)


@pytest.fixture
def service():
    return ComplianceScorecardService()


class TestScorecardCheck:
    def test_to_dict(self):
        check = ScorecardCheck("test", "A test check", True, "All good")
        d = check.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True
        assert d["details"] == "All good"

    def test_failed_check(self):
        check = ScorecardCheck("test", "A test check", False, "Not configured")
        assert check.passed is False


class TestComplianceScorecard:
    def test_to_dict_all_pass(self):
        checks = [ScorecardCheck(f"c{i}", f"Check {i}", True) for i in range(7)]
        sc = ComplianceScorecard(repo_id="repo-1", checks=checks, overall_pass=True)
        d = sc.to_dict()
        assert d["overall_pass"] is True
        assert d["checks_passed"] == 7
        assert d["checks_total"] == 7

    def test_to_dict_partial_fail(self):
        checks = [
            ScorecardCheck("a", "A", True),
            ScorecardCheck("b", "B", False),
        ]
        sc = ComplianceScorecard(repo_id="repo-1", checks=checks, overall_pass=False)
        d = sc.to_dict()
        assert d["overall_pass"] is False
        assert d["checks_passed"] == 1
        assert d["checks_total"] == 2


class TestComplianceScorecardService:
    def test_all_checks_pass(self, service):
        data = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
            execute_tier_policy_passed=True,
        )
        result = service.evaluate("repo-1", data)
        assert result.overall_pass is True
        assert len(result.checks) == 8
        assert all(c.passed for c in result.checks)

    def test_all_checks_fail(self, service):
        data = RepoComplianceData()  # All defaults are False
        result = service.evaluate("repo-1", data)
        assert result.overall_pass is False
        assert not any(c.passed for c in result.checks)

    def test_partial_failure_blocks_overall(self, service):
        data = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=False,  # One failure
            execute_tier_policy_passed=True,
        )
        result = service.evaluate("repo-1", data)
        assert result.overall_pass is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert failed[0].name == "execution_plane_health"

    def test_check_names_match_spec(self, service):
        data = RepoComplianceData()
        result = service.evaluate("repo-1", data)
        expected_names = {
            "branch_protection",
            "required_reviewers",
            "standard_labels",
            "projects_v2",
            "evidence_format",
            "idempotency_guard",
            "execution_plane_health",
            "execute_tier_policy",
        }
        actual_names = {c.name for c in result.checks}
        assert actual_names == expected_names

    def test_failed_checks_have_details(self, service):
        data = RepoComplianceData()
        result = service.evaluate("repo-1", data)
        for check in result.checks:
            assert check.details  # Every check has a detail string

    def test_cache_returns_same_result(self, service):
        data = RepoComplianceData(branch_protection_enabled=True)
        result1 = service.evaluate("repo-1", data)
        # Second call without data should return cached
        result2 = service.evaluate("repo-1")
        assert result2.overall_pass == result1.overall_pass

    def test_invalidate_cache(self, service):
        data = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
            execute_tier_policy_passed=True,
        )
        service.evaluate("repo-1", data)
        service.invalidate_cache("repo-1")
        # Without data, should get default (all False)
        result = service.evaluate("repo-1")
        assert result.overall_pass is False

    def test_default_data_is_all_false(self, service):
        result = service.evaluate("repo-1")
        assert result.overall_pass is False

    def test_different_repos_independent(self, service):
        data_pass = RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execution_plane_healthy=True,
            execute_tier_policy_passed=True,
        )
        data_fail = RepoComplianceData()
        r1 = service.evaluate("repo-pass", data_pass)
        r2 = service.evaluate("repo-fail", data_fail)
        assert r1.overall_pass is True
        assert r2.overall_pass is False
