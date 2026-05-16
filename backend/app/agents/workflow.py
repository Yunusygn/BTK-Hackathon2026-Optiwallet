"""
LangGraph Workflow — Conversational Recommendation Pipeline.

ARCHITECTURE:
ConsultantAgent giriş kapısıdır. Confidence'a göre 2 yol:
- ready=True → Research → Market → Finance → END
- ready=False → END (kullanıcı clarification cevaplayana kadar)

CURRENT NODES (4):
- consultant: Entry gate (niyet anla, eksikse sor)
- research: Multi-criteria decision analysis (6 boyut)
- market: Real-time price + seller analysis
- finance: Cash flow + debt + coaching

NEXT NODES (gelecek):
- tco: 5-year total cost projection
- strategy: Final synthesis (Pro tier)
- auditor: Reflexion quality check

PHILOSOPHY:
- Conversation-first (clarification olmadan pipeline başlamaz)
- Strict Budget Respect (bütçesiz öneri yok)
- Strict Honesty (alım sıkışıksa 'ertele' der)
- KVKK compliant (finansal bilgi opsiyonel)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.consultant import ConsultantAgent
from app.agents.finance import FinanceAgent
from app.agents.market import MarketAgent
from app.agents.research_v3 import ResearchAgentV3
from app.agents.state import AgentState, WorkflowStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Node Wrappers
# ============================================================
async def consultant_node(state: AgentState) -> AgentState:
    """
    ConsultantAgent node wrapper.

    Output:
        consultant_output dict ile:
        - ready_for_pipeline: bool
        - clarification_questions: list (eksikse)
        - parsed_needs: NeedsAnalysisOutput (varsa)
        - interaction_mode: ready/clarification/educational/category_selection
    """
    agent = ConsultantAgent()
    new_state = await agent.run(state)

    # ConsultantAgent çıktısını sonraki agent'ların kullanabileceği
    # formata da kopyala (parsed_needs varsa needs_analysis'e map et)
    consultant_output = new_state.get("consultant_output")
    if consultant_output and consultant_output.get("parsed_needs"):
        new_state["needs_analysis"] = consultant_output["parsed_needs"]

    return new_state


async def research_node(state: AgentState) -> AgentState:
    """ResearchAgent v3 - Hibrit Smart Filter + Tournament."""
    agent = ResearchAgentV3()
    return await agent.run(state)


async def market_node(state: AgentState) -> AgentState:
    """MarketAgent - Real-time price + seller analysis."""
    agent = MarketAgent()
    return await agent.run(state)


async def finance_node(state: AgentState) -> AgentState:
    """FinanceAgent - Cash flow + debt + coaching."""
    agent = FinanceAgent()
    return await agent.run(state)


# ============================================================
# Conditional Router
# ============================================================
def route_after_consultant(state: AgentState) -> str:
    """
    ConsultantAgent sonrası akışı belirler.

    Kararlar:
    - ready_for_pipeline=True → research (devam et)
    - ready_for_pipeline=False → END (kullanıcı cevap verene kadar bekle)
    """
    consultant_output = state.get("consultant_output")

    if not consultant_output:
        logger.warning("route_consultant_output_missing")
        return "end"

    ready = consultant_output.get("ready_for_pipeline", False)
    mode = consultant_output.get("interaction_mode", "unknown")

    logger.info(
        "route_after_consultant",
        ready=ready,
        mode=mode,
    )

    if ready:
        return "research"
    else:
        # Clarification, educational, veya category_selection mode
        return "end"


# ============================================================
# Workflow Builder
# ============================================================
def build_workflow() -> Any:
    """
    Conversational Recommendation Pipeline (4 nodes).

    Flow:
        START → Consultant
                  ↓ (conditional)
                  ├── ready → Research → Market → Finance → END
                  └── not ready → END
    """
    graph = StateGraph(AgentState)

    # ===== Node'ları ekle =====
    graph.add_node("consultant", consultant_node)
    graph.add_node("research", research_node)
    graph.add_node("market", market_node)
    graph.add_node("finance", finance_node)

    # ===== Edges =====
    # Start → Consultant
    graph.add_edge(START, "consultant")

    # Consultant → (conditional) → Research veya END
    graph.add_conditional_edges(
        "consultant",
        route_after_consultant,
        {
            "research": "research",
            "end": END,
        },
    )

    # Research → Market → Finance → END (linear)
    graph.add_edge("research", "market")
    graph.add_edge("market", "finance")
    graph.add_edge("finance", END)

    # Compile
    compiled = graph.compile()

    logger.info(
        "workflow_compiled",
        node_count=4,
        nodes=["consultant", "research", "market", "finance"],
        conditional_routing=True,
    )

    return compiled


# ============================================================
# Singleton Workflow Instance
# ============================================================
_workflow_instance: Any | None = None


def get_workflow() -> Any:
    """Singleton workflow instance."""
    global _workflow_instance

    if _workflow_instance is None:
        _workflow_instance = build_workflow()
        logger.info("workflow_singleton_created")

    return _workflow_instance


# ============================================================
# Initial State Builder
# ============================================================
def create_initial_state(
    user_query: str,
    session_id: str,
    user_id: str | None = None,
    conversation_id: str | None = None,
    user_context: dict | None = None,
) -> AgentState:
    """Workflow için başlangıç state'i."""
    return {
        # Identity
        "user_id": user_id,
        "conversation_id": conversation_id,
        "session_id": session_id,

        # Input
        "user_query": user_query,
        "user_context": user_context or {},

        # Messages
        "messages": [],

        # Agent outputs
        "consultant_output": None,
        "needs_analysis": None,
        "market_intel": None,
        "research_intel": None,
        "finance_analysis": None,
        "recommendation": None,
        "verification": None,
        "audit": None,

        # Workflow control
        "workflow_status": WorkflowStatus.INITIALIZED,
        "current_agent": None,
        "agent_history": [],

        # Reflexion
        "auditor_attempts": 0,
        "max_auditor_attempts": 3,

        # Metadata
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "total_tokens_used": 0,
        "total_duration_ms": 0,

        # Errors
        "errors": [],
    }