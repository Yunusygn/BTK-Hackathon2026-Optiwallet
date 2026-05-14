"""
User & Authentication Models.

Tablolar:
- User: Ana kullanıcı tablosu (soft-delete destekli)
- OAuthAccount: Google/Apple OAuth bağlantıları
- Session: Aktif oturumlar (refresh token, device tracking)
- TwoFactorSecret: 2FA için TOTP secret

Mixin Kullanımı:
- IDMixin: UUID primary key (hepsi)
- TimestampMixin: created_at, updated_at (hepsi)
- SoftDeleteMixin: User için (silinen user'lar tarihte kalır)
- SerializationMixin: to_dict() ve secure __repr__
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import (
    IDMixin,
    SerializationMixin,
    SoftDeleteMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    pass


# ============================================================
# Enums
# ============================================================
class OAuthProvider(str, enum.Enum):
    """Desteklenen OAuth provider'lar."""

    GOOGLE = "google"
    APPLE = "apple"


class UserRole(str, enum.Enum):
    """
    Kullanıcı rolleri (RBAC hazırlığı).

    USER: Standart kullanıcı
    PREMIUM: Ödeme yapan kullanıcı (gelecekte)
    ADMIN: Sistem yöneticisi
    """

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


# ============================================================
# User
# ============================================================
class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin, SerializationMixin):
    """
    Ana kullanıcı tablosu.

    Özellikler:
    - Email/şifre + OAuth (Google, Apple) authentication
    - 2FA support (TOTP)
    - Soft delete (KVKK uyumlu)
    - Role-based access control
    - Account locking (failed login attempts)
    - Session tracking

    İlişkiler:
    - oauth_accounts: 0..N OAuth bağlantısı
    - sessions: 0..N aktif oturum
    - two_factor_secret: 0..1 2FA setup
    """

    # ===== Identity =====
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email (unique, case-insensitive)",
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Authentication =====
    # Nullable çünkü OAuth-only kullanıcılar olabilir
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt hashed password (NULL for OAuth-only users)",
    )

    # ===== Profile (denormalized for performance) =====
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ===== Role & Status =====
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp (brute force protection)",
    )

    # ===== Security Tracking =====
    failed_login_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Consecutive failed login attempts",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IPv4 or IPv6 of last login",
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== 2FA =====
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ===== Preferences (defaults for Turkish users) =====
    locale: Mapped[str] = mapped_column(String(10), default="tr-TR", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Europe/Istanbul",
        nullable=False,
    )

    # ============================================================
    # Relationships
    # ============================================================
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    two_factor_secret: Mapped[TwoFactorSecret | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    # ============================================================
    # Indexes & Constraints
    # ============================================================
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    # ============================================================
    # Domain Logic (Business Methods)
    # ============================================================
    @property
    def full_name(self) -> str:
        """Tam isim — yoksa email'in @ öncesini döner."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email.split("@")[0]

    @property
    def is_oauth_user(self) -> bool:
        """OAuth-only kullanıcı mı (şifresiz)?"""
        return self.password_hash is None and len(self.oauth_accounts) > 0

    @property
    def can_login(self) -> bool:
        """Şu an giriş yapabilir mi?"""
        if not self.is_active or self.is_deleted:
            return False
        if self.is_locked and self.locked_until:
            return datetime.now(timezone.utc) > self.locked_until
        return True

    def record_successful_login(self, ip: str | None = None) -> None:
        """Başarılı girişi kaydet ve sayaçları sıfırla."""
        self.last_login_at = datetime.now(timezone.utc)
        self.last_login_ip = ip
        self.failed_login_count = 0
        self.is_locked = False
        self.locked_until = None

    def record_failed_login(self, max_attempts: int = 5) -> None:
        """Başarısız girişi kaydet. Limit aşılırsa hesabı kilitle."""
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.is_locked = True
            # 30 dakika kilitle (exponential backoff yapılabilir)
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)


# ============================================================
# OAuth Account
# ============================================================
class OAuthAccount(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    OAuth provider bağlantıları.

    Bir kullanıcı birden fazla provider'a bağlanabilir
    (Google + Apple gibi).

    Token'lar production'da AES-256 ile şifrelenmeli.
    """

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[OAuthProvider] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"),
        nullable=False,
    )
    provider_account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="OAuth provider'ın kendi user ID'si",
    )
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Token storage (encrypted at rest in production)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Scope ve provider-specific data
    scopes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    raw_user_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ===== Relationships =====
    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        Index(
            "uq_oauth_provider_account",
            "provider",
            "provider_account_id",
            unique=True,
        ),
    )


# ============================================================
# Session
# ============================================================
class Session(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Aktif kullanıcı oturumları.

    Refresh token rotasyonu + device tracking.
    "Tüm cihazlardan çıkış" özelliği için kritik.

    SoftDeleteMixin kullanmıyoruz — session'lar revoke edilir,
    sonra periyodik olarak temizlenir (Celery beat task).
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token storage (hashed — düz token saklanmaz!)
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Device & Network info
    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User-friendly device name (e.g., 'Chrome on Windows')",
    )
    device_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="mobile, desktop, tablet",
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="City, Country (IP-based geolocation)",
    )

    # Lifecycle
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Session manually revoked (logout)",
    )

    # ===== Relationships =====
    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user_expires", "user_id", "expires_at"),
    )

    @property
    def is_active(self) -> bool:
        """Session hâlâ aktif mi?"""
        if self.revoked_at is not None:
            return False
        return self.expires_at > datetime.now(timezone.utc)

    def revoke(self) -> None:
        """Session'ı iptal et (logout)."""
        self.revoked_at = datetime.now(timezone.utc)


# ============================================================
# Two-Factor Authentication
# ============================================================
class TwoFactorSecret(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    2FA TOTP secrets.

    Kullanıcı başına bir tane (one-to-one).
    Backup codes hash'lenmiş şekilde array'de tutulur.

    Production'da `encrypted_secret` AES-256 ile şifrelenmeli.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Encrypted TOTP secret
    encrypted_secret: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256 encrypted TOTP secret",
    )

    # Backup codes (each hashed individually)
    backup_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Hashed backup recovery codes",
    )

    # Status tracking
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="2FA aktivasyonu tamamlandığında set olur",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Relationships =====
    user: Mapped[User] = relationship(back_populates="two_factor_secret")

    @property
    def is_confirmed(self) -> bool:
        """2FA aktivasyon tamamlandı mı?"""
        return self.confirmed_at is not None