from llm.clients.base import BaseLLMClient
from llm.clients.config import LLMClientConfig, LLMProvider
from llm.clients.custom import CustomEndpointClient
from llm.clients.gguf import LocalGGUFClient
from llm.clients.ollama import OllamaClient
from llm.clients.openai_compat import OpenAIClient
from llm.clients.vf_server import VFServerClient


def create_llm_client(config: LLMClientConfig) -> BaseLLMClient:
    if config.provider == LLMProvider.OPENAI:
        return OpenAIClient(config)
    if config.provider == LLMProvider.OLLAMA:
        return OllamaClient(config)
    if config.provider == LLMProvider.CUSTOM:
        return CustomEndpointClient(config)
    if config.provider == LLMProvider.GGUF:
        model_path = config.extra.get("model_path")
        if not model_path:
            raise ValueError("GGUF provider requires extra.model_path")
        return LocalGGUFClient(model_path=model_path, **config.extra)
    if config.provider == LLMProvider.VF_SERVER:
        return VFServerClient(config)
    raise ValueError(f"Unsupported provider: {config.provider}")


def create_llm_client_from_env() -> BaseLLMClient:
    return create_llm_client(LLMClientConfig.from_env())
