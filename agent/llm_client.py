"""
Тонкая обёртка над OpenAI-совместимым Chat Completions API
(farabi-inference.kaznu.kz), реализованная напрямую через httpx.

ВАЖНО: сознательно НЕ используется пакет `openai`. Существующий
`requirements.txt` этого проекта тянет `openmines>=0.1.0`, который жёстко
пинит `openai==0.27.8` (древний pre-v1 SDK, без класса AsyncOpenAI и без
`chat.completions.create`). Современный `openai>=1.x` конфликтует с этим
пином при `pip install` (ResolutionImpossible). httpx не участвует в этом
конфликте и уже используется в проекте транзитивно, поэтому здесь простой
прямой HTTP-вызов к /chat/completions, повторяющий контракт OpenAI API.

Логика подавления/вырезания "утечек" рассуждений (<think> теги у Qwen3)
портирована из соседнего rag_agent/app/llm/client.py без изменений.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from agent.config import get_agent_settings

logger = logging.getLogger(__name__)

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_REASONING_LEAK_MARKERS = (
    "here's a thinking process",
    "let me think",
    "let's think step by step",
    "analyze user input",
)


def _strip_leaked_reasoning(text: str) -> str:
    if not text:
        return text

    cleaned = _THINK_TAG_RE.sub("", text).strip()
    if cleaned != text.strip():
        logger.warning("LLM вернул <think>-теги в content; вырезаны перед выдачей пользователю.")
        text = cleaned

    lowered = text.lstrip().lower()
    if any(lowered.startswith(marker) for marker in _REASONING_LEAK_MARKERS):
        logger.error(
            "Обнаружена утечка reasoning-текста в content без <think>-тегов; начало ответа: %s",
            text[:200],
        )

    return text


class AgentLLMClient:
    def __init__(self) -> None:
        settings = get_agent_settings()
        self._base_url = settings.agent_base_url.rstrip("/")
        self._api_key = settings.agent_api_key
        self._model = settings.agent_model_name
        self._default_temperature = settings.agent_temperature
        self._default_max_tokens = settings.agent_max_tokens

    async def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        enable_thinking: bool = False,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._default_temperature,
            "max_tokens": max_tokens or self._default_max_tokens,
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        }
        data = await self._post_chat_completion(payload)
        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        return _strip_leaked_reasoning(content)

    async def complete_json(self, messages: list[dict[str, str]], temperature: float = 0.0) -> dict[str, Any]:
        # Запрашивает строго JSON-ответ. Используется ReAct-циклом агента для выбора инструмента/финального ответа.
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self._default_max_tokens,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        data = await self._post_chat_completion(payload)
        raw = data["choices"][0]["message"].get("content") or "{}"
        raw = _THINK_TAG_RE.sub("", raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("LLM вернул невалидный JSON: %s", raw[:300])
            return {"final_answer": raw, "proposed_actions": []}


_llm_singleton: AgentLLMClient | None = None


def get_agent_llm_client() -> AgentLLMClient:
    global _llm_singleton
    if _llm_singleton is None:
        _llm_singleton = AgentLLMClient()
    return _llm_singleton
