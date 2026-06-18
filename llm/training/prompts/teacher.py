from __future__ import annotations

import json
from typing import Any

from llm.models.output import (
    ControlCommand,
    SideEffectEvaluation,
    Step1Output,
    Step2Output,
    Step3Output,
)
from llm.training.prompts.examples import STAGE_EXAMPLES, get_few_shot_example
from llm.training.schemas import DPOFlawCategory, SeedScenario, WorkflowStage

TEACHER_SYSTEM_ROLE = """
You are an expert vertical-farm control annotator generating high-quality training data.
Produce physically plausible, JSON-compliant outputs for the specified workflow stage.
"""

DEVICE_CONSTRAINTS = """
# Device Constraints
- Fans can only cool the room to external temperature within ~3 minutes.
- LED lights can heat the room up to ~3°C in 15 minutes when fans are OFF.
- During Lights OFF, LED must remain OFF (no emergency heating without explicit rationale).
- During Lights ON, LED must remain ON to support photosynthesis.
- Fan speed change must not exceed ±70%; LED brightness change must not exceed ±50%.
- Fan RPM range: 0–3400. LED PWM: 0–100%.
"""

FORBIDDEN_PATTERNS = """
# Forbidden Patterns
- Do NOT output raw MQTT commands or skip simulation steps.
- Do NOT use unquoted JSON keys or trailing commas.
- Do NOT propose physically impossible actions (e.g., max LED + zero fan when overheating).
- Do NOT violate photoperiod constraints.
"""

STAGE_SCHEMAS: dict[WorkflowStage, type] = {
    WorkflowStage.DIAGNOSIS: Step1Output,
    WorkflowStage.PLANNING: Step2Output,
    WorkflowStage.SIDE_EFFECT: SideEffectEvaluation,
    WorkflowStage.DECISION: Step3Output,
    WorkflowStage.FINAL_COMMAND: ControlCommand,
}

NEGATIVE_INSTRUCTIONS: dict[DPOFlawCategory, str] = {
    DPOFlawCategory.JSON_FORMAT: "Produce intentionally malformed JSON: missing required fields, unquoted keys, or trailing commas.",
    DPOFlawCategory.PHYSICAL_CONTRADICTION: (
        "Produce a plan that contradicts physics: e.g., max LED + zero fan when internal temp exceeds ideal high."
    ),
    DPOFlawCategory.SAFETY_BYPASS: (
        "Skip the simulation step and output a direct MQTT control command instead of function calls."
    ),
    DPOFlawCategory.CONSTRAINT_VIOLATION: (
        "Violate photoperiod: set LED > 0 during Lights OFF without emergency heating rationale."
    ),
}


def _serialize_seed(seed: SeedScenario) -> str:
    payload = {
        "state_vector": seed.state_vector.model_dump(),
        "operator_action": seed.operator_action.model_dump(),
        "operator_rationale": seed.operator_rationale,
        "crop_context": seed.crop_context.model_dump(),
    }
    return json.dumps(payload, indent=2)


def _serialize_prior(prior_outputs: dict[str, Any] | None) -> str:
    if not prior_outputs:
        return "None"
    return json.dumps(prior_outputs, indent=2)


def build_teacher_prompt(
    stage: WorkflowStage,
    seed: SeedScenario,
    prior_outputs: dict[str, Any] | None = None,
) -> str:
    schema_model = STAGE_SCHEMAS[stage]
    example = get_few_shot_example(stage)
    return f"""{TEACHER_SYSTEM_ROLE}

{DEVICE_CONSTRAINTS}

# Input State
{_serialize_seed(seed)}

# Prior Workflow Outputs
{_serialize_prior(prior_outputs)}

# Target Stage
{stage.value}

# Output JSON Schema
{json.dumps(schema_model.model_json_schema(), indent=2)}

# Few-Shot Example
Input: {json.dumps(example.get('input_state', {}), indent=2)}
Output: {json.dumps(example['output_json'], indent=2)}

{FORBIDDEN_PATTERNS}

Generate ONLY the JSON output for stage '{stage.value}'. No markdown fences, no explanation.
"""


def build_negative_prompt(
    stage: WorkflowStage,
    seed: SeedScenario,
    flaw_category: DPOFlawCategory,
    prior_outputs: dict[str, Any] | None = None,
) -> str:
    instruction = NEGATIVE_INSTRUCTIONS[flaw_category]
    return f"""{TEACHER_SYSTEM_ROLE}

{DEVICE_CONSTRAINTS}

# Input State
{_serialize_seed(seed)}

# Prior Workflow Outputs
{_serialize_prior(prior_outputs)}

# Target Stage
{stage.value}

# NEGATIVE EXAMPLE INSTRUCTION
{instruction}

Generate a deliberately FLAWED output for training preference optimization (rejected sample).
Output ONLY the flawed JSON or text. No explanation.
"""
