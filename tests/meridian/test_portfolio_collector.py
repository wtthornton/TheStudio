"""Tests for the Meridian portfolio data collector (Story 29.5).

Validates PortfolioSnapshot construction, field extraction, and grouping.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.meridian.portfolio_collector import (
    PortfolioItem,
    PortfolioSnapshot,
    _extract_field_value,
    _parse_item,
    collect_portfolio,
)

# --- Test data fixtures ---


def _make_raw_item(
    item_id: str = "PVTI_1",
    title: str = "Fix login bug",
    number: int = 42,
    repo: str = "org/repo-a",
    state: str = "OPEN",
    status: str = "In Progress",
    risk_tier: str = "Medium",
    automation_tier: str = "Suggest",
) -> dict:
    """Create a raw GraphQL project item dict."""
    return {
        "id": item_id,
        "content": {
            "title": title,
            "number": number,
            "state": state,
            "repository": {"nameWithOwner": repo},
        },
        "fieldValues": {
            "nodes": [
                {
                    "name": status,
                    "field": {"name": "Status"},
                },
                {
                    "name": risk_tier,
                    "field": {"name": "Risk Tier"},
                },
                {
                    "name": automation_tier,
                    "field": {"name": "Automation Tier"},
                },
            ]
        },
    }


# --- _extract_field_value ---


class TestExtractFieldValue:
    def test_extracts_single_select(self):
        nodes = [{"name": "In Progress", "field": {"name": "Status"}}]
        assert _extract_field_value(nodes, "Status") == "In Progress"

    def test_extracts_text_field(self):
        nodes = [{"text": "some-owner", "field": {"name": "Owner"}}]
        assert _extract_field_value(nodes, "Owner") == "some-owner"

    def test_returns_empty_for_missing_field(self):
        nodes = [{"name": "In Progress", "field": {"name": "Status"}}]
        assert _extract_field_value(nodes, "Risk Tier") == ""

    def test_handles_empty_nodes(self):
        assert _extract_field_value([], "Status") == ""

    def test_handles_none_nodes(self):
        nodes = [None, {"name": "Done", "field": {"name": "Status"}}]
        assert _extract_field_value(nodes, "Status") == "Done"


# --- _parse_item ---


class TestParseItem:
    def test_parses_valid_item(self):
        raw = _make_raw_item()
        item = _parse_item(raw)
        assert item is not None
        assert item.item_id == "PVTI_1"
        assert item.title == "Fix login bug"
        assert item.number == 42
        assert item.repo == "org/repo-a"
        assert item.status == "In Progress"
        assert item.risk_tier == "Medium"
        assert item.automation_tier == "Suggest"
        assert item.state == "OPEN"

    def test_returns_none_for_empty(self):
        assert _parse_item({}) is None
        assert _parse_item(None) is None

    def test_handles_missing_content(self):
        raw = {"id": "PVTI_1", "fieldValues": {"nodes": []}}
        item = _parse_item(raw)
        assert item is not None
        assert item.title == ""
        assert item.repo == ""

    def test_handles_missing_repository(self):
        raw = {
            "id": "PVTI_1",
            "content": {"title": "Test", "number": 1, "state": "OPEN"},
            "fieldValues": {"nodes": []},
        }
        item = _parse_item(raw)
        assert item is not None
        assert item.repo == ""


# --- collect_portfolio ---


class TestCollectPortfolio:
    @pytest.mark.asyncio
    async def test_collects_and_groups_items(self):
        raw_items = [
            _make_raw_item("PVTI_1", "Bug A", 1, "org/repo-a", status="In Progress"),
            _make_raw_item("PVTI_2", "Bug B", 2, "org/repo-a", status="Blocked"),
            _make_raw_item("PVTI_3", "Feature C", 3, "org/repo-b", status="In Progress"),
        ]

        mock_client = AsyncMock()
        mock_client.get_project_items = AsyncMock(return_value=raw_items)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.github.projects_client.ProjectsV2Client",
            return_value=mock_client,
        ):
            snapshot = await collect_portfolio("org", 1, "token")

        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.total_items == 3
        assert len(snapshot.items) == 3

        # Grouped by repo
        assert "org/repo-a" in snapshot.items_by_repo
        assert len(snapshot.items_by_repo["org/repo-a"]) == 2
        assert "org/repo-b" in snapshot.items_by_repo
        assert len(snapshot.items_by_repo["org/repo-b"]) == 1

        # Grouped by status
        assert "In Progress" in snapshot.items_by_status
        assert len(snapshot.items_by_status["In Progress"]) == 2
        assert "Blocked" in snapshot.items_by_status
        assert len(snapshot.items_by_status["Blocked"]) == 1

    @pytest.mark.asyncio
    async def test_handles_empty_project(self):
        mock_client = AsyncMock()
        mock_client.get_project_items = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.github.projects_client.ProjectsV2Client",
            return_value=mock_client,
        ):
            snapshot = await collect_portfolio("org", 1, "token")

        assert snapshot.total_items == 0
        assert snapshot.items == []
        assert snapshot.items_by_repo == {}
        assert snapshot.items_by_status == {}

    @pytest.mark.asyncio
    async def test_snapshot_has_timestamp(self):
        mock_client = AsyncMock()
        mock_client.get_project_items = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.github.projects_client.ProjectsV2Client",
            return_value=mock_client,
        ):
            snapshot = await collect_portfolio("org", 1, "token")

        assert isinstance(snapshot.collected_at, datetime)
        assert snapshot.collected_at.tzinfo is not None


# --- PortfolioItem dataclass ---


class TestPortfolioItem:
    def test_defaults(self):
        item = PortfolioItem(item_id="x", title="t", number=1, repo="r")
        assert item.status == ""
        assert item.automation_tier == ""
        assert item.risk_tier == ""
        assert item.priority == ""
        assert item.owner == ""
        assert item.state == ""
