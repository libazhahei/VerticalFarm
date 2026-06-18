from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import PromptTemplate

from llm.models.input import LocalLLMInput, build_step_data
from llm.models.output import ActionPlan, Step1Output, Step2Output
from llm.prompts.local import (
    curr_env_status,
    diagnosis_brief,
    diagnosis_output_prompt,
    diagnosis_prompt,
    environment_forecast,
    final_command_prompt,
    goal_and_objectives,
    history_context,
    plan_exploration,
    role_and_task,
    step2_brief,
    step2_functions_prompt,
    step2_output_prompt,
    step3_decision_prompt,
    step3_output_prompt,
)
from llm.training.schemas import WorkflowStage


def _fill_template(template: str, data: dict[str, Any]) -> str:
    return PromptTemplate.from_template(template).format(**data)


def build_diagnosis_prompt(user_input: LocalLLMInput, playbook_context: str = "") -> str:
    parts = [
        role_and_task,
        goal_and_objectives,
        curr_env_status,
        history_context,
        environment_forecast,
    ]
    if playbook_context:
        parts.append(f"\n# Playbook Context\n{playbook_context}\n")
    parts.extend([diagnosis_prompt, diagnosis_output_prompt])
    return _fill_template("".join(parts), build_step_data(user_input))


def build_planning_prompt(
    user_input: LocalLLMInput,
    step1_output: Step1Output,
    playbook_context: str = "",
) -> str:
    data = {**build_step_data(user_input), "summary": step1_output.core_issue}
    parts = [
        role_and_task,
        goal_and_objectives,
        curr_env_status,
        history_context,
        environment_forecast,
        step2_brief,
    ]
    if playbook_context:
        parts.append(f"\n# Playbook Context\n{playbook_context}\n")
    parts.extend([plan_exploration, step2_functions_prompt, step2_output_prompt])
    return _fill_template("".join(parts), data)


def build_side_effect_prompt(
    user_input: LocalLLMInput,
    action_plan: ActionPlan,
) -> str:
    data = build_step_data(user_input)
    fc_json = json.dumps([fc.model_dump() for fc in action_plan.function_calls])
    side_effect_block = f"""
# Side Effect Evaluation
Evaluate side effects for solution {action_plan.solution_id}:
{action_plan.description}

Function calls: {fc_json}

Respond in JSON with: solution_id, side_effects[], overall_risk_assessment, recommended_action, confidence.
"""
    base = _fill_template("".join([role_and_task, goal_and_objectives, curr_env_status]), data)
    return base + side_effect_block


def build_decision_prompt(
    user_input: LocalLLMInput,
    step1_output: Step1Output,
    simulated_results: list[str],
) -> str:
    data = {
        **build_step_data(user_input),
        "states": step1_output.states,
        "core_issue": step1_output.core_issue,
    }
    sim_block = "The simulated results are as follows:\n"
    for idx, result in enumerate(simulated_results):
        sim_block += f"- SOLUTION_{idx + 1:02d}: {result}\n"
    parts = [
        role_and_task,
        goal_and_objectives,
        diagnosis_brief,
        sim_block,
        step3_decision_prompt,
        step3_output_prompt,
    ]
    return _fill_template("".join(parts), data)


def build_final_command_prompt(user_input: LocalLLMInput, selected_plan: ActionPlan) -> str:
    data = {**build_step_data(user_input), **selected_plan.model_dump()}
    parts = [
        role_and_task,
        goal_and_objectives,
        curr_env_status,
        history_context,
        environment_forecast,
        final_command_prompt,
    ]
    return _fill_template("".join(parts), data)


def build_prompt_for_stage(
    stage: WorkflowStage,
    user_input: LocalLLMInput,
    prior_outputs: dict[str, Any] | None = None,
    playbook_context: str = "",
) -> str:
    prior = prior_outputs or {}
    if stage == WorkflowStage.DIAGNOSIS:
        return build_diagnosis_prompt(user_input, playbook_context)
    if stage == WorkflowStage.PLANNING:
        step1 = Step1Output.model_validate(prior["diagnosis"])
        return build_planning_prompt(user_input, step1, playbook_context)
    if stage == WorkflowStage.SIDE_EFFECT:
        step2 = Step2Output.model_validate(prior["planning"])
        if not step2.action_plan:
            raise ValueError("planning output required for side_effect stage")
        return build_side_effect_prompt(user_input, step2.action_plan[0])
    if stage == WorkflowStage.DECISION:
        step1 = Step1Output.model_validate(prior["diagnosis"])
        sim_results = prior.get("simulation_results", ["Temperature drops to 20.5°C within 15 min"])
        return build_decision_prompt(user_input, step1, sim_results)
    if stage == WorkflowStage.FINAL_COMMAND:
        step2 = Step2Output.model_validate(prior["planning"])
        if not step2.action_plan:
            raise ValueError("planning output required for final_command stage")
        return build_final_command_prompt(user_input, step2.action_plan[0])
    raise ValueError(f"Unknown stage: {stage}")


def format_chat_messages(user_prompt: str, assistant_json: str) -> list[dict[str, str]]:
    return [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": assistant_json},
    ]
