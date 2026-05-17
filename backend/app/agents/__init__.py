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
from app.agents.consultant import ConsultantAgent
from app.agents.finance import FinanceAgent 
from app.agents.market import MarketAgent  
from app.agents.needs_analysis import NeedsAnalysisAgent
from app.agents.research import ResearchAgent
from app.agents.state import AgentState, WorkflowStatus
from app.agents.strategy import StrategyAgent
from app.agents.tco import TCOAgent

__all__ = [
    "AgentState",
    "BaseAgent",
    "ModelTier",
    "ConsultantAgent",
    "FinanceAgent",
    "MarketAgent",
    "NeedsAnalysisAgent",
    "ResearchAgent",
    "WorkflowStatus",
    "get_gemini_model",
    "StrategyAgent",
    "TCOAgent",
]