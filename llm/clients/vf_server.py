"""LLM client that proxies inference to the vf Rust TCP server."""

from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.chat_models import BaseChatModel as LCBaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import PromptTemplate
from pydantic import ConfigDict

from llm.clients.base import BaseLLMClient
from llm.clients.config import LLMClientConfig, LLMProvider
from llm.clients.vf_context import get_cycle_id, get_stage_override, get_user_input
from llm.clients.vf_prompt import (
    SENSOR_TEMPLATE,
    STATIC_TEMPLATE,
    build_state_signature,
    detect_stage,
    split_prompt_segments,
)
from llm.clients.vf_models import preload_models_for_stage, preload_models_for_workflow_start, resolve_model_for_stage
from llm.clients.vf_tcp import TcpInferenceTransport
from llm.models.input import build_step_data


class VfServerChatModel(LCBaseChatModel):
    """Minimal LangChain chat model that routes invoke() to VFServerClient."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    client: Any
    temperature: float = 0.2

    @property
    def _llm_type(self) -> str:
        return "vf-server"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        temperature = float(kwargs.get("temperature", self.temperature))
        payload_messages = [{"role": "user", "content": message.content} for message in messages]
        text = self.client._infer_messages(payload_messages, temperature=temperature)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


class VFServerClient(BaseLLMClient):
    """Proxy LLM client: runs llm/ workflow locally, forwards infer calls to vf-server."""

    def __init__(
        self,
        config: LLMClientConfig,
        transport: TcpInferenceTransport | None = None,
        auto_heartbeat: bool = True,
    ) -> None:
        self._config = config
        self.transport = transport or TcpInferenceTransport(
            host=config.host,
            port=config.port,
            model_name=config.model_name,
        )
        self._auto_heartbeat = auto_heartbeat
        self._connected = False

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.VF_SERVER

    @property
    def config(self) -> LLMClientConfig:
        return self._config

    def connect(self) -> None:
        self.transport.connect()
        if self._auto_heartbeat:
            self.transport.start_heartbeat()
        self._connected = True
        try:
            self.transport.preload_models(preload_models_for_workflow_start())
        except Exception as error:
            print(f"[VFServerClient] initial preload skipped: {error}")

    def close(self) -> None:
        try:
            self.transport.cycle_end(get_cycle_id())
        except Exception:
            pass
        self.transport.close()
        self._connected = False

    def ensure_connected(self) -> None:
        if not self._connected:
            self.connect()

    def get_model(self, temperature: float = 0.2) -> BaseChatModel:
        self.ensure_connected()
        return VfServerChatModel(client=self, temperature=temperature)

    def run_chain(self, prompt_template: PromptTemplate, data: dict, temperature: float = 0.2) -> AIMessage:
        self.ensure_connected()
        stage = get_stage_override() or detect_stage(prompt_template.template)
        prompt_segments = split_prompt_segments(prompt_template, data)
        return AIMessage(content=self._infer(stage, prompt_segments, temperature))

    def run_messages(self, messages: list[dict], temperature: float = 0.2) -> AIMessage:
        self.ensure_connected()
        return AIMessage(content=self._infer_messages(messages, temperature=temperature))

    def _default_signature(self) -> dict:
        return {
            "internal_temp_bucket": "0-2",
            "external_temp_bucket": "0-2",
            "humidity_bucket": "0-10",
            "photoperiod": "ON",
            "temp_trend_sign": "0",
            "temp_trend_magnitude": "lo",
            "crop": "iceberg_lettuce",
            "growth_stage": "head_development",
        }

    def _infer_messages(self, messages: list[dict], temperature: float) -> str:
        messages_text = "\n".join(str(item.get("content", "")) for item in messages)
        stage = get_stage_override() or detect_stage("", messages_text)

        user_input = get_user_input()
        if user_input is None:
            prompt_segments = {
                "static_prefix": "",
                "instruction": messages_text,
                "sensor_state": "",
            }
            return self._infer(stage, prompt_segments, temperature, state_signature=self._default_signature())

        data = build_step_data(user_input)
        sensor_state = PromptTemplate.from_template(SENSOR_TEMPLATE).format(**data)
        static_prefix = PromptTemplate.from_template(STATIC_TEMPLATE).format(**data)
        prompt_segments = {
            "static_prefix": static_prefix.strip(),
            "instruction": messages_text,
            "sensor_state": sensor_state.strip(),
        }
        return self._infer(stage, prompt_segments, temperature, state_signature=build_state_signature(user_input))

    def _infer(
        self,
        stage: str,
        prompt_segments: dict[str, str],
        temperature: float,
        state_signature: dict | None = None,
    ) -> str:
        user_input = get_user_input()
        signature = state_signature or (build_state_signature(user_input) if user_input else self._default_signature())
        model_name = resolve_model_for_stage(stage, self.transport.model_name)
        preload_models = preload_models_for_stage(stage)
        response = self.transport.infer(
            stage=stage,
            cycle_id=get_cycle_id(),
            prompt=prompt_segments,
            state_signature=signature,
            model_name=model_name,
            temperature=temperature,
            preload_models=preload_models,
        )
        if response.get("cache_hit"):
            print(f"[VFServerClient] cache hit stage={stage} model={response.get('model_used', model_name)}")
        if response.get("model_fallback"):
            print(
                f"[VFServerClient] OOM fallback stage={stage} "
                f"model={response.get('model_used')} recovered={response.get('oom_recovered', False)}"
            )
        return str(response.get("output", ""))
