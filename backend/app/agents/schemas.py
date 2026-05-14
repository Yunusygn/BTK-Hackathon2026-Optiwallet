"""
Agent Output Schemas.

Pydantic models for type-safe agent outputs.

Pattern: "Structured Output" — Gemini'nin JSON mode'unu Pydantic
ile birleştirip type safety + validation sağlıyoruz.

Bu, OpenAI/Anthropic'in "function calling" pattern'ine eşdeğer.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Enums — Limited choice fields
# ============================================================
class ProductCategory(str, Enum):
    """Desteklenen ana ürün kategorileri."""

    TV = "tv"
    LAPTOP = "laptop"
    PHONE = "phone"
    TABLET = "tablet"
    HEADPHONES = "headphones"
    SMARTWATCH = "smartwatch"
    CAMERA = "camera"
    APPLIANCE = "appliance"  # Buzdolabı, çamaşır makinesi, vs.
    GAMING = "gaming"  # Konsol, PC
    OTHER = "other"


class UrgencyLevel(str, Enum):
    """Sorgunun aciliyet seviyesi."""

    NOT_URGENT = "not_urgent"  # "İleride alacağım"
    MODERATE = "moderate"  # "Önümüzdeki ay"
    URGENT = "urgent"  # "Bugün/yarın lazım"


# ============================================================
# Main Output Schema
# ============================================================
class NeedsAnalysisOutput(BaseModel):
    """
    NeedsAnalysisAgent'in çıktı şeması.

    Gemini'nin response_mime_type=application/json modu bu şemaya
    uygun JSON üretecek.
    """

    # ============ ÜRÜN ============
    product_category: ProductCategory = Field(
        ...,
        description="Ana ürün kategorisi",
    )
    subcategory: str | None = Field(
        None,
        description="Alt kategori (örn: 'gaming_laptop', 'smart_tv')",
        max_length=50,
    )

    # ============ ÖZELLİKLER ============
    must_have_features: list[str] = Field(
        default_factory=list,
        description="Olmazsa olmaz özellikler. Snake_case (örn: '55_inch', '16gb_ram')",
        max_length=10,
    )
    nice_to_have_features: list[str] = Field(
        default_factory=list,
        description="Olsa iyi olur özellikler",
        max_length=10,
    )
    deal_breakers: list[str] = Field(
        default_factory=list,
        description="Kesinlikle istenmeyen özellikler (örn: 'lcd_only', 'plastic_body')",
        max_length=5,
    )

    # ============ BÜTÇE ============
    budget_min: Decimal | None = Field(
        None,
        description="Minimum bütçe (TRY). Belirtilmemişse None.",
        ge=0,
    )
    budget_max: Decimal | None = Field(
        None,
        description="Maksimum bütçe (TRY). Belirtilmemişse None.",
        ge=0,
    )
    budget_currency: str = Field(
        default="TRY",
        description="Para birimi (ISO 4217)",
        min_length=3,
        max_length=3,
    )

    # ============ KULLANIM ============
    use_case: str = Field(
        ...,
        description=(
            "Kullanım amacı snake_case (örn: 'family_movie_watching', "
            "'professional_video_editing', 'casual_gaming')"
        ),
        max_length=100,
    )
    user_context: dict = Field(
        default_factory=dict,
        description="Ek bağlam (audience, room_size, vs.)",
    )

    # ============ ACİLİYET ============
    urgency: UrgencyLevel = Field(
        default=UrgencyLevel.NOT_URGENT,
        description="Aciliyet seviyesi",
    )
    deadline_days: int | None = Field(
        None,
        description="Belirtilmişse: kaç gün içinde lazım",
        ge=0,
        le=365,
    )

    # ============ META ============
    confidence: float = Field(
        ...,
        description=(
            "Bu analizin güvenilirliği (0.0-1.0). "
            "Düşük confidence → kullanıcıdan daha fazla bilgi iste."
        ),
        ge=0.0,
        le=1.0,
    )
    clarification_questions: list[str] = Field(
        default_factory=list,
        description=(
            "Confidence düşükse: kullanıcıya sorulacak netleştirme soruları"
        ),
        max_length=3,
    )

    # ============ Validators ============
    @field_validator("budget_max")
    @classmethod
    def budget_max_greater_than_min(
        cls, v: Decimal | None, info
    ) -> Decimal | None:
        """budget_max >= budget_min olmalı."""
        budget_min = info.data.get("budget_min")
        if v is not None and budget_min is not None and v < budget_min:
            raise ValueError("budget_max must be >= budget_min")
        return v

    @field_validator("must_have_features", "nice_to_have_features", "deal_breakers")
    @classmethod
    def features_snake_case(cls, v: list[str]) -> list[str]:
        """Özellikleri snake_case'e normalize et."""
        return [
            feat.lower().replace(" ", "_").replace("-", "_") for feat in v
        ]