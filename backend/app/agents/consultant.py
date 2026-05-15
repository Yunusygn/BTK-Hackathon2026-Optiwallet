"""
ConsultantAgent — Kullanıcının Giriş Kapısı.

OptiWallet'in en önemli agent'ı çünkü kullanıcıyla ilk teması yapar.

3 MOD:
1. READY: İhtiyaç net → pipeline başlat
2. CLARIFICATION: 1-3 soru sor (multiple choice)
3. EDUCATIONAL: Kullanıcı bilgi istiyor → bilgi ver

PATTERN: Progressive Conversation (sohbet stili)
- Maksimum 2-3 soru (UX kuralı)
- "Bilmiyorum" seçeneği her zaman var
- Confidence-based decision tree

KRİTİK DESIGN DECISION:
LLM'in verdiği confidence'a körü körüne güvenmiyoruz.
Kendi iş kurallarımızı (Python) uyguluyoruz:
- Bütçe yoksa max 0.55 (1 soru gerek)
- Kategori yoksa max 0.20 (kategori sor)
- Hepsi varsa 0.85+ (pipeline'a geç)

Bu OptiWallet'in "Strict Budget Respect" manifestosunu
korumak için kritik.

NEDEN ÖNEMLI?
İnsanın 3 stresinden ilki "ne lazım?" stresi.
ConsultantAgent bunu çözer — kullanıcının istediğini
açıkça anlar veya soru sorarak netleştirir.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from json_repair import repair_json
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseAgent
from app.agents.gemini_client import ModelTier, get_gemini_model
from app.agents.question_bank import (
    EDUCATIONAL_CONTENT,
    QUESTION_BANK,
    ConfidenceThresholds,
)
from app.agents.schemas import (
    ClarificationOption,
    ClarificationQuestion,
    ConsultantOutput,
    NeedsAnalysisOutput,
)
from app.agents.state import AgentState


# ============================================================
# Prompt
# ============================================================
CONSULTANT_SYSTEM_PROMPT = """Sen OptiWallet'in giriş danışmanısın.

GÖREVİN:
Kullanıcının doğal dil mesajını analiz et ve şu bilgileri çıkar:

1. NIYET TIPI:
   - "transactional": Ürün arıyor (alışveriş niyeti)
   - "educational": Bilgi istiyor (özellikler, nasıl seçilir)
   - "ambiguous": Belirsiz

2. ÇIKARILABILEN BILGILER:
   - Ürün kategorisi (tv, laptop, phone, vs.)
   - Bütçe (varsa)
   - Kullanım amacı (varsa)
   - Olmazsa olmazlar (varsa)
   - Marka tercihi/hariç tutmaları

ÇIKTI FORMATI: SADECE JSON

{
  "intent_type": "transactional" | "educational" | "ambiguous",
  "category": "tv" | "laptop" | "phone" | ... | null,
  "budget_min": number | null,
  "budget_max": number | null,
  "use_case": string | null,
  "must_haves": [strings],
  "excluded_brands": [strings],
  "extracted_summary": "Kullanıcı şunu istiyor: ..."
}

KURALLAR:
- Türkçe doğal dili anla
- Bütçe varsa TL/lira/bin kelimelerini tespit et
- "5K" = 5000, "20 bin" = 20000, "25K TL" = 25000
- Edu keywords: "hangi özellik", "neye bakmalı", "anlat", "nasıl seçilir"
- DİL: Kullanıcı Türkçe yazmış ama field değerleri:
  - use_case: snake_case İngilizce ("family_movie_watching")
  - category: lowercase İngilizce ("tv", "laptop")
  - must_haves: snake_case ("55_inch", "smart_tv")
"""


class ConsultantAgent(BaseAgent):
    """
    Kullanıcının giriş kapısı. Niyeti anla, eksikse soru sor.

    Decision Tree:
        confidence >= 0.85 → READY (pipeline başlar)
        confidence >= 0.55 → 1 soru sor
        confidence >= 0.30 → 2-3 soru sor
        confidence < 0.30  → Kategori belirsiz, kategori sor

    Eğer kullanıcı "anlat", "neye bakmalı" gibi soru sorduysa
    educational mode'a geçer ve bilgi verir.
    """

    @property
    def name(self) -> str:
        return "consultant"

    @property
    def description(self) -> str:
        return (
            "Kullanıcının niyetini anlar, eksik bilgi varsa soru sorar, "
            "eğitim modunda bilgi verir."
        )

    # ============================================================
    # Main Execute
    # ============================================================
    async def _execute(self, state: AgentState) -> AgentState:
        """ConsultantAgent ana logic."""
        user_query = state.get("user_query", "").strip()

        if not user_query:
            raise ValueError("ConsultantAgent: user_query is empty")

        self.logger.info(
            "consultant_started",
            user_query_preview=user_query[:100],
        )

        # ===== 1. Gemini ile parse et =====
        parsed = await self._parse_user_query(user_query)

        intent_type = parsed.get("intent_type", "ambiguous")
        category = parsed.get("category")

        # ===== 2. KENDİ CONFIDENCE HESABIMIZ =====
        # LLM cömert davranabilir, biz kontrol ederiz
        confidence = self._calculate_real_confidence(parsed)
        parsed["confidence"] = confidence  # Override

        self.logger.info(
            "consultant_parsed",
            intent_type=intent_type,
            category=category,
            confidence=confidence,
            budget_max=parsed.get("budget_max"),
            use_case=parsed.get("use_case"),
        )

        # ===== 3. Educational Mode? =====
        if intent_type == "educational" and category:
            output = self._build_educational_response(category, parsed)
            return self.update_state(
                state,
                consultant_output=output.model_dump(),
                current_agent=self.name,
            )

        # ===== 4. Kategori belirsizse =====
        if not category or confidence < ConfidenceThresholds.CATEGORY_UNKNOWN:
            output = self._build_category_question()
            return self.update_state(
                state,
                consultant_output=output.model_dump(),
                current_agent=self.name,
            )

        # ===== 5. Confidence-based routing =====
        if confidence >= ConfidenceThresholds.READY:
            # Hazır, pipeline'a geç
            output = self._build_ready_response(parsed)
        elif confidence >= ConfidenceThresholds.NEEDS_ONE_Q:
            # 1 soru sor (en kritik eksik)
            output = self._build_one_question(category, parsed)
        else:
            # 2-3 soru sor
            output = self._build_multiple_questions(category, parsed)

        self.logger.info(
            "consultant_completed",
            mode=output.interaction_mode,
            ready=output.ready_for_pipeline,
            questions_count=len(output.clarification_questions),
        )

        return self.update_state(
            state,
            consultant_output=output.model_dump(),
            current_agent=self.name,
        )

    # ============================================================
    # Confidence Calculator (KRITIK İŞ KURALI)
    # ============================================================
    def _calculate_real_confidence(self, parsed: dict) -> float:
        """
        Gemini'nin confidence'ı yerine kendi iş kurallarımızı uygula.

        İŞ KURALI (OptiWallet manifesto):
        - Kategori yoksa: max 0.10 (kategori_unknown threshold)
        - Bütçe yoksa: max 0.55 (1 soru ile düzelir)
        - Kullanım yoksa: max 0.70 (1 soru ile düzelir)
        - Hepsi varsa: 0.85+

        Bu sayede 'bütçesi yok ama hazır' olamaz.

        Skorlama:
        - Educational mode: 1.0 (zaten bilgi modu)
        - Kategori: +0.40 (zorunlu temel)
        - Bütçe: +0.30 (kritik için kullanıcı bilgilendirme)
        - Use case: +0.20 (önemli ama default'lanabilir)
        - Must-haves: +0.10 (yardımcı)
        """
        # Educational mode için confidence 1.0 olabilir
        if parsed.get("intent_type") == "educational":
            return 1.0

        category = parsed.get("category")
        budget = parsed.get("budget_max")
        use_case = parsed.get("use_case")

        # Hiç kategori yoksa
        if not category:
            return 0.10

        # Skorlama
        score = 0.0

        # Kategori (zorunlu) → 0.40
        score += 0.40

        # Bütçe varsa → +0.30
        if budget and budget > 0:
            score += 0.30

        # Kullanım amacı varsa → +0.20
        if use_case:
            score += 0.20

        # Must-haves varsa → +0.10 (yardımcı)
        must_haves = parsed.get("must_haves", [])
        if must_haves:
            score += 0.10

        return min(score, 1.0)

    # ============================================================
    # Gemini Parse
    # ============================================================
    async def _parse_user_query(self, user_query: str) -> dict:
        """Kullanıcı mesajını LLM ile parse et."""
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.0,
            json_mode=True,
            max_tokens=2048,
        )

        messages = [
            SystemMessage(content=CONSULTANT_SYSTEM_PROMPT),
            HumanMessage(content=f"Kullanıcı mesajı:\n\n{user_query}"),
        ]

        # Retry with backoff
        response = await self._invoke_with_retry(model, messages)
        raw = self._extract_text(response)

        # Parse JSON (with repair fallback)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("consultant_json_repair_needed")
            try:
                repaired = repair_json(raw, return_objects=True)
                if isinstance(repaired, dict):
                    parsed = repaired
                else:
                    parsed = {
                        "intent_type": "ambiguous",
                        "category": None,
                        "extracted_summary": "Anlaşılamadı",
                    }
            except Exception as exc:
                self.logger.error(
                    "consultant_parse_failed",
                    error=str(exc),
                    raw_preview=raw[:300],
                )
                parsed = {
                    "intent_type": "ambiguous",
                    "category": None,
                    "extracted_summary": "Anlaşılamadı",
                }

        # ✅ NORMALIZE: must_haves snake_case, vs.
        parsed = self._normalize_parsed_output(parsed)
        return parsed

    # ============================================================
    # Output Normalizer
    # ============================================================
    def _normalize_parsed_output(self, parsed: dict) -> dict:
        """
        LLM çıktısını normalleştir.

        Sorun: LLM bazen "55 inç" bazen "55_inch" dönüyor.
        Çözüm: Tek formata getir (snake_case, lowercase).
        """
        # must_haves normalize
        must_haves = parsed.get("must_haves", [])
        if must_haves:
            parsed["must_haves"] = [
                self._normalize_feature(f) for f in must_haves if f
            ]

        # excluded_brands normalize
        excluded = parsed.get("excluded_brands", [])
        if excluded:
            parsed["excluded_brands"] = [
                b.strip().title() for b in excluded if b
            ]

        # Category lowercase
        category = parsed.get("category")
        if category:
            parsed["category"] = category.lower().strip()

        # use_case snake_case
        use_case = parsed.get("use_case")
        if use_case:
            parsed["use_case"] = (
                use_case.lower()
                .replace(" ", "_")
                .replace("-", "_")
                .strip()
            )

        return parsed

    def _normalize_feature(self, feature: str) -> str:
        """
        Özellik string'ini standartlaştır.

        Örnekler:
            "55 inç" → "55_inch"
            "smart tv" → "smart_tv"
            "4K" → "4k"
            "HDR" → "hdr"
        """
        f = feature.strip().lower()

        # Türkçe → İngilizce mapping
        replacements = {
            " inç": "_inch",
            "inç": "_inch",
            " inch": "_inch",
            " ": "_",
            "-": "_",
        }
        for tr, en in replacements.items():
            f = f.replace(tr, en)

        # Çift underscore'ları tek yap
        while "__" in f:
            f = f.replace("__", "_")

        # Baş/son underscore'ları sil
        return f.strip("_")

    # ============================================================
    # Response Builders
    # ============================================================
    def _build_ready_response(self, parsed: dict) -> ConsultantOutput:
        """Tüm bilgiler var → pipeline'a geç."""
        needs = NeedsAnalysisOutput(
            product_category=parsed.get("category", "unknown"),
            product_subcategory=None,
            must_have_features=parsed.get("must_haves", []),
            nice_to_have_features=[],
            budget_min=parsed.get("budget_min"),
            budget_max=parsed.get("budget_max"),
            budget_currency="TRY",
            use_case=parsed.get("use_case"),
            confidence=parsed.get("confidence", 0.85),
        )

        return ConsultantOutput(
            ready_for_pipeline=True,
            parsed_needs=needs,
            clarification_questions=[],
            educational_content=None,
            interaction_mode="ready",
            message_to_user=(
                f"Süper, anladım! 🎯\n\n"
                f"İstediğin: {parsed.get('extracted_summary', '')}\n\n"
                f"Araştırmaya başlıyorum... 🔍"
            ),
            confidence=parsed.get("confidence", 0.85),
        )

    def _build_one_question(
        self,
        category: str,
        parsed: dict,
    ) -> ConsultantOutput:
        """Sadece 1 kritik soru sor."""
        questions_pool = QUESTION_BANK.get(category, QUESTION_BANK["_default"])

        # En kritik eksik field'ı bul
        missing_question = self._find_most_critical_missing(
            questions_pool, parsed
        )

        if not missing_question:
            # Hiçbir field eksik değilse hazır say
            return self._build_ready_response(parsed)

        clarification = self._dict_to_clarification_question(missing_question)

        return ConsultantOutput(
            ready_for_pipeline=False,
            parsed_needs=None,
            clarification_questions=[clarification],
            educational_content=None,
            interaction_mode="clarification",
            message_to_user=(
                "Anladım! Bir tek şey sormam gerek 🙏"
            ),
            confidence=parsed.get("confidence", 0.6),
        )

    def _build_multiple_questions(
        self,
        category: str,
        parsed: dict,
    ) -> ConsultantOutput:
        """2-3 soru sor (en kritik olanlar)."""
        questions_pool = QUESTION_BANK.get(category, QUESTION_BANK["_default"])

        # En kritik 2-3 soruyu seç
        critical = self._select_critical_questions(
            questions_pool, parsed, max_count=3
        )

        clarifications = [
            self._dict_to_clarification_question(q) for q in critical
        ]

        return ConsultantOutput(
            ready_for_pipeline=False,
            parsed_needs=None,
            clarification_questions=clarifications,
            educational_content=None,
            interaction_mode="clarification",
            message_to_user=(
                f"Sana en doğru {category} önerisini sunabilmem için "
                f"{len(clarifications)} hızlı sorum var. "
                f"'Bilmiyorum' seçeneğini de seçebilirsin 💪"
            ),
            confidence=parsed.get("confidence", 0.3),
        )

    def _build_educational_response(
        self,
        category: str,
        parsed: dict,
    ) -> ConsultantOutput:
        """Eğitim modu - bilgi ver."""
        content = EDUCATIONAL_CONTENT.get(
            category,
            f"{category} hakkında detaylı bilgi henüz hazır değil, "
            "ama sana yardım etmek için aramaya başlayabilirim.",
        )

        return ConsultantOutput(
            ready_for_pipeline=False,
            parsed_needs=None,
            clarification_questions=[],
            educational_content=content,
            interaction_mode="educational",
            message_to_user=(
                f"Tabii, anlatayım! İşte bilmen gerekenler:\n\n"
                f"Bu bilgilerle araştırma yapmak ister misin? "
                f"İstediğin zaman 'evet, ara' diyebilirsin."
            ),
            confidence=1.0,
        )

    def _build_category_question(self) -> ConsultantOutput:
        """Kategori belirsiz → kategori sor."""
        category_q = QUESTION_BANK["_default"][0]
        clarification = self._dict_to_clarification_question(category_q)

        return ConsultantOutput(
            ready_for_pipeline=False,
            parsed_needs=None,
            clarification_questions=[clarification],
            educational_content=None,
            interaction_mode="category_selection",
            message_to_user=(
                "Tabii, sana yardımcı olayım! 🛒\n\n"
                "Önce hangi kategoride aradığını söyle:"
            ),
            confidence=0.0,
        )

    # ============================================================
    # Helpers
    # ============================================================
    def _dict_to_clarification_question(
        self,
        q_dict: dict,
    ) -> ClarificationQuestion:
        """Question bank dict → Pydantic model."""
        options = [
            ClarificationOption(label=o["label"], value=o.get("value"))
            for o in q_dict.get("options", [])
        ]

        return ClarificationQuestion(
            field=q_dict["field"],
            question=q_dict["question"],
            options=options,
            allow_skip=True,
            priority=q_dict.get("priority", 1),
        )

    def _find_most_critical_missing(
        self,
        questions_pool: list[dict],
        parsed: dict,
    ) -> dict | None:
        """Parsed'da eksik olan en kritik field'ın sorusunu bul."""
        # Priority'ye göre sırala (1 = en kritik)
        sorted_questions = sorted(
            questions_pool, key=lambda q: q.get("priority", 99)
        )

        for q in sorted_questions:
            field = q["field"]
            # Bu field parsed'da yoksa veya boş ise eksik
            if not parsed.get(field):
                return q

        return None

    def _select_critical_questions(
        self,
        questions_pool: list[dict],
        parsed: dict,
        max_count: int = 3,
    ) -> list[dict]:
        """En kritik 2-3 soruyu seç."""
        missing = []
        sorted_questions = sorted(
            questions_pool, key=lambda q: q.get("priority", 99)
        )

        for q in sorted_questions:
            field = q["field"]
            if not parsed.get(field):
                missing.append(q)
                if len(missing) >= max_count:
                    break

        return missing

    # ============================================================
    # Invoke with Retry
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