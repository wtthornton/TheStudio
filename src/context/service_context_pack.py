"""Service Context Pack interface and stub.

Phase 0: stub implementation. Phase 3 plugs in real packs.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceContextPack:
    """A context pack containing service-specific knowledge."""

    name: str
    version: str
    content: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "content": self.content,
        }


def get_context_packs(repo: str) -> list[ServiceContextPack]:
    """Return applicable Service Context Packs for a repo.

    Phase 0: returns empty list (no real packs yet).
    """
    # Stub — Phase 3 will query a pack registry based on repo and components
    return []
