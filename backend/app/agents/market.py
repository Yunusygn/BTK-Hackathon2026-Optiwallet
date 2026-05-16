"""
MarketAgent — Piyasa Stresi Çözücüsü.

GÖREVİ: "Kazıklanıyor muyum? Nerede ucuz?" stresini çözer.

PIPELINE (2-step):
1. Stage 1: Gemini Grounding ile fiyat tarama (text output)
2. Stage 2: Stage 1 sonucunu JSON formatına çevir

NEDEN 2-STEP?
Google API: Grounding + JSON mode aynı anda kullanılamaz.
"Tool use with response mime type 'application/json' is unsupported"

Çözüm: ResearchAgent v2 pattern'i — Grounding text → JSON formatter.
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
    get_grounded_model,
)
from app.agents.prompts import (
    MARKET_AGENT_GROUNDING_PROMPT,
    MARKET_AGENT_FORMATTER_PROMPT,
)
from app.agents.schemas import (
    MarketOutput,
)
from app.agents.state import AgentState


class MarketAgent(BaseAgent):
    """
    Pazar analizcisi — fiyat + satıcı + kampanya.

    2-step pipeline:
        Step 1: Grounded text (gerçek piyasa)
        Step 2: JSON formatter (yapılandırma)
    """

    @property
    def name(self) -> str:
        return "market"

    @property
    def description(self) -> str:
        return (
            "Pazar dedektifi — fiyat, satıcı, kampanya, taksit bilgisi. "
            "Türk e-ticaret pazarını gerçek zamanlı tarar."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """Pazar analizi yap (2-step)."""
        research = state.get("research_intel")
        needs = state.get("needs_analysis")

        if not research:
            raise ValueError("MarketAgent: research_intel required")

        # Top ürünleri al
        top_evaluations = research.get("top_evaluations", [])
        if not top_evaluations:
            self.logger.warning("market_no_top_products")
            empty_output = self._build_empty_output(needs)
            return self.update_state(
                state,
                market_intel=empty_output,
                current_agent=self.name,
            )

        budget_max = needs.get("budget_max") if needs else None

        # Ürün listesini hazırla
        products_str = "\n".join(
            f"- {e['name']} (marka: {e.get('brand', 'N/A')}, "
            f"tahmini fiyat: {e.get('estimated_price_try', 'bilinmiyor')} TL)"
            for e in top_evaluations
        )

        self.logger.info(
            "market_started",
            product_count=len(top_evaluations),
            budget_max=budget_max,
        )

        # ===== STEP 1: Grounded research (text) =====
        market_text, citations = await self._step1_grounded_search(
            products_str=products_str,
            budget_max=budget_max,
        )

        self.logger.info(
            "market_step1_completed",
            text_length=len(market_text),
            citations_count=len(citations),
        )

        # ===== STEP 2: JSON formatter =====
        result = await self._step2_format_json(
            market_text=market_text,
            budget_max=budget_max,
        )

        # Sources inject
        result["sources"] = self._build_sources(citations)

        # Pydantic validation
        try:
            validated = MarketOutput(**result)
        except Exception as exc:
            self.logger.error(
                "market_validation_failed",
                error=str(exc)[:300],
            )
            raise

        self.logger.info(
            "market_completed",
            products_count=len(validated.products),
            confidence=validated.confidence,
        )

        return self.update_state(
            state,
            market_intel=validated.model_dump(),
            current_agent=self.name,
        )

    # ============================================================
    # STEP 1: Grounded Search (text mode)
    # ============================================================
    async def _step1_grounded_search(
        self,
        products_str: str,
        budget_max: float | None,
    ) -> tuple[str, list[dict]]:
        """
        Gemini Grounding ile gerçek piyasa verisi tara.

        json_mode=False çünkü grounding + json çakışıyor.

        Returns:
            (text_content, citations_list)
        """
        model = get_grounded_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=False,  # ✅ KRITIK: grounding ile JSON ÇAKIŞIYOR
        )

        prompt = MARKET_AGENT_GROUNDING_PROMPT.format(
            products_list=products_str,
            budget_max=int(budget_max) if budget_max else "belirsiz",
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)

        text = self._extract_text(response)
        citations = self._extract_citations(response)

        return text, citations

    # ============================================================
    # STEP 2: JSON Formatter (no grounding)
    # ============================================================
    async def _step2_format_json(
        self,
        market_text: str,
        budget_max: float | None,
    ) -> dict:
        """
        Step 1'den gelen text'i yapısal JSON'a dönüştür.

        Grounding YOK, JSON mode VAR.
        """
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=True,
            max_tokens=8192,
        )

        prompt = MARKET_AGENT_FORMATTER_PROMPT.format(
            market_text=market_text,
            budget_max=int(budget_max) if budget_max else "belirsiz",
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)

        # Parse + repair
        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("market_json_repair_needed")
            try:
                output = repair_json(raw, return_objects=True)
                if not isinstance(output, dict):
                    output = self._build_empty_dict()
            except Exception as exc:
                self.logger.error(
                    "market_parse_failed",
                    error=str(exc),
                    raw_preview=raw[:300],
                )
                output = self._build_empty_dict()

        # Confidence default
        if "confidence" not in output:
            output["confidence"] = 0.75

        return output

    # ============================================================
    # Helpers
    # ============================================================
    def _build_empty_output(self, needs: dict | None) -> dict:
        """Top ürün yoksa boş output."""
        return {
            "products": [],
            "market_summary": "Önceki adımda analiz edilen ürün bulunamadı.",
            "budget_status": {
                "user_budget": needs.get("budget_max") if needs else None,
                "in_budget_count": 0,
                "out_of_budget_count": 0,
            },
            "sources": [],
            "confidence": 0.0,
        }

    def _build_empty_dict(self) -> dict:
        """JSON parse fail ise boş dict."""
        return {
            "products": [],
            "market_summary": "Pazar bilgisi alınamadı.",
            "budget_status": {},
            "confidence": 0.3,
        }

    def _build_sources(self, citations: list[dict]) -> list[dict]:
        """Citation listesini SourceCitation formatına çevir."""
        sources = []
        for c in citations[:15]:
            sources.append({
                "title": c.get("title", "Web kaynağı")[:300],
                "url": c.get("url", ""),
                "source_type": self._detect_source_type(c.get("url", "")),
                "snippet": None,
            })
        return sources

    def _detect_source_type(self, url: str) -> str:
        """URL'den kaynak tipini tespit et."""
        url_lower = url.lower()
        if any(e in url_lower for e in [
            "trendyol", "hepsiburada", "n11", "mediamarkt",
            "amazon", "akakce", "teknosa", "vatanbilgisayar"
        ]):
            return "ecommerce"
        if "blog" in url_lower:
            return "blog"
        return "web"

    def _extract_citations(self, response: Any) -> list[dict]:
        """Grounding metadata'sından citation çıkar."""
        try:
            meta = response.response_metadata or {}
            grounding = meta.get("grounding_metadata", {})
            chunks = grounding.get("grounding_chunks", [])

            citations = []
            for chunk in chunks:
                web = chunk.get("web", {})
                if web:
                    citations.append({
                        "url": web.get("uri", ""),
                        "title": web.get("title", "Web"),
                    })
            return citations
        except Exception as exc:
            self.logger.warning("citation_extraction_failed", error=str(exc))
            return []

    def _clean_json(self, text: str) -> str:
        """JSON code fence temizle."""
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        return cleaned.strip()

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