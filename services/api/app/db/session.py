"""
Aegis AI — Database Engine & Session Management.

Provides async SQLAlchemy engine, session factory, and FastAPI dependency
for database session injection.

Architecture Decision:
    We use SQLAlchemy 2.0's async engine with asyncpg for non-blocking
    database operations. Sessions are scoped to individual HTTP requests
    via FastAPI's dependency injection, ensuring proper cleanup.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All models inherit from this to participate in metadata collection
    and Alembic migration generation.
    """
    pass


def create_engine(settings: Settings | None = None):
    """
    Create an async SQLAlchemy engine with connection pooling.

    Args:
        settings: Application settings. Uses global settings if not provided.

    Returns:
        AsyncEngine configured for the application database.
    """
    if settings is None:
        settings = get_settings()

    if "sqlite" in settings.database_url:
        from sqlalchemy.pool import StaticPool
        return create_async_engine(
            settings.database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=settings.app_debug and settings.is_development,
        )

    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        poolclass=AsyncAdaptedQueuePool,
        echo=settings.app_debug and settings.is_development,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "server_settings": {
                "application_name": settings.app_name,
                "jit": "off",
            }
        },
    )


# Global engine and session factory — initialized on startup
engine = create_engine()
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    The session is automatically committed on success and rolled back
    on exception, then closed in all cases.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Type alias for cleaner route signatures
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
