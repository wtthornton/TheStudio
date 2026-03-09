"""Unit tests for Epic 10 UI router endpoints.

Covers quarantine, dead-letter, planes, merge-mode, promotion-history.

Uses FastAPI TestClient with mocked services (same pattern as test_admin_ui.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.admin.merge_mode import MergeMode, set_merge_mode
from src.admin.merge_mode import clear as clear_merge_modes
from src.admin.rbac import Role
from src.compliance.plane_registry import clear as clear_planes
from src.compliance.plane_registry import get_plane_registry
from src.compliance.promotion import (
    TierTransition,
    store_transition,
)
from src.compliance.promotion import (
    clear as clear_transitions,
)
from src.outcome.dead_letter import clear as clear_dead_letters
from src.outcome.dead_letter import get_dead_letter_store
from src.outcome.models import QuarantineReason
from src.outcome.quarantine import clear as clear_quarantine
from src.outcome.quarantine import get_quarantine_store
from src.repo.repo_profile import RepoTier


@pytest.fixture(autouse=True)
def _reset_all_state():
    clear_merge_modes()
    clear_planes()
    clear_transitions()
    clear_quarantine()
    clear_dead_letters()
    yield
    clear_merge_modes()
    clear_planes()
    clear_transitions()
    clear_quarantine()
    clear_dead_letters()


@pytest.fixture
def _mock_services():
    """Minimal mocks for services the UI router depends on."""
    rbac_svc = MagicMock()
    rbac_svc.get_user_role = AsyncMock(return_value=Role.ADMIN)

    health_svc = MagicMock()
    health_svc.check_all = AsyncMock(return_value=MagicMock(
        healthy=True,
        services={},
        overall_status="healthy",
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
def client(_mock_services) -> TestClient:
    from src.admin.ui_router import ui_router

    app = FastAPI()
    app.include_router(ui_router)
    return TestClient(app)


ADMIN_HEADERS = {"X-User-ID": "admin@studio"}


# --- Quarantine Routes (AC1) ---


class TestQuarantinePage:
    def test_quarantine_page_renders(self, client):
        resp = client.get("/admin/ui/quarantine", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_quarantine_partial_empty(self, client):
        resp = client.get("/admin/ui/partials/quarantine", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_quarantine_partial_with_data(self, client):
        store = get_quarantine_store()
        store.quarantine({"evt": "test"}, QuarantineReason.UNKNOWN_REPO, repo_id="r1")
        resp = client.get("/admin/ui/partials/quarantine", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_quarantine_partial_filter_by_reason(self, client):
        store = get_quarantine_store()
        store.quarantine({"a": 1}, QuarantineReason.MISSING_CORRELATION_ID)
        store.quarantine({"b": 2}, QuarantineReason.UNKNOWN_REPO)
        resp = client.get(
            "/admin/ui/partials/quarantine?reason=unknown_repo",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200

    def test_quarantine_detail_found(self, client):
        store = get_quarantine_store()
        qid = store.quarantine({"evt": "test"}, QuarantineReason.UNKNOWN_REPO)
        resp = client.get(f"/admin/ui/partials/quarantine/{qid}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_quarantine_detail_not_found(self, client):
        fake_id = uuid4()
        resp = client.get(f"/admin/ui/partials/quarantine/{fake_id}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "not found" in resp.text.lower()

    def test_quarantine_replay(self, client):
        store = get_quarantine_store()
        qid = store.quarantine({"evt": "test"}, QuarantineReason.UNKNOWN_REPO)
        resp = client.post(f"/admin/ui/partials/quarantine/{qid}/replay", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        event = store.get_quarantined(qid)
        assert event.replayed_at is not None

    def test_quarantine_delete(self, client):
        store = get_quarantine_store()
        qid = store.quarantine({"evt": "test"}, QuarantineReason.UNKNOWN_REPO)
        resp = client.delete(f"/admin/ui/partials/quarantine/{qid}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "deleted" in resp.text.lower()
        assert store.get_quarantined(qid) is None


# --- Dead-Letter Routes (AC2) ---


class TestDeadLetterPage:
    def test_dead_letters_page_renders(self, client):
        resp = client.get("/admin/ui/dead-letters", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_dead_letters_partial_empty(self, client):
        resp = client.get("/admin/ui/partials/dead-letters", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_dead_letters_partial_with_data(self, client):
        store = get_dead_letter_store()
        store.add_dead_letter(b"raw data", "parse error", 3)
        resp = client.get("/admin/ui/partials/dead-letters", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_dead_letter_detail_found(self, client):
        store = get_dead_letter_store()
        eid = store.add_dead_letter(b"raw", "err", 2)
        resp = client.get(f"/admin/ui/partials/dead-letter/{eid}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_dead_letter_detail_not_found(self, client):
        resp = client.get(f"/admin/ui/partials/dead-letter/{uuid4()}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "not found" in resp.text.lower()

    def test_dead_letter_delete(self, client):
        store = get_dead_letter_store()
        eid = store.add_dead_letter(b"raw", "err", 2)
        resp = client.delete(f"/admin/ui/partials/dead-letter/{eid}", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "deleted" in resp.text.lower()
        assert store.get_dead_letter(eid) is None


# --- Merge Mode Routes (AC3) ---


class TestMergeModeRoutes:
    def test_merge_mode_get_default(self, client):
        resp = client.get("/admin/ui/partials/merge-mode/my-repo", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "draft_only" in resp.text

    def test_merge_mode_get_after_set(self, client):
        set_merge_mode("my-repo", MergeMode.AUTO_MERGE)
        resp = client.get("/admin/ui/partials/merge-mode/my-repo", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "auto_merge" in resp.text

    def test_merge_mode_post_update(self, client):
        resp = client.post(
            "/admin/ui/partials/merge-mode/my-repo",
            data={"mode": "require_review"},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert "Updated" in resp.text
        from src.admin.merge_mode import get_merge_mode

        assert get_merge_mode("my-repo") == MergeMode.REQUIRE_REVIEW

    def test_merge_mode_post_invalid_falls_back(self, client):
        resp = client.post(
            "/admin/ui/partials/merge-mode/my-repo",
            data={"mode": "invalid_mode"},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        from src.admin.merge_mode import get_merge_mode

        assert get_merge_mode("my-repo") == MergeMode.DRAFT_ONLY


# --- Execution Plane Routes (AC6) ---


class TestPlaneRoutes:
    def test_planes_page_renders(self, client):
        resp = client.get("/admin/ui/planes", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_planes_partial_empty(self, client):
        resp = client.get("/admin/ui/partials/planes", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_planes_partial_with_data(self, client):
        registry = get_plane_registry()
        registry.register("us-east", region="us-east-1")
        resp = client.get("/admin/ui/partials/planes", headers=ADMIN_HEADERS)
        assert resp.status_code == 200

    def test_plane_register(self, client):
        resp = client.post(
            "/admin/ui/partials/planes/register",
            data={"name": "new-plane", "region": "eu-west-1"},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        registry = get_plane_registry()
        planes = registry.list_planes()
        assert len(planes) == 1
        assert planes[0].name == "new-plane"
        assert planes[0].region == "eu-west-1"

    def test_plane_register_empty_name_ignored(self, client):
        resp = client.post(
            "/admin/ui/partials/planes/register",
            data={"name": "", "region": "default"},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        registry = get_plane_registry()
        assert len(registry.list_planes()) == 0

    def test_plane_pause(self, client):
        registry = get_plane_registry()
        plane = registry.register("test")
        resp = client.post(
            f"/admin/ui/partials/planes/{plane.plane_id}/pause",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        from src.compliance.plane_registry import PlaneStatus

        assert registry.get_plane(plane.plane_id).status == PlaneStatus.PAUSED

    def test_plane_resume(self, client):
        registry = get_plane_registry()
        plane = registry.register("test")
        from src.compliance.plane_registry import PlaneStatus

        registry.set_status(plane.plane_id, PlaneStatus.PAUSED)
        resp = client.post(
            f"/admin/ui/partials/planes/{plane.plane_id}/resume",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert registry.get_plane(plane.plane_id).status == PlaneStatus.ACTIVE


# --- Promotion History Route (AC7) ---


class TestPromotionHistoryRoute:
    def test_no_history(self, client):
        repo_id = uuid4()
        resp = client.get(
            f"/admin/ui/partials/promotion-history/{repo_id}",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert "No promotion history" in resp.text

    def test_with_history(self, client):
        repo_id = uuid4()
        store_transition(TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.OBSERVE,
            to_tier=RepoTier.SUGGEST,
            triggered_by="admin",
            compliance_score=85.0,
            reason="Promoted by admin",
        ))
        resp = client.get(
            f"/admin/ui/partials/promotion-history/{repo_id}",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert "observe" in resp.text
        assert "suggest" in resp.text
        assert "admin" in resp.text
        assert "85" in resp.text

    def test_with_remediation_items(self, client):
        from src.compliance.promotion import RemediationItem

        repo_id = uuid4()
        store_transition(TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.SUGGEST,
            to_tier=RepoTier.EXECUTE,
            triggered_by="system",
            reason="Blocked: ci",
            remediation_items=[
                RemediationItem(check_name="ci", description="Fix CI"),
            ],
        ))
        resp = client.get(
            f"/admin/ui/partials/promotion-history/{repo_id}",
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert "1 item(s)" in resp.text
