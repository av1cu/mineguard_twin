"""Простая in-memory история диалога по session_id (без персистентности —
достаточно для демо; не трогает основную БД mineguard.db)."""
from __future__ import annotations

from typing import Dict, List

from agent.config import get_agent_settings


class ConversationMemory:
    def __init__(self) -> None:
        self._sessions: Dict[str, List[dict]] = {}

    def get(self, session_id: str) -> List[dict]:
        return self._sessions.get(session_id, [])

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        settings = get_agent_settings()
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": role, "content": content})
        max_turns = settings.agent_memory_max_turns
        if len(history) > max_turns:
            del history[: len(history) - max_turns]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


_memory_singleton: ConversationMemory | None = None


def get_conversation_memory() -> ConversationMemory:
    global _memory_singleton
    if _memory_singleton is None:
        _memory_singleton = ConversationMemory()
    return _memory_singleton
