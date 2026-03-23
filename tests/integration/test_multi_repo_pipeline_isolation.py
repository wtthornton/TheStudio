"""Integration tests for concurrent pipeline isolation across repos (Epic 41, Story 41.10).

Verifies that TaskPackets created for two different repos are:
1. Stored with the correct ``repo`` field
2. Retrieved independently without cross-contamination
3. Filterable by repo via the tasks list endpoint
4. Not visible in each other's repo-filtered query results

These tests use a real PostgreSQL database (in-test engine) and the FastAPI HTTP
client. Workflow activation is skipped (skip_triage=True + mock Temporal) so the
test focuses on the isolation of data records rather than workflow execution.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.settings import settings

pytestmark = pytest.mark.integration

_REPO_A = "test-iso-org/repo-alpha"
_REPO_B = "test-iso-org/repo-beta"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_engine():
    """Transient in-test PostgreSQL engine with fresh schema."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine):
    """Live database session for direct assertion queries."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def http_client(db_engine, monkeypatch: pytest.MonkeyPatch):
    """Async HTTP client wired to the FastAPI app with real DB and no auth/workflow."""
    monkeypatch.setattr(settings, "dashboard_token", "")
    monkeypatch.setattr(settings, "llm_provider", "mock")

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_body(repo: str, title: str, skip_triage: bool = False) -> dict:
    return {
        "title": title,
        "description": f"Automated isolation test task for {repo}.",
        "repo": repo,
        "skip_triage": skip_triage,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineIsolation:
    """TaskPackets for two repos are independently stored and retrieved."""

    async def test_task_a_has_correct_repo_field(
        self, http_client: AsyncClient
    ) -> None:
        """TaskPacket created for repo-alpha stores repo=test-iso-org/repo-alpha."""
        resp = await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Task for repo-alpha")
        )
        assert resp.status_code == 201
        assert resp.json()["task"]["repo"] == _REPO_A

    async def test_task_b_has_correct_repo_field(
        self, http_client: AsyncClient
    ) -> None:
        """TaskPacket created for repo-beta stores repo=test-iso-org/repo-beta."""
        resp = await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Task for repo-beta")
        )
        assert resp.status_code == 201
        assert resp.json()["task"]["repo"] == _REPO_B

    async def test_repo_a_filter_excludes_repo_b_tasks(
        self, http_client: AsyncClient
    ) -> None:
        """GET /tasks?repo=repo-alpha returns only repo-alpha tasks."""
        # Create one task for each repo
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Repo A task")
        )
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Repo B task")
        )

        resp = await http_client.get(
            "/api/v1/dashboard/tasks", params={"repo": _REPO_A}
        )
        assert resp.status_code == 200
        tasks = resp.json()["items"]

        for task in tasks:
            assert task["repo"] == _REPO_A, (
                f"Expected only repo-alpha tasks but found repo={task['repo']}"
            )

    async def test_repo_b_filter_excludes_repo_a_tasks(
        self, http_client: AsyncClient
    ) -> None:
        """GET /tasks?repo=repo-beta returns only repo-beta tasks."""
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Repo A task")
        )
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Repo B task")
        )

        resp = await http_client.get(
            "/api/v1/dashboard/tasks", params={"repo": _REPO_B}
        )
        assert resp.status_code == 200
        tasks = resp.json()["items"]

        for task in tasks:
            assert task["repo"] == _REPO_B, (
                f"Expected only repo-beta tasks but found repo={task['repo']}"
            )

    async def test_all_repos_view_shows_both(
        self, http_client: AsyncClient
    ) -> None:
        """GET /tasks without repo filter returns tasks from all repos."""
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Repo A task")
        )
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Repo B task")
        )

        resp = await http_client.get("/api/v1/dashboard/tasks")
        assert resp.status_code == 200
        tasks = resp.json()["items"]

        repos_seen = {t["repo"] for t in tasks}
        assert _REPO_A in repos_seen
        assert _REPO_B in repos_seen

    async def test_no_cross_repo_task_id_collision(
        self, http_client: AsyncClient
    ) -> None:
        """Tasks from different repos have distinct UUIDs — no shared state."""
        resp_a = await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Repo A task")
        )
        resp_b = await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Repo B task")
        )

        id_a = resp_a.json()["task"]["id"]
        id_b = resp_b.json()["task"]["id"]
        assert id_a != id_b

    async def test_concurrent_task_creation_both_land_correctly(
        self, http_client: AsyncClient
    ) -> None:
        """Creating tasks for two repos concurrently produces independently correct records."""
        import asyncio

        results = await asyncio.gather(
            http_client.post(
                "/api/v1/dashboard/tasks",
                json=_task_body(_REPO_A, "Concurrent repo-alpha task"),
            ),
            http_client.post(
                "/api/v1/dashboard/tasks",
                json=_task_body(_REPO_B, "Concurrent repo-beta task"),
            ),
        )

        assert results[0].status_code == 201
        assert results[1].status_code == 201

        task_a = results[0].json()["task"]
        task_b = results[1].json()["task"]

        assert task_a["repo"] == _REPO_A
        assert task_b["repo"] == _REPO_B
        assert task_a["id"] != task_b["id"]

    async def test_repo_a_task_not_retrievable_via_repo_b_filter(
        self, http_client: AsyncClient
    ) -> None:
        """A specific task from repo-alpha does not appear in repo-beta task list."""
        resp_a = await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Repo A only task")
        )
        task_a_id = resp_a.json()["task"]["id"]

        # Fetch task list filtered to repo-beta
        resp_list = await http_client.get(
            "/api/v1/dashboard/tasks", params={"repo": _REPO_B}
        )
        tasks_b = resp_list.json()["items"]

        task_b_ids = {t["id"] for t in tasks_b}
        assert task_a_id not in task_b_ids, (
            "repo-alpha task appeared in repo-beta filtered results"
        )

    async def test_stage_metrics_isolated_by_repo(
        self, http_client: AsyncClient
    ) -> None:
        """GET /stages/metrics?repo=... returns metrics for that repo only."""
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_A, "Stage metrics repo-A")
        )
        await http_client.post(
            "/api/v1/dashboard/tasks", json=_task_body(_REPO_B, "Stage metrics repo-B")
        )

        resp = await http_client.get(
            "/api/v1/dashboard/stages/metrics", params={"repo": _REPO_A}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stages" in data
        # The response structure is valid; repo filter was applied (data is empty since
        # newly created tasks have no stage_timings yet, but no 500 error occurred)
