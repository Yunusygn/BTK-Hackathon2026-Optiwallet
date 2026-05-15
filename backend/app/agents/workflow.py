"""
LangGraph Workflow — Conversational Recommendation Pipeline.

ARCHITECTURE:
ConsultantAgent giriş kapısıdır. Confidence'a göre 2 yol:
- ready=True → ResearchAgent → (gelecekte: Market, Finance, Strategy)
- ready=False → Kullanıcıya soru gösterip dur (clarification döngüsü)

CURRENT NODES:
- consultant: Entry gate (niyet anla, eksikse sor)
- research: Multi-criteria decision analysis (6 boyut)

NEXT NODES (gelecek):
- market: Fiyat + satıcı + kampanya
- finance: Cash flow + taksit + coaching
- tco: 5 yıllık toplam maliyet
- strategy: Sentez + final öneri
- auditor: Reflexion kontrol

PHILOSOPHY:
- Conversation-first (clarification olmadan pipeline başlamaz)
- Strict Budget Respect (bütçesiz öneri yok)
- Patron + Asistan + CEO hiyerarşi
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.consultant import ConsultantAgent
from app.agents.research import ResearchAgent
from app.agents.state import AgentState, WorkflowStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Node Wrappers
# ============================================================
async def consultant_node(state: AgentState) -> AgentState:
    """
    ConsultantAgent node wrapper.

    Kullanıcının giriş kapısı. Niyeti anla, eksikse soru sor.

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
    """ResearchAgent node wrapper - 6-dimensional MCDA."""
    agent = ResearchAgent()
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

    Returns:
        "research" veya "end"
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
        # Kullanıcıya cevap göster, sonraki turn'ü bekle
        return "end"


# ============================================================
# Workflow Builder
# ============================================================
def build_workflow() -> Any:
    """
    Conversational Recommendation Pipeline.

    Şu anki node'lar:
    - consultant: Entry gate
    - research: Multi-criteria decision analysis

    Eklenecek (gelecek günler):
    - market, finance, tco, strategy, auditor

    Returns:
        Compiled LangGraph application.
    """
    graph = StateGraph(AgentState)

    # ===== Node'ları ekle =====
    graph.add_node("consultant", consultant_node)
    graph.add_node("research", research_node)

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

    # Research → END (şimdilik; sonra market, finance, vs.)
    graph.add_edge("research", END)

    # Compile
    compiled = graph.compile()

    logger.info(
        "workflow_compiled",
        node_count=2,
        nodes=["consultant", "research"],
        conditional_routing=True,
    )

    return compiled


# ============================================================
# Singleton Workflow Instance
# ============================================================
_workflow_instance: Any | None = None


def get_workflow() -> Any:
    """
    Singleton workflow instance.

    İlk çağrıda compile edilir, sonra cache'lenir.
    """
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
    """
    Workflow için başlangıç state'i oluştur.

    Args:
        user_query: Kullanıcının doğal dil sorgusu.
        session_id: Session UUID.
        user_id: User UUID (misafir mod için None).
        conversation_id: Var olan konuşmaya devam ediliyorsa.
        user_context: Profile, finansal profil, vs.

    Returns:
        Initial AgentState.
    """
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

        # Agent outputs (None başlangıçta)
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