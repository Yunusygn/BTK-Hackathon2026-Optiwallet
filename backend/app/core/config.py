"""
Application Configuration.

Pydantic Settings ile environment variables type-safe okunur.
Tüm konfigürasyon tek bir Settings sınıfından alınır.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Tüm sırlar .env dosyasından okunur. Production'da
    environment variables veya secret manager kullanılır.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ===== Application =====
    APP_NAME: str = "OptiWallet"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # ===== Gemini AI =====
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    GEMINI_MODEL_FAST: str = "gemini-2.5-flash"
    GEMINI_MODEL_PRO: str = "gemini-2.5-pro"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ===== Database (PostgreSQL) =====
    POSTGRES_USER: str = "optiwallet"
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = "optiwallet"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync PostgreSQL connection URL (Alembic için)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ===== Redis =====
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Redis connection URL."""
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ===== Security =====
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT signing key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_HASH_ROUNDS: int = 12
    ENCRYPTION_KEY: str = Field(..., min_length=32, description="AES-256 encryption key")

    # ===== OAuth =====
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/api/auth/callback/google"
    APPLE_CLIENT_ID: str = ""
    APPLE_CLIENT_SECRET: str = ""

    # ===== Email =====
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@optiwallet.app"
    EMAIL_FROM_NAME: str = "OptiWallet"

    # ===== Storage =====
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "optiwallet"
    S3_SECRET_KEY: str = Field(..., description="S3/MinIO secret key")
    S3_BUCKET: str = "optiwallet-uploads"
    S3_REGION: str = "us-east-1"

    # ===== Mock Bank API =====
    MOCK_BANK_API_URL: str = "http://mock-bank-api:8001"
    MOCK_BANK_CLIENT_ID: str = "optiwallet"
    MOCK_BANK_CLIENT_SECRET: str = "optiwallet_mock_secret_2026"

    # ===== Monitoring =====
    SENTRY_DSN: str = ""

    # ===== Rate Limiting =====
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ===== Logging =====
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # ===== Computed Properties =====
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """True if running in development environment."""
        return self.APP_ENV == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """True if running in production environment."""
        return self.APP_ENV == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins."""
        return [
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://localhost:3001",
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Settings singleton.

    `lru_cache` ile uygulamada tek bir Settings instance olur.
    Bu fonksiyon FastAPI dependency olarak kullanılır.

    Returns:
        Settings: Application configuration object.
    """
    return Settings()  # type: ignore[call-arg]


# Modül seviyesi shortcut (import edilebilir)
settings = get_settings()