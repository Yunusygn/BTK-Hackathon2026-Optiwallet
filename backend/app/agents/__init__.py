"""
AI Agents — LangGraph 7-Agent Architecture.

7 uzman ajan, her biri kendi domain'inde uzman:
- ResearchAgent: Forum, review, YouTube tarama (Grounding)
- NeedsAnalysisAgent: Doğal dil → teknik kriter ✅
- MarketAgent: Anlık fiyat ve kupon (Grounding)
- FinanceAgent: Bütçe, kart, taksit analizi
- StrategyAgent: Tüm verileri sentezleyip tavsiye üretir
- VerifierAgent: Faktüel doğrulama (link, fiyat, math)
- AuditorAgent: Mantıksal doğrulama (Reflexion pattern)

Pattern: LangGraph (state machine) + Gemini 2.5 (Smart Routing)
"""

from app.agents.base import BaseAgent
from app.agents.gemini_client import ModelTier, get_gemini_model
from app.agents.needs_analysis import NeedsAnalysisAgent
from app.agents.state import AgentState, WorkflowStatus

__all__ = [
    "AgentState",
    "BaseAgent",
    "ModelTier",
    "NeedsAnalysisAgent",
    "WorkflowStatus",
    "get_gemini_model",
]