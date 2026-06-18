"""Prompt splitting, stage detection, and cache signatures for vf-server."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from langchain_core.prompts import PromptTemplate

from llm.models.input import LocalLLMInput, build_step_data
from llm.prompts.local import (
    curr_env_status,
    environment_forecast,
    goal_and_objectives,
    history_context,
    role_and_task,
)

STATIC_TEMPLATE = role_and_task + goal_and_objectives
SENSOR_TEMPLATE = curr_env_status + history_context + environment_forecast

STAGE_MARKERS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("decision", ("# Decision Making", "final_decision")),
    ("final_command", ("# Command Generation",)),
    ("side_effects", ("overall_risk_assessment", "side_effects", "Side Effect")),
    ("action_assessment", ("# Revised Solution Assessment", "new_plan")),
    ("action_plan", ("# Action Plan Explanation", "function_calls")),
    ("diagnosis_assessment", ("# Your Proposed Diagnosis", "reliability of that result")),
    ("diagnosis_rethink", ("expanded context", "re-diagnos", "rethink")),
    ("diagnosis", ("# Diagnosis", "core_issue")),
)


def bucket_temperature(value: float, width: float = 2.0) -> str:
    lower = int(value // width) * width
    upper = lower + width
    return f"{int(lower)}-{int(upper)}"


def bucket_humidity(value: float, width: float = 10.0) -> str:
    lower = int(value // width) * width
    upper = lower + width
    return f"{int(lower)}-{int(upper)}"


def bucket_trend(history: list[float]) -> tuple[str, str, float]:
    if not history:
        return "0", "lo", 0.0
    trend = sum(history) / len(history)
    sign = "+" if trend > 0.05 else "-" if trend < -0.05 else "0"
    magnitude = "hi" if abs(trend) > 1.5 else "mid" if abs(trend) > 1.0 else "lo"
    return sign, magnitude, trend


def build_state_signature(user_input: LocalLLMInput) -> Dict[str, Any]:
    sign, magnitude, trend = bucket_trend(user_input.history_temp_change)
    external = user_input.pred_env_temp_range[0] if user_input.pred_env_temp_range else user_input.internal_temp
    photoperiod = "ON" if user_input.photoperiod_status.upper() in {"ON", "LIGHTS_ON"} else "OFF"
    return {
        "internal_temp_bucket": bucket_temperature(user_input.internal_temp),
        "external_temp_bucket": bucket_temperature(external),
        "humidity_bucket": bucket_humidity(user_input.humidity),
        "photoperiod": photoperiod,
        "temp_trend_sign": sign,
        "temp_trend_magnitude": magnitude,
        "crop": getattr(user_input, "crop", "iceberg_lettuce"),
        "growth_stage": getattr(user_input, "growth_stage", "head_development"),
        "temp_trend_c_per_15min": trend,
    }


def detect_stage(prompt_text: str, messages_text: str = "") -> str:
    haystack = f"{prompt_text}\n{messages_text}".lower()
    for stage, markers in STAGE_MARKERS:
        if any(marker.lower() in haystack for marker in markers):
            return stage
    return "diagnosis"


def split_prompt_segments(prompt_template: PromptTemplate, data: dict[str, Any]) -> Dict[str, str]:
    static_prefix = PromptTemplate.from_template(STATIC_TEMPLATE).format(**data)
    sensor_state = PromptTemplate.from_template(SENSOR_TEMPLATE).format(**data)
    full_prompt = prompt_template.format(**data)

    instruction = full_prompt
    if full_prompt.startswith(static_prefix):
        instruction = instruction[len(static_prefix) :]
    if sensor_state in instruction:
        instruction = instruction.replace(sensor_state, "", 1)
    instruction = instruction.strip()

    return {
        "static_prefix": static_prefix.strip(),
        "instruction": instruction,
        "sensor_state": sensor_state.strip(),
    }


def split_messages_prompt(messages: list[dict[str, Any]]) -> Dict[str, str]:
    combined = "\n".join(str(item.get("content", "")) for item in messages)
    return {
        "static_prefix": PromptTemplate.from_template(STATIC_TEMPLATE).format(
            **{key: "?" for key in ("ideal_temp_low", "ideal_temp_high")}
        ),
        "instruction": combined.strip(),
        "sensor_state": "",
    }
