import json
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput, build_step_data
from llm.models.output import Step1Output
from llm.prompts.local import (
    curr_env_status,
    diagnosis_output_prompt,
    diagnosis_prompt,
    environment_forecast,
    goal_and_objectives,
    history_context,
    revised_step1_prompt_part,
    role_and_task,
)
from llm.utils.json import fix_and_validate_json


class DiagnosisStep:
    def __init__(self, client: BaseLLMClient, repair_client: BaseLLMClient | None = None) -> None:
        self.client = client
        self.repair_client = repair_client or client

    def step1(self, user_input: LocalLLMInput, playbook_context: str = "") -> Step1Output:
        prompt_parts = [
            role_and_task,
            goal_and_objectives,
            curr_env_status,
            history_context,
            environment_forecast,
        ]
        if playbook_context:
            prompt_parts.append(f"\n# Playbook Context\n{playbook_context}\n")
        prompt_parts.extend([diagnosis_prompt, diagnosis_output_prompt])
        step1_prompt = "".join(prompt_parts)
        step1_data = build_step_data(user_input)
        step1_prompt_template = PromptTemplate.from_template(step1_prompt)
        try:
            step1_response = self.client.run_chain(step1_prompt_template, step1_data, temperature=0.2)
            parsed_json = JsonOutputParser().invoke(step1_response)
            return Step1Output.model_validate(parsed_json)
        except Exception as error:
            print(f"[DiagnosisStep] Error in step1: {error}")
            return Step1Output(
                core_issue="Unable to analyze current conditions due to processing error",
                states=["Stable Maintenance"],
                confidence=[5],
            )

    def validate_consistency(self, user_input: LocalLLMInput, step1_output: Step1Output) -> Optional[Step1Output]:
        contradictions: list[str] = []
        current_temp = user_input.internal_temp
        ideal_range = user_input.ideal_temp_range
        temp_trend = user_input.history_temp_change[-3:] if len(user_input.history_temp_change) >= 3 else user_input.history_temp_change
        is_temp_high = current_temp > ideal_range[1]
        is_temp_low = current_temp < ideal_range[0]
        is_temp_rising = len(temp_trend) >= 2 and temp_trend[-1] > temp_trend[-2]
        diagnosed_states = [state.lower() for state in step1_output.states]

        if is_temp_high and not any("high" in state and "temp" in state for state in diagnosed_states):
            contradictions.append(
                f"Temperature is {current_temp}°C (above ideal {ideal_range[1]}°C) but diagnosis doesn't mention high temperature"
            )
        if is_temp_rising and not any("rising" in state or "increasing" in state or "trend" in state for state in diagnosed_states):
            contradictions.append(f"Temperature trend is rising {temp_trend} but diagnosis doesn't mention rising trend")
        if is_temp_low and not any("low" in state and "temp" in state for state in diagnosed_states):
            contradictions.append(
                f"Temperature is {current_temp}°C (below ideal {ideal_range[0]}°C) but diagnosis doesn't mention low temperature"
            )

        if not contradictions:
            return None

        correction_prompt = f"""The initial diagnosis shows potential consistency issues. Please review and provide a corrected diagnosis.

INITIAL DIAGNOSIS: {step1_output.core_issue}
DIAGNOSED STATES: {step1_output.states}

CONSISTENCY ISSUES DETECTED:
{chr(10).join(f"- {c}" for c in contradictions)}

ENVIRONMENTAL FACTS:
- Current temperature: {current_temp}°C
- Ideal range: {ideal_range[0]}-{ideal_range[1]}°C
- Recent temperature trend: {temp_trend}
- Fan status: {user_input.fan_status}
- LED status: {user_input.led_light_status}

Please provide a corrected diagnosis that addresses these consistency issues:
{diagnosis_output_prompt}
"""
        try:
            correction_response = self.client.run_messages([{"role": "user", "content": correction_prompt}], temperature=0.2)
            parsed_json = JsonOutputParser().invoke(correction_response)
            return Step1Output.model_validate(parsed_json)
        except Exception as error:
            print(f"[DiagnosisStep] Failed to generate correction: {error}")
            return None

    def revised_step1(self, user_input: LocalLLMInput, step1_output: Step1Output) -> Step1Output:
        revised_step1_prompt = "".join(
            [
                role_and_task,
                goal_and_objectives,
                curr_env_status,
                history_context,
                environment_forecast,
                revised_step1_prompt_part,
                diagnosis_output_prompt,
            ]
        )
        core_reason = step1_output.core_issue
        result: list[Step1Output] = []

        for state, confidence in zip(step1_output.states, step1_output.confidence):
            try:
                revised_data = {
                    **build_step_data(user_input),
                    "state": state,
                    "core_issue": core_reason,
                    "confidence": confidence,
                }
                revised_prompt_template = PromptTemplate.from_template(revised_step1_prompt)
                revised_response = self.client.run_chain(revised_prompt_template, revised_data, temperature=0.2)
                parsed_json = JsonOutputParser().invoke(revised_response)
                revised_output = Step1Output.model_validate(parsed_json)
                result.append(revised_output)
            except Exception as error:
                print(f"[DiagnosisStep] Error in revised_step1 for state '{state}': {error}")
                try:
                    fixed_json = fix_and_validate_json(
                        revised_response,
                        Step1Output,
                        self.repair_client.get_model(temperature=0.0),
                    )
                    if fixed_json:
                        result.append(Step1Output.model_validate(json.loads(fixed_json)))
                    else:
                        result.append(
                            Step1Output(core_issue=core_reason, states=[state], confidence=[confidence])
                        )
                except Exception:
                    result.append(Step1Output(core_issue=core_reason, states=[state], confidence=[confidence]))

        if not result:
            return step1_output

        combined_states: set[str] = set()
        state_confidence_map: dict[str, int] = {}
        for output in result:
            for state, conf in zip(output.states, output.confidence):
                combined_states.add(state)
                if state not in state_confidence_map or conf > state_confidence_map[state]:
                    state_confidence_map[state] = conf

        final_states = list(combined_states)
        final_confidence = [state_confidence_map[state] for state in final_states]
        most_detailed_core_issue = core_reason
        for output in result:
            if len(output.core_issue) > len(most_detailed_core_issue):
                most_detailed_core_issue = output.core_issue

        return Step1Output(
            core_issue=most_detailed_core_issue,
            states=final_states,
            confidence=final_confidence,
        )
