"""
API v1 Main Router.

Tüm v1 endpoint'leri bu router altında toplanır.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health, recommendation

api_router = APIRouter()

# Sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(recommendation.router)

# Sonradan:
# api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])