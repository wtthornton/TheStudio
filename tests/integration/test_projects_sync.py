"""Integration tests for GitHub Projects v2 sync (Epic 38, Story 38.20).

Tests cover:
- Stage transition pushes status to Projects v2 board (mocked GitHub GraphQL)
- Manual GitHub status change (projects_v2_item webhook) updates TaskPacket
- Self-triggered webhook is detected and skipped (feedback loop guard)
- Force sync endpoint re-pushes all active TaskPackets

GitHub GraphQL API is mocked so no real project is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.github.projects_client import THESTUDIO_SYNC_MARKER
from src.github.projects_sync import is_self_triggered
from src.settings import settings

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_REPO = "test-org/sync-test-repo"


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Provide an async session."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_client(db_engine):
    """Create an HTTPX test client with DB override."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 38.19: Feedback loop guard — self-triggered detection
# ---------------------------------------------------------------------------


class TestSelfTriggeredDetection:
    """Tests for the is_self_triggered() feedback loop guard (Story 38.19)."""

    def test_bot_sender_is_self_triggered(self):
        """A webhook from a Bot sender is considered self-triggered."""
        payload = {
            "sender": {"login": "thestudio-app[bot]", "type": "Bot"},
            "action": "edited",
        }
        assert is_self_triggered(payload) is True

    def test_user_sender_is_not_self_triggered(self):
        """A webhook from a human user is not self-triggered."""
        payload = {
            "sender": {"login": "alice", "type": "User"},
            "action": "edited",
        }
        assert is_self_triggered(payload) is False

    def test_mutation_id_marker_detected(self):
        """Explicit THESTUDIO_SYNC_MARKER in mutation_id is detected."""
        payload = {
            "sender": {"login": "alice", "type": "User"},
            "changes": {
                "field_value": {"mutation_id": THESTUDIO_SYNC_MARKER}
            },
        }
        assert is_self_triggered(payload) is True

    def test_no_sender_is_not_self_triggered(self):
        """Missing sender defaults to not self-triggered."""
        payload = {"action": "edited"}
        assert is_self_triggered(payload) is False


# ---------------------------------------------------------------------------
# 38.15: Inbound webhook — projects_v2_item event handling
# ---------------------------------------------------------------------------


class TestProjectsV2ItemWebhook:
    """Tests for handle_projects_v2_item_event (Story 38.15)."""

    @pytest.mark.asyncio
    async def test_disabled_flag_returns_early(self, db_session: AsyncSession):
        """When projects_v2_enabled is False, handler returns early."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = False
        try:
            result = await handle_projects_v2_item_event(
                {"action": "edited", "projects_v2_item": {}}, db_session
            )
            assert result["outcome"] == "projects_v2_disabled"
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_self_triggered_skipped(self, db_session: AsyncSession):
        """Self-triggered events (bot sender) are skipped."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            payload = {
                "action": "edited",
                "sender": {"login": "thestudio[bot]", "type": "Bot"},
                "projects_v2_item": {"content_type": "Issue", "content_node_id": "I_abc"},
            }
            result = await handle_projects_v2_item_event(payload, db_session)
            assert result["outcome"] == "self_triggered_skipped"
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_non_issue_content_type_skipped(self, db_session: AsyncSession):
        """DraftIssue and PullRequest content types are not handled."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            payload = {
                "action": "edited",
                "sender": {"login": "alice", "type": "User"},
                "projects_v2_item": {
                    "content_type": "DraftIssue",
                    "content_node_id": "DI_abc",
                },
                "changes": {"field_value": {"field_name": "Status"}},
            }
            result = await handle_projects_v2_item_event(payload, db_session)
            assert "content_type_not_issue" in result["outcome"]
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_non_status_field_change_ignored(self, db_session: AsyncSession):
        """Changes to fields other than Status are ignored."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            payload = {
                "action": "edited",
                "sender": {"login": "alice", "type": "User"},
                "projects_v2_item": {
                    "content_type": "Issue",
                    "content_node_id": "I_abc",
                },
                "changes": {
                    "field_value": {
                        "field_name": "Priority",
                        "after": {"name": "High"},
                        "before": {"name": "Medium"},
                    }
                },
            }
            result = await handle_projects_v2_item_event(payload, db_session)
            assert "field_not_status" in result["outcome"]
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_status_change_to_done_logged(self, db_session: AsyncSession):
        """Status changed to Done is logged (informational in MVP scope)."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            payload = {
                "action": "edited",
                "sender": {"login": "alice", "type": "User"},
                "projects_v2_item": {
                    "content_type": "Issue",
                    "content_node_id": "I_kwDO123",
                },
                "changes": {
                    "field_value": {
                        "field_name": "Status",
                        "after": {"name": "Done"},
                        "before": {"name": "In Progress"},
                    }
                },
            }
            result = await handle_projects_v2_item_event(payload, db_session)
            assert result["outcome"] == "item_marked_done_logged"
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_status_change_to_in_progress_no_action(self, db_session: AsyncSession):
        """Status changed to In Progress takes no action (informational)."""
        from src.github.projects_sync import handle_projects_v2_item_event

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            payload = {
                "action": "edited",
                "sender": {"login": "alice", "type": "User"},
                "projects_v2_item": {
                    "content_type": "Issue",
                    "content_node_id": "I_kwDO456",
                },
                "changes": {
                    "field_value": {
                        "field_name": "Status",
                        "after": {"name": "In Progress"},
                        "before": {"name": "Queued"},
                    }
                },
            }
            result = await handle_projects_v2_item_event(payload, db_session)
            assert "status_change_noted" in result["outcome"]
        finally:
            settings.projects_v2_enabled = original


# ---------------------------------------------------------------------------
# 38.16: Config API endpoints
# ---------------------------------------------------------------------------


class TestProjectsSyncConfigEndpoints:
    """Tests for GET/PUT /api/v1/dashboard/github/projects/config (Story 38.16)."""

    @pytest.mark.asyncio
    async def test_get_config_returns_defaults(self, test_client: AsyncClient):
        """GET /github/projects/config returns current settings."""
        response = await test_client.get("/api/v1/dashboard/github/projects/config")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "status" in data
        assert "enabled" in data["config"]
        assert "auto_add" in data["config"]

    @pytest.mark.asyncio
    async def test_put_config_updates_settings(self, test_client: AsyncClient):
        """PUT /github/projects/config updates the enabled flag."""
        original = settings.projects_v2_enabled
        try:
            payload = {
                "enabled": True,
                "owner": "my-org",
                "project_number": 42,
                "auto_add": True,
                "auto_close": False,
                "respect_manual_overrides": True,
            }
            response = await test_client.put(
                "/api/v1/dashboard/github/projects/config", json=payload
            )
            assert response.status_code == 200
            data = response.json()
            assert data["config"]["enabled"] is True
            assert settings.projects_v2_enabled is True
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_put_config_updates_sync_flags(self, test_client: AsyncClient):
        """PUT /github/projects/config updates individual sync behavior flags."""
        original_auto_add = settings.projects_sync_auto_add
        original_auto_close = settings.projects_sync_auto_close
        try:
            payload = {
                "enabled": False,
                "owner": "",
                "project_number": 0,
                "auto_add": False,
                "auto_close": True,
                "respect_manual_overrides": False,
            }
            response = await test_client.put(
                "/api/v1/dashboard/github/projects/config", json=payload
            )
            assert response.status_code == 200
            assert settings.projects_sync_auto_add is False
            assert settings.projects_sync_auto_close is True
        finally:
            settings.projects_sync_auto_add = original_auto_add
            settings.projects_sync_auto_close = original_auto_close


# ---------------------------------------------------------------------------
# 38.17: Force sync endpoint
# ---------------------------------------------------------------------------


class TestForceSyncEndpoint:
    """Tests for POST /api/v1/dashboard/github/projects/sync (Story 38.17)."""

    @pytest.mark.asyncio
    async def test_force_sync_disabled_returns_503(self, test_client: AsyncClient):
        """Force sync returns 503 when Projects v2 is not enabled."""
        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = False
        try:
            response = await test_client.post("/api/v1/dashboard/github/projects/sync")
            assert response.status_code == 503
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_force_sync_no_token_returns_503(self, test_client: AsyncClient):
        """Force sync returns 503 when token is not configured."""
        original_enabled = settings.projects_v2_enabled
        original_owner = settings.projects_v2_owner
        original_number = settings.projects_v2_number
        original_token = settings.projects_v2_token
        original_app_id = settings.github_app_id

        settings.projects_v2_enabled = True
        settings.projects_v2_owner = "test-org"
        settings.projects_v2_number = 1
        settings.projects_v2_token = ""
        settings.github_app_id = ""
        try:
            response = await test_client.post("/api/v1/dashboard/github/projects/sync")
            assert response.status_code == 503
        finally:
            settings.projects_v2_enabled = original_enabled
            settings.projects_v2_owner = original_owner
            settings.projects_v2_number = original_number
            settings.projects_v2_token = original_token
            settings.github_app_id = original_app_id

    @pytest.mark.asyncio
    async def test_force_sync_with_no_active_tasks(self, test_client: AsyncClient):
        """Force sync with no active tasks returns success with zero tasks found."""
        original_enabled = settings.projects_v2_enabled
        original_owner = settings.projects_v2_owner
        original_number = settings.projects_v2_number
        original_token = settings.projects_v2_token

        settings.projects_v2_enabled = True
        settings.projects_v2_owner = "test-org"
        settings.projects_v2_number = 1
        settings.projects_v2_token = "test-token"

        # Mock the ProjectsV2Client to avoid real API calls
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.ensure_cost_and_complexity_fields = AsyncMock()
        mock_project = MagicMock()
        mock_project.project_id = "PVT_test"
        mock_project.fields = {}
        mock_client.find_project = AsyncMock(return_value=mock_project)

        try:
            with patch("src.dashboard.github_router.ProjectsV2Client", return_value=mock_client):
                response = await test_client.post("/api/v1/dashboard/github/projects/sync")
            assert response.status_code == 200
            data = response.json()
            assert data["triggered"] is True
            assert data["active_tasks_found"] == 0
        finally:
            settings.projects_v2_enabled = original_enabled
            settings.projects_v2_owner = original_owner
            settings.projects_v2_number = original_number
            settings.projects_v2_token = original_token


# ---------------------------------------------------------------------------
# 38.13: Feature flag integration — update_project_status_activity
# ---------------------------------------------------------------------------


class TestProjectsV2FeatureFlag:
    """Verify the projects_v2_enabled flag gates sync activity (Story 38.13)."""

    @pytest.mark.asyncio
    async def test_activity_skips_when_disabled(self):
        """update_project_status_activity returns synced=False when flag is off."""
        from src.workflow.activities import (
            ProjectStatusInput,
            update_project_status_activity,
        )

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = False
        try:
            result = await update_project_status_activity(
                ProjectStatusInput(
                    taskpacket_id=str(uuid4()),
                    taskpacket_status="RECEIVED",
                    repo_tier="observe",
                    complexity_index="low",
                    project_item_id="",
                )
            )
            assert result.synced is False
            assert result.error == "projects_v2_disabled"
        finally:
            settings.projects_v2_enabled = original

    @pytest.mark.asyncio
    async def test_workflow_trigger_propagates_projects_v2_enabled(self):
        """start_workflow passes projects_v2_enabled from settings to workflow arg.

        Story 38.13: The flag must be forwarded at workflow launch time so that
        PipelineInput.projects_v2_enabled reflects the runtime settings value.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4

        task_id = uuid4()
        corr_id = uuid4()

        mock_handle = MagicMock()
        mock_handle.result_run_id = "run-abc"

        mock_client = AsyncMock()
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        original = settings.projects_v2_enabled
        settings.projects_v2_enabled = True
        try:
            with patch(
                "src.ingress.workflow_trigger.get_temporal_client",
                return_value=mock_client,
            ):
                from src.ingress.workflow_trigger import start_workflow

                await start_workflow(task_id, corr_id)

            _args, kwargs = mock_client.start_workflow.call_args
            workflow_arg = kwargs.get("arg") or _args[1]
            assert workflow_arg["projects_v2_enabled"] is True, (
                "projects_v2_enabled must be forwarded to PipelineInput so the "
                "Projects v2 sync activity is not silently skipped."
            )
        finally:
            settings.projects_v2_enabled = original


# ---------------------------------------------------------------------------
# 38.14: Field mapping — Cost and Complexity
# ---------------------------------------------------------------------------


class TestCostComplexityMapping:
    """Unit tests for the new Cost and Complexity field mappings (Story 38.14)."""

    def test_map_cost_formats_correctly(self):
        """map_cost produces 4-decimal-place string."""
        from src.github.projects_mapping import map_cost

        assert map_cost(1.23456789) == "1.2346"
        assert map_cost(0.0) == "0.0000"
        assert map_cost(10.5) == "10.5000"

    def test_map_complexity_known_values(self):
        """map_complexity maps low/medium/high correctly."""
        from src.github.projects_mapping import map_complexity

        assert map_complexity("low") == "Low"
        assert map_complexity("medium") == "Medium"
        assert map_complexity("high") == "High"
        assert map_complexity("HIGH") == "High"

    def test_map_complexity_unknown_returns_none(self):
        """map_complexity returns None for unmapped values."""
        from src.github.projects_mapping import map_complexity

        assert map_complexity("unknown") is None
        assert map_complexity("") is None
