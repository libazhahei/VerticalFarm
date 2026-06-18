from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from llm.clients.base import LangChainChatClient
from llm.clients.config import LLMClientConfig, LLMProvider


class OllamaClient(LangChainChatClient):
    """Ollama local inference via langchain-ollama."""

    def __init__(self, config: LLMClientConfig) -> None:
        if config.provider != LLMProvider.OLLAMA:
            config = config.model_copy(update={"provider": LLMProvider.OLLAMA})
        super().__init__(config, client_label="OllamaClient")

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OLLAMA

    def _build_model(self, temperature: float = 0.2) -> BaseChatModel:
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "temperature": temperature,
            "base_url": self._config.build_base_url(),
            "timeout": self._config.timeout,
        }
        kwargs.update(self._config.extra)
        return ChatOllama(**kwargs)
