"""Integration tests for TaskPacket CRUD (Story 0.2).

Requires PostgreSQL. Run with: pytest -m integration
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.base import Base
from src.models.taskpacket import TaskPacketCreate, TaskPacketStatus
from src.models.taskpacket_crud import (
    InvalidStatusTransitionError,
    create,
    get_by_correlation_id,
    get_by_delivery,
    get_by_id,
    update_status,
)
from src.settings import settings

pytestmark = pytest.mark.integration


@pytest.fixture
async def session():
    """Create a test database session with fresh tables."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_create_taskpacket(session: AsyncSession) -> None:
    data = TaskPacketCreate(repo="owner/repo", issue_id=42, delivery_id=str(uuid4()))
    result = await create(session, data)
    assert result.repo == "owner/repo"
    assert result.issue_id == 42
    assert result.status == TaskPacketStatus.RECEIVED
    assert result.id is not None
    assert result.created_at is not None


async def test_create_duplicate_returns_existing(session: AsyncSession) -> None:
    delivery = str(uuid4())
    data = TaskPacketCreate(repo="owner/repo", issue_id=1, delivery_id=delivery)
    first = await create(session, data)
    second = await create(session, data)
    assert first.id == second.id


async def test_get_by_id(session: AsyncSession) -> None:
    data = TaskPacketCreate(repo="owner/repo", issue_id=1, delivery_id=str(uuid4()))
    created = await create(session, data)
    fetched = await get_by_id(session, created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_by_id_not_found(session: AsyncSession) -> None:
    result = await get_by_id(session, uuid4())
    assert result is None


async def test_get_by_delivery(session: AsyncSession) -> None:
    delivery = str(uuid4())
    data = TaskPacketCreate(repo="owner/repo", issue_id=1, delivery_id=delivery)
    created = await create(session, data)
    fetched = await get_by_delivery(session, delivery, "owner/repo")
    assert fetched is not None
    assert fetched.id == created.id


async def test_update_status(session: AsyncSession) -> None:
    data = TaskPacketCreate(repo="owner/repo", issue_id=1, delivery_id=str(uuid4()))
    created = await create(session, data)
    updated = await update_status(session, created.id, TaskPacketStatus.ENRICHED)
    assert updated.status == TaskPacketStatus.ENRICHED
    assert updated.updated_at >= created.updated_at


async def test_invalid_status_transition(session: AsyncSession) -> None:
    data = TaskPacketCreate(repo="owner/repo", issue_id=1, delivery_id=str(uuid4()))
    created = await create(session, data)
    with pytest.raises(InvalidStatusTransitionError):
        await update_status(session, created.id, TaskPacketStatus.PUBLISHED)


async def test_get_by_correlation_id(session: AsyncSession) -> None:
    cid = uuid4()
    data = TaskPacketCreate(
        repo="owner/repo", issue_id=1, delivery_id=str(uuid4()), correlation_id=cid
    )
    created = await create(session, data)
    fetched = await get_by_correlation_id(session, cid)
    assert fetched is not None
    assert fetched.id == created.id
