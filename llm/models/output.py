from typing import Any

from pydantic import BaseModel, Field

from gateway.msg import ControlMsg


class Step1Output(BaseModel):
    core_issue: str
    states: list[str]
    confidence: list[int]


class FunctionCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    simulating_time: str


class ActionPlan(BaseModel):
    solution_id: str
    description: str
    function_calls: list[FunctionCall]
    confidence: int


class Step2Output(BaseModel):
    action_plan: list[ActionPlan]


class ActionSuggestion(BaseModel):
    solution_id: str
    description: str
    new_plan: str


class RevisedStep2Output(BaseModel):
    action_plan: list[ActionSuggestion]


class SideEffectConcern(BaseModel):
    parameter_name: str
    change_magnitude: float
    change_type: str
    potential_impact: str
    risk_level: str


class SideEffectEvaluation(BaseModel):
    solution_id: str
    side_effects: list[SideEffectConcern]
    overall_risk_assessment: str
    recommended_action: str
    confidence: int


class SideEffectEvaluationOutput(BaseModel):
    evaluations: list[SideEffectEvaluation]


class Step3Output(BaseModel):
    final_decision: str
    reason: str


class Step3EvaluationOutput(BaseModel):
    decision_quality: str
    meets_target_requirements: bool
    confidence_assessment: int
    recommended_action: str
    evaluation_reason: str
    alternative_suggestions: list[str]


class ControlCommand(BaseModel):
    fan_pwm: int
    led_pwm: int
    pid: dict[str, Any] = Field(default_factory=dict)
    rationale: str


class LocalPlannerOutput(BaseModel):
    comments: str
    solution_action: ActionPlan
    control_command: ControlCommand | None = None
    mqtt_command: ControlMsg | None = None
