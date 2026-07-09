"""
ReAct-цикл AI-агента диспетчера: JSON-based tool calling (не полагаемся на
нативный OpenAI function-calling — фермa инференса farabi-inference не
гарантированно его поддерживает для Qwen3, и соседний rag_agent тоже общается
с LLM через простой complete()/complete_json(), так что этот же паттерн
переиспользован здесь для консистентности).

Каждый шаг цикла: модель получает системный промпт + историю + описание
последнего результата инструмента и обязана вернуть один JSON-объект —
либо вызов инструмента, либо финальный ответ с proposed_actions.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.config import get_agent_settings
from agent.llm_client import get_agent_llm_client
from agent.tools import READ_ONLY_TOOLS

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    answer: str
    proposed_actions: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)


def _truncate(obj: Any, limit: int = 1500) -> str:
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        text = str(obj)
    return text if len(text) <= limit else text[:limit] + "...(truncated)"


async def run_agent(
    system_prompt: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> AgentRunResult:
    """Запускает ReAct-цикл. history — предыдущие ходы диалога (user/assistant
    текстовые сообщения, без деталей tool-calls, чтобы не раздувать контекст)."""
    settings = get_agent_settings()
    llm = get_agent_llm_client()

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})

    trace: List[Dict[str, Any]] = []

    for step in range(settings.agent_max_tool_iterations):
        raw = await llm.complete_json(messages)

        if "final_answer" in raw and raw.get("final_answer"):
            proposed = raw.get("proposed_actions") or []
            if not isinstance(proposed, list):
                proposed = []
            return AgentRunResult(answer=str(raw["final_answer"]), proposed_actions=proposed, trace=trace)

        tool_name = raw.get("tool")
        if not tool_name or tool_name not in READ_ONLY_TOOLS:
            # Модель вернула что-то невалидное — просим поправиться один раз,
            # либо, если это последний шаг, отдаём как есть.
            if step == settings.agent_max_tool_iterations - 1:
                return AgentRunResult(
                    answer=raw.get("final_answer") or "Не удалось получить ответ от агента.",
                    proposed_actions=[],
                    trace=trace,
                )
            messages.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})
            messages.append({
                "role": "user",
                "content": "Некорректный формат. Верни JSON строго вида {\"tool\": ...} или {\"final_answer\": ...}.",
            })
            continue

        args = raw.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        try:
            tool_fn = READ_ONLY_TOOLS[tool_name]
            result = tool_fn(**args)
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"Ошибка вызова инструмента {tool_name}: {exc}"}
            logger.exception("Tool call failed: %s(%s)", tool_name, args)

        trace.append({"tool": tool_name, "args": args, "result_preview": _truncate(result, 500)})

        messages.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})
        messages.append({
            "role": "user",
            "content": f"Результат вызова {tool_name}: {_truncate(result)}",
        })

    return AgentRunResult(
        answer="Достигнут лимит шагов рассуждения без финального ответа. Попробуйте переформулировать запрос.",
        proposed_actions=[],
        trace=trace,
    )
