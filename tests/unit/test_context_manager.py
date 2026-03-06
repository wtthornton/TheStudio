"""Unit tests for Context Manager (Story 0.3).

Tests scope analyzer, risk flagger, complexity scoring, and service context packs.
"""


from src.context.complexity import compute_complexity
from src.context.risk_flagger import flag_risks
from src.context.scope_analyzer import ScopeResult, analyze_scope
from src.context.service_context_pack import ServiceContextPack, get_context_packs

# --- Scope Analyzer Tests ---


class TestScopeAnalyzer:
    def test_simple_issue_single_file(self) -> None:
        result = analyze_scope("Fix typo in README", "There is a typo on line 5.")
        assert result.affected_files_estimate >= 1
        assert isinstance(result.components, list)

    def test_file_references_detected(self) -> None:
        result = analyze_scope(
            "Update configs",
            "Please update src/settings.py and src/app.py with new values.",
        )
        assert len(result.file_references) >= 2
        assert result.affected_files_estimate >= 2

    def test_component_detection(self) -> None:
        result = analyze_scope(
            "Refactor auth module",
            "The auth and database components need refactoring.",
        )
        assert "auth" in result.components
        assert "database" in result.components

    def test_empty_body(self) -> None:
        result = analyze_scope("Fix bug", "")
        assert result.affected_files_estimate >= 1
        assert isinstance(result, ScopeResult)

    def test_multi_file_from_components(self) -> None:
        result = analyze_scope(
            "Refactor across api, frontend, and backend",
            "This touches api, frontend, backend, and test modules.",
        )
        assert result.affected_files_estimate > 1
        assert len(result.components) >= 3

    def test_to_dict(self) -> None:
        result = analyze_scope("Test", "content")
        d = result.to_dict()
        assert "affected_files_estimate" in d
        assert "components" in d
        assert "file_references" in d


# --- Risk Flagger Tests ---


class TestRiskFlagger:
    def test_no_risks(self) -> None:
        flags = flag_risks("Fix typo in README", "Small text change.")
        assert not any(flags.values())

    def test_security_risk(self) -> None:
        flags = flag_risks(
            "Fix credential leak in config",
            "Credentials are being logged to stdout.",
        )
        assert flags["risk_security"] is True

    def test_breaking_risk(self) -> None:
        flags = flag_risks(
            "Remove deprecated API v1 endpoints",
            "This is a breaking change for existing consumers.",
        )
        assert flags["risk_breaking"] is True

    def test_cross_team_risk(self) -> None:
        flags = flag_risks(
            "Update shared API contract",
            "This affects the cross-team dependency on payments service.",
        )
        assert flags["risk_cross_team"] is True

    def test_data_risk(self) -> None:
        flags = flag_risks(
            "Add new column to users",
            "ALTER TABLE users ADD COLUMN email_verified BOOLEAN.",
        )
        assert flags["risk_data"] is True

    def test_multiple_risks(self) -> None:
        flags = flag_risks(
            "Security migration",
            "Fix vulnerability by migrating auth database schema. Breaking change.",
        )
        assert flags["risk_security"] is True
        assert flags["risk_data"] is True
        assert flags["risk_breaking"] is True

    def test_all_flags_present(self) -> None:
        flags = flag_risks("test", "test")
        assert "risk_security" in flags
        assert "risk_breaking" in flags
        assert "risk_cross_team" in flags
        assert "risk_data" in flags


# --- Complexity Index Tests ---


class TestComplexity:
    def test_low_complexity(self) -> None:
        result = compute_complexity(
            1, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "low"

    def test_medium_from_files(self) -> None:
        result = compute_complexity(
            3, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "medium"

    def test_medium_from_one_risk(self) -> None:
        result = compute_complexity(
            1, {"risk_security": True, "risk_breaking": False, "risk_data": False}
        )
        assert result == "medium"

    def test_high_from_many_files(self) -> None:
        result = compute_complexity(
            5, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "high"

    def test_high_from_two_risks(self) -> None:
        result = compute_complexity(
            1, {"risk_security": True, "risk_breaking": True, "risk_data": False}
        )
        assert result == "high"

    def test_high_from_risks_and_files(self) -> None:
        result = compute_complexity(
            10, {"risk_security": True, "risk_breaking": True, "risk_data": True}
        )
        assert result == "high"


# --- Service Context Pack Tests ---


class TestServiceContextPack:
    def test_pack_to_dict(self) -> None:
        pack = ServiceContextPack(name="test-pack", version="1.0", content={"key": "val"})
        d = pack.to_dict()
        assert d["name"] == "test-pack"
        assert d["version"] == "1.0"
        assert d["content"] == {"key": "val"}

    def test_get_context_packs_returns_empty(self) -> None:
        """Phase 0 stub returns empty list."""
        packs = get_context_packs("owner/repo")
        assert packs == []


# --- Integration-style tests combining components ---


class TestContextManagerIntegration:
    def test_simple_issue_flow(self) -> None:
        """Test case 1: Simple issue, no risks -> low complexity."""
        title = "Fix typo in README"
        body = "There is a typo on line 5 of the README."
        scope = analyze_scope(title, body)
        risks = flag_risks(title, body)
        complexity = compute_complexity(scope.affected_files_estimate, risks)
        assert complexity == "low"
        assert not any(risks.values())

    def test_multi_file_security_issue(self) -> None:
        """Test case 4: Security issue -> high complexity."""
        title = "Fix credential leak in config"
        body = "Credentials are logged. Check src/config.py and src/auth.py and database module."
        scope = analyze_scope(title, body)
        risks = flag_risks(title, body)
        complexity = compute_complexity(scope.affected_files_estimate, risks)
        assert risks["risk_security"] is True
        assert risks["risk_data"] is True
        assert complexity == "high"

    def test_breaking_change_issue(self) -> None:
        """Test case 3: Breaking change -> high complexity."""
        title = "Remove deprecated API v1 endpoints"
        body = "This is a breaking change. Remove all v1 routes from api and backend."
        scope = analyze_scope(title, body)
        risks = flag_risks(title, body)
        compute_complexity(scope.affected_files_estimate, risks)
        assert risks["risk_breaking"] is True

    def test_cross_team_mention(self) -> None:
        """Test case 5: Cross-team mention."""
        title = "Update shared API contract with team-payments"
        body = "The upstream dependency on the other team service needs updating."
        risks = flag_risks(title, body)
        assert risks["risk_cross_team"] is True

    def test_empty_body_defaults(self) -> None:
        """Test case 6: Empty body -> low complexity, no risks."""
        scope = analyze_scope("Minor fix", "")
        risks = flag_risks("Minor fix", "")
        complexity = compute_complexity(scope.affected_files_estimate, risks)
        assert complexity == "low"
        assert not any(risks.values())
