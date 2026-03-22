"""GitHub Projects v2 GraphQL client.

Epic 29 AC 1: Provides ProjectsV2Client for finding projects, getting/setting
field values, and adding items. Uses GitHub's GraphQL API with the existing
GitHub App installation token.

GraphQL implementation note (from epic): The mutation pattern is multi-step:
1. Query project ID by owner + number
2. Query field IDs for the project
3. Query option IDs for single-select fields
4. Call updateProjectV2ItemFieldValue with project ID + field ID + value

Cache project/field/option IDs after first resolution to avoid redundant queries.

Architecture reference: docs/epics/epic-29-github-projects-v2-meridian-portfolio-review.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Mutation ID marker for feedback loop detection (Epic 38.19).
# Outbound GraphQL mutations include this as clientMutationId so incoming
# webhooks triggered by our own writes can be detected and skipped.
THESTUDIO_SYNC_MARKER = "thestudio-sync"


class ProjectsV2Error(Exception):
    """Raised when a Projects v2 GraphQL operation fails."""


@dataclass
class FieldOption:
    """A single-select field option (e.g., Status="In Progress")."""

    id: str
    name: str


@dataclass
class ProjectField:
    """A field on a Projects v2 board."""

    id: str
    name: str
    data_type: str  # "SINGLE_SELECT", "TEXT", "NUMBER", etc.
    options: list[FieldOption] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """Cached metadata about a GitHub Project."""

    project_id: str
    project_number: int
    title: str
    fields: dict[str, ProjectField] = field(default_factory=dict)


class ProjectsV2Client:
    """Async GitHub Projects v2 client using GraphQL.

    Uses httpx.AsyncClient for GraphQL calls. Authentication via
    GitHub App installation token (same token as the REST client).

    Caches project/field/option IDs after first resolution per AC 1 note.
    """

    def __init__(self, token: str) -> None:
        self._token = token
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        # Cache: owner/project_number -> ProjectInfo
        self._cache: dict[str, ProjectInfo] = {}

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ProjectsV2Client:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # -- GraphQL helpers -------------------------------------------------------

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query and return the data dict.

        Raises ProjectsV2Error on GraphQL-level errors.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = await self._client.post(GITHUB_GRAPHQL_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()

        if "errors" in result:
            error_msgs = [e.get("message", str(e)) for e in result["errors"]]
            raise ProjectsV2Error(f"GraphQL errors: {error_msgs}")

        return result.get("data", {})

    # -- Project resolution ----------------------------------------------------

    async def find_project(self, owner: str, project_number: int) -> ProjectInfo:
        """Find a project by owner (org or user) and project number.

        Caches the result for subsequent calls. Returns ProjectInfo with
        all field definitions including single-select option IDs.
        """
        cache_key = f"{owner}/{project_number}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        query = """
        query($owner: String!, $number: Int!) {
            user(login: $owner) {
                projectV2(number: $number) {
                    id
                    title
                    number
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2Field {
                                id
                                name
                                dataType
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                dataType
                                options {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"owner": owner, "number": project_number})

        # Try user first, then org
        project_data = None
        user_data = data.get("user")
        if user_data and user_data.get("projectV2"):
            project_data = user_data["projectV2"]

        if project_data is None:
            # Try as organization
            org_query = query.replace("user(login: $owner)", "organization(login: $owner)")
            data = await self._graphql(org_query, {"owner": owner, "number": project_number})
            org_data = data.get("organization")
            if org_data and org_data.get("projectV2"):
                project_data = org_data["projectV2"]

        if project_data is None:
            raise ProjectsV2Error(
                f"Project #{project_number} not found for owner '{owner}'"
            )

        # Parse fields
        fields: dict[str, ProjectField] = {}
        for node in project_data.get("fields", {}).get("nodes", []):
            if not node or "id" not in node:
                continue
            options = [
                FieldOption(id=opt["id"], name=opt["name"])
                for opt in node.get("options", [])
            ]
            pf = ProjectField(
                id=node["id"],
                name=node["name"],
                data_type=node.get("dataType", ""),
                options=options,
            )
            fields[pf.name] = pf

        info = ProjectInfo(
            project_id=project_data["id"],
            project_number=project_data["number"],
            title=project_data["title"],
            fields=fields,
        )
        self._cache[cache_key] = info
        logger.info(
            "projects_v2.project_resolved",
            extra={
                "owner": owner,
                "project_number": project_number,
                "project_id": info.project_id,
                "field_count": len(fields),
            },
        )
        return info

    # -- Item operations -------------------------------------------------------

    async def add_item(self, project_id: str, content_id: str) -> str:
        """Add an issue or PR to a project by its node ID.

        Returns the project item ID.
        """
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
            addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item {
                    id
                }
            }
        }
        """
        data = await self._graphql(mutation, {
            "projectId": project_id,
            "contentId": content_id,
        })
        item_id = data["addProjectV2ItemById"]["item"]["id"]
        logger.info(
            "projects_v2.item_added",
            extra={"project_id": project_id, "content_id": content_id, "item_id": item_id},
        )
        return item_id

    async def set_field_value(
        self,
        project_id: str,
        item_id: str,
        field: ProjectField,
        value: str,
    ) -> None:
        """Set a field value on a project item.

        For single-select fields, resolves the option ID from the value name.
        For text fields, sets the value directly.

        Includes THESTUDIO_SYNC_MARKER as clientMutationId so inbound
        webhook events triggered by this write can be detected and skipped
        (Epic 38.19 feedback loop guard).
        """
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!, $clientMutationId: String) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId,
                itemId: $itemId,
                fieldId: $fieldId,
                value: $value,
                clientMutationId: $clientMutationId
            }) {
                projectV2Item {
                    id
                }
                clientMutationId
            }
        }
        """

        if field.data_type == "SINGLE_SELECT":
            option = next(
                (opt for opt in field.options if opt.name == value),
                None,
            )
            if option is None:
                raise ProjectsV2Error(
                    f"Option '{value}' not found for field '{field.name}'. "
                    f"Available: {[o.name for o in field.options]}"
                )
            field_value = {"singleSelectOptionId": option.id}
        elif field.data_type == "TEXT":
            field_value = {"text": value}
        elif field.data_type == "NUMBER":
            field_value = {"number": float(value)}
        else:
            field_value = {"text": value}

        await self._graphql(mutation, {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field.id,
            "value": field_value,
            "clientMutationId": THESTUDIO_SYNC_MARKER,
        })
        logger.debug(
            "projects_v2.field_updated",
            extra={
                "project_id": project_id,
                "item_id": item_id,
                "field": field.name,
                "value": value,
            },
        )

    # -- Convenience methods ---------------------------------------------------

    async def set_status(
        self,
        owner: str,
        project_number: int,
        item_id: str,
        status: str,
    ) -> None:
        """Set the Status field on a project item.

        Resolves the project and field IDs from cache or API.
        """
        project = await self.find_project(owner, project_number)
        status_field = project.fields.get("Status")
        if status_field is None:
            raise ProjectsV2Error("Status field not found on project")
        await self.set_field_value(project.project_id, item_id, status_field, status)

    async def set_automation_tier(
        self,
        owner: str,
        project_number: int,
        item_id: str,
        tier: str,
    ) -> None:
        """Set the Automation Tier field on a project item."""
        project = await self.find_project(owner, project_number)
        tier_field = project.fields.get("Automation Tier")
        if tier_field is None:
            logger.warning("projects_v2.field_missing: Automation Tier")
            return
        await self.set_field_value(project.project_id, item_id, tier_field, tier)

    async def set_risk_tier(
        self,
        owner: str,
        project_number: int,
        item_id: str,
        risk: str,
    ) -> None:
        """Set the Risk Tier field on a project item."""
        project = await self.find_project(owner, project_number)
        risk_field = project.fields.get("Risk Tier")
        if risk_field is None:
            logger.warning("projects_v2.field_missing: Risk Tier")
            return
        await self.set_field_value(project.project_id, item_id, risk_field, risk)

    async def get_project_items(
        self,
        owner: str,
        project_number: int,
        *,
        first: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all items from a project with their field values.

        Used by the Meridian portfolio collector (Epic 29 Sprint 2).
        Returns a list of item dicts with fieldValues.
        """
        project = await self.find_project(owner, project_number)

        query = """
        query($projectId: ID!, $first: Int!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: $first) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    title
                                    number
                                    state
                                    repository { nameWithOwner }
                                }
                                ... on PullRequest {
                                    title
                                    number
                                    state
                                    repository { nameWithOwner }
                                }
                            }
                            fieldValues(first: 20) {
                                nodes {
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                        field { ... on ProjectV2SingleSelectField { name } }
                                    }
                                    ... on ProjectV2ItemFieldTextValue {
                                        text
                                        field { ... on ProjectV2Field { name } }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {
            "projectId": project.project_id,
            "first": first,
        })

        items_data = data.get("node", {}).get("items", {}).get("nodes", [])
        return items_data

    async def get_configured_fields(
        self,
        owner: str,
        project_number: int,
    ) -> set[str]:
        """Get the set of field names configured on the project.

        Used by compliance checker to verify required fields exist.
        """
        project = await self.find_project(owner, project_number)
        return set(project.fields.keys())

    async def create_custom_field(
        self,
        project_id: str,
        name: str,
        data_type: str,
        single_select_options: list[str] | None = None,
    ) -> ProjectField:
        """Create a custom field on a Projects v2 board.

        Epic 38.14: Net-new GraphQL mutation capability. The client currently
        reads fields but cannot create them. This adds support for auto-creating
        Cost (NUMBER) and Complexity (SINGLE_SELECT) fields on first sync.

        Args:
            project_id: The project node ID.
            name: The field name (e.g., "Cost", "Complexity").
            data_type: "NUMBER" or "SINGLE_SELECT".
            single_select_options: Required for SINGLE_SELECT fields.

        Returns:
            The newly created ProjectField with its ID.
        """
        if data_type == "SINGLE_SELECT":
            options_input = [{"name": opt, "color": "GRAY", "description": ""} for opt in (single_select_options or [])]
            mutation = """
            mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
                createProjectV2Field(input: {
                    projectId: $projectId,
                    dataType: SINGLE_SELECT,
                    name: $name,
                    singleSelectOptions: $options
                }) {
                    projectV2Field {
                        ... on ProjectV2SingleSelectField {
                            id
                            name
                            dataType
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
            """
            data = await self._graphql(mutation, {
                "projectId": project_id,
                "name": name,
                "options": options_input,
            })
        else:
            mutation = """
            mutation($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!) {
                createProjectV2Field(input: {
                    projectId: $projectId,
                    dataType: $dataType,
                    name: $name
                }) {
                    projectV2Field {
                        ... on ProjectV2Field {
                            id
                            name
                            dataType
                        }
                    }
                }
            }
            """
            data = await self._graphql(mutation, {
                "projectId": project_id,
                "name": name,
                "dataType": data_type,
            })

        field_data = data.get("createProjectV2Field", {}).get("projectV2Field", {})
        if not field_data or "id" not in field_data:
            raise ProjectsV2Error(f"Failed to create field '{name}': no field data returned")

        options = [FieldOption(id=opt["id"], name=opt["name"]) for opt in field_data.get("options", [])]
        pf = ProjectField(
            id=field_data["id"],
            name=name,
            data_type=field_data.get("dataType", data_type),
            options=options,
        )
        logger.info(
            "projects_v2.field_created",
            extra={"project_id": project_id, "field_name": name, "data_type": data_type},
        )
        return pf

    async def ensure_cost_and_complexity_fields(
        self,
        owner: str,
        project_number: int,
    ) -> None:
        """Auto-create Cost and Complexity fields if they do not exist.

        Epic 38.14: On first sync, check whether the project has the Cost and
        Complexity fields. If not, create them. Updates the local cache so
        subsequent set_field_value calls see the new fields.
        """
        from src.github.projects_mapping import (
            COMPLEXITY_FIELD_NAME,
            COMPLEXITY_MAPPING,
            COST_FIELD_NAME,
        )

        project = await self.find_project(owner, project_number)
        created_any = False

        if COST_FIELD_NAME not in project.fields:
            cost_field = await self.create_custom_field(
                project.project_id, COST_FIELD_NAME, "NUMBER"
            )
            project.fields[COST_FIELD_NAME] = cost_field
            created_any = True

        if COMPLEXITY_FIELD_NAME not in project.fields:
            options = list(COMPLEXITY_MAPPING.values())
            complexity_field = await self.create_custom_field(
                project.project_id,
                COMPLEXITY_FIELD_NAME,
                "SINGLE_SELECT",
                single_select_options=options,
            )
            project.fields[COMPLEXITY_FIELD_NAME] = complexity_field
            created_any = True

        if created_any:
            logger.info(
                "projects_v2.custom_fields_ensured",
                extra={"owner": owner, "project_number": project_number},
            )

    async def validate_token_scopes(self) -> tuple[bool, str | None]:
        """Validate that the token has the required 'project' scope.

        Epic 38 AC-3 / Risk R1: GitHub Projects v2 API requires a PAT with
        ``project`` scope.  Standard GITHUB_TOKEN (GitHub App installation
        tokens) does not carry OAuth scopes, so this check will surface a
        clear error rather than silently failing mid-sync.

        Returns:
            (valid, error_message) where valid is True if the token has the
            ``project`` scope and error_message describes the problem otherwise.
        """
        try:
            resp = await self._client.get("https://api.github.com/user")
            resp.raise_for_status()
        except Exception as exc:
            return False, f"token_validation_request_failed: {exc}"

        scopes_header = resp.headers.get("X-OAuth-Scopes", "")
        if not scopes_header:
            # GitHub App installation tokens do not return X-OAuth-Scopes.
            # They use fine-grained permissions, not classic OAuth scopes.
            # Projects v2 GraphQL mutations require a PAT with `project` scope —
            # installation tokens cannot access Projects v2 write endpoints.
            return False, (
                "token_missing_project_scope: no X-OAuth-Scopes header returned. "
                "GitHub App installation tokens lack 'project' scope. "
                "Use a PAT with 'project' scope for Projects v2 sync."
            )

        scopes = {s.strip() for s in scopes_header.split(",")}
        if "project" not in scopes:
            return False, (
                f"token_missing_project_scope: token has scopes [{scopes_header}] "
                "but 'project' scope is required for GitHub Projects v2 sync."
            )

        logger.info(
            "projects_v2.token_scopes_valid",
            extra={"scopes": scopes_header},
        )
        return True, None
