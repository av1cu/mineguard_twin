"""
Централизованная конфигурация AI-агента диспетчера.

Отдельный модуль конфигурации (не трогает backend/*), значения читаются из
.env в корне проекта. По умолчанию указаны параметры инфраструктуры
farabi-inference.kaznu.kz (тот же inference-сервер, что используется в
соседнем rag_agent проекте) — тот же паттерн конфигурации намеренно
переиспользован для консистентности между проектами.
"""
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", protected_namespaces=()
    )

    # --- LLM (Farabi inference, OpenAI-совместимый API) ---
    # Каждое поле принимает либо агент-специфичное имя переменной (AGENT_*),
    # либо "общее" имя в стиле соседнего rag_agent/.env (BASE_URL, API_KEY,
    # ...) - так один и тот же .env можно переиспользовать между проектами
    # независимо от того, какой набор имён там уже используется.
    agent_base_url: str = Field(
        default="https://farabi-inference.kaznu.kz/v1",
        validation_alias=AliasChoices("AGENT_BASE_URL", "BASE_URL"),
    )
    agent_api_key: str = Field(
        default="changeme",
        validation_alias=AliasChoices("AGENT_API_KEY", "API_KEY"),
    )
    agent_model_name: str = Field(
        default="Qwen/Qwen3.6-27B",
        validation_alias=AliasChoices("AGENT_MODEL_NAME", "MODEL_NAME"),
    )
    agent_temperature: float = Field(
        default=0.2,
        validation_alias=AliasChoices("AGENT_TEMPERATURE", "TEMPERATURE"),
    )
    agent_max_tokens: int = Field(
        default=1536,
        validation_alias=AliasChoices("AGENT_MAX_TOKENS", "MAX_TOKENS"),
    )

    # --- ReAct loop ---
    agent_max_tool_iterations: int = 6
    agent_memory_max_turns: int = 12


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
