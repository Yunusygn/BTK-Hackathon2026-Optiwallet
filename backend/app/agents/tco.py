"""
TCOAgent v3 — Lean Honesty + Grounding (Aksesuar + Servis).

PHILOSOPHY:
"Yalan söylemekten kaçınmak için MİNİMUM gerekli veri ver"

KALDIRILANLAR (yalan riski):
- Servis maliyeti rakamı (ama servis SIKLIK bilgisi Grounding'den var)
- Aksesuar TOPLAM maliyeti (ama öneri var)
- İkinci el değeri (5 yıl sonra tahmin imkansız)
- Etiket + Elektrik TOPLAM (kafa karıştırıcı)
- Aylık ortalama (yanıltıcı)

KALANLAR (gerçek + bilimsel):
- Alış fiyatı (GERÇEK - MarketAgent)
- Enerji etiketi (GERÇEK - Grounding)
- kWh fiyatı (GERÇEK - EPDK, cache'li)
- Yıllık tüketim aralığı (EU standardı)
- 5-yıl elektrik tahmini ARALIK (min-max-avg)

BONUS (Grounding'den):
- Aksesuar önerileri (kategoriye özel, 7-gün cache)
- Servis/arıza sıklığı (sikayetvar + forum, 30-gün cache)
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_grounded_model,
)
from app.agents.prompts import (
    TCO_ACCESSORIES_PROMPT,
    TCO_ENERGY_LABEL_PROMPT,
    TCO_KWH_PRICE_PROMPT,
    TCO_SERVICE_RELIABILITY_PROMPT,
)
from app.agents.schemas import (
    AccessoryRecommendation,
    ServiceReliability,
    TCOBreakdown,
    TCODataSource,
    TCOOutput,
)
from app.agents.state import AgentState
from app.core.cache import cache_get, cache_set


# ============================================================
# Cache Keys
# ============================================================
CACHE_KEY_KWH_PRICE = "turkey_kwh_price_2026"
CACHE_KEY_ACCESSORIES_PREFIX = "accessories_"
CACHE_KEY_SERVICE_PREFIX = "service_reliability_"

CACHE_TTL_SECONDS = 86400  # 24 saat (kWh fiyatı)
CACHE_TTL_ACCESSORIES = 604800  # 7 gün
CACHE_TTL_SERVICE = 86400  # 24 saat


# ============================================================
# Sabitler
# ============================================================
DEFAULT_KWH_PRICE_TRY = 2.65


# Kategori + Energy Label → Yıllık kWh ARALIĞI (min, max)
# EU 2021 etiket standardı
KWH_RANGE_BY_LABEL: dict[str, dict[str, tuple[float, float]]] = {
    "tv": {
        "A": (30, 50),
        "B": (80, 120),
        "C": (130, 180),
        "D": (190, 250),
        "E": (260, 330),
        "F": (340, 420),
        "G": (430, 500),
        "unknown": (180, 280),
    },
    "laptop": {
        "A": (30, 50),
        "B": (60, 80),
        "C": (90, 120),
        "D": (130, 160),
        "E": (170, 200),
        "F": (210, 250),
        "G": (260, 320),
        "unknown": (80, 130),
    },
    "phone": {
        "A": (5, 10),
        "B": (10, 14),
        "C": (14, 18),
        "D": (18, 22),
        "E": (22, 26),
        "F": (26, 30),
        "G": (30, 35),
        "unknown": (10, 18),
    },
    "appliance": {
        "A": (100, 150),
        "B": (150, 200),
        "C": (200, 270),
        "D": (270, 340),
        "E": (340, 420),
        "F": (420, 500),
        "G": (500, 600),
        "unknown": (250, 400),
    },
    "console": {
        "A": (60, 100),
        "B": (100, 140),
        "C": (140, 180),
        "D": (180, 220),
        "E": (220, 280),
        "F": (280, 320),
        "G": (320, 400),
        "unknown": (140, 200),
    },
    "monitor": {
        "A": (50, 80),
        "B": (80, 110),
        "C": (110, 150),
        "D": (150, 200),
        "E": (200, 250),
        "F": (250, 300),
        "G": (300, 360),
        "unknown": (100, 180),
    },
    "headphones": {
        "A": (2, 5),
        "B": (5, 8),
        "C": (8, 11),
        "D": (11, 14),
        "E": (14, 18),
        "F": (18, 22),
        "G": (22, 28),
        "unknown": (5, 10),
    },
    "_default": {
        "A": (40, 80),
        "B": (80, 130),
        "C": (130, 180),
        "D": (180, 240),
        "E": (240, 310),
        "F": (310, 390),
        "G": (390, 480),
        "unknown": (150, 260),
    },
}


# ============================================================
# TCOAgent v3
# ============================================================
class TCOAgent(BaseAgent):
    """
    Lean TCO — Sadece elektrik maliyeti tahmini.

    Felsefe: Minimum Viable Honesty.
    Bonus: Grounding ile aksesuar + servis sıklığı.
    """

    @property
    def name(self) -> str:
        return "tco"

    @property
    def description(self) -> str:
        return (
            "Lean elektrik maliyeti tahmini — EU standardı aralık + "
            "EPDK güncel kWh fiyatı + Grounding aksesuar/servis."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """Lean TCO analizi."""
        market = state.get("market_intel")
        needs = state.get("needs_analysis")

        if not market or not needs:
            self.logger.warning(
                "tco_missing_input",
                has_market=bool(market),
                has_needs=bool(needs),
            )
            return self._build_empty_response(state, "Veri eksik")

        products = market.get("products", [])
        if not products:
            return self._build_empty_response(state, "Ürün bulunamadı")

        target_product = products[0]
        product_name = target_product.get("product_name", "Ürün")
        purchase_price = target_product.get("best_price")

        if not purchase_price or purchase_price <= 0:
            return self._build_empty_response(state, "Fiyat bilinmiyor")

        category = needs.get("product_category", "_default").lower()

        self.logger.info(
            "tco_started",
            product_name=product_name[:50],
            purchase_price=purchase_price,
            category=category,
        )

        # ===== STEP 1: kWh fiyatı =====
        kwh_price, kwh_source = await self._fetch_kwh_price()

        # ===== STEP 2: Enerji etiketi =====
        energy_label, label_source = await self._fetch_energy_label(
            product_name=product_name,
            category=category,
        )

        # ===== STEP 3: Lean hesap =====
        breakdown = self._calculate_tco(
            purchase_price=float(purchase_price),
            category=category,
            energy_label=energy_label,
            kwh_price=kwh_price,
        )

        # ===== STEP 4: Aksesuar önerileri (Grounding) =====
        accessories, accessories_source = await self._fetch_accessories(
            product_name=product_name,
            category=category,
        )

        # ===== STEP 5: Servis/Arıza sıklığı (Grounding) =====
        service_reliability, service_source = await self._fetch_service_reliability(
            product_name=product_name,
            category=category,
        )

        # ===== STEP 6: Koçluk mesajı =====
        coaching = self._build_coaching_message(
            product_name=product_name,
            breakdown=breakdown,
            category=category,
            label_source=label_source,
            kwh_source=kwh_source,
            accessories=accessories,
            service_reliability=service_reliability,
        )

        # ===== Data Sources =====
        data_sources = TCODataSource(
            energy_label_source=label_source,
            kwh_price_source=kwh_source,
            accessories_source=accessories_source,
            service_reliability_source=service_source,
            kwh_price_fetched_at=datetime.now(timezone.utc).isoformat(),
        )

        # ===== OUTPUT =====
        output = TCOOutput(
            product_name=product_name,
            breakdown=breakdown,
            coaching_message=coaching,
            accessories_recommended=accessories,
            service_reliability=service_reliability,
            data_sources=data_sources,
            sources=[],
            confidence=0.85 if label_source == "grounding" else 0.65,
        )

        self.logger.info(
            "tco_completed",
            energy_label=energy_label,
            kwh_avg=breakdown.annual_kwh_avg,
            elec_min=breakdown.electricity_5yr_min,
            elec_max=breakdown.electricity_5yr_max,
        )

        return self.update_state(
            state,
            tco_analysis=output.model_dump(),
            current_agent=self.name,
        )

    # ============================================================
    # STEP 1: kWh Fiyatı
    # ============================================================
    async def _fetch_kwh_price(self) -> tuple[float, str]:
        """Türkiye güncel kWh fiyatını al (cache veya Grounding)."""
        cached = await cache_get(CACHE_KEY_KWH_PRICE)
        if cached is not None:
            return float(cached.get("value", DEFAULT_KWH_PRICE_TRY)), "cache"

        try:
            model = get_grounded_model(
                tier=ModelTier.FAST,
                temperature=0.0,
            )

            messages = [HumanMessage(content=TCO_KWH_PRICE_PROMPT)]
            response = await self._invoke_with_retry(model, messages)
            raw = self._extract_text(response)

            parsed = self._parse_json_safely(raw)
            kwh_price = parsed.get("kwh_price_try", DEFAULT_KWH_PRICE_TRY)

            if not isinstance(kwh_price, (int, float)) or kwh_price < 0.5 or kwh_price > 10:
                kwh_price = DEFAULT_KWH_PRICE_TRY

            await cache_set(
                CACHE_KEY_KWH_PRICE,
                float(kwh_price),
                ttl_seconds=CACHE_TTL_SECONDS,
            )

            return float(kwh_price), "grounding"

        except Exception as exc:
            self.logger.warning(
                "tco_kwh_fetch_failed",
                error=str(exc)[:200],
            )
            return DEFAULT_KWH_PRICE_TRY, "estimated"

    # ============================================================
    # STEP 2: Enerji Etiketi
    # ============================================================
    async def _fetch_energy_label(
        self,
        product_name: str,
        category: str,
    ) -> tuple[str, str]:
        """Spesifik ürünün enerji etiketini bul."""
        try:
            model = get_grounded_model(
                tier=ModelTier.FAST,
                temperature=0.0,
            )

            prompt = TCO_ENERGY_LABEL_PROMPT.format(
                product_name=product_name,
                category=category,
            )

            messages = [HumanMessage(content=prompt)]
            response = await self._invoke_with_retry(model, messages)
            raw = self._extract_text(response)

            parsed = self._parse_json_safely(raw)
            label = parsed.get("energy_label", "unknown")
            confidence = parsed.get("confidence", 0.0)

            label = str(label).upper().strip()
            valid_labels = ["A", "B", "C", "D", "E", "F", "G"]

            if label not in valid_labels:
                if "+++" in label:
                    label = "A"
                elif "++" in label:
                    label = "B"
                elif "+" in label:
                    label = "C"
                else:
                    label = "unknown"

            if confidence < 0.3:
                label = "unknown"

            return label, ("grounding" if label != "unknown" else "estimated")

        except Exception as exc:
            self.logger.warning(
                "tco_label_fetch_failed",
                error=str(exc)[:200],
            )
            return "unknown", "estimated"

    # ============================================================
    # STEP 3: Lean Hesap (Sadece Elektrik Aralığı)
    # ============================================================
    def _calculate_tco(
        self,
        purchase_price: float,
        category: str,
        energy_label: str,
        kwh_price: float,
    ) -> TCOBreakdown:
        """5-yıl elektrik maliyeti aralık hesabı."""
        kwh_table = KWH_RANGE_BY_LABEL.get(
            category, KWH_RANGE_BY_LABEL["_default"]
        )
        kwh_min, kwh_max = kwh_table.get(
            energy_label, kwh_table.get("unknown", (150, 250))
        )
        kwh_avg = (kwh_min + kwh_max) / 2

        electricity_5yr_min = kwh_min * kwh_price * 5
        electricity_5yr_max = kwh_max * kwh_price * 5
        electricity_5yr_avg = kwh_avg * kwh_price * 5

        return TCOBreakdown(
            purchase_price=round(purchase_price, 2),
            energy_label=energy_label,
            annual_kwh_min=round(kwh_min, 2),
            annual_kwh_max=round(kwh_max, 2),
            annual_kwh_avg=round(kwh_avg, 2),
            kwh_price_try=round(kwh_price, 2),
            electricity_5yr_min=round(electricity_5yr_min, 2),
            electricity_5yr_max=round(electricity_5yr_max, 2),
            electricity_5yr_avg=round(electricity_5yr_avg, 2),
        )

    # ============================================================
    # STEP 4: Aksesuar Önerileri (Grounding + 7 gün cache)
    # ============================================================
    async def _fetch_accessories(
        self,
        product_name: str,
        category: str,
    ) -> tuple[list[AccessoryRecommendation], str]:
        """Aksesuar önerilerini Grounding ile al."""
        cache_key = f"{CACHE_KEY_ACCESSORIES_PREFIX}{category}"

        cached = await cache_get(cache_key)
        if cached is not None:
            value = cached.get("value", [])
            try:
                accessories = [AccessoryRecommendation(**a) for a in value]
                return accessories, "cache"
            except Exception:
                pass

        try:
            model = get_grounded_model(
                tier=ModelTier.FAST,
                temperature=0.2,
            )

            prompt = TCO_ACCESSORIES_PROMPT.format(
                product_name=product_name,
                category=category,
            )

            messages = [HumanMessage(content=prompt)]
            response = await self._invoke_with_retry(model, messages)
            raw = self._extract_text(response)

            parsed = self._parse_json_safely(raw)
            accessories_raw = parsed.get("accessories", [])

            if not isinstance(accessories_raw, list) or not accessories_raw:
                return self._fallback_accessories(category), "estimated"

            accessories = []
            for a in accessories_raw[:5]:
                try:
                    accessories.append(AccessoryRecommendation(**a))
                except Exception:
                    continue

            if not accessories:
                return self._fallback_accessories(category), "estimated"

            await cache_set(
                cache_key,
                [a.model_dump() for a in accessories],
                ttl_seconds=CACHE_TTL_ACCESSORIES,
            )

            return accessories, "grounding"

        except Exception as exc:
            self.logger.warning(
                "tco_accessories_fetch_failed",
                error=str(exc)[:200],
            )
            return self._fallback_accessories(category), "estimated"

    def _fallback_accessories(self, category: str) -> list[AccessoryRecommendation]:
        """Grounding başarısız ise minimal fallback."""
        fallbacks = {
            "tv": [
                AccessoryRecommendation(
                    name="Soundbar",
                    price_range="1.500-3.000 TL",
                    why_needed="TV hoparlörleri genellikle yetersizdir",
                    importance="recommended",
                ),
                AccessoryRecommendation(
                    name="HDMI Kablo",
                    price_range="100-300 TL",
                    why_needed="Cihaz bağlantısı için",
                    importance="essential",
                ),
            ],
            "laptop": [
                AccessoryRecommendation(
                    name="Notebook Çantası",
                    price_range="300-800 TL",
                    why_needed="Taşıma ve koruma için",
                    importance="recommended",
                ),
                AccessoryRecommendation(
                    name="Harici Mouse",
                    price_range="200-1.000 TL",
                    why_needed="Uzun süreli kullanım için",
                    importance="recommended",
                ),
            ],
            "phone": [
                AccessoryRecommendation(
                    name="Kılıf",
                    price_range="100-500 TL",
                    why_needed="Düşme/çarpma koruması",
                    importance="essential",
                ),
                AccessoryRecommendation(
                    name="Ekran Koruyucu Cam",
                    price_range="100-300 TL",
                    why_needed="Ekran çatlak koruması",
                    importance="essential",
                ),
            ],
        }
        return fallbacks.get(category, [])

    # ============================================================
    # STEP 5: Servis/Arıza Sıklığı (Grounding + 30 gün cache)
    # ============================================================
    async def _fetch_service_reliability(
        self,
        product_name: str,
        category: str,
    ) -> tuple[ServiceReliability | None, str]:
        """Ürünün servis/arıza şikayet sıklığını Grounding ile al."""
        sanitized = re.sub(r"[^a-z0-9]", "_", product_name.lower())[:50]
        cache_key = f"{CACHE_KEY_SERVICE_PREFIX}{sanitized}"

        cached = await cache_get(cache_key)
        if cached is not None:
            value = cached.get("value", {})
            try:
                return ServiceReliability(**value), "cache"
            except Exception:
                pass

        try:
            model = get_grounded_model(
                tier=ModelTier.FAST,
                temperature=0.2,
            )

            prompt = TCO_SERVICE_RELIABILITY_PROMPT.format(
                product_name=product_name,
                category=category,
            )

            messages = [HumanMessage(content=prompt)]
            response = await self._invoke_with_retry(model, messages)
            raw = self._extract_text(response)

            parsed = self._parse_json_safely(raw)

            level = parsed.get("level", "unknown")
            if level not in ["low", "medium", "high", "unknown"]:
                level = "unknown"

            service = ServiceReliability(
                level=level,
                summary=parsed.get("summary", "Yeterli veri bulunamadı"),
                common_issues=parsed.get("common_issues", [])[:5],
                active_complaints_last_12m=parsed.get("active_complaints_last_12m"),
                complaint_time_range=parsed.get("complaint_time_range"),
            )

            await cache_set(
                cache_key,
                service.model_dump(),
                ttl_seconds=CACHE_TTL_SERVICE,
            )

            return service, "grounding"

        except Exception as exc:
            self.logger.warning(
                "tco_service_fetch_failed",
                error=str(exc)[:200],
            )
            return None, "estimated"

    # ============================================================
    # STEP 6: Coaching Message — Dürüst, Aralıklı, Lean
    # ============================================================
    def _build_coaching_message(
        self,
        product_name: str,
        breakdown: TCOBreakdown,
        category: str,
        label_source: str,
        kwh_source: str,
        accessories: list[AccessoryRecommendation],
        service_reliability: ServiceReliability | None,
    ) -> str:
        """Lean coaching — sadece elektrik aralığı + servis + aksesuar."""
        msg_parts = []

        # Başlık
        msg_parts.append(
            f"📊 **{product_name} için elektrik maliyeti tahmini:**\n"
        )

        # GERÇEK VERİLER
        msg_parts.append("✅ **GERÇEK VERİLER:**")
        msg_parts.append(
            f"💰 Alış fiyatı: **{int(breakdown.purchase_price):,} TL** (piyasa)"
        )

        if breakdown.energy_label != "unknown":
            msg_parts.append(
                f"⚡ Enerji etiketi: **{breakdown.energy_label}** "
                f"(ürün resmi etiketi)"
            )
        else:
            msg_parts.append(
                f"⚡ Enerji etiketi: bilinmiyor "
                f"(kategori ortalaması kullanıldı)"
            )

        kwh_source_text = "EPDK 2026 verisi" if kwh_source != "estimated" else "varsayılan"
        msg_parts.append(
            f"💡 Güncel kWh fiyatı: **{breakdown.kwh_price_try:.2f} TL** "
            f"({kwh_source_text})\n"
        )

        # BİLİMSEL TAHMİN (Aralık)
        msg_parts.append("📐 **ELEKTRİK MALİYETİ TAHMİNİ (EU enerji standardı):**")
        msg_parts.append(
            f"⚡ Yıllık tüketim: **{int(breakdown.annual_kwh_min)}-"
            f"{int(breakdown.annual_kwh_max)} kWh** "
            f"(ortalama ~{int(breakdown.annual_kwh_avg)} kWh)"
        )

        # Yıllık elektrik
        yearly_min = breakdown.electricity_5yr_min / 5
        yearly_max = breakdown.electricity_5yr_max / 5
        msg_parts.append(
            f"💸 **Yıllık elektrik:** "
            f"**{int(yearly_min):,} - {int(yearly_max):,} TL/yıl**"
        )

        # 5-yıl elektrik
        msg_parts.append(
            f"💸 **5-yıl elektrik:** "
            f"**{int(breakdown.electricity_5yr_min):,} - "
            f"{int(breakdown.electricity_5yr_max):,} TL arası**\n"
        )

        # SERVİS GÜVENİLİRLİĞİ — TARİH + DISCLAIMER
        if service_reliability and service_reliability.level != "unknown":
            level_emoji = {
                "low": "✅",
                "medium": "🟡",
                "high": "⚠️",
            }.get(service_reliability.level, "❓")

            level_text = {
                "low": "AZ ŞİKAYET",
                "medium": "ORTA ŞİKAYET",
                "high": "ÇOK ŞİKAYET — DİKKAT",
            }.get(service_reliability.level, "BİLİNMİYOR")

            msg_parts.append(
                f"🔧 **SERVİS/ARIZA DURUMU:** {level_emoji} **{level_text}**"
            )

            # Tarih bilgisi
            if service_reliability.complaint_time_range:
                msg_parts.append(
                    f"   📅 Şikayet dönemi: {service_reliability.complaint_time_range}"
                )

            # Son 12 ay aktif mi?
            if service_reliability.active_complaints_last_12m is True:
                msg_parts.append(
                    f"   ⚠️ Son 12 ay içinde AKTİF şikayet var"
                )
            elif service_reliability.active_complaints_last_12m is False:
                msg_parts.append(
                    f"   ✅ Son 12 ay aktif ciddi şikayet bulunmadı"
                )

            msg_parts.append(f"   {service_reliability.summary}")

            if service_reliability.common_issues:
                msg_parts.append("   📌 Yaygın sorunlar:")
                for issue in service_reliability.common_issues[:3]:
                    msg_parts.append(f"      • {issue}")

            # DISCLAIMER (önemli!)
            msg_parts.append(
                "\n   ℹ️ *Şikayet analizi sosyal medya/forumlardan derlenir. "
                "Büyük pazar payına sahip markalar görece daha çok şikayet "
                "alabilir (daha çok ürün satıldığı için). Tek karar kriteri "
                "olarak değil, ipucu olarak değerlendirin.*\n"
            )
        else:
            msg_parts.append(
                "🔧 **SERVİS DURUMU:** Bu model için yeterli kullanıcı verisi "
                "bulunamadı.\n"
            )

        # ŞEFFAFLIK NOTU
        msg_parts.append("ℹ️ **Bu bilgiler nasıl toplandı?**")
        msg_parts.append(
            "• Alış fiyatı ve enerji etiketi web'den çekildi (gerçek)\n"
            "• kWh fiyatı EPDK güncel verisi\n"
            "• Yıllık tüketim EU enerji etiketi standart aralığından\n"
            "• Servis bilgisi gerçek kullanıcı şikayetlerinden (sikayetvar, forumlar)\n"
        )

        # Aksesuar önerileri
        if accessories:
            msg_parts.append("🎁 **Bu ürünle birlikte alabilirsin:**")
            for a in accessories[:5]:
                importance_emoji = {
                    "essential": "⭐",
                    "recommended": "✅",
                    "optional": "💡",
                }.get(a.importance, "💡")
                msg_parts.append(
                    f"   {importance_emoji} **{a.name}** ({a.price_range})\n"
                    f"      {a.why_needed}"
                )

        return "\n".join(msg_parts)

    # ============================================================
    # Empty Response
    # ============================================================
    def _build_empty_response(
        self,
        state: AgentState,
        reason: str,
    ) -> AgentState:
        """Veri yoksa boş output."""
        output = {
            "product_name": "Ürün",
            "breakdown": {
                "purchase_price": 0,
                "energy_label": "unknown",
                "annual_kwh_min": 0,
                "annual_kwh_max": 0,
                "annual_kwh_avg": 0,
                "kwh_price_try": DEFAULT_KWH_PRICE_TRY,
                "electricity_5yr_min": 0,
                "electricity_5yr_max": 0,
                "electricity_5yr_avg": 0,
            },
            "coaching_message": f"TCO hesaplanamadı: {reason}",
            "accessories_recommended": [],
            "service_reliability": None,
            "data_sources": {
                "energy_label_source": "estimated",
                "kwh_price_source": "estimated",
                "accessories_source": "estimated",
                "service_reliability_source": "estimated",
                "kwh_price_fetched_at": None,
            },
            "sources": [],
            "confidence": 0.0,
        }

        return self.update_state(
            state,
            tco_analysis=output,
            current_agent=self.name,
        )

    # ============================================================
    # Helpers
    # ============================================================
    def _parse_json_safely(self, raw: str) -> dict:
        """JSON parse + repair fallback."""
        cleaned = self._clean_json(raw)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        try:
            parsed = repair_json(cleaned, return_objects=True)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        return {}

    def _clean_json(self, text: str) -> str:
        """JSON code fence temizle."""
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        return cleaned.strip()

    async def _invoke_with_retry(
        self,
        model: Any,
        messages: list,
        max_attempts: int = 3,
    ) -> Any:
        """Exponential backoff retry."""
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await model.ainvoke(messages)
            except Exception as exc:
                last_exc = exc
                error_str = str(exc)
                is_retriable = (
                    "503" in error_str
                    or "UNAVAILABLE" in error_str
                    or "timeout" in error_str.lower()
                )

                if not is_retriable or attempt == max_attempts:
                    raise

                wait_seconds = 2 ** attempt
                await asyncio.sleep(wait_seconds)

        if last_exc:
            raise last_exc
        raise RuntimeError("All retry attempts exhausted")

    def _extract_text(self, response: Any) -> str:
        """Response'tan text çıkar."""
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
            )
        return str(content) if content else ""