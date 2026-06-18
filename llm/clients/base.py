import time
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from llm.clients.config import LLMClientConfig, LLMProvider
from llm.utils.json import repair_json_with_model
from llm.utils.logging import ansi_cprint


class BaseLLMClient(ABC):
    """Abstract interface for all LLM backends used by the agent workflow."""

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        pass

    @property
    @abstractmethod
    def config(self) -> LLMClientConfig:
        pass

    @abstractmethod
    def get_model(self, temperature: float = 0.2) -> BaseChatModel:
        pass

    @abstractmethod
    def run_chain(self, prompt_template: PromptTemplate, data: dict, temperature: float = 0.2) -> Any:
        pass

    @abstractmethod
    def run_messages(self, messages: list[dict], temperature: float = 0.2) -> Any:
        pass

    def repair_json(self, error_json: str, schema: dict, max_attempts: int = 3) -> str:
        return repair_json_with_model(
            error_json,
            schema,
            self.get_model(temperature=0.0),
            max_attempts=max_attempts,
        )


class LangChainChatClient(BaseLLMClient):
    """Shared LangChain chat-model client with retry logic."""

    def __init__(self, config: LLMClientConfig, client_label: str) -> None:
        self._config = config
        self._client_label = client_label

    @property
    def config(self) -> LLMClientConfig:
        return self._config

    @abstractmethod
    def _build_model(self, temperature: float = 0.2) -> BaseChatModel:
        pass

    def get_model(self, temperature: float = 0.2) -> BaseChatModel:
        return self._build_model(temperature)

    def run_chain(self, prompt_template: PromptTemplate, data: dict, temperature: float = 0.2) -> Any:
        model = self._build_model(temperature)
        chain = prompt_template | model
        attempts = 0
        while attempts < self._config.max_retries:
            try:
                return chain.invoke(data)
            except Exception as error:
                attempts += 1
                ansi_cprint(f"[{self._client_label}] chain attempt {attempts} failed: {error}", fg="red")
                time.sleep(1.0 * attempts)
        raise RuntimeError(f"{self._client_label} chain failed after retries")

    def run_messages(self, messages: list[dict], temperature: float = 0.2) -> Any:
        model = self._build_model(temperature)
        attempts = 0
        while attempts < self._config.max_retries:
            try:
                return model.invoke(messages)
            except Exception as error:
                attempts += 1
                ansi_cprint(f"[{self._client_label}] messages attempt {attempts} failed: {error}", fg="red")
                time.sleep(1.0 * attempts)
        raise RuntimeError(f"{self._client_label} chat failed after retries")
