"""Feed pipeline — convert polled issues into TaskPackets and start workflows.

Epic 17 — Poll for Issues as Backup to Webhooks.
Uses synthetic delivery IDs for deduplication.
"""

import logging
import re

from opentelemetry import context as otel_context
from sqlalchemy.ext.asyncio import AsyncSession

from src.ingress.dedupe import is_duplicate
from src.ingress.workflow_trigger import start_workflow
from src.models.taskpacket import TaskPacketCreate
from src.models.taskpacket_crud import create as create_taskpacket
from src.observability.correlation import attach_correlation_id, generate_correlation_id

logger = logging.getLogger(__name__)


def synthetic_delivery_id(repo_full_name: str, issue_number: int, updated_at: str) -> str:
    """Generate a stable synthetic delivery ID for poll-originated events.

    Format: poll-{owner}-{repo}-{issue_number}-{updated_at_normalized}
    Normalizes updated_at (ISO 8601) for deterministic ID: replace colons with hyphens.

    Args:
        repo_full_name: owner/repo format.
        issue_number: GitHub issue number.
        updated_at: ISO 8601 timestamp from GitHub API.

    Returns:
        Deterministic synthetic delivery ID.
    """
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_full_name.replace("/", "-"))
    normalized = re.sub(r"[:\s]", "-", updated_at)[:19]  # YYYY-MM-DDTHH-MM-SS
    return f"poll-{slug}-{issue_number}-{normalized}"


async def feed_issues_to_pipeline(
    session: AsyncSession,
    issues: list[dict],
    repo_full_name: str,
) -> int:
    """Feed polled issues into the pipeline (TaskPacket + workflow).

    For each issue: compute synthetic delivery ID, dedupe, create TaskPacket, start workflow.
    Skips issues that already exist (same delivery_id + repo).

    Args:
        session: Database session.
        issues: List of issue dicts from GitHub API (number, updated_at).
        repo_full_name: owner/repo format.

    Returns:
        Count of TaskPackets created.
    """
    count = 0
    for issue in issues:
        number = issue.get("number", 0)
        updated_at = issue.get("updated_at", "")
        if not number or not updated_at:
            logger.warning(
                "poll.feed.skip issue=%s repo=%s missing number/updated_at",
                number,
                repo_full_name,
            )
            continue

        delivery_id = synthetic_delivery_id(repo_full_name, number, updated_at)
        if await is_duplicate(session, delivery_id, repo_full_name):
            continue

        correlation_id = generate_correlation_id()
        token = attach_correlation_id(correlation_id)

        task_data = TaskPacketCreate(
            repo=repo_full_name,
            issue_id=number,
            delivery_id=delivery_id,
            correlation_id=correlation_id,
        )
        try:
            taskpacket = await create_taskpacket(session, task_data)
            await start_workflow(taskpacket.id, correlation_id)
            count += 1
            otel_context.detach(token)
            logger.info(
                "poll.feed.created repo=%s issue=%d delivery_id=%s",
                repo_full_name,
                number,
                delivery_id,
            )
        except Exception:
            otel_context.detach(token)
            logger.exception(
                "poll.feed.failed repo=%s issue=%d delivery_id=%s",
                repo_full_name,
                number,
                delivery_id,
            )

    return count
