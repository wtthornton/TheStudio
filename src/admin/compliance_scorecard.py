"""Compliance Scorecard — Execute-tier promotion gate.

Story 7.7: Compliance Scorecard Service
Story 7.8: Compliance Scorecard API & Promotion Gate
Architecture reference: thestudioarc/23-admin-control-ui.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class ScorecardCheck:
    """A single compliance check result."""

    name: str
    description: str
    passed: bool
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass
class ComplianceScorecard:
    """Full compliance scorecard for a repo."""

    repo_id: str
    checks: list[ScorecardCheck] = field(default_factory=list)
    overall_pass: bool = False
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "checks": [c.to_dict() for c in self.checks],
            "overall_pass": self.overall_pass,
            "checks_passed": sum(1 for c in self.checks if c.passed),
            "checks_total": len(self.checks),
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class RepoComplianceData:
    """Input data for evaluating compliance.

    In production, this would be fetched from GitHub API, repo profile,
    and execution plane health. For now, it's provided explicitly.
    """

    branch_protection_enabled: bool = False
    required_reviewers_configured: bool = False
    standard_labels_present: bool = False
    projects_v2_configured: bool = False
    evidence_format_valid: bool = False
    idempotency_guard_active: bool = False
    execution_plane_healthy: bool = False


@runtime_checkable
class ComplianceScorecardProtocol(Protocol):
    """Interface for compliance scorecard evaluation."""

    def evaluate(
        self,
        repo_id: str,
        data: RepoComplianceData | None = None,
    ) -> ComplianceScorecard: ...
    def invalidate_cache(self, repo_id: str) -> None: ...


class InMemoryComplianceScorecardService:
    """Evaluates repos against Execute-tier requirements.

    7 checks per AC 13:
    (a) branch protection rulesets enabled
    (b) required reviewers configured for sensitive paths
    (c) standard labels present
    (d) Projects v2 fields configured
    (e) evidence comment format validated on last 3 PRs
    (f) idempotency guard active
    (g) execution plane health = healthy
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[ComplianceScorecard, datetime]] = {}
        self._cache_ttl_seconds = 3600  # 1 hour

    def evaluate(
        self,
        repo_id: str,
        data: RepoComplianceData | None = None,
    ) -> ComplianceScorecard:
        """Evaluate compliance for a repo.

        Uses cached result if available and fresh (< 1 hour).
        """
        # Check cache
        cached = self._cache.get(repo_id)
        if cached and data is None:
            scorecard, cached_at = cached
            age = (datetime.now(UTC) - cached_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return scorecard

        if data is None:
            data = self._fetch_compliance_data(repo_id)

        checks = [
            ScorecardCheck(
                name="branch_protection",
                description="Branch protection rulesets enabled",
                passed=data.branch_protection_enabled,
                details="Enabled"
                if data.branch_protection_enabled
                else "Branch protection not configured",
            ),
            ScorecardCheck(
                name="required_reviewers",
                description="Required reviewers configured for sensitive paths",
                passed=data.required_reviewers_configured,
                details="Configured"
                if data.required_reviewers_configured
                else "No required reviewers for sensitive paths",
            ),
            ScorecardCheck(
                name="standard_labels",
                description="Standard platform labels present",
                passed=data.standard_labels_present,
                details="All standard labels present"
                if data.standard_labels_present
                else "Missing standard labels (agent:run, tier:*, type:*, risk:*)",
            ),
            ScorecardCheck(
                name="projects_v2",
                description="Projects v2 fields configured",
                passed=data.projects_v2_configured,
                details="Configured"
                if data.projects_v2_configured
                else "Projects v2 fields not configured (Status, Tier, Priority, Owner)",
            ),
            ScorecardCheck(
                name="evidence_format",
                description="Evidence comment format validated on last 3 PRs",
                passed=data.evidence_format_valid,
                details="Valid"
                if data.evidence_format_valid
                else "Evidence comments missing or malformed on recent PRs",
            ),
            ScorecardCheck(
                name="idempotency_guard",
                description="Idempotency guard active",
                passed=data.idempotency_guard_active,
                details="Active"
                if data.idempotency_guard_active
                else "Idempotency guard not active — risk of duplicate PRs",
            ),
            ScorecardCheck(
                name="execution_plane_health",
                description="Execution plane health = healthy",
                passed=data.execution_plane_healthy,
                details="Healthy"
                if data.execution_plane_healthy
                else "Execution plane not healthy — check workers and verification runner",
            ),
        ]

        overall = all(c.passed for c in checks)
        scorecard = ComplianceScorecard(
            repo_id=repo_id,
            checks=checks,
            overall_pass=overall,
        )

        # Cache result
        self._cache[repo_id] = (scorecard, datetime.now(UTC))

        return scorecard

    def invalidate_cache(self, repo_id: str) -> None:
        """Remove cached scorecard for a repo."""
        self._cache.pop(repo_id, None)

    def _fetch_compliance_data(self, repo_id: str) -> RepoComplianceData:
        """Fetch compliance data from the compliance data store and plane health.

        Checks the in-memory compliance data store for repo configuration flags
        and the execution plane registry for plane health status.
        Falls back to False for any field that cannot be determined.
        """
        from src.compliance.plane_registry import get_plane_registry

        stored = get_compliance_data(repo_id)
        if stored is not None:
            data = RepoComplianceData(
                branch_protection_enabled=stored.branch_protection_enabled,
                required_reviewers_configured=stored.required_reviewers_configured,
                standard_labels_present=stored.standard_labels_present,
                projects_v2_configured=stored.projects_v2_configured,
                evidence_format_valid=stored.evidence_format_valid,
                idempotency_guard_active=stored.idempotency_guard_active,
            )
        else:
            data = RepoComplianceData()

        # --- Execution plane health ---
        plane_registry = get_plane_registry()
        summaries = plane_registry.get_health_summary()
        for summary in summaries:
            if summary.healthy:
                plane = plane_registry.get_plane(summary.plane_id)
                if plane and repo_id in plane.repo_ids:
                    data.execution_plane_healthy = True
                    break

        return data


# --- In-memory compliance data store ---
# Populated by admin API or integration hooks; consumed by _fetch_compliance_data.

_compliance_data_store: dict[str, RepoComplianceData] = {}


def set_compliance_data(repo_id: str, data: RepoComplianceData) -> None:
    """Register compliance data for a repo."""
    _compliance_data_store[repo_id] = data


def get_compliance_data(repo_id: str) -> RepoComplianceData | None:
    """Retrieve stored compliance data for a repo."""
    return _compliance_data_store.get(repo_id)


def clear_compliance_data() -> None:
    """Clear all stored compliance data (for testing)."""
    _compliance_data_store.clear()


# Backwards-compatible alias
ComplianceScorecardService = InMemoryComplianceScorecardService


# Global instance
_scorecard_service: InMemoryComplianceScorecardService | None = None


def get_scorecard_service() -> ComplianceScorecardProtocol:
    """Return the module-level ComplianceScorecardService singleton."""
    global _scorecard_service
    if _scorecard_service is None:
        _scorecard_service = InMemoryComplianceScorecardService()
    return _scorecard_service
