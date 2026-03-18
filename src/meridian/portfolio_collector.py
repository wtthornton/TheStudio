"""Portfolio data collector — snapshots GitHub Projects v2 board state.

Epic 29 AC 13: Queries the GitHub Projects v2 API to collect current board
state with all items and field values, grouped by repo and status.

Uses ProjectsV2Client.get_project_items() and shapes the data into a
PortfolioSnapshot for the Meridian portfolio review agent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.observability.conventions import SPAN_MERIDIAN_PORTFOLIO_COLLECT
from src.observability.tracing import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("thestudio.meridian.portfolio_collector")


@dataclass
class PortfolioItem:
    """A single item on the Projects v2 board."""

    item_id: str
    title: str
    number: int
    repo: str
    status: str = ""
    automation_tier: str = ""
    risk_tier: str = ""
    priority: str = ""
    owner: str = ""
    state: str = ""  # GitHub issue/PR state (OPEN, CLOSED, MERGED)


@dataclass
class PortfolioSnapshot:
    """Point-in-time snapshot of the Projects v2 board state.

    Items are grouped by repo and by status for easy analysis
    by the Meridian portfolio review agent.
    """

    collected_at: datetime
    total_items: int = 0
    items: list[PortfolioItem] = field(default_factory=list)
    items_by_repo: dict[str, list[PortfolioItem]] = field(default_factory=dict)
    items_by_status: dict[str, list[PortfolioItem]] = field(default_factory=dict)


def _extract_field_value(field_values_nodes: list[dict[str, Any]], field_name: str) -> str:
    """Extract a field value by name from a list of field value nodes."""
    for node in field_values_nodes:
        if not node:
            continue
        # Single-select fields have 'name' + nested 'field.name'
        node_field = node.get("field", {})
        node_field_name = node_field.get("name", "") if node_field else ""
        if node_field_name == field_name:
            # Single-select: value is in 'name'
            if "name" in node:
                return node["name"]
            # Text: value is in 'text'
            if "text" in node:
                return node["text"]
    return ""


def _parse_item(raw_item: dict[str, Any]) -> PortfolioItem | None:
    """Parse a raw GraphQL project item into a PortfolioItem."""
    if not raw_item:
        return None

    content = raw_item.get("content") or {}
    field_values = raw_item.get("fieldValues", {}).get("nodes", [])

    repo_data = content.get("repository", {})
    repo = repo_data.get("nameWithOwner", "") if repo_data else ""

    return PortfolioItem(
        item_id=raw_item.get("id", ""),
        title=content.get("title", ""),
        number=content.get("number", 0),
        repo=repo,
        status=_extract_field_value(field_values, "Status"),
        automation_tier=_extract_field_value(field_values, "Automation Tier"),
        risk_tier=_extract_field_value(field_values, "Risk Tier"),
        priority=_extract_field_value(field_values, "Priority"),
        owner=_extract_field_value(field_values, "Owner"),
        state=content.get("state", ""),
    )


async def collect_portfolio(
    owner: str,
    project_number: int,
    token: str,
) -> PortfolioSnapshot:
    """Collect a snapshot of the Projects v2 board state.

    Uses ProjectsV2Client.get_project_items() and shapes the raw GraphQL
    response into a PortfolioSnapshot with items grouped by repo and status.
    """
    from src.github.projects_client import ProjectsV2Client

    with tracer.start_as_current_span(SPAN_MERIDIAN_PORTFOLIO_COLLECT) as span:
        span.set_attribute("thestudio.projects_v2.owner", owner)
        span.set_attribute("thestudio.projects_v2.project_number", project_number)

        async with ProjectsV2Client(token) as client:
            raw_items = await client.get_project_items(owner, project_number)

        items: list[PortfolioItem] = []
        for raw in raw_items:
            item = _parse_item(raw)
            if item is not None:
                items.append(item)

        # Group by repo
        items_by_repo: dict[str, list[PortfolioItem]] = {}
        for item in items:
            items_by_repo.setdefault(item.repo, []).append(item)

        # Group by status
        items_by_status: dict[str, list[PortfolioItem]] = {}
        for item in items:
            items_by_status.setdefault(item.status, []).append(item)

        snapshot = PortfolioSnapshot(
            collected_at=datetime.now(UTC),
            total_items=len(items),
            items=items,
            items_by_repo=items_by_repo,
            items_by_status=items_by_status,
        )

        span.set_attribute("thestudio.meridian.total_items", snapshot.total_items)
        span.set_attribute("thestudio.meridian.repo_count", len(items_by_repo))

        logger.info(
            "meridian.portfolio.collected",
            extra={
                "total_items": snapshot.total_items,
                "repo_count": len(items_by_repo),
                "status_distribution": {k: len(v) for k, v in items_by_status.items()},
            },
        )

        return snapshot
