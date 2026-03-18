"""Tests for GitHub Projects v2 GraphQL client (Epic 29 AC 1)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from src.github.projects_client import (
    FieldOption,
    ProjectField,
    ProjectInfo,
    ProjectsV2Client,
    ProjectsV2Error,
)

# -- Fixtures ----------------------------------------------------------------


def _mock_graphql_response(data: dict, errors: list | None = None) -> httpx.Response:
    """Build a mock httpx.Response for GraphQL."""
    body: dict = {"data": data}
    if errors:
        body["errors"] = errors
    return httpx.Response(200, json=body, request=httpx.Request("POST", "https://api.github.com/graphql"))


def _sample_project_data() -> dict:
    """Sample GraphQL response for a project query."""
    return {
        "user": {
            "projectV2": {
                "id": "PVT_123",
                "title": "TheStudio Board",
                "number": 1,
                "fields": {
                    "nodes": [
                        {
                            "id": "FIELD_STATUS",
                            "name": "Status",
                            "dataType": "SINGLE_SELECT",
                            "options": [
                                {"id": "OPT_QUEUED", "name": "Queued"},
                                {"id": "OPT_IN_PROGRESS", "name": "In Progress"},
                                {"id": "OPT_IN_REVIEW", "name": "In Review"},
                                {"id": "OPT_BLOCKED", "name": "Blocked"},
                                {"id": "OPT_DONE", "name": "Done"},
                            ],
                        },
                        {
                            "id": "FIELD_TIER",
                            "name": "Automation Tier",
                            "dataType": "SINGLE_SELECT",
                            "options": [
                                {"id": "OPT_OBSERVE", "name": "Observe"},
                                {"id": "OPT_SUGGEST", "name": "Suggest"},
                                {"id": "OPT_EXECUTE", "name": "Execute"},
                            ],
                        },
                        {
                            "id": "FIELD_RISK",
                            "name": "Risk Tier",
                            "dataType": "SINGLE_SELECT",
                            "options": [
                                {"id": "OPT_LOW", "name": "Low"},
                                {"id": "OPT_MEDIUM", "name": "Medium"},
                                {"id": "OPT_HIGH", "name": "High"},
                            ],
                        },
                        {
                            "id": "FIELD_PRIORITY",
                            "name": "Priority",
                            "dataType": "TEXT",
                        },
                        {
                            "id": "FIELD_OWNER",
                            "name": "Owner",
                            "dataType": "TEXT",
                        },
                        {
                            "id": "FIELD_REPO",
                            "name": "Repo",
                            "dataType": "TEXT",
                        },
                    ]
                },
            }
        }
    }


# -- Tests -------------------------------------------------------------------


class TestProjectsV2ClientInit:
    """Client initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        async with ProjectsV2Client("test-token") as client:
            assert client._token == "test-token"

    def test_empty_cache_on_init(self) -> None:
        client = ProjectsV2Client("test-token")
        assert len(client._cache) == 0


class TestFindProject:
    """AC 1: Find project by owner and number."""

    @pytest.mark.asyncio
    async def test_find_project_user(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value=_sample_project_data())

        project = await client.find_project("myorg", 1)

        assert project.project_id == "PVT_123"
        assert project.title == "TheStudio Board"
        assert project.project_number == 1
        assert "Status" in project.fields
        assert "Automation Tier" in project.fields
        assert "Risk Tier" in project.fields
        assert len(project.fields) == 6

    @pytest.mark.asyncio
    async def test_find_project_caches_result(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value=_sample_project_data())

        await client.find_project("myorg", 1)
        await client.find_project("myorg", 1)

        # Should only call GraphQL once (cached)
        assert client._graphql.call_count == 1

    @pytest.mark.asyncio
    async def test_find_project_falls_back_to_org(self) -> None:
        """When user query returns null, tries organization query."""
        client = ProjectsV2Client("test-token")

        # First call (user) returns null, second call (org) returns data
        org_data = _sample_project_data()
        org_data["organization"] = org_data.pop("user")

        client._graphql = AsyncMock(
            side_effect=[
                {"user": None},  # user query fails
                org_data,  # org query succeeds
            ]
        )

        project = await client.find_project("myorg", 1)
        assert project.project_id == "PVT_123"

    @pytest.mark.asyncio
    async def test_find_project_not_found_raises(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(
            side_effect=[
                {"user": None},
                {"organization": None},
            ]
        )

        with pytest.raises(ProjectsV2Error, match="not found"):
            await client.find_project("myorg", 999)

    @pytest.mark.asyncio
    async def test_field_options_parsed(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value=_sample_project_data())

        project = await client.find_project("myorg", 1)
        status_field = project.fields["Status"]

        assert status_field.data_type == "SINGLE_SELECT"
        assert len(status_field.options) == 5
        option_names = {o.name for o in status_field.options}
        assert "Queued" in option_names
        assert "Done" in option_names


class TestAddItem:
    """AC 1: Add items to project."""

    @pytest.mark.asyncio
    async def test_add_item_returns_item_id(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value={
            "addProjectV2ItemById": {"item": {"id": "PVTI_456"}}
        })

        item_id = await client.add_item("PVT_123", "I_789")
        assert item_id == "PVTI_456"


class TestSetFieldValue:
    """AC 1: Set field values on project items."""

    @pytest.mark.asyncio
    async def test_set_single_select_field(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value={
            "updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_456"}}
        })

        field = ProjectField(
            id="FIELD_STATUS",
            name="Status",
            data_type="SINGLE_SELECT",
            options=[
                FieldOption(id="OPT_DONE", name="Done"),
                FieldOption(id="OPT_QUEUED", name="Queued"),
            ],
        )

        await client.set_field_value("PVT_123", "PVTI_456", field, "Done")

        # Verify the mutation was called with the option ID
        call_args = client._graphql.call_args
        variables = call_args[1]["variables"] if "variables" in call_args[1] else call_args[0][1]
        assert variables["value"] == {"singleSelectOptionId": "OPT_DONE"}

    @pytest.mark.asyncio
    async def test_set_text_field(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value={
            "updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_456"}}
        })

        field = ProjectField(id="FIELD_OWNER", name="Owner", data_type="TEXT")

        await client.set_field_value("PVT_123", "PVTI_456", field, "thestudio-bot")

        call_args = client._graphql.call_args
        variables = call_args[1]["variables"] if "variables" in call_args[1] else call_args[0][1]
        assert variables["value"] == {"text": "thestudio-bot"}

    @pytest.mark.asyncio
    async def test_set_unknown_option_raises(self) -> None:
        client = ProjectsV2Client("test-token")

        field = ProjectField(
            id="FIELD_STATUS",
            name="Status",
            data_type="SINGLE_SELECT",
            options=[FieldOption(id="OPT_DONE", name="Done")],
        )

        with pytest.raises(ProjectsV2Error, match="Option 'NonExistent' not found"):
            await client.set_field_value("PVT_123", "PVTI_456", field, "NonExistent")


class TestSetStatus:
    """Convenience method for status updates."""

    @pytest.mark.asyncio
    async def test_set_status_resolves_project(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value=_sample_project_data())
        client.set_field_value = AsyncMock()

        await client.set_status("myorg", 1, "PVTI_456", "Done")

        client.set_field_value.assert_called_once()
        args = client.set_field_value.call_args
        assert args[0][2].name == "Status"
        assert args[0][3] == "Done"

    @pytest.mark.asyncio
    async def test_set_status_missing_field_raises(self) -> None:
        client = ProjectsV2Client("test-token")
        # Cache a project with no Status field
        client._cache["myorg/1"] = ProjectInfo(
            project_id="PVT_123", project_number=1, title="Test", fields={}
        )

        with pytest.raises(ProjectsV2Error, match="Status field not found"):
            await client.set_status("myorg", 1, "PVTI_456", "Done")


class TestGraphQLErrors:
    """Error handling for GraphQL responses."""

    @pytest.mark.asyncio
    async def test_graphql_errors_raise(self) -> None:
        client = ProjectsV2Client("test-token")

        mock_resp = httpx.Response(
            200,
            json={"errors": [{"message": "Field not found"}]},
            request=httpx.Request("POST", "https://api.github.com/graphql"),
        )
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(ProjectsV2Error, match="Field not found"):
            await client._graphql("query { viewer { login } }")


class TestGetConfiguredFields:
    """Used by compliance checker (AC 8)."""

    @pytest.mark.asyncio
    async def test_returns_field_names(self) -> None:
        client = ProjectsV2Client("test-token")
        client._graphql = AsyncMock(return_value=_sample_project_data())

        fields = await client.get_configured_fields("myorg", 1)

        assert "Status" in fields
        assert "Automation Tier" in fields
        assert "Risk Tier" in fields
        assert "Priority" in fields
        assert "Owner" in fields
        assert "Repo" in fields
