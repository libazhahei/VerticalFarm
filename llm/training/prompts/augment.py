"""Teacher prompts for LLM-based dataset augmentation from existing samples."""

from __future__ import annotations

import json
from typing import Any

from llm.training.prompts.teacher import DEVICE_CONSTRAINTS, FORBIDDEN_PATTERNS, STAGE_SCHEMAS
from llm.training.schemas import SeedScenario, WorkflowStage

AUGMENT_SYSTEM_ROLE = """
You are an expert vertical-farm training data augmentor.
Given an existing (input, output) demonstration, generate a NEW valid training example
for a slightly perturbed environmental scenario. The new output must remain physically
plausible and JSON-schema compliant.
"""

AUGMENT_STRATEGIES = {
    "perturbation": (
        "Apply the described state perturbation and produce an updated JSON output "
        "that correctly addresses the new conditions."
    ),
    "paraphrase": (
        "Keep the same environmental state and control intent, but paraphrase descriptions "
        "and optionally propose an alternative equally-valid solution (different fan/LED values within constraints)."
    ),
    "crop_context": (
        "The crop type or growth stage has changed. Update the output to reflect the new "
        "ideal temperature/humidity requirements while keeping the environmental state similar."
    ),
    "edge_case": (
        "Push the scenario toward an edge case (near threshold temperature, photoperiod boundary, "
        "or sensor anomaly) while maintaining a safe, valid control response."
    ),
}


def build_augment_prompt(
    stage: WorkflowStage,
    original_user: str,
    original_assistant: str,
    seed: SeedScenario | None,
    strategy: str,
    perturbation_desc: str = "",
) -> str:
    schema_model = STAGE_SCHEMAS[stage]
    strategy_instruction = AUGMENT_STRATEGIES.get(strategy, AUGMENT_STRATEGIES["perturbation"])
    seed_block = json.dumps(seed.model_dump(), indent=2) if seed else "N/A"
    return f"""{AUGMENT_SYSTEM_ROLE}

{DEVICE_CONSTRAINTS}

# Augmentation Strategy
{strategy}: {strategy_instruction}

# Perturbation / Variation Applied
{perturbation_desc or "Generate a meaningfully different but valid variant."}

# Perturbed / Target State
{seed_block}

# Original Training Example (reference — do NOT copy verbatim)
## Original User Prompt (excerpt)
{original_user[:2500]}

## Original Assistant Output
{original_assistant}

# Target Stage
{stage.value}

# Output JSON Schema
{json.dumps(schema_model.model_json_schema(), indent=2)}

{FORBIDDEN_PATTERNS}

Generate ONLY the new JSON output for the augmented scenario. No markdown fences.
"""


def build_dpo_augment_prompt(
    original_prompt: str,
    chosen: str,
    rejected: str,
    strategy: str = "edge_case",
) -> str:
    return f"""{AUGMENT_SYSTEM_ROLE}

You are creating a NEW preference pair for DPO training based on an existing pair.

# Strategy
{strategy}: Create a variant preference pair where the chosen response remains safe and
the rejected response violates a different but equally instructive constraint.

# Original Prompt
{original_prompt[:2000]}

# Original Chosen (safe)
{chosen}

# Original Rejected (unsafe)
{rejected}

Respond with JSON only:
{{
  "chosen": "<safe JSON or text>",
  "rejected": "<unsafe JSON or text>",
  "category": "<violation category>"
}}
"""
