"""Tests for GET /api/v1/dashboard/tasks/:id/evidence (Epic 38, Story 38.7)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketRead, TaskPacketStatus, TaskTrustTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_read(
    *,
    task_id: UUID | None = None,
    status: TaskPacketStatus = TaskPacketStatus.PUBLISHED,
    trust_tier: TaskTrustTier | None = TaskTrustTier.SUGGEST,
    pr_number: int | None = 42,
    pr_url: str | None = "https://github.com/owner/repo/pull/42",
    loopback_count: int = 1,
    issue_title: str | None = "Fix SSO login timeout",
) -> TaskPacketRead:
    """Build a TaskPacketRead with sensible defaults."""
    now = datetime.now(UTC)
    return TaskPacketRead(
        id=task_id or uuid4(),
        repo="owner/repo",
        issue_id=7,
        delivery_id="d-abc123",
        correlation_id=uuid4(),
        source_name="github",
        status=status,
        loopback_count=loopback_count,
        task_trust_tier=trust_tier,
        pr_number=pr_number,
        pr_url=pr_url,
        issue_title=issue_title,
        created_at=now,
        updated_at=now,
    )


def _mock_session(task: TaskPacketRead | None) -> AsyncMock:
    """Return an AsyncMock DB session whose get() returns a matching row or None."""
    session = AsyncMock()
    if task is None:
        session.get = AsyncMock(return_value=None)
    else:
        # get_by_id uses session.get(TaskPacketRow, task_id)
        row = MagicMock()
        row.configure_mock(**task.model_dump())
        # Ensure model_validate works by having all fields accessible as attributes
        for field_name, value in task.model_dump().items():
            setattr(row, field_name, value)
        session.get = AsyncMock(return_value=row)
    return session


@pytest.fixture(autouse=True)
def no_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable bearer-token auth for all tests in this module."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient for the full app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestGetTaskEvidenceHappyPath:
    def test_returns_200_with_evidence_payload(self, client: TestClient) -> None:
        """Returns HTTP 200 with a well-formed EvidencePayload for a known task."""
        task = _make_task_read()
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == "1.0"
        assert data["generated_at"] is not None

    def test_task_summary_fields_populated(self, client: TestClient) -> None:
        """task_summary section contains id, status, repo, issue_id from the TaskPacket."""
        task = _make_task_read(status=TaskPacketStatus.PUBLISHED)
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["taskpacket_id"] == str(task.id)
        assert ts["repo"] == "owner/repo"
        assert ts["issue_id"] == 7
        assert ts["status"] == "published"

    def test_trust_tier_included(self, client: TestClient) -> None:
        """trust_tier is serialised as its string value in task_summary."""
        task = _make_task_read(trust_tier=TaskTrustTier.EXECUTE)
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["trust_tier"] == "execute"

    def test_trust_tier_none_when_not_set(self, client: TestClient) -> None:
        """trust_tier is null in task_summary when not assigned."""
        task = _make_task_read(trust_tier=None)
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["trust_tier"] is None

    def test_pr_fields_included(self, client: TestClient) -> None:
        """PR number and URL are included in task_summary when present."""
        task = _make_task_read(pr_number=77, pr_url="https://github.com/owner/repo/pull/77")
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["pr_number"] == 77
        assert ts["pr_url"] == "https://github.com/owner/repo/pull/77"

    def test_pr_fields_null_when_not_published(self, client: TestClient) -> None:
        """PR fields are null for tasks that have not been published yet."""
        task = _make_task_read(
            status=TaskPacketStatus.IN_PROGRESS,
            pr_number=None,
            pr_url=None,
        )
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["pr_number"] is None
        assert ts["pr_url"] is None

    def test_loopback_count_included(self, client: TestClient) -> None:
        """loopback_count is accurately reflected in task_summary."""
        task = _make_task_read(loopback_count=3)
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["loopback_count"] == 3

    def test_optional_sections_are_null(self, client: TestClient) -> None:
        """intent, gate_results, cost_breakdown, provenance are null (not yet persisted)."""
        task = _make_task_read()
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] is None
        assert data["gate_results"] is None
        assert data["cost_breakdown"] is None
        assert data["provenance"] is None
        assert data["files_changed"] == []

    def test_issue_title_included(self, client: TestClient) -> None:
        """issue_title is surfaced in task_summary when stored."""
        task = _make_task_read(issue_title="Add dark mode support")
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["issue_title"] == "Add dark mode support"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestGetTaskEvidenceErrorCases:
    def test_returns_404_for_unknown_task(self, client: TestClient) -> None:
        """Returns HTTP 404 when no TaskPacket exists for the given ID."""
        missing_id = uuid4()
        session = _mock_session(None)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{missing_id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_returns_422_for_invalid_uuid(self, client: TestClient) -> None:
        """Returns HTTP 422 when the task_id path parameter is not a valid UUID."""
        resp = client.get("/api/v1/dashboard/tasks/not-a-uuid/evidence")
        assert resp.status_code == 422

    def test_correlation_id_in_task_summary(self, client: TestClient) -> None:
        """correlation_id is present in task_summary."""
        task = _make_task_read()
        session = _mock_session(task)

        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = client.get(f"/api/v1/dashboard/tasks/{task.id}/evidence")
        finally:
            app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        ts = resp.json()["task_summary"]
        assert ts["correlation_id"] == str(task.correlation_id)
