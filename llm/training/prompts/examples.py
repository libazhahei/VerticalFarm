"""Canonical few-shot examples for teacher LLM annotation."""

from __future__ import annotations

from typing import Any

from llm.training.schemas import WorkflowStage

EXAMPLE_DIAGNOSIS: dict[str, Any] = {
    "stage": WorkflowStage.DIAGNOSIS.value,
    "input_state": {
        "internal_temp": 24.2,
        "external_temp": 19.5,
        "internal_humidity": 72.0,
        "external_humidity": 45.0,
        "led_pwm": 0.70,
        "fan_rpm": 1800,
        "photoperiod": "Lights_ON",
        "temp_trend_15min": "+1.8°C",
        "crop": "iceberg_lettuce",
        "growth_stage": "seedling",
        "ideal_temp_range": [15, 21],
        "ideal_humidity_range": [50, 70],
    },
    "output_json": {
        "core_issue": (
            "Internal temperature at 24.2°C exceeds the seedling upper bound of 21°C and continues "
            "to rise at +1.8°C/15min. LED is at 70% PWM, contributing to heat load. External temperature "
            "(19.5°C) is below internal, so fan-based cooling is viable."
        ),
        "states": ["High Temperature", "Rising Trend"],
        "confidence": [9, 8],
    },
}

EXAMPLE_PLANNING: dict[str, Any] = {
    "stage": WorkflowStage.PLANNING.value,
    "input_state": EXAMPLE_DIAGNOSIS["input_state"],
    "output_json": {
        "action_plan": [
            {
                "solution_id": "SOLUTION_01",
                "description": (
                    "Reduce LED to 40% to cut heat load while maintaining partial photosynthesis. "
                    "Increase fan to 2800 RPM to accelerate cooling toward external 19.5°C."
                ),
                "function_calls": [
                    {
                        "name": "predict_temp_change_with_action",
                        "arguments": {"led_brightness_change": 40, "fan_speed_change": 2800},
                        "simulating_time": "15 minutes",
                    }
                ],
                "confidence": 9,
            },
            {
                "solution_id": "SOLUTION_02",
                "description": (
                    "Aggressive cooling: cut LED to 10% and run fan at maximum 3400 RPM. "
                    "Accept temporary DLI loss for rapid temperature recovery."
                ),
                "function_calls": [
                    {
                        "name": "predict_temp_change_with_action",
                        "arguments": {"led_brightness_change": 10, "fan_speed_change": 3400},
                        "simulating_time": "15 minutes",
                    }
                ],
                "confidence": 6,
            },
        ]
    },
}

EXAMPLE_DPO_PAIR: dict[str, Any] = {
    "stage": WorkflowStage.PLANNING.value,
    "context": {"internal_temp": 22.5, "ideal_temp_high": 21, "photoperiod": "Lights_ON"},
    "rejected": {
        "solution_id": "SOLUTION_REJECTED",
        "description": "Turn LED to 100% and fan to 0% to maximize DLI.",
        "function_calls": [
            {
                "name": "predict_temp_change_with_action",
                "arguments": {"led_brightness_change": 100, "fan_speed_change": 0},
            }
        ],
        "confidence": 8,
    },
    "chosen": {
        "solution_id": "SOLUTION_CHOSEN",
        "description": (
            "Temperature already exceeds upper bound. Reduce LED to 50% and increase fan to 2400 RPM. "
            "Restore LED incrementally once T < 20°C."
        ),
        "function_calls": [
            {
                "name": "predict_temp_change_with_action",
                "arguments": {"led_brightness_change": 50, "fan_speed_change": 2400},
            }
        ],
        "confidence": 9,
    },
}

EXAMPLE_DECISION: dict[str, Any] = {
    "stage": WorkflowStage.DECISION.value,
    "input_state": EXAMPLE_DIAGNOSIS["input_state"],
    "output_json": {
        "reason": "SOLUTION_01 brings temp into ideal range with acceptable risk",
        "final_decision": "SOLUTION_01",
    },
}

EXAMPLE_SIDE_EFFECT: dict[str, Any] = {
    "stage": WorkflowStage.SIDE_EFFECT.value,
    "output_json": {
        "solution_id": "SOLUTION_01",
        "side_effects": [
            {
                "parameter_name": "fan_speed",
                "change_magnitude": 20,
                "change_type": "increase",
                "potential_impact": "humidity_reduction",
                "risk_level": "medium",
            }
        ],
        "overall_risk_assessment": "Moderate humidity drop expected; acceptable for cooling priority.",
        "recommended_action": "proceed",
        "confidence": 7,
    },
}

EXAMPLE_FINAL_COMMAND: dict[str, Any] = {
    "stage": WorkflowStage.FINAL_COMMAND.value,
    "output_json": {
        "fan_pwm": 85,
        "led_pwm": 50,
        "pid": {},
        "rationale": "High internal temp requires aggressive cooling while maintaining partial photosynthesis.",
    },
}

STAGE_EXAMPLES: dict[WorkflowStage, dict[str, Any]] = {
    WorkflowStage.DIAGNOSIS: EXAMPLE_DIAGNOSIS,
    WorkflowStage.PLANNING: EXAMPLE_PLANNING,
    WorkflowStage.SIDE_EFFECT: EXAMPLE_SIDE_EFFECT,
    WorkflowStage.DECISION: EXAMPLE_DECISION,
    WorkflowStage.FINAL_COMMAND: EXAMPLE_FINAL_COMMAND,
}


def get_few_shot_example(stage: WorkflowStage) -> dict[str, Any]:
    return STAGE_EXAMPLES[stage]
