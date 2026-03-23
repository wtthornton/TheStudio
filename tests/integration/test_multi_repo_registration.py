"""Integration tests for multi-repo registration (Epic 41, Story 41.2).

Tests the full repo registration flow against a real PostgreSQL database:
- Register two repos independently, verify independent retrieval
- Duplicate registration returns 409
- Each repo has correct owner/repo_name separation
- New repos start at OBSERVE tier
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.repo.repository import RepoRepository
from src.settings import settings

pytestmark = pytest.mark.integration

_REPO_A = {"owner": "test-org-a", "repo": "repo-alpha", "installation_id": 111, "default_branch": "main"}
_REPO_B = {"owner": "test-org-b", "repo": "repo-beta", "installation_id": 222, "default_branch": "main"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    """Async HTTP client wired to the FastAPI app with real DB and no auth."""
    monkeypatch.setattr(settings, "dashboard_token", "")
    monkeypatch.setattr(settings, "llm_provider", "mock")

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session

    # Provide a default webhook_secret so register_repo does not crash
    monkeypatch.setattr(settings, "webhook_secret", "test-secret-for-registration")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMultiRepoRegistration:
    """Register two repos and verify independent retrieval."""

    async def test_register_repo_a(self, http_client: AsyncClient) -> None:
        """Registering the first repo returns 201 with correct fields."""
        response = await http_client.post("/admin/repos", json=_REPO_A)
        assert response.status_code == 201
        data = response.json()
        assert data["owner"] == _REPO_A["owner"]
        assert data["repo"] == _REPO_A["repo"]
        assert data["tier"] == "OBSERVE"
        assert data["installation_id"] == _REPO_A["installation_id"]
        assert "id" in data

    async def test_register_repo_b(self, http_client: AsyncClient) -> None:
        """Registering the second repo returns 201 with correct fields."""
        response = await http_client.post("/admin/repos", json=_REPO_B)
        assert response.status_code == 201
        data = response.json()
        assert data["owner"] == _REPO_B["owner"]
        assert data["repo"] == _REPO_B["repo"]
        assert data["tier"] == "OBSERVE"

    async def test_both_repos_listed_independently(self, http_client: AsyncClient) -> None:
        """After registering two repos, GET /admin/repos returns both independently."""
        # Register both
        await http_client.post("/admin/repos", json=_REPO_A)
        await http_client.post("/admin/repos", json=_REPO_B)

        response = await http_client.get("/admin/repos")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        full_names = {f"{r['owner']}/{r['repo']}" for r in data["repos"]}
        assert f"{_REPO_A['owner']}/{_REPO_A['repo']}" in full_names
        assert f"{_REPO_B['owner']}/{_REPO_B['repo']}" in full_names

    async def test_repos_have_independent_ids(self, http_client: AsyncClient) -> None:
        """Two repos have distinct UUIDs — no shared state in the DB row."""
        resp_a = await http_client.post("/admin/repos", json=_REPO_A)
        resp_b = await http_client.post("/admin/repos", json=_REPO_B)
        assert resp_a.json()["id"] != resp_b.json()["id"]

    async def test_duplicate_registration_returns_409(self, http_client: AsyncClient) -> None:
        """Registering the same repo twice returns 409 Conflict."""
        await http_client.post("/admin/repos", json=_REPO_A)
        response = await http_client.post("/admin/repos", json=_REPO_A)
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    async def test_repo_detail_endpoint_returns_correct_repo(
        self, http_client: AsyncClient
    ) -> None:
        """GET /admin/repos/{id} returns exactly the registered repo, not a sibling."""
        # Register both to confirm no cross-contamination
        resp_a = await http_client.post("/admin/repos", json=_REPO_A)
        await http_client.post("/admin/repos", json=_REPO_B)

        repo_a_id = resp_a.json()["id"]
        detail_resp = await http_client.get(f"/admin/repos/{repo_a_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["owner"] == _REPO_A["owner"]
        assert detail["repo_name"] == _REPO_A["repo"]

    async def test_new_repos_start_at_observe_tier(self, http_client: AsyncClient) -> None:
        """Both repos start at OBSERVE tier (safety invariant)."""
        resp_a = await http_client.post("/admin/repos", json=_REPO_A)
        resp_b = await http_client.post("/admin/repos", json=_REPO_B)
        assert resp_a.json()["tier"] == "OBSERVE"
        assert resp_b.json()["tier"] == "OBSERVE"

    async def test_repo_repository_list_all(
        self, http_client: AsyncClient, session: AsyncSession
    ) -> None:
        """RepoRepository.list_all() returns both registered repos from the DB layer."""
        await http_client.post("/admin/repos", json=_REPO_A)
        await http_client.post("/admin/repos", json=_REPO_B)

        repo_repo = RepoRepository()
        repos = await repo_repo.list_all(session)
        assert len(repos) == 2
        full_names = {r.full_name for r in repos}
        assert f"{_REPO_A['owner']}/{_REPO_A['repo']}" in full_names
        assert f"{_REPO_B['owner']}/{_REPO_B['repo']}" in full_names
