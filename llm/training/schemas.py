from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    DIAGNOSIS = "diagnosis"
    PLANNING = "planning"
    SIDE_EFFECT = "side_effect"
    DECISION = "decision"
    FINAL_COMMAND = "final_command"

    @classmethod
    def all_stages(cls) -> list[WorkflowStage]:
        return list(cls)


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    ACCEPT = "accept"
    NEEDS_REVISION = "needs_revision"
    REJECT = "reject"


class StateVector(BaseModel):
    internal_temp: float
    external_temp: float
    internal_humidity: float
    external_humidity: float
    led_pwm: float
    fan_rpm: int
    photoperiod_status: str
    temp_trend_15min: str
    humidity_trend_15min: str


class OperatorAction(BaseModel):
    new_led_pwm: float
    new_fan_rpm: int


class CropContext(BaseModel):
    crop: str
    growth_stage: str
    ideal_temp_range: list[float]
    ideal_humidity_range: list[float]
    dli_target: float


class SeedScenario(BaseModel):
    seed_id: str
    state_vector: StateVector
    operator_action: OperatorAction
    operator_rationale: str
    crop_context: CropContext


class SFTSample(BaseModel):
    stage: WorkflowStage
    messages: list[dict[str, str]]
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_jsonl_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "messages": self.messages,
            "metadata": self.metadata,
        }


class DPOPair(BaseModel):
    prompt: str
    chosen: str
    rejected: str
    stage: WorkflowStage
    category: str = "safety_bypass"
    rejection_source: str = "teacher_flaw"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_jsonl_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "stage": self.stage.value,
            "category": self.category,
            "rejection_source": self.rejection_source,
            "metadata": self.metadata,
        }


class DPOFlawCategory(str, Enum):
    JSON_FORMAT = "json_format_violation"
    PHYSICAL_CONTRADICTION = "physical_contradiction"
    SAFETY_BYPASS = "safety_bypass"
    CONSTRAINT_VIOLATION = "constraint_violation"
