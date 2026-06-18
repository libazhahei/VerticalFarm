from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from llm.clients.base import BaseLLMClient
from llm.clients.config import LLMClientConfig, LLMProvider


class LocalGGUFClient(BaseLLMClient):
    """Placeholder for future on-device GGUF inference on Jetson."""

    def __init__(self, model_path: str, config: LLMClientConfig | None = None, **kwargs: Any) -> None:
        self.model_path = model_path
        self._config = config or LLMClientConfig(
            provider=LLMProvider.GGUF,
            model_name=model_path,
            extra={"model_path": model_path, **kwargs},
        )
        self.kwargs = kwargs

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.GGUF

    @property
    def config(self) -> LLMClientConfig:
        return self._config

    def get_model(self, temperature: float = 0.2) -> BaseChatModel:
        raise NotImplementedError(
            "LocalGGUFClient is not implemented yet. Use OpenAIClient or OllamaClient for now."
        )

    def run_chain(self, prompt_template: PromptTemplate, data: dict, temperature: float = 0.2) -> Any:
        raise NotImplementedError("LocalGGUFClient is not implemented yet.")

    def run_messages(self, messages: list[dict], temperature: float = 0.2) -> Any:
        raise NotImplementedError("LocalGGUFClient is not implemented yet.")
