from langchain_core.output_parsers import JsonOutputParser

from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput
from llm.models.output import (
    ActionPlan,
    SideEffectConcern,
    SideEffectEvaluation,
    SideEffectEvaluationOutput,
    Step2Output,
)
from llm.prompts.local import curr_env_status, goal_and_objectives, role_and_task


class SideEffectEvaluator:
    def __init__(self, client: BaseLLMClient) -> None:
        self.client = client

    def evaluate(self, user_input: LocalLLMInput, step2_output: Step2Output) -> SideEffectEvaluationOutput:
        evaluations: list[SideEffectEvaluation] = []
        for action_plan in step2_output.action_plan:
            concerns = self._analyze_solution_adjustments(action_plan)
            if not concerns:
                continue
            try:
                side_effect_prompt = self._generate_side_effect_prompt(user_input, action_plan, concerns)
                full_prompt = f"""{role_and_task}
{goal_and_objectives}
{curr_env_status}
{side_effect_prompt}

Please respond in JSON format:
{{
    "solution_id": "{action_plan.solution_id}",
    "side_effects": [
        {{
            "parameter_name": "string",
            "change_magnitude": 0,
            "change_type": "string",
            "potential_impact": "string",
            "risk_level": "string"
        }}
    ],
    "overall_risk_assessment": "string",
    "recommended_action": "proceed, modify, or reject",
    "confidence": 5
}}
"""
                evaluation_response = self.client.run_messages(
                    [{"role": "user", "content": full_prompt}],
                    temperature=0.2,
                )
                parsed_json = JsonOutputParser().invoke(evaluation_response)
                evaluations.append(SideEffectEvaluation.model_validate(parsed_json))
            except Exception as error:
                print(f"[SideEffectEvaluator] Error for {action_plan.solution_id}: {error}")
                evaluations.append(
                    SideEffectEvaluation(
                        solution_id=action_plan.solution_id,
                        side_effects=concerns,
                        overall_risk_assessment=f"Unable to fully evaluate. Identified {len(concerns)} concerns.",
                        recommended_action="modify" if any(c.risk_level == "high" for c in concerns) else "proceed",
                        confidence=3,
                    )
                )
        return SideEffectEvaluationOutput(evaluations=evaluations)

    def filter_solutions(
        self,
        step2_output: Step2Output,
        side_effect_evaluation: SideEffectEvaluationOutput,
    ) -> Step2Output:
        filtered: list[ActionPlan] = []
        evaluation_lookup = {item.solution_id: item for item in side_effect_evaluation.evaluations}
        for action_plan in step2_output.action_plan:
            evaluation = evaluation_lookup.get(action_plan.solution_id)
            if evaluation is None:
                filtered.append(action_plan)
                continue
            if evaluation.recommended_action == "proceed":
                filtered.append(action_plan)
            elif evaluation.recommended_action == "modify":
                filtered.append(
                    ActionPlan(
                        solution_id=action_plan.solution_id,
                        description=f"{action_plan.description} (CAUTION: {evaluation.overall_risk_assessment})",
                        confidence=max(1, action_plan.confidence - 1),
                        function_calls=action_plan.function_calls,
                    )
                )
            elif evaluation.recommended_action != "reject":
                filtered.append(action_plan)
        return Step2Output(action_plan=filtered)

    def _analyze_solution_adjustments(self, action_plan: ActionPlan) -> list[SideEffectConcern]:
        concerns: list[SideEffectConcern] = []
        for func_call in action_plan.function_calls:
            func_name = func_call.name.lower()
            arguments = func_call.arguments
            if "fan" in func_name and "fan_speed_change" in arguments:
                change = float(arguments["fan_speed_change"])
                if abs(change) >= 15:
                    concerns.append(
                        SideEffectConcern(
                            parameter_name="fan_speed",
                            change_magnitude=abs(change),
                            change_type="increase" if change > 0 else "decrease",
                            potential_impact="humidity_reduction" if change > 0 else "humidity_increase",
                            risk_level="high" if abs(change) >= 25 else "medium",
                        )
                    )
            elif ("led" in func_name or "light" in func_name) and "led_brightness_change" in arguments:
                change = float(arguments["led_brightness_change"])
                if abs(change) >= 20:
                    concerns.append(
                        SideEffectConcern(
                            parameter_name="led_brightness",
                            change_magnitude=abs(change),
                            change_type="increase" if change > 0 else "decrease",
                            potential_impact="temperature_spike" if change > 0 else "photosynthesis_reduction",
                            risk_level="high" if abs(change) >= 30 else "medium",
                        )
                    )
        return concerns

    def _generate_side_effect_prompt(
        self,
        user_input: LocalLLMInput,
        action_plan: ActionPlan,
        concerns: list[SideEffectConcern],
    ) -> str:
        base_prompt = f"You have proposed the following solution: {action_plan.description}\n\nPotential adjustments:\n"
        for concern in concerns:
            base_prompt += (
                f"- {concern.change_type} {concern.parameter_name} by {concern.change_magnitude} "
                f"(impact: {concern.potential_impact}, risk: {concern.risk_level})\n"
            )
        base_prompt += f"""
Current environmental conditions:
- Internal temperature: {user_input.internal_temp}°C
- Ideal range: {user_input.ideal_temp_range[0]}-{user_input.ideal_temp_range[1]}°C
- Fan status: {user_input.fan_status}
- LED status: {user_input.led_light_status}
"""
        return base_prompt
