"""
Notification Models.

Bildirim sistemi tabloları:
- NotificationSettings: Kullanıcı bildirim tercihleri
- Notification: Gönderilen/gönderilecek bildirimler
- PushSubscription: PWA push notification abonelikleri
- AuditLog: Güvenlik ve compliance için işlem kayıtları
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IDMixin, SerializationMixin, TimestampMixin


# ============================================================
# Enums
# ============================================================
class NotificationType(str, enum.Enum):
    """Bildirim tipleri."""

    # Fiyat takibi
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    PRICE_ALERT_TRIGGERED = "price_alert_triggered"

    # Bütçe
    BUDGET_THRESHOLD = "budget_threshold"
    BUDGET_EXCEEDED = "budget_exceeded"

    # Mali hedefler
    GOAL_PROGRESS = "goal_progress"
    GOAL_ACHIEVED = "goal_achieved"

    # Kuponlar
    COUPON_EXPIRING = "coupon_expiring"
    NEW_COUPON = "new_coupon"

    # Periyodik ödemeler
    RECURRING_PAYMENT_DUE = "recurring_payment_due"

    # AI ve sistem
    AI_INSIGHT = "ai_insight"  # Haftalık özet
    SECURITY_ALERT = "security_alert"  # Yeni cihazdan giriş
    SYSTEM_ANNOUNCEMENT = "system_announcement"  # Yeni özellik
    ACCOUNT_ACTIVITY = "account_activity"  # Genel hesap aktivitesi


class NotificationChannel(str, enum.Enum):
    """Bildirim kanalı."""

    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    """Bildirim durumu."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class NotificationFrequency(str, enum.Enum):
    """Bildirim sıklığı."""

    INSTANT = "instant"  # Anlık
    DAILY = "daily"  # Günlük özet
    WEEKLY = "weekly"  # Haftalık özet
    DISABLED = "disabled"  # Kapalı


class AuditAction(str, enum.Enum):
    """Audit log eylemleri."""

    # Auth
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    EMAIL_CHANGED = "email_changed"
    TWO_FACTOR_ENABLED = "two_factor_enabled"
    TWO_FACTOR_DISABLED = "two_factor_disabled"

    # Account
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"

    # Data
    DATA_EXPORTED = "data_exported"
    PROFILE_UPDATED = "profile_updated"

    # Financial
    CARD_ADDED = "card_added"
    CARD_REMOVED = "card_removed"
    BANK_LINKED = "bank_linked"
    BANK_UNLINKED = "bank_unlinked"

    # AI
    CHAT_STARTED = "chat_started"
    RECOMMENDATION_GENERATED = "recommendation_generated"


# ============================================================
# Notification Settings
# ============================================================
class NotificationSettings(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kullanıcı bildirim tercihleri.

    Her bildirim tipi için ayrı kanal/sıklık ayarlanabilir.
    """
    
    __tablename__ = "notification_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ===== Master Switches =====
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ===== Email Digest Frequency =====
    email_frequency: Mapped[NotificationFrequency] = mapped_column(
        Enum(NotificationFrequency, name="notification_frequency"),
        default=NotificationFrequency.INSTANT,
        nullable=False,
    )

    # ===== Per-type Settings =====
    # JSONB ile esnek ayar: { "price_drop": {"email": true, "push": true}, ... }
    type_settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Her notification_type için kanal tercihi",
    )

    # ===== Quiet Hours =====
    quiet_hours_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    quiet_hours_start: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM format (örn: '22:00')",
    )
    quiet_hours_end: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM format (örn: '08:00')",
    )


# ============================================================
# Notification
# ============================================================
class Notification(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Gönderilen veya gönderilecek bildirimler.

    Bir bildirim birden fazla kanaldan gidebilir (in-app + email).
    Her kanal ayrı status takip eder.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Type =====
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
        index=True,
    )

    # ===== Content =====
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ===== Action =====
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Tıklandığında gidilecek URL",
    )
    action_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Action button text",
    )

    # ===== Metadata (esnek) =====
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bildirim tipine özel ek veri",
    )

    # ===== Channels (delivery status) =====
    channels: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Gönderildiği kanallar",
    )

    # ===== Status =====
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # ===== Read tracking =====
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Scheduling =====
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="İleri tarihli bildirimler için",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    def mark_as_read(self) -> None:
        """Bildirimi okundu olarak işaretle."""
        from datetime import timezone
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)
        if self.status == NotificationStatus.DELIVERED:
            self.status = NotificationStatus.READ


# ============================================================
# Push Subscription
# ============================================================
class PushSubscription(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    PWA push notification abonelikleri.

    Bir kullanıcının birden fazla cihazı olabilir (telefon + tablet).
    Endpoint+keys browser tarafından üretilir.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Web Push API Data =====
    endpoint: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        comment="Browser's push service URL",
    )
    p256dh_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Public key (encryption)",
    )
    auth_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Auth secret",
    )

    # ===== Device Info =====
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="desktop, mobile, tablet",
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Status =====
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_push_subscriptions_user_active", "user_id", "is_active"),
    )


# ============================================================
# Audit Log
# ============================================================
class AuditLog(Base, IDMixin, SerializationMixin):
    """
    Güvenlik ve compliance için audit log.

    KVKK uyumluluğu, security forensics, debug için kritik.
    Tüm hassas işlemler buraya kaydedilir.

    Not: TimestampMixin yok — `occurred_at` daha açıklayıcı.
    """

    # User nullable çünkü failed login (henüz authenticate olmadı) gibi durumlar olabilir
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ===== Action =====
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"),
        nullable=False,
        index=True,
    )

    # ===== Resource =====
    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Hangi kaynak (örn: 'credit_card', 'conversation')",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Kaynak ID",
    )

    # ===== Context =====
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ===== Extra Data =====
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Olaya özel ek bilgi (eski değer/yeni değer, vb.)",
    )

    # ===== Success/Failure =====
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Timing =====
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_user_occurred", "user_id", "occurred_at"),
        Index("ix_audit_logs_action_occurred", "action", "occurred_at"),
    )