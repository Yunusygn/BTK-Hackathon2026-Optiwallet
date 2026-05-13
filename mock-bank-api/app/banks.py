"""
Supported Turkish Banks Registry.

Mock veritabanı için banka konfigürasyonları.
Production'da bu kısım gerçek banka API endpoint'lerine bağlanacak.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BankCode(str, Enum):
    """Turkish bank codes (BDDK standardı)."""

    AKBANK = "akbank"
    GARANTI = "garanti"
    ISBANK = "isbank"
    YAPIKREDI = "yapikredi"
    ZIRAAT = "ziraat"
    HALKBANK = "halkbank"
    VAKIFBANK = "vakifbank"
    QNB = "qnb"


@dataclass(frozen=True)
class BankInfo:
    """Banka bilgisi."""

    code: BankCode
    name: str
    short_name: str
    logo_url: str
    primary_color: str
    interest_rate: float  # Yıllık nominal faiz oranı
    installment_options: list[int]  # Maksimum taksit seçenekleri
    points_per_lira: float  # Her TL için kazanılan puan
    rewards_program: str


SUPPORTED_BANKS: dict[BankCode, BankInfo] = {
    BankCode.AKBANK: BankInfo(
        code=BankCode.AKBANK,
        name="Akbank T.A.Ş.",
        short_name="Akbank",
        logo_url="/banks/akbank.svg",
        primary_color="#E2001A",
        interest_rate=0.0349,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.5,
        rewards_program="Axess",
    ),
    BankCode.GARANTI: BankInfo(
        code=BankCode.GARANTI,
        name="Garanti BBVA",
        short_name="Garanti",
        logo_url="/banks/garanti.svg",
        primary_color="#006633",
        interest_rate=0.0379,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.4,
        rewards_program="Bonus",
    ),
    BankCode.ISBANK: BankInfo(
        code=BankCode.ISBANK,
        name="Türkiye İş Bankası",
        short_name="İş Bankası",
        logo_url="/banks/isbank.svg",
        primary_color="#003D7E",
        interest_rate=0.0359,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.3,
        rewards_program="Maximum",
    ),
    BankCode.YAPIKREDI: BankInfo(
        code=BankCode.YAPIKREDI,
        name="Yapı ve Kredi Bankası",
        short_name="Yapı Kredi",
        logo_url="/banks/yapikredi.svg",
        primary_color="#003F7F",
        interest_rate=0.0369,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.4,
        rewards_program="World",
    ),
    BankCode.ZIRAAT: BankInfo(
        code=BankCode.ZIRAAT,
        name="Ziraat Bankası",
        short_name="Ziraat",
        logo_url="/banks/ziraat.svg",
        primary_color="#C81026",
        interest_rate=0.0299,
        installment_options=[2, 3, 6, 9, 12, 18],
        points_per_lira=0.25,
        rewards_program="Bankkart",
    ),
    BankCode.HALKBANK: BankInfo(
        code=BankCode.HALKBANK,
        name="Türkiye Halk Bankası",
        short_name="Halkbank",
        logo_url="/banks/halkbank.svg",
        primary_color="#0066B3",
        interest_rate=0.0329,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.3,
        rewards_program="Paraf",
    ),
    BankCode.VAKIFBANK: BankInfo(
        code=BankCode.VAKIFBANK,
        name="VakıfBank",
        short_name="VakıfBank",
        logo_url="/banks/vakifbank.svg",
        primary_color="#FFC72C",
        interest_rate=0.0339,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.35,
        rewards_program="World",
    ),
    BankCode.QNB: BankInfo(
        code=BankCode.QNB,
        name="QNB Finansbank",
        short_name="QNB",
        logo_url="/banks/qnb.svg",
        primary_color="#62147F",
        interest_rate=0.0389,
        installment_options=[2, 3, 6, 9, 12],
        points_per_lira=0.4,
        rewards_program="CardFinans",
    ),
}


def get_bank(code: BankCode | str) -> BankInfo:
    """
    Bank bilgisini getir.

    Args:
        code: Banka kodu.

    Returns:
        BankInfo: Banka bilgisi.

    Raises:
        KeyError: Banka bulunamazsa.
    """
    if isinstance(code, str):
        code = BankCode(code.lower())
    return SUPPORTED_BANKS[code]


def list_banks() -> list[BankInfo]:
    """Tüm desteklenen bankaları listele."""
    return list(SUPPORTED_BANKS.values())