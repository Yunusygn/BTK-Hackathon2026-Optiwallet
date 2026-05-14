"""
Conversation & Recommendation Models.

Sohbet ve tavsiye akışı tabloları:
- Folder: Sohbetleri organize etmek için klasörler
- Conversation: Sohbetler (kullanıcı + AI)
- Message: Sohbet mesajları (user, assistant, system)
- Recommendation: AI'ın ürettiği nihai tavsiyeler
- FavoriteFolder: Favori ürünleri organize etmek için klasörler
- Favorite: Favorilenmiş ürünler
- PriceHistory: Favori ürünlerin fiyat geçmişi
- PriceAlert: Fiyat alarmı kuralları
- Comparison: Kullanıcının kaydettiği karşılaştırmalar
- MessageFeedback: Mesaj beğeni/beğenmeme
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import IDMixin, SerializationMixin, SoftDeleteMixin, TimestampMixin


# ============================================================
# Enums
# ============================================================
class MessageRole(str, enum.Enum):
    """Sohbet mesaj rolü (OpenAI/LangChain standardı)."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationStatus(str, enum.Enum):
    """Sohbet durumu."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    SHARED = "shared"


class AgentName(str, enum.Enum):
    """7 AI ajanımızın isimleri (logging ve UI için)."""

    RESEARCH = "research"
    NEEDS_ANALYSIS = "needs_analysis"
    MARKET = "market"
    FINANCE = "finance"
    STRATEGY = "strategy"
    VERIFIER = "verifier"
    AUDITOR = "auditor"


class FeedbackRating(str, enum.Enum):
    """Mesaj feedback'i."""

    LIKE = "like"
    DISLIKE = "dislike"


class AlertType(str, enum.Enum):
    """Fiyat alarmı tipi."""

    BELOW_AMOUNT = "below_amount"  # X TL altına düşerse
    PERCENT_DROP = "percent_drop"  # %X düşerse
    BACK_IN_STOCK = "back_in_stock"  # Stoka tekrar girerse


# ============================================================
# Folder (Conversation Organization)
# ============================================================
class Folder(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Sohbetleri organize etmek için klasörler.

    Örnek: "Ev Alışverişi", "Hediyeler", "Elektronik"
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Hex color veya tailwind class",
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Emoji veya icon kodu",
    )
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)


# ============================================================
# Conversation
# ============================================================
class Conversation(Base, IDMixin, TimestampMixin, SoftDeleteMixin, SerializationMixin):
    """
    Kullanıcının sohbetleri.

    Her sohbet birden fazla mesaj ve tavsiye barındırır.
    Misafir kullanıcılar için user_id NULL olabilir (geçici sohbet).
    """

    # User nullable — misafir mod için
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ===== Identity =====
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="AI ile otomatik oluşturulur, kullanıcı düzenleyebilir",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI ile oluşturulan kısa özet",
    )

    # ===== Tags =====
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Kullanıcı etiketleri (#tv, #hediye, vs.)",
    )

    # ===== Status =====
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ===== Sharing =====
    share_token: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Public share URL token (NULL = paylaşılmadı)",
    )
    shared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Statistics =====
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ===== Relationships =====
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_conversations_user_last_message", "user_id", "last_message_at"),
        Index("ix_conversations_user_status", "user_id", "status"),
    )


# ============================================================
# Message
# ============================================================
class Message(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Sohbet mesajları.

    User mesajı, AI cevapları ve agent step detayları burada.
    Streaming için her chunk ayrı message değil, son halinde kaydedilir.
    """

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Message Content =====
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ===== Agent Workflow (LangGraph tracing) =====
    agent_steps: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Her ajanın adımı (Research, Needs, Market, ..., Auditor)",
    )

    # ===== Sources (Grounding citations) =====
    sources: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Kaynak URL'leri ve özetleri",
    )

    # ===== Multimodal Attachments =====
    attachments: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Foto, ses dosyaları, vb.",
    )

    # ===== AI Metadata =====
    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Hangi Gemini modeli kullanıldı",
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Toplam token (input + output)",
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="0.00-1.00 arası güven skoru",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Cevap üretim süresi (ms)",
    )

    # ===== Auditor Flag =====
    auditor_rejected_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Auditor kaç kez reddetti (sahne anı için)",
    )

    # ===== Relationships =====
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    feedback: Mapped["MessageFeedback | None"] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="confidence_score_range",
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


# ============================================================
# Message Feedback
# ============================================================
class MessageFeedback(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Mesaja kullanıcı geri bildirimi (beğeni/beğenmeme + yorum).

    AI'ın gelişmesi için değerli veri.
    """

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    rating: Mapped[FeedbackRating] = mapped_column(
        Enum(FeedbackRating, name="feedback_rating"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Relationships =====
    message: Mapped[Message] = relationship(back_populates="feedback")


# ============================================================
# Recommendation
# ============================================================
class Recommendation(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    AI'ın ürettiği nihai ürün tavsiyesi.

    Bir Strategy Agent + Auditor + Verifier çıktısı.
    Mesajdan ayrı tutuyoruz çünkü kullanıcı sonra "favorilere ekle",
    "karşılaştır", "fiyat takibi" gibi işlemler yapacak.
    """

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Primary Recommendation =====
    primary_product: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Ana tavsiye edilen ürün (name, price, platform, url, vs.)",
    )

    # ===== Alternatives =====
    alternatives: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Alternatif ürünler",
    )

    # ===== Reasoning =====
    reasoning: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Neden bu ürün önerildi (markdown)",
    )

    # ===== Confidence =====
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        comment="AI'ın bu tavsiyeye güveni (0.00-1.00)",
    )

    # ===== Market Consensus =====
    market_consensus: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Forum, review, YouTube'dan toplanan piyasa görüşü",
    )

    # ===== Financial Analysis =====
    financial_analysis: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Taksit, bütçe, hedef etkisi analizi",
    )

    # ===== Sources =====
    sources: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Kaynak linkler",
    )

    # ===== Relationships =====
    conversation: Mapped[Conversation] = relationship(back_populates="recommendations")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
    )


# ============================================================
# Favorite Folder
# ============================================================
class FavoriteFolder(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Favori ürünleri organize etmek için klasörler.

    Örnek: "Almak istediklerim", "Hediyeler", "Sonra alırım"
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)


# ============================================================
# Favorite
# ============================================================
class Favorite(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Favorilenmiş ürünler.

    Fiyat takibi, alarm, karşılaştırma için kullanılır.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("favorite_folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ===== Product Data (JSONB for flexibility) =====
    product_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Ürün bilgisi (name, image, platform, url, category, vs.)",
    )

    # ===== User Notes =====
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Tracking =====
    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Son bilinen fiyat",
    )
    initial_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Favoriye eklenirken fiyat",
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Relationships =====
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="favorite",
        cascade="all, delete-orphan",
        order_by="PriceHistory.captured_at",
    )
    price_alerts: Mapped[list["PriceAlert"]] = relationship(
        back_populates="favorite",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_favorites_user_folder", "user_id", "folder_id"),
    )


# ============================================================
# Price History
# ============================================================
class PriceHistory(Base, IDMixin, SerializationMixin):
    """
    Favori ürünlerin fiyat geçmişi.

    Celery task ile periyodik olarak güncellenir.
    Grafik göstermek için kullanılır.

    Not: TimestampMixin yok — `captured_at` kendi timestamp'i.
    """

    favorite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("favorites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)

    is_in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_on_sale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Hangi platformdan çekildi (trendyol, hepsiburada, vs.)",
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # ===== Relationships =====
    favorite: Mapped[Favorite] = relationship(back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_favorite_captured", "favorite_id", "captured_at"),
    )


# ============================================================
# Price Alert
# ============================================================
class PriceAlert(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kullanıcının kurduğu fiyat alarmları.

    "X TL altına düşerse haber ver" veya "%15 düşerse" gibi.
    """

    favorite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("favorites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type"),
        nullable=False,
    )

    # ===== Thresholds =====
    target_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="BELOW_AMOUNT için hedef fiyat",
    )
    percent_threshold: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="PERCENT_DROP için yüzde",
    )

    # ===== Status =====
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ===== Relationships =====
    favorite: Mapped[Favorite] = relationship(back_populates="price_alerts")


# ============================================================
# Comparison
# ============================================================
class Comparison(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kullanıcının kaydettiği karşılaştırmalar.

    "Bu 3 TV'yi karşılaştırdım" gibi snapshot'lar.
    Sonra geri dönüp bakabilir.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Karşılaştırılan ürünlerin snapshot'ı
    products: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Karşılaştırılan ürünlerin tam snapshot'ı",
    )

    # AI'ın o anki tavsiyesi
    ai_recommendation: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI'ın bu karşılaştırma için verdiği tavsiye",
    )