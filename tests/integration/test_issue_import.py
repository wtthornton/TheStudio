"""Integration tests for POST /api/v1/dashboard/github/import (Epic 38, Story 38.4).

Tests the full import flow against a real PostgreSQL database:
- Import 2 issues → TaskPackets created with source_name="dashboard_import"
- Duplicate import blocked (second call with same issue number returns status="duplicate")
- Triage mode: status=TRIAGE, workflow NOT started
- Direct mode: status=RECEIVED, workflow started

GitHub API is not called by the import endpoint (issue data is provided in the request
body), so no GitHub API mock is needed.  The Temporal workflow trigger IS mocked to
avoid requiring a live Temporal server.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketStatus
from src.models.taskpacket_crud import get_by_repo_and_issue
from src.settings import settings

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_REPO = "test-org/import-test-repo"


@pytest.fixture
async def db_engine():
    """Create a transient in-test PostgreSQL engine with fresh schema."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine):
    """Yield a live database session for assertion helpers."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def http_client(db_engine, monkeypatch: pytest.MonkeyPatch):
    """Async HTTP client wired to the FastAPI app with real DB and no auth.

    * ``get_session`` dependency is overridden to use the test-scoped engine.
    * Dashboard token auth is disabled.
    * GitHub token is set to a stub value.
    * Temporal workflow trigger is mocked globally for this fixture's scope.
    """
    # Configure settings
    monkeypatch.setattr(settings, "dashboard_token", "")
    monkeypatch.setattr(settings, "intake_poll_token", "test-token-abc")

    # Override get_session to use the test-scoped engine
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _issue(number: int, title: str = "Fix bug #{n}", body: str | None = None) -> dict:
    return {
        "number": number,
        "title": title.format(n=number),
        "body": body or f"Description for issue #{number}",
        "labels": ["bug"],
    }


def _import_payload(
    issues: list[dict],
    repo: str = _REPO,
    triage_override: bool | None = None,
) -> dict:
    body: dict = {"repo": repo, "issues": issues}
    if triage_override is not None:
        body["triage_override"] = triage_override
    return body


# ---------------------------------------------------------------------------
# Test: import 2 issues in direct mode (RECEIVED + workflow started)
# ---------------------------------------------------------------------------


async def test_import_two_issues_direct_mode(
    http_client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importing 2 issues in direct mode creates 2 TaskPackets with correct metadata."""
    monkeypatch.setattr(settings, "triage_mode_enabled", False)

    workflow_mock = AsyncMock(return_value="run-id")
    with patch("src.ingress.workflow_trigger.start_workflow", workflow_mock):
        resp = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(
                issues=[_issue(10), _issue(11)],
            ),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["repo"] == _REPO
    assert data["created"] == 2
    assert data["duplicates"] == 0
    assert data["errors"] == 0
    assert len(data["results"]) == 2

    for result in data["results"]:
        assert result["status"] == "created"
        assert result["task_id"] is not None
        assert result["workflow_started"] is True

    # Verify TaskPackets exist in the database with correct source_name
    for issue_number in (10, 11):
        row = await get_by_repo_and_issue(session, _REPO, issue_number)
        assert row is not None, f"TaskPacket for issue #{issue_number} not found"
        assert row.source_name == "dashboard_import"
        assert row.status == TaskPacketStatus.RECEIVED
        assert row.repo == _REPO
        assert row.issue_id == issue_number

    # Workflow should have been triggered twice (once per issue)
    assert workflow_mock.call_count == 2


# ---------------------------------------------------------------------------
# Test: duplicate import blocked
# ---------------------------------------------------------------------------


async def test_duplicate_import_blocked(
    http_client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-importing the same issue returns status='duplicate' without creating a second row."""
    monkeypatch.setattr(settings, "triage_mode_enabled", False)

    workflow_mock = AsyncMock(return_value="run-id")
    with patch("src.ingress.workflow_trigger.start_workflow", workflow_mock):
        # First import — should succeed
        resp1 = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(issues=[_issue(20)]),
        )
        assert resp1.status_code == 200
        first_task_id = resp1.json()["results"][0]["task_id"]

        # Second import of the same issue — should be blocked
        resp2 = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(issues=[_issue(20)]),
        )

    assert resp2.status_code == 200, resp2.text
    data = resp2.json()

    assert data["created"] == 0
    assert data["duplicates"] == 1
    assert data["errors"] == 0

    dup_result = data["results"][0]
    assert dup_result["status"] == "duplicate"
    assert dup_result["task_id"] == first_task_id  # Returns the existing task's id
    assert dup_result["workflow_started"] is False

    # Workflow was only started once (not a second time for the duplicate)
    assert workflow_mock.call_count == 1


# ---------------------------------------------------------------------------
# Test: triage mode — status=TRIAGE, workflow NOT started
# ---------------------------------------------------------------------------


async def test_import_triage_mode(
    http_client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Import with triage_override=True creates TaskPacket in TRIAGE status, no workflow."""
    monkeypatch.setattr(settings, "triage_mode_enabled", False)  # server default off

    workflow_mock = AsyncMock(return_value="run-id")
    with patch("src.ingress.workflow_trigger.start_workflow", workflow_mock):
        resp = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(
                issues=[_issue(30)],
                triage_override=True,  # Explicit triage mode
            ),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["created"] == 1
    result = data["results"][0]
    assert result["status"] == "created"
    assert result["workflow_started"] is False  # No workflow in triage mode

    # Verify status in DB
    row = await get_by_repo_and_issue(session, _REPO, 30)
    assert row is not None
    assert row.status == TaskPacketStatus.TRIAGE
    assert row.source_name == "dashboard_import"

    # Workflow must NOT have been called
    workflow_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test: direct mode via triage_override=False
# ---------------------------------------------------------------------------


async def test_import_direct_mode_override(
    http_client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Import with triage_override=False creates RECEIVED TaskPacket and starts workflow,
    even when server triage_mode_enabled=True."""
    monkeypatch.setattr(settings, "triage_mode_enabled", True)  # server default ON

    workflow_mock = AsyncMock(return_value="run-id")
    with patch("src.ingress.workflow_trigger.start_workflow", workflow_mock):
        resp = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(
                issues=[_issue(40)],
                triage_override=False,  # Override: skip triage
            ),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["created"] == 1
    result = data["results"][0]
    assert result["status"] == "created"
    assert result["workflow_started"] is True

    # Verify status in DB
    row = await get_by_repo_and_issue(session, _REPO, 40)
    assert row is not None
    assert row.status == TaskPacketStatus.RECEIVED
    assert row.source_name == "dashboard_import"

    # Workflow WAS called
    workflow_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Test: mixed import — one new + one duplicate
# ---------------------------------------------------------------------------


async def test_import_mixed_new_and_duplicate(
    http_client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch with one new issue and one pre-existing issue: correct split of counts."""
    monkeypatch.setattr(settings, "triage_mode_enabled", False)

    workflow_mock = AsyncMock(return_value="run-id")
    with patch("src.ingress.workflow_trigger.start_workflow", workflow_mock):
        # Pre-create issue #50
        await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(issues=[_issue(50)]),
        )

        # Now import issue #50 (existing) + issue #51 (new)
        resp = await http_client.post(
            "/api/v1/dashboard/github/import",
            json=_import_payload(issues=[_issue(50), _issue(51)]),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["created"] == 1
    assert data["duplicates"] == 1
    assert data["errors"] == 0

    statuses = {r["number"]: r["status"] for r in data["results"]}
    assert statuses[50] == "duplicate"
    assert statuses[51] == "created"
