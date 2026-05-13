"""
Mock Bank API — Main Application.

Bu servis, Türk bankacılık sistemini simüle eder.
Production'da gerçek banka API'leriyle entegre edilecek.

⚠️ UYARI: Bu MOCK servistir, gerçek bankacılık işlemi yapmaz.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app import __version__
from app.banks import BankCode, list_banks, get_bank


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    print(f"🏦 Mock Bank API başlıyor — v{__version__}")
    print(f"🏦 {len(list_banks())} banka simüle ediliyor")
    yield
    print("🏦 Mock Bank API kapatılıyor")


app = FastAPI(
    title="Mock Bank API",
    description=(
        "OptiWallet için Türk bankacılık sistemini simüle eden servis. "
        "Production'da gerçek banka API'leri ile değiştirilecek."
    ),
    version=__version__,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Root & Health
# ============================================================
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """API root."""
    return {
        "service": "Mock Bank API",
        "version": __version__,
        "docs": "/docs",
        "warning": "Bu servis bankacılık simülasyonudur — gerçek işlem yapmaz",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Health check."""
    return {"status": "healthy", "service": "mock-bank-api"}


# ============================================================
# Bank Information
# ============================================================
@app.get(
    "/api/v1/banks",
    tags=["Banks"],
    summary="Desteklenen bankaları listele",
)
async def list_supported_banks() -> dict[str, list[dict[str, str | float | list[int]]]]:
    """
    Sistemin desteklediği tüm bankaları döner.

    Returns:
        Banka listesi (kod, isim, logo, faiz oranı, taksit seçenekleri).
    """
    banks = []
    for bank in list_banks():
        banks.append(
            {
                "code": bank.code.value,
                "name": bank.name,
                "short_name": bank.short_name,
                "logo_url": bank.logo_url,
                "primary_color": bank.primary_color,
                "interest_rate": bank.interest_rate,
                "installment_options": bank.installment_options,
                "rewards_program": bank.rewards_program,
                "points_per_lira": bank.points_per_lira,
            }
        )
    return {"banks": banks}


@app.get(
    "/api/v1/banks/{bank_code}",
    tags=["Banks"],
    summary="Banka detayını getir",
)
async def get_bank_details(bank_code: BankCode) -> dict[str, str | float | list[int]]:
    """
    Belirli bir banka hakkında detaylı bilgi döner.

    Args:
        bank_code: Banka kodu (akbank, garanti, isbank, vb.)

    Returns:
        Banka detayları.
    """
    try:
        bank = get_bank(bank_code)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank not found: {bank_code}",
        ) from None

    return {
        "code": bank.code.value,
        "name": bank.name,
        "short_name": bank.short_name,
        "logo_url": bank.logo_url,
        "primary_color": bank.primary_color,
        "interest_rate": bank.interest_rate,
        "installment_options": bank.installment_options,
        "rewards_program": bank.rewards_program,
        "points_per_lira": bank.points_per_lira,
    }


# ============================================================
# OAuth Flow (Simülasyon)
# ============================================================
@app.get(
    "/api/v1/oauth/authorize",
    tags=["OAuth"],
    summary="OAuth authorization endpoint",
)
async def oauth_authorize(
    bank_code: BankCode,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> dict[str, str]:
    """
    OAuth authorize endpoint — gerçek bankalardaki gibi.

    Production'da kullanıcı banka loginine yönlendirilecek.
    Mock'ta direkt onay simüle edilir.
    """
    # TODO: Gerçek implementasyon — kullanıcıyı login sayfasına yönlendir
    return {
        "message": "OAuth flow başlatıldı (mock)",
        "bank": bank_code.value,
        "next_step": "POST /api/v1/oauth/token to exchange code",
        "redirect_uri": redirect_uri,
        "state": state,
    }


@app.post(
    "/api/v1/oauth/token",
    tags=["OAuth"],
    summary="Access token exchange",
)
async def oauth_token(
    bank_code: BankCode,
    code: str,
    client_id: str,
    client_secret: str,
) -> dict[str, str | int]:
    """
    Authorization code'u access token ile değiş.

    Mock implementation — gerçek token üretmez.
    """
    # TODO: Gerçek JWT token üret
    return {
        "access_token": f"mock_access_token_{bank_code.value}_demo",
        "refresh_token": f"mock_refresh_token_{bank_code.value}_demo",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "accounts:read cards:read transactions:read",
    }


# ============================================================
# Accounts & Cards (Placeholder endpoints)
# ============================================================
@app.get(
    "/api/v1/accounts",
    tags=["Accounts"],
    summary="Hesapları listele (auth gerekli)",
)
async def list_accounts() -> dict[str, str]:
    """Kullanıcının hesaplarını döner."""
    return {
        "status": "not_implemented",
        "message": "Hesap listeleme endpoint'i geliştirilecek",
    }


@app.get(
    "/api/v1/cards",
    tags=["Cards"],
    summary="Kredi kartlarını listele (auth gerekli)",
)
async def list_cards() -> dict[str, str]:
    """Kullanıcının kredi kartlarını döner."""
    return {
        "status": "not_implemented",
        "message": "Kart listeleme endpoint'i geliştirilecek",
    }


@app.get(
    "/api/v1/transactions",
    tags=["Transactions"],
    summary="İşlemleri listele (auth gerekli)",
)
async def list_transactions() -> dict[str, str]:
    """Kullanıcının son işlemlerini döner."""
    return {
        "status": "not_implemented",
        "message": "İşlem listeleme endpoint'i geliştirilecek",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)  # noqa: S104