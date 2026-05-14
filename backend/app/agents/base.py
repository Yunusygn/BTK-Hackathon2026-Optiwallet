"""
Abstract Base Agent.

Tüm agent'lar bu sınıftan türer. Standart interface'i garanti eder:
- Her agent run() metoduna sahip
- Her agent state'i okur ve günceller
- Her agent kendi adını döner (logging için)
- Her agent error handling yapar

Pattern: Template Method + Strategy.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.agents.state import AgentState
from app.core.logging import get_logger


class BaseAgent(ABC):
    """
    Tüm AI agent'ların base class'ı.

    Subclass'lar şunları yapmalı:
    1. `name` property override et (agent ismi).
    2. `description` property override et (ne yapar).
    3. `_execute()` method'u implement et (asıl iş).

    Template method `run()` otomatik:
    - Logging
    - Error handling
    - Timing
    - State update (agent_history)
    """

    def __init__(self) -> None:
        self.logger = get_logger(f"agent.{self.name}")

    # ============================================================
    # Properties (subclass tarafından override edilecek)
    # ============================================================
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent ismi (snake_case)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent ne yapar?"""
        ...

    # ============================================================
    # Public Interface
    # ============================================================
    async def run(self, state: AgentState) -> AgentState:
        """
        Agent'i çalıştır.

        Bu template method:
        1. Log "agent_started"
        2. _execute() çağır
        3. state.agent_history güncelle
        4. Log "agent_completed"
        5. Hata olursa state.errors'a ekle

        Args:
            state: Shared workflow state.

        Returns:
            Güncellenmiş state.
        """
        start_time = time.time()
        started_at = datetime.now(timezone.utc)

        self.logger.info(
            "agent_started",
            agent=self.name,
            description=self.description,
        )

        # Agent history'e başlangıç kaydı ekle
        history_entry = {
            "agent": self.name,
            "started_at": started_at.isoformat(),
            "status": "running",
        }

        try:
            # Asıl işi yap (subclass implement eder)
            updated_state = await self._execute(state)

            # Süre hesapla
            duration_ms = int((time.time() - start_time) * 1000)

            # History'e completion kaydı
            history_entry.update(
                {
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            self.logger.info(
                "agent_completed",
                agent=self.name,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)

            history_entry.update(
                {
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )

            self.logger.error(
                "agent_failed",
                agent=self.name,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )

            # Hatayı state'e ekle ama akışı durdurma
            errors = state.get("errors", [])
            errors.append(history_entry.copy())
            updated_state = {**state, "errors": errors}

        # agent_history güncelle
        agent_history = updated_state.get("agent_history", [])
        agent_history.append(history_entry)
        updated_state["agent_history"] = agent_history

        return updated_state

    # ============================================================
    # Subclass Interface
    # ============================================================
    @abstractmethod
    async def _execute(self, state: AgentState) -> AgentState:
        """
        Asıl agent logic'i. Subclass implement etmeli.

        Args:
            state: Mevcut workflow state.

        Returns:
            Güncellenmiş state (dict copy ile).

        Implementation rehberi:
            async def _execute(self, state: AgentState) -> AgentState:
                # 1. State'den gerekli bilgiyi oku
                query = state["user_query"]

                # 2. Gemini'ye sor
                result = await self._call_gemini(query)

                # 3. State'i güncelle (immutable)
                return {**state, "needs_analysis": result}
        """
        ...

    # ============================================================
    # Helpers
    # ============================================================
    def update_state(self, state: AgentState, **kwargs: Any) -> AgentState:
        """
        State'i immutable şekilde güncelle.

        Usage:
            return self.update_state(state, needs_analysis=result)
        """
        return {**state, **kwargs}  # type: ignore[typeddict-item]