"""
Health Check Endpoints.

Production'da load balancer ve monitoring tarafından kullanılır.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check yanıtı."""

    status: str
    timestamp: datetime
    service: str = "optiwallet-backend"
    version: str = "0.1.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Servis çalışıyor mu kontrol et",
)
async def health_check() -> HealthResponse:
    """Basit health check."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )