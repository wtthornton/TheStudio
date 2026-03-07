"""Tests for Tool Catalog Schema, Registry & Policy Engine (Stories 7.1-7.2)."""

import pytest

from src.admin.tool_catalog import (
    AccessDecision,
    ApprovalStatus,
    CapabilityCategory,
    InvalidPromotionError,
    SuiteDuplicateError,
    SuiteNotFoundError,
    ToolCatalog,
    ToolEntry,
    ToolPolicyEngine,
    ToolProfile,
    ToolSuite,
    seed_standard_suites,
)


@pytest.fixture
def catalog():
    c = ToolCatalog()
    seed_standard_suites(c)
    return c


@pytest.fixture
def policy(catalog):
    return ToolPolicyEngine(catalog)


class TestToolEntry:
    def test_to_dict(self):
        entry = ToolEntry("ruff", "Linter", CapabilityCategory.CODE_QUALITY)
        d = entry.to_dict()
        assert d["name"] == "ruff"
        assert d["read_only"] is True

    def test_write_tool(self):
        entry = ToolEntry("readme-gen", "Gen", CapabilityCategory.DOCUMENTATION, read_only=False)
        assert entry.read_only is False


class TestToolSuite:
    def test_to_dict(self):
        suite = ToolSuite(
            name="test-suite",
            description="Test",
            tools=[ToolEntry("t1", "Tool 1", CapabilityCategory.CODE_QUALITY)],
        )
        d = suite.to_dict()
        assert d["name"] == "test-suite"
        assert d["tool_count"] == 1
        assert d["approval_status"] == "observe"

    def test_default_approval_is_observe(self):
        suite = ToolSuite(name="x", description="x")
        assert suite.approval_status == ApprovalStatus.OBSERVE


class TestToolCatalog:
    def test_register_and_list(self, catalog):
        suites = catalog.list_suites()
        assert len(suites) == 3
        names = {s.name for s in suites}
        assert "code-quality" in names
        assert "context-retrieval" in names
        assert "documentation" in names

    def test_get_suite(self, catalog):
        suite = catalog.get_suite("code-quality")
        assert suite.name == "code-quality"
        assert len(suite.tools) == 4

    def test_get_suite_not_found(self, catalog):
        with pytest.raises(SuiteNotFoundError):
            catalog.get_suite("nonexistent")

    def test_register_duplicate(self, catalog):
        dupe = ToolSuite(name="code-quality", description="Dupe")
        with pytest.raises(SuiteDuplicateError):
            catalog.register(dupe)

    def test_promote_observe_to_suggest(self):
        c = ToolCatalog()
        suite = ToolSuite(name="new", description="New", approval_status=ApprovalStatus.OBSERVE)
        c.register(suite)
        promoted = c.promote_suite("new")
        assert promoted.approval_status == ApprovalStatus.SUGGEST

    def test_promote_suggest_to_execute(self):
        c = ToolCatalog()
        suite = ToolSuite(name="new", description="New", approval_status=ApprovalStatus.SUGGEST)
        c.register(suite)
        promoted = c.promote_suite("new")
        assert promoted.approval_status == ApprovalStatus.EXECUTE

    def test_promote_execute_fails(self):
        c = ToolCatalog()
        suite = ToolSuite(name="new", description="New", approval_status=ApprovalStatus.EXECUTE)
        c.register(suite)
        with pytest.raises(InvalidPromotionError):
            c.promote_suite("new")

    def test_promote_not_found(self):
        c = ToolCatalog()
        with pytest.raises(SuiteNotFoundError):
            c.promote_suite("missing")

    def test_get_suites_for_tier(self, catalog):
        # All tiers see all approval statuses
        observe = catalog.get_suites_for_tier("observe")
        assert len(observe) == 3

    def test_clear(self, catalog):
        catalog.clear()
        assert len(catalog.list_suites()) == 0

    def test_standard_suites_have_correct_tools(self, catalog):
        cq = catalog.get_suite("code-quality")
        tool_names = [t.name for t in cq.tools]
        assert "ruff" in tool_names
        assert "mypy" in tool_names
        assert "bandit" in tool_names
        assert "dead-code" in tool_names


class TestToolProfile:
    def test_to_dict(self):
        p = ToolProfile("p1", "repo-1", ["code-quality"], "suggest")
        d = p.to_dict()
        assert d["profile_id"] == "p1"
        assert d["tier_scope"] == "suggest"
        assert "code-quality" in d["enabled_suites"]


class TestToolPolicyEngine:
    def test_developer_allowed_code_quality(self, policy):
        result = policy.check_access("developer", [], "execute", "code-quality", "ruff")
        assert result.allowed is True

    def test_developer_denied_repository_analysis(self, policy):
        # Developer doesn't have repository-analysis
        cat = ToolCatalog()
        suite = ToolSuite(
            name="repository-analysis",
            description="Repo analysis",
            tools=[ToolEntry("dep-check", "Deps", CapabilityCategory.REPOSITORY_ANALYSIS)],
            approval_status=ApprovalStatus.EXECUTE,
        )
        cat.register(suite)
        engine = ToolPolicyEngine(cat)
        result = engine.check_access("developer", [], "execute", "repository-analysis", "dep-check")
        assert result.allowed is False
        assert "does not have access" in result.reason

    def test_architect_allowed_repository_analysis(self, policy):
        # Need to add the suite to catalog first
        cat = ToolCatalog()
        seed_standard_suites(cat)
        suite = ToolSuite(
            name="repository-analysis",
            description="Repo analysis",
            tools=[ToolEntry("dep-check", "Deps", CapabilityCategory.REPOSITORY_ANALYSIS)],
            approval_status=ApprovalStatus.EXECUTE,
        )
        cat.register(suite)
        engine = ToolPolicyEngine(cat)
        result = engine.check_access("architect", [], "execute", "repository-analysis", "dep-check")
        assert result.allowed is True

    def test_security_overlay_adds_security_suite(self):
        cat = ToolCatalog()
        suite = ToolSuite(
            name="security",
            description="Security tools",
            tools=[ToolEntry("vuln-scan", "Scanner", CapabilityCategory.SECURITY)],
            approval_status=ApprovalStatus.EXECUTE,
        )
        cat.register(suite)
        engine = ToolPolicyEngine(cat)
        result = engine.check_access("developer", ["security"], "execute", "security", "vuln-scan")
        assert result.allowed is True

    def test_unknown_role_denied(self, policy):
        result = policy.check_access("unknown-role", [], "execute", "code-quality", "ruff")
        assert result.allowed is False
        assert "Unknown agent role" in result.reason

    def test_unknown_suite_denied(self, policy):
        result = policy.check_access("developer", [], "execute", "nonexistent", "tool")
        assert result.allowed is False
        assert "not found in catalog" in result.reason

    def test_tool_not_in_suite_denied(self, policy):
        result = policy.check_access("developer", [], "execute", "code-quality", "nonexistent-tool")
        assert result.allowed is False
        assert "not found in suite" in result.reason

    def test_unknown_tier_denied(self, policy):
        result = policy.check_access("developer", [], "unknown-tier", "code-quality", "ruff")
        assert result.allowed is False
        assert "Unknown repo tier" in result.reason

    def test_observe_tier_requires_execute_approval(self):
        cat = ToolCatalog()
        suite = ToolSuite(
            name="code-quality",
            description="Quality",
            tools=[ToolEntry("ruff", "Lint", CapabilityCategory.CODE_QUALITY)],
            approval_status=ApprovalStatus.OBSERVE,
        )
        cat.register(suite)
        engine = ToolPolicyEngine(cat)
        result = engine.check_access("developer", [], "observe", "code-quality", "ruff")
        assert result.allowed is False
        assert "does not meet" in result.reason

    def test_access_decision_to_dict(self):
        d = AccessDecision(True, "ok", "dev", "suite", "tool").to_dict()
        assert d["allowed"] is True
