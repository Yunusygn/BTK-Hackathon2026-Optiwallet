"""
ResearchAgent v2 — Multi-Criteria Decision Analysis.

Consumer Reports + Wirecutter + akademik MCDA çerçevesi.

PATTERN: 3-Step Pipeline
- Step 1: Grounded Research → Türkçe detaylı analiz (plain text + citations)
- Step 2: Format → 6-boyutlu structured JSON (json-repair fallback ile)
- Step 3: Citation Injection → gerçek URL'leri ekle

NEDEN MULTI-CRITERIA?
- "İyi/kötü" yargısı subjektif ve eksik
- Bir ürün bir kullanıcı için iyi, diğer için kötü olabilir
- Şeffaf, kişiselleştirilebilir, gerçek piyasa analizi standardı
- Beko paradoxu: Türkiye'de servis yıldız, global'de teknoloji mütevazı

JSON PARSE STRATEJİSİ:
LLM'ler bazen büyük/kompleks JSON'da syntax hatası yapar.
2-attempt yaklaşımı:
1. json.loads (strict) — temiz JSON için hızlı
2. json_repair (fallback) — LLM hatalarını otomatik düzeltir
   Microsoft, OpenAI, LangChain pipelinelarında kullanılır.

Üretim pattern'leri:
- Multi-step LLM pipeline (Decomposition-based prompting)
- Real Grounding citations (no hallucination)
- Exponential backoff retry
- Defensive multi-format response parsing
- 2-tier JSON parsing (strict + repair)
- Structured logging at every step
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_gemini_model,
    get_grounded_model,
)
from app.agents.prompts import (
    RESEARCH_FORMATTER_PROMPT,
    RESEARCH_GROUNDING_PROMPT,
)
from app.agents.schemas import ResearchOutput, SourceCitation
from app.agents.state import AgentState


class ResearchAgent(BaseAgent):
    """
    Multi-Criteria Decision Analysis Research Agent.

    Forum, review, profesyonel test verilerini tarayarak her marka/model
    için 6-boyutlu detaylı değerlendirme üretir.

    Output structure:
    - Per-brand/model 6-dimensional scoring
    - Turkey vs Global perspective separation
    - Strengths & cautions per item
    - Real citations from Grounding metadata
    """

    @property
    def name(self) -> str:
        return "research"

    @property
    def description(self) -> str:
        return (
            "Multi-criteria pazar araştırması — her ürünü 6 boyutta "
            "(performans, güvenilirlik, servis, fiyat, memnuniyet, uzun vade) "
            "değerlendirir, Türkiye + Global perspektif sunar."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """3-step Multi-Criteria pipeline."""
        # ===== 0. Context Hazırla =====
        needs = state.get("needs_analysis")
        if not needs:
            self.logger.error("needs_analysis_missing")
            raise ValueError(
                "ResearchAgent requires needs_analysis to run first"
            )

        category = needs.get("product_category", "unknown")
        must_haves = needs.get("must_have_features", [])
        budget_max = needs.get("budget_max")
        use_case = needs.get("use_case", "")
        currency = needs.get("budget_currency", "TRY")

        search_context = self._build_search_context(
            category=category,
            must_haves=must_haves,
            budget_max=budget_max,
            use_case=use_case,
            currency=currency,
        )

        self.logger.info(
            "research_started_v2",
            category=category,
            must_haves_count=len(must_haves),
            approach="multi_criteria_3_step",
            dimensions=6,
        )

        # ===== STEP 1: Grounded Multi-Criteria Research =====
        plain_text, citations = await self._step1_grounded_research(
            search_context
        )

        if not plain_text or len(plain_text) < 200:
            self.logger.error(
                "step1_empty_or_too_short",
                length=len(plain_text) if plain_text else 0,
            )
            raise ValueError(
                "Step 1 (grounding) returned empty or too short response"
            )

        self.logger.info(
            "step1_completed",
            text_length=len(plain_text),
            citations_count=len(citations),
            preview=plain_text[:300],
        )

        # ===== STEP 2: Format to Multi-Criteria JSON =====
        json_str = await self._step2_format_to_json(plain_text)

        # ===== 2-Attempt JSON Parse: strict → repair fallback =====
        # LLM'ler bazen syntax hatası yapar (eksik virgül, escape, vs.)
        # json-repair production-grade fix kütüphanesi
        parsed = self._parse_json_with_repair(json_str)

        # ===== STEP 3: Citation Injection =====
        parsed["sources"] = [c.model_dump() for c in citations]

        self.logger.info(
            "step3_citations_injected",
            sources_count=len(citations),
        )

        # ===== Pydantic Validation =====
        try:
            validated = ResearchOutput(**parsed)
        except ValidationError as exc:
            self.logger.error(
                "schema_validation_failed",
                errors=exc.errors(),
                parsed_preview=str(parsed)[:1000],
            )
            raise ValueError(
                f"ResearchOutput validation failed: {exc}"
            ) from exc

        # ===== State Format =====
        research_dict = {
            "consensus_summary": validated.consensus_summary,
            "evaluations": [e.model_dump() for e in validated.evaluations],
            "forum_quotes": validated.forum_quotes,
            "category_insights": validated.category_insights,
            "sources": [s.model_dump() for s in validated.sources],
            "confidence": validated.confidence,
        }

        self.logger.info(
            "research_completed_v2",
            evaluations_count=len(validated.evaluations),
            evaluated_brands=[e.name for e in validated.evaluations],
            forum_quotes_count=len(validated.forum_quotes),
            category_insights_count=len(validated.category_insights),
            sources_count=len(validated.sources),
            confidence=validated.confidence,
        )

        return self.update_state(
            state,
            research_intel=research_dict,
            current_agent=self.name,
        )

    # ============================================================
    # JSON Parser — 2-Attempt: strict + repair
    # ============================================================
    def _parse_json_with_repair(self, json_str: str) -> dict:
        """
        JSON'u önce strict parse et, fail olursa json-repair ile düzelt.

        json-repair Microsoft, OpenAI, LangChain projelerinde kullanılır.
        LLM output'undaki tipik hataları (eksik virgül, kötü escape,
        yarım kalan JSON) otomatik fix eder.
        """
        # Attempt 1: Strict parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc_strict:
            self.logger.warning(
                "json_parse_strict_failed_trying_repair",
                error=str(exc_strict),
                raw_preview=json_str[:300],
            )

        # Attempt 2: Repair + parse
        try:
            repaired = repair_json(json_str, return_objects=True)

            if not isinstance(repaired, dict):
                raise ValueError(
                    f"repair_json returned {type(repaired).__name__}, "
                    f"expected dict"
                )

            self.logger.info(
                "json_parse_succeeded_with_repair",
                fields_recovered=list(repaired.keys()),
            )
            return repaired

        except Exception as exc_repair:
            self.logger.error(
                "json_parse_failed_both_strict_and_repair",
                repair_error=str(exc_repair),
                raw_preview=json_str[:500],
            )
            raise ValueError(
                f"Step 2 returned invalid JSON (repair also failed): "
                f"{exc_repair}"
            ) from exc_repair

    # ============================================================
    # Step 1: Grounded Research → Plain Text + Citations
    # ============================================================
    async def _step1_grounded_research(
        self,
        search_context: str,
    ) -> tuple[str, list[SourceCitation]]:
        """Gemini Grounding ile detaylı Türkçe analiz."""
        model = get_grounded_model(
            tier=ModelTier.FAST,
            temperature=0.3,
            json_mode=False,
        )

        messages = [
            SystemMessage(content=RESEARCH_GROUNDING_PROMPT),
            HumanMessage(content=search_context),
        ]

        response = await self._invoke_with_retry(model, messages)
        plain_text = self._extract_text(response)
        citations = self._extract_citations_from_grounding(response)

        return plain_text, citations

    # ============================================================
    # Step 2: Plain Text → Structured JSON
    # ============================================================
    async def _step2_format_to_json(self, plain_text: str) -> str:
        """Detaylı analizi 6-boyutlu JSON'a çevir."""
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=True,
            max_tokens=16384,  # Multi-criteria için bol space
        )

        messages = [
            SystemMessage(content=RESEARCH_FORMATTER_PROMPT),
            HumanMessage(content=plain_text),
        ]

        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)
        return self._extract_json(raw)

    # ============================================================
    # Helper: Extract Citations from Grounding Metadata
    # ============================================================
    def _extract_citations_from_grounding(
        self,
        response: Any,
    ) -> list[SourceCitation]:
        """Grounding metadata'sından gerçek URL'leri çıkar."""
        try:
            kwargs = response.additional_kwargs or {}
            metadata = kwargs.get("grounding_metadata") or kwargs.get(
                "groundingMetadata"
            )

            if not metadata:
                metadata = (
                    response.response_metadata.get("grounding_metadata")
                    if hasattr(response, "response_metadata")
                    else None
                )

            if not metadata:
                self.logger.warning(
                    "no_grounding_metadata",
                    additional_kwargs_keys=list(kwargs.keys()),
                )
                return []

            chunks = metadata.get("grounding_chunks") or metadata.get(
                "groundingChunks", []
            )

            if not chunks:
                self.logger.warning("no_grounding_chunks")
                return []

            citations = []
            for chunk in chunks:
                web_info = chunk.get("web") or {}
                uri = web_info.get("uri") or web_info.get("url", "")
                title = web_info.get("title", "")

                if not uri:
                    continue

                source_type = self._detect_source_type(uri, title)

                citation = SourceCitation(
                    title=title or self._extract_domain(uri),
                    url=uri,
                    source_type=source_type,
                    snippet=None,
                )
                citations.append(citation)

            return citations[:30]

        except Exception as exc:
            self.logger.warning(
                "citation_extraction_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return []

    def _detect_source_type(self, url: str, title: str) -> str:
        """URL ve title'dan source type tahmin et."""
        url_lower = url.lower()

        forum_keywords = [
            "donanimhaber",
            "technopat",
            "sikayetvar",
            "eksisozluk",
            "forum",
            "discuss",
            "reddit",
        ]
        if any(kw in url_lower for kw in forum_keywords):
            return "forum"

        if "youtube" in url_lower or "video" in url_lower:
            return "video"

        review_keywords = [
            "rtings",
            "techradar",
            "tomshardware",
            "cnet",
            "wirecutter",
            "review",
        ]
        if any(kw in url_lower for kw in review_keywords):
            return "review"

        if "blog" in url_lower or "medium" in url_lower:
            return "blog"

        ecommerce_keywords = [
            "trendyol",
            "hepsiburada",
            "amazon",
            "n11",
            "vatan",
            "teknosa",
        ]
        if any(kw in url_lower for kw in ecommerce_keywords):
            return "ecommerce"

        return "web"

    def _extract_domain(self, url: str) -> str:
        """URL'den domain ismi çıkar."""
        try:
            match = re.match(r"https?://(?:www\.)?([^/]+)", url)
            if match:
                return match.group(1)
        except Exception:
            pass
        return url[:50]

    # ============================================================
    # Helper: Invoke with Retry
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
                    self.logger.info(
                        "call_succeeded_on_retry",
                        attempt=attempt,
                    )
                return response

            except Exception as exc:
                last_exc = exc
                error_str = str(exc)

                is_retriable = (
                    "503" in error_str
                    or "UNAVAILABLE" in error_str
                    or "overload" in error_str.lower()
                    or "timeout" in error_str.lower()
                    or "connection" in error_str.lower()
                )

                if not is_retriable or attempt == max_attempts:
                    self.logger.error(
                        "call_failed",
                        attempt=attempt,
                        is_retriable=is_retriable,
                        error=error_str,
                        error_type=type(exc).__name__,
                    )
                    raise

                wait_seconds = 2 ** attempt
                self.logger.warning(
                    "call_retry",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    wait_seconds=wait_seconds,
                    error_preview=error_str[:200],
                )
                await asyncio.sleep(wait_seconds)

        if last_exc:
            raise last_exc
        raise RuntimeError("All retry attempts exhausted")

    # ============================================================
    # Helper: Build Search Context
    # ============================================================
    def _build_search_context(
        self,
        category: str,
        must_haves: list[str],
        budget_max: Any,
        use_case: str,
        currency: str,
    ) -> str:
        """Arama context'ini Türkçe doğal dilde hazırla."""
        features = ", ".join(must_haves) if must_haves else "özel kriter yok"
        budget = (
            f"{budget_max} {currency}" if budget_max else "esnek bütçe"
        )

        return (
            f"Ürün kategorisi: {category}\n"
            f"Olmazsa olmaz özellikler: {features}\n"
            f"Bütçe: {budget}\n"
            f"Kullanım amacı: {use_case}\n\n"
            f"Bu kriterler doğrultusunda en uygun 3-4 marka/modeli "
            f"6 boyutta detaylı analiz et. Türkiye + Global perspektif "
            f"farkını mutlaka açıkla."
        )

    # ============================================================
    # Helper: Extract Text from Response (Multi-format)
    # ============================================================
    def _extract_text(self, response: Any) -> str:
        """Response'tan text extract et (defensive)."""
        content = response.content

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif "text" in block:
                        text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts).strip()

        kwargs = response.additional_kwargs or {}
        if "text" in kwargs:
            return kwargs["text"]

        return str(content) if content else ""

    # ============================================================
    # Helper: Extract JSON from Text
    # ============================================================
    def _extract_json(self, text: str) -> str:
        """Text'ten JSON kısmını çıkar."""
        json_block = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            re.DOTALL,
        )
        if json_block:
            return json_block.group(1).strip()

        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            return text[first_brace : last_brace + 1].strip()

        return text.strip()