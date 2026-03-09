"""Unit tests for src/compliance/plane_registry.py — Epic 10 AC6."""

import pytest

from src.compliance.plane_registry import (
    ExecutionPlane,
    ExecutionPlaneRegistry,
    PlaneHealthSummary,
    PlaneStatus,
    clear,
    get_plane_registry,
)


@pytest.fixture(autouse=True)
def _reset_state():
    clear()
    yield
    clear()


@pytest.fixture
def registry() -> ExecutionPlaneRegistry:
    return ExecutionPlaneRegistry()


class TestPlaneStatus:
    def test_enum_values(self):
        assert PlaneStatus.ACTIVE == "active"
        assert PlaneStatus.PAUSED == "paused"
        assert PlaneStatus.DRAINING == "draining"


class TestExecutionPlane:
    def test_to_dict(self):
        plane = ExecutionPlane(name="us-east", region="us-east-1")
        d = plane.to_dict()
        assert d["name"] == "us-east"
        assert d["region"] == "us-east-1"
        assert d["status"] == "active"
        assert d["repo_count"] == 0
        assert d["repo_ids"] == []
        assert "plane_id" in d
        assert "created_at" in d


class TestPlaneHealthSummary:
    def test_to_dict(self):
        from uuid import uuid4

        pid = uuid4()
        s = PlaneHealthSummary(
            plane_id=pid,
            name="test",
            status=PlaneStatus.PAUSED,
            repo_count=3,
            healthy=False,
            reason="Plane is paused",
        )
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["healthy"] is False
        assert d["reason"] == "Plane is paused"


class TestRegister:
    def test_register_creates_plane(self, registry):
        plane = registry.register("us-east", region="us-east-1")
        assert plane.name == "us-east"
        assert plane.region == "us-east-1"
        assert plane.status == PlaneStatus.ACTIVE

    def test_register_default_region(self, registry):
        plane = registry.register("default-plane")
        assert plane.region == "default"

    def test_register_multiple(self, registry):
        registry.register("plane-1")
        registry.register("plane-2")
        assert len(registry.list_planes()) == 2


class TestListPlanes:
    def test_empty(self, registry):
        assert registry.list_planes() == []

    def test_sorted_by_creation(self, registry):
        p1 = registry.register("first")
        p2 = registry.register("second")
        planes = registry.list_planes()
        assert planes[0].plane_id == p1.plane_id
        assert planes[1].plane_id == p2.plane_id


class TestGetPlane:
    def test_found(self, registry):
        plane = registry.register("test")
        assert registry.get_plane(plane.plane_id) is plane

    def test_not_found(self, registry):
        from uuid import uuid4

        assert registry.get_plane(uuid4()) is None


class TestAssignRepo:
    def test_assign_success(self, registry):
        plane = registry.register("test")
        assert registry.assign_repo(plane.plane_id, "owner/repo") is True
        assert "owner/repo" in plane.repo_ids

    def test_assign_idempotent(self, registry):
        plane = registry.register("test")
        registry.assign_repo(plane.plane_id, "owner/repo")
        registry.assign_repo(plane.plane_id, "owner/repo")
        assert plane.repo_ids.count("owner/repo") == 1

    def test_assign_nonexistent_plane(self, registry):
        from uuid import uuid4

        assert registry.assign_repo(uuid4(), "owner/repo") is False


class TestUnassignRepo:
    def test_unassign_success(self, registry):
        plane = registry.register("test")
        registry.assign_repo(plane.plane_id, "owner/repo")
        assert registry.unassign_repo(plane.plane_id, "owner/repo") is True
        assert "owner/repo" not in plane.repo_ids

    def test_unassign_not_assigned(self, registry):
        plane = registry.register("test")
        assert registry.unassign_repo(plane.plane_id, "owner/repo") is True

    def test_unassign_nonexistent_plane(self, registry):
        from uuid import uuid4

        assert registry.unassign_repo(uuid4(), "owner/repo") is False


class TestSetStatus:
    def test_pause(self, registry):
        plane = registry.register("test")
        assert registry.set_status(plane.plane_id, PlaneStatus.PAUSED) is True
        assert plane.status == PlaneStatus.PAUSED

    def test_drain(self, registry):
        plane = registry.register("test")
        assert registry.set_status(plane.plane_id, PlaneStatus.DRAINING) is True
        assert plane.status == PlaneStatus.DRAINING

    def test_resume(self, registry):
        plane = registry.register("test")
        registry.set_status(plane.plane_id, PlaneStatus.PAUSED)
        assert registry.set_status(plane.plane_id, PlaneStatus.ACTIVE) is True
        assert plane.status == PlaneStatus.ACTIVE

    def test_nonexistent_plane(self, registry):
        from uuid import uuid4

        assert registry.set_status(uuid4(), PlaneStatus.PAUSED) is False


class TestHealthSummary:
    def test_active_plane_healthy(self, registry):
        registry.register("healthy")
        summaries = registry.get_health_summary()
        assert len(summaries) == 1
        assert summaries[0].healthy is True
        assert summaries[0].reason is None

    def test_paused_plane_unhealthy(self, registry):
        plane = registry.register("paused")
        registry.set_status(plane.plane_id, PlaneStatus.PAUSED)
        summaries = registry.get_health_summary()
        assert summaries[0].healthy is False
        assert "paused" in summaries[0].reason

    def test_draining_plane_unhealthy(self, registry):
        plane = registry.register("draining")
        registry.set_status(plane.plane_id, PlaneStatus.DRAINING)
        summaries = registry.get_health_summary()
        assert summaries[0].healthy is False

    def test_repo_count_in_summary(self, registry):
        plane = registry.register("test")
        registry.assign_repo(plane.plane_id, "repo-1")
        registry.assign_repo(plane.plane_id, "repo-2")
        summaries = registry.get_health_summary()
        assert summaries[0].repo_count == 2


class TestTotalRepoCount:
    def test_empty(self, registry):
        assert registry.total_repo_count() == 0

    def test_counts_unique_repos(self, registry):
        p1 = registry.register("plane-1")
        p2 = registry.register("plane-2")
        registry.assign_repo(p1.plane_id, "repo-a")
        registry.assign_repo(p1.plane_id, "repo-b")
        registry.assign_repo(p2.plane_id, "repo-b")  # Duplicate
        registry.assign_repo(p2.plane_id, "repo-c")
        assert registry.total_repo_count() == 3  # a, b, c


class TestDelete:
    def test_delete_empty_plane(self, registry):
        plane = registry.register("test")
        assert registry.delete(plane.plane_id) is True
        assert registry.get_plane(plane.plane_id) is None

    def test_delete_with_repos_fails(self, registry):
        plane = registry.register("test")
        registry.assign_repo(plane.plane_id, "repo-1")
        assert registry.delete(plane.plane_id) is False
        assert registry.get_plane(plane.plane_id) is not None

    def test_delete_nonexistent(self, registry):
        from uuid import uuid4

        assert registry.delete(uuid4()) is False


class TestGetPlaneRegistry:
    def test_returns_singleton(self):
        r1 = get_plane_registry()
        r2 = get_plane_registry()
        assert r1 is r2
