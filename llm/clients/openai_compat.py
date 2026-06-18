import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from llm.clients.base import LangChainChatClient
from llm.clients.config import LLMClientConfig, LLMProvider

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(_PROJECT_ROOT / ".env")
        _ENV_LOADED = True


def _resolve_openai_config() -> LLMClientConfig:
    _ensure_env_loaded()
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider not in {"openai", ""}:
        return LLMClientConfig.from_env()
    return LLMClientConfig.from_env()


class OpenAIClient(LangChainChatClient):
    """OpenAI-compatible cloud APIs (OpenAI, DeepSeek, Groq, OpenRouter, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        api_base: str | None = None,
        api_type: str | None = None,
        api_version: str | None = None,
        config: LLMClientConfig | None = None,
    ) -> None:
        if config is None:
            if api_key is None or model_name is None:
                config = _resolve_openai_config()
            else:
                extra: dict[str, Any] = {}
                if api_type:
                    extra["api_type"] = api_type
                if api_version:
                    extra["api_version"] = api_version
                config = LLMClientConfig(
                    provider=LLMProvider.OPENAI,
                    model_name=model_name,
                    api_key=api_key,
                    api_base=api_base,
                    extra=extra,
                )
        elif config.provider != LLMProvider.OPENAI:
            config = config.model_copy(update={"provider": LLMProvider.OPENAI})
        super().__init__(config, client_label="OpenAIClient")

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    @property
    def api_key(self) -> str:
        return self._config.api_key or ""

    @property
    def model_name(self) -> str:
        return self._config.model_name

    @property
    def api_base(self) -> str | None:
        return self._config.api_base

    @classmethod
    def from_env(cls) -> "OpenAIClient":
        config = LLMClientConfig.from_env()
        if config.provider != LLMProvider.OPENAI:
            raise EnvironmentError(
                f"LLM_PROVIDER={config.provider.value}. Use create_llm_client_from_env() for non-openai providers."
            )
        return cls(config=config)

    def _build_model(self, temperature: float = 0.2) -> BaseChatModel:
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "temperature": temperature,
            "api_key": self._config.api_key,
            "request_timeout": self._config.timeout,
        }
        if self._config.api_base:
            kwargs["openai_api_base"] = self._config.api_base
        if api_type := self._config.extra.get("api_type"):
            kwargs["openai_api_type"] = api_type
        if api_version := self._config.extra.get("api_version"):
            kwargs["openai_api_version"] = api_version
        return ChatOpenAI(**kwargs)
