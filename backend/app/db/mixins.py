"""
SQLAlchemy Model Mixins.

Reusable mixin'ler — her tabloya tekrar tekrar yazmak yerine
domain odaklı sınıflardan miras alarak kompozisyon yapıyoruz.

Pattern: Composition over Inheritance.

Kullanım:
    class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
        ...
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


# ============================================================
# ID Mixin
# ============================================================
class IDMixin:
    """
    UUID Primary Key.

    Auto-increment INT yerine UUID kullanıyoruz çünkü:
    - Distributed sistemler için güvenli (collision riski yok)
    - URL'lerde tahmin edilemez (security)
    - Multi-DB sync için ideal
    - Microservice'ler arası ID consistency
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique identifier (UUID v4)",
    )


# ============================================================
# Timestamp Mixin
# ============================================================
class TimestampMixin:
    """
    created_at + updated_at otomatik takip.

    Her tabloda manuel yazmak yerine bu mixin'i kullan.
    `updated_at` her UPDATE'te otomatik güncellenir.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Record last update timestamp",
    )


# ============================================================
# Soft Delete Mixin
# ============================================================
class SoftDeleteMixin:
    """
    Soft Delete Pattern.

    Veriyi gerçekten silmek yerine `deleted_at` set ediyoruz.
    Avantajları:
    - KVKK uyumlu (audit history kalır)
    - Yanlış silme kurtarılabilir
    - İlişkili kayıtlar zarar görmez
    - Analitik için tarihsel veri korunur
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft-delete timestamp (NULL = active)",
    )

    @property
    def is_deleted(self) -> bool:
        """Bu kayıt soft-delete edilmiş mi?"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Kaydı soft-delete et."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Soft-delete'i geri al."""
        self.deleted_at = None


# ============================================================
# Audit Mixin
# ============================================================
class AuditMixin:
    """
    Audit Trail Pattern.

    Kim oluşturdu, kim güncelledi? KVKK ve compliance için kritik.
    """

    @declared_attr
    @classmethod
    def created_by_id(cls) -> Mapped[uuid.UUID | None]:
        """Oluşturan kullanıcı ID."""
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="User who created this record",
        )

    @declared_attr
    @classmethod
    def updated_by_id(cls) -> Mapped[uuid.UUID | None]:
        """Son güncelleyen kullanıcı ID."""
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who last updated this record",
        )


# ============================================================
# Serialization Mixin
# ============================================================
class SerializationMixin:
    """
    Model'i dict'e veya repr'a çevirme yardımcıları.

    Logging, debugging ve JSON serialization için.
    """

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Model'i dict'e çevir.

        Args:
            exclude: Atlanacak alanların seti.

        Returns:
            Tüm kolonlar dict olarak (UUID ve datetime stringe çevrilir).
        """
        exclude = exclude or set()
        result = {}
        for column in self.__table__.columns:  # type: ignore[attr-defined]
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def __repr__(self) -> str:
        """Helpful debug representation (sensitive data hariç)."""
        sensitive_fields = {
            "password_hash",
            "encrypted_secret",
            "refresh_token",
            "access_token",
            "refresh_token_hash",
        }
        attrs = [
            f"{c.name}={getattr(self, c.name)!r}"
            for c in self.__table__.columns  # type: ignore[attr-defined]
            if c.name not in sensitive_fields
        ]
        return f"<{self.__class__.__name__}({', '.join(attrs[:3])}...)>"