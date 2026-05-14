"""
Alembic Environment Configuration.

Async SQLAlchemy 2.0 ile uyumlu, settings'den DB URL okuyor.
Tüm modeller import edilir ki autogenerate çalışsın.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ===== Project Imports =====
from app.core.config import settings
from app.db.base import Base

# Tüm modelleri import et (autogenerate için kritik)
from app.models import (  # noqa: F401
    # User & Auth
    User,
    OAuthAccount,
    Session,
    TwoFactorSecret,
    # Profile
    Profile,
    FinancialProfile,
    Preferences,
    # Finance
    CreditCard,
    Coupon,
    FinancialGoal,
    Expense,
    Budget,
    RecurringPayment,
    # Conversation
    Folder,
    Conversation,
    Message,
    MessageFeedback,
    Recommendation,
    FavoriteFolder,
    Favorite,
    PriceHistory,
    PriceAlert,
    Comparison,
    # Notification
    Notification,
    NotificationSettings,
    PushSubscription,
    AuditLog,
)

# ===== Alembic Config =====
config = context.config

# Async URL'i sync'e çevir (Alembic sync çalışır)
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_db_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate için target metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline mode — SQL script üret ama uygulamadan."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Migration'ları sync connection ile çalıştır."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async engine üzerinden sync migration çalıştır."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online mode — gerçek database'e bağlanıp migration çalıştır."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()