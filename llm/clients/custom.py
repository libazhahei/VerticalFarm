from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from llm.clients.base import LangChainChatClient
from llm.clients.config import LLMClientConfig, LLMProvider


class CustomEndpointClient(LangChainChatClient):
    """
    OpenAI-compatible HTTP endpoint at a custom host/port/path.

  Examples:
    - vLLM:   LLM_PROVIDER=custom LLM_HOST=192.168.1.10 LLM_PORT=8000 LLM_API_PATH=v1
    - LocalAI: LLM_PROVIDER=custom LLM_HOST=127.0.0.1 LLM_PORT=8080
    """

    def __init__(self, config: LLMClientConfig) -> None:
        if config.provider != LLMProvider.CUSTOM:
            config = config.model_copy(update={"provider": LLMProvider.CUSTOM})
        super().__init__(config, client_label="CustomEndpointClient")

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.CUSTOM

    def _build_model(self, temperature: float = 0.2) -> BaseChatModel:
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "temperature": temperature,
            "api_key": self._config.api_key or "no-key",
            "openai_api_base": self._config.build_base_url(),
            "request_timeout": self._config.timeout,
        }
        if api_type := self._config.extra.get("api_type"):
            kwargs["openai_api_type"] = api_type
        if api_version := self._config.extra.get("api_version"):
            kwargs["openai_api_version"] = api_version
        return ChatOpenAI(**kwargs)
