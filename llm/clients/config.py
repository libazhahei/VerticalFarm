import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from llm.constants import OLLAMA_HOST, OLLAMA_PORT


class LLMProvider(str, Enum):
    """Supported LLM backend providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"
    GGUF = "gguf"
    VF_SERVER = "vf_server"


class LLMClientConfig(BaseModel):
    """Unified configuration for all LLM client backends."""

    provider: LLMProvider = LLMProvider.OPENAI
    model_name: str
    api_key: str | None = None
    api_base: str | None = None
    host: str = OLLAMA_HOST
    port: int = OLLAMA_PORT
    scheme: str = "http"
    api_path: str = "v1"
    timeout: int = 120
    max_retries: int = 3
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> "LLMClientConfig":
        if self.provider == LLMProvider.OPENAI and not self.api_key:
            raise ValueError("api_key is required for openai provider")
        return self

    def build_base_url(self) -> str:
        if self.api_base:
            return self.api_base.rstrip("/")
        if self.provider == LLMProvider.OLLAMA:
            return f"{self.scheme}://{self.host}:{self.port}"
        if self.provider == LLMProvider.CUSTOM:
            base = f"{self.scheme}://{self.host}:{self.port}"
            path = self.api_path.strip("/")
            return f"{base}/{path}" if path else base
        return self.api_base or "https://api.openai.com/v1"

    @classmethod
    def from_env(cls) -> "LLMClientConfig":
        from llm.clients.openai_compat import _ensure_env_loaded

        _ensure_env_loaded()

        provider_raw = (os.environ.get("LLM_PROVIDER") or "openai").lower()
        try:
            provider = LLMProvider(provider_raw)
        except ValueError as error:
            allowed = ", ".join(item.value for item in LLMProvider)
            raise EnvironmentError(f"Invalid LLM_PROVIDER={provider_raw!r}. Use one of: {allowed}") from error

        model_name = os.environ.get("LLM_MODEL_NAME")
        api_key = os.environ.get("LLM_API_KEY")
        api_base = os.environ.get("LLM_API_BASE")
        host = os.environ.get("LLM_HOST") or os.environ.get("OLLAMA_HOST") or OLLAMA_HOST
        port = int(os.environ.get("LLM_PORT") or os.environ.get("OLLAMA_PORT") or OLLAMA_PORT)
        scheme = os.environ.get("LLM_SCHEME") or "http"
        api_path = os.environ.get("LLM_API_PATH") or "v1"
        timeout = int(os.environ.get("LLM_TIMEOUT") or "120")
        max_retries = int(os.environ.get("LLM_MAX_RETRIES") or "3")

        if provider == LLMProvider.OPENAI:
            if not api_key and os.environ.get("OPENAI_API_KEY"):
                api_key = os.environ["OPENAI_API_KEY"]
            if not model_name:
                model_name = "gpt-4o-mini"
            if not api_base:
                api_base = "https://api.openai.com/v1"
            if not api_key and os.environ.get("DEEPSEEK_API_KEY"):
                api_key = os.environ["DEEPSEEK_API_KEY"]
                model_name = model_name or "deepseek-chat"
                api_base = api_base or "https://api.deepseek.com"
        elif provider == LLMProvider.OLLAMA:
            model_name = model_name or os.environ.get("OLLAMA_MODEL") or "qwen3:4b"
            api_base = api_base or f"{scheme}://{host}:{port}"
        elif provider == LLMProvider.CUSTOM:
            model_name = model_name or "default"
            api_base = api_base or cls(
                provider=provider,
                model_name=model_name,
                host=host,
                port=port,
                scheme=scheme,
                api_path=api_path,
            ).build_base_url()
            api_key = api_key or os.environ.get("LLM_API_KEY") or "no-key"
        elif provider == LLMProvider.VF_SERVER:
            model_name = model_name or os.environ.get("VF_MODEL_NAME") or "qwen2.5-4b-agent-q4km"
            host = os.environ.get("VF_SERVER_HOST") or host
            port = int(os.environ.get("VF_SERVER_PORT") or port or 9500)

        if not model_name:
            raise EnvironmentError("LLM_MODEL_NAME is required.")

        return cls(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            host=host,
            port=port,
            scheme=scheme,
            api_path=api_path,
            timeout=timeout,
            max_retries=max_retries,
        )
