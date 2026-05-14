"""
Finance Models.

Mali yönetim tabloları:
- CreditCard: Kullanıcının kredi kartları
- Coupon: Aktif kuponlar
- FinancialGoal: Mali hedefler (yaz tatili, yeni telefon, vs.)
- Expense: Harcamalar
- Budget: Kategori bazlı bütçe
- BudgetHistory: Aylık bütçe geçmişi
- RecurringPayment: Periyodik ödemeler (kira, faturalar)
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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

if TYPE_CHECKING:
    from app.models.user import User


# ============================================================
# Enums
# ============================================================
class BankCode(str, enum.Enum):
    """
    Türk bankaları.

    Mock Bank API'mizdeki bankalarla birebir eşleşiyor.
    """

    AKBANK = "akbank"
    GARANTI = "garanti"
    ISBANK = "isbank"
    YAPIKREDI = "yapikredi"
    ZIRAAT = "ziraat"
    HALKBANK = "halkbank"
    VAKIFBANK = "vakifbank"
    QNB = "qnb"
    OTHER = "other"


class CardType(str, enum.Enum):
    """Kart tipleri (ödül programları)."""

    AXESS = "axess"  # Akbank
    BONUS = "bonus"  # Garanti
    WORLD = "world"  # Yapı Kredi, VakıfBank
    MAXIMUM = "maximum"  # İş Bankası
    BANKKART = "bankkart"  # Ziraat
    PARAF = "paraf"  # Halkbank
    CARDFINANS = "cardfinans"  # QNB
    OTHER = "other"


class CouponType(str, enum.Enum):
    """Kupon tipleri."""

    AMOUNT = "amount"  # Sabit tutar indirimi (50 TL)
    PERCENTAGE = "percentage"  # Yüzde indirimi (%10)


class ExpenseCategory(str, enum.Enum):
    """
    Harcama kategorileri.

    AI ile otomatik kategorize edilir, kullanıcı manuel düzeltebilir.
    """

    GROCERY = "grocery"  # Market
    DINING = "dining"  # Restoran
    TRANSPORT = "transport"  # Ulaşım
    UTILITIES = "utilities"  # Faturalar
    RENT = "rent"  # Kira
    HEALTHCARE = "healthcare"  # Sağlık
    ENTERTAINMENT = "entertainment"  # Eğlence
    CLOTHING = "clothing"  # Giyim
    ELECTRONICS = "electronics"  # Elektronik
    EDUCATION = "education"  # Eğitim
    TRAVEL = "travel"  # Seyahat
    SUBSCRIPTION = "subscription"  # Abonelikler
    HOME = "home"  # Ev eşyası
    PERSONAL_CARE = "personal_care"  # Kişisel bakım
    GIFTS = "gifts"  # Hediyeler
    OTHER = "other"


class GoalStatus(str, enum.Enum):
    """Mali hedef durumu."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class RecurringFrequency(str, enum.Enum):
    """Periyodik ödeme sıklığı."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    WEEKLY = "weekly"


# ============================================================
# Credit Card
# ============================================================
class CreditCard(Base, IDMixin, TimestampMixin, SoftDeleteMixin, SerializationMixin):
    """
    Kullanıcının kredi kartları.

    Kart numarası SAKLAMAZ (PCI-DSS).
    Sadece bilgilendirme amaçlı meta veri tutar.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Card Identity =====
    nickname: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Kullanıcının verdiği isim (örn: 'İş Kartı', 'Alışveriş Kartı')",
    )
    bank: Mapped[BankCode] = mapped_column(
        Enum(BankCode, name="bank_code"),
        nullable=False,
    )
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType, name="card_type"),
        nullable=False,
    )
    last_four_digits: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="Sadece son 4 hane (görüntüleme için)",
    )

    # ===== Limits & Balance =====
    total_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Toplam kart limiti",
    )
    available_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Anlık kullanılabilir limit",
    )

    # ===== Statement Dates =====
    statement_day: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Hesap kesim günü (1-28)",
    )
    payment_due_day: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Son ödeme günü",
    )

    # ===== Rewards =====
    points_per_lira: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.00"),
        nullable=False,
        comment="1 TL harcamada kazanılan puan",
    )
    current_points: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # ===== Installment Configuration =====
    installment_options: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        default=lambda: [2, 3, 6, 9, 12],
        nullable=False,
        comment="Bu kart için mevcut taksit seçenekleri",
    )
    default_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        default=Decimal("0.0349"),
        nullable=False,
        comment="Yıllık nominal faiz oranı (banka varsayılanı)",
    )

    # ===== Status =====
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Varsayılan kart mı?",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "statement_day IS NULL OR (statement_day >= 1 AND statement_day <= 28)",
            name="statement_day_range",
        ),
        CheckConstraint(
            "payment_due_day IS NULL OR (payment_due_day >= 1 AND payment_due_day <= 28)",
            name="payment_due_day_range",
        ),
        CheckConstraint(
            "available_limit <= total_limit",
            name="available_limit_lte_total",
        ),
        Index("ix_credit_cards_user_active", "user_id", "is_active"),
    )

    @property
    def used_limit(self) -> Decimal:
        """Kullanılan limit (toplam - kullanılabilir)."""
        return self.total_limit - self.available_limit

    @property
    def usage_percentage(self) -> float:
        """Kullanım yüzdesi (%)."""
        if self.total_limit == 0:
            return 0.0
        return float(self.used_limit / self.total_limit * 100)


# ============================================================
# Coupon
# ============================================================
class Coupon(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Aktif kuponlar.

    Süresi dolmuş kuponlar Celery task ile temizlenir.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Coupon Info =====
    platform: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Pazaryeri (trendyol, hepsiburada, vs.)",
    )
    code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Kupon kodu (varsa)",
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ===== Value =====
    coupon_type: Mapped[CouponType] = mapped_column(
        Enum(CouponType, name="coupon_type"),
        nullable=False,
    )
    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Sabit tutar (TYPE=amount ise)",
    )
    percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Yüzde (TYPE=percentage ise, 0-100)",
    )

    # ===== Constraints =====
    min_basket_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Min. sepet tutarı",
    )
    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maks. indirim (% kuponlarda)",
    )
    applicable_categories: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Geçerli kategoriler (boş = tüm kategoriler)",
    )

    # ===== Validity =====
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # ===== Usage =====
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="percentage_range",
        ),
        Index("ix_coupons_user_expires", "user_id", "expires_at"),
    )


# ============================================================
# Financial Goal
# ============================================================
class FinancialGoal(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Mali hedefler.

    Örnekler: "Yaz tatili - 24K TL", "Yeni laptop - 50K TL"
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Goal Info =====
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Emoji veya icon kodu",
    )

    # ===== Financial =====
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    monthly_contribution: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Aylık planlanan katkı",
    )

    # ===== Timeline =====
    target_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ===== Status =====
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status"),
        default=GoalStatus.ACTIVE,
        nullable=False,
    )
    achieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_amount_positive"),
        CheckConstraint("current_amount >= 0", name="current_amount_non_negative"),
    )

    @property
    def progress_percentage(self) -> float:
        """İlerleme yüzdesi (%)."""
        if self.target_amount == 0:
            return 0.0
        return min(100.0, float(self.current_amount / self.target_amount * 100))

    @property
    def remaining_amount(self) -> Decimal:
        """Kalan tutar."""
        return max(Decimal("0"), self.target_amount - self.current_amount)

    @property
    def is_achieved(self) -> bool:
        """Hedef tamamlandı mı?"""
        return self.current_amount >= self.target_amount


# ============================================================
# Expense
# ============================================================
class Expense(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Harcama kayıtları.

    Manuel veya banka API'si üzerinden otomatik girilebilir.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Expense Info =====
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)

    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    merchant: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Satıcı/işyeri adı",
    )

    # ===== Date =====
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ===== Source =====
    source: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        nullable=False,
        comment="manual, mock_bank, receipt_ocr, vs.",
    )

    # ===== Optional Card =====
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_cards.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        Index("ix_expenses_user_category", "user_id", "category"),
    )


# ============================================================
# Budget
# ============================================================
class Budget(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kategori bazlı aylık bütçe limitleri.

    Aylık reset edilir, BudgetHistory'de geçmişi saklanır.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"),
        nullable=False,
    )

    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_spent: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # ===== Alert Thresholds =====
    alert_at_percentage: Mapped[int] = mapped_column(
        default=80,
        nullable=False,
        comment="Yüzde kaçta uyarı versin? (50, 75, 80, 90, 100)",
    )
    last_alert_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("monthly_limit > 0", name="monthly_limit_positive"),
        CheckConstraint(
            "alert_at_percentage >= 0 AND alert_at_percentage <= 100",
            name="alert_at_percentage_range",
        ),
        Index(
            "uq_budgets_user_category",
            "user_id",
            "category",
            unique=True,
        ),
    )

    @property
    def usage_percentage(self) -> float:
        """Kullanım yüzdesi (%)."""
        if self.monthly_limit == 0:
            return 0.0
        return float(self.current_spent / self.monthly_limit * 100)

    @property
    def is_over_threshold(self) -> bool:
        """Uyarı eşiğini geçti mi?"""
        return self.usage_percentage >= self.alert_at_percentage


# ============================================================
# Recurring Payment (Periyodik Ödemeler)
# ============================================================
class RecurringPayment(Base, IDMixin, TimestampMixin, SoftDeleteMixin, SerializationMixin):
    """
    Periyodik ödemeler — kira, fatura, abonelikler.

    Kullanıcı bunları manuel kaydeder veya banka entegrasyonuyla
    otomatik tespit edilir.

    İstediği ödemeler için bildirim alır, istemediklerini kapatabilir.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== Payment Info =====
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category"),
        nullable=False,
    )

    # ===== Schedule =====
    frequency: Mapped[RecurringFrequency] = mapped_column(
        Enum(RecurringFrequency, name="recurring_frequency"),
        default=RecurringFrequency.MONTHLY,
        nullable=False,
    )
    payment_day: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ayın hangi günü (1-31)",
    )

    # ===== Auto-payment Status =====
    is_auto_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Bankada otomatik ödemeye bağlanmış mı?",
    )

    # ===== Notifications =====
    notify_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Bildirim gönderilsin mi?",
    )
    notify_days_before: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="Kaç gün önce hatırlat?",
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "payment_day >= 1 AND payment_day <= 31",
            name="payment_day_range",
        ),
        CheckConstraint(
            "notify_days_before >= 0 AND notify_days_before <= 30",
            name="notify_days_before_range",
        ),
    )