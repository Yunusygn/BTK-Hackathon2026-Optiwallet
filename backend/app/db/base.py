"""
SQLAlchemy Declarative Base.

Tüm modeller bu Base sınıfından türer.
Common alanlar (id, created_at, vs.) Mixin'lerde tanımlı.
"""

from __future__ import annotations

import re

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr


# Naming convention — Alembic migration'ları temiz olsun
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Ana Base class — tüm modeller bundan türer.

    Sadece tabloya özgü olmayan ayarlar burada:
    - Naming convention (Alembic için)
    - Otomatik tablo adı (snake_case + plural)

    Common alanlar için Mixin'ler kullanılır:
    - IDMixin: UUID primary key
    - TimestampMixin: created_at, updated_at
    - SoftDeleteMixin: deleted_at + soft delete logic
    - AuditMixin: created_by_id, updated_by_id

    Örnek:
        from app.db.mixins import IDMixin, TimestampMixin, SoftDeleteMixin

        class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
            email: Mapped[str] = mapped_column(String(255))
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """
        Sınıf adından snake_case + plural tablo adı üret.

        Örnekler:
            User → users
            OAuthAccount → oauth_accounts
            CreditCard → credit_cards
            Category → categories
        """
        # PascalCase → snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

        # Basit pluralization
        if name.endswith("y"):
            return name[:-1] + "ies"
        if name.endswith(("s", "x", "ch", "sh")):
            return name + "es"
        return name + "s"