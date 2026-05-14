"""
Recommendation API Schemas.

Pydantic models for request validation and response serialization.

Frontend ile contract burada tanımlı — değiştirirsen frontend
de değişmeli (versioning ile yönetilir).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# Request Schemas
# ============================================================
class RecommendationRequest(BaseModel):
    """
    Tavsiye isteği.

    Example:
        {
            "query": "55 inç akıllı TV, 25K bütçem var, ailecek film",
            "conversation_id": null,
            "context": {}
        }
    """

    query: str = Field(
        ...,
        description="Kullanıcının doğal dil sorgusu",
        min_length=3,
        max_length=2000,
        examples=[
            "55 inç akıllı TV almak istiyorum, 25K bütçem var, ailecek film izleyeceğiz"
        ],
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Mevcut konuşmaya devam ediyorsa UUID",
    )
    context: dict = Field(
        default_factory=dict,
        description="Ek bağlam (lokasyon, mevcut cihazlar, vs.)",
    )


# ============================================================
# Response Schemas
# ============================================================
class NeedsAnalysisResponse(BaseModel):
    """NeedsAnalysisAgent çıktısı (API formatı)."""

    raw_query: str
    product_category: str
    subcategory: str | None
    must_have_features: list[str]
    nice_to_have_features: list[str]
    deal_breakers: list[str]
    budget_min: Decimal | None
    budget_max: Decimal | None
    budget_currency: str
    use_case: str
    user_context: dict
    is_urgent: bool
    deadline_days: int | None


class AgentExecutionInfo(BaseModel):
    """Bir agent'ın çalışma metadata'sı."""

    agent: str
    status: str
    started_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    error: str | None = None


class WorkflowMetadata(BaseModel):
    """Workflow execution metadata."""

    session_id: str
    workflow_status: str
    total_duration_ms: int
    agent_count: int
    agents_executed: list[AgentExecutionInfo]
    started_at: datetime
    completed_at: datetime | None
    error_count: int = 0


class RecommendationResponse(BaseModel):
    """
    Tavsiye yanıtı.

    Şu an: sadece needs_analysis.
    Sonradan: research, market, finance, recommendation eklenecek.
    """

    success: bool = Field(..., description="İşlem başarılı mı")
    needs_analysis: NeedsAnalysisResponse | None = Field(
        default=None,
        description="Kullanıcı isteğinin yapılandırılmış analizi",
    )
    metadata: WorkflowMetadata = Field(
        ...,
        description="Execution metadata (debugging için)",
    )
    errors: list[dict] = Field(
        default_factory=list,
        description="Hata varsa detaylar",
    )


# ============================================================
# Streaming Event Schemas (SSE için sonradan)
# ============================================================
class StreamEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: str = Field(
        ...,
        description="Event tipi: 'agent_started', 'agent_completed', 'done', 'error'",
    )
    agent: str | None = None
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now())