"""Tool Catalog — Tool Hub schema, registry, and policy engine.

Story 7.1: Tool Catalog Schema & Registry
Story 7.2: Tool Profile & Policy Engine
Architecture reference: thestudioarc/25-tool-hub-mcp-toolkit.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any


class ApprovalStatus(StrEnum):
    """Approval lifecycle for tool suites."""

    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


class CapabilityCategory(StrEnum):
    """Capability categories for tools."""

    CODE_QUALITY = "code_quality"
    CONTEXT_RETRIEVAL = "context_retrieval"
    DOCUMENTATION = "documentation"
    BROWSER_AUTOMATION = "browser_automation"
    REPOSITORY_ANALYSIS = "repository_analysis"
    OBSERVABILITY = "observability"
    SECURITY = "security"


@dataclass
class ToolEntry:
    """A single tool within a tool suite."""

    name: str
    description: str
    capability: CapabilityCategory
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capability": self.capability.value,
            "read_only": self.read_only,
        }


@dataclass
class ToolSuite:
    """A named group of tools with shared approval status."""

    name: str
    description: str
    tools: list[ToolEntry] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.OBSERVE
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tools": [t.to_dict() for t in self.tools],
            "approval_status": self.approval_status.value,
            "version": self.version,
            "tool_count": len(self.tools),
        }


# --- Promotion rules ---

_PROMOTION_ORDER = [ApprovalStatus.OBSERVE, ApprovalStatus.SUGGEST, ApprovalStatus.EXECUTE]


class InvalidPromotionError(Exception):
    """Raised when a suite promotion is invalid."""

    def __init__(self, suite: str, current: ApprovalStatus, target: ApprovalStatus) -> None:
        self.suite = suite
        self.current = current
        self.target = target
        super().__init__(f"Cannot promote {suite} from {current.value} to {target.value}")


class SuiteNotFoundError(Exception):
    """Raised when a tool suite is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool suite '{name}' not found")


class SuiteDuplicateError(Exception):
    """Raised when registering a duplicate suite."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool suite '{name}' already registered")


class ToolCatalog:
    """In-memory registry of tool suites."""

    def __init__(self) -> None:
        self._suites: dict[str, ToolSuite] = {}

    def register(self, suite: ToolSuite) -> None:
        if suite.name in self._suites:
            raise SuiteDuplicateError(suite.name)
        self._suites[suite.name] = suite

    def get_suite(self, name: str) -> ToolSuite:
        if name not in self._suites:
            raise SuiteNotFoundError(name)
        return self._suites[name]

    def list_suites(self) -> list[ToolSuite]:
        return list(self._suites.values())

    def promote_suite(self, name: str) -> ToolSuite:
        """Promote a suite to the next approval status.

        observe -> suggest -> execute. Cannot promote past execute.
        """
        suite = self.get_suite(name)
        idx = _PROMOTION_ORDER.index(suite.approval_status)
        if idx >= len(_PROMOTION_ORDER) - 1:
            raise InvalidPromotionError(name, suite.approval_status, suite.approval_status)
        suite.approval_status = _PROMOTION_ORDER[idx + 1]
        return suite

    def get_suites_for_tier(self, tier: str) -> list[ToolSuite]:
        """Return suites available at a given repo tier.

        observe tier: only observe-approved suites
        suggest tier: observe + suggest
        execute tier: all suites
        """
        tier_map: dict[str, set[ApprovalStatus]] = {
            "observe": {ApprovalStatus.OBSERVE, ApprovalStatus.SUGGEST, ApprovalStatus.EXECUTE},
            "suggest": {ApprovalStatus.OBSERVE, ApprovalStatus.SUGGEST, ApprovalStatus.EXECUTE},
            "execute": {ApprovalStatus.OBSERVE, ApprovalStatus.SUGGEST, ApprovalStatus.EXECUTE},
        }
        allowed = tier_map.get(tier, set())
        return [s for s in self._suites.values() if s.approval_status in allowed]

    def clear(self) -> None:
        self._suites.clear()


# --- Tool Profile & Policy Engine (Story 7.2) ---


@dataclass
class ToolProfile:
    """Maps a repo to its enabled tool suites."""

    profile_id: str
    repo_id: str
    enabled_suites: list[str] = field(default_factory=list)
    tier_scope: str = "observe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "repo_id": self.repo_id,
            "enabled_suites": self.enabled_suites,
            "tier_scope": self.tier_scope,
        }


# Agent roles for tool access (maps to thestudioarc/08-agent-roles.md)
class AgentRole(StrEnum):
    DEVELOPER = "developer"
    ARCHITECT = "architect"
    PLANNER = "planner"


# Overlays that restrict tool access
class ToolOverlay(StrEnum):
    SECURITY = "security"
    COMPLIANCE = "compliance"
    HOTFIX = "hotfix"


# Default role -> allowed suites mapping
ROLE_SUITE_ALLOWLIST: dict[AgentRole, frozenset[str]] = {
    AgentRole.DEVELOPER: frozenset({"code-quality", "context-retrieval", "documentation"}),
    AgentRole.ARCHITECT: frozenset({"code-quality", "context-retrieval", "documentation", "repository-analysis"}),
    AgentRole.PLANNER: frozenset({"context-retrieval", "documentation"}),
}

# Overlays that add suite access
OVERLAY_SUITE_ADDITIONS: dict[ToolOverlay, frozenset[str]] = {
    ToolOverlay.SECURITY: frozenset({"security"}),
    ToolOverlay.COMPLIANCE: frozenset({"code-quality", "security"}),
    ToolOverlay.HOTFIX: frozenset(),
}

# Tier -> minimum approval status required
TIER_MIN_APPROVAL: dict[str, ApprovalStatus] = {
    "observe": ApprovalStatus.EXECUTE,
    "suggest": ApprovalStatus.SUGGEST,
    "execute": ApprovalStatus.OBSERVE,
}


@dataclass
class AccessDecision:
    """Result of a tool access check."""

    allowed: bool
    reason: str
    role: str
    suite: str
    tool: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "role": self.role,
            "suite": self.suite,
            "tool": self.tool,
        }


class ToolPolicyEngine:
    """Enforces tool access based on role, overlays, and repo tier."""

    def __init__(self, catalog: ToolCatalog) -> None:
        self._catalog = catalog

    def check_access(
        self,
        role: str,
        overlays: list[str],
        repo_tier: str,
        suite_name: str,
        tool_name: str,
    ) -> AccessDecision:
        """Check if a tool call is allowed.

        Deny by default. Allow only when:
        1. Suite exists in catalog
        2. Suite approval status meets tier minimum
        3. Role has suite in allowlist (or overlay adds it)
        4. Tool exists in suite
        """
        base = AccessDecision(
            allowed=False, reason="", role=role, suite=suite_name, tool=tool_name
        )

        # Check suite exists
        try:
            suite = self._catalog.get_suite(suite_name)
        except SuiteNotFoundError:
            base.reason = f"Suite '{suite_name}' not found in catalog"
            return base

        # Check tool exists in suite
        tool_names = [t.name for t in suite.tools]
        if tool_name not in tool_names:
            base.reason = f"Tool '{tool_name}' not found in suite '{suite_name}'"
            return base

        # Check tier approval
        min_approval = TIER_MIN_APPROVAL.get(repo_tier)
        if min_approval is None:
            base.reason = f"Unknown repo tier '{repo_tier}'"
            return base

        tier_idx = _PROMOTION_ORDER.index(min_approval)
        suite_idx = _PROMOTION_ORDER.index(suite.approval_status)
        if suite_idx < tier_idx:
            base.reason = (
                f"Suite '{suite_name}' at {suite.approval_status.value} "
                f"does not meet {min_approval.value} required for {repo_tier} tier"
            )
            return base

        # Check role allowlist + overlay additions
        try:
            agent_role = AgentRole(role)
        except ValueError:
            base.reason = f"Unknown agent role '{role}'"
            return base

        allowed_suites = set(ROLE_SUITE_ALLOWLIST.get(agent_role, frozenset()))
        for overlay_str in overlays:
            try:
                overlay = ToolOverlay(overlay_str)
                allowed_suites |= set(OVERLAY_SUITE_ADDITIONS.get(overlay, frozenset()))
            except ValueError:
                pass  # Unknown overlays are ignored

        if suite_name not in allowed_suites:
            base.reason = (
                f"Role '{role}' with overlays {overlays} "
                f"does not have access to suite '{suite_name}'"
            )
            return base

        base.allowed = True
        base.reason = "Access granted"
        return base


# --- Standard suites (seeded on import) ---

CODE_QUALITY_SUITE = ToolSuite(
    name="code-quality",
    description="Deterministic code analysis tools",
    tools=[
        ToolEntry("ruff", "Python linter and formatter", CapabilityCategory.CODE_QUALITY),
        ToolEntry("mypy", "Static type checker", CapabilityCategory.CODE_QUALITY),
        ToolEntry("bandit", "Security linter for Python", CapabilityCategory.SECURITY),
        ToolEntry("dead-code", "Dead code detector", CapabilityCategory.CODE_QUALITY),
    ],
    approval_status=ApprovalStatus.EXECUTE,
    version="1.0.0",
)

CONTEXT_RETRIEVAL_SUITE = ToolSuite(
    name="context-retrieval",
    description="Knowledge base and context pack access",
    tools=[
        ToolEntry("doc-fetch", "Fetch documentation from knowledge base", CapabilityCategory.CONTEXT_RETRIEVAL),
        ToolEntry("pack-lookup", "Look up Service Context Packs", CapabilityCategory.CONTEXT_RETRIEVAL),
        ToolEntry("memory-search", "Search project memory store", CapabilityCategory.CONTEXT_RETRIEVAL),
    ],
    approval_status=ApprovalStatus.EXECUTE,
    version="1.0.0",
)

DOCUMENTATION_SUITE = ToolSuite(
    name="documentation",
    description="Documentation generation and validation",
    tools=[
        ToolEntry("readme-gen", "Generate README from code", CapabilityCategory.DOCUMENTATION, read_only=False),
        ToolEntry("changelog", "Generate changelog entries", CapabilityCategory.DOCUMENTATION, read_only=False),
        ToolEntry("link-validation", "Validate documentation links", CapabilityCategory.DOCUMENTATION),
    ],
    approval_status=ApprovalStatus.SUGGEST,
    version="1.0.0",
)

STANDARD_SUITES = [CODE_QUALITY_SUITE, CONTEXT_RETRIEVAL_SUITE, DOCUMENTATION_SUITE]


def seed_standard_suites(catalog: ToolCatalog) -> None:
    """Register the 3 standard tool suites."""
    for suite in STANDARD_SUITES:
        try:
            catalog.register(suite)
        except SuiteDuplicateError:
            pass


# --- Default profiles ---

DEFAULT_PROFILES = [
    ToolProfile("observe-default", "default", ["code-quality"], "observe"),
    ToolProfile("suggest-default", "default", ["code-quality", "context-retrieval"], "suggest"),
    ToolProfile("execute-default", "default", ["code-quality", "context-retrieval", "documentation"], "execute"),
]


# --- Global instances ---

_catalog: ToolCatalog | None = None
_policy_engine: ToolPolicyEngine | None = None


def get_tool_catalog() -> ToolCatalog:
    global _catalog
    if _catalog is None:
        _catalog = ToolCatalog()
        seed_standard_suites(_catalog)
    return _catalog


def get_tool_policy_engine() -> ToolPolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = ToolPolicyEngine(get_tool_catalog())
    return _policy_engine
