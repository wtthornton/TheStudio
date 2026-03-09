"""Execution Plane Registry — manage multiple execution planes and repo assignments.

Epic 10, AC6: Execution Plane Management.
Tracks planes, their status, assigned repos, and health summaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class PlaneStatus(StrEnum):
    """Execution plane operational status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"


@dataclass
class ExecutionPlane:
    """An execution plane that runs workflows for assigned repos."""

    plane_id: UUID = field(default_factory=uuid4)
    name: str = ""
    region: str = "default"
    status: PlaneStatus = PlaneStatus.ACTIVE
    repo_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "plane_id": str(self.plane_id),
            "name": self.name,
            "region": self.region,
            "status": self.status.value,
            "repo_ids": self.repo_ids,
            "repo_count": len(self.repo_ids),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PlaneHealthSummary:
    """Health summary for an execution plane."""

    plane_id: UUID
    name: str
    status: PlaneStatus
    repo_count: int
    healthy: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plane_id": str(self.plane_id),
            "name": self.name,
            "status": self.status.value,
            "repo_count": self.repo_count,
            "healthy": self.healthy,
            "reason": self.reason,
        }


# In-memory registry
_planes: dict[UUID, ExecutionPlane] = {}


class ExecutionPlaneRegistry:
    """Manages execution planes and repo-to-plane assignments."""

    def register(self, name: str, region: str = "default") -> ExecutionPlane:
        """Register a new execution plane."""
        plane = ExecutionPlane(name=name, region=region)
        _planes[plane.plane_id] = plane
        logger.info("Registered plane %s (%s) in region %s", plane.plane_id, name, region)
        return plane

    def list_planes(self) -> list[ExecutionPlane]:
        """List all registered planes."""
        return sorted(_planes.values(), key=lambda p: p.created_at)

    def get_plane(self, plane_id: UUID) -> ExecutionPlane | None:
        """Get a plane by ID."""
        return _planes.get(plane_id)

    def assign_repo(self, plane_id: UUID, repo_id: str) -> bool:
        """Assign a repo to a plane."""
        plane = _planes.get(plane_id)
        if plane is None:
            return False
        if repo_id not in plane.repo_ids:
            plane.repo_ids.append(repo_id)
            logger.info("Assigned repo %s to plane %s", repo_id, plane.name)
        return True

    def unassign_repo(self, plane_id: UUID, repo_id: str) -> bool:
        """Remove a repo from a plane."""
        plane = _planes.get(plane_id)
        if plane is None:
            return False
        if repo_id in plane.repo_ids:
            plane.repo_ids.remove(repo_id)
            logger.info("Unassigned repo %s from plane %s", repo_id, plane.name)
        return True

    def set_status(self, plane_id: UUID, status: PlaneStatus) -> bool:
        """Set plane status (active, paused, draining)."""
        plane = _planes.get(plane_id)
        if plane is None:
            return False
        plane.status = status
        logger.info("Plane %s status set to %s", plane.name, status.value)
        return True

    def get_health_summary(self) -> list[PlaneHealthSummary]:
        """Get health summary for all planes."""
        summaries = []
        for plane in self.list_planes():
            healthy = plane.status == PlaneStatus.ACTIVE
            reason = None if healthy else f"Plane is {plane.status.value}"
            summaries.append(PlaneHealthSummary(
                plane_id=plane.plane_id,
                name=plane.name,
                status=plane.status,
                repo_count=len(plane.repo_ids),
                healthy=healthy,
                reason=reason,
            ))
        return summaries

    def total_repo_count(self) -> int:
        """Count total repos across all planes."""
        seen: set[str] = set()
        for plane in _planes.values():
            seen.update(plane.repo_ids)
        return len(seen)

    def delete(self, plane_id: UUID) -> bool:
        """Delete a plane (must have no assigned repos)."""
        plane = _planes.get(plane_id)
        if plane is None:
            return False
        if plane.repo_ids:
            logger.warning("Cannot delete plane %s: has %d assigned repos", plane.name, len(plane.repo_ids))
            return False
        del _planes[plane_id]
        logger.info("Deleted plane %s", plane.name)
        return True


def clear() -> None:
    """Clear all planes (for testing)."""
    _planes.clear()


# Global instance
_registry: ExecutionPlaneRegistry | None = None


def get_plane_registry() -> ExecutionPlaneRegistry:
    """Get or create the global ExecutionPlaneRegistry instance."""
    global _registry
    if _registry is None:
        _registry = ExecutionPlaneRegistry()
    return _registry
