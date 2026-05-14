"""
Profile Models.

User'ın yan tabloları:
- Profile: Kişisel bilgiler (ad, soyad, doğum tarihi, meslek, vs.)
- FinancialProfile: Mali bilgiler (gelir, gider, tasarruf hedefi)
- Preferences: Kullanıcı tercihleri (sevilen markalar, ödeme tercihi)

Mimari Karar:
- Bilgileri User tablosuna gömmek yerine ayrı tablolarda tutuyoruz.
- Sebep: User tablosu sık okunur (auth her istekte), ama profile detayları
  sadece profil sayfasında lazım. Normalization performansı artırıyor.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import IDMixin, SerializationMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


# ============================================================
# Enums
# ============================================================
class Occupation(str, enum.Enum):
    """
    Meslek kategorileri.

    Finans tavsiyelerini etkiliyor:
    - SALARIED: Düzenli gelir → uzun taksitler güvenli
    - FREELANCER: Düzensiz → peşin/kısa taksit + acil fon
    - BUSINESS_OWNER: Yüksek volatilite → likidite önemli
    - STUDENT: Düşük bütçe → ucuz alternatifler
    - RETIRED: Sabit gelir → risk almama eğilimi
    - PUBLIC_SERVANT: Stabil → konut/araba kredisi avantajlı
    - UNEMPLOYED: Tasarruf modu
    """

    SALARIED = "salaried"
    FREELANCER = "freelancer"
    BUSINESS_OWNER = "business_owner"
    STUDENT = "student"
    RETIRED = "retired"
    PUBLIC_SERVANT = "public_servant"
    UNEMPLOYED = "unemployed"
    OTHER = "other"


class MaritalStatus(str, enum.Enum):
    """
    Aile durumu.

    Tavsiye sürecini etkiliyor:
    - SINGLE: Bireysel ürünler
    - MARRIED_NO_KIDS: Çift kullanımına uygun
    - MARRIED_WITH_KIDS: Aile odaklı (TV, eğitim teknolojisi)
    - SINGLE_PARENT: Bütçe optimizasyonu öncelikli
    """

    SINGLE = "single"
    MARRIED_NO_KIDS = "married_no_kids"
    MARRIED_WITH_KIDS = "married_with_kids"
    SINGLE_PARENT = "single_parent"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Gender(str, enum.Enum):
    """Cinsiyet (opsiyonel, ürün önerilerinde kullanılır)."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class PaymentPreference(str, enum.Enum):
    """Tercih edilen ödeme yöntemi."""

    CASH = "cash"  # Peşin
    INSTALLMENT = "installment"  # Taksit
    CREDIT = "credit"  # Kredi
    MIXED = "mixed"  # Karma


# ============================================================
# Profile (Kişisel Bilgiler)
# ============================================================
class Profile(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kullanıcı kişisel bilgileri.

    User ile one-to-one ilişki.
    Tüm alanlar nullable — kullanıcı isteğine göre doldurur.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ===== Personal Info =====
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender"),
        nullable=True,
    )

    # ===== Location =====
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="İl (örn: İstanbul, Ankara)",
    )
    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="İlçe/semt",
    )
    country: Mapped[str] = mapped_column(
        String(2),
        default="TR",
        nullable=False,
        comment="ISO 3166-1 alpha-2 country code",
    )

    # ===== Lifestyle Context (AI tavsiyeleri için) =====
    occupation: Mapped[Occupation | None] = mapped_column(
        Enum(Occupation, name="occupation"),
        nullable=True,
        comment="Meslek (finans tavsiyelerini etkiler)",
    )
    occupation_detail: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Mesleğin serbest metin açıklaması",
    )
    marital_status: Mapped[MaritalStatus | None] = mapped_column(
        Enum(MaritalStatus, name="marital_status"),
        nullable=True,
    )
    number_of_children: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Çocuk sayısı (aile alışverişleri için)",
    )

    # ===== Bio =====
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kullanıcının kendi tanımı (max 500 karakter)",
    )

    __table_args__ = (
        CheckConstraint(
            "number_of_children >= 0 AND number_of_children <= 20",
            name="number_of_children_range",
        ),
    )

    @property
    def age(self) -> int | None:
        """Yaş hesabı (doğum tarihi varsa)."""
        if self.birth_date is None:
            return None
        today = date.today()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years


# ============================================================
# Financial Profile (Mali Bilgiler)
# ============================================================
class FinancialProfile(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Mali profil — bütçeleme ve tavsiye için kritik.

    Para alanları Decimal kullanır (float değil!).
    Float kullanmak finansal hataya yol açar (banker's rounding sorunu).
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ===== Income & Expenses (Aylık) =====
    monthly_income: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Aylık net gelir (TL)",
    )
    monthly_fixed_expenses: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Aylık sabit giderler (kira, faturalar, kredi)",
    )
    monthly_variable_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Aylık değişken bütçe (alışveriş, eğlence)",
    )

    # ===== Savings =====
    monthly_savings_target: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Aylık tasarruf hedefi",
    )
    yearly_savings_target: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    current_total_savings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Toplam birikim (manuel girilir veya banka API'sinden çekilir)",
    )

    # ===== Currency =====
    currency: Mapped[str] = mapped_column(
        String(3),
        default="TRY",
        nullable=False,
        comment="ISO 4217 currency code",
    )

    # ===== Risk Profile (1-10 scale) =====
    risk_tolerance: Mapped[int] = mapped_column(
        default=5,
        nullable=False,
        comment="1=çok muhafazakar, 10=çok agresif",
    )

    __table_args__ = (
        CheckConstraint(
            "monthly_income IS NULL OR monthly_income >= 0",
            name="monthly_income_non_negative",
        ),
        CheckConstraint(
            "monthly_fixed_expenses IS NULL OR monthly_fixed_expenses >= 0",
            name="monthly_fixed_expenses_non_negative",
        ),
        CheckConstraint(
            "risk_tolerance >= 1 AND risk_tolerance <= 10",
            name="risk_tolerance_range",
        ),
    )

    @property
    def monthly_disposable_income(self) -> Decimal | None:
        """Aylık harcanabilir gelir (gelir - sabit giderler)."""
        if self.monthly_income is None or self.monthly_fixed_expenses is None:
            return None
        return self.monthly_income - self.monthly_fixed_expenses

    @property
    def savings_rate(self) -> float | None:
        """
        Tasarruf oranı (%).

        Sağlıklı bir oran %20'dir (50/30/20 kuralı).
        """
        if not self.monthly_income or self.monthly_income == 0:
            return None
        if not self.monthly_savings_target:
            return 0.0
        return float(self.monthly_savings_target / self.monthly_income * 100)


# ============================================================
# User Preferences (Tercihler)
# ============================================================
class Preferences(Base, IDMixin, TimestampMixin, SerializationMixin):
    """
    Kullanıcı tercihleri.

    AI tavsiyelerini kişiselleştirmek için kullanılır.
    """

    __tablename__ = "preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ===== Brand Preferences =====
    favorite_brands: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Sevilen markalar (whitelist)",
    )
    blocked_brands: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Tercih edilmeyen markalar (blacklist)",
    )

    # ===== Platform Preferences =====
    preferred_marketplaces: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="Tercih edilen pazaryerleri (trendyol, hepsiburada, vs.)",
    )

    # ===== Shopping Preferences =====
    payment_preference: Mapped[PaymentPreference] = mapped_column(
        Enum(PaymentPreference, name="payment_preference"),
        default=PaymentPreference.MIXED,
        nullable=False,
    )
    price_quality_balance: Mapped[int] = mapped_column(
        default=5,
        nullable=False,
        comment="1=en ucuz öncelik, 10=en kalite öncelik",
    )

    # ===== Category Interests =====
    interested_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
        comment="İlgilenilen ürün kategorileri",
    )

    # ===== Custom Preferences (Extensible) =====
    custom_settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Genişletilebilir custom ayarlar",
    )

    __table_args__ = (
        CheckConstraint(
            "price_quality_balance >= 1 AND price_quality_balance <= 10",
            name="price_quality_balance_range",
        ),
    )