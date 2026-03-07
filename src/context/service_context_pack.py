"""Service Context Pack schema and registry.

Provides ServiceContextPack dataclass and PackRegistry for matching
repos to their applicable context packs.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceContextPack:
    """A context pack containing service-specific knowledge for a domain."""

    name: str
    version: str
    repo_patterns: list[str] = field(default_factory=list)
    conventions: list[str] = field(default_factory=list)
    api_patterns: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    testing_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "content": {
                "conventions": self.conventions,
                "api_patterns": self.api_patterns,
                "constraints": self.constraints,
                "testing_notes": self.testing_notes,
            },
        }

    def matches_repo(self, repo: str) -> bool:
        """Check if this pack applies to the given repo."""
        return any(fnmatch.fnmatch(repo, pattern) for pattern in self.repo_patterns)


class PackRegistry:
    """In-memory registry of Service Context Packs."""

    def __init__(self) -> None:
        self._packs: list[ServiceContextPack] = []

    def register(self, pack: ServiceContextPack) -> None:
        """Register a context pack."""
        self._packs.append(pack)

    def get_packs(self, repo: str) -> list[ServiceContextPack]:
        """Return all packs matching the given repo."""
        return [p for p in self._packs if p.matches_repo(repo)]

    @property
    def all_packs(self) -> list[ServiceContextPack]:
        """Return all registered packs."""
        return list(self._packs)

    def clear(self) -> None:
        """Remove all registered packs (for testing)."""
        self._packs.clear()


# Global registry instance
_registry = PackRegistry()


def get_registry() -> PackRegistry:
    """Return the global pack registry."""
    return _registry


def get_context_packs(repo: str) -> list[ServiceContextPack]:
    """Return applicable Service Context Packs for a repo."""
    return _registry.get_packs(repo)
