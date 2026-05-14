"""
NeedsAnalysisAgent.

Kullanıcının doğal dil sorgusunu structured JSON'a çevirir.

Pattern: BaseAgent + Gemini Flash + JSON mode + Pydantic validation.
Model: gemini-2.5-flash (fast tier - basit parsing için yeterli)
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.base import BaseAgent
from app.agents.gemini_client import (
    ModelTier,
    get_gemini_model,
    invoke_with_retry,
)
from app.agents.prompts import NEEDS_ANALYSIS_SYSTEM_PROMPT
from app.agents.schemas import NeedsAnalysisOutput
from app.agents.state import AgentState


class NeedsAnalysisAgent(BaseAgent):
    """
    Doğal dil sorgu → Structured JSON.

    Bu agent tüm workflow'un **giriş kapısı**. Diğer agent'lar
    bu agent'in çıktısını input olarak alır.

    Bu yüzden:
    - JSON mode kullanır (güvenli output)
    - Pydantic validation ile yapı garantili
    - Düşük temperature (0.2) → deterministic
    """

    @property
    def name(self) -> str:
        return "needs_analysis"

    @property
    def description(self) -> str:
        return "Doğal dil sorguyu yapılandırılmış kritere çevirir"

    async def _execute(self, state: AgentState) -> AgentState:
        """
        Asıl iş.

        Adımlar:
        1. State'den user_query al
        2. Gemini'ye JSON mode'da sor
        3. Pydantic ile validate et
        4. NeedsAnalysis dict olarak state'e ekle
        """
        user_query = state["user_query"]

        self.logger.info(
            "needs_analysis_started",
            query_length=len(user_query),
            query_preview=user_query[:80],
        )

        # ===== 1. Gemini Setup =====
        # Flash tier: hızlı + ucuz
        # JSON mode: structured output
        # Low temperature: deterministic (her aynı input için aynı output)
        model = get_gemini_model(
            tier=ModelTier.FAST,
            temperature=0.2,
            json_mode=True,
            max_tokens=2048,
        )

        # ===== 2. Messages =====
        messages = [
            SystemMessage(content=NEEDS_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ]

        # ===== 3. Gemini Call (with retry) =====
        try:
            raw_response = await invoke_with_retry(model, messages)
        except Exception as exc:
            self.logger.error(
                "gemini_call_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        # ===== 4. JSON Parse =====
        try:
            parsed_json = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            self.logger.error(
                "invalid_json_response",
                raw_response=raw_response[:500],
                error=str(exc),
            )
            raise ValueError(
                f"Gemini returned invalid JSON: {exc}"
            ) from exc

        # ===== 5. Pydantic Validation =====
        try:
            validated = NeedsAnalysisOutput(**parsed_json)
        except ValidationError as exc:
            self.logger.error(
                "schema_validation_failed",
                errors=exc.errors(),
                raw_parsed=parsed_json,
            )
            raise ValueError(
                f"Output failed schema validation: {exc}"
            ) from exc

        # ===== 6. Convert to State Format =====
        needs_analysis_dict = {
            "raw_query": user_query,
            "product_category": validated.product_category.value,
            "subcategory": validated.subcategory,
            "must_have_features": validated.must_have_features,
            "nice_to_have_features": validated.nice_to_have_features,
            "deal_breakers": validated.deal_breakers,
            "budget_min": validated.budget_min,
            "budget_max": validated.budget_max,
            "budget_currency": validated.budget_currency,
            "use_case": validated.use_case,
            "user_context": validated.user_context,
            "is_urgent": validated.urgency.value == "urgent",
            "deadline_days": validated.deadline_days,
        }

        self.logger.info(
            "needs_analysis_completed",
            product_category=validated.product_category.value,
            confidence=validated.confidence,
            has_clarifications=bool(validated.clarification_questions),
        )

        # ===== 7. State Update =====
        return self.update_state(
            state,
            needs_analysis=needs_analysis_dict,
            current_agent=self.name,
        )