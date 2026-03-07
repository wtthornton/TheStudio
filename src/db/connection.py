from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (FastAPI Depends generator)."""
    async with async_session_factory() as session:
        yield session


def get_async_session() -> AsyncSession:
    """Return an async session as a context manager.

    Usage:
        async with get_async_session() as session:
            ...
    """
    return async_session_factory()
