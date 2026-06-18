from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput
from llm.models.output import (
    ActionPlan,
    Step1Output,
    Step2Output,
    Step3EvaluationOutput,
    Step3Output,
)
from llm.prompts.local import (
    diagnosis_brief,
    goal_and_objectives,
    role_and_task,
    step3_decision_prompt,
    step3_output_prompt,
)
from llm.utils.json import fix_and_validate_json


class DecisionStep:
    def __init__(self, client: BaseLLMClient, repair_client: BaseLLMClient | None = None) -> None:
        self.client = client
        self.repair_client = repair_client or client

    def _build_step3_data(self, user_input: LocalLLMInput, step1_output: Step1Output) -> dict:
        from llm.models.input import build_step_data

        return {
            **build_step_data(user_input),
            "states": step1_output.states,
            "core_issue": step1_output.core_issue,
        }

    def _build_step3_prompt(self, simulated_plan: list[ActionPlan], simulated_results: list[str]) -> str:
        base_prompt = "The simulated results are as follows:\n"
        for plan, result in zip(simulated_plan, simulated_results):
            base_prompt += f"- {plan.solution_id}: {result}\n"
        return "".join(
            [
                role_and_task,
                goal_and_objectives,
                diagnosis_brief,
                base_prompt,
                step3_decision_prompt,
                step3_output_prompt,
            ]
        )

    def step3(
        self,
        user_input: LocalLLMInput,
        step1_output: Step1Output,
        step2_output: Step2Output,
        simulated_results: list[str],
    ) -> Step3Output:
        step3_prompt = self._build_step3_prompt(step2_output.action_plan, simulated_results)
        step3_prompt_template = PromptTemplate.from_template(step3_prompt)
        step3_data = self._build_step3_data(user_input, step1_output)
        try:
            step3_response = self.client.run_chain(step3_prompt_template, step3_data, temperature=0.2)
            parsed_json = JsonOutputParser().invoke(step3_response)
            return Step3Output.model_validate(parsed_json)
        except Exception as error:
            print(f"[DecisionStep] Error in step3: {error}")
            fixed_json = fix_and_validate_json(
                step3_response if "step3_response" in locals() else "{}",
                Step3Output,
                self.repair_client.get_model(temperature=0.0),
            )
            if fixed_json:
                return Step3Output.model_validate_json(fixed_json)
            raise ValueError("Failed to generate a valid step3 output after repair attempts.") from error

    def evaluate_step3_decision(
        self,
        user_input: LocalLLMInput,
        step3_output: Step3Output,
        action_plans: list[ActionPlan],
        simulation_results: list[str],
    ) -> Step3EvaluationOutput:
        selected_plan = next((plan for plan in action_plans if plan.solution_id == step3_output.final_decision), None)
        if not selected_plan:
            return Step3EvaluationOutput(
                decision_quality="poor",
                meets_target_requirements=False,
                confidence_assessment=1,
                recommended_action="regenerate_plans",
                evaluation_reason="Selected plan not found in available options",
                alternative_suggestions=[],
            )

        concerns: list[str] = []
        if selected_plan.confidence < 5:
            concerns.append(f"Selected plan has low confidence ({selected_plan.confidence}/10)")

        better_alternatives = [
            plan
            for plan in action_plans
            if plan.solution_id != step3_output.final_decision and plan.confidence > selected_plan.confidence
        ]

        simulation_quality = "good"
        for result in simulation_results:
            if any(keyword in result.lower() for keyword in ["error", "fail", "risk", "exceed"]):
                concerns.append(f"Simulation shows potential issues: {result}")
                simulation_quality = "concerning"

        target_alignment = self._check_target_alignment(user_input, selected_plan, simulation_results)

        if len(concerns) == 0 and target_alignment and simulation_quality == "good":
            decision_quality, meets_requirements, recommended_action = "excellent", True, "proceed"
        elif len(concerns) <= 1 and target_alignment:
            decision_quality, meets_requirements, recommended_action = "good", True, "proceed_with_caution"
        elif len(concerns) <= 2:
            decision_quality = "fair"
            meets_requirements = False
            recommended_action = "select_alternative" if better_alternatives else "regenerate_plans"
        else:
            decision_quality = "poor"
            meets_requirements = False
            recommended_action = "regenerate_plans"

        alternative_suggestions = [
            f"Consider {alt.solution_id} (confidence: {alt.confidence}): {alt.description[:100]}..."
            for alt in better_alternatives[:2]
        ]

        evaluation_reason = (
            f"Decision quality: {decision_quality}. Concerns: {len(concerns)}. "
            f"Target alignment: {'Yes' if target_alignment else 'No'}. Simulation quality: {simulation_quality}."
        )
        return Step3EvaluationOutput(
            decision_quality=decision_quality,
            meets_target_requirements=meets_requirements,
            confidence_assessment=max(1, min(10, selected_plan.confidence - len(concerns))),
            recommended_action=recommended_action,
            evaluation_reason=evaluation_reason,
            alternative_suggestions=alternative_suggestions,
        )

    def step3_revised(
        self,
        step2_output: Step2Output,
        step3_output: Step3Output,
        step3_evaluation: Step3EvaluationOutput,
    ) -> Step3Output:
        if step3_evaluation.recommended_action == "proceed":
            return step3_output
        if step3_evaluation.recommended_action == "proceed_with_caution":
            return Step3Output(
                final_decision=step3_output.final_decision,
                reason=f"{step3_output.reason} (CAUTION: {step3_evaluation.evaluation_reason})",
            )
        if step3_evaluation.recommended_action == "select_alternative":
            alternatives = [plan for plan in step2_output.action_plan if plan.solution_id != step3_output.final_decision]
            if alternatives:
                best_alternative = max(alternatives, key=lambda plan: plan.confidence)
                return Step3Output(
                    final_decision=best_alternative.solution_id,
                    reason=(
                        f"Revised decision: Selected {best_alternative.solution_id} instead of "
                        f"{step3_output.final_decision} due to evaluation concerns."
                    ),
                )
        if step3_evaluation.recommended_action == "regenerate_plans":
            return Step3Output(
                final_decision="re_assess_solution",
                reason=f"Plan regeneration required: {step3_evaluation.evaluation_reason}",
            )
        return step3_output

    def should_regenerate_all_plans(
        self,
        step3_evaluation: Step3EvaluationOutput,
        available_plans: list[ActionPlan],
    ) -> bool:
        if all(plan.confidence < 4 for plan in available_plans):
            return True
        if step3_evaluation.decision_quality == "poor" and step3_evaluation.confidence_assessment < 3:
            return True
        if not step3_evaluation.meets_target_requirements and not step3_evaluation.alternative_suggestions:
            return True
        return False

    def _check_target_alignment(
        self,
        user_input: LocalLLMInput,
        selected_plan: ActionPlan,
        simulation_results: list[str],
    ) -> bool:
        del simulation_results
        current_temp = user_input.internal_temp
        target_low, target_high = user_input.ideal_temp_range
        if target_low <= current_temp <= target_high:
            return True
        for func_call in selected_plan.function_calls:
            if current_temp < target_low:
                if "led" in func_call.name.lower() and func_call.arguments.get("led_brightness_change", 0) > 0:
                    return True
                if "fan" in func_call.name.lower() and func_call.arguments.get("fan_speed_change", 0) < 0:
                    return True
            elif current_temp > target_high:
                if "fan" in func_call.name.lower() and func_call.arguments.get("fan_speed_change", 0) > 0:
                    return True
                if "led" in func_call.name.lower() and func_call.arguments.get("led_brightness_change", 0) < 0:
                    return True
        return len(selected_plan.function_calls) == 0
