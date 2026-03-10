"""Unit tests for Settings API endpoints.

Story 12.2: Settings API Endpoints.
Tests CRUD, RBAC enforcement, validation, and audit logging.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.admin.persistence.pg_settings import SettingCategory
from src.admin.rbac import (
    Role,
    get_current_user_id,
    get_current_user_role,
)
from src.admin.router import router
from src.admin.settings_service import SettingValue, SettingsService
from src.db.connection import get_session

app = FastAPI()
app.include_router(router)


def _mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_settings_service():
    svc = MagicMock(spec=SettingsService)
    with patch("src.admin.router.get_settings_service", return_value=svc):
        yield svc


@pytest.fixture
def mock_rbac_admin():
    """Override FastAPI dependencies to always return admin role."""
    app.dependency_overrides[get_current_user_id] = lambda: "admin@test.com"
    app.dependency_overrides[get_current_user_role] = lambda: Role.ADMIN
    app.dependency_overrides[get_session] = _mock_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_rbac_viewer():
    """Override FastAPI dependencies to return viewer role (should be denied)."""
    app.dependency_overrides[get_current_user_id] = lambda: "viewer@test.com"
    app.dependency_overrides[get_current_user_role] = lambda: Role.VIEWER
    app.dependency_overrides[get_session] = _mock_session
    yield
    app.dependency_overrides.clear()


class TestListSettings:
    @pytest.mark.asyncio
    async def test_list_settings_by_category(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.list_by_category = AsyncMock(return_value=[
            SettingValue("agent_model", "claude-sonnet-4-5", "env", SettingCategory.AGENT_CONFIG, False),
        ])

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-User-ID": "admin@test.com"},
        ) as client:
            resp = await client.get("/admin/settings?category=agent_config")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["settings"]) == 1
        assert data["settings"][0]["key"] == "agent_model"

    @pytest.mark.asyncio
    async def test_list_settings_masks_sensitive(self, mock_settings_service, mock_rbac_admin):
        sv = SettingValue("anthropic_api_key", "sk-ant-test-12345", "db", SettingCategory.API_KEYS, True)
        mock_settings_service.list_by_category = AsyncMock(return_value=[sv])

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-User-ID": "admin@test.com"},
        ) as client:
            resp = await client.get("/admin/settings?category=api_keys")

        assert resp.status_code == 200
        value = resp.json()["settings"][0]["value"]
        assert "sk-ant" not in value
        assert value.endswith("2345")


class TestGetSetting:
    @pytest.mark.asyncio
    async def test_get_setting_returns_source(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.get = AsyncMock(return_value=SettingValue(
            "agent_model", "claude-sonnet-4-5", "env", SettingCategory.AGENT_CONFIG, False,
        ))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-User-ID": "admin@test.com"},
        ) as client:
            resp = await client.get("/admin/settings/agent_model")

        assert resp.status_code == 200
        assert resp.json()["source"] == "env"

    @pytest.mark.asyncio
    async def test_get_setting_not_found(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.get = AsyncMock(return_value=None)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-User-ID": "admin@test.com"},
        ) as client:
            resp = await client.get("/admin/settings/nonexistent")

        assert resp.status_code == 404


class TestUpdateSetting:
    @pytest.mark.asyncio
    async def test_update_setting_success(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.get = AsyncMock(return_value=SettingValue(
            "agent_model", "claude-sonnet-4-5", "env", SettingCategory.AGENT_CONFIG, False,
        ))
        mock_settings_service.set = AsyncMock(return_value=SettingValue(
            "agent_model", "claude-opus-4-6", "db", SettingCategory.AGENT_CONFIG, False,
        ))

        with patch("src.admin.router.get_audit_service") as mock_audit:
            mock_audit.return_value.log_event = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-User-ID": "admin@test.com"},
            ) as client:
                resp = await client.put(
                    "/admin/settings/agent_model",
                    json={"value": "claude-opus-4-6"},
                )

        assert resp.status_code == 200
        assert resp.json()["value"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_update_setting_validation_failure(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.get = AsyncMock(return_value=None)
        mock_settings_service.set = AsyncMock(side_effect=ValueError("agent_max_turns must be >= 1"))

        with patch("src.admin.router.get_audit_service"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-User-ID": "admin@test.com"},
            ) as client:
                resp = await client.put(
                    "/admin/settings/agent_max_turns",
                    json={"value": "0"},
                )

        assert resp.status_code == 422


class TestDeleteSetting:
    @pytest.mark.asyncio
    async def test_delete_setting_success(self, mock_settings_service, mock_rbac_admin):
        mock_settings_service.delete = AsyncMock(return_value=True)

        with patch("src.admin.router.get_audit_service") as mock_audit:
            mock_audit.return_value.log_event = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-User-ID": "admin@test.com"},
            ) as client:
                resp = await client.delete("/admin/settings/agent_model")

        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
