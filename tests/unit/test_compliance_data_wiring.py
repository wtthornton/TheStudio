"""Tests for compliance scorecard data wiring — Epic 11.

Verifies that _fetch_compliance_data pulls from in-memory compliance data
store and execution plane health, replacing the old all-False defaults.
"""

from __future__ import annotations

import pytest

from src.admin.compliance_scorecard import (
    InMemoryComplianceScorecardService,
    RepoComplianceData,
    clear_compliance_data,
    get_compliance_data,
    set_compliance_data,
)
from src.compliance.plane_registry import (
    ExecutionPlaneRegistry,
    clear as clear_planes,
)


@pytest.fixture(autouse=True)
def _reset():
    clear_compliance_data()
    clear_planes()
    yield
    clear_compliance_data()
    clear_planes()


class TestComplianceDataStore:
    """Test in-memory compliance data store CRUD."""

    def test_set_and_get(self):
        data = RepoComplianceData(branch_protection_enabled=True)
        set_compliance_data("org/repo", data)
        assert get_compliance_data("org/repo") is data

    def test_get_missing_returns_none(self):
        assert get_compliance_data("org/nonexistent") is None

    def test_clear(self):
        set_compliance_data("org/repo", RepoComplianceData())
        clear_compliance_data()
        assert get_compliance_data("org/repo") is None


class TestFetchComplianceData:
    """Test _fetch_compliance_data wiring."""

    def test_no_stored_data_returns_all_false(self):
        svc = InMemoryComplianceScorecardService()
        scorecard = svc.evaluate("org/repo")
        assert scorecard.overall_pass is False
        assert all(not c.passed for c in scorecard.checks)

    def test_stored_data_used_in_evaluation(self):
        set_compliance_data("org/repo", RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
        ))
        svc = InMemoryComplianceScorecardService()
        scorecard = svc.evaluate("org/repo")

        # 6 of 7 checks pass (execution_plane_healthy still False)
        passed_names = {c.name for c in scorecard.checks if c.passed}
        assert "branch_protection" in passed_names
        assert "required_reviewers" in passed_names
        assert "standard_labels" in passed_names
        assert "projects_v2" in passed_names
        assert "evidence_format" in passed_names
        assert "idempotency_guard" in passed_names
        assert "execution_plane_health" not in passed_names
        assert scorecard.overall_pass is False  # plane health fails

    def test_plane_health_wired(self):
        """Execution plane health check uses plane registry."""
        set_compliance_data("org/repo", RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
            execute_tier_policy_passed=True,
        ))

        # Register a healthy plane with the repo assigned
        registry = ExecutionPlaneRegistry()
        plane = registry.register("plane-1")
        registry.assign_repo(plane.plane_id, "org/repo")

        svc = InMemoryComplianceScorecardService()
        scorecard = svc.evaluate("org/repo")

        # All 8 checks pass
        assert scorecard.overall_pass is True
        plane_check = next(c for c in scorecard.checks if c.name == "execution_plane_health")
        assert plane_check.passed is True

    def test_plane_health_fails_when_repo_not_assigned(self):
        """Plane is healthy but repo not in it — still fails."""
        set_compliance_data("org/repo", RepoComplianceData(
            branch_protection_enabled=True,
            required_reviewers_configured=True,
            standard_labels_present=True,
            projects_v2_configured=True,
            evidence_format_valid=True,
            idempotency_guard_active=True,
        ))

        registry = ExecutionPlaneRegistry()
        registry.register("plane-1")  # No repos assigned

        svc = InMemoryComplianceScorecardService()
        scorecard = svc.evaluate("org/repo")
        assert scorecard.overall_pass is False

    def test_explicit_data_overrides_store(self):
        """When data is passed explicitly, store is not consulted."""
        set_compliance_data("org/repo", RepoComplianceData(branch_protection_enabled=True))

        explicit = RepoComplianceData()  # All False
        svc = InMemoryComplianceScorecardService()
        scorecard = svc.evaluate("org/repo", data=explicit)
        assert all(not c.passed for c in scorecard.checks)
