from pathlib import Path

from control.llm_calls import FunctionCallService
from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput
from llm.models.mqtt import control_command_to_mqtt
from llm.models.output import ActionPlan, LocalPlannerOutput, Step2Output
from llm.utils.logging import WorkflowLogger, WorkflowStage, ansi_cprint
from llm.workflow.decision import DecisionStep
from llm.workflow.diagnosis import DiagnosisStep
from llm.workflow.final_command import FinalCommandGenerator
from llm.workflow.planning import PlanningStep
from llm.workflow.playbook import RuleBasedPlaybookRetriever
from llm.workflow.safety_shield import SafetyShield
from llm.workflow.side_effects import SideEffectEvaluator
from llm.workflow.simulation import Simulator


class LocalWorkflow:
    """Full local agent workflow orchestrator (legacy LocalPlanner behavior)."""

    def __init__(
        self,
        client: BaseLLMClient,
        repair_client: BaseLLMClient | None = None,
        max_tries: int = 2,
        playbook_path: str | Path | None = None,
        fc_service: FunctionCallService | None = None,
        logger: WorkflowLogger | None = None,
    ) -> None:
        self.client = client
        self.repair_client = repair_client or client
        self.max_tries = max_tries
        self.logger = logger or WorkflowLogger()
        self.playbook = RuleBasedPlaybookRetriever(playbook_path=playbook_path)
        self.diagnosis = DiagnosisStep(client, self.repair_client)
        self.planning = PlanningStep(client, self.repair_client)
        self.side_effects = SideEffectEvaluator(client)
        self.safety_shield = SafetyShield(self.logger)
        self.simulator = Simulator(fc_service=fc_service, logger=self.logger)
        self.decision = DecisionStep(client, self.repair_client)
        self.final_command = FinalCommandGenerator(client, self.repair_client, self.logger)

    def _finalize(
        self,
        user_input: LocalLLMInput,
        chosen_plan: ActionPlan,
        comments: str,
    ) -> LocalPlannerOutput:
        control_command = self.final_command.generate(user_input, chosen_plan)
        mqtt_command = control_command_to_mqtt(control_command, user_input.board_id)
        self.logger.stage(
            WorkflowStage.FINAL_COMMAND,
            f"fan_pwm={control_command.fan_pwm}, led_pwm={control_command.led_pwm}",
        )
        self.logger.detail(mqtt_command.to_json(indent=2))
        return LocalPlannerOutput(
            comments=comments,
            solution_action=chosen_plan,
            control_command=control_command,
            mqtt_command=mqtt_command,
        )

    def execute(self, user_input: LocalLLMInput) -> LocalPlannerOutput:
        last_filtered: Step2Output | None = None
        for attempt in range(1, self.max_tries + 1):
            try:
                ansi_cprint(f"# Starting plan generation (attempt {attempt}/{self.max_tries})", fg="green", style="bold")

                recalled = self.playbook.retrieve(user_input)
                playbook_context = self.playbook.format_context(recalled)
                case_ids = ", ".join(case.case_id for case in recalled) or "none"
                self.logger.stage(WorkflowStage.PLAYBOOK, f"Recalled cases: {case_ids}")
                self.logger.detail(playbook_context)

                step1_output = self.diagnosis.step1(user_input, playbook_context)
                self.logger.stage(WorkflowStage.DIAGNOSIS, step1_output.core_issue)
                self.logger.detail(f"States: {step1_output.states}")

                corrected = self.diagnosis.validate_consistency(user_input, step1_output)
                if corrected:
                    step1_output = corrected
                    self.logger.detail(f"Corrected diagnosis: {step1_output.core_issue}")

                revised_step1 = self.diagnosis.revised_step1(user_input, step1_output)
                self.logger.detail(f"Revised diagnosis: {revised_step1.core_issue}")

                filtered_step2_output = None
                simulated_results: list[str] = []
                for inner_try in range(3):
                    step2_output = self.planning.step2(user_input, revised_step1, playbook_context)
                    self.logger.stage(
                        WorkflowStage.CANDIDATES,
                        f"Generated {len(step2_output.action_plan)} candidate solutions (try {inner_try + 1})",
                    )
                    for plan in step2_output.action_plan:
                        self.logger.detail(f"{plan.solution_id}: {plan.description}")

                    step2_revised = self.planning.step2_revised(user_input, revised_step1, step2_output)
                    side_effect_eval = self.side_effects.evaluate(user_input, step2_revised)
                    self.logger.stage(
                        WorkflowStage.SIDE_EFFECTS,
                        f"Evaluated {len(side_effect_eval.evaluations)} solutions for side effects",
                    )
                    filtered_step2_output = self.side_effects.filter_solutions(step2_revised, side_effect_eval)

                    filtered_step2_output = self.safety_shield.filter(user_input, filtered_step2_output)
                    self.logger.stage(
                        WorkflowStage.SAFETY_SHIELD,
                        f"{len(filtered_step2_output.action_plan)} solutions passed safety shield",
                    )

                    simulated_results = self.simulator.simulate_sync(user_input, filtered_step2_output)
                    self.logger.stage(WorkflowStage.SIMULATION, f"{len(simulated_results)} simulation results")
                    if simulated_results:
                        break

                if filtered_step2_output is None:
                    raise ValueError("Planning failed to produce any step2 output")

                last_filtered = filtered_step2_output

                step3_output = self.decision.step3(user_input, revised_step1, filtered_step2_output, simulated_results)
                step3_eval = self.decision.evaluate_step3_decision(
                    user_input,
                    step3_output,
                    filtered_step2_output.action_plan,
                    simulated_results,
                )
                revised_step3 = self.decision.step3_revised(filtered_step2_output, step3_output, step3_eval)
                self.logger.stage(
                    WorkflowStage.DECISION,
                    f"{revised_step3.final_decision} ({step3_eval.decision_quality})",
                )

                if revised_step3.final_decision in {"NO_SOLUTION", "re_assess_solution"}:
                    if attempt == self.max_tries and filtered_step2_output.action_plan:
                        best = max(filtered_step2_output.action_plan, key=lambda plan: plan.confidence)
                        self.logger.warn(
                            f"Forcing fallback plan {best.solution_id} after re_assess_solution on final attempt"
                        )
                        return self._finalize(
                            user_input,
                            best,
                            f"{revised_step3.reason} (fallback: best remaining plan after re-assess)",
                        )
                    continue

                if self.decision.should_regenerate_all_plans(step3_eval, filtered_step2_output.action_plan):
                    if attempt == self.max_tries and filtered_step2_output.action_plan:
                        best = max(filtered_step2_output.action_plan, key=lambda plan: plan.confidence)
                        self.logger.warn(f"Forcing fallback plan {best.solution_id} after regenerate suggestion")
                        return self._finalize(
                            user_input,
                            best,
                            "Fallback to best plan after regeneration was suggested on final attempt",
                        )
                    self.logger.warn("Regenerating all plans due to poor step3 evaluation")
                    continue

                chosen_plan = next(
                    (plan for plan in filtered_step2_output.action_plan if plan.solution_id == revised_step3.final_decision),
                    None,
                )
                if chosen_plan is None and filtered_step2_output.action_plan:
                    chosen_plan = filtered_step2_output.action_plan[0]
                    self.logger.warn(f"Using fallback plan {chosen_plan.solution_id}")

                if chosen_plan is None:
                    continue

                return self._finalize(user_input, chosen_plan, revised_step3.reason)
            except Exception as error:
                ansi_cprint(f"[LocalWorkflow] attempt {attempt} failed: {error}", fg="red")
                if attempt == self.max_tries:
                    fallback = ActionPlan(
                        solution_id="ERROR_FALLBACK",
                        description="Failed to generate plan due to processing errors",
                        function_calls=[],
                        confidence=1,
                    )
                    return LocalPlannerOutput(comments=f"Plan generation failed: {error}", solution_action=fallback)

        if last_filtered and last_filtered.action_plan:
            best = max(last_filtered.action_plan, key=lambda plan: plan.confidence)
            self.logger.warn(f"Maximum attempts exceeded; using best plan {best.solution_id}")
            return self._finalize(
                user_input,
                best,
                "Maximum attempts exceeded; emitted best available plan as fallback",
            )

        fallback = ActionPlan(
            solution_id="THE_BEST_ONE",
            description="Failed to generate plan after maximum attempts",
            function_calls=[],
            confidence=1,
        )
        return LocalPlannerOutput(comments="Maximum attempts exceeded", solution_action=fallback)
