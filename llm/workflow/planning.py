import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput, build_step_data
from llm.models.output import (
    ActionPlan,
    ActionSuggestion,
    RevisedStep2Output,
    Step1Output,
    Step2Output,
)
from llm.prompts.local import (
    curr_env_status,
    environment_forecast,
    goal_and_objectives,
    history_context,
    plan_exploration,
    revised_step2_modify_prompt_part,
    revised_step2_output_prompt,
    revised_step2_prompt_part,
    role_and_task,
    step2_brief,
    step2_functions_prompt,
    step2_output_prompt,
)
from llm.utils.json import fix_and_validate_json


class PlanningStep:
    def __init__(self, client: BaseLLMClient, repair_client: BaseLLMClient | None = None) -> None:
        self.client = client
        self.repair_client = repair_client or client

    def _build_step2_data(self, user_input: LocalLLMInput, step1_output: Step1Output) -> dict:
        return {
            **build_step_data(user_input),
            "states": step1_output.states,
            "core_issue": step1_output.core_issue,
        }

    def step2(self, user_input: LocalLLMInput, step1_output: Step1Output, playbook_context: str = "") -> Step2Output:
        prompt_parts = [
            role_and_task,
            goal_and_objectives,
            curr_env_status,
            history_context,
            environment_forecast,
            step2_brief.format(summary=step1_output.core_issue),
        ]
        if playbook_context:
            prompt_parts.append(f"\n# Recalled Playbook\n{playbook_context}\n")
        prompt_parts.extend([plan_exploration, step2_functions_prompt, step2_output_prompt])
        step2_prompt = "".join(prompt_parts)
        step2_data = self._build_step2_data(user_input, step1_output)
        step2_data.update(
            {
                "core_issue": step1_output.core_issue,
                "states": step1_output.states,
                "confidence": step1_output.confidence,
            }
        )
        step2_prompt_template = PromptTemplate.from_template(step2_prompt)
        try:
            step2_response = self.client.run_chain(step2_prompt_template, step2_data, temperature=0.2)
            parsed_json = JsonOutputParser().invoke(step2_response)
            return Step2Output.model_validate(parsed_json)
        except Exception as error:
            print(f"[PlanningStep] Error in step2: {error}")
            return Step2Output(action_plan=[])

    def step2_revised(self, user_input: LocalLLMInput, step1_output: Step1Output, step2_output: Step2Output) -> Step2Output:
        def _build_part1_data() -> dict:
            prev_data = self._build_step2_data(user_input, step1_output)
            return {
                **prev_data,
                "solutions": [
                    f"Solution{idx}: {sol.description}" for idx, sol in enumerate(step2_output.action_plan, start=1)
                ],
            }

        def part_1() -> RevisedStep2Output:
            revised_step2_prompt = "".join(
                [role_and_task, goal_and_objectives, revised_step2_prompt_part, revised_step2_output_prompt]
            )
            revised_prompt_template = PromptTemplate.from_template(revised_step2_prompt)
            revised_data = _build_part1_data()
            try:
                revised_response = self.client.run_chain(revised_prompt_template, revised_data, temperature=0.2)
                parsed_json = JsonOutputParser().invoke(revised_response)
                return RevisedStep2Output.model_validate(parsed_json)
            except Exception as error:
                print(f"[PlanningStep] Error in revised_step2 part 1: {error}")
                try:
                    fixed_json = fix_and_validate_json(
                        revised_response,
                        RevisedStep2Output,
                        self.repair_client.get_model(temperature=0.0),
                    )
                    if fixed_json:
                        return RevisedStep2Output.model_validate(json.loads(fixed_json))
                except Exception:
                    pass
                return RevisedStep2Output(
                    action_plan=[
                        ActionSuggestion(
                            solution_id=action.solution_id,
                            description=action.description,
                            new_plan="Maintain current approach due to processing error",
                        )
                        for action in step2_output.action_plan
                    ]
                )

        def _build_part2_data(revised_output: RevisedStep2Output) -> dict:
            revised_solutions = [
                f"Solution{idx}: {sol.new_plan}" for idx, sol in enumerate(revised_output.action_plan, start=1)
            ]
            prev_data = _build_part1_data()
            return {
                **prev_data,
                "solutions": [
                    f"Solution{idx}: {sol.description}" for idx, sol in enumerate(step2_output.action_plan, start=1)
                ],
                "revised_step2_prompt_part": revised_solutions,
            }

        def part_2(revised_output: RevisedStep2Output) -> Step2Output:
            revised_modify_prompt = "".join(
                [
                    role_and_task,
                    goal_and_objectives,
                    curr_env_status,
                    step2_functions_prompt,
                    revised_step2_modify_prompt_part,
                    step2_output_prompt,
                ]
            )
            revised_prompt_template = PromptTemplate.from_template(revised_modify_prompt)
            revised_data = _build_part2_data(revised_output)
            try:
                revised_response = self.client.run_chain(revised_prompt_template, revised_data, temperature=0.2)
                parsed_json = JsonOutputParser().invoke(revised_response)
                return Step2Output.model_validate(parsed_json)
            except Exception as error:
                print(f"[PlanningStep] Error in revised_step2 part 2: {error}")
                try:
                    fixed_json = fix_and_validate_json(
                        revised_response,
                        Step2Output,
                        self.repair_client.get_model(temperature=0.0),
                    )
                    if fixed_json:
                        return Step2Output.model_validate(json.loads(fixed_json))
                except Exception:
                    pass
                return step2_output

        try:
            revised_output = part_1()
            return part_2(revised_output)
        except Exception as error:
            print(f"[PlanningStep] Error in step2_revised: {error}")
            return step2_output
