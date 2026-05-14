"""
LangGraph Shared State.

Tüm agent'lar bu state üzerinde çalışır:
- Bir agent state'i okur
- İşini yapar
- State'i günceller (immutable update)
- Sonraki agent okur

Bu pattern, multi-agent orchestration'ın temelidir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ============================================================
# Enums
# ============================================================
class AgentStatus(str, Enum):
    """Bir agent'ın çalışma durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Tüm workflow'un durumu."""

    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    AUDITOR_REJECTED = "auditor_rejected"  # Reflexion loop
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# Sub-States (her agent'ın kendi çıktısı)
# ============================================================
class NeedsAnalysis(TypedDict, total=False):
    """Needs Analysis Agent çıktısı."""

    raw_query: str  # Kullanıcının orijinal mesajı

    # Ürün kategorisi
    product_category: str  # "tv", "laptop", "telefon", vs.
    subcategory: str | None  # "smart_tv", "gaming_laptop", vs.

    # Teknik kriterler
    must_have_features: list[str]  # "55_inch", "4k", "smart"
    nice_to_have_features: list[str]  # "hdr", "dolby_atmos"
    deal_breakers: list[str]  # "lcd_only", "below_60hz"

    # Bütçe
    budget_min: Decimal | None
    budget_max: Decimal | None
    budget_currency: str

    # Kullanım amacı
    use_case: str  # "family_movie_watching"
    user_context: dict  # extra info

    # Aciliyet
    is_urgent: bool
    deadline_days: int | None


class MarketIntel(TypedDict, total=False):
    """Market Agent çıktısı (anlık fiyatlar, kuponlar)."""

    products_found: list[dict]
    price_range: dict  # {"min": 15000, "max": 35000, "avg": 22000}
    available_coupons: list[dict]
    flash_sales: list[dict]
    sources: list[dict]
    queried_at: datetime


class ResearchIntel(TypedDict, total=False):
    """Research Agent çıktısı (forum, review, video)."""

    consensus_summary: str  # AI özet
    pros: list[str]
    cons: list[str]
    top_brands: list[str]
    avoid_brands: list[str]
    expert_picks: list[dict]
    forum_quotes: list[dict]  # Forum'dan alıntılar
    sources: list[dict]


class FinanceAnalysis(TypedDict, total=False):
    """Finance Agent çıktısı (bütçe, kart, taksit)."""

    budget_feasibility: dict
    recommended_cards: list[dict]
    installment_options: list[dict]
    monthly_impact: Decimal | None
    goal_impact: list[dict]  # Hangi mali hedefler etkilenir
    warnings: list[str]


class FinalRecommendation(TypedDict, total=False):
    """Strategy Agent'in nihai çıktısı."""

    primary_product: dict
    alternatives: list[dict]
    reasoning: str
    confidence_score: float  # 0.0 - 1.0


class VerificationResult(TypedDict, total=False):
    """Verifier Agent çıktısı."""

    is_factually_correct: bool
    issues_found: list[str]
    corrections_applied: list[str]


class AuditResult(TypedDict, total=False):
    """Auditor Agent çıktısı (Reflexion)."""

    is_approved: bool
    rejection_reasons: list[str]
    suggested_improvements: list[str]
    confidence_score: float


# ============================================================
# Main Workflow State
# ============================================================
class AgentState(TypedDict, total=False):
    """
    Shared state — tüm agent'lar bunu okur ve günceller.

    `total=False` çünkü her field her aşamada dolu değil.
    """

    # ===== Identity =====
    user_id: str | None  # Misafir mod için None
    conversation_id: str | None
    session_id: str

    # ===== Input =====
    user_query: str
    user_context: dict  # User profile, financial profile, preferences

    # ===== Messages (LangChain history) =====
    messages: Annotated[list[BaseMessage], add_messages]

    # ===== Agent Outputs =====
    needs_analysis: NeedsAnalysis | None
    market_intel: MarketIntel | None
    research_intel: ResearchIntel | None
    finance_analysis: FinanceAnalysis | None
    recommendation: FinalRecommendation | None
    verification: VerificationResult | None
    audit: AuditResult | None

    # ===== Workflow Control =====
    workflow_status: WorkflowStatus
    current_agent: str | None
    agent_history: list[dict]  # Hangi agent ne zaman çalıştı

    # ===== Reflexion Loop =====
    auditor_attempts: int  # Auditor kaç kez reddetti
    max_auditor_attempts: int  # Genelde 3

    # ===== Metadata =====
    started_at: datetime
    completed_at: datetime | None
    total_tokens_used: int
    total_duration_ms: int

    # ===== Error Handling =====
    errors: list[dict]