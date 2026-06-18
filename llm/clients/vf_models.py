"""Model registry and per-stage model selection for vf-server proxy."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

WORKFLOW_STAGE_ORDER = [
    "diagnosis",
    "diagnosis_rethink",
    "diagnosis_assessment",
    "action_plan",
    "action_assessment",
    "side_effects",
    "decision",
    "final_command",
]

NEXT_STAGE_MODEL_HINTS: Dict[str, List[str]] = {
    "diagnosis": ["qwen2.5-4b-agent-q4km", "qwen2.5-1.5b-agent-q4km"],
    "diagnosis_rethink": ["qwen2.5-4b-agent-q4km"],
    "diagnosis_assessment": ["qwen2.5-1.5b-agent-q4km"],
    "action_plan": ["qwen2.5-4b-agent-q4km"],
    "action_assessment": ["qwen2.5-1.5b-agent-q4km"],
    "side_effects": ["qwen2.5-1.5b-agent-q4km"],
    "decision": ["qwen2.5-4b-agent-q4km"],
    "final_command": ["qwen2.5-4b-agent-q4km"],
}


def _default_registry_path() -> Path:
    env_path = os.environ.get("VF_MODELS_CONFIG")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "inference" / "models.json"


@lru_cache(maxsize=1)
def load_model_registry(path: Optional[str] = None) -> dict:
    registry_path = Path(path) if path else _default_registry_path()
    return json.loads(registry_path.read_text(encoding="utf-8"))


def resolve_model_for_stage(stage: str, requested: Optional[str] = None) -> str:
    registry = load_model_registry()
    if requested and _model_exists(registry, requested):
        return requested

    for spec in registry.get("models", []):
        stages = spec.get("stages", [])
        if stage in stages:
            return spec["name"]

    return registry.get("default_model", os.environ.get("VF_MODEL_NAME", "qwen2.5-4b-agent-q4km"))


def preload_models_for_stage(stage: str) -> List[str]:
    hints = list(NEXT_STAGE_MODEL_HINTS.get(stage, []))
    registry = load_model_registry()
    default = registry.get("default_model")
    if default and default not in hints:
        hints.append(default)
    return hints


def preload_models_for_workflow_start() -> List[str]:
    registry = load_model_registry()
    return [
        spec["name"]
        for spec in registry.get("models", [])
        if spec.get("preload", False)
    ]


def _model_exists(registry: dict, name: str) -> bool:
    return any(spec.get("name") == name for spec in registry.get("models", []))
