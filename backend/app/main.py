"""
OptiWallet Backend — Main Application Entry Point.

FastAPI uygulamasının giriş noktası. Tüm middleware, router'lar
ve lifecycle event'leri burada konfigüre edilir.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse

from app import __version__
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

# Setup logging önce
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Startup: DB bağlantısı, cache warm-up, vs.
    Shutdown: Graceful cleanup.
    """
    # ===== Startup =====
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=__version__,
        environment=settings.APP_ENV,
        debug=settings.APP_DEBUG,
    )

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Warm up AI models
    # TODO: Verify external services

    logger.info("application_started")

    yield

    # ===== Shutdown =====
    logger.info("application_shutting_down")

    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Flush metrics

    logger.info("application_stopped")


def create_application() -> FastAPI:
    """
    Application factory.

    FastAPI instance'ını oluşturur ve konfigüre eder.
    Test edilebilirlik için factory pattern kullanılır.

    Returns:
        FastAPI: Configured FastAPI application.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered shopping advisor — BTK Hackathon 2026",
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ===== Middleware =====
    _setup_middleware(app)

    # ===== Routes =====
    _setup_routes(app)

    # ===== Exception Handlers =====
    _setup_exception_handlers(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Configure all middleware."""

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Trusted Host (production'da çok önemli)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["optiwallet.app", "*.optiwallet.app"],
        )


def _setup_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        response_description="API info",
    )
    async def root() -> dict[str, str]:
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": __version__,
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "status": "operational",
        }

    @app.get(
        "/health",
        tags=["Health"],
        summary="Health Check",
        status_code=status.HTTP_200_OK,
    )
    async def health_check() -> dict[str, str]:
        """
        Kubernetes/Docker healthcheck endpoint.

        Returns 200 OK if the service is alive.
        """
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": __version__,
        }

    @app.get(
        "/health/ready",
        tags=["Health"],
        summary="Readiness Check",
    )
    async def readiness_check() -> dict[str, str | bool]:
        """
        Readiness probe — checks all dependencies.

        Returns 200 only if all dependencies (DB, Redis, etc.) are ready.
        """
        # TODO: Check database connection
        # TODO: Check Redis connection
        # TODO: Check Gemini API availability

        return {
            "status": "ready",
            "database": True,  # TODO: implement real check
            "redis": True,  # TODO: implement real check
            "gemini": True,  # TODO: implement real check
        }

    # TODO: Mount API routers here
    # from app.api.routes import auth, chat, profile
    # app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    # app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    # app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])


def _setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Catch-all exception handler.

        Logs the exception and returns a sanitized 500 response.
        """
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "Bir hata oluştu. Lütfen tekrar deneyin.",
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
        )


# Application instance (uvicorn için)
app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_config=None,  # structlog kullanıyoruz
    )