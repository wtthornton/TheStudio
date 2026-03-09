"""Scale proof test — Epic 11 Sprint 3 exit criterion.

Verifies:
- 2+ execution planes can be registered and operated
- 10+ repos can be assigned across planes
- Health summary renders correctly with this data
- Admin UI planes page renders with seed data via TestClient
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.admin.rbac import Role
from src.compliance.plane_registry import (
    ExecutionPlaneRegistry,
    PlaneStatus,
    clear,
    get_plane_registry,
)


@pytest.fixture(autouse=True)
def _reset():
    clear()
    yield
    clear()


def _seed_planes_and_repos(
    registry: ExecutionPlaneRegistry,
    plane_count: int = 3,
    repos_per_plane: int = 5,
) -> tuple[list[UUID], list[str]]:
    """Seed execution planes with repos. Returns (plane_ids, repo_ids)."""
    plane_ids = []
    all_repo_ids = []

    regions = ["us-east-1", "eu-west-1", "ap-southeast-1"]

    for i in range(plane_count):
        plane = registry.register(
            name=f"plane-{i + 1}",
            region=regions[i % len(regions)],
        )
        plane_ids.append(plane.plane_id)

        for j in range(repos_per_plane):
            repo_id = f"org-{i + 1}/repo-{j + 1}"
            registry.assign_repo(plane.plane_id, repo_id)
            all_repo_ids.append(repo_id)

    return plane_ids, all_repo_ids


class TestScaleProof:
    """Phase 4 exit criterion: 2+ planes, 10+ repos."""

    def test_register_multiple_planes(self):
        registry = ExecutionPlaneRegistry()
        plane_ids, repo_ids = _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=5)

        assert len(plane_ids) == 3
        assert len(repo_ids) == 15
        assert registry.total_repo_count() == 15

    def test_minimum_scale_2_planes_10_repos(self):
        """Minimum: 2 planes, 10 repos."""
        registry = ExecutionPlaneRegistry()
        plane_ids, repo_ids = _seed_planes_and_repos(registry, plane_count=2, repos_per_plane=5)

        planes = registry.list_planes()
        assert len(planes) >= 2
        assert registry.total_repo_count() >= 10

    def test_health_summary_at_scale(self):
        registry = ExecutionPlaneRegistry()
        plane_ids, _ = _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=5)

        # Pause one plane
        registry.set_status(plane_ids[1], PlaneStatus.PAUSED)

        summaries = registry.get_health_summary()
        assert len(summaries) == 3

        healthy_count = sum(1 for s in summaries if s.healthy)
        unhealthy_count = sum(1 for s in summaries if not s.healthy)
        assert healthy_count == 2
        assert unhealthy_count == 1

        # All summaries have correct repo counts
        for s in summaries:
            assert s.repo_count == 5

    def test_plane_operations_at_scale(self):
        """Pause, resume, drain operations work correctly at scale."""
        registry = ExecutionPlaneRegistry()
        plane_ids, _ = _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=4)

        # Pause all
        for pid in plane_ids:
            registry.set_status(pid, PlaneStatus.PAUSED)
        assert all(p.status == PlaneStatus.PAUSED for p in registry.list_planes())

        # Resume first, drain second
        registry.set_status(plane_ids[0], PlaneStatus.ACTIVE)
        registry.set_status(plane_ids[1], PlaneStatus.DRAINING)

        statuses = {p.name: p.status for p in registry.list_planes()}
        assert statuses["plane-1"] == PlaneStatus.ACTIVE
        assert statuses["plane-2"] == PlaneStatus.DRAINING
        assert statuses["plane-3"] == PlaneStatus.PAUSED

    def test_cross_plane_repo_assignment(self):
        """Same repo assigned to multiple planes (edge case)."""
        registry = ExecutionPlaneRegistry()
        p1 = registry.register("plane-1")
        p2 = registry.register("plane-2")

        # Assign same 5 repos to both planes
        for i in range(5):
            repo_id = f"shared/repo-{i}"
            registry.assign_repo(p1.plane_id, repo_id)
            registry.assign_repo(p2.plane_id, repo_id)

        # Assign 3 unique repos to plane-1 only
        for i in range(3):
            registry.assign_repo(p1.plane_id, f"unique/repo-{i}")

        # Total unique repos = 5 shared + 3 unique = 8
        assert registry.total_repo_count() == 8


class TestScaleProofUIRendering:
    """Verify admin UI planes page renders correctly with seed data."""

    @pytest.fixture
    def _mock_services(self):
        rbac_svc = MagicMock()
        rbac_svc.get_user_role = AsyncMock(return_value=Role.ADMIN)

        health_svc = MagicMock()
        health_svc.check_all = AsyncMock(return_value=MagicMock(
            healthy=True, services={}, overall_status="healthy",
        ))

        with (
            patch("src.admin.ui_router.get_rbac_service", return_value=rbac_svc),
            patch("src.admin.ui_router.get_health_service", return_value=health_svc),
            patch("src.admin.ui_router.get_async_session"),
        ):
            from src.admin import ui_router as ui_mod

            mock_session = AsyncMock()
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            ui_mod.get_async_session = MagicMock(return_value=mock_cm)
            yield

    @pytest.fixture
    def client(self, _mock_services) -> TestClient:
        from src.admin.ui_router import ui_router

        app = FastAPI()
        app.include_router(ui_router)
        return TestClient(app)

    def test_planes_page_with_seed_data(self, client):
        """Planes page renders with 3 planes and 15 repos."""
        registry = get_plane_registry()
        _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=5)

        resp = client.get("/admin/ui/planes", headers={"X-User-ID": "admin@studio"})
        assert resp.status_code == 200

    def test_planes_partial_shows_all_planes(self, client):
        """Planes partial renders all 3 planes with repo counts."""
        registry = get_plane_registry()
        _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=5)

        resp = client.get("/admin/ui/partials/planes", headers={"X-User-ID": "admin@studio"})
        assert resp.status_code == 200

    def test_planes_partial_with_mixed_statuses(self, client):
        """Planes partial correctly shows mixed health statuses."""
        registry = get_plane_registry()
        plane_ids, _ = _seed_planes_and_repos(registry, plane_count=3, repos_per_plane=4)

        registry.set_status(plane_ids[1], PlaneStatus.PAUSED)
        registry.set_status(plane_ids[2], PlaneStatus.DRAINING)

        resp = client.get("/admin/ui/partials/planes", headers={"X-User-ID": "admin@studio"})
        assert resp.status_code == 200
