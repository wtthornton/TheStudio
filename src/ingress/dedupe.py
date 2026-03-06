"""Delivery ID + repo deduplication for webhook events."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.taskpacket_crud import get_by_delivery


async def is_duplicate(session: AsyncSession, delivery_id: str, repo: str) -> bool:
    """Check if a (delivery_id, repo) combination already exists."""
    existing = await get_by_delivery(session, delivery_id, repo)
    return existing is not None
