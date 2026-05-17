"""
StrategyAgent — Final Sentez Agent'ı.

5 agent çıktısını birleştirir, kullanıcıya NET tavsiye verir.

PATTERN: Persona-Aware Multi-Source Synthesis
TIER: Gemini-2.5-Pro (en güçlü model, kritik sentez)

INPUT:
- ConsultantAgent: needs
- ResearchAgent v3: top 4 + 6 boyut analiz
- MarketAgent: fiyat + satıcı
- FinanceAgent: cash flow + uyarılar
- TCOAgent v3: elektrik + servis + aksesuar

OUTPUT:
- Persona tespit
- Ana ürün önerisi (1)
- Alternatifler (1-3)
- Eylem planı (3-7 adım)
- Uyarılar (sentez)
- Final empatik mesaj (Türkçe)
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_gemini_model,
)
from app.agents.prompts import STRATEGY_AGENT_PROMPT
from app.agents.schemas import StrategyOutput
from app.agents.state import AgentState


class StrategyAgent(BaseAgent):
    """
    Final sentez agent'ı.

    5 agent verisi alır, kullanıcıya tek net tavsiye verir.
    Pro tier (gemini-2.5-pro) kullanır - kritik sentez.
    """

    @property
    def name(self) -> str:
        return "strategy"

    @property
    def description(self) -> str:
        return (
            "Final sentez — 5 agent çıktısını birleştirir, "
            "persona-aware ana ürün tavsiyesi + eylem planı + uyarılar."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """5 agent verisi → sentez."""
        # Inputs
        needs = state.get("needs_analysis", {})
        research = state.get("research_intel", {})
        market = state.get("market_intel", {})
        finance = state.get("finance_analysis", {})
        tco = state.get("tco_analysis", {})
        user_context = state.get("user_context", {})

        # Eksik veri kontrol
        if not research or not market:
            self.logger.warning(
                "strategy_missing_input",
                has_research=bool(research),
                has_market=bool(market),
            )
            return self._build_fallback_response(state, "Yetersiz veri")

        self.logger.info(
            "strategy_started",
            has_finance=bool(finance),
            has_tco=bool(tco),
            research_count=len(research.get("top_evaluations", [])),
            market_count=len(market.get("products", [])),
        )

        # Prompt oluştur
        prompt = self._build_prompt(
            needs=needs,
            research=research,
            market=market,
            finance=finance,
            tco=tco,
            user_context=user_context,
        )

        # LLM call (Pro tier)
        try:
            model = get_gemini_model(
                tier=ModelTier.PRO,  # En güçlü model
                temperature=0.4,  # Yaratıcılık + tutarlılık dengesi
                json_mode=True,
            )

            messages = [HumanMessage(content=prompt)]
            response = await self._invoke_with_retry(model, messages)
            raw = self._extract_text(response)

            # Parse
            parsed = self._parse_json_safely(raw)

            if not parsed:
                self.logger.warning("strategy_parse_failed")
                return self._build_fallback_response(state, "JSON parse hatası")

            # Validate
            try:
                output = StrategyOutput(**parsed)
            except Exception as exc:
                self.logger.warning(
                    "strategy_validation_failed",
                    error=str(exc)[:300],
                )
                # Repair attempt
                parsed = self._defansive_fill(parsed, research, market)
                output = StrategyOutput(**parsed)

            self.logger.info(
                "strategy_completed",
                persona=output.persona_detected,
                recommended=output.recommended_product.name[:50],
                alternatives_count=len(output.alternatives),
                actions_count=len(output.action_plan),
                warnings_count=len(output.warnings),
                confidence=output.confidence,
            )

            return self.update_state(
                state,
                final_strategy=output.model_dump(),
                current_agent=self.name,
            )

        except Exception as exc:
            self.logger.error(
                "strategy_failed",
                error=str(exc)[:300],
            )
            return self._build_fallback_response(state, str(exc)[:200])

    # ============================================================
    # Build Prompt
    # ============================================================
    def _build_prompt(
        self,
        needs: dict,
        research: dict,
        market: dict,
        finance: dict,
        tco: dict,
        user_context: dict,
    ) -> str:
        """Prompt'u doldur — kategoriye göre özet ile."""
        def compact(data: dict, limit: int = 5000) -> str:
            return json.dumps(data, ensure_ascii=False, indent=2)[:limit]

        # TCO ve Finance için manuel özet (önemli alanlar garanti)
        tco_summary = self._summarize_tco(tco) if tco else "TCO analizi yok"
        finance_summary = (
            self._summarize_finance(finance)
            if finance
            else "Finansal profil paylaşılmadı"
        )

        return STRATEGY_AGENT_PROMPT.format(
            user_context=compact(user_context, 1500) if user_context else "Bilgi yok",
            needs_analysis=compact(needs, 1500) if needs else "Bilgi yok",
            research_intel=compact(research, 6000),
            market_intel=compact(market, 4000),
            finance_analysis=finance_summary,
            tco_analysis=tco_summary,
        )

    def _summarize_tco(self, tco: dict) -> str:
        """TCO için anahtar bilgileri Türkçe metin olarak özetle."""
        if not tco:
            return "TCO analizi yok"

        bd = tco.get("breakdown", {})
        service = tco.get("service_reliability") or {}
        accessories = tco.get("accessories_recommended", [])
        data_sources = tco.get("data_sources", {})

        parts = []

        # Ürün + alış
        parts.append(f"Ürün: {tco.get('product_name', 'N/A')}")
        parts.append(f"Alış fiyatı: {bd.get('purchase_price', 0):,.0f} TL (GERÇEK - MarketAgent)")

        # Enerji
        parts.append(
            f"Enerji etiketi: {bd.get('energy_label', 'unknown')} "
            f"(kaynak: {data_sources.get('energy_label_source', 'N/A')})"
        )
        parts.append(
            f"Yıllık tüketim: {bd.get('annual_kwh_min', 0):.0f}-"
            f"{bd.get('annual_kwh_max', 0):.0f} kWh "
            f"(ortalama {bd.get('annual_kwh_avg', 0):.0f}) [EU 2021 standardı]"
        )
        parts.append(f"kWh fiyatı: {bd.get('kwh_price_try', 0):.2f} TL (EPDK 2026)")
        parts.append(
            f"5-yıl elektrik aralığı: {bd.get('electricity_5yr_min', 0):,.0f}-"
            f"{bd.get('electricity_5yr_max', 0):,.0f} TL"
        )

        # SERVİS GÜVENİLİRLİĞİ (KRİTİK - eksikti!)
        if service:
            parts.append("\n=== SERVİS/ARIZA DURUMU ===")
            level = service.get('level', 'unknown')
            level_tr = {
                'low': 'AZ ŞİKAYET (iyi)',
                'medium': 'ORTA ŞİKAYET (dikkatli)',
                'high': 'ÇOK ŞİKAYET (UYARI!)',
                'unknown': 'BİLİNMİYOR',
            }.get(level, level)
            parts.append(f"Seviye: {level_tr}")

            if service.get('complaint_time_range'):
                parts.append(f"Şikayet dönemi: {service['complaint_time_range']}")

            active_12m = service.get('active_complaints_last_12m')
            if active_12m is True:
                parts.append("⚠️ Son 12 ay AKTİF şikayet var")
            elif active_12m is False:
                parts.append("✅ Son 12 ay aktif ciddi şikayet YOK")

            summary = service.get('summary', '')
            if summary:
                parts.append(f"Özet: {summary[:500]}")

            issues = service.get('common_issues', [])
            if issues:
                parts.append("Yaygın sorunlar:")
                for issue in issues[:5]:
                    parts.append(f"  • {issue}")

        # Aksesuar önerileri
        if accessories:
            parts.append(f"\n=== AKSESUAR ÖNERİLERİ ({len(accessories)}) ===")
            for a in accessories[:6]:
                importance = a.get('importance', 'optional')
                parts.append(
                    f"  - {a.get('name', '')} ({a.get('price_range', '')}) "
                    f"[{importance}]"
                )
                why = a.get('why_needed', '')
                if why:
                    parts.append(f"    Sebep: {why[:200]}")

        # DISCLAIMER (BIAS UYARI - StrategyAgent bunu warning'e koymalı)
        parts.append(
            "\n=== ÖNEMLİ DISCLAIMER ==="
        )
        parts.append(
            "Şikayet analizi sosyal medya/forumlardan derlenir. "
            "Büyük pazar payına sahip markalar görece daha çok şikayet alabilir "
            "(daha çok ürün satıldığı için). Bunu kullanıcıya HATIRLAT - "
            "tek karar kriteri olarak değil, ipucu olarak değerlendirilmeli."
        )

        return "\n".join(parts)

    def _summarize_finance(self, finance: dict) -> str:
        """Finance için anahtar bilgileri Türkçe metin olarak özetle."""
        if not finance:
            return "Finansal profil paylaşılmadı"

        parts = []

        profile_complete = finance.get("profile_complete", False)
        parts.append(f"Profil tam mı: {profile_complete}")

        if profile_complete:
            cf = finance.get("cash_flow", {})
            if cf:
                parts.append("\n=== CASH FLOW ===")
                parts.append(f"Aylık gelir: {cf.get('monthly_income', 0):,.0f} TL")
                parts.append(
                    f"Aylık toplam gider: {cf.get('monthly_total_expenses', 0):,.0f} TL"
                )
                parts.append(
                    f"Disposable income: {cf.get('disposable_income', 0):,.0f} TL/ay"
                )
                parts.append(
                    f"Borç/Gelir oranı: {cf.get('debt_to_income_ratio', 0):.2f}"
                )
                parts.append(
                    f"Sağlıklı alım kapasitesi: "
                    f"{cf.get('healthy_purchase_capacity', 0):,.0f} TL/ay"
                )

            pf = finance.get("purchase_feasibility", {})
            if pf:
                parts.append("\n=== ALIM FİZİBİLİTESİ ===")
                feasibility_tr = {
                    'rahat': 'RAHAT (sağlıklı)',
                    'zor': 'ZOR (dikkatli)',
                    'tehlikeli': 'TEHLİKELİ',
                    'imkansiz': 'YAPMA',
                    'n/a': 'Belirlenmedi',
                }.get(pf.get('feasibility', 'n/a'), pf.get('feasibility'))
                parts.append(f"Fizibilite: {feasibility_tr}")
                parts.append(f"Tavsiye: {pf.get('recommendation', 'N/A')}")
                reasoning = pf.get('reasoning', '')
                if reasoning:
                    parts.append(f"Gerekçe: {reasoning[:500]}")

                # Taksit detayları
                installments = pf.get('installment_options', [])
                if installments:
                    parts.append("\nTaksit seçenekleri:")
                    for opt in installments[:4]:
                        if isinstance(opt, dict):
                            parts.append(
                                f"  • {opt.get('months', 0)} ay: "
                                f"{opt.get('monthly_payment', 0):,.0f} TL/ay "
                                f"({opt.get('recommendation_level', 'N/A')})"
                            )

        # KRİTİK UYARILAR
        warnings = finance.get("warnings", [])
        if warnings:
            parts.append(f"\n=== FİNANS UYARILARI ({len(warnings)}) ===")
            for w in warnings:
                parts.append(f"  ⚠️ {w}")

        # Coaching özet
        coaching = finance.get("coaching_message", "")
        if coaching:
            parts.append(f"\n=== FINANCE KOÇLUĞU ÖZETİ ===")
            parts.append(coaching[:800])

        return "\n".join(parts)

    # ============================================================
    # Defensive Fill (validation hataları için)
    # ============================================================
    def _defansive_fill(
        self,
        parsed: dict,
        research: dict,
        market: dict,
    ) -> dict:
        """Eksik field'ları doldurmaya çalış."""
        # recommended_product zorunlu
        if "recommended_product" not in parsed:
            # Market'ten ilk ürünü al
            products = market.get("products", [])
            if products:
                p = products[0]
                parsed["recommended_product"] = {
                    "name": p.get("product_name", "Ürün"),
                    "brand": p.get("brand"),
                    "price_try": p.get("best_price", 0),
                    "best_seller": (
                        p.get("best_seller", {}).get("seller_name", "Bilinmiyor")
                        if isinstance(p.get("best_seller"), dict)
                        else "Bilinmiyor"
                    ),
                    "why_chosen": "MarketAgent tarafından en iyi fiyatla bulunan ürün",
                    "strengths": ["Bütçeye uygun"],
                    "considerations": [],
                }

        # Defaults
        parsed.setdefault("persona_detected", "general")
        parsed.setdefault("persona_reasoning", "Yeterli bilgi yok")
        parsed.setdefault("alternatives", [])
        parsed.setdefault("action_plan", [])
        parsed.setdefault("warnings", [])
        parsed.setdefault("final_message", "Detaylı tavsiye üretilemedi.")
        parsed.setdefault("decision_matrix_summary", "Karşılaştırma yapılamadı.")
        parsed.setdefault("confidence", 0.5)

        return parsed

    # ============================================================
    # Fallback Response
    # ============================================================
    def _build_fallback_response(
        self,
        state: AgentState,
        reason: str,
    ) -> AgentState:
        """Sentez başarısız olursa minimal output."""
        market = state.get("market_intel", {})
        products = market.get("products", [])

        if products:
            p = products[0]
            product_name = p.get("product_name", "Ürün")
            price = p.get("best_price", 0)

            output = {
                "persona_detected": "general",
                "persona_reasoning": "Sentez başarısız, varsayılan persona",
                "recommended_product": {
                    "name": product_name,
                    "brand": p.get("brand"),
                    "price_try": price,
                    "best_seller": (
                        p.get("best_seller", {}).get("seller_name", "Bilinmiyor")
                        if isinstance(p.get("best_seller"), dict)
                        else "Bilinmiyor"
                    ),
                    "why_chosen": f"MarketAgent tarafından en iyi fiyatla bulunan: {product_name}",
                    "strengths": ["Bütçeye uygun"],
                    "considerations": [
                        f"Sentez başarısız: {reason}",
                        "Detaylı analiz için yeniden deneyin",
                    ],
                },
                "alternatives": [],
                "action_plan": [
                    {
                        "order": 1,
                        "action": f"{product_name} ürününü değerlendirin",
                        "why": "Ana öneri",
                        "priority": "normal",
                    }
                ],
                "warnings": [
                    f"Final sentez başarısız ({reason})",
                    "Detaylı analiz için yeniden deneyin",
                ],
                "final_message": (
                    f"Sizin için bulduğum: {product_name} - {int(price):,} TL.\n"
                    f"Detaylı sentez oluşturulamadı."
                ),
                "decision_matrix_summary": "Karşılaştırma yapılamadı",
                "confidence": 0.3,
            }
        else:
            output = {
                "persona_detected": "general",
                "persona_reasoning": "Yetersiz veri",
                "recommended_product": {
                    "name": "Önerilemedi",
                    "brand": None,
                    "price_try": 0,
                    "best_seller": "Bilinmiyor",
                    "why_chosen": "Ürün bulunamadı",
                    "strengths": [],
                    "considerations": [reason],
                },
                "alternatives": [],
                "action_plan": [],
                "warnings": [f"Sentez başarısız: {reason}"],
                "final_message": "Üzgünüm, yeterli veri olmadığı için tavsiye veremedim.",
                "decision_matrix_summary": "Yetersiz veri",
                "confidence": 0.0,
            }

        return self.update_state(
            state,
            final_strategy=output,
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