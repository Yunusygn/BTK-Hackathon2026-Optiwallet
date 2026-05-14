"""
Database Session Management.

Async SQLAlchemy 2.0 ile PostgreSQL bağlantısı.
Connection pooling, dependency injection, session lifecycle.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine.

    Connection pool settings production'a uygun.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG and settings.is_development,
        echo_pool=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,  # Connection sağlığını kontrol et
        pool_recycle=3600,    # 1 saat sonra recycle
        future=True,
    )
    logger.info("database_engine_created", url=settings.POSTGRES_HOST)
    return engine


# Module-level engine ve session factory
engine: AsyncEngine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: async database session.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close all database connections (shutdown event'inde çağrılır)."""
    await engine.dispose()
    logger.info("database_engine_disposed")