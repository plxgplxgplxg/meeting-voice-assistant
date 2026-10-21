from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an asynchronous database session with automatic commit or rollback.

    Yields:
        AsyncSession: An active SQLAlchemy async session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
