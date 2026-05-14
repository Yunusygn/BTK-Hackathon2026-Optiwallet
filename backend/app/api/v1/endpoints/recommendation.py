"""
Recommendation Endpoints.

AI tavsiye sistemine ana giriş noktası.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.agents.workflow import create_initial_state, get_workflow
from app.core.logging import get_logger
from app.schemas.recommendation import (
    AgentExecutionInfo,
    NeedsAnalysisResponse,
    RecommendationRequest,
    RecommendationResponse,
    WorkflowMetadata,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/recommendation", tags=["Recommendation"])


@router.post(
    "/analyze",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Tavsiye Analizi",
    description=(
        "Doğal dil sorguyu analiz eder ve yapılandırılmış tavsiye üretir.\n\n"
        "**Şu an Aşama 1:** Sadece Needs Analysis agent çalışıyor.\n"
        "Diğer ajanlar (Research, Market, Finance, Strategy, Verifier, "
        "Auditor) sonraki sürümlerde eklenecek."
    ),
)
async def analyze_query(
    request: RecommendationRequest,
) -> RecommendationResponse:
    """
    Kullanıcı sorgusunu analiz et.

    Pipeline:
    1. LangGraph workflow başlat
    2. NeedsAnalysisAgent çalıştır
    3. Sonucu yapılandır
    4. Response döndür
    """
    start_time = time.time()
    session_id = str(uuid.uuid4())

    logger.info(
        "recommendation_request_received",
        session_id=session_id,
        query_length=len(request.query),
        query_preview=request.query[:80],
    )

    # ===== 1. Initial State =====
    initial_state = create_initial_state(
        user_query=request.query,
        session_id=session_id,
        conversation_id=(
            str(request.conversation_id) if request.conversation_id else None
        ),
        user_context=request.context,
    )

    # ===== 2. Workflow Execute =====
    try:
        workflow = get_workflow()
        final_state = await workflow.ainvoke(initial_state)
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "workflow_execution_failed",
            session_id=session_id,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=duration_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {exc!s}",
        ) from exc

    # ===== 3. Build Response =====
    total_duration_ms = int((time.time() - start_time) * 1000)

    # Needs analysis çıkarımı
    needs_data = final_state.get("needs_analysis")
    needs_response = (
        NeedsAnalysisResponse(**needs_data) if needs_data else None
    )

    # Agent history → execution info
    agent_history = final_state.get("agent_history", [])
    agents_executed = [
        AgentExecutionInfo(
            agent=entry.get("agent", "unknown"),
            status=entry.get("status", "unknown"),
            started_at=entry.get("started_at", ""),
            completed_at=entry.get("completed_at"),
            duration_ms=entry.get("duration_ms"),
            error=entry.get("error"),
        )
        for entry in agent_history
    ]

    # Metadata
    metadata = WorkflowMetadata(
        session_id=session_id,
        workflow_status=final_state.get("workflow_status", "completed"),
        total_duration_ms=total_duration_ms,
        agent_count=len(agents_executed),
        agents_executed=agents_executed,
        started_at=initial_state["started_at"],
        completed_at=datetime.now(timezone.utc),
        error_count=len(final_state.get("errors", [])),
    )

    response = RecommendationResponse(
        success=needs_response is not None,
        needs_analysis=needs_response,
        metadata=metadata,
        errors=final_state.get("errors", []),
    )

    logger.info(
        "recommendation_request_completed",
        session_id=session_id,
        duration_ms=total_duration_ms,
        success=response.success,
        agent_count=len(agents_executed),
    )

    return response