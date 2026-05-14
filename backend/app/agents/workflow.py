"""
LangGraph Workflow — Recommendation Pipeline.

7-Agent state machine (şu an: 1 agent — incremental development).

Mimari Akış (final hedef):
                    [START]
                       ↓
              [Needs Analysis]
                       ↓
           ┌───────────┼───────────┐
           ↓           ↓           ↓
        [Research]  [Market]   [Finance]
           ↓           ↓           ↓
           └───────────┼───────────┘
                       ↓
                  [Strategy]
                       ↓
                  [Verifier]
                       ↓
                  [Auditor]
                       ↓
              ❓ approved?
            /              \\
           No                Yes
            ↓                 ↓
       [Strategy]          [END]

Şu an Aşama 1: [START] → [NeedsAnalysis] → [END]
Diğer ajanlar sonraki günlerde eklenecek (incremental).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.needs_analysis import NeedsAnalysisAgent
from app.agents.state import AgentState, WorkflowStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Node Wrappers
# ============================================================
async def needs_analysis_node(state: AgentState) -> AgentState:
    """LangGraph node wrapper for NeedsAnalysisAgent."""
    agent = NeedsAnalysisAgent()
    return await agent.run(state)


# ============================================================
# Workflow Builder
# ============================================================
def build_workflow() -> Any:
    """
    Recommendation workflow'unu LangGraph ile kur.

    Şu an basit: tek node. Sonradan diğer agent'lar eklenecek.

    Returns:
        Compiled LangGraph application.
    """
    # State graph oluştur
    graph = StateGraph(AgentState)

    # Node'ları ekle
    graph.add_node("needs_analysis", needs_analysis_node)
    # Sonradan eklenecek:
    # graph.add_node("research", research_node)
    # graph.add_node("market", market_node)
    # graph.add_node("finance", finance_node)
    # graph.add_node("strategy", strategy_node)
    # graph.add_node("verifier", verifier_node)
    # graph.add_node("auditor", auditor_node)

    # Edges (akış)
    graph.add_edge(START, "needs_analysis")
    graph.add_edge("needs_analysis", END)
    # Sonradan:
    # graph.add_edge("needs_analysis", "research")
    # ... vs.

    # Compile
    compiled = graph.compile()

    logger.info(
        "workflow_compiled",
        node_count=1,
        nodes=["needs_analysis"],
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
    Her request için yeniden compile etmek pahalı olur.
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