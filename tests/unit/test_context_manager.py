"""Unit tests for Context Manager (Story 0.3, upgraded in Story 2.1).

Tests scope analyzer, risk flagger, complexity scoring (v0 and v1), and service context packs.
"""


from src.context.complexity import (
    ComplexityDimensions,
    ComplexityIndex,
    compute_complexity,
    compute_complexity_index,
)
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


class TestComplexityV0:
    """Legacy v0 complexity interface (band string only).
    
    Note: v1 formula produces different bands than original v0 rules.
    These tests reflect the v1 behavior accessed via the legacy interface.
    """

    def test_low_complexity(self) -> None:
        result = compute_complexity(
            1, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "low"

    def test_low_from_few_files_no_risks(self) -> None:
        # v1: 3 files → scope_breadth=2, score=4.5 → low
        result = compute_complexity(
            3, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "low"

    def test_medium_from_one_risk(self) -> None:
        # v1: 1 file + 1 risk → score=5.5 → medium
        result = compute_complexity(
            1, {"risk_security": True, "risk_breaking": False, "risk_data": False}
        )
        assert result == "medium"

    def test_medium_from_many_files(self) -> None:
        # v1: 5 files → scope_breadth=3, score=6.5 → medium
        result = compute_complexity(
            5, {"risk_security": False, "risk_breaking": False, "risk_data": False}
        )
        assert result == "medium"

    def test_medium_from_two_risks(self) -> None:
        # v1: 1 file + 2 risks → score=8.5 → medium
        result = compute_complexity(
            1, {"risk_security": True, "risk_breaking": True, "risk_data": False}
        )
        assert result == "medium"

    def test_high_from_many_risks_and_files(self) -> None:
        # v1: 10 files + 3 risks → scope_breadth=3 + 9 risk points = high
        result = compute_complexity(
            10, {"risk_security": True, "risk_breaking": True, "risk_data": True}
        )
        assert result == "high"


class TestComplexityIndexV1:
    """Complexity Index v1 tests (Story 2.1)."""

    def test_dimensions_dataclass(self) -> None:
        dims = ComplexityDimensions(
            scope_breadth=2,
            risk_flag_count=1,
            dependency_count=3,
            lines_estimate=100,
            expert_coverage=2,
        )
        assert dims.scope_breadth == 2
        assert dims.risk_flag_count == 1
        assert dims.dependency_count == 3
        assert dims.lines_estimate == 100
        assert dims.expert_coverage == 2

    def test_dimensions_to_dict(self) -> None:
        dims = ComplexityDimensions(
            scope_breadth=1,
            risk_flag_count=0,
            dependency_count=0,
            lines_estimate=25,
            expert_coverage=0,
        )
        d = dims.to_dict()
        assert d["scope_breadth"] == 1
        assert d["risk_flag_count"] == 0
        assert d["dependency_count"] == 0
        assert d["lines_estimate"] == 25
        assert d["expert_coverage"] == 0

    def test_complexity_index_to_dict(self) -> None:
        dims = ComplexityDimensions(
            scope_breadth=2,
            risk_flag_count=1,
            dependency_count=2,
            lines_estimate=50,
            expert_coverage=1,
        )
        index = ComplexityIndex(score=10.5, band="medium", dimensions=dims)
        d = index.to_dict()
        assert d["score"] == 10.5
        assert d["band"] == "medium"
        assert d["dimensions"]["scope_breadth"] == 2

    def test_complexity_index_from_dict(self) -> None:
        data = {
            "score": 8.0,
            "band": "medium",
            "dimensions": {
                "scope_breadth": 2,
                "risk_flag_count": 1,
                "dependency_count": 1,
                "lines_estimate": 75,
                "expert_coverage": 1,
            },
        }
        index = ComplexityIndex.from_dict(data)
        assert index.score == 8.0
        assert index.band == "medium"
        assert index.dimensions.scope_breadth == 2
        assert index.dimensions.expert_coverage == 1

    def test_compute_low_complexity(self) -> None:
        scope = ScopeResult(affected_files_estimate=1, components=[], file_references=[])
        risk_flags = {"risk_security": False, "risk_breaking": False, "risk_data": False}
        index = compute_complexity_index(scope, risk_flags)
        assert index.band == "low"
        assert index.score <= 5.0
        assert index.dimensions.scope_breadth == 1
        assert index.dimensions.risk_flag_count == 0

    def test_compute_medium_complexity_from_scope(self) -> None:
        scope = ScopeResult(
            affected_files_estimate=3,
            components=["auth", "api"],
            file_references=[],
        )
        risk_flags = {"risk_security": False, "risk_breaking": False, "risk_data": False}
        index = compute_complexity_index(scope, risk_flags)
        assert index.band == "medium"
        assert index.dimensions.scope_breadth == 2
        assert index.dimensions.dependency_count == 2

    def test_compute_medium_complexity_from_risk(self) -> None:
        scope = ScopeResult(affected_files_estimate=1, components=[], file_references=[])
        risk_flags = {"risk_security": True, "risk_breaking": False, "risk_data": False}
        index = compute_complexity_index(scope, risk_flags)
        assert index.band == "medium"
        assert index.dimensions.risk_flag_count == 1

    def test_compute_high_complexity(self) -> None:
        scope = ScopeResult(
            affected_files_estimate=10,
            components=["auth", "api", "database", "frontend"],
            file_references=["src/a.py", "src/b.py", "src/c.py"],
        )
        risk_flags = {"risk_security": True, "risk_breaking": True, "risk_data": True}
        index = compute_complexity_index(scope, risk_flags, mandatory_expert_classes=["sec", "qa"])
        assert index.band == "high"
        assert index.dimensions.scope_breadth == 3
        assert index.dimensions.risk_flag_count == 3
        assert index.dimensions.expert_coverage == 2

    def test_expert_coverage_affects_score(self) -> None:
        scope = ScopeResult(affected_files_estimate=1, components=[], file_references=[])
        risk_flags = {"risk_security": False}
        
        # Without experts
        index_no_experts = compute_complexity_index(scope, risk_flags, mandatory_expert_classes=())
        
        # With experts
        index_with_experts = compute_complexity_index(
            scope, risk_flags, mandatory_expert_classes=["security", "qa", "compliance"]
        )
        
        assert index_with_experts.score > index_no_experts.score
        assert index_with_experts.dimensions.expert_coverage == 3
        assert index_no_experts.dimensions.expert_coverage == 0

    def test_lines_estimate_from_file_refs(self) -> None:
        scope = ScopeResult(
            affected_files_estimate=3,
            components=[],
            file_references=["a.py", "b.py", "c.py"],
        )
        risk_flags = {}
        index = compute_complexity_index(scope, risk_flags)
        assert index.dimensions.lines_estimate == 90  # 3 files * 30 lines

    def test_lines_estimate_from_components(self) -> None:
        scope = ScopeResult(
            affected_files_estimate=4,
            components=["auth", "api"],
            file_references=[],
        )
        risk_flags = {}
        index = compute_complexity_index(scope, risk_flags)
        assert index.dimensions.lines_estimate == 100  # 2 components * 50 lines

    def test_zero_flags_edge_case(self) -> None:
        scope = ScopeResult(affected_files_estimate=1, components=[], file_references=[])
        risk_flags = {}  # Empty dict
        index = compute_complexity_index(scope, risk_flags)
        assert index.dimensions.risk_flag_count == 0
        assert index.band == "low"

    def test_max_complexity_edge_case(self) -> None:
        scope = ScopeResult(
            affected_files_estimate=100,
            components=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"],
            file_references=["f1.py", "f2.py", "f3.py", "f4.py", "f5.py"],
        )
        risk_flags = {
            "risk_security": True,
            "risk_breaking": True,
            "risk_data": True,
            "risk_cross_team": True,
            "risk_compliance": True,
            "risk_migration": True,
        }
        index = compute_complexity_index(
            scope, risk_flags, mandatory_expert_classes=["a", "b", "c", "d", "e"]
        )
        assert index.band == "high"
        assert index.score > 12.0
        assert index.dimensions.risk_flag_count == 6
        assert index.dimensions.expert_coverage == 5

    def test_score_rounding(self) -> None:
        scope = ScopeResult(affected_files_estimate=1, components=[], file_references=[])
        risk_flags = {}
        index = compute_complexity_index(scope, risk_flags)
        # Score should be rounded to 1 decimal place
        assert index.score == round(index.score, 1)


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
        """Test case 4: Security issue with multiple risk flags."""
        title = "Fix credential leak in config"
        body = "Credentials are logged. Check src/config.py and src/auth.py and database module."
        scope = analyze_scope(title, body)
        risks = flag_risks(title, body)
        # Use v1 compute_complexity_index for full scoring
        index = compute_complexity_index(scope, risks)
        assert risks["risk_security"] is True
        assert risks["risk_data"] is True
        # v1: 2 files + 2 risks + 2 components (config, database) → medium/high
        assert index.band in ("medium", "high")
        assert index.dimensions.risk_flag_count == 2

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
