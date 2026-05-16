"""
FinanceAgent — Finans Stresi Çözücüsü.

GÖREVİ: "Param yetiyor mu, ay sonunu getirebilir miyim?" stresini çözer.

PHASE 1 (bu dosya):
- Cash flow analizi
- Mevcut borç etkisi
- Peşin vs Taksit hesabı
- Koçluk mesajı

GELECEKTEKI PHASE'LER:
- Phase 2: Banka kampanya tarama (Grounding)
- Phase 3: 5 yıllık TCO bilgilendirme

KVKK UYUMLU:
- Tüm finansal bilgi opsiyonel
- Hiçbir veri kalıcı saklanmaz
- Kullanıcı boş bırakırsa "incomplete" mode

ASLA YAPMAYACAK:
- Yatırım tavsiyesi (hisse, kripto)
- Vergi kaçırma önerisi
- Banka yönlendirmesi
- Kullanıcıyı suçlama
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_gemini_model,
)
from app.agents.prompts import (
    FINANCE_AGENT_PROMPT,
    FINANCE_INCOMPLETE_PROMPT,
)
from app.agents.schemas import (
    FinanceOutput,
)
from app.agents.state import AgentState


class FinanceAgent(BaseAgent):
    """
    Finansal koç — cash flow + borç + coaching.

    Phase 1: Manuel finansal profil ile çalışır.
    Profile yoksa generic coaching yapar.
    """

    @property
    def name(self) -> str:
        return "finance"

    @property
    def description(self) -> str:
        return (
            "Finansal koç — gelir/gider analizi, borç yükü, "
            "peşin vs taksit, empati ile koçluk."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """Cash flow + alım fizibilitesi analizi."""
        market = state.get("market_intel")
        needs = state.get("needs_analysis")
        user_context = state.get("user_context", {})

        # market_intel yoksa graceful degradation
        # (MarketAgent başarısız olduysa, finance generic coaching versin)
        if not market:
            self.logger.warning(
                "finance_no_market_data",
                reason="MarketAgent did not produce output",
            )
            return self._build_no_market_response(state, needs)

        # En iyi ürünü al (en düşük fiyatlı bütçe içi)
        products = market.get("products", [])
        if not products:
            self.logger.warning("finance_no_products")
            return self._build_no_products_response(state)

        # İlk ürünü hedef al (top recommendation)
        target_product = products[0]
        product_name = target_product.get("product_name", "Ürün")
        product_price = target_product.get("best_price", 0)

        budget_max = needs.get("budget_max") if needs else None

        # User financial profile
        financial_profile = user_context.get("financial_profile", {})
        profile_complete = self._is_profile_complete(financial_profile)

        self.logger.info(
            "finance_started",
            product_name=product_name[:50],
            product_price=product_price,
            profile_complete=profile_complete,
        )

        # Profile durumuna göre route
        if profile_complete:
            result = await self._analyze_with_profile(
                financial_profile=financial_profile,
                product_name=product_name,
                product_price=product_price,
                budget_max=budget_max,
            )
        else:
            result = await self._generic_coaching(
                product_name=product_name,
                product_price=product_price,
            )

        # Pydantic validation
        try:
            validated = FinanceOutput(**result)
        except Exception as exc:
            self.logger.error(
                "finance_validation_failed",
                error=str(exc)[:300],
            )
            raise

        self.logger.info(
            "finance_completed",
            profile_complete=validated.profile_complete,
            feasibility=(
                validated.purchase_feasibility.feasibility
                if validated.purchase_feasibility
                else "n/a"
            ),
            warnings_count=len(validated.warnings),
        )

        return self.update_state(
            state,
            finance_analysis=validated.model_dump(),
            current_agent=self.name,
        )

    # ============================================================
    # Profile Validation
    # ============================================================
    def _is_profile_complete(self, profile: dict) -> bool:
        """
        Yeterli finansal bilgi var mı?

        Minimum: monthly_income gerekli.
        Yardımcı: expenses, savings, credit_cards.
        """
        if not profile:
            return False

        income = profile.get("monthly_income")
        if not income or income <= 0:
            return False

        return True

    # ============================================================
    # Full Analysis (Profile Complete)
    # ============================================================
    async def _analyze_with_profile(
        self,
        financial_profile: dict,
        product_name: str,
        product_price: float,
        budget_max: float | None,
    ) -> dict:
        """Detaylı cash flow + fizibilite analizi."""
        # Profile'ı text'e çevir
        profile_text = self._format_profile(financial_profile)

        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=True,
            max_tokens=8192,
        )

        prompt = FINANCE_AGENT_PROMPT.format(
            user_profile_text=profile_text,
            product_name=product_name,
            product_price=int(product_price),
            budget_max=int(budget_max) if budget_max else "belirsiz",
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)

        # Parse
        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("finance_json_repair_needed")
            try:
                output = repair_json(raw, return_objects=True)
                if not isinstance(output, dict):
                    output = self._build_fallback(product_name, product_price)
            except Exception:
                output = self._build_fallback(product_name, product_price)

        # Defaults
        if "confidence" not in output:
            output["confidence"] = 0.85
        if "warnings" not in output:
            output["warnings"] = []

        return output

    # ============================================================
    # Generic Coaching (No Profile)
    # ============================================================
    async def _generic_coaching(
        self,
        product_name: str,
        product_price: float,
    ) -> dict:
        """Profile yoksa generic coaching."""
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.3,
            json_mode=True,
            max_tokens=2048,
        )

        prompt = FINANCE_INCOMPLETE_PROMPT.format(
            product_name=product_name,
            product_price=int(product_price),
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)

        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            output = {
                "profile_complete": False,
                "coaching_message": (
                    f"{product_name} için {int(product_price):,} TL ödeme yapacaksınız. "
                    "Finansal bilgilerinizi paylaşırsanız (aylık gelir, giderler), "
                    "size daha kişiselleştirilmiş tavsiye verebilirim. "
                    "Genel olarak: Acil durum fonunuzu (3 ay gider) korumaya özen gösterin, "
                    "vade farksız taksit seçeneklerini araştırın."
                ),
                "warnings": [],
                "confidence": 0.5,
            }

        output.setdefault("profile_complete", False)
        output.setdefault("warnings", [])
        output.setdefault("confidence", 0.5)
        output.setdefault("cash_flow", None)
        output.setdefault("purchase_feasibility", None)

        return output

    # ============================================================
    # Helpers
    # ============================================================
    def _format_profile(self, profile: dict) -> str:
        """Finansal profili Türkçe metne çevir."""
        lines = []

        income = profile.get("monthly_income")
        if income:
            lines.append(f"- Aylık net gelir: {int(income):,} TL")

        fixed = profile.get("monthly_fixed_expenses")
        if fixed:
            lines.append(f"- Sabit giderler (kira, fatura): {int(fixed):,} TL")

        variable = profile.get("monthly_variable_expenses")
        if variable:
            lines.append(f"- Değişken giderler: {int(variable):,} TL")

        savings = profile.get("current_savings")
        if savings is not None:
            lines.append(f"- Birikim: {int(savings):,} TL")

        loans = profile.get("consumer_loans_monthly", 0)
        if loans:
            lines.append(f"- Aylık kredi ödemesi: {int(loans):,} TL")

        # Credit cards
        cards = profile.get("credit_cards", [])
        if cards:
            lines.append("\nKredi kartları:")
            for c in cards[:5]:
                bank = c.get("bank_name", "Banka")
                limit = c.get("credit_limit", 0)
                debt = c.get("current_debt", 0)
                lines.append(
                    f"  • {bank}: Limit {int(limit):,} TL, "
                    f"Borç {int(debt):,} TL"
                )

        # Upcoming expenses
        upcoming = profile.get("upcoming_expenses", [])
        if upcoming:
            lines.append(f"\nYaklaşan giderler: {', '.join(upcoming)}")

        if not lines:
            return "Bilgi yok"

        return "\n".join(lines)

    def _build_fallback(
        self,
        product_name: str,
        product_price: float,
    ) -> dict:
        """JSON parse fail ise fallback."""
        return {
            "profile_complete": True,
            "cash_flow": {
                "monthly_income": 0,
                "monthly_total_expenses": 0,
                "disposable_income": 0,
                "current_debt_monthly": 0,
                "debt_to_income_ratio": 0,
                "healthy_purchase_capacity": 0,
            },
            "purchase_feasibility": {
                "feasibility": "zor",
                "cash_purchase": {"affordable": False, "warning": "Analiz yapılamadı"},
                "installment_options": [],
                "recommendation": "delay",
                "reasoning": "Finansal analiz yapılamadı, lütfen tekrar deneyin.",
            },
            "coaching_message": (
                f"{product_name} için {int(product_price):,} TL ödeme yapacaksınız. "
                "Detaylı analiz şu an yapılamadı."
            ),
            "warnings": ["Analiz tamamlanamadı"],
            "confidence": 0.3,
        }
    
    def _build_no_market_response(
        self,
        state: AgentState,
        needs: dict | None,
    ) -> AgentState:
        """
        MarketAgent başarısız olduğunda graceful fallback.

        ResearchAgent çıktısından fiyat tahmini al, generic coaching ver.
        """
        # Research'ten fiyat tahmini almaya çalış
        research = state.get("research_intel", {})
        top_evals = research.get("top_evaluations", []) if research else []

        if top_evals:
            first = top_evals[0]
            product_name = first.get("name", "Ürün")
            estimated_price = first.get("estimated_price_try", 0) or 0
        else:
            product_name = "Hedef ürün"
            estimated_price = needs.get("budget_max", 0) if needs else 0

        output = {
            "profile_complete": False,
            "cash_flow": None,
            "purchase_feasibility": None,
            "coaching_message": (
                f"{product_name} için yaklaşık {int(estimated_price):,} TL bütçe "
                f"ayırmanız gerekiyor.\n\n"
                f"Detaylı pazar bilgisi alınamadığı için kişiselleştirilmiş "
                f"finansal analiz yapamadım. Ancak genel kurallar:\n\n"
                f"• Acil durum fonunuzu (3 ay gider) korumaya özen gösterin\n"
                f"• Bu alım için aylık disposable income'ınızı zorlamayın\n"
                f"• Vade farksız taksit seçeneklerini araştırın\n"
                f"• Mevcut borçlarınız varsa onları önceliklendirin"
            ),
            "warnings": ["Pazar bilgisi alınamadı, tahmini fiyatla genel tavsiye"],
            "confidence": 0.4,
        }

        return self.update_state(
            state,
            finance_analysis=output,
            current_agent=self.name,
        )

    def _build_no_products_response(self, state: AgentState) -> AgentState:
        """MarketAgent ürün bulamadıysa."""
        output = {
            "profile_complete": False,
            "cash_flow": None,
            "purchase_feasibility": None,
            "coaching_message": (
                "Üzgünüm, bütçenize uygun ürün bulamadığım için "
                "finansal analiz yapamıyorum. Bütçenizi tekrar gözden "
                "geçirebilir veya kriterlerinizi esnetebilirsiniz."
            ),
            "warnings": ["Bütçeye uygun ürün bulunamadı"],
            "confidence": 0.3,
        }

        return self.update_state(
            state,
            finance_analysis=output,
            current_agent=self.name,
        )

    # ============================================================
    # Retry Logic
    # ============================================================
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
                response = await model.ainvoke(messages)
                if attempt > 1:
                    self.logger.info("call_succeeded_on_retry", attempt=attempt)
                return response
            except Exception as exc:
                last_exc = exc
                error_str = str(exc)
                is_retriable = (
                    "503" in error_str
                    or "UNAVAILABLE" in error_str
                    or "timeout" in error_str.lower()
                )

                if not is_retriable or attempt == max_attempts:
                    self.logger.error(
                        "call_failed",
                        attempt=attempt,
                        error=error_str[:200],
                    )
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