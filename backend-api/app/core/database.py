from collections.abc import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.errors import DomainError

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class with deterministic constraint names."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


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

    This dependency owns the request transaction: services only flush.

    Yields:
        AsyncSession: An active SQLAlchemy async session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except DomainError as exc:
            if exc.commit_changes:
                await session.commit()
            else:
                await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
