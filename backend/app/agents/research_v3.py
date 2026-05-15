"""
ResearchAgent v3 — Hibrit Smart Filter + Tournament.

3-AŞAMALI MIMARI (Wirecutter pattern):

AŞAMA 1: GENİŞ TARAMA
    ↓ Türkiye'deki tüm markalar bulunur (10-20 marka)
    ↓
AŞAMA 2: SMART FILTER (4 Constraint)
    ├── Bütçe
    ├── Must-haves
    ├── Exclusions
    └── Lokasyon
    ↓ 5-10 marka kalır
    ↓
AŞAMA 3: TIERED EVALUATION
    🥇 Top 4: Tam 6 boyut MCDA
    🥈 5-8: Özet
    🥉 9+: Sadece isim

Sonuç: Şeffaflık + Derinlik dengeli.

NEDEN HİBRİT?
Saf Tournament: 105 LLM call gerek, çok pahalı.
Saf Filter: Şeffaflık yok, kullanıcı "neden bu yok?" diyemez.
Hibrit: Hem hızlı hem şeffaf.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_gemini_model,
    get_grounded_model,
)
from app.agents.prompts import (
    RESEARCH_V3_STAGE1_PROMPT,
    RESEARCH_V3_STAGE3_PROMPT,
)
from app.agents.schemas import (
    AlternativeEvaluation,
    BrandMention,
    MultiCriteriaEvaluation,
    ResearchOutputV3,
    SourceCitation,
)
from app.agents.state import AgentState


class ResearchAgentV3(BaseAgent):
    """
    Hibrit Smart Filter + Tournament researcher.

    3-aşamalı pipeline ile pazar analizi + filtreleme + sıralama.
    """

    @property
    def name(self) -> str:
        return "research_v3"

    @property
    def description(self) -> str:
        return (
            "Hibrit pazar analizcisi — Wirecutter pattern. "
            "Geniş tarama + Smart filter + Tiered evaluation."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """3-aşamalı analiz."""
        needs = state.get("needs_analysis")
        if not needs:
            raise ValueError("ResearchAgentV3: needs_analysis required")

        category = needs.get("product_category", "unknown")
        budget_max = needs.get("budget_max")
        use_case = needs.get("use_case", "general")
        must_haves = needs.get("must_have_features", [])

        self.logger.info(
            "research_v3_started",
            category=category,
            budget_max=budget_max,
            use_case=use_case,
            must_haves_count=len(must_haves),
        )

        # ===== AŞAMA 1: Geniş Tarama =====
        scanned = await self._stage1_wide_scan(
            category=category,
            use_case=use_case,
            must_haves=must_haves,
        )

        all_brands = scanned.get("scanned_brands", [])
        self.logger.info(
            "stage1_completed",
            total_brands=len(all_brands),
        )

        # ===== AŞAMA 2: Smart Filter =====
        filtered_brands, market_overview_excluded = self._stage2_smart_filter(
            all_brands=all_brands,
            budget_max=budget_max,
            must_haves=must_haves,
            exclusions=[],  # Henüz kullanıcıdan exclusion almıyoruz
        )

        self.logger.info(
            "stage2_filtered",
            in_budget=len(filtered_brands),
            out_of_budget=len(market_overview_excluded),
        )

        # ===== AŞAMA 3: Tiered Evaluation =====
        output_dict = await self._stage3_tiered_evaluation(
            filtered_brands=filtered_brands,
            market_overview_excluded=market_overview_excluded,
            category=category,
            budget_max=budget_max,
            use_case=use_case,
            must_haves=must_haves,
            grounding_citations=scanned.get("citations", []),
        )

        # ===== Pydantic Validation =====
        try:
            output_dict["total_brands_scanned"] = len(all_brands)
            output_dict["brands_in_budget"] = len(filtered_brands)
            validated = ResearchOutputV3(**output_dict)
        except Exception as exc:
            self.logger.error(
                "research_v3_validation_failed",
                error=str(exc)[:300],
            )
            raise

        self.logger.info(
            "research_v3_completed",
            top_count=len(validated.top_evaluations),
            alt_count=len(validated.alternative_evaluations),
            market_count=len(validated.market_overview),
            sources_count=len(validated.sources),
        )

        return self.update_state(
            state,
            research_intel=validated.model_dump(),
            current_agent=self.name,
        )

    # ============================================================
    # AŞAMA 1: Geniş Tarama
    # ============================================================
    async def _stage1_wide_scan(
        self,
        category: str,
        use_case: str,
        must_haves: list[str],
    ) -> dict:
        """
        Tüm pazar markalarını grounding ile tara.
        """
        # NOT: get_grounded_model max_tokens parametresi almıyor
        # Default Gemini max output (8192) yeterli
        model = get_grounded_model(
            tier=ModelTier.FAST,
            temperature=0.0,
        )

        prompt = RESEARCH_V3_STAGE1_PROMPT.format(
            category=category,
            use_case=use_case or "genel",
            must_haves=", ".join(must_haves) if must_haves else "yok",
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)

        raw = self._extract_text(response)
        citations = self._extract_citations(response)

        # JSON parse
        try:
            parsed = json.loads(self._clean_json(raw))
        except json.JSONDecodeError:
            self.logger.warning("stage1_json_repair_needed")
            try:
                parsed = repair_json(self._clean_json(raw), return_objects=True)
                if not isinstance(parsed, dict):
                    parsed = {"scanned_brands": [], "category_overview": ""}
            except Exception as exc:
                self.logger.error(
                    "stage1_parse_failed",
                    error=str(exc),
                    raw_preview=raw[:300],
                )
                parsed = {"scanned_brands": [], "category_overview": ""}

        parsed["citations"] = citations
        return parsed

    # ============================================================
    # AŞAMA 2: Smart Filter (4 Constraint)
    # ============================================================
    def _stage2_smart_filter(
        self,
        all_brands: list[dict],
        budget_max: float | None,
        must_haves: list[str],
        exclusions: list[str],
    ) -> tuple[list[dict], list[dict]]:
        """
        4 constraint ile filtreleme:
        1. Bütçe
        2. Must-haves
        3. Exclusions
        4. Lokasyon (Türkiye, otomatik geçildi varsayım)

        Returns:
            (in_budget_brands, out_of_budget_brands)
        """
        in_budget = []
        out_of_budget = []

        for brand in all_brands:
            price = brand.get("estimated_price_try")
            name = brand.get("name", "Unknown")
            brand_name = brand.get("brand", "")

            # Constraint 1: Bütçe
            if budget_max and price:
                if price > budget_max * 1.1:  # %10 tolerans
                    out_of_budget.append({
                        "name": name,
                        "brand": brand_name,
                        "estimated_price_try": price,
                        "status": "out_of_budget",
                        "note": f"Tahmini fiyat {int(price)} TL (bütçe üstü)",
                    })
                    continue

            # Constraint 3: Exclusions
            if exclusions:
                if any(
                    excl.lower() in brand_name.lower() or
                    excl.lower() in name.lower()
                    for excl in exclusions
                ):
                    continue  # Tamamen atla, market_overview'a bile koyma

            # Bütçede ve exclusions'de değil → in_budget
            in_budget.append(brand)

        return in_budget, out_of_budget

    # ============================================================
    # AŞAMA 3: Tiered Evaluation
    # ============================================================
    async def _stage3_tiered_evaluation(
        self,
        filtered_brands: list[dict],
        market_overview_excluded: list[dict],
        category: str,
        budget_max: float | None,
        use_case: str,
        must_haves: list[str],
        grounding_citations: list[dict],
    ) -> dict:
        """
        Filtrelenmiş markaları sıralayıp 3 tier'a böl.
        """
        if not filtered_brands:
            # Bütçede ürün yok
            self.logger.warning("stage3_no_brands_in_budget")
            return self._build_empty_response(market_overview_excluded)

        # LLM'e gönderilecek marka listesi
        brands_list_str = "\n".join(
            f"- {b['name']} (marka: {b.get('brand', 'N/A')}, "
            f"tahmini: {b.get('estimated_price_try', 'bilinmiyor')} TL)"
            for b in filtered_brands[:15]  # Max 15 marka analiz
        )

        # Stage 3 prompt
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=True,
            max_tokens=16384,
        )

        prompt = RESEARCH_V3_STAGE3_PROMPT.format(
            filtered_brands_list=brands_list_str,
            category=category,
            budget_max=int(budget_max) if budget_max else "belirsiz",
            use_case=use_case or "genel",
            must_haves=", ".join(must_haves) if must_haves else "yok",
        )

        messages = [HumanMessage(content=prompt)]
        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)

        # Parse + repair
        try:
            output = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("stage3_json_repair_needed")
            try:
                output = repair_json(raw, return_objects=True)
                if not isinstance(output, dict):
                    output = {}
            except Exception as exc:
                self.logger.error(
                    "stage3_parse_failed",
                    error=str(exc),
                    raw_preview=raw[:300],
                )
                output = {}

        # Sources inject (deterministic)
        output["sources"] = self._build_sources(grounding_citations)

        # market_overview'a out_of_budget'i ekle
        existing_market = output.get("market_overview", [])
        if not isinstance(existing_market, list):
            existing_market = []

        # Out of budget markaları market_overview'a ekle
        for b in market_overview_excluded[:8]:  # Max 8
            existing_market.append({
                "name": b["name"],
                "status": "out_of_budget",
                "note": b["note"],
            })

        output["market_overview"] = existing_market[:15]

        return output

    # ============================================================
    # Helpers
    # ============================================================
    def _build_empty_response(
        self,
        market_overview_excluded: list[dict],
    ) -> dict:
        """Bütçede hiç ürün yoksa empty response döndür."""
        return {
            "consensus_summary": (
                "Bu bütçe ve kriterlerle Türkiye pazarında uygun ürün "
                "bulunamadı. Bütçeyi artırmak veya kriterleri esnetmek "
                "gerekiyor."
            ),
            "top_evaluations": [],
            "alternative_evaluations": [],
            "market_overview": [
                {
                    "name": b["name"],
                    "status": "out_of_budget",
                    "note": b["note"],
                }
                for b in market_overview_excluded[:15]
            ],
            "forum_quotes": [],
            "category_insights": [
                "Bu bütçe aralığında ürün bulunmadı.",
                "Bütçeyi artırmak veya kriterleri değiştirmek gerekir.",
            ],
            "sources": [],
            "confidence": 0.5,
        }

    def _build_sources(self, citations: list[dict]) -> list[dict]:
        """Grounding citation'larını SourceCitation formatına çevir."""
        sources = []
        for c in citations[:20]:  # Max 20 source
            sources.append({
                "title": c.get("title", "Web kaynağı")[:300],
                "url": c.get("url", ""),
                "source_type": self._detect_source_type(c.get("url", "")),
                "snippet": c.get("snippet", "")[:500] if c.get("snippet") else None,
            })
        return sources

    def _detect_source_type(self, url: str) -> str:
        """URL'den kaynak tipini tespit et."""
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "video"
        if "forum" in url_lower or "donanimhaber" in url_lower or "technopat" in url_lower:
            return "forum"
        if "rtings" in url_lower or "techradar" in url_lower or "wirecutter" in url_lower:
            return "review"
        if any(e in url_lower for e in ["trendyol", "hepsiburada", "amazon", "n11"]):
            return "ecommerce"
        if "blog" in url_lower:
            return "blog"
        return "web"

    def _extract_citations(self, response: Any) -> list[dict]:
        """Grounding metadata'sından citation listesi çıkar."""
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
        """Model'i exponential backoff ile çağır."""
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
                self.logger.warning(
                    "call_retry",
                    attempt=attempt,
                    wait_seconds=wait_seconds,
                )
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